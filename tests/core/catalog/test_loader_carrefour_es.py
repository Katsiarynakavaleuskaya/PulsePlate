# -*- coding: utf-8 -*-
"""
Tests for Carrefour ES catalog loader (PR-7).

RU: Тесты для загрузчика каталога Carrefour ES.
EN: Tests for Carrefour ES catalog loader.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from core.catalog.loaders.carrefour_es import CarrefourESLoader


def test_carrefour_loader_loads_snapshot(fixtures_dir: Path) -> None:
    """Test that Carrefour loader produces valid snapshot."""
    loader = CarrefourESLoader(fixtures_dir / "catalog_raw" / "carrefour_es_sample.csv")
    snapshot = loader.load()

    assert len(snapshot.regions) == 1
    assert snapshot.regions[0].region_id == "ES"
    assert snapshot.regions[0].currency == "EUR"
    assert len(snapshot.stores) >= 1
    assert len(snapshot.skus) >= 1
    assert len(snapshot.aliases) >= 1


def test_carrefour_loader_aliases_are_non_empty_and_unique(fixtures_dir: Path) -> None:
    """Test that aliases are non-empty and unique (data quality)."""
    loader = CarrefourESLoader(fixtures_dir / "catalog_raw" / "carrefour_es_sample.csv")
    snap = loader.load()

    alias_values = [a for a, _ in snap.aliases]
    # Validate aliases after stripping to catch whitespace-only aliases
    stripped_aliases = [a.strip() for a in alias_values]
    assert all(stripped_aliases), "All aliases must be non-empty after stripping"
    assert len(stripped_aliases) == len(
        set(stripped_aliases)
    ), "All aliases must be unique after stripping"
    assert all(sku.name.strip() for sku in snap.skus), "All SKU names must be non-empty"


def test_carrefour_loader_skus_have_decimal_prices(fixtures_dir: Path) -> None:
    """Test that prices are Decimal (not float)."""
    loader = CarrefourESLoader(fixtures_dir / "catalog_raw" / "carrefour_es_sample.csv")
    snapshot = loader.load()

    for sku in snapshot.skus:
        if sku.price is not None:
            assert isinstance(sku.price, Decimal), "Price must be Decimal type"
