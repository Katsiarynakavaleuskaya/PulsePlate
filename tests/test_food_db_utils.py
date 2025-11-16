"""Unit tests for helpers in core.food_db."""

from core.food_db import _parse_optional_float


def test_parse_optional_float_handles_none() -> None:
    assert _parse_optional_float(None) is None


def test_parse_optional_float_handles_blanks() -> None:
    assert _parse_optional_float("   ") is None


def test_parse_optional_float_handles_invalid_numbers() -> None:
    assert _parse_optional_float("not_a_number") is None


def test_parse_optional_float_parses_values() -> None:
    assert _parse_optional_float("12.5") == 12.5
