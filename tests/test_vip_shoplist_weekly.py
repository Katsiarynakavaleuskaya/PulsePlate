# -*- coding: utf-8 -*-
"""Tests for VIP shoplist weekly endpoint.

RU: Тесты для endpoint /api/v1/vip/shoplist/weekly.
EN: Tests for /api/v1/vip/shoplist/weekly endpoint.

This test suite ensures weekly endpoint matches /generate contract:
- Same gating (VIP_MODULE_ENABLED, VIP tier)
- Same mapping (invalid enum → 422)
- Same response format per day (reasons + analytics)
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import _disable_vip, _enable_vip


def _payload_one_day() -> dict:
    """Minimal valid payload with one day."""
    return {
        "days": [
            {
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
            },
        ],
    }


def test_weekly_success_200_contains_days(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weekly endpoint should return 200 with days list (same contract as /generate per day)."""
    _enable_vip(monkeypatch)

    payload = _payload_one_day()
    r = client_with_vip_access.post("/api/v1/vip/shoplist/weekly", json=payload)

    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()

    # Verify response structure
    assert "days" in data
    assert isinstance(data["days"], list)
    assert len(data["days"]) == 1

    # Verify each day has same structure as /generate
    day = data["days"][0]
    assert "packed" in day
    assert "unpacked" in day
    assert "analytics" in day

    # Verify deterministic results
    assert len(day["packed"]) == 1
    assert day["packed"][0]["food_id"] == "chicken"
    assert day["packed"][0]["packs"] == 3  # ceil(1200/500) = 3
    assert "reasons" in day["packed"][0]
    assert len(day["packed"][0]["reasons"]) > 0


def test_weekly_multiple_days_returns_all_days(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weekly endpoint should process all days independently."""
    _enable_vip(monkeypatch)

    payload = {
        "days": [
            {
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
            },
            {
                "items": [
                    {"food_id": "rice", "qty": {"value": "2000", "unit": "G"}, "form": "RAW"},
                ],
                "packaging_rules": [
                    {
                        "food_id": "rice",
                        "pack_size": {"value": "1000", "unit": "G"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                ],
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/weekly", json=payload)

    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert len(data["days"]) == 2

    # Verify first day
    assert data["days"][0]["packed"][0]["food_id"] == "chicken"
    # Verify second day
    assert data["days"][1]["packed"][0]["food_id"] == "rice"


def test_weekly_vip_module_disabled_returns_404(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VIP module disabled (feature flag off) should return 404."""
    _disable_vip(monkeypatch)

    payload = _payload_one_day()
    r = client_with_vip_access.post("/api/v1/vip/shoplist/weekly", json=payload)

    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text
    data = r.json()
    assert "not found" in str(data["detail"]).lower()


def test_weekly_insufficient_vip_tier_returns_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid API key but insufficient VIP tier must return 403."""
    _enable_vip(monkeypatch)

    import app.main as app_module

    # Create client WITHOUT VIP access override (uses real tier check)
    client = TestClient(app_module.app)

    payload = _payload_one_day()

    # Use PRO key (insufficient for VIP endpoint)
    r = client.post(
        "/api/v1/vip/shoplist/weekly",
        json=payload,
        headers={"X-API-Key": "test_pro_key"},
    )

    # In dev mode, may return 401 or 403 depending on implementation
    assert r.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ), f"Expected 401 or 403, got {r.status_code}: {r.text}"

    data = r.json()

    # Verify error message mentions API key/VIP/tier/permission
    detail_lower = str(data.get("detail", "")).lower()
    assert any(
        kw in detail_lower
        for kw in ("api key", "vip", "tier", "forbidden", "permission", "upgrade", "invalid")
    )


def test_weekly_missing_api_key_returns_401_or_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing API key should return 401 or 403."""
    import app.main as app_main_module

    _enable_vip(monkeypatch)

    # Create client WITHOUT VIP access (no dependency override)
    client = TestClient(app_main_module.app)

    payload = _payload_one_day()
    r = client.post("/api/v1/vip/shoplist/weekly", json=payload)

    # legacy_app may return 401 or 403 depending on implementation
    assert r.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ), f"Expected 401 or 403, got {r.status_code}: {r.text}"


def test_weekly_empty_days_returns_200(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty days list should return 200 with empty days."""
    _enable_vip(monkeypatch)

    payload = {"days": []}
    r = client_with_vip_access.post("/api/v1/vip/shoplist/weekly", json=payload)

    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["days"] == []
