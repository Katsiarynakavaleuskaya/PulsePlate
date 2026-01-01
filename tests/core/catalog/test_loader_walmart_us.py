# -*- coding: utf-8 -*-
"""
Tests for Walmart US catalog loader (PR-7).

RU: Тесты для загрузчика каталога Walmart US.
EN: Tests for Walmart US catalog loader.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from core.catalog.loaders.walmart_us import WalmartUSLoader


def test_walmart_loader_loads_snapshot(fixtures_dir: Path) -> None:
    """Test that Walmart loader produces valid snapshot."""
    loader = WalmartUSLoader(fixtures_dir / "catalog_raw" / "walmart_us_sample.csv")
    snapshot = loader.load()

    assert len(snapshot.regions) == 1
    assert snapshot.regions[0].region_id == "US"
    assert snapshot.regions[0].currency == "USD"
    assert len(snapshot.stores) >= 1
    assert len(snapshot.skus) >= 1
    assert len(snapshot.aliases) >= 1


def test_walmart_loader_aliases_are_non_empty_and_unique(fixtures_dir: Path) -> None:
    """Test that aliases are non-empty and unique (data quality)."""
    loader = WalmartUSLoader(fixtures_dir / "catalog_raw" / "walmart_us_sample.csv")
    snap = loader.load()

    alias_values = [a for a, _ in snap.aliases]
    assert all(alias_values), "All aliases must be non-empty"
    assert len(alias_values) == len(set(alias_values)), "All aliases must be unique"
    assert all(sku.name.strip() for sku in snap.skus), "All SKU names must be non-empty"


def test_walmart_loader_skus_have_decimal_prices(fixtures_dir: Path) -> None:
    """Test that prices are Decimal (not float)."""
    loader = WalmartUSLoader(fixtures_dir / "catalog_raw" / "walmart_us_sample.csv")
    snapshot = loader.load()

    for sku in snapshot.skus:
        if sku.price is not None:
            assert isinstance(sku.price, Decimal), "Price must be Decimal type"
