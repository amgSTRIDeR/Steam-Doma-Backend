import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from steam_doma.modules.games.normalizer import normalize_game

SEED_ID = "steam-games-initial-v1"
BATCH_SIZE = 200


def prepare_documents(path: Path) -> tuple[list[dict], int]:
    """Read, validate and normalize the Steam dataset."""
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")

    records = payload.get("games")

    if not isinstance(records, list) or not records:
        raise ValueError("Expected a non-empty games array")

    documents = []
    seen_appids = set()
    skipped = 0

    for record in records:
        document = normalize_game(record)

        if document is None:
            skipped += 1
            continue

        appid = document["steam_appid"]

        if appid in seen_appids:
            skipped += 1
            continue

        seen_appids.add(appid)
        documents.append(document)

    if not documents:
        raise ValueError("No valid games found in dataset")

    return documents, skipped


async def seed_games(path: Path) -> None:
    """Seed an empty local or Azure database once."""
    documents, skipped = prepare_documents(path)

    database_provider = os.getenv("DATABASE_PROVIDER", "local").strip().lower()

    database_name = os.environ["MONGO_DB_NAME"]

    if database_provider == "azure":
        client = AsyncMongoClient(
            os.environ["AZURE_DOCUMENTDB_URI"],
            username=os.environ["AZURE_DOCUMENTDB_USERNAME"],
            password=os.environ["AZURE_DOCUMENTDB_PASSWORD"],
            serverSelectionTimeoutMS=10000,
        )
    elif database_provider == "local":
        client = AsyncMongoClient(
            os.environ["MONGO_URI"],
            serverSelectionTimeoutMS=5000,
        )
    else:
        raise ValueError(f"Unsupported database provider: {database_provider}")

    try:
        await client.admin.command("ping")

        db = client[database_name]
        games = db["games"]
        history = db["seed_history"]

        print(f"Database provider: {database_provider}")
        print(f"Database name: {db.name}")
        print(f"Dataset: {path}")
        print(f"Prepared documents: {len(documents)}")
        print(f"Skipped documents: {skipped}")

        # Never seed a database that was seeded before.
        previous_seed = await history.find_one({"_id": SEED_ID})

        if previous_seed is not None:
            raise RuntimeError(
                f"Initial game seed has already been attempted. Status: {previous_seed['status']}"
            )

        # Protect databases populated without seed_history.
        if await games.count_documents({}) > 0:
            raise RuntimeError("Games collection is not empty. Initial seed cancelled.")

        await games.create_index(
            "steam_appid",
            unique=True,
            sparse=True,
        )

        # Reserve this seed ID before inserting any games.
        try:
            await history.insert_one(
                {
                    "_id": SEED_ID,
                    "status": "started",
                    "started_at": datetime.now(UTC),
                }
            )
        except DuplicateKeyError as error:
            raise RuntimeError("Another process has already started this seed.") from error

        inserted = 0

        print("Starting game import...")

        for offset in range(0, len(documents), BATCH_SIZE):
            batch = documents[offset : offset + BATCH_SIZE]

            result = await games.insert_many(batch)

            inserted += len(result.inserted_ids)

            print(
                f"Import progress: {inserted}/{len(documents)} ({inserted / len(documents):.1%})",
                flush=True,
            )

        result = await history.update_one(
            {"_id": SEED_ID, "status": "started"},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.now(UTC),
                    "inserted": inserted,
                    "skipped": skipped,
                }
            },
        )

        if result.matched_count != 1:
            raise RuntimeError("Could not mark the initial seed as completed.")

        print(f"Seed completed: {SEED_ID}")
        print(f"Inserted: {inserted}")
        print(f"Skipped: {skipped}")

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Steam games into an empty MongoDB database.")
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the Steam JSON dataset",
    )

    args = parser.parse_args()

    asyncio.run(seed_games(args.path))
