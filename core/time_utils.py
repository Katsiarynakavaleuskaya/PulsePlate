"""Timezone utilities for consistent UTC handling across the app.

RU: Утилиты для работы с часовыми поясами и UTC-временем.
EN: Utilities for working with timezones and UTC-aware datetimes.
"""

from __future__ import annotations


try:
    from datetime import UTC, datetime  # Python 3.11+
except ImportError:  # pragma: no cover - Python <3.11 fallback
    from datetime import datetime
    from datetime import timezone as _timezone

    UTC = UTC  # pragma: no cover


try:  # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - fallback for very old runtimes
    ZoneInfo = None  # type: ignore


def now_utc() -> datetime:
    """Return the current UTC time as an aware ``datetime``."""

    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure ``dt`` is timezone-aware in UTC."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def isoformat_utc(dt: datetime | None = None) -> str:
    """Return an ISO 8601 string in UTC."""

    return ensure_utc(dt or now_utc()).isoformat()


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO 8601 string, defaulting to UTC when tzinfo is missing."""

    dt = datetime.fromisoformat(value)
    return ensure_utc(dt)


def to_timezone(dt: datetime, tz_name: str) -> datetime:
    """Convert ``dt`` (assumed UTC if naive) to the user's timezone."""

    if ZoneInfo is None:
        raise RuntimeError("zoneinfo module is required for timezone conversions")
    tz = ZoneInfo(tz_name)
    return ensure_utc(dt).astimezone(tz)


def local_now(tz_name: str) -> datetime:
    """Return current time in the given timezone."""

    return to_timezone(now_utc(), tz_name)


def local_date_today(tz_name: str) -> str:
    """Return today's date (YYYY-MM-DD) in the given timezone."""

    return local_now(tz_name).date().isoformat()
