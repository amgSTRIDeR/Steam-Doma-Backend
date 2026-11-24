import asyncio
import os
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient

from steam_doma.modules.games.repository import (
    GameFilters,
    GameRepository,
    GameSortBy,
    SortDirection,
    build_sort_stages,
)


@pytest.mark.parametrize(
    ("sort_by", "direction"),
    [
        ("rating", SortDirection.ASC),
        (GameSortBy.PRICE, "up"),
    ],
)
def test_invalid_sort(sort_by: str, direction: str) -> None:
    with pytest.raises(ValueError):
        build_sort_stages(sort_by, direction)


def test_repository_sorting() -> None:
    db_name = f"steam_doma_sort_test_{uuid4().hex}"

    async def scenario() -> None:
        client = AsyncMongoClient(os.environ["MONGO_URI"])

        try:
            games = client[db_name]["games"]

            await games.insert_many(
                [
                    {
                        "name": "Alpha Free",
                        "is_free": True,
                        "price": None,
                        "steam_data": {"recommendations": {"total": 5}},
                    },
                    {
                        "name": "Beta Cheap",
                        "is_free": False,
                        "price": {
                            "final": 500,
                            "discount_percent": 10,
                        },
                        "steam_data": {"recommendations": {"total": 100}},
                    },
                    {
                        "name": "Charlie Expensive",
                        "is_free": False,
                        "price": {
                            "final": 3000,
                            "discount_percent": 30,
                        },
                        "steam_data": {"recommendations": {"total": 20}},
                    },
                    {
                        "name": "Delta Unknown",
                        "is_free": False,
                        "price": None,
                        "steam_data": {},
                    },
                    {
                        "name": "Echo Mid",
                        "is_free": False,
                        "price": {
                            "final": 1500,
                            "discount_percent": 0,
                        },
                        "steam_data": {},
                    },
                ]
            )

            repository = GameRepository(games)

            async def names(
                sort_by: GameSortBy,
                direction: SortDirection,
            ) -> list[str]:
                result = await repository.list_page(
                    sort_by=sort_by,
                    sort_direction=direction,
                )
                return [game["name"] for game in result]

            assert await names(
                GameSortBy.PRICE,
                SortDirection.ASC,
            ) == [
                "Alpha Free",
                "Beta Cheap",
                "Echo Mid",
                "Charlie Expensive",
                "Delta Unknown",
            ]

            assert await names(
                GameSortBy.PRICE,
                SortDirection.DESC,
            ) == [
                "Charlie Expensive",
                "Echo Mid",
                "Beta Cheap",
                "Alpha Free",
                "Delta Unknown",
            ]

            assert await names(
                GameSortBy.DISCOUNT,
                SortDirection.DESC,
            ) == [
                "Charlie Expensive",
                "Beta Cheap",
                "Echo Mid",
                "Alpha Free",
                "Delta Unknown",
            ]

            assert await names(
                GameSortBy.RECOMMENDATIONS,
                SortDirection.DESC,
            ) == [
                "Beta Cheap",
                "Charlie Expensive",
                "Alpha Free",
                "Delta Unknown",
                "Echo Mid",
            ]

            assert await names(
                GameSortBy.NAME,
                SortDirection.DESC,
            ) == [
                "Echo Mid",
                "Delta Unknown",
                "Charlie Expensive",
                "Beta Cheap",
                "Alpha Free",
            ]

            filtered = await repository.list_page(
                filters=GameFilters(
                    min_price_minor=1000,
                    max_price_minor=3500,
                ),
                sort_by=GameSortBy.PRICE,
                sort_direction=SortDirection.DESC,
            )

            assert [game["name"] for game in filtered] == [
                "Charlie Expensive",
                "Echo Mid",
            ]

            page = await repository.list_page(
                page=2,
                page_size=2,
                sort_by=GameSortBy.PRICE,
                sort_direction=SortDirection.ASC,
            )

            assert [game["name"] for game in page] == [
                "Echo Mid",
                "Charlie Expensive",
            ]

            assert "_sort_value" not in page[0]
            assert "_sort_missing" not in page[0]

        finally:
            await client.drop_database(db_name)
            await client.close()

    asyncio.run(scenario())
