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

from app.services.catalog_adapter import build_default_mock_provider
from app.services.catalog_provider_sqlite import SQLiteCatalogProvider
from core.catalog.loaders.carrefour_es import CarrefourESLoader
from core.catalog.loaders.walmart_us import WalmartUSLoader


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
        assert catalog is None or isinstance(catalog.sku, str)


def test_sqlite_provider_no_network(tmp_path: Path) -> None:
    """Test that SQLiteCatalogProvider does not make network calls."""
    from core.catalog.loaders.carrefour_es import CarrefourESLoader
    from core.catalog.storage.sqlite_writer import SQLiteCatalogWriter

    db_path = tmp_path / "test.sqlite"
    loader = CarrefourESLoader()
    snapshot = loader.load()
    writer = SQLiteCatalogWriter(db_path)
    writer.write(snapshot)

    provider = SQLiteCatalogProvider(db_path)

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
        assert catalog is None or isinstance(catalog.sku, str)


def test_loaders_no_network_in_load() -> None:
    """Test that loaders do not make network calls during load() (data prep phase)."""
    # Note: In PR-7, loaders are minimal and read from in-memory data.
    # In future PRs, they may read from CSV/JSON files, but still no network.

    loader_es = CarrefourESLoader()
    loader_us = WalmartUSLoader()

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
    from app.schemas.vip_shoplist import PackedLineDTO, ShoplistGenerateResponse, UnpackedLineDTO
    from app.services.catalog_adapter import enrich_shoplist_response

    provider = build_default_mock_provider()

    # Create minimal response
    response = ShoplistGenerateResponse(
        packed=[
            PackedLineDTO(
                food_id="carrot",
                quantity={"value": "500", "unit": "G"},
                packs=1,
                catalog=None,
            )
        ],
        unpacked=[],
        analytics={},
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

        # Should return enriched response (catalog field may be None or populated)
        assert hasattr(enriched.packed[0], 'catalog')
