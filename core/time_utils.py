"""Timezone utilities for consistent UTC handling across the app.

RU: Утилиты для работы с часовыми поясами и UTC-временем.
EN: Utilities for working with timezones and UTC-aware datetimes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

try:  # Python 3.9+
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for very old runtimes
    ZoneInfo = None  # type: ignore


def now_utc() -> datetime:
    """Return the current UTC time as an aware ``datetime``."""

    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure ``dt`` is timezone-aware in UTC."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def isoformat_utc(dt: Optional[datetime] = None) -> str:
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


# ---------------------------------------------------------------------------
# Thin facades for utils_pack feature key (PR-880)
# ---------------------------------------------------------------------------


def parse_datetime(value: str) -> Optional[datetime]:
    """Parse datetime string in various formats.

    Args:
        value: Datetime string to parse.

    Returns:
        Parsed datetime or None if parsing fails.
    """
    if not value:
        return None
    try:
        return parse_iso8601(value)
    except (ValueError, TypeError):
        # Try common date-only format
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None


def format_datetime(dt: object, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
    """Format datetime object or string to specified format.

    Args:
        dt: Datetime object or ISO string.
        fmt: Output format string.

    Returns:
        Formatted datetime string or None on error.
    """
    if dt is None:
        return None
    try:
        if isinstance(dt, str):
            parsed = parse_datetime(dt)
            if parsed is None:
                return None
            return parsed.strftime(fmt)
        if isinstance(dt, datetime):
            return dt.strftime(fmt)
        return None
    except (ValueError, TypeError, AttributeError):
        return None


def get_timezone_offset(tz_name: str) -> Optional[float]:
    """Get timezone offset in hours from UTC.

    Args:
        tz_name: Timezone name (e.g., 'UTC', 'US/Eastern').

    Returns:
        Offset in hours or None if timezone is invalid.
    """
    if not tz_name:
        return None
    if tz_name.upper() == "UTC":
        return 0.0
    if ZoneInfo is None:
        return None
    try:
        tz = ZoneInfo(tz_name)
        offset = datetime.now(tz).utcoffset()
        if offset is None:
            return None
        return offset.total_seconds() / 3600
    except (KeyError, ValueError, TypeError):
        return None


def is_valid_date(value: str) -> bool:
    """Check if string is a valid date.

    Args:
        value: Date string to validate.

    Returns:
        True if valid date, False otherwise.
    """
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def format_time(t: object, fmt: str = "%H:%M:%S") -> Optional[str]:
    """Format time object to specified format.

    Args:
        t: Time or datetime object.
        fmt: Output format string.

    Returns:
        Formatted time string or None on error.
    """
    if t is None:
        return None
    try:
        if isinstance(t, datetime):
            return t.strftime(fmt)
        if hasattr(t, "strftime"):
            strftimeMethod = getattr(t, "strftime")
            result = strftimeMethod(fmt)
            return str(result) if result is not None else None
        return None
    except (ValueError, TypeError, AttributeError):
        return None


def human_delta(delta: object) -> str:
    """Convert timedelta to human-readable string.

    Args:
        delta: Timedelta object or seconds as number.

    Returns:
        Human-readable duration string.
    """
    try:
        if isinstance(delta, (int, float)):
            delta = timedelta(seconds=delta)
        if not isinstance(delta, timedelta):
            return "0 seconds"
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds} second{'s' if total_seconds != 1 else ''}"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        days = hours // 24
        return f"{days} day{'s' if days != 1 else ''}"
    except (ValueError, TypeError, AttributeError):
        return "0 seconds"
