# -*- coding: utf-8 -*-
"""
Integration tests for optional catalog enrichment in VIP shoplist endpoints.

RU: Интеграционные тесты для опционального catalog enrichment.
EN: Integration tests for optional catalog enrichment.
"""

from __future__ import annotations

# NOTE: Always use client_with_vip_access for VIP endpoints to avoid leaking
# dependency_overrides (API key + tier gating) across the test session.
# The fixture properly handles both VIP tier and route-level API key dependencies
# and cleans up overrides in teardown.

from typing import Any, Mapping

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import _enable_vip


def _generate_payload_minimal(*, food_id: str = "carrot") -> dict[str, Any]:
    """Minimal valid payload for shoplist generation."""
    return {
        "items": [
            {
                "food_id": food_id,
                "qty": {"value": "100", "unit": "G"},
                "form": "RAW",
            }
        ],
        "packaging_rules": [
            {
                "food_id": food_id,
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }


def _force_mock_catalog_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Force deterministic catalog provider for tests.

    RU: Принудительно используем mock provider, чтобы тесты не зависели от env/SQLite снапшотов.
    EN: Force mock provider so tests are not coupled to env/SQLite snapshots.
    """
    from app.services.catalog_adapter import reset_catalog_provider_for_tests

    monkeypatch.setenv("CATALOG_PROVIDER", "mock")
    reset_catalog_provider_for_tests()


def _assert_catalog_fields(
    catalog: Mapping[str, Any],
    *,
    region_id: str,
    store_id: str,
    sku: str | None = None,
) -> None:
    assert catalog["region_id"] == region_id, (
        f"catalog['region_id'] expected {region_id!r}, got {catalog.get('region_id')!r}"
    )
    assert catalog["store_id"] == store_id, (
        f"catalog['store_id'] expected {store_id!r}, got {catalog.get('store_id')!r}"
    )
    if sku is not None:
        assert "sku" in catalog, (
            f"catalog missing 'sku' key; expected sku={sku!r} (catalog keys={list(catalog.keys())})"
        )
        assert catalog["sku"] == sku, f"catalog['sku'] expected {sku!r}, got {catalog.get('sku')!r}"


def test_generate_without_region_store_has_no_catalog(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that without region_id/store_id, catalog field is None."""
    _enable_vip(monkeypatch)

    # client_with_vip_access fixture handles VIP tier and API key overrides
    client = client_with_vip_access

    r = client.post("/api/v1/vip/shoplist/generate", json=_generate_payload_minimal())
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert data["packed"], data
    # Catalog field always present in schema; null when not enriched
    packed_item = data["packed"][0]
    assert "catalog" in packed_item
    assert packed_item["catalog"] is None


def test_generate_with_region_store_attaches_catalog_when_food_found(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that with region_id/store_id, catalog is attached when found."""
    _enable_vip(monkeypatch)
    _force_mock_catalog_provider(monkeypatch)

    # client_with_vip_access fixture handles VIP tier and API key overrides
    client = client_with_vip_access

    r = client.post(
        "/api/v1/vip/shoplist/generate?region_id=es&store_id=carrefour_es",
        json=_generate_payload_minimal(),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    packed_item = data["packed"][0]
    # Contract: catalog field always present in schema; enrichment is fail-soft.
    assert "catalog" in packed_item
    catalog = packed_item["catalog"]
    assert catalog is not None
    _assert_catalog_fields(
        catalog,
        region_id="es",
        store_id="carrefour_es",
        sku="CRF-ES-000123",
    )


def test_generate_with_region_store_returns_null_catalog_when_food_unknown(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Explicitly validates fail-soft branch: catalog key exists but value may be null."""
    _enable_vip(monkeypatch)
    _force_mock_catalog_provider(monkeypatch)

    client = client_with_vip_access

    r = client.post(
        "/api/v1/vip/shoplist/generate?region_id=es&store_id=carrefour_es",
        json=_generate_payload_minimal(food_id="not_in_mock_catalog"),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert "packed" in data
    assert data["packed"], data

    packed_item = data["packed"][0]
    assert packed_item["food_id"] == "not_in_mock_catalog"
    assert "catalog" in packed_item
    assert packed_item["catalog"] is None


def test_daily_with_enrichment_attaches_catalog_when_food_found(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that /daily endpoint applies enrichment when params provided."""
    _enable_vip(monkeypatch)
    _force_mock_catalog_provider(monkeypatch)

    # client_with_vip_access fixture handles VIP tier and API key overrides
    client = client_with_vip_access

    r = client.post(
        "/api/v1/vip/shoplist/daily?region_id=es&store_id=carrefour_es",
        json=_generate_payload_minimal(),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert "packed" in data
    packed_item = data["packed"][0]
    # Contract: catalog field always present in schema; enrichment is fail-soft (covered separately).
    assert "catalog" in packed_item
    catalog = packed_item["catalog"]
    assert catalog is not None
    _assert_catalog_fields(catalog, region_id="es", store_id="carrefour_es")


def test_daily_with_enrichment_returns_null_catalog_when_food_unknown(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Explicitly validates fail-soft branch: catalog key exists but value may be null."""
    _enable_vip(monkeypatch)
    _force_mock_catalog_provider(monkeypatch)

    client = client_with_vip_access

    r = client.post(
        "/api/v1/vip/shoplist/daily?region_id=es&store_id=carrefour_es",
        json=_generate_payload_minimal(food_id="not_in_mock_catalog"),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    assert "packed" in data
    assert data["packed"], data

    packed_item = data["packed"][0]
    assert packed_item["food_id"] == "not_in_mock_catalog"
    assert "catalog" in packed_item
    assert packed_item["catalog"] is None


def test_generate_with_uppercase_region_id_normalizes_to_lowercase(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that region_id is normalized to lowercase in catalog response."""
    _enable_vip(monkeypatch)
    _force_mock_catalog_provider(monkeypatch)

    # client_with_vip_access fixture handles VIP tier and API key overrides
    client = client_with_vip_access

    # Pass uppercase region_id
    r = client.post(
        "/api/v1/vip/shoplist/generate?region_id=ES&store_id=carrefour_es",
        json=_generate_payload_minimal(),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    packed_item = data["packed"][0]
    assert "catalog" in packed_item
    catalog = packed_item["catalog"]
    # Verify catalog is attached to test normalization
    assert catalog is not None, "Expected catalog to be attached to verify normalization"
    _assert_catalog_fields(catalog, region_id="es", store_id="carrefour_es")


def test_generate_with_uppercase_store_id_normalizes_to_lowercase(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that store_id is normalized to lowercase in catalog response."""
    _enable_vip(monkeypatch)
    _force_mock_catalog_provider(monkeypatch)

    client = client_with_vip_access

    r = client.post(
        "/api/v1/vip/shoplist/generate?region_id=es&store_id=CARREFOUR_ES",
        json=_generate_payload_minimal(),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    packed_item = data["packed"][0]
    assert "catalog" in packed_item
    catalog = packed_item["catalog"]
    assert catalog is not None, "Expected catalog to be attached to verify normalization"
    _assert_catalog_fields(catalog, region_id="es", store_id="carrefour_es")
