import asyncio
import os

from pymongo import ASCENDING, AsyncMongoClient


async def main() -> None:
    mongo_uri = os.environ["MONGO_URI"]
    database_name = os.environ["MONGO_DB_NAME"]

    client = AsyncMongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        await client.admin.command("ping")
        print("MongoDB connection successful")

        db = client[database_name]
        games = db["games"]

        index_name = await games.create_index(
            [("steam_appid", ASCENDING)],
            unique=True,
            sparse=True,
        )

        print(f"Index created: {index_name}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
