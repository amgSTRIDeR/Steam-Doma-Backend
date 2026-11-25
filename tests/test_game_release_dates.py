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
        (
            {"coming_soon": False, "date": "6 JUL 2015"},
            datetime(2015, 7, 6, tzinfo=UTC),
        ),
        (
            {"coming_soon": False, "date": "10 окт. 2019 г."},
            datetime(2019, 10, 10, tzinfo=UTC),
        ),
        (
            {"coming_soon": False, "date": "31 фев. 2024 г."},
            None,
        ),
    ],
)
def test_parse_release_date(
    release_date: object,
    expected: datetime | None,
) -> None:
    assert parse_release_date(release_date) == expected
