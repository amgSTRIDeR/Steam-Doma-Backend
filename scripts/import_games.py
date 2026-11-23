import asyncio
import json
import os
import sys
from pathlib import Path

from pymongo import TEXT, AsyncMongoClient, UpdateOne

from steam_doma.modules.games.normalizer import normalize_game

BATCH_SIZE = 200


async def import_games(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")

    records = payload.get("games")
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a non-empty games array")

    async with AsyncMongoClient(os.environ["MONGO_URI"]) as client:
        db = client[os.environ["MONGO_DB_NAME"]]
        games = db["games"]

        await games.create_index("steam_appid", unique=True, sparse=True)
        await games.create_index("name")
        await games.create_index([("name", TEXT)])
        await games.create_index("genres.id")
        await games.create_index("categories.id")
        await games.create_index("price.final")

        inserted = 0
        existing = 0
        skipped = 0
        seen = set()
        operations = []

        async def save_batch() -> None:
            nonlocal inserted, existing

            if not operations:
                return

            result = await games.bulk_write(operations, ordered=False)
            inserted += result.upserted_count
            existing += result.matched_count
            operations.clear()

        for record in records:
            document = normalize_game(record)

            if document is None:
                skipped += 1
                continue

            appid = document["steam_appid"]

            if appid in seen:
                skipped += 1
                continue

            seen.add(appid)

            operations.append(
                UpdateOne(
                    {"steam_appid": appid},
                    {"$setOnInsert": document},
                    upsert=True,
                )
            )

            if len(operations) >= BATCH_SIZE:
                await save_batch()

        await save_batch()

        print(f"Inserted: {inserted}")
        print(f"Already existing: {existing}")
        print(f"Skipped: {skipped}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/import_games.py <json_path>")

    asyncio.run(import_games(Path(sys.argv[1])))
