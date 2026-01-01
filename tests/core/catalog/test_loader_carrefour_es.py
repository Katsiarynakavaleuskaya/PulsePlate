# -*- coding: utf-8 -*-
"""
Tests for Carrefour ES catalog loader (PR-7).

RU: Тесты для загрузчика каталога Carrefour ES.
EN: Tests for Carrefour ES catalog loader.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    assert all(alias_values), "All aliases must be non-empty"
    assert len(alias_values) == len(set(alias_values)), "All aliases must be unique"
    assert all(sku.name.strip() for sku in snap.skus), "All SKU names must be non-empty"


def test_carrefour_loader_skus_have_decimal_prices(fixtures_dir: Path) -> None:
    """Test that prices are Decimal (not float)."""
    loader = CarrefourESLoader(fixtures_dir / "catalog_raw" / "carrefour_es_sample.csv")
    snapshot = loader.load()

    for sku in snapshot.skus:
        if sku.price is not None:
            assert isinstance(sku.price, type(snapshot.skus[0].price)), "Price must be Decimal type"
            # Verify it's not float (Decimal has different type)
            assert str(type(sku.price).__name__) == "Decimal" or hasattr(sku.price, "as_tuple"), "Price must be Decimal"

