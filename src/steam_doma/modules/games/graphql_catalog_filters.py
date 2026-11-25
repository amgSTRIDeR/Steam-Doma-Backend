import strawberry
from strawberry.types import Info

from steam_doma.modules.games.repository import GameRepository


@strawberry.type
class GenreOption:
    id: str
    name: str


@strawberry.type
class CategoryOption:
    id: int
    name: str


@strawberry.type
class PlatformOption:
    id: str
    name: str


@strawberry.type
class CatalogFilterOptions:
    genres: list[GenreOption]
    categories: list[CategoryOption]
    platforms: list[PlatformOption]


async def resolve_catalog_filters(
    info: Info,
) -> CatalogFilterOptions:
    repository: GameRepository = info.context["games_repository"]

    genre_documents, category_documents = await repository.get_filter_options()

    genres = [
        GenreOption(
            id=document["_id"],
            name=document["name"],
        )
        for document in genre_documents
    ]

    categories = [
        CategoryOption(
            id=document["_id"],
            name=document["name"],
        )
        for document in category_documents
    ]

    platforms = [
        PlatformOption(id="windows", name="Windows"),
        PlatformOption(id="mac", name="macOS"),
        PlatformOption(id="linux", name="Linux"),
    ]

    return CatalogFilterOptions(
        genres=genres,
        categories=categories,
        platforms=platforms,
    )
