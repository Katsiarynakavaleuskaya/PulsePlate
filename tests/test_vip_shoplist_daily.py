# -*- coding: utf-8 -*-
"""Tests for VIP shoplist daily endpoint.

RU: Тесты для endpoint /api/v1/vip/shoplist/daily.
EN: Tests for /api/v1/vip/shoplist/daily endpoint.

This test suite ensures daily endpoint matches /generate contract:
- Same gating (VIP_MODULE_ENABLED, VIP tier)
- Same mapping (invalid enum → 422)
- Same response format (reasons + analytics)
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import status
from fastapi.testclient import TestClient


def _enable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable VIP module flag via router module patch."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)


def _disable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable VIP module flag via router module patch."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: False)


def _payload_one_item() -> dict:
    """Minimal valid payload with one item and packaging rule."""
    return {
        "items": [
            {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "chicken",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }


def test_daily_success_200_deterministic(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daily endpoint should return 200 with deterministic results (same as /generate)."""
    _enable_vip(monkeypatch)

    payload = _payload_one_item()
    r = client_with_vip_access.post("/api/v1/vip/shoplist/daily", json=payload)

    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()

    # Verify response structure matches /generate
    assert "packed" in data
    assert "unpacked" in data
    assert "analytics" in data

    # Verify deterministic results
    assert len(data["packed"]) == 1
    assert data["packed"][0]["food_id"] == "chicken"
    assert data["packed"][0]["packs"] == 3  # ceil(1200/500) = 3
    assert "reasons" in data["packed"][0]
    assert len(data["packed"][0]["reasons"]) > 0

    # Verify analytics
    assert data["analytics"]["total_lines"] == 1
    assert data["analytics"]["packed_lines"] == 1
    assert data["analytics"]["unpacked_lines"] == 0


def test_daily_vip_module_disabled_returns_404(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VIP module disabled (feature flag off) should return 404."""
    _disable_vip(monkeypatch)

    payload = _payload_one_item()
    r = client_with_vip_access.post("/api/v1/vip/shoplist/daily", json=payload)

    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text
    data = r.json()
    assert "not found" in str(data["detail"]).lower()


def test_daily_missing_api_key_returns_401_or_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing API key should return 401 or 403."""
    from fastapi.testclient import TestClient

    import app.main as app_main_module

    _enable_vip(monkeypatch)

    # Create client WITHOUT VIP access (no dependency override)
    client = TestClient(app_main_module.app)

    payload = _payload_one_item()
    r = client.post("/api/v1/vip/shoplist/daily", json=payload)

    # legacy_app may return 401 or 403 depending on implementation
    assert r.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ), f"Expected 401 or 403, got {r.status_code}: {r.text}"


def test_daily_empty_items_returns_200(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty items list should return 200 with empty result."""
    _enable_vip(monkeypatch)

    payload = {"items": []}
    r = client_with_vip_access.post("/api/v1/vip/shoplist/daily", json=payload)

    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["packed"] == []
    assert data["unpacked"] == []
    assert data["analytics"]["total_lines"] == 0
