from datetime import UTC, datetime

import strawberry
from bson import ObjectId

from steam_doma.modules.games.graphql_types import (
    GameCard,
    game_to_card,
)


def make_game_document() -> dict:
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
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
        "platforms": {
            "windows": True,
            "mac": False,
            "linux": True,
        },
        "release_date_utc": datetime(2024, 4, 10, tzinfo=UTC),
        "steam_data": {
            "header_image": "https://example.com/game.jpg",
            "recommendations": {
                "total": 150,
            },
        },
    }


def test_game_to_card() -> None:
    card = game_to_card(make_game_document())

    assert str(card.id) == "507f1f77bcf86cd799439011"
    assert card.steam_appid == 123456
    assert card.name == "Example Game"
    assert card.is_free is False

    assert card.price_minor == 999
    assert card.original_currency == "USD"
    assert card.discount_percent == 20

    assert [genre.name for genre in card.genres] == [
        "Action",
        "RPG",
    ]

    assert card.platforms.windows is True
    assert card.platforms.mac is False
    assert card.platforms.linux is True

    assert card.release_date.isoformat() == "2024-04-10"
    assert card.recommendations_total == 150


def test_free_game_without_price() -> None:
    document = make_game_document()
    document["is_free"] = True
    document["price"] = None

    card = game_to_card(document)

    assert card.is_free is True
    assert card.price_minor == 0
    assert card.discount_percent is None


def test_game_with_unknown_data() -> None:
    document = make_game_document()
    document["is_free"] = None
    document["price"] = None
    document["genres"] = []
    document["platforms"] = {}
    document["release_date_utc"] = None
    document["steam_data"] = {}

    card = game_to_card(document)

    assert card.is_free is None
    assert card.price_minor is None
    assert card.original_currency is None
    assert card.discount_percent is None

    assert card.genres == []
    assert card.platforms.windows is False
    assert card.platforms.mac is False
    assert card.platforms.linux is False

    assert card.release_date is None
    assert card.recommendations_total is None
    assert card.header_image is None


def test_graphql_serialization() -> None:
    @strawberry.type
    class Query:
        @strawberry.field
        def game(self) -> GameCard:
            return game_to_card(make_game_document())

    schema = strawberry.Schema(query=Query)

    result = schema.execute_sync(
        """
        query {
          game {
            id
            steamAppid
            name
            priceMinor
            originalCurrency
            discountPercent
            genres {
              id
              name
            }
            platforms {
              windows
              mac
              linux
            }
            releaseDate
            recommendationsTotal
          }
        }
        """
    )

    assert result.errors is None

    assert result.data is not None
    game = result.data["game"]

    assert game["id"] == "507f1f77bcf86cd799439011"
    assert game["steamAppid"] == 123456
    assert game["priceMinor"] == 999
    assert game["discountPercent"] == 20
    assert game["releaseDate"] == "2024-04-10"
    assert game["recommendationsTotal"] == 150

    assert game["genres"] == [
        {"id": "1", "name": "Action"},
        {"id": "3", "name": "RPG"},
    ]
