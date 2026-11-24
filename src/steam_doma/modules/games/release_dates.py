from datetime import UTC, datetime

DATE_FORMATS = (
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b, %Y",
    "%d %B, %Y",
    "%Y-%m-%d",
)


def parse_release_date(release_date: object) -> datetime | None:
    """Parse a confirmed Steam release date into a UTC datetime."""

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
        except ValueError:
            continue

        return parsed.replace(tzinfo=UTC)

    return None
