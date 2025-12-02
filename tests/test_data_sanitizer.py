"""Tests for core.data_sanitizer module."""

from core.data_sanitizer import sanity_filter_plate_data


def test_sanity_filter_plate_data_returns_unchanged() -> None:
    """sanity_filter_plate_data returns input data unchanged (stub behavior)."""
    test_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
    result = sanity_filter_plate_data(test_data)
    assert result == test_data
    assert result is test_data  # Should return the same object


def test_sanity_filter_plate_data_empty_dict() -> None:
    """sanity_filter_plate_data handles empty dictionary."""
    result = sanity_filter_plate_data({})
    assert result == {}
