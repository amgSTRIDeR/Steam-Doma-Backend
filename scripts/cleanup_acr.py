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

DELETE_ENABLED = os.getenv("DELETE_ENABLED") == "true"


def az_json(*args):
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "json"],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def image_references() -> set[str]:
    """Collect images referenced by existing revisions."""
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


def main() -> None:
    references = image_references()

    manifests = az_json(
        "acr",
        "manifest",
        "list-metadata",
        "--registry",
        ACR_NAME,
        "--name",
        REPOSITORY,
    )

    manifests.sort(key=updated_at, reverse=True)

    # Avoid deleting dependencies of multi-platform images.
    for manifest in manifests:
        media_type = manifest.get("mediaType", "")

        if (
            "manifest.list" in media_type
            or "image.index" in media_type
            or manifest.get("references")
        ):
            raise RuntimeError("Multi-platform images require separate cleanup rules")

    prefix = f"{ACR_LOGIN_SERVER}/{REPOSITORY}"

    tagged = [manifest for manifest in manifests if manifest.get("tags")]

    protected = {manifest["digest"] for manifest in tagged[:KEEP_IMAGES]}

    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)

    print(f"Repository: {REPOSITORY}")
    print(f"Deletion enabled: {DELETE_ENABLED}")
    print(f"Images found: {len(tagged)}")

    deleted = 0
    candidates = 0

    for manifest in tagged:
        digest = manifest["digest"]
        tags = manifest["tags"]

        image_refs = {f"{prefix}:{tag}" for tag in tags}
        image_refs.add(f"{prefix}@{digest}")
        image_refs.update(f"{prefix}:{tag}@{digest}" for tag in tags)

        if digest in protected:
            print(f"KEEP: {tags} — recent image")
            continue

        if updated_at(manifest) >= cutoff:
            print(f"KEEP: {tags} — younger than 7 days")
            continue

        if not all(re.fullmatch(r"[0-9a-f]{40}", tag) for tag in tags):
            print(f"KEEP: {tags} — custom tag")
            continue

        # Refresh revision references before each deletion.
        references = image_references()

        if references.intersection(image_refs):
            print(f"KEEP: {tags} — referenced by a revision")
            continue

        candidates += 1

        if not DELETE_ENABLED:
            print(f"DRY RUN: would delete {tags}")
            continue

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

        deleted += 1
        print(f"DELETED: {tags}")

    print(f"Candidates: {candidates}")
    print(f"Deleted: {deleted}")


if __name__ == "__main__":
    main()
