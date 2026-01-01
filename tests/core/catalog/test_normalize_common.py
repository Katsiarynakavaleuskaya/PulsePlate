# -*- coding: utf-8 -*-
"""
Tests for core/catalog/normalize/common.py (PR-7).

RU: Тесты для функций нормализации (parse_decimal, normalize_currency, normalize_unit).
EN: Tests for normalization functions.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.catalog.normalize.common import normalize_currency, normalize_unit, parse_decimal


class TestParseDecimal:
    """Tests for parse_decimal function."""

    def test_parse_decimal_none(self) -> None:
        """Test that None returns None."""
        assert parse_decimal(None) is None

    def test_parse_decimal_empty_string(self) -> None:
        """Test that empty string returns None."""
        assert parse_decimal("") is None
        assert parse_decimal("   ") is None

    def test_parse_decimal_simple_integer(self) -> None:
        """Test parsing simple integers."""
        assert parse_decimal("123") == Decimal("123")
        assert parse_decimal("0") == Decimal("0")

    def test_parse_decimal_simple_decimal(self) -> None:
        """Test parsing simple decimals."""
        assert parse_decimal("123.45") == Decimal("123.45")
        assert parse_decimal("0.5") == Decimal("0.5")

    def test_parse_decimal_eu_format_comma(self) -> None:
        """Test parsing EU format with comma as decimal separator."""
        assert parse_decimal("123,45") == Decimal("123.45")
        assert parse_decimal("0,5") == Decimal("0.5")

    def test_parse_decimal_eu_format_with_thousands(self) -> None:
        """Test parsing EU format with thousands separator."""
        assert parse_decimal("1.234,56") == Decimal("1234.56")
        assert parse_decimal("10.000,99") == Decimal("10000.99")

    def test_parse_decimal_us_format_with_thousands(self) -> None:
        """Test parsing US format with thousands separator."""
        assert parse_decimal("1,234.56") == Decimal("1234.56")
        assert parse_decimal("1,234,567.89") == Decimal("1234567.89")

    def test_parse_decimal_with_spaces(self) -> None:
        """Test parsing numbers with spaces as thousand separators."""
        assert parse_decimal("1 234.56") == Decimal("1234.56")
        assert parse_decimal("1 234 567.89") == Decimal("1234567.89")
        assert parse_decimal("1 234,56") == Decimal("1234.56")

    def test_parse_decimal_invalid_returns_none(self) -> None:
        """Test that invalid input returns None."""
        assert parse_decimal("abc") is None
        assert parse_decimal("12.34.56") is None
        assert parse_decimal("not a number") is None


class TestNormalizeCurrency:
    """Tests for normalize_currency function."""

    def test_normalize_currency_none(self) -> None:
        """Test that None returns default."""
        assert normalize_currency(None, default="EUR") == "EUR"

    def test_normalize_currency_empty_string(self) -> None:
        """Test that empty string returns default."""
        assert normalize_currency("", default="USD") == "USD"
        # Note: "   " after strip() becomes "", which is falsy, so returns default
        assert normalize_currency("   ", default="EUR") == "EUR"

    def test_normalize_currency_uppercase(self) -> None:
        """Test that currency is normalized to uppercase."""
        assert normalize_currency("eur", default="USD") == "EUR"
        assert normalize_currency("usd", default="EUR") == "USD"

    def test_normalize_currency_with_spaces(self) -> None:
        """Test that spaces are stripped."""
        assert normalize_currency("  EUR  ", default="USD") == "EUR"
        assert normalize_currency(" USD ", default="EUR") == "USD"

    def test_normalize_currency_already_uppercase(self) -> None:
        """Test that already uppercase currency is preserved."""
        assert normalize_currency("EUR", default="USD") == "EUR"
        assert normalize_currency("USD", default="EUR") == "USD"


class TestNormalizeUnit:
    """Tests for normalize_unit function."""

    def test_normalize_unit_none(self) -> None:
        """Test that None returns None."""
        assert normalize_unit(None) is None

    def test_normalize_unit_empty_string(self) -> None:
        """Test that empty string returns None."""
        assert normalize_unit("") is None
        assert normalize_unit("   ") is None

    def test_normalize_unit_standard_units(self) -> None:
        """Test normalization of standard units."""
        assert normalize_unit("g") == "g"
        assert normalize_unit("kg") == "kg"
        assert normalize_unit("ml") == "ml"
        assert normalize_unit("l") == "l"
        assert normalize_unit("pcs") == "pcs"

    def test_normalize_unit_case_insensitive(self) -> None:
        """Test that unit normalization is case-insensitive."""
        assert normalize_unit("G") == "g"
        assert normalize_unit("KG") == "kg"
        assert normalize_unit("ML") == "ml"
        assert normalize_unit("L") == "l"
        assert normalize_unit("PCS") == "pcs"

    def test_normalize_unit_with_spaces(self) -> None:
        """Test that spaces are stripped."""
        assert normalize_unit("  g  ") == "g"
        assert normalize_unit(" kg ") == "kg"

    def test_normalize_unit_aliases(self) -> None:
        """Test normalization of unit aliases."""
        assert normalize_unit("gram") == "g"
        assert normalize_unit("grams") == "g"
        assert normalize_unit("pc") == "pcs"
        assert normalize_unit("piece") == "pcs"
        assert normalize_unit("pieces") == "pcs"

    def test_normalize_unit_unknown_returns_lowercase(self) -> None:
        """Test that unknown units are returned as lowercase."""
        assert normalize_unit("UNKNOWN") == "unknown"
        assert normalize_unit("custom_unit") == "custom_unit"
