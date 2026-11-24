import asyncio
import os
from typing import Any
from uuid import uuid4

import strawberry
from pymongo import AsyncMongoClient

from steam_doma.modules.games.graphql_catalog_filters import (
    CatalogFilterOptions,
    resolve_catalog_filters,
)
from steam_doma.modules.games.repository import GameRepository


@strawberry.type
class Query:
    catalog_filters: CatalogFilterOptions = strawberry.field(resolver=resolve_catalog_filters)


schema = strawberry.Schema(query=Query)


async def run_catalog_filters_query(
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    database_name = f"steam_doma_filter_options_test_{uuid4().hex}"

    client = AsyncMongoClient(os.environ["MONGO_URI"])

    try:
        collection = client[database_name]["games"]

        if documents:
            await collection.insert_many(documents)

        repository = GameRepository(collection)

        result = await schema.execute(
            """
            query {
              catalogFilters {
                genres {
                  id
                  name
                }
                categories {
                  id
                  name
                }
                platforms {
                  id
                  name
                }
              }
            }
            """,
            context_value={
                "games_repository": repository,
            },
        )

        assert result.errors is None
        assert result.data is not None

        return result.data["catalogFilters"]

    finally:
        await client.drop_database(database_name)
        await client.close()


def test_catalog_filter_options() -> None:
    documents = [
        {
            "name": "Alpha Game",
            "genres": [
                {"id": "3", "description": "RPG"},
                {"id": "1", "description": "Action"},
            ],
            "categories": [
                {"id": 2, "description": "Single-player"},
            ],
        },
        {
            "name": "Beta Game",
            "genres": [
                {"id": "3", "description": "RPG"},
            ],
            "categories": [
                {"id": 28, "description": "Full controller support"},
                {"id": 2, "description": "Single-player"},
            ],
        },
        {
            "name": "Gamma Game",
            "genres": [
                {"id": 42, "description": "Incorrect genre ID"},
                {"id": "5", "description": ""},
            ],
            "categories": [],
        },
    ]

    result = asyncio.run(run_catalog_filters_query(documents))

    assert result["genres"] == [
        {"id": "1", "name": "Action"},
        {"id": "3", "name": "RPG"},
    ]

    assert result["categories"] == [
        {"id": 28, "name": "Full controller support"},
        {"id": 2, "name": "Single-player"},
    ]

    assert result["platforms"] == [
        {"id": "windows", "name": "Windows"},
        {"id": "mac", "name": "macOS"},
        {"id": "linux", "name": "Linux"},
    ]


def test_empty_catalog_filter_options() -> None:
    result = asyncio.run(run_catalog_filters_query([]))

    assert result["genres"] == []
    assert result["categories"] == []

    assert result["platforms"] == [
        {"id": "windows", "name": "Windows"},
        {"id": "mac", "name": "macOS"},
        {"id": "linux", "name": "Linux"},
    ]
