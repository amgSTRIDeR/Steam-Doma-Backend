import re
from datetime import UTC, datetime

DATE_FORMATS = (
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b, %Y",
    "%d %B, %Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%d",
)

RU_MONTHS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "мая": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "сент": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}


def parse_release_date(release_date: object) -> datetime | None:
    if not isinstance(release_date, dict):
        return None

    if release_date.get("coming_soon") is not False:
        return None

    raw_date = release_date.get("date")

    if not isinstance(raw_date, str):
        return None

    raw_date = raw_date.strip()

    for date_format in DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw_date, date_format)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue

    russian_date = re.fullmatch(
        r"(?P<day>\d{1,2})\s+(?P<month>[а-яё]{3,4})\.\s+"
        r"(?P<year>\d{4})\s+г\.",
        raw_date,
        flags=re.IGNORECASE,
    )

    if russian_date is None:
        return None

    month = RU_MONTHS.get(russian_date["month"].lower())

    if month is None:
        return None

    try:
        return datetime(
            int(russian_date["year"]),
            month,
            int(russian_date["day"]),
            tzinfo=UTC,
        )
    except ValueError:
        return None
