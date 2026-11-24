import argparse
import asyncio
import os

from pymongo import AsyncMongoClient, UpdateOne

from steam_doma.modules.games.release_dates import parse_release_date

BATCH_SIZE = 200


async def backfill_release_dates(apply: bool) -> None:
    database_name = os.environ["MONGO_DB_NAME"]

    client = AsyncMongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
    )

    try:
        games = client[database_name]["games"]

        cursor = games.find(
            {
                "source": "steam",
                "release_date_utc": {"$exists": False},
            },
            {"steam_data.release_date": 1},
        )

        operations = []
        skipped = 0

        async for game in cursor:
            steam_data = game.get("steam_data", {})
            release_date = steam_data.get("release_date")

            parsed_date = parse_release_date(release_date)

            if parsed_date is None:
                skipped += 1
                continue

            operations.append(
                UpdateOne(
                    {
                        "_id": game["_id"],
                        "release_date_utc": {"$exists": False},
                    },
                    {"$set": {"release_date_utc": parsed_date}},
                )
            )

        print(f"Database: {database_name}")
        print(f"Documents to update: {len(operations)}")
        print(f"Documents without confirmed date: {skipped}")

        if not apply:
            print("Dry run: no changes made")
            return

        updated = 0

        for offset in range(0, len(operations), BATCH_SIZE):
            batch = operations[offset : offset + BATCH_SIZE]

            result = await games.bulk_write(
                batch,
                ordered=False,
            )

            updated += result.modified_count

        print(f"Updated: {updated}")

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    asyncio.run(backfill_release_dates(apply=args.apply))
