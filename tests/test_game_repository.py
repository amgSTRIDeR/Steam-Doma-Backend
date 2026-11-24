import asyncio
import os
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient

from steam_doma.modules.games.repository import GameRepository


def test_game_repository() -> None:
    db_name = f"steam_doma_repository_test_{uuid4().hex}"

    async def scenario() -> None:
        client = AsyncMongoClient(os.environ["MONGO_URI"])

        try:
            games = client[db_name]["games"]

            result = await games.insert_many(
                [
                    {
                        "name": "Beta",
                        "steam_appid": 101,
                        "steam_data": {
                            "header_image": "beta.jpg",
                            "detailed_description": "Description",
                        },
                    },
                    {
                        "name": "Alpha",
                        "steam_appid": 102,
                        "steam_data": {
                            "header_image": "alpha.jpg",
                            "detailed_description": "Description",
                        },
                    },
                    {
                        "name": "Gamma",
                        "steam_appid": 103,
                    },
                ]
            )

            repository = GameRepository(games)

            game_id = str(result.inserted_ids[1])
            game = await repository.get_by_id(game_id)

            assert game is not None
            assert game["name"] == "Alpha"
            assert game["steam_data"]["detailed_description"] == "Description"

            first_page = await repository.list_page(
                page=1,
                page_size=2,
            )
            second_page = await repository.list_page(
                page=2,
                page_size=2,
            )

            assert [game["name"] for game in first_page] == [
                "Alpha",
                "Beta",
            ]
            assert [game["name"] for game in second_page] == [
                "Gamma",
            ]

            assert "detailed_description" not in first_page[0]["steam_data"]
            assert await repository.get_by_id("invalid-id") is None

            with pytest.raises(ValueError):
                await repository.list_page(page=0)

        finally:
            await client.drop_database(db_name)
            await client.close()

    asyncio.run(scenario())
