import asyncio
import os
from datetime import UTC, datetime
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
def test_invalid_sort(
    sort_by: GameSortBy | str,
    direction: SortDirection | str,
) -> None:
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
                        "release_date_utc": datetime(2021, 7, 1, tzinfo=UTC),
                        "steam_data": {"recommendations": {"total": 5}},
                    },
                    {
                        "name": "Beta Cheap",
                        "is_free": False,
                        "price": {
                            "final": 500,
                            "discount_percent": 10,
                        },
                        "release_date_utc": datetime(2024, 4, 10, tzinfo=UTC),
                        "steam_data": {"recommendations": {"total": 100}},
                    },
                    {
                        "name": "Charlie Expensive",
                        "is_free": False,
                        "price": {
                            "final": 3000,
                            "discount_percent": 30,
                        },
                        "release_date_utc": datetime(2019, 1, 5, tzinfo=UTC),
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
                        "release_date_utc": datetime(2024, 4, 10, tzinfo=UTC),
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

            # 1. Price: ascending.
            # Free games have price 0.
            # Unknown prices must be last.

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

            # 2. Price: descending.
            # Unknown prices must still be last.

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

            # 3. Discount: descending.
            # Missing discounts must be last.

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

            # 4. Discount: ascending.

            assert await names(
                GameSortBy.DISCOUNT,
                SortDirection.ASC,
            ) == [
                "Echo Mid",
                "Beta Cheap",
                "Charlie Expensive",
                "Alpha Free",
                "Delta Unknown",
            ]

            # 5. Steam recommendations: descending.
            # Missing recommendations must be last.

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

            # 6. Steam recommendations: ascending.

            assert await names(
                GameSortBy.RECOMMENDATIONS,
                SortDirection.ASC,
            ) == [
                "Alpha Free",
                "Charlie Expensive",
                "Beta Cheap",
                "Delta Unknown",
                "Echo Mid",
            ]

            # 7. Name: ascending.

            assert await names(
                GameSortBy.NAME,
                SortDirection.ASC,
            ) == [
                "Alpha Free",
                "Beta Cheap",
                "Charlie Expensive",
                "Delta Unknown",
                "Echo Mid",
            ]

            # 8. Name: descending.

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

            # 9. Release date: oldest first.
            # Games with unknown release dates must be last.

            assert await names(
                GameSortBy.RELEASE_DATE,
                SortDirection.ASC,
            ) == [
                "Charlie Expensive",
                "Alpha Free",
                "Beta Cheap",
                "Echo Mid",
                "Delta Unknown",
            ]

            # 10. Release date: newest first.
            # Equal dates are ordered by name.

            assert await names(
                GameSortBy.RELEASE_DATE,
                SortDirection.DESC,
            ) == [
                "Beta Cheap",
                "Echo Mid",
                "Alpha Free",
                "Charlie Expensive",
                "Delta Unknown",
            ]

            # 11. Filters and sorting must work together.

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

            # 12. Pagination after sorting by price.

            price_page = await repository.list_page(
                page=2,
                page_size=2,
                sort_by=GameSortBy.PRICE,
                sort_direction=SortDirection.ASC,
            )

            assert [game["name"] for game in price_page] == [
                "Echo Mid",
                "Charlie Expensive",
            ]

            # 13. Pagination after sorting by release date.

            release_date_page = await repository.list_page(
                page=2,
                page_size=2,
                sort_by=GameSortBy.RELEASE_DATE,
                sort_direction=SortDirection.DESC,
            )

            assert [game["name"] for game in release_date_page] == [
                "Alpha Free",
                "Charlie Expensive",
            ]

            # 14. Internal sorting fields must not be
            # returned to API consumers.

            assert "_sort_value" not in price_page[0]
            assert "_sort_missing" not in price_page[0]

            assert "_sort_value" not in release_date_page[0]
            assert "_sort_missing" not in release_date_page[0]

        finally:
            await client.drop_database(db_name)
            await client.close()

    asyncio.run(scenario())
