# -*- coding: utf-8 -*-
"""
Integration tests for optional catalog enrichment in VIP shoplist endpoints.

RU: Интеграционные тесты для опционального catalog enrichment.
EN: Integration tests for optional catalog enrichment.
"""

from __future__ import annotations

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
    catalog = data["packed"][0].get("catalog")
    # Mock provider has carrot in es/carrefour_es, so catalog should be present
    assert catalog is not None
    assert catalog["region_id"] == "es"
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
    # Enrichment applied (catalog should be present for carrot in mock)
    catalog = data["packed"][0].get("catalog")
    assert catalog is not None
    assert catalog["region_id"] == "es"
