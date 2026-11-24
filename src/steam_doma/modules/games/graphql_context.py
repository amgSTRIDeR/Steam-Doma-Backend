import os

from fastapi import Request

from steam_doma.modules.games.repository import GameRepository


def get_graphql_context(request: Request) -> dict:
    client = request.app.state.mongo_client

    database_name = os.environ["MONGO_DB_NAME"]
    games_collection = client[database_name]["games"]

    repository = GameRepository(games_collection)

    return {
        "games_repository": repository,
    }
