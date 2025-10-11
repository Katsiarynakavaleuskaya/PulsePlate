"""Coverage tests for core.time_utils helper functions."""

from datetime import UTC, datetime

from core import time_utils


def test_now_utc_returns_aware_datetime() -> None:
    """now_utc should return an aware datetime in UTC."""
    dt = time_utils.now_utc()
    assert dt.tzinfo == UTC


def test_ensure_utc_converts_naive_datetime() -> None:
    """ensure_utc should attach UTC to naive datetimes."""
    naive = datetime(2024, 1, 1, 12, 0, 0)
    converted = time_utils.ensure_utc(naive)
    assert converted.tzinfo == UTC
    assert converted.hour == 12


def test_isoformat_utc_uses_utc_timezone() -> None:
    """isoformat_utc should produce an ISO string suffixed with UTC offset."""
    naive = datetime(2024, 1, 1, 0, 0, 0)
    iso_value = time_utils.isoformat_utc(naive)
    assert iso_value.endswith("+00:00")


def test_parse_iso8601_handles_offset_and_naive() -> None:
    """parse_iso8601 should normalise both naive and offset datetimes to UTC."""
    parsed = time_utils.parse_iso8601("2024-01-01T12:00:00+02:00")
    assert parsed.tzinfo == UTC
    assert parsed.hour == 10  # Converted back to UTC

    parsed_naive = time_utils.parse_iso8601("2024-01-01T12:00:00")
    assert parsed_naive.tzinfo == UTC
    assert parsed_naive.hour == 12


def test_to_timezone_applies_zoneinfo() -> None:
    """to_timezone should convert the datetime into the requested zone."""
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    berlin = time_utils.to_timezone(base, "Europe/Berlin")
    assert berlin.tzinfo is not None
    assert berlin.tzinfo.key == "Europe/Berlin"
    assert berlin.hour == 13  # UTC+1 in January


def test_local_helpers_use_target_timezone() -> None:
    """local_now/local_date_today should respect the requested timezone."""
    utc_now = time_utils.local_now("UTC")
    assert getattr(utc_now.tzinfo, "key", "UTC") == "UTC"

    assert time_utils.local_date_today("UTC") == time_utils.now_utc().date().isoformat()
