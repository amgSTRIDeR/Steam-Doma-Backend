import asyncio
import os
from collections import Counter

from pymongo import AsyncMongoClient

from steam_doma.modules.games.release_dates import parse_release_date


async def main() -> None:
    client = AsyncMongoClient(os.environ["MONGO_URI"])

    try:
        db = client[os.environ["MONGO_DB_NAME"]]
        games = db["games"]

        total = 0
        parsed = 0
        coming_soon = 0
        unknown_dates = Counter()

        cursor = games.find(
            {},
            {"steam_data.release_date": 1},
        )

        async for game in cursor:
            total += 1

            steam_data = game.get("steam_data")

            release_date = steam_data.get("release_date") if isinstance(steam_data, dict) else None

            if isinstance(release_date, dict) and release_date.get("coming_soon") is True:
                coming_soon += 1
                continue

            parsed_date = parse_release_date(release_date)

            if parsed_date is not None:
                parsed += 1
            else:
                raw_date = release_date.get("date") if isinstance(release_date, dict) else None

                unknown_dates[str(raw_date)] += 1

        print(f"Total games: {total}")
        print(f"Coming soon: {coming_soon}")
        print(f"Parsed release dates: {parsed}")
        print(f"Unparsed non-coming-soon dates: {sum(unknown_dates.values())}")

        print("\nMost common unparsed values:")

        for value, count in unknown_dates.most_common(15):
            print(f"{value!r}: {count}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
