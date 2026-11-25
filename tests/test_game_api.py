import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient

from steam_doma.main import app

GAME_ID = "507f1f77bcf86cd799439011"


def make_test_games() -> list[dict]:
    return [
        {
            "_id": ObjectId(GAME_ID),
            "steam_appid": 100001,
            "name": "Alpha Free",
            "is_free": True,
            "price": None,
            "genres": [
                {"id": "1", "description": "Action"},
            ],
            "categories": [
                {"id": 2, "description": "Single-player"},
            ],
            "platforms": {
                "windows": True,
                "mac": False,
                "linux": False,
            },
            "release_date_utc": datetime(2024, 1, 10, tzinfo=UTC),
            "steam_data": {
                "short_description": "A free action game.",
                "release_date": {
                    "coming_soon": False,
                    "date": "Jan 10, 2024",
                },
                "screenshots": [
                    {
                        "id": 0,
                        "path_thumbnail": ("https://example.com/alpha-small.jpg"),
                        "path_full": ("https://example.com/alpha-full.jpg"),
                    },
                ],
            },
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "steam_appid": 100002,
            "name": "Beta Paid",
            "is_free": False,
            "price": {
                "final": 1500,
                "currency": "USD",
                "discount_percent": 25,
            },
            "genres": [
                {"id": "3", "description": "RPG"},
            ],
            "categories": [
                {"id": 2, "description": "Single-player"},
            ],
            "platforms": {
                "windows": False,
                "mac": False,
                "linux": True,
            },
            "release_date_utc": datetime(2022, 5, 15, tzinfo=UTC),
            "steam_data": {
                "short_description": "A paid role-playing game.",
                "recommendations": {"total": 120},
                "release_date": {
                    "coming_soon": False,
                    "date": "May 15, 2022",
                },
            },
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439013"),
            "steam_appid": 100003,
            "name": "Gamma Unknown",
            "is_free": False,
            "price": None,
            "genres": [
                {"id": "1", "description": "Action"},
            ],
            "categories": [],
            "platforms": {
                "windows": True,
                "mac": False,
                "linux": False,
            },
            "steam_data": {
                "release_date": {
                    "coming_soon": True,
                    "date": "Coming soon",
                },
            },
        },
    ]


@pytest.fixture
def api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    database_name = f"steam_doma_be002_http_test_{uuid4().hex}"

    monkeypatch.setenv(
        "MONGO_DB_NAME",
        database_name,
    )

    async def prepare_database() -> None:
        client = AsyncMongoClient(os.environ["MONGO_URI"])

        try:
            await client[database_name]["games"].insert_many(make_test_games())
        finally:
            await client.close()

    async def cleanup_database() -> None:
        client = AsyncMongoClient(os.environ["MONGO_URI"])

        try:
            await client.drop_database(database_name)
        finally:
            await client.close()

    try:
        asyncio.run(prepare_database())

        with TestClient(app) as client:
            yield client

    finally:
        asyncio.run(cleanup_database())


def test_health_and_ping(api_client: TestClient) -> None:
    health_response = api_client.get("/health")

    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
    }

    graphql_response = api_client.post(
        "/graphql",
        json={
            "query": "{ ping }",
        },
    )

    assert graphql_response.status_code == 200
    assert graphql_response.json() == {
        "data": {"ping": "pong"},
    }


def test_games_sorting_and_pagination(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                query {
                  games(
                    page: 1
                    pageSize: 2
                    sortBy: PRICE
                    sortDirection: ASC
                  ) {
                    totalCount
                    page
                    pageSize
                    items {
                      name
                      priceMinor
                    }
                  }
                }
            """,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "errors" not in body

    assert body["data"]["games"] == {
        "totalCount": 3,
        "page": 1,
        "pageSize": 2,
        "items": [
            {
                "name": "Alpha Free",
                "priceMinor": 0,
            },
            {
                "name": "Beta Paid",
                "priceMinor": 1500,
            },
        ],
    }

    second_page = api_client.post(
        "/graphql",
        json={
            "query": """
                query {
                  games(
                    page: 2
                    pageSize: 2
                    sortBy: PRICE
                    sortDirection: ASC
                  ) {
                    items {
                      name
                      priceMinor
                    }
                  }
                }
            """,
        },
    )

    assert second_page.status_code == 200

    assert second_page.json()["data"]["games"]["items"] == [
        {
            "name": "Gamma Unknown",
            "priceMinor": None,
        },
    ]


def test_games_filtering(api_client: TestClient) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                query Catalog($genres: [String!]) {
                  games(
                    filters: {
                      genreIds: $genres
                      platforms: ["windows"]
                    }
                    sortBy: NAME
                  ) {
                    totalCount
                    items {
                      name
                    }
                  }
                }
            """,
            "variables": {
                "genres": ["1"],
            },
        },
    )

    assert response.status_code == 200
    assert "errors" not in response.json()

    assert response.json()["data"]["games"] == {
        "totalCount": 2,
        "items": [
            {"name": "Alpha Free"},
            {"name": "Gamma Unknown"},
        ],
    }


def test_game_details_and_missing_game(
    api_client: TestClient,
) -> None:
    query = """
        query GetGame($id: ID!) {
          game(id: $id) {
            id
            name
            isFree
            priceMinor
            shortDescription
            releaseDate
            screenshots {
              fullUrl
            }
          }
        }
    """

    response = api_client.post(
        "/graphql",
        json={
            "query": query,
            "variables": {"id": GAME_ID},
        },
    )

    assert response.status_code == 200
    assert "errors" not in response.json()

    assert response.json()["data"]["game"] == {
        "id": GAME_ID,
        "name": "Alpha Free",
        "isFree": True,
        "priceMinor": 0,
        "shortDescription": "A free action game.",
        "releaseDate": "2024-01-10",
        "screenshots": [
            {"fullUrl": ("https://example.com/alpha-full.jpg")},
        ],
    }

    missing_response = api_client.post(
        "/graphql",
        json={
            "query": query,
            "variables": {
                "id": "507f1f77bcf86cd799439099",
            },
        },
    )

    assert missing_response.status_code == 200
    assert missing_response.json() == {
        "data": {"game": None},
    }


def test_catalog_filters(api_client: TestClient) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
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
        },
    )

    assert response.status_code == 200
    assert "errors" not in response.json()

    filters = response.json()["data"]["catalogFilters"]

    assert filters["genres"] == [
        {"id": "1", "name": "Action"},
        {"id": "3", "name": "RPG"},
    ]

    assert filters["categories"] == [
        {"id": 2, "name": "Single-player"},
    ]

    assert filters["platforms"] == [
        {"id": "windows", "name": "Windows"},
        {"id": "mac", "name": "macOS"},
        {"id": "linux", "name": "Linux"},
    ]


def test_invalid_page_returns_graphql_error(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                query {
                  games(page: 0) {
                    totalCount
                  }
                }
            """,
        },
    )

    body = response.json()

    assert body.get("errors") is not None
    assert body["errors"][0]["message"] == ("Page must be at least 1")
