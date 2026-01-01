# -*- coding: utf-8 -*-
"""
No-network guard tests for catalog providers (PR-7).

RU: Guard-тесты, гарантирующие отсутствие network I/O в runtime path.
EN: Guard tests ensuring no network I/O in runtime path.

These tests verify that catalog providers and loaders do not make network calls
during request-path operations (only during data preparation).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.catalog_adapter import build_default_mock_provider, enrich_shoplist_response
from app.services.catalog_provider_sqlite import SQLiteCatalogProvider
from app.schemas.vip_shoplist import PackedLineDTO, ShoplistGenerateResponse, UnpackedLineDTO
from tests.conftest import build_demo_catalog_sqlite, fixtures_dir


def test_mock_provider_no_network() -> None:
    """Test that MockCatalogProvider does not make network calls."""
    provider = build_default_mock_provider()

    # Mock socket to detect any network calls
    with patch("socket.socket") as mock_socket:
        catalog = provider.get_catalog_info(
            food_id="carrot",
            region_id="es",
            store_id="carrefour_es",
        )

        # Should not create any sockets
        mock_socket.assert_not_called()

        # Should return catalog info (or None)
        if catalog:
            assert isinstance(catalog, dict) or hasattr(catalog, "sku")
            assert (
                isinstance(catalog.sku, str)
                if hasattr(catalog, "sku")
                else isinstance(catalog.get("sku"), str)
            )


def test_sqlite_provider_no_network(
    tmp_path: Path,
    fixtures_dir: Path,
) -> None:
    """Test that SQLiteCatalogProvider does not make network calls."""
    # Build demo SQLite using helper from conftest
    db_path = tmp_path / "test.sqlite"
    build_demo_catalog_sqlite(db_path, fixtures_dir=fixtures_dir)

    provider = SQLiteCatalogProvider(str(db_path))

    # Mock socket to detect any network calls
    with patch("socket.socket") as mock_socket:
        catalog = provider.get_catalog_info(
            food_id="carrot",
            region_id="ES",
            store_id="carrefour_es_main",
        )

        # Should not create any sockets
        mock_socket.assert_not_called()

        # Should return catalog info (or None)
        if catalog:
            assert isinstance(catalog, dict) or hasattr(catalog, "sku")
            assert (
                isinstance(catalog.sku, str)
                if hasattr(catalog, "sku")
                else isinstance(catalog.get("sku"), str)
            )


def test_loaders_no_network_in_load(fixtures_dir: Path) -> None:
    """Test that loaders do not make network calls during load() (data prep phase)."""
    from core.catalog.loaders.carrefour_es import CarrefourESLoader
    from core.catalog.loaders.walmart_us import WalmartUSLoader

    carrefour_csv = fixtures_dir / "catalog_raw" / "carrefour_es_sample.csv"
    walmart_csv = fixtures_dir / "catalog_raw" / "walmart_us_sample.csv"

    loader_es = CarrefourESLoader(carrefour_csv)
    loader_us = WalmartUSLoader(walmart_csv)

    # Mock socket to detect any network calls
    with patch("socket.socket") as mock_socket:
        snapshot_es = loader_es.load()
        snapshot_us = loader_us.load()

        # Should not create any sockets
        mock_socket.assert_not_called()

        # Should return valid snapshots
        assert len(snapshot_es.regions) > 0
        assert len(snapshot_es.stores) > 0
        assert len(snapshot_us.regions) > 0
        assert len(snapshot_us.stores) > 0


def test_catalog_adapter_no_network() -> None:
    """Test that catalog adapter does not make network calls."""
    provider = build_default_mock_provider()

    # Create minimal response with correct DTO structure
    response = ShoplistGenerateResponse(
        packed=[
            PackedLineDTO(
                food_id="carrot",
                requested={"value": "500", "unit": "G"},
                pack_size={"value": "500", "unit": "G"},
                packs=1,
                provided={"value": "500", "unit": "G"},
                overage={"value": "0", "unit": "G"},
                rounding="CEIL",
                min_packs=1,
                reasons=[],
                catalog=None,
            )
        ],
        unpacked=[],
        analytics=None,
    )

    # Mock socket to detect any network calls
    with patch("socket.socket") as mock_socket:
        enriched = enrich_shoplist_response(
            response,
            region_id="es",
            store_id="carrefour_es",
            provider=provider,
        )

        # Should not create any sockets
        mock_socket.assert_not_called()

        # Should return enriched response
        assert len(enriched.packed) == len(response.packed)
        packed_item = enriched.packed[0]
        assert "catalog" in packed_item.model_dump() or hasattr(packed_item, "catalog")
        # Catalog field may be None or populated (fail-soft)
        catalog = packed_item.catalog
        assert catalog is None or isinstance(catalog, dict) or hasattr(catalog, "sku")
