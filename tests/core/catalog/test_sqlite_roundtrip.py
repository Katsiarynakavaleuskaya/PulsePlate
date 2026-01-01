# -*- coding: utf-8 -*-
"""
SQLite catalog snapshot roundtrip tests (PR-7).

RU: Тесты для записи и чтения каталога через SQLite.
EN: Tests for catalog snapshot write/read roundtrip via SQLite.

These tests verify that snapshots can be written to SQLite and read back correctly,
with proper Decimal preservation, index usage, and alias lookup.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.services.catalog_provider_sqlite import SQLiteCatalogProvider
from core.catalog.provider import CatalogRegion, CatalogSKU, CatalogSnapshot, CatalogStore
from core.catalog.storage.sqlite_writer import write_snapshot


def test_sqlite_roundtrip_alias_lookup(tmp_path: Path) -> None:
    """Test that alias lookup works after roundtrip through SQLite."""
    path = tmp_path / "catalog.sqlite"

    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_1",
                store_id="carrefour_es_main",
                ean="841000000001",
                name="Olive Oil",
                brand="Carrefour",
                aisle="Aceites",
                package_size=Decimal("1"),
                unit="l",
                price=Decimal("6.99"),
                currency="EUR",
                updated_at="2026-01-01",
            )
        ],
        aliases=[("olive_oil_1l", "sku_1")],
    )

    write_snapshot(path, snapshot)

    provider = SQLiteCatalogProvider(str(path))
    catalog = provider.get_catalog_info(
        food_id="olive_oil_1l",
        region_id="ES",
        store_id="carrefour_es_main",
    )

    assert catalog is not None
    assert catalog.sku == "sku_1"
    assert catalog.store_id == "carrefour_es_main"
    assert catalog.region_id == "ES"
    assert catalog.price is not None
    assert catalog.price.value == Decimal("6.99")
    assert catalog.price.currency.value == "EUR"


def test_sqlite_roundtrip_decimal_preservation(tmp_path: Path) -> None:
    """Test that Decimal values are preserved exactly through SQLite roundtrip."""
    path = tmp_path / "catalog.sqlite"

    # Use precise decimal values that would lose precision with float
    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="US", country="US", currency="USD", locale="en-US")],
        stores=[
            CatalogStore(
                store_id="walmart_us_main",
                region_id="US",
                name="Walmart (US)",
                provider="walmart",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_decimal",
                store_id="walmart_us_main",
                ean=None,
                name="Test Product",
                brand=None,
                aisle=None,
                package_size=Decimal("0.123456789"),
                unit="kg",
                price=Decimal("99.999999"),
                currency="USD",
                updated_at=None,
            )
        ],
        aliases=[("test_product", "sku_decimal")],
    )

    write_snapshot(path, snapshot)

    provider = SQLiteCatalogProvider(str(path))
    catalog = provider.get_catalog_info(
        food_id="test_product",
        region_id="US",
        store_id="walmart_us_main",
    )

    assert catalog is not None
    assert catalog.price is not None
    # Verify exact decimal preservation (no float conversion)
    assert catalog.price.value == Decimal("99.999999")
    assert str(catalog.price.value) == "99.999999"


def test_sqlite_writer_rejects_duplicate_alias(tmp_path: Path) -> None:
    """Test that writer rejects duplicate aliases in same region (fail-fast)."""
    path = tmp_path / "catalog.sqlite"

    # Snapshot with duplicate alias in same region
    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_1",
                store_id="carrefour_es_main",
                ean=None,
                name="Product 1",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            ),
            CatalogSKU(
                sku_id="sku_2",
                store_id="carrefour_es_main",
                ean=None,
                name="Product 2",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            ),
        ],
        aliases=[
            ("duplicate_alias", "sku_1"),
            ("duplicate_alias", "sku_2"),  # Duplicate in same region
        ],
    )

    with pytest.raises(ValueError, match="Duplicate alias"):
        write_snapshot(path, snapshot)


def test_sqlite_writer_rejects_unknown_store_id(tmp_path: Path) -> None:
    """Test that writer rejects SKU with unknown store_id (fail-fast)."""
    path = tmp_path / "catalog.sqlite"

    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_orphan",
                store_id="unknown_store",  # Store not in snapshot
                ean=None,
                name="Orphan Product",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            )
        ],
        aliases=[("orphan_alias", "sku_orphan")],
    )

    with pytest.raises(ValueError, match="Unknown store_id"):
        write_snapshot(path, snapshot)


def test_sqlite_writer_rejects_unknown_sku_id_in_alias(tmp_path: Path) -> None:
    """Test that writer rejects alias with unknown sku_id (fail-fast)."""
    path = tmp_path / "catalog.sqlite"

    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_1",
                store_id="carrefour_es_main",
                ean=None,
                name="Product 1",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            )
        ],
        aliases=[
            ("valid_alias", "sku_1"),
            ("orphan_alias", "unknown_sku_id"),  # SKU not in snapshot
        ],
    )

    with pytest.raises(ValueError, match="Unknown sku_id"):
        write_snapshot(path, snapshot)
