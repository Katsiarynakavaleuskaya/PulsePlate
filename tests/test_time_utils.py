"""Tests for timezone utility helpers."""

from datetime import UTC, datetime, timezone

import core.time_utils as time_utils


def test_parse_iso8601_handles_naive_and_aware():
    naive = time_utils.parse_iso8601("2023-01-01T00:00:00")
    aware = time_utils.parse_iso8601("2023-01-01T00:00:00+02:00")

    assert naive.tzinfo == UTC
    assert aware.tzinfo == UTC
    assert aware.hour == 22  # converted back to UTC


def test_to_timezone_converts_correctly():
    base = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    converted = time_utils.to_timezone(base, "Europe/Minsk")

    assert converted.tzname() in {"MSK", "UTC+03:00", "+03"}
    assert converted.hour == 15


def test_local_date_today_uses_timezone(monkeypatch):
    fake_now = datetime(2023, 1, 2, 2, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(time_utils, "now_utc", lambda: fake_now)

    assert time_utils.local_date_today("America/Los_Angeles") == "2023-01-01"
    assert time_utils.local_date_today("Europe/Minsk") == "2023-01-02"


def test_isoformat_utc_returns_timezone():
    ts = time_utils.isoformat_utc(datetime(2023, 5, 1, 10, 30, tzinfo=UTC))
    assert ts.endswith("+00:00")


def test_now_utc_is_timezone_aware():
    now = time_utils.now_utc()
    assert now.tzinfo == UTC
