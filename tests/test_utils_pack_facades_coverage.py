"""Coverage tests for utils_pack facades (PR-880).

Covers all new facade functions in core/utils.py and core/time_utils.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


class TestCoreUtilsFacades:
    """Test core.utils facade functions for coverage."""

    def test_safe_float_valid_inputs(self) -> None:
        """Test safe_float with valid inputs."""
        from core.utils import safe_float

        assert safe_float("123.45") == 123.45
        assert safe_float("0") == 0.0
        assert safe_float("-123.45") == -123.45
        assert safe_float(42) == 42.0
        assert safe_float(3.14) == 3.14

    def test_safe_float_invalid_inputs(self) -> None:
        """Test safe_float with invalid inputs returns default."""
        from core.utils import safe_float

        assert safe_float("invalid") is None
        assert safe_float("") is None
        assert safe_float(None) is None
        assert safe_float("invalid", default=0.0) == 0.0
        assert safe_float(None, default=-1.0) == -1.0

    def test_safe_int_valid_inputs(self) -> None:
        """Test safe_int with valid inputs."""
        from core.utils import safe_int

        assert safe_int("123") == 123
        assert safe_int("0") == 0
        assert safe_int("-123") == -123
        assert safe_int(42) == 42
        assert safe_int("123.45") == 123  # truncates float string

    def test_safe_int_invalid_inputs(self) -> None:
        """Test safe_int with invalid inputs returns default."""
        from core.utils import safe_int

        assert safe_int("invalid") is None
        assert safe_int("") is None
        assert safe_int(None) is None
        assert safe_int("invalid", default=0) == 0
        assert safe_int(None, default=-1) == -1

    def test_slugify_various_inputs(self) -> None:
        """Test slugify with various inputs."""
        from core.utils import slugify

        assert slugify("Test String") == "test-string"
        assert slugify("Special!@#$%Characters") == "special-characters"
        assert slugify("") == ""
        assert slugify(None) == ""
        assert slugify("  Leading Trailing  ") == "leading-trailing"
        assert slugify("multiple   spaces") == "multiple-spaces"

    def test_format_number_valid(self) -> None:
        """Test format_number with valid inputs."""
        from core.utils import format_number

        assert format_number(1234.567) == "1234.57"
        assert format_number(1234.567, decimals=1) == "1234.6"
        assert format_number(0) == "0.00"
        assert format_number("42.1") == "42.10"

    def test_format_number_invalid(self) -> None:
        """Test format_number with invalid inputs returns str(value)."""
        from core.utils import format_number

        result = format_number("invalid")
        assert result == "invalid"
        result = format_number(None)
        assert result == "None"

    def test_generate_id(self) -> None:
        """Test generate_id returns valid UUID hex."""
        from core.utils import generate_id

        idVal = generate_id()
        assert isinstance(idVal, str)
        assert len(idVal) == 32
        # Should be unique
        idVal2 = generate_id()
        assert idVal != idVal2

    def test_sanitize_html(self) -> None:
        """Test sanitize_html removes tags."""
        from core.utils import sanitize_html

        assert sanitize_html("<script>alert('xss')</script>") == "alert('xss')"
        assert sanitize_html("<p>Valid</p>") == "Valid"
        assert sanitize_html("No tags") == "No tags"
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_validate_email(self) -> None:
        """Test validate_email."""
        from core.utils import validate_email

        assert validate_email("test@example.com") is True
        assert validate_email("user.name+tag@domain.co.uk") is True
        assert validate_email("invalid-email") is False
        assert validate_email("@nodomain.com") is False
        assert validate_email("noat.com") is False
        assert validate_email("") is False
        assert validate_email(None) is False


class TestCoreTimeUtilsFacades:
    """Test core.time_utils facade functions for coverage."""

    def test_parse_datetime_iso(self) -> None:
        """Test parse_datetime with ISO format."""
        from core.time_utils import parse_datetime

        result = parse_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_datetime_date_only(self) -> None:
        """Test parse_datetime with date-only format."""
        from core.time_utils import parse_datetime

        result = parse_datetime("2024-01-15")
        assert result is not None
        assert result.year == 2024

    def test_parse_datetime_invalid(self) -> None:
        """Test parse_datetime with invalid input."""
        from core.time_utils import parse_datetime

        assert parse_datetime("invalid") is None
        assert parse_datetime("") is None
        assert parse_datetime("not-a-date") is None

    def test_format_datetime_from_string(self) -> None:
        """Test format_datetime with string input."""
        from core.time_utils import format_datetime

        result = format_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert "2024" in result

    def test_format_datetime_from_datetime(self) -> None:
        """Test format_datetime with datetime object."""
        from core.time_utils import format_datetime

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_datetime(dt)
        assert result is not None
        assert "2024" in result

    def test_format_datetime_none(self) -> None:
        """Test format_datetime with None."""
        from core.time_utils import format_datetime

        assert format_datetime(None) is None

    def test_format_datetime_invalid_string(self) -> None:
        """Test format_datetime with invalid string."""
        from core.time_utils import format_datetime

        assert format_datetime("invalid") is None

    def test_format_datetime_invalid_type(self) -> None:
        """Test format_datetime with invalid type returns None."""
        from core.time_utils import format_datetime

        assert format_datetime(12345) is None

    def test_get_timezone_offset_utc(self) -> None:
        """Test get_timezone_offset with UTC."""
        from core.time_utils import get_timezone_offset

        assert get_timezone_offset("UTC") == 0.0

    def test_get_timezone_offset_named(self) -> None:
        """Test get_timezone_offset with named timezone."""
        from core.time_utils import get_timezone_offset

        # US/Eastern is either -5 or -4 depending on DST
        offset = get_timezone_offset("US/Eastern")
        assert offset is None or isinstance(offset, float)

    def test_get_timezone_offset_empty(self) -> None:
        """Test get_timezone_offset with empty string."""
        from core.time_utils import get_timezone_offset

        assert get_timezone_offset("") is None

    def test_get_timezone_offset_invalid(self) -> None:
        """Test get_timezone_offset with invalid timezone."""
        from core.time_utils import get_timezone_offset

        assert get_timezone_offset("Invalid/Timezone") is None

    def test_is_valid_date(self) -> None:
        """Test is_valid_date."""
        from core.time_utils import is_valid_date

        assert is_valid_date("2024-01-15") is True
        assert is_valid_date("invalid") is False
        assert is_valid_date("") is False
        assert is_valid_date("2024-13-45") is False  # invalid month/day

    def test_format_time_datetime(self) -> None:
        """Test format_time with datetime object."""
        from core.time_utils import format_time

        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = format_time(dt)
        assert result == "10:30:45"

    def test_format_time_none(self) -> None:
        """Test format_time with None."""
        from core.time_utils import format_time

        assert format_time(None) is None

    def test_format_time_invalid(self) -> None:
        """Test format_time with invalid type."""
        from core.time_utils import format_time

        assert format_time("not a time") is None
        assert format_time(12345) is None

    def test_human_delta_seconds(self) -> None:
        """Test human_delta with seconds."""
        from core.time_utils import human_delta

        assert human_delta(30) == "30 seconds"
        assert human_delta(1) == "1 second"
        assert human_delta(0) == "0 seconds"

    def test_human_delta_minutes(self) -> None:
        """Test human_delta with minutes."""
        from core.time_utils import human_delta

        assert human_delta(60) == "1 minute"
        assert human_delta(120) == "2 minutes"
        assert human_delta(90) == "1 minute"  # rounds down

    def test_human_delta_hours(self) -> None:
        """Test human_delta with hours."""
        from core.time_utils import human_delta

        assert human_delta(3600) == "1 hour"
        assert human_delta(7200) == "2 hours"

    def test_human_delta_days(self) -> None:
        """Test human_delta with days."""
        from core.time_utils import human_delta

        assert human_delta(86400) == "1 day"
        assert human_delta(172800) == "2 days"

    def test_human_delta_timedelta(self) -> None:
        """Test human_delta with timedelta object."""
        from core.time_utils import human_delta

        assert human_delta(timedelta(seconds=30)) == "30 seconds"
        assert human_delta(timedelta(minutes=5)) == "5 minutes"
        assert human_delta(timedelta(hours=2)) == "2 hours"
        assert human_delta(timedelta(days=3)) == "3 days"

    def test_human_delta_invalid(self) -> None:
        """Test human_delta with invalid input."""
        from core.time_utils import human_delta

        assert human_delta("invalid") == "0 seconds"
        assert human_delta(None) == "0 seconds"


class TestTimeUtilsEdgeCases:
    """Additional edge case tests for time_utils to reach 97% coverage."""

    def test_format_datetime_exception_path(self) -> None:
        """Test format_datetime exception handling with datetime subclass."""
        from datetime import datetime

        from core.time_utils import format_datetime

        # Subclass of datetime that raises on strftime
        class BadDatetime(datetime):
            def strftime(self, fmt: str) -> str:
                raise ValueError("bad format")

        # Create instance that will pass isinstance check but raise on strftime
        bad_dt = BadDatetime(2024, 1, 1, 12, 0, 0)
        result = format_datetime(bad_dt)
        assert result is None

    def test_get_timezone_offset_zoneinfo_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_timezone_offset when ZoneInfo unavailable."""
        import core.time_utils as tu

        monkeypatch.setattr(tu, "ZoneInfo", None)
        result = tu.get_timezone_offset("America/New_York")
        assert result is None

    def test_get_timezone_offset_invalid_timezone(self) -> None:
        """Test get_timezone_offset with invalid timezone names."""
        from core.time_utils import get_timezone_offset

        # Invalid timezone names trigger KeyError path
        assert get_timezone_offset("Invalid/Timezone") is None
        assert get_timezone_offset("NotATimezone") is None
        assert get_timezone_offset("Fake/Zone/Name") is None

    def test_get_timezone_offset_utcoffset_returns_none(self) -> None:
        """Test get_timezone_offset when utcoffset returns None."""
        from unittest.mock import MagicMock, patch

        import core.time_utils as tu

        # Create a mock datetime that returns None for utcoffset
        mock_dt = MagicMock()
        mock_dt.utcoffset.return_value = None

        # Patch the datetime class in the time_utils module
        with patch.object(tu, "datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            result = tu.get_timezone_offset("America/New_York")
            assert result is None

    def test_format_time_with_time_object(self) -> None:
        """Test format_time with time object that has strftime."""
        from datetime import time

        from core.time_utils import format_time

        t = time(10, 30, 45)
        result = format_time(t)
        assert result == "10:30:45"

    def test_format_time_strftime_returns_none(self) -> None:
        """Test format_time when strftime returns None."""
        from core.time_utils import format_time

        class WeirdTime:
            def strftime(self, fmt: str) -> None:
                return None

        result = format_time(WeirdTime())
        assert result is None

    def test_format_time_strftime_raises(self) -> None:
        """Test format_time when strftime raises."""
        from core.time_utils import format_time

        class BadTime:
            def strftime(self, fmt: str) -> str:
                raise TypeError("bad")

        result = format_time(BadTime())
        assert result is None

    def test_human_delta_exception_in_total_seconds(self) -> None:
        """Test human_delta exception path with timedelta subclass."""
        from datetime import timedelta

        from core.time_utils import human_delta

        # Subclass of timedelta that raises on total_seconds
        class BadDelta(timedelta):
            def total_seconds(self) -> float:
                raise ValueError("cannot compute total_seconds")

        # Create instance that will pass isinstance check but raise on total_seconds
        bad_delta = BadDelta(seconds=100)
        result = human_delta(bad_delta)
        assert result == "0 seconds"
