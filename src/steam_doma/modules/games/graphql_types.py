from datetime import date, datetime
from typing import Any

import strawberry


@strawberry.type
class GameGenre:
    id: str
    name: str


@strawberry.type
class GamePlatforms:
    windows: bool
    mac: bool
    linux: bool


@strawberry.type
class GameCard:
    id: strawberry.ID
    steam_appid: int
    name: str
    is_free: bool | None

    price_minor: int | None
    original_currency: str | None
    discount_percent: int | None

    header_image: str | None
    genres: list[GameGenre]
    platforms: GamePlatforms

    release_date: date | None
    recommendations_total: int | None


@strawberry.type
class GamePage:
    items: list[GameCard]
    total_count: int
    page: int
    page_size: int


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _non_negative_int(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value

    return None


def game_to_card(document: dict[str, Any]) -> GameCard:
    """Convert a MongoDB game document to a GraphQL card."""

    price = _as_dict(document.get("price"))
    platforms = _as_dict(document.get("platforms"))
    steam_data = _as_dict(document.get("steam_data"))
    recommendations = _as_dict(steam_data.get("recommendations"))

    raw_is_free = document.get("is_free")

    is_free = raw_is_free if type(raw_is_free) is bool else None

    if is_free is True:
        price_minor = 0
    else:
        price_minor = _non_negative_int(price.get("final"))

    raw_discount = _non_negative_int(price.get("discount_percent"))

    discount_percent = raw_discount if raw_discount is not None and raw_discount <= 100 else None

    raw_currency = price.get("currency")
    original_currency = raw_currency if isinstance(raw_currency, str) else None

    raw_genres = document.get("genres")
    genres: list[GameGenre] = []

    if isinstance(raw_genres, list):
        for genre in raw_genres:
            if not isinstance(genre, dict):
                continue

            genre_id = genre.get("id")
            genre_name = genre.get("description")

            if isinstance(genre_id, str) and isinstance(genre_name, str):
                genres.append(
                    GameGenre(
                        id=genre_id,
                        name=genre_name,
                    )
                )

    raw_image = steam_data.get("header_image")
    header_image = raw_image if isinstance(raw_image, str) else None

    raw_release_date = document.get("release_date_utc")

    release_date = raw_release_date.date() if isinstance(raw_release_date, datetime) else None

    return GameCard(
        id=strawberry.ID(str(document["_id"])),
        steam_appid=document["steam_appid"],
        name=document["name"],
        is_free=is_free,
        price_minor=price_minor,
        original_currency=original_currency,
        discount_percent=discount_percent,
        header_image=header_image,
        genres=genres,
        platforms=GamePlatforms(
            windows=platforms.get("windows") is True,
            mac=platforms.get("mac") is True,
            linux=platforms.get("linux") is True,
        ),
        release_date=release_date,
        recommendations_total=_non_negative_int(recommendations.get("total")),
    )
