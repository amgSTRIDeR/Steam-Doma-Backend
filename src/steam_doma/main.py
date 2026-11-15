import os
from contextlib import asynccontextmanager

import strawberry
from fastapi import FastAPI, Request
from pymongo import AsyncMongoClient
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class Query:
    @strawberry.field
    async def ping(self) -> str:
        return "pong"


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
    GraphQLRouter(schema),
    prefix="/graphql",
)
