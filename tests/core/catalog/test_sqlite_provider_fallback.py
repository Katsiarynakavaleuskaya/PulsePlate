# -*- coding: utf-8 -*-
"""
Store-aware lookup fallback tests for SQLite catalog provider (PR-7).

RU: Тесты для fallback логики в store-aware lookup.
EN: Tests for fallback logic in store-aware lookup.

These tests verify that when store_id is provided but no exact match exists,
the provider falls back to any matching SKU (deterministic behavior).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.services.catalog_provider_sqlite import SQLiteCatalogProvider
from core.catalog.provider import CatalogRegion, CatalogSKU, CatalogSnapshot, CatalogStore
from core.catalog.storage.sqlite_writer import write_snapshot


def test_sqlite_provider_fallback_to_any_store_when_exact_match_not_found(
    tmp_path: Path,
) -> None:
    """
    RU: Проверяем fallback: если store_id задан, но точного совпадения нет,
        возвращаем любой SKU для этого alias (детерминированно).
    EN: Verify fallback: when store_id provided but no exact match,
        return any SKU for this alias (deterministic).
    """
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with SKU in different store
    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            ),
            CatalogStore(
                store_id="walmart_es_main",
                region_id="ES",
                name="Walmart (ES)",
                provider="walmart",
            ),
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_carrefour",
                store_id="carrefour_es_main",
                ean=None,
                name="Milk 1L",
                brand=None,
                aisle="Dairy",
                package_size=Decimal("1"),
                unit="l",
                price=Decimal("2.99"),
                currency="EUR",
                updated_at=None,
            ),
            CatalogSKU(
                sku_id="sku_walmart",
                store_id="walmart_es_main",
                ean=None,
                name="Milk 1L",
                brand=None,
                aisle="Dairy",
                package_size=Decimal("1"),
                unit="l",
                price=Decimal("2.49"),
                currency="EUR",
                updated_at=None,
            ),
        ],
        aliases=[
            ("milk_carrefour", "sku_carrefour"),
            ("milk_walmart", "sku_walmart"),
        ],
    )

    write_snapshot(db_path, snapshot)
    provider = SQLiteCatalogProvider(str(db_path))

    # Act: lookup with store_id that doesn't match any SKU
    # Should fallback to any matching SKU (deterministic by sku_id ASC)
    info = provider.get_catalog_info(
        food_id="milk_carrefour",
        region_id="ES",
        store_id="unknown_store",  # Store doesn't exist, should fallback
    )

    # Assert: should return a SKU (fallback behavior)
    assert info is not None
    assert info.sku == "sku_carrefour"


def test_sqlite_provider_prefers_exact_store_match(tmp_path: Path) -> None:
    """
    RU: Проверяем, что точное совпадение store_id имеет приоритет.
    EN: Verify that exact store_id match has priority.
    """
    db_path = tmp_path / "catalog.sqlite"

    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="US", country="US", currency="USD", locale="en-US")],
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
                sku_id="sku_a",
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
                sku_id="sku_b",
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
            ("product_a", "sku_a"),
            ("product_b", "sku_b"),
        ],
    )

    write_snapshot(db_path, snapshot)
    provider = SQLiteCatalogProvider(str(db_path))

    # Act: lookup with exact store_id match
    info = provider.get_catalog_info(
        food_id="product_a",
        region_id="US",
        store_id="store_a",
    )

    # Assert: should prefer exact match (store_a)
    assert info is not None
    assert info.sku == "sku_a"
    assert info.store_id == "store_a"
