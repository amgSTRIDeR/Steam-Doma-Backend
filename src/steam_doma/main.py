import os
from contextlib import asynccontextmanager

import strawberry
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def parse_cors_origins(value: str) -> list[str]:
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


CORS_ORIGINS = parse_cors_origins(os.getenv("CORS_ORIGINS") or DEFAULT_CORS_ORIGINS)


@strawberry.type
class Query:
    @strawberry.field
    async def ping(self) -> str:
        return "pong"

    games: GamePage = strawberry.field(resolver=resolve_games)

    game: GameDetail | None = strawberry.field(resolver=resolve_game)

    catalog_filters: CatalogFilterOptions = strawberry.field(resolver=resolve_catalog_filters)


schema = strawberry.Schema(query=Query)


def create_mongo_client() -> AsyncMongoClient:
    database_provider = os.getenv("DATABASE_PROVIDER", "local").strip().lower()

    if database_provider == "azure":
        return AsyncMongoClient(
            os.environ["AZURE_DOCUMENTDB_URI"],
            username=os.environ["AZURE_DOCUMENTDB_USERNAME"],
            password=os.environ["AZURE_DOCUMENTDB_PASSWORD"],
            serverSelectionTimeoutMS=10000,
        )

    if database_provider == "local":
        return AsyncMongoClient(
            os.environ["MONGO_URI"],
            serverSelectionTimeoutMS=5000,
        )

    raise ValueError(f"Unsupported database provider: {database_provider}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = create_mongo_client()

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
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
