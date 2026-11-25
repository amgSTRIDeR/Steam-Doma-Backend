from datetime import date
from typing import Any

import strawberry

from steam_doma.modules.games.graphql_types import (
    GameGenre,
    GamePlatforms,
    game_to_card,
)


@strawberry.type
class GameCategory:
    id: int
    name: str


@strawberry.type
class GameScreenshot:
    id: int | None
    thumbnail_url: str | None
    full_url: str | None


@strawberry.type
class GameTrailer:
    id: int | None
    name: str | None
    thumbnail_url: str | None
    mp4_url: str | None
    webm_url: str | None


@strawberry.type
class GameRequirements:
    minimum: str | None
    recommended: str | None


@strawberry.type
class GameDetail:
    id: strawberry.ID
    steam_appid: int
    name: str
    is_free: bool | None

    price_minor: int | None
    original_currency: str | None
    discount_percent: int | None

    header_image: str | None
    genres: list[GameGenre]
    categories: list[GameCategory]
    platforms: GamePlatforms

    release_date: date | None
    release_date_text: str | None
    coming_soon: bool | None

    short_description: str | None
    detailed_description: str | None
    about_the_game: str | None

    developers: list[str]
    publishers: list[str]

    screenshots: list[GameScreenshot]
    trailers: list[GameTrailer]

    pc_requirements: GameRequirements | None
    mac_requirements: GameRequirements | None
    linux_requirements: GameRequirements | None

    supported_languages: str | None
    controller_support: str | None
    required_age: int | None
    website: str | None

    recommendations_total: int | None
    metacritic_score: int | None


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _non_negative_int(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def _text_list(value: object) -> list[str]:
    result = []

    for item in _as_list(value):
        text = _text(item)
        if text is not None:
            result.append(text)

    return result


def _requirements(value: object) -> GameRequirements | None:
    data = _as_dict(value)

    minimum = _text(data.get("minimum"))
    recommended = _text(data.get("recommended"))

    if minimum is None and recommended is None:
        return None

    return GameRequirements(
        minimum=minimum,
        recommended=recommended,
    )


def _video_url(value: object) -> str | None:
    data = _as_dict(value)

    return _text(data.get("max")) or _text(data.get("480"))


def game_to_detail(document: dict[str, Any]) -> GameDetail:
    """Convert a full MongoDB game document to GraphQL detail."""

    card = game_to_card(document)
    steam_data = _as_dict(document.get("steam_data"))
    release_data = _as_dict(steam_data.get("release_date"))
    metacritic = _as_dict(steam_data.get("metacritic"))

    categories: list[GameCategory] = []

    for item in _as_list(document.get("categories")):
        category = _as_dict(item)

        category_id = category.get("id")
        category_name = _text(category.get("description"))

        if type(category_id) is int and category_name is not None:
            categories.append(
                GameCategory(
                    id=category_id,
                    name=category_name,
                )
            )

    screenshots: list[GameScreenshot] = []

    for item in _as_list(steam_data.get("screenshots")):
        screenshot = _as_dict(item)

        screenshots.append(
            GameScreenshot(
                id=_non_negative_int(screenshot.get("id")),
                thumbnail_url=_text(screenshot.get("path_thumbnail")),
                full_url=_text(screenshot.get("path_full")),
            )
        )

    trailers: list[GameTrailer] = []

    for item in _as_list(steam_data.get("movies")):
        movie = _as_dict(item)

        trailers.append(
            GameTrailer(
                id=_non_negative_int(movie.get("id")),
                name=_text(movie.get("name")),
                thumbnail_url=_text(movie.get("thumbnail")),
                mp4_url=_video_url(movie.get("mp4")),
                webm_url=_video_url(movie.get("webm")),
            )
        )

    raw_coming_soon = release_data.get("coming_soon")

    coming_soon = raw_coming_soon if type(raw_coming_soon) is bool else None

    score = _non_negative_int(metacritic.get("score"))

    if score is not None and score > 100:
        score = None

    return GameDetail(
        id=card.id,
        steam_appid=card.steam_appid,
        name=card.name,
        is_free=card.is_free,
        price_minor=card.price_minor,
        original_currency=card.original_currency,
        discount_percent=card.discount_percent,
        header_image=card.header_image,
        genres=card.genres,
        categories=categories,
        platforms=card.platforms,
        release_date=card.release_date,
        release_date_text=_text(release_data.get("date")),
        coming_soon=coming_soon,
        short_description=_text(steam_data.get("short_description")),
        detailed_description=_text(steam_data.get("detailed_description")),
        about_the_game=_text(steam_data.get("about_the_game")),
        developers=_text_list(steam_data.get("developers")),
        publishers=_text_list(steam_data.get("publishers")),
        screenshots=screenshots,
        trailers=trailers,
        pc_requirements=_requirements(steam_data.get("pc_requirements")),
        mac_requirements=_requirements(steam_data.get("mac_requirements")),
        linux_requirements=_requirements(steam_data.get("linux_requirements")),
        supported_languages=_text(steam_data.get("supported_languages")),
        controller_support=_text(steam_data.get("controller_support")),
        required_age=_non_negative_int(steam_data.get("required_age")),
        website=_text(steam_data.get("website")),
        recommendations_total=card.recommendations_total,
        metacritic_score=score,
    )
