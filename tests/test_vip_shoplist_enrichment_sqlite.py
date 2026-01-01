# -*- coding: utf-8 -*-
"""
VIP shoplist enrichment integration tests with SQLite provider (PR-7).

RU: Интеграционные тесты для enrichment с SQLite provider.
EN: Integration tests for enrichment with SQLite provider.

These tests verify that SQLiteCatalogProvider works correctly with VIP shoplist endpoints.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.services.catalog_adapter import reset_catalog_provider_for_tests
from tests.conftest import _enable_vip, build_demo_catalog_sqlite, client_with_vip_access, fixtures_dir


def _generate_payload_minimal() -> dict:
    """Minimal valid payload for shoplist generation."""
    return {
        "items": [
            {
                "food_id": "carrot",
                "qty": {"value": "100", "unit": "G"},
                "form": "RAW",
            }
        ],
        "packaging_rules": [
            {
                "food_id": "carrot",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }


def test_vip_shoplist_generate_enriches_catalog_with_sqlite(
    tmp_path: Path,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """
    RU: Проверяем, что при SQLite provider enrichment не ломает ответ и добавляет catalog.
    EN: Ensure SQLite provider enriches catalog optionally and never breaks contract.
    """
    _enable_vip(monkeypatch)

    # 1) Build demo SQLite from fixtures
    db_path = tmp_path / "catalog_demo.sqlite"
    build_demo_catalog_sqlite(db_path, fixtures_dir=fixtures_dir)

    # 2) Enable SQLite provider
    monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
    monkeypatch.setenv("CATALOG_SQLITE_PATH", str(db_path))

    # 3) Reset provider cache to pick up new env vars
    reset_catalog_provider_for_tests()

    # 4) Re-import vip_shoplist module to get new provider
    import importlib
    import app.routers.vip_shoplist

    importlib.reload(app.routers.vip_shoplist)

    client = client_with_vip_access

    # 5) Call /generate with region_id/store_id query params
    # Use "carrot" which should match alias in fixtures
    payload = _generate_payload_minimal()
    r = client.post(
        "/api/v1/vip/shoplist/generate",
        json=payload,
        params={"region_id": "ES", "store_id": "carrefour_es_main"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert data["packed"], data

    # 6) Contract: catalog field always present
    packed_item = data["packed"][0]
    assert "catalog" in packed_item, "Contract: field `catalog` must always be present"

    # 7) For known food_id (carrot) in fixtures, catalog should be enriched
    # Note: fixtures use "carrot" as alias, so it should match
    assert packed_item["catalog"] is not None, "Expected catalog enrichment for known food_id"
    assert packed_item["catalog"]["sku"] is not None
    assert packed_item["catalog"]["region_id"] == "ES"
    assert packed_item["catalog"]["store_id"] == "carrefour_es_main"


def test_vip_shoplist_generate_fail_soft_for_unknown_food_id(
    tmp_path: Path,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """
    RU: Проверяем fail-soft: неизвестный food_id возвращает catalog=null, но не ломает ответ.
    EN: Verify fail-soft: unknown food_id returns catalog=null but doesn't break response.
    """
    _enable_vip(monkeypatch)

    # 1) Build demo SQLite from fixtures
    db_path = tmp_path / "catalog_demo.sqlite"
    build_demo_catalog_sqlite(db_path, fixtures_dir=fixtures_dir)

    # 2) Enable SQLite provider
    monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
    monkeypatch.setenv("CATALOG_SQLITE_PATH", str(db_path))

    # 3) Reset provider cache
    reset_catalog_provider_for_tests()

    # 4) Re-import vip_shoplist module
    import importlib
    import app.routers.vip_shoplist

    importlib.reload(app.routers.vip_shoplist)

    client = client_with_vip_access

    # 5) Use unknown food_id that doesn't exist in fixtures
    payload = {
        "items": [
            {
                "food_id": "unknown_item_xyz",
                "qty": {"value": "100", "unit": "G"},
                "form": "RAW",
            }
        ],
        "packaging_rules": [
            {
                "food_id": "unknown_item_xyz",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }

    r = client.post(
        "/api/v1/vip/shoplist/generate",
        json=payload,
        params={"region_id": "ES", "store_id": "carrefour_es_main"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert data["packed"], data

    # 6) Contract: catalog field always present, but null for unknown food_id
    packed_item = data["packed"][0]
    assert "catalog" in packed_item, "Contract: field `catalog` must always be present"
    assert packed_item["catalog"] is None, "Expected catalog=null for unknown food_id (fail-soft)"
