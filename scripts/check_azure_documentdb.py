import asyncio
import os
import unicodedata
from urllib.parse import urlsplit

from pymongo import AsyncMongoClient, MongoClient
from pymongo.errors import PyMongoError

DATABASE_NAME = "steam_doma"


def get_credentials() -> tuple[str, str, str]:
    """Read credentials from environment variables."""

    uri = os.environ.get("AZURE_DOCUMENTDB_URI", "")
    username = os.environ.get("AZURE_DOCUMENTDB_USERNAME", "")
    password = os.environ.get("AZURE_DOCUMENTDB_PASSWORD", "")

    if not all((uri, username, password)):
        raise ValueError("Missing Azure DocumentDB environment variables")

    if not uri.startswith("mongodb+srv://"):
        raise ValueError("AZURE_DOCUMENTDB_URI must start with mongodb+srv://")

    if "@" in urlsplit(uri).netloc:
        raise ValueError(
            "Remove username and password from the URI. Use the separate environment variables."
        )

    # Detect invisible control and formatting characters.
    invalid_characters = [char for char in password if unicodedata.category(char) in {"Cc", "Cf"}]

    if invalid_characters:
        raise ValueError("Password contains invisible control or formatting characters.")

    return uri, username, password


def check_sync(
    uri: str,
    username: str,
    password: str,
) -> None:
    print("[1/2] Testing MongoClient...")

    client = MongoClient(
        uri,
        username=username,
        password=password,
        serverSelectionTimeoutMS=10000,
    )

    try:
        result = client.admin.command("ping")
        print(f"MongoClient ping: {result}")
    finally:
        client.close()


async def check_async(
    uri: str,
    username: str,
    password: str,
) -> None:
    print("[2/2] Testing AsyncMongoClient...")

    client = AsyncMongoClient(
        uri,
        username=username,
        password=password,
        serverSelectionTimeoutMS=10000,
    )

    try:
        result = await client.admin.command("ping")
        print(f"AsyncMongoClient ping: {result}")

        collections = await client[DATABASE_NAME].list_collection_names()

        print(f"Database: {DATABASE_NAME}")
        print(f"Collections: {collections}")
    finally:
        await client.close()


def main() -> None:
    print("Azure DocumentDB diagnostic")
    print("Reading credentials from environment...")

    try:
        uri, username, password = get_credentials()

        print("Credentials loaded successfully.")
        print(f"Password length: {len(password)}")

        check_sync(uri, username, password)

        asyncio.run(check_async(uri, username, password))

        print("All checks passed!")

    except (PyMongoError, ValueError, RuntimeError) as error:
        print(f"Connection failed: {type(error).__name__}")

        code = getattr(error, "code", None)
        if code is not None:
            print(f"MongoDB error code: {code}")

        if isinstance(error, ValueError):
            print(str(error))

        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
