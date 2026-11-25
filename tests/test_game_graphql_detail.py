import asyncio
from datetime import UTC, datetime
from typing import Any

import strawberry
from bson import ObjectId

from steam_doma.modules.games.graphql_detail import (
    GameDetail,
    game_to_detail,
)
from steam_doma.modules.games.graphql_queries import resolve_game

GAME_ID = "507f1f77bcf86cd799439011"


def make_game_document() -> dict[str, Any]:
    return {
        "_id": ObjectId(GAME_ID),
        "steam_appid": 123456,
        "name": "Example Game",
        "is_free": False,
        "price": {
            "final": 999,
            "currency": "USD",
            "discount_percent": 20,
        },
        "genres": [
            {"id": "1", "description": "Action"},
            {"id": "3", "description": "RPG"},
        ],
        "categories": [
            {"id": 2, "description": "Single-player"},
        ],
        "platforms": {
            "windows": True,
            "mac": False,
            "linux": True,
        },
        "release_date_utc": datetime(2024, 4, 10, tzinfo=UTC),
        "steam_data": {
            "short_description": "A test game.",
            "detailed_description": "<p>Full description</p>",
            "about_the_game": "<p>About the game</p>",
            "header_image": "https://example.com/header.jpg",
            "developers": ["Example Studio"],
            "publishers": ["Example Publisher"],
            "release_date": {
                "coming_soon": False,
                "date": "Apr 10, 2024",
            },
            "screenshots": [
                {
                    "id": 0,
                    "path_thumbnail": ("https://example.com/screenshot-small.jpg"),
                    "path_full": ("https://example.com/screenshot-full.jpg"),
                },
            ],
            "movies": [
                {
                    "id": 100,
                    "name": "Gameplay Trailer",
                    "thumbnail": ("https://example.com/trailer.jpg"),
                    "mp4": {
                        "max": "https://example.com/trailer.mp4",
                    },
                    "webm": {
                        "max": "https://example.com/trailer.webm",
                    },
                },
            ],
            "pc_requirements": {
                "minimum": "<p>Windows 10</p>",
                "recommended": "<p>Windows 11</p>",
            },
            "mac_requirements": [],
            "linux_requirements": {
                "minimum": "<p>Linux</p>",
            },
            "supported_languages": "English",
            "controller_support": "full",
            "required_age": 12,
            "website": "https://example.com",
            "recommendations": {
                "total": 150,
            },
            "metacritic": {
                "score": 88,
            },
        },
    }


class FakeGameRepository:
    def __init__(
        self,
        document: dict[str, Any] | None,
    ) -> None:
        self.document = document
        self.requested_id: str | None = None

    async def get_by_id(
        self,
        game_id: str,
    ) -> dict[str, Any] | None:
        self.requested_id = game_id

        if self.document is None:
            return None

        if str(self.document["_id"]) != game_id:
            return None

        return self.document


@strawberry.type
class Query:
    game: GameDetail | None = strawberry.field(resolver=resolve_game)


schema = strawberry.Schema(query=Query)


def test_game_to_detail() -> None:
    game = game_to_detail(make_game_document())

    assert str(game.id) == GAME_ID
    assert game.steam_appid == 123456
    assert game.name == "Example Game"

    assert game.price_minor == 999
    assert game.discount_percent == 20

    assert game.short_description == "A test game."
    assert game.detailed_description == "<p>Full description</p>"

    assert game.developers == ["Example Studio"]
    assert game.publishers == ["Example Publisher"]

    assert [genre.name for genre in game.genres] == [
        "Action",
        "RPG",
    ]

    assert [category.name for category in game.categories] == [
        "Single-player",
    ]

    assert len(game.screenshots) == 1
    assert game.screenshots[0].id == 0
    assert game.screenshots[0].full_url == ("https://example.com/screenshot-full.jpg")

    assert len(game.trailers) == 1
    assert game.trailers[0].mp4_url == ("https://example.com/trailer.mp4")

    assert game.pc_requirements is not None
    assert game.pc_requirements.minimum == "<p>Windows 10</p>"

    assert game.mac_requirements is None

    assert game.linux_requirements is not None
    assert game.linux_requirements.minimum == "<p>Linux</p>"

    assert game.release_date is not None
    assert game.release_date.isoformat() == "2024-04-10"
    assert game.release_date_text == "Apr 10, 2024"
    assert game.coming_soon is False

    assert game.recommendations_total == 150
    assert game.metacritic_score == 88


def test_game_with_missing_optional_data() -> None:
    document = {
        "_id": ObjectId(GAME_ID),
        "steam_appid": 123456,
        "name": "Incomplete Game",
        "is_free": True,
        "price": None,
        "steam_data": {},
    }

    game = game_to_detail(document)

    assert game.price_minor == 0
    assert game.genres == []
    assert game.categories == []
    assert game.screenshots == []
    assert game.trailers == []

    assert game.release_date is None
    assert game.release_date_text is None
    assert game.coming_soon is None

    assert game.short_description is None
    assert game.pc_requirements is None
    assert game.metacritic_score is None


def test_graphql_game_query() -> None:
    repository = FakeGameRepository(make_game_document())

    result = asyncio.run(
        schema.execute(
            """
            query GetGame($id: ID!) {
              game(id: $id) {
                id
                steamAppid
                name
                priceMinor
                releaseDate
                releaseDateText
                comingSoon
                developers
                metacriticScore
                screenshots {
                  id
                  thumbnailUrl
                  fullUrl
                }
                trailers {
                  name
                  mp4Url
                  webmUrl
                }
                pcRequirements {
                  minimum
                  recommended
                }
              }
            }
            """,
            variable_values={"id": GAME_ID},
            context_value={
                "games_repository": repository,
            },
        )
    )

    assert result.errors is None
    assert result.data is not None

    game = result.data["game"]

    assert game["id"] == GAME_ID
    assert game["steamAppid"] == 123456
    assert game["name"] == "Example Game"
    assert game["priceMinor"] == 999
    assert game["releaseDate"] == "2024-04-10"
    assert game["releaseDateText"] == "Apr 10, 2024"
    assert game["comingSoon"] is False
    assert game["developers"] == ["Example Studio"]
    assert game["metacriticScore"] == 88

    assert game["screenshots"] == [
        {
            "id": 0,
            "thumbnailUrl": ("https://example.com/screenshot-small.jpg"),
            "fullUrl": ("https://example.com/screenshot-full.jpg"),
        }
    ]

    assert game["trailers"] == [
        {
            "name": "Gameplay Trailer",
            "mp4Url": "https://example.com/trailer.mp4",
            "webmUrl": "https://example.com/trailer.webm",
        }
    ]

    assert game["pcRequirements"] == {
        "minimum": "<p>Windows 10</p>",
        "recommended": "<p>Windows 11</p>",
    }

    assert repository.requested_id == GAME_ID


def test_graphql_game_not_found() -> None:
    repository = FakeGameRepository(None)

    result = asyncio.run(
        schema.execute(
            """
            query {
              game(id: "507f1f77bcf86cd799439011") {
                id
                name
              }
            }
            """,
            context_value={
                "games_repository": repository,
            },
        )
    )

    assert result.errors is None
    assert result.data == {"game": None}
    assert repository.requested_id == GAME_ID
