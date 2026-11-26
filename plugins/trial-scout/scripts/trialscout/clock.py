"""Time: aware-UTC now (overridable in tests), ISO parsing, filename timestamps."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime


def parse_time(value: str | date | datetime) -> datetime:
    """ISO date or datetime -> aware UTC datetime. Date-only -> T12:00:00Z; naive -> assumed UTC."""
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            value = date.fromisoformat(s)
        else:
            try:
                value = datetime.fromisoformat(s)
            except ValueError:
                raise ValueError(f"not an ISO date or datetime: {value!r}") from None
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, 12, tzinfo=UTC)
    raise ValueError(f"not a date or datetime: {value!r}")


