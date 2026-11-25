import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

CATALOG_PROJECTION = {
    "steam_appid": 1,
    "source": 1,
    "name": 1,
    "is_free": 1,
    "price": 1,
    "genres": 1,
    "platforms": 1,
    "release_date_utc": 1,
    "steam_data.header_image": 1,
    "steam_data.recommendations.total": 1,
}

ALLOWED_PLATFORMS = {"windows", "mac", "linux"}


@dataclass(frozen=True)
class GameFilters:
    search: str | None = None
    genre_ids: tuple[str, ...] = ()
    category_ids: tuple[int, ...] = ()
    platforms: tuple[str, ...] = ()
    min_price_minor: int | None = None
    max_price_minor: int | None = None
    free_only: bool = False
    discounted_only: bool = False


class GameSortBy(StrEnum):
    NAME = "name"
    PRICE = "price"
    DISCOUNT = "discount"
    RECOMMENDATIONS = "recommendations"
    RELEASE_DATE = "release_date"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


def build_game_query(filters: GameFilters) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = []

    if filters.search:
        term = filters.search.strip()

        if len(term) > 100:
            raise ValueError("Search term is too long")

        if term:
            conditions.append(
                {
                    "name": {
                        "$regex": re.escape(term),
                        "$options": "i",
                    }
                }
            )

    if filters.genre_ids:
        conditions.append({"genres.id": {"$in": list(filters.genre_ids)}})

    if filters.category_ids:
        conditions.append({"categories.id": {"$in": list(filters.category_ids)}})

    if filters.platforms:
        if any(platform not in ALLOWED_PLATFORMS for platform in filters.platforms):
            raise ValueError("Unsupported platform")

        conditions.append(
            {"$or": [{f"platforms.{platform}": True} for platform in filters.platforms]}
        )

    minimum = filters.min_price_minor
    maximum = filters.max_price_minor

    for value in (minimum, maximum):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Price must be a non-negative integer")

    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Minimum price cannot exceed maximum price")

    if filters.free_only:
        conditions.append({"is_free": True})

    if filters.discounted_only:
        conditions.append({"price.discount_percent": {"$gt": 0}})

    if minimum is not None or maximum is not None:
        price_bounds: dict[str, int] = {}

        if minimum is not None:
            price_bounds["$gte"] = minimum

        if maximum is not None:
            price_bounds["$lte"] = maximum

        priced_game = {
            "is_free": {"$ne": True},
            "price.final": price_bounds,
        }

        if minimum is None or minimum == 0:
            conditions.append(
                {
                    "$or": [
                        {"is_free": True},
                        priced_game,
                    ]
                }
            )
        else:
            conditions.append(priced_game)

    if not conditions:
        return {}

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


def build_sort_stages(
    sort_by: GameSortBy,
    direction: SortDirection,
) -> list[dict[str, Any]]:
    if not isinstance(sort_by, GameSortBy):
        raise ValueError("Unsupported sort field")

    if not isinstance(direction, SortDirection):
        raise ValueError("Unsupported sort direction")

    order = 1 if direction == SortDirection.ASC else -1

    if sort_by == GameSortBy.NAME:
        return [
            {"$sort": {"name": order, "_id": 1}},
        ]

    if sort_by == GameSortBy.PRICE:
        sort_value = {
            "$cond": [
                {"$eq": ["$is_free", True]},
                0,
                {
                    "$cond": [
                        {"$isNumber": "$price.final"},
                        "$price.final",
                        None,
                    ]
                },
            ]
        }

    elif sort_by == GameSortBy.RELEASE_DATE:
        sort_value = {
            "$cond": [
                {
                    "$eq": [
                        {"$type": "$release_date_utc"},
                        "date",
                    ]
                },
                "$release_date_utc",
                None,
            ]
        }

    else:
        field = {
            GameSortBy.DISCOUNT: "$price.discount_percent",
            GameSortBy.RECOMMENDATIONS: ("$steam_data.recommendations.total"),
        }[sort_by]

        sort_value = {
            "$cond": [
                {"$isNumber": field},
                field,
                None,
            ]
        }

    return [
        {"$addFields": {"_sort_value": sort_value}},
        {
            "$addFields": {
                "_sort_missing": {
                    "$cond": [
                        {"$eq": ["$_sort_value", None]},
                        1,
                        0,
                    ]
                }
            }
        },
        {
            "$sort": {
                "_sort_missing": 1,
                "_sort_value": order,
                "name": 1,
                "_id": 1,
            }
        },
    ]


class GameRepository:
    def __init__(self, games: AsyncCollection) -> None:
        self._games = games

    async def get_by_id(
        self,
        game_id: str,
    ) -> dict[str, Any] | None:
        if not ObjectId.is_valid(game_id):
            return None

        return await self._games.find_one({"_id": ObjectId(game_id)})

    async def list_page(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        filters: GameFilters | None = None,
        sort_by: GameSortBy = GameSortBy.NAME,
        sort_direction: SortDirection = SortDirection.ASC,
    ) -> list[dict[str, Any]]:
        if type(page) is not int or page < 1:
            raise ValueError("Page must be at least 1")

        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100")

        query = build_game_query(filters or GameFilters())
        offset = (page - 1) * page_size

        pipeline = [
            {"$match": query},
            *build_sort_stages(sort_by, sort_direction),
            {"$skip": offset},
            {"$limit": page_size},
            {"$project": CATALOG_PROJECTION},
        ]

        cursor = await self._games.aggregate(pipeline)

        return await cursor.to_list()

    async def count_games(
        self,
        *,
        filters: GameFilters | None = None,
    ) -> int:
        query = build_game_query(filters or GameFilters())

        return await self._games.count_documents(query)

    async def get_filter_options(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        genre_pipeline = [
            {"$unwind": "$genres"},
            {
                "$match": {
                    "genres.id": {"$type": "string"},
                    "genres.description": {
                        "$type": "string",
                        "$ne": "",
                    },
                }
            },
            {
                "$group": {
                    "_id": "$genres.id",
                    "name": {"$first": "$genres.description"},
                }
            },
            {"$sort": {"name": 1, "_id": 1}},
        ]

        category_pipeline = [
            {"$unwind": "$categories"},
            {
                "$match": {
                    "categories.id": {"$type": ["int", "long"]},
                    "categories.description": {
                        "$type": "string",
                        "$ne": "",
                    },
                }
            },
            {
                "$group": {
                    "_id": "$categories.id",
                    "name": {"$first": "$categories.description"},
                }
            },
            {"$sort": {"name": 1, "_id": 1}},
        ]

        genre_cursor = await self._games.aggregate(genre_pipeline)
        genres = await genre_cursor.to_list()

        category_cursor = await self._games.aggregate(category_pipeline)
        categories = await category_cursor.to_list()

        return genres, categories
