from enum import Enum

import strawberry
from graphql import GraphQLError
from strawberry.types import Info

from steam_doma.modules.games.graphql_types import (
    GamePage,
    game_to_card,
)
from steam_doma.modules.games.repository import (
    GameFilters,
    GameRepository,
    GameSortBy,
    SortDirection,
)


@strawberry.enum
class GameSortField(Enum):
    NAME = "name"
    PRICE = "price"
    DISCOUNT = "discount"
    RECOMMENDATIONS = "recommendations"
    RELEASE_DATE = "release_date"


@strawberry.enum
class GameSortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


@strawberry.input
class GameFiltersInput:
    search: str | None = None
    genre_ids: list[str] | None = None
    category_ids: list[int] | None = None
    platforms: list[str] | None = None
    min_price_minor: int | None = None
    max_price_minor: int | None = None
    free_only: bool = False
    discounted_only: bool = False


async def resolve_games(
    info: Info,
    page: int = 1,
    page_size: int = 20,
    filters: GameFiltersInput | None = None,
    sort_by: GameSortField = GameSortField.NAME,
    sort_direction: GameSortOrder = GameSortOrder.ASC,
) -> GamePage:
    repository: GameRepository = info.context["games_repository"]

    if filters is None:
        game_filters = GameFilters()
    else:
        game_filters = GameFilters(
            search=filters.search,
            genre_ids=tuple(filters.genre_ids or ()),
            category_ids=tuple(filters.category_ids or ()),
            platforms=tuple(filters.platforms or ()),
            min_price_minor=filters.min_price_minor,
            max_price_minor=filters.max_price_minor,
            free_only=filters.free_only,
            discounted_only=filters.discounted_only,
        )

    try:
        documents = await repository.list_page(
            page=page,
            page_size=page_size,
            filters=game_filters,
            sort_by=GameSortBy(sort_by.value),
            sort_direction=SortDirection(sort_direction.value),
        )

        total_count = await repository.count_games(
            filters=game_filters,
        )

    except ValueError as error:
        raise GraphQLError(str(error)) from error

    return GamePage(
        items=[game_to_card(document) for document in documents],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
