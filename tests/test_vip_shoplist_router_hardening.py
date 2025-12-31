# -*- coding: utf-8 -*-
"""Router hardening tests for VIP shoplist endpoints.

RU: Тесты на обработку ошибок и валидацию в VIP shoplist роутере.
EN: Error handling and validation tests for VIP shoplist router.

This test suite ensures all error paths (422/404/401/403/500) are properly
handled and return controlled, predictable responses.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_generate_invalid_unit_returns_422(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid unit value should return 422 (Pydantic validation at DTO level)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "INVALID_UNIT"}, "form": "RAW"},
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 422, r.text
    data = r.json()
    # Pydantic validates at DTO level, so error mentions expected literals
    assert "unit" in str(data).lower() or "G" in str(data)


def test_generate_invalid_rounding_returns_422(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid rounding value should return 422 (Pydantic validation at DTO level)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "flour",
                "pack_size": {"value": "1000", "unit": "G"},
                "rounding": "INVALID_ROUNDING",
                "min_packs": 1,
            }
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 422, r.text
    data = r.json()
    # Pydantic validates at DTO level
    assert "rounding" in str(data).lower() or "CEIL" in str(data)


def test_generate_invalid_form_returns_422(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid form value should return 422 (Pydantic validation at DTO level)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "INVALID_FORM"},
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 422, r.text
    data = r.json()
    # Pydantic validates at DTO level
    assert "form" in str(data).lower() or "RAW" in str(data)


def test_generate_min_packs_zero_returns_422(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """min_packs=0 should be rejected by Pydantic validation (ge=1)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "flour",
                "pack_size": {"value": "1000", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 0,  # Invalid: must be >= 1
            }
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 422, r.text
    # Pydantic validation error should mention min_packs constraint
    data = r.json()
    assert "min_packs" in str(data).lower() or "greater than or equal to 1" in str(data).lower()


def test_generate_empty_food_id_returns_422(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty food_id should be rejected by Pydantic validation (min_length=1)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {
                "food_id": "",
                "qty": {"value": "1", "unit": "G"},
                "form": "RAW",
            },  # Invalid: empty string
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 422, r.text
    data = r.json()
    assert "food_id" in str(data).lower()


def test_generate_negative_quantity_returns_422(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative quantity value should be rejected by Pydantic validation (ge=0)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {
                "food_id": "flour",
                "qty": {"value": "-1", "unit": "G"},
                "form": "RAW",
            },  # Invalid: negative
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 422, r.text
    data = r.json()
    assert "greater than or equal to 0" in str(data).lower() or "value" in str(data).lower()


def test_generate_vip_module_disabled_returns_404(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VIP module disabled (feature flag off) should return 404."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: False)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 404, r.text
    data = r.json()
    assert data["detail"] == "Not Found"


def test_generate_missing_api_key_returns_403(
    app_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing API key should return 403 Forbidden (legacy_app handles it as 403)."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    # Create client WITHOUT VIP access (no dependency override)
    client = TestClient(app_module.app)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ]
    }

    r = client.post("/api/v1/vip/shoplist/generate", json=payload)
    # legacy_app returns 403 for missing/invalid API key
    assert r.status_code == 403, r.text
    data = r.json()
    assert "API key" in data["detail"].lower() or "Invalid" in data["detail"]


def test_generate_invalid_api_key_tier_returns_403(
    app_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid API key (insufficient tier) should return 403 Forbidden."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    # Create client WITHOUT VIP access override
    client = TestClient(app_module.app)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ]
    }

    # Use PRO key (insufficient for VIP endpoint)
    r = client.post(
        "/api/v1/vip/shoplist/generate",
        json=payload,
        headers={"X-API-Key": "test_pro_key"},
    )
    assert r.status_code == 403, r.text
    data = r.json()
    # legacy_app may return generic "Invalid API Key" or specific tier message
    assert (
        "API key" in data["detail"].lower()
        or "VIP" in data["detail"]
        or "Invalid" in data["detail"]
    )


def test_generate_missing_items_field_returns_200_with_empty_result(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing 'items' field uses default_factory=list, returns 200 with empty result."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {}  # Missing 'items' field (defaults to [])

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    # items has default_factory=list, so empty list is valid
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["packed"] == []
    assert data["unpacked"] == []


def test_generate_empty_items_list_returns_200(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty items list should return 200 with empty packed/unpacked (edge case)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["packed"] == []
    assert data["unpacked"] == []
    assert data["analytics"]["total_lines"] == 0
    assert data["analytics"]["packed_lines"] == 0
    assert data["analytics"]["unpacked_lines"] == 0
