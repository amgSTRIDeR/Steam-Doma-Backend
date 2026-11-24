import re
from dataclasses import dataclass
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.asynchronous.collection import AsyncCollection

CATALOG_PROJECTION = {
    "steam_appid": 1,
    "source": 1,
    "name": 1,
    "is_free": 1,
    "price": 1,
    "genres": 1,
    "platforms": 1,
    "steam_data.header_image": 1,
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


def build_game_query(filters: GameFilters) -> dict[str, Any]:
    """Build a MongoDB query from catalog filters."""
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
        if any(p not in ALLOWED_PLATFORMS for p in filters.platforms):
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


class GameRepository:
    def __init__(self, games: AsyncCollection) -> None:
        self._games = games

    async def get_by_id(self, game_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(game_id):
            return None

        return await self._games.find_one({"_id": ObjectId(game_id)})

    async def list_page(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        filters: GameFilters | None = None,
    ) -> list[dict[str, Any]]:
        if type(page) is not int or page < 1:
            raise ValueError("Page must be at least 1")

        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100")

        query = build_game_query(filters or GameFilters())
        offset = (page - 1) * page_size

        cursor = (
            self._games.find(
                query,
                projection=CATALOG_PROJECTION,
            )
            .sort(
                [
                    ("name", ASCENDING),
                    ("_id", ASCENDING),
                ]
            )
            .skip(offset)
            .limit(page_size)
        )

        return await cursor.to_list()

    async def count_games(
        self,
        *,
        filters: GameFilters | None = None,
    ) -> int:
        query = build_game_query(filters or GameFilters())

        return await self._games.count_documents(query)
