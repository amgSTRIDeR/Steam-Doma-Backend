import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta

KEEP_IMAGES = 3
RETENTION_DAYS = 7

ACR_NAME = os.environ["ACR_NAME"]
ACR_LOGIN_SERVER = os.environ["ACR_LOGIN_SERVER"]
RESOURCE_GROUP = os.environ["RESOURCE_GROUP"]
APP_NAME = os.environ["APP_NAME"]
REPOSITORY = APP_NAME
PREFIX = f"{ACR_LOGIN_SERVER}/{REPOSITORY}"
DELETE_ENABLED = os.getenv("DELETE_ENABLED") == "true"

INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}
IMAGE_TYPES = {
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
}


def az_json(*args):
    """Run Azure CLI and return its JSON response."""
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Azure CLI command failed")
    data = json.loads(result.stdout)
    return json.loads(data) if isinstance(data, str) else data


def image_references() -> set[str]:
    revisions = az_json(
        "containerapp",
        "revision",
        "list",
        "--name",
        APP_NAME,
        "--resource-group",
        RESOURCE_GROUP,
        "--all",
    )
    app = az_json(
        "containerapp",
        "show",
        "--name",
        APP_NAME,
        "--resource-group",
        RESOURCE_GROUP,
    )
    references = set()
    for resource in [app, *revisions]:
        template = resource["properties"]["template"]
        for key in ("containers", "initContainers"):
            for container in template.get(key) or []:
                references.add(container["image"])
    if not references:
        raise RuntimeError("No container image references found")
    return references


def updated_at(manifest: dict) -> datetime:
    timestamp = manifest.get("lastUpdateTime") or manifest["timestamp"]
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def registry_state() -> tuple[dict, dict]:
    items = az_json(
        "acr",
        "manifest",
        "list-metadata",
        "--registry",
        ACR_NAME,
        "--name",
        REPOSITORY,
    )
    manifests = {item["digest"]: item for item in items}
    dependencies = {}
    for digest, manifest in manifests.items():
        media_type = manifest["mediaType"]
        if media_type not in INDEX_TYPES | IMAGE_TYPES:
            raise RuntimeError(f"Unsupported manifest type: {media_type}")
        if media_type not in INDEX_TYPES:
            continue
        raw = az_json(
            "acr",
            "manifest",
            "show",
            "--registry",
            ACR_NAME,
            "--name",
            f"{REPOSITORY}@{digest}",
            "--raw",
        )
        children = {item["digest"] for item in raw["manifests"]}
        if not children or not children.issubset(manifests):
            raise RuntimeError(f"Incomplete OCI index: {digest}")
        dependencies[digest] = children
    return manifests, dependencies


def revision_digests(manifests: dict) -> set[str]:
    tags = {
        tag: digest for digest, manifest in manifests.items() for tag in manifest.get("tags") or []
    }
    protected = set()
    for image in image_references():
        if image.startswith(f"{PREFIX}@") or image.startswith(f"{PREFIX}:"):
            if "@" in image:
                digest = image.rsplit("@", 1)[1]
            else:
                digest = tags.get(image[len(PREFIX) + 1 :])
            if digest not in manifests:
                raise RuntimeError(f"Revision image not found in ACR: {image}")
            protected.add(digest)
    if not protected:
        raise RuntimeError("No revision images matched the target repository")
    return protected


def dependent_digests(dependencies: dict) -> set[str]:
    return {child for children in dependencies.values() for child in children}


def descendants(digest: str, dependencies: dict) -> set[str]:
    found = set()
    pending = list(dependencies.get(digest, set()))
    while pending:
        child = pending.pop()
        if child not in found:
            found.add(child)
            pending.extend(dependencies.get(child, set()))
    return found


def delete_manifest(digest: str) -> None:
    subprocess.run(
        [
            "az",
            "acr",
            "repository",
            "delete",
            "--name",
            ACR_NAME,
            "--image",
            f"{REPOSITORY}@{digest}",
            "--yes",
            "--only-show-errors",
        ],
        check=True,
    )


def plan_images(
    manifests: dict, dependencies: dict, revisions: set[str], cutoff: datetime
) -> list[str]:
    tagged = sorted(
        (item for item in manifests.values() if item.get("tags")),
        key=updated_at,
        reverse=True,
    )
    recent = {item["digest"] for item in tagged[:KEEP_IMAGES]}
    children = dependent_digests(dependencies)
    candidates = []
    for manifest in tagged:
        digest = manifest["digest"]
        tags = manifest["tags"]
        if digest in revisions or descendants(digest, dependencies) & revisions:
            reason = "referenced by a revision"
        elif digest in recent:
            reason = "recent image"
        elif digest in children:
            reason = "dependent manifest"
        elif updated_at(manifest) >= cutoff:
            reason = "younger than retention period"
        elif not all(re.fullmatch(r"[0-9a-f]{40}", tag) for tag in tags):
            reason = "custom tag"
        else:
            candidates.append(digest)
            continue
        print(f"KEEP: {tags} - {reason}")
    return candidates


def main() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    manifests, dependencies = registry_state()
    revisions = revision_digests(manifests)
    print(f"Repository: {REPOSITORY}")
    print(f"Deletion enabled: {DELETE_ENABLED}")
    print(f"Minimum retained images: {KEEP_IMAGES}")
    print(f"Retention period: {RETENTION_DAYS} days")
    print(f"Images found: {sum(bool(m.get('tags')) for m in manifests.values())}")
    print(f"OCI/Docker indexes: {len(dependencies)}")
    print(f"Dependent manifests: {len(dependent_digests(dependencies))}")
    print(f"Revision image digests: {len(revisions)}")

    candidates = plan_images(manifests, dependencies, revisions, cutoff)
    deleted = 0
    for digest in candidates:
        # CI and cleanup share a concurrency group. Recheck references anyway.
        revisions = revision_digests(manifests)
        if digest in revisions or descendants(digest, dependencies) & revisions:
            print(f"KEEP: {digest} - revision reference changed")
            continue
        if DELETE_ENABLED:
            delete_manifest(digest)
            deleted += 1
            print(f"DELETED: {manifests[digest]['tags']}")
        else:
            print(f"DRY RUN: would delete {manifests[digest]['tags']}")

    print(f"Candidates: {len(candidates)}")
    print(f"Deleted: {deleted}")
    print("Cleanup completed successfully.")


if __name__ == "__main__":
    main()
