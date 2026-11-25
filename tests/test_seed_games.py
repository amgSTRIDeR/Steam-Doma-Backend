import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient

from scripts.seed_games import prepare_documents, seed_games


def make_record(appid: int, game_type: str = "game") -> dict:
    return {
        "appid": appid,
        "app_details": {
            "success": True,
            "data": {
                "steam_appid": appid,
                "type": game_type,
                "name": f"Test Game {appid}",
                "is_free": False,
            },
        },
    }


def test_prepare_documents(tmp_path: Path) -> None:
    path = tmp_path / "games.json"

    records = [
        make_record(100),
        make_record(100),
        make_record(200, "demo"),
    ]

    path.write_text(
        json.dumps({"games": records}),
        encoding="utf-8",
    )

    documents, skipped = prepare_documents(path)

    assert len(documents) == 1
    assert documents[0]["steam_appid"] == 100
    assert skipped == 2


def test_seed_does_not_restore_deleted_game(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_name = f"steam_doma_seed_test_{uuid4().hex}"

    monkeypatch.setenv("MONGO_DB_NAME", db_name)

    path = tmp_path / "games.json"
    path.write_text(
        json.dumps({"games": [make_record(100)]}),
        encoding="utf-8",
    )

    async def scenario() -> None:
        client = AsyncMongoClient(os.environ["MONGO_URI"])

        try:
            await seed_games(path)

            db = client[db_name]
            games = db["games"]
            history = db["seed_history"]

            assert await games.count_documents({}) == 1

            seed = await history.find_one({"_id": "steam-games-initial-v1"})
            assert seed is not None
            assert seed["status"] == "completed"

            await games.delete_one({"steam_appid": 100})

            assert await games.count_documents({}) == 0

            with pytest.raises(
                RuntimeError,
                match="already been attempted",
            ):
                await seed_games(path)

            assert await games.count_documents({}) == 0

        finally:
            await client.drop_database(db_name)
            await client.close()

    asyncio.run(scenario())
