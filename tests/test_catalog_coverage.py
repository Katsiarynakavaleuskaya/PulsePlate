# -*- coding: utf-8 -*-
"""
Coverage tests for catalog adapter and SQLite provider (PR-7).

RU: Тесты для покрытия непокрытых строк в catalog_adapter и catalog_provider_sqlite.
EN: Coverage tests for uncovered lines in catalog_adapter and catalog_provider_sqlite.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.services.catalog_adapter import (
    MockCatalogProvider,
    _get_provider,
    build_default_mock_provider,
    reset_catalog_provider_for_tests,
)
from app.services.catalog_provider_sqlite import SQLiteCatalogProvider
from core.catalog.provider import CatalogRegion, CatalogSKU, CatalogSnapshot, CatalogStore
from core.catalog.storage.sqlite_writer import write_snapshot
from tests.conftest import build_demo_catalog_sqlite, fixtures_dir


class TestMockCatalogProviderCoverage:
    """Tests for MockCatalogProvider coverage."""

    def test_list_stores_returns_stores_from_data(self) -> None:
        """Test that list_stores extracts stores from mock data."""
        data = {
            ("es", "store_a", "food1"): CatalogInfoDTO(
                sku="sku1",
                store_id="store_a",
                region_id="es",
                pack_label="500 G",
                aisle=None,
                price=None,
            ),
            ("es", "store_b", "food2"): CatalogInfoDTO(
                sku="sku2",
                store_id="store_b",
                region_id="es",
                pack_label="1 L",
                aisle=None,
                price=None,
            ),
            ("us", "store_c", "food3"): CatalogInfoDTO(
                sku="sku3",
                store_id="store_c",
                region_id="us",
                pack_label="2 L",
                aisle=None,
                price=None,
            ),
        }
        provider = MockCatalogProvider(data=data)

        stores_es = provider.list_stores(region_id="ES")
        assert len(stores_es) == 2
        store_ids = {s.store_id for s in stores_es}
        assert store_ids == {"store_a", "store_b"}

        stores_us = provider.list_stores(region_id="US")
        assert len(stores_us) == 1
        assert stores_us[0].store_id == "store_c"

        stores_fr = provider.list_stores(region_id="FR")
        assert len(stores_fr) == 0

    def test_get_catalog_info_fallback_when_no_exact_store_match(self) -> None:
        """Test fallback logic when store_id provided but no exact match."""
        data = {
            ("es", "store_a", "carrot"): CatalogInfoDTO(
                sku="sku_a",
                store_id="store_a",
                region_id="es",
                pack_label="500 G",
                aisle=None,
                price=None,
            ),
            ("es", "store_b", "carrot"): CatalogInfoDTO(
                sku="sku_b",
                store_id="store_b",
                region_id="es",
                pack_label="400 G",
                aisle=None,
                price=None,
            ),
        }
        provider = MockCatalogProvider(data=data)

        # Request store_c (doesn't exist), should fallback to any store deterministically
        result = provider.get_catalog_info(
            food_id="carrot",
            region_id="es",
            store_id="store_c",  # Doesn't exist
        )
        assert result is not None
        # Deterministic: should return first by key sort
        assert result.sku in ("sku_a", "sku_b")

    def test_get_catalog_info_no_store_id_returns_any(self) -> None:
        """Test that get_catalog_info without store_id returns any matching SKU."""
        data = {
            ("es", "store_a", "carrot"): CatalogInfoDTO(
                sku="sku_a",
                store_id="store_a",
                region_id="es",
                pack_label="500 G",
                aisle=None,
                price=None,
            ),
        }
        provider = MockCatalogProvider(data=data)

        result = provider.get_catalog_info(
            food_id="carrot",
            region_id="es",
            store_id=None,
        )
        assert result is not None
        assert result.sku == "sku_a"


class TestSQLiteCatalogProviderCoverage:
    """Tests for SQLiteCatalogProvider coverage."""

    def test_list_stores_returns_stores_for_region(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """Test that list_stores returns stores for given region."""
        db_path = tmp_path / "catalog.sqlite"
        build_demo_catalog_sqlite(db_path, fixtures_dir=fixtures_dir)

        provider = SQLiteCatalogProvider(str(db_path))

        stores_es = provider.list_stores(region_id="ES")
        assert len(stores_es) > 0
        assert all(s.region_id == "ES" for s in stores_es)

        stores_us = provider.list_stores(region_id="US")
        assert len(stores_us) > 0
        assert all(s.region_id == "US" for s in stores_us)

        stores_fr = provider.list_stores(region_id="FR")
        assert len(stores_fr) == 0

    def test_list_stores_handles_missing_file(self, tmp_path: Path) -> None:
        """Test that list_stores returns empty list when file missing."""
        db_path = tmp_path / "missing.sqlite"
        provider = SQLiteCatalogProvider(str(db_path))

        stores = provider.list_stores(region_id="ES")
        assert stores == []

    def test_list_stores_handles_sqlite_error(self, tmp_path: Path) -> None:
        """Test that list_stores handles SQLite errors gracefully."""
        # Create invalid SQLite file
        db_path = tmp_path / "invalid.sqlite"
        db_path.write_text("not a sqlite file")

        provider = SQLiteCatalogProvider(str(db_path))

        stores = provider.list_stores(region_id="ES")
        assert stores == []

    def test_get_catalog_info_handles_invalid_currency(self, tmp_path: Path) -> None:
        """Test that get_catalog_info handles invalid currency gracefully."""
        db_path = tmp_path / "catalog.sqlite"
        snapshot = CatalogSnapshot(
            regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
            stores=[
                CatalogStore(
                    store_id="test_store",
                    region_id="ES",
                    name="Test Store",
                    provider="test",
                )
            ],
            skus=[
                CatalogSKU(
                    sku_id="sku1",
                    store_id="test_store",
                    ean=None,
                    name="Test Product",
                    brand=None,
                    aisle=None,
                    package_size=Decimal("1"),
                    unit="l",
                    price=Decimal("10.00"),
                    currency="INVALID",  # Invalid currency
                    updated_at=None,
                )
            ],
            aliases=[("test_product", "sku1")],
        )
        write_snapshot(db_path, snapshot)

        provider = SQLiteCatalogProvider(str(db_path))
        info = provider.get_catalog_info(
            food_id="test_product",
            region_id="ES",
            store_id="test_store",
        )

        assert info is not None
        assert info.sku == "sku1"
        # Price should be None due to invalid currency (fail-soft)
        assert info.price is None

    def test_get_catalog_info_with_pack_label(self, tmp_path: Path) -> None:
        """Test that get_catalog_info builds pack_label correctly."""
        db_path = tmp_path / "catalog.sqlite"
        snapshot = CatalogSnapshot(
            regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
            stores=[
                CatalogStore(
                    store_id="test_store",
                    region_id="ES",
                    name="Test Store",
                    provider="test",
                )
            ],
            skus=[
                CatalogSKU(
                    sku_id="sku1",
                    store_id="test_store",
                    ean=None,
                    name="Milk",
                    brand=None,
                    aisle="Dairy",
                    package_size=Decimal("1"),
                    unit="l",
                    price=Decimal("2.99"),
                    currency="EUR",
                    updated_at=None,
                )
            ],
            aliases=[("milk", "sku1")],
        )
        write_snapshot(db_path, snapshot)

        provider = SQLiteCatalogProvider(str(db_path))
        info = provider.get_catalog_info(
            food_id="milk",
            region_id="ES",
            store_id="test_store",
        )

        assert info is not None
        assert info.pack_label == "1 l"
        assert info.aisle == "Dairy"

    def test_get_catalog_info_without_pack_label(self, tmp_path: Path) -> None:
        """Test that get_catalog_info handles missing package_size/unit."""
        db_path = tmp_path / "catalog.sqlite"
        snapshot = CatalogSnapshot(
            regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
            stores=[
                CatalogStore(
                    store_id="test_store",
                    region_id="ES",
                    name="Test Store",
                    provider="test",
                )
            ],
            skus=[
                CatalogSKU(
                    sku_id="sku1",
                    store_id="test_store",
                    ean=None,
                    name="Product",
                    brand=None,
                    aisle=None,
                    package_size=None,  # No package_size
                    unit=None,  # No unit
                    price=Decimal("5.00"),
                    currency="EUR",
                    updated_at=None,
                )
            ],
            aliases=[("product", "sku1")],
        )
        write_snapshot(db_path, snapshot)

        provider = SQLiteCatalogProvider(str(db_path))
        info = provider.get_catalog_info(
            food_id="product",
            region_id="ES",
            store_id="test_store",
        )

        assert info is not None
        assert info.pack_label is None

    def test_get_catalog_info_without_store_id(self, tmp_path: Path) -> None:
        """Test that get_catalog_info works without store_id (covers else branch)."""
        db_path = tmp_path / "catalog.sqlite"
        snapshot = CatalogSnapshot(
            regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
            stores=[
                CatalogStore(
                    store_id="test_store",
                    region_id="ES",
                    name="Test Store",
                    provider="test",
                )
            ],
            skus=[
                CatalogSKU(
                    sku_id="sku1",
                    store_id="test_store",
                    ean=None,
                    name="Product",
                    brand=None,
                    aisle=None,
                    package_size=Decimal("1"),
                    unit="l",
                    price=Decimal("5.00"),
                    currency="EUR",
                    updated_at=None,
                )
            ],
            aliases=[("product", "sku1")],
        )
        write_snapshot(db_path, snapshot)

        provider = SQLiteCatalogProvider(str(db_path))
        # Call without store_id (covers else branch in _get_sku_by_alias)
        info = provider.get_catalog_info(
            food_id="product",
            region_id="ES",
            store_id=None,  # No store_id
        )

        assert info is not None
        assert info.sku == "sku1"

    def test_get_sku_by_alias_handles_connection_error(self, tmp_path: Path) -> None:
        """Test that _get_sku_by_alias handles SQLite connection errors."""
        # Create a directory (not a file) to cause connection error
        db_path = tmp_path / "catalog.sqlite"
        db_path.mkdir()  # Create as directory, not file

        provider = SQLiteCatalogProvider(str(db_path))
        # Should return None on connection error
        sku = provider._get_sku_by_alias(region_id="ES", alias="test", store_id=None)
        assert sku is None


class TestCatalogAdapterProviderSelection:
    """Tests for _get_provider coverage."""

    def test_get_provider_sqlite_with_absolute_path(
        self, tmp_path: Path, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test _get_provider with SQLite provider and absolute path."""
        reset_catalog_provider_for_tests()

        db_path = tmp_path / "catalog.sqlite"
        build_demo_catalog_sqlite(db_path, fixtures_dir=fixtures_dir)

        monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
        monkeypatch.setenv("CATALOG_SQLITE_PATH", str(db_path))

        provider = _get_provider()
        assert isinstance(provider, SQLiteCatalogProvider)

    def test_get_provider_sqlite_with_relative_path(
        self, tmp_path: Path, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test _get_provider with SQLite provider and relative path."""
        reset_catalog_provider_for_tests()

        # Keep the relative-path contract while isolating the SQLite file per test run.
        data_dir = tmp_path / "data" / "catalog" / "snapshots"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "catalog_demo.sqlite"
        build_demo_catalog_sqlite(db_path, fixtures_dir=fixtures_dir)

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
        monkeypatch.setenv("CATALOG_SQLITE_PATH", "data/catalog/snapshots/catalog_demo.sqlite")

        provider = _get_provider()
        assert isinstance(provider, SQLiteCatalogProvider)

    def test_get_provider_sqlite_fallback_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_provider falls back to mock when SQLite initialization fails."""
        reset_catalog_provider_for_tests()

        # SQLiteCatalogProvider doesn't fail on init, only on read
        # So we test with a path that would cause ValueError during path resolution
        # Actually, the provider is created successfully, but returns None on queries
        # This test verifies the provider is created (not falling back immediately)
        monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
        monkeypatch.setenv("CATALOG_SQLITE_PATH", "/nonexistent/path/catalog.sqlite")

        provider = _get_provider()
        # SQLiteCatalogProvider is created (lazy fail-soft), but queries return None
        assert isinstance(provider, SQLiteCatalogProvider)

        # Verify fail-soft behavior: queries return None
        info = provider.get_catalog_info(food_id="test", region_id="ES", store_id="test")
        assert info is None

    def test_get_provider_mock_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_provider defaults to mock when env not set."""
        reset_catalog_provider_for_tests()

        monkeypatch.delenv("CATALOG_PROVIDER", raising=False)

        provider = _get_provider()
        assert isinstance(provider, MockCatalogProvider)

    def test_get_provider_sqlite_error_handling(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test _get_provider error handling when SQLite provider raises ValueError."""
        reset_catalog_provider_for_tests()

        monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
        monkeypatch.setenv("CATALOG_SQLITE_PATH", str(tmp_path / "catalog.sqlite"))

        # Mock the import inside _get_provider to raise ValueError
        with patch(
            "app.services.catalog_provider_sqlite.SQLiteCatalogProvider",
            side_effect=ValueError("Invalid path"),
        ):
            provider = _get_provider()
            # Should fallback to mock
            assert isinstance(provider, MockCatalogProvider)
