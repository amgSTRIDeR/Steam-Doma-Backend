import os
from contextlib import asynccontextmanager

import strawberry
from fastapi import FastAPI, Request
from pymongo import AsyncMongoClient
from strawberry.fastapi import GraphQLRouter

from steam_doma.modules.games.graphql_catalog_filters import (
    CatalogFilterOptions,
    resolve_catalog_filters,
)
from steam_doma.modules.games.graphql_context import (
    get_graphql_context,
)
from steam_doma.modules.games.graphql_detail import GameDetail
from steam_doma.modules.games.graphql_queries import (
    resolve_game,
    resolve_games,
)
from steam_doma.modules.games.graphql_types import GamePage


@strawberry.type
class Query:
    @strawberry.field
    async def ping(self) -> str:
        return "pong"

    games: GamePage = strawberry.field(resolver=resolve_games)

    game: GameDetail | None = strawberry.field(resolver=resolve_game)

    catalog_filters: CatalogFilterOptions = strawberry.field(resolver=resolve_catalog_filters)


schema = strawberry.Schema(query=Query)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_uri = os.environ["MONGO_URI"]

    client = AsyncMongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        await client.admin.command("ping")

        app.state.mongo = client
        app.state.mongo_client = client

        yield
    finally:
        await client.close()


app = FastAPI(
    title="Steam Doma API",
    lifespan=lifespan,
)


@app.get("/health")
async def health(request: Request):
    await request.app.state.mongo.admin.command("ping")
    return {"status": "ok"}


app.include_router(
    GraphQLRouter(
        schema,
        context_getter=get_graphql_context,
    ),
    prefix="/graphql",
)
