import asyncio
import os

from pymongo import ASCENDING, AsyncMongoClient


async def main() -> None:
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

        print("MongoDB connection successful")
        print(f"Database provider: {database_provider}")
        print(f"Database name: {database_name}")

        db = client[database_name]
        games = db["games"]

        index_name = await games.create_index(
            [("steam_appid", ASCENDING)],
            unique=True,
            sparse=True,
        )

        print(f"Index ensured: {index_name}")

        print("\nAvailable indexes:")

        async for index in await games.list_indexes():
            print(f"  {index['name']}: {dict(index['key'])}")

        print("\nIndex setup completed successfully.")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
