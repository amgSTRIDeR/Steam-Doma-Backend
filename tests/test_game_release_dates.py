from datetime import UTC, datetime

import pytest

from steam_doma.modules.games.release_dates import parse_release_date


@pytest.mark.parametrize(
    ("release_date", "expected"),
    [
        (
            {"coming_soon": False, "date": "Jul 16, 2025"},
            datetime(2025, 7, 16, tzinfo=UTC),
        ),
        (
            {"coming_soon": False, "date": "July 16, 2025"},
            datetime(2025, 7, 16, tzinfo=UTC),
        ),
        (
            {"coming_soon": False, "date": "16 Jul, 2025"},
            datetime(2025, 7, 16, tzinfo=UTC),
        ),
        (
            {"coming_soon": False, "date": "2025-07-16"},
            datetime(2025, 7, 16, tzinfo=UTC),
        ),
        (
            {"coming_soon": True, "date": "Dec 1, 2027"},
            None,
        ),
        (
            {"coming_soon": True, "date": "To be announced"},
            None,
        ),
        (
            {"coming_soon": False, "date": "Summer 2025"},
            None,
        ),
        (
            {"coming_soon": False, "date": "Feb 30, 2025"},
            None,
        ),
        (
            {"coming_soon": False, "date": "2025"},
            None,
        ),
        (None, None),
        ({}, None),
    ],
)
def test_parse_release_date(
    release_date: object,
    expected: datetime | None,
) -> None:
    assert parse_release_date(release_date) == expected
