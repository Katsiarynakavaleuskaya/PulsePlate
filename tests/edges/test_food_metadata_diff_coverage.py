"""Diff-coverage smoke tests for bounded food metadata passthrough."""

from __future__ import annotations

from core.food_sources.base import (
    first_gtin_value,
    first_metadata_value,
    normalize_optional_gtin,
    normalize_optional_metadata,
)
from core.food_sources.off import OFFAdapter
from core.food_sources.usda import USDAAdapter


def test_food_metadata_helpers_cover_blank_fallbacks_and_ascii_gtin() -> None:
    """Shared metadata helpers keep blank/null values out and GTINs ASCII-only."""

    assert normalize_optional_metadata(None) is None
    assert normalize_optional_metadata(" null ") is None
    assert normalize_optional_metadata(" Brand ") == "Brand"
    assert normalize_optional_gtin(None) is None
    assert normalize_optional_gtin("nan") is None
    assert normalize_optional_gtin(" 0-12 ٣٤-56 ") == "01256"
    assert first_metadata_value({"a": " ", "b": "null", "c": "Chosen"}, ("a", "b", "c")) == "Chosen"
    assert first_metadata_value({"a": None}, ("a", "b")) is None
    assert first_gtin_value({"a": "abc", "b": " 00-12 "}, ("a", "b")) == "0012"
    assert first_gtin_value({"a": "abc", "b": None}, ("a", "b")) is None


def test_usda_and_off_metadata_assignments_are_in_fast_coverage(
    monkeypatch,
) -> None:
    """The CI fast lane should exercise adapter metadata assignment lines."""

    usda = USDAAdapter(csv_path="/tmp/unused.csv")
    monkeypatch.setattr(
        usda,
        "fetch",
        lambda: [
            {
                "description": "Granola Bar",
                "fdcId": " 234567 ",
                "brandName": " Test Foods ",
                "upc": "00 123-456 78905",
            }
        ],
    )

    usda_food = next(iter(usda.normalize()))
    assert usda_food.fdc_id == "234567"
    assert usda_food.brand == "Test Foods"
    assert usda_food.gtin == "0012345678905"

    off = OFFAdapter(csv_path="/tmp/unused.csv")
    monkeypatch.setattr(
        off,
        "fetch",
        lambda: [
            {
                "product_name": "Chocolate Bar",
                "brands_en": " ChocoCorp ",
                "barcode": "0 301-7620422003",
            }
        ],
    )

    off_food = next(iter(off.normalize()))
    assert off_food.brand == "ChocoCorp"
    assert off_food.gtin == "03017620422003"
    assert off_food.fdc_id is None
