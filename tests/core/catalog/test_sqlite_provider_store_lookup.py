# -*- coding: utf-8 -*-
"""
Store-aware lookup tests for SQLite catalog provider (PR-7).

RU: Тесты для store-aware lookup в SQLite provider.
EN: Tests for store-aware lookup in SQLite provider.

These tests verify that store-specific SKUs are preferred over generic ones
when store_id is provided, with deterministic fallback behavior.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.services.catalog_provider_sqlite import SQLiteCatalogProvider
from core.catalog.provider import CatalogRegion, CatalogSKU, CatalogSnapshot, CatalogStore
from core.catalog.storage.sqlite_writer import write_snapshot


def test_store_aware_lookup_prefers_store_specific(tmp_path: Path) -> None:
    """Test that store-specific SKU is preferred when store_id is provided."""
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with:
    # - alias "milk" -> SKU_MILK_WALMART (store=walmart_us_main)
    # - alias "milk" -> SKU_MILK_GENERIC (store=carrefour_es_main)
    snapshot = CatalogSnapshot(
        regions=[
            CatalogRegion(region_id="US", country="US", currency="USD", locale="en-US")
        ],
        stores=[
            CatalogStore(
                store_id="walmart_us_main",
                region_id="US",
                name="Walmart (US)",
                provider="walmart",
            ),
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="US",  # Same region for test
                name="Carrefour (US)",
                provider="carrefour",
            ),
        ],
        skus=[
            CatalogSKU(
                sku_id="SKU_MILK_WALMART",
                store_id="walmart_us_main",
                ean=None,
                name="Milk Walmart",
                brand=None,
                aisle=None,
                package_size=Decimal("1"),
                unit="l",
                price=Decimal("2.99"),
                currency="USD",
                updated_at=None,
            ),
            CatalogSKU(
                sku_id="SKU_MILK_GENERIC",
                store_id="carrefour_es_main",
                ean=None,
                name="Milk Generic",
                brand=None,
                aisle=None,
                package_size=Decimal("1"),
                unit="l",
                price=Decimal("3.49"),
                currency="USD",
                updated_at=None,
            ),
        ],
        aliases=[
            ("milk", "SKU_MILK_WALMART"),
            ("milk", "SKU_MILK_GENERIC"),
        ],
    )

    write_snapshot(db_path, snapshot)
    provider = SQLiteCatalogProvider(str(db_path))

    # Act: store-aware lookup for walmart
    info = provider.get_catalog_info(
        food_id="milk",
        region_id="US",
        store_id="walmart_us_main",
    )

    # Assert: should prefer walmart-specific SKU
    assert info is not None
    assert info.store_id == "walmart_us_main"
    assert info.sku == "SKU_MILK_WALMART"


def test_store_aware_lookup_fallback_to_any_store(tmp_path: Path) -> None:
    """Test that lookup falls back to any store when exact match not found."""
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with only one SKU for alias
    snapshot = CatalogSnapshot(
        regions=[
            CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")
        ],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            ),
        ],
        skus=[
            CatalogSKU(
                sku_id="SKU_BREAD",
                store_id="carrefour_es_main",
                ean=None,
                name="Bread",
                brand=None,
                aisle=None,
                package_size=Decimal("500"),
                unit="g",
                price=Decimal("1.50"),
                currency="EUR",
                updated_at=None,
            ),
        ],
        aliases=[("bread", "SKU_BREAD")],
    )

    write_snapshot(db_path, snapshot)
    provider = SQLiteCatalogProvider(str(db_path))

    # Act: lookup with different store_id (should fallback to any)
    info = provider.get_catalog_info(
        food_id="bread",
        region_id="ES",
        store_id="unknown_store",  # Store doesn't exist, should fallback
    )

    # Assert: should return the only available SKU (fallback)
    assert info is not None
    assert info.sku == "SKU_BREAD"
    assert info.store_id == "carrefour_es_main"


def test_store_aware_lookup_deterministic_when_no_store_id(tmp_path: Path) -> None:
    """Test that lookup is deterministic when store_id is not provided."""
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with multiple SKUs for same alias
    snapshot = CatalogSnapshot(
        regions=[
            CatalogRegion(region_id="US", country="US", currency="USD", locale="en-US")
        ],
        stores=[
            CatalogStore(
                store_id="store_a",
                region_id="US",
                name="Store A",
                provider="provider_a",
            ),
            CatalogStore(
                store_id="store_b",
                region_id="US",
                name="Store B",
                provider="provider_b",
            ),
        ],
        skus=[
            CatalogSKU(
                sku_id="SKU_A",
                store_id="store_a",
                ean=None,
                name="Product A",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="USD",
                updated_at=None,
            ),
            CatalogSKU(
                sku_id="SKU_B",
                store_id="store_b",
                ean=None,
                name="Product B",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="USD",
                updated_at=None,
            ),
        ],
        aliases=[
            ("product", "SKU_A"),
            ("product", "SKU_B"),
        ],
    )

    write_snapshot(db_path, snapshot)
    provider = SQLiteCatalogProvider(str(db_path))

    # Act: lookup without store_id (should be deterministic)
    info1 = provider.get_catalog_info(food_id="product", region_id="US", store_id=None)
    info2 = provider.get_catalog_info(food_id="product", region_id="US", store_id=None)

    # Assert: should return same SKU (deterministic by ORDER BY sku_id ASC)
    assert info1 is not None
    assert info2 is not None
    assert info1.sku == info2.sku  # Deterministic
    assert info1.sku == "SKU_A"  # First by sku_id ASC

