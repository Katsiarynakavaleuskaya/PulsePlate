"""
Tests for delimiter handling in food_store CSV parsing.

RU: Тесты для обработки разделителей в парсинге CSV food_store.
EN: Tests for delimiter handling in food_store CSV parsing.
"""

import csv
from io import StringIO
from pathlib import Path

import pytest

from app.services.food_store import _parse_primary_aliases_schema


def test_parse_primary_aliases_schema_semicolon_delimiter() -> None:
    """Test parsing with semicolon delimiter in aliases field."""
    # CSV with semicolon-separated aliases
    # Function reads header itself, so we pass reader positioned at start
    csv_content = "primary,aliases\napple,green apple;red apple;granny smith"
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    assert "apple" in result
    assert "green apple" in result["apple"]
    assert "red apple" in result["apple"]
    assert "granny smith" in result["apple"]


def test_parse_primary_aliases_schema_comma_delimiter() -> None:
    """Test parsing with comma delimiter in aliases field."""
    # CSV with comma-separated aliases (unquoted commas)
    # Function reads header itself
    csv_content = "primary,aliases\nbanana,yellow fruit,curved fruit,sweet fruit"
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    assert "banana" in result
    # All values after primary should be parsed as aliases
    assert "yellow fruit" in result["banana"]
    assert "curved fruit" in result["banana"]
    assert "sweet fruit" in result["banana"]


def test_parse_primary_aliases_schema_mixed_delimiters() -> None:
    """Test parsing with mixed semicolon and comma delimiters."""
    # CSV with both semicolons and commas in aliases
    # Function reads header itself
    csv_content = "primary,aliases\norange,citrus fruit;round fruit,sweet orange"
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    assert "orange" in result
    # Should split by semicolon first, then by comma
    assert "citrus fruit" in result["orange"]
    assert "round fruit" in result["orange"]
    assert "sweet orange" in result["orange"]


def test_parse_primary_aliases_schema_empty_fields() -> None:
    """Test parsing with empty fields in CSV."""
    # Function reads header itself
    csv_content = "primary,aliases\napple,green apple,,red apple\nbanana,"
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    # Empty fields should be skipped
    assert "apple" in result
    assert "green apple" in result["apple"]
    assert "red apple" in result["apple"]
    assert "" not in result["apple"]

    # Entry with empty aliases should still be present (but with empty list)
    assert "banana" in result


def test_parse_primary_aliases_schema_whitespace_handling() -> None:
    """Test parsing with whitespace around aliases."""
    # Function reads header itself
    csv_content = "primary,aliases\napple, green apple , red apple , granny smith "
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    assert "apple" in result
    # Whitespace should be stripped
    assert "green apple" in result["apple"]
    assert "red apple" in result["apple"]
    assert "granny smith" in result["apple"]
    # No leading/trailing spaces
    assert " green apple " not in result["apple"]


def test_parse_primary_aliases_schema_duplicate_aliases() -> None:
    """Test parsing handles duplicate aliases correctly."""
    # Function reads header itself
    csv_content = "primary,aliases\napple,red apple,green apple,red apple"
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    assert "apple" in result
    # Duplicates should be removed
    assert result["apple"].count("red apple") == 1
    assert "green apple" in result["apple"]


def test_parse_primary_aliases_schema_case_insensitive() -> None:
    """Test parsing is case-insensitive for primary names."""
    # Function reads header itself
    csv_content = "primary,aliases\nApple,red apple\nBANANA,yellow fruit"
    reader = csv.reader(StringIO(csv_content))

    result = _parse_primary_aliases_schema(reader)

    # Primary should be lowercased
    assert "apple" in result
    assert "banana" in result
    assert "Apple" not in result
    assert "BANANA" not in result
