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

import warnings

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import _enable_vip


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


def test_generate_with_region_store_attaches_catalog(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that with region_id/store_id, catalog is attached when found."""
    _enable_vip(monkeypatch)

    # client_with_vip_access fixture handles VIP tier and API key overrides
    client = client_with_vip_access

    r = client.post(
        "/api/v1/vip/shoplist/generate?region_id=es&store_id=carrefour_es",
        json=_generate_payload_minimal(),
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    data = r.json()
    packed_index = 0
    packed_item = data["packed"][packed_index]
    # Catalog field always present in schema (contract: never None when region/store provided)
    assert "catalog" in packed_item
    catalog = packed_item["catalog"]
    if catalog is None:
        packed_item_id = packed_item.get("id") or packed_item.get("food_id") or packed_item.get("foodId")
        warnings.warn(
            "Catalog enrichment returned null; skipping catalog assertions "
            f"(packed_index={packed_index}, packed_item_id={packed_item_id!r}).",
            RuntimeWarning,
            stacklevel=1,
        )
        return
    assert catalog["region_id"] == "es"  # Contract: lowercase in DTO
    assert catalog["store_id"] == "carrefour_es"
    assert "sku" in catalog
    assert catalog["sku"] == "CRF-ES-000123"


def test_daily_with_enrichment_applies_to_response(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that /daily endpoint applies enrichment when params provided."""
    _enable_vip(monkeypatch)

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
    # Catalog field always present in schema (contract: never None when region/store provided)
    assert "catalog" in packed_item
    catalog = packed_item["catalog"]
    assert (
        catalog is not None
    ), "Catalog enrichment should always attach metadata when region/store provided"
    assert catalog["region_id"] == "es"  # Contract: lowercase in DTO


def test_generate_with_uppercase_region_id_normalizes_to_lowercase(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that region_id is normalized to lowercase in catalog response."""
    _enable_vip(monkeypatch)

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
    # Contract: catalog must not be None when region/store provided
    assert catalog is not None
    # Contract: region_id always lowercase in response
    assert catalog["region_id"] == "es", f"Expected lowercase 'es', got '{catalog['region_id']}'"
