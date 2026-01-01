# -*- coding: utf-8 -*-
"""
VIP shoplist enrichment integration tests with SQLite provider (PR-7).

RU: Интеграционные тесты для enrichment с SQLite provider.
EN: Integration tests for enrichment with SQLite provider.

These tests verify that SQLiteCatalogProvider works correctly with VIP shoplist endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.services.catalog_adapter import reset_catalog_provider_for_tests
from tests.conftest import (
    _enable_vip,
    build_demo_catalog_sqlite,
    client_with_vip_access,
    fixtures_dir,
)


def _generate_payload_minimal() -> dict[str, Any]:
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

    client = client_with_vip_access

    # 4) Call /generate with region_id/store_id query params
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

    # 5) Contract: catalog field always present
    packed_item = data["packed"][0]
    assert "catalog" in packed_item, "Contract: field `catalog` must always be present"

    # 6) For known food_id (carrot) in fixtures, catalog should be enriched
    # Note: fixtures use "carrot" as alias, so it should match
    catalog = packed_item["catalog"]
    assert catalog is not None, "Expected catalog enrichment for known food_id"
    assert isinstance(catalog, dict), "Catalog must be dict when enriched"
    assert "sku" in catalog and isinstance(catalog["sku"], str), "Catalog must have sku string"
    assert catalog["region_id"] == "es"  # Contract: lowercase in DTO
    assert catalog["store_id"] == "carrefour_es_main"


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

    client = client_with_vip_access

    # 4) Use unknown food_id that doesn't exist in fixtures
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

    # 5) Contract: catalog field always present, but null for unknown food_id
    packed_item = data["packed"][0]
    assert "catalog" in packed_item, "Contract: field `catalog` must always be present"
    catalog = packed_item["catalog"]
    assert catalog is None, "Expected catalog=null for unknown food_id (fail-soft)"


def test_vip_shoplist_generate_fail_soft_for_invalid_sqlite_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """
    RU: Проверяем fail-soft: битый/несуществующий SQLite файл не ломает endpoint.
    EN: Verify fail-soft: invalid/missing SQLite file doesn't break endpoint.
    """
    _enable_vip(monkeypatch)

    # 1) Create invalid SQLite file (text file, not SQLite)
    invalid_db_path = tmp_path / "invalid.sqlite"
    invalid_db_path.write_text("This is not a SQLite file", encoding="utf-8")

    # 2) Enable SQLite provider with invalid path
    monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
    monkeypatch.setenv("CATALOG_SQLITE_PATH", str(invalid_db_path))

    # 3) Reset provider cache
    reset_catalog_provider_for_tests()

    client = client_with_vip_access

    # 4) Call /generate - should still return 200 with catalog=null
    payload = _generate_payload_minimal()
    r = client.post(
        "/api/v1/vip/shoplist/generate",
        json=payload,
        params={"region_id": "ES", "store_id": "carrefour_es_main"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert data["packed"], data

    # 5) Contract: catalog field always present, but null when provider fails (fail-soft)
    packed_item = data["packed"][0]
    assert "catalog" in packed_item, "Contract: field `catalog` must always be present"
    catalog = packed_item["catalog"]
    assert catalog is None, "Expected catalog=null when SQLite file is invalid (fail-soft)"


def test_vip_shoplist_generate_fail_soft_for_missing_sqlite_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """
    RU: Проверяем fail-soft: отсутствующий SQLite файл не ломает endpoint.
    EN: Verify fail-soft: missing SQLite file doesn't break endpoint.
    """
    _enable_vip(monkeypatch)

    # 1) Use non-existent SQLite file path
    missing_db_path = tmp_path / "missing.sqlite"

    # 2) Enable SQLite provider with missing path
    monkeypatch.setenv("CATALOG_PROVIDER", "sqlite")
    monkeypatch.setenv("CATALOG_SQLITE_PATH", str(missing_db_path))

    # 3) Reset provider cache
    reset_catalog_provider_for_tests()

    client = client_with_vip_access

    # 4) Call /generate - should still return 200 with catalog=null
    payload = _generate_payload_minimal()
    r = client.post(
        "/api/v1/vip/shoplist/generate",
        json=payload,
        params={"region_id": "ES", "store_id": "carrefour_es_main"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert data["packed"], data

    # 5) Contract: catalog field always present, but null when file missing (fail-soft)
    packed_item = data["packed"][0]
    assert "catalog" in packed_item, "Contract: field `catalog` must always be present"
    catalog = packed_item["catalog"]
    assert catalog is None, "Expected catalog=null when SQLite file is missing (fail-soft)"
