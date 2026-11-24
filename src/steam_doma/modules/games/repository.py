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
    ) -> list[dict[str, Any]]:
        if page < 1:
            raise ValueError("Page must be at least 1")

        if not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100")

        offset = (page - 1) * page_size

        cursor = (
            self._games.find(
                {},
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
