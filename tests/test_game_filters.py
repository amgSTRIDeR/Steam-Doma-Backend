import asyncio
import os
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient

from steam_doma.modules.games.repository import (
    GameFilters,
    GameRepository,
    build_game_query,
)


@pytest.mark.parametrize(
    "filters",
    [
        GameFilters(min_price_minor=-1),
        GameFilters(min_price_minor=5000, max_price_minor=1000),
        GameFilters(platforms=("android",)),
    ],
)
def test_invalid_filters(filters: GameFilters) -> None:
    with pytest.raises(ValueError):
        build_game_query(filters)


def test_empty_filters() -> None:
    assert build_game_query(GameFilters()) == {}


def test_repository_filters() -> None:
    db_name = f"steam_doma_filters_test_{uuid4().hex}"

    async def scenario() -> None:
        client = AsyncMongoClient(os.environ["MONGO_URI"])

        try:
            games = client[db_name]["games"]

            await games.insert_many(
                [
                    {
                        "name": "Alpha C++",
                        "genres": [{"id": "1"}],
                        "categories": [{"id": 2}],
                        "platforms": {"windows": True},
                        "is_free": False,
                        "price": {
                            "final": 2500,
                            "discount_percent": 20,
                        },
                    },
                    {
                        "name": "Beta Free",
                        "genres": [{"id": "3"}],
                        "categories": [{"id": 2}],
                        "platforms": {"linux": True},
                        "is_free": True,
                        "price": None,
                    },
                    {
                        "name": "Gamma Unknown",
                        "genres": [{"id": "1"}],
                        "platforms": {"windows": True},
                        "is_free": False,
                        "price": None,
                    },
                    {
                        "name": "Delta Costly",
                        "genres": [{"id": "1"}],
                        "platforms": {"windows": True},
                        "is_free": False,
                        "price": {"final": 8000},
                    },
                    {
                        "name": "Echo Other",
                        "genres": [{"id": "1"}],
                        "platforms": {"mac": True},
                        "is_free": False,
                        "price": {"final": 1500},
                    },
                ]
            )

            repository = GameRepository(games)

            filters = GameFilters(
                search="C++",
                genre_ids=("1",),
                category_ids=(2,),
                platforms=("windows",),
                min_price_minor=1000,
                max_price_minor=3000,
                discounted_only=True,
            )

            results = await repository.list_page(filters=filters)

            assert [game["name"] for game in results] == ["Alpha C++"]
            assert await repository.count_games(filters=filters) == 1

            free_games = await repository.list_page(filters=GameFilters(max_price_minor=0))
            assert [game["name"] for game in free_games] == ["Beta Free"]

            platform_games = await repository.list_page(
                filters=GameFilters(
                    platforms=("windows", "mac"),
                    min_price_minor=1000,
                    max_price_minor=3000,
                )
            )

            assert [game["name"] for game in platform_games] == [
                "Alpha C++",
                "Echo Other",
            ]

            assert (
                await repository.count_games(
                    filters=GameFilters(
                        platforms=("windows", "mac"),
                        min_price_minor=1000,
                        max_price_minor=3000,
                    )
                )
                == 2
            )

            impossible = await repository.list_page(
                filters=GameFilters(
                    free_only=True,
                    min_price_minor=1000,
                )
            )
            assert impossible == []

        finally:
            await client.drop_database(db_name)
            await client.close()

    asyncio.run(scenario())
