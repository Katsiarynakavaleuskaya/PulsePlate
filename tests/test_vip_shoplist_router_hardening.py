# -*- coding: utf-8 -*-
"""Router hardening tests for VIP shoplist endpoints.

RU: Fail-fast тесты — invalid input не должен доходить до engine.
EN: Fail-fast and standardized error behavior tests.

This test suite ensures all error paths (422/404/401/403/500) are properly
handled and return controlled, predictable responses.
"""

from __future__ import annotations

from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from core.shoplist_engine.models import FoodRef, PackPlan, Quantity, Unit
from core.shoplist_engine.packager import PackagingResult
from tests.helpers.module_resolve import resolve_module


def _enable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable VIP module flag via router module patch."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)


def _disable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable VIP module flag via router module patch."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: False)


def _payload_one_item(
    *,
    unit: str = "KG",
    form: str = "RAW",
) -> dict[str, Any]:
    """Minimal valid payload with one item and packaging rule."""
    return {
        "items": [
            {"food_id": "flour", "qty": {"value": "1.0", "unit": unit}, "form": form},
        ],
        "packaging_rules": [
            {
                "food_id": "flour",
                "pack_size": {"value": "1000", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }


def test_generate_invalid_unit_returns_422(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid unit value should return 422 (Pydantic validation at DTO level)."""
    _enable_vip(monkeypatch)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "INVALID_UNIT"}, "form": "RAW"},
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text
    data = r.json()
    # Pydantic validates at DTO level - check error structure
    errors = data.get("detail", [])
    assert isinstance(errors, list)
    assert any(
        "unit" in str(err.get("loc", [])).lower() or "unit" in str(err.get("msg", "")).lower()
        for err in errors
    )


def test_generate_invalid_rounding_returns_422(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid rounding value should return 422 (Pydantic validation at DTO level)."""
    _enable_vip(monkeypatch)

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
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text
    data = r.json()
    # Pydantic validates at DTO level - check error structure
    errors = data.get("detail", [])
    assert isinstance(errors, list)
    assert any(
        "rounding" in str(err.get("loc", [])).lower()
        or "rounding" in str(err.get("msg", "")).lower()
        for err in errors
    )


def test_generate_invalid_form_returns_422(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid form value should return 422 (Pydantic validation at DTO level)."""
    _enable_vip(monkeypatch)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "INVALID_FORM"},
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text
    data = r.json()
    # Pydantic validates at DTO level - check error structure
    errors = data.get("detail", [])
    assert isinstance(errors, list)
    assert any(
        "form" in str(err.get("loc", [])).lower() or "form" in str(err.get("msg", "")).lower()
        for err in errors
    )


def test_generate_min_packs_zero_returns_422(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """min_packs=0 should be rejected by Pydantic validation (ge=1)."""
    _enable_vip(monkeypatch)

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
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text
    data = r.json()
    # Pydantic validation error should mention min_packs constraint
    errors = data.get("detail", [])
    assert isinstance(errors, list)
    assert any(
        "min_packs" in str(err.get("loc", [])).lower()
        or "greater than or equal to 1" in str(err.get("msg", "")).lower()
        for err in errors
    )


def test_generate_empty_food_id_returns_422(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty food_id should be rejected by Pydantic validation (min_length=1)."""
    _enable_vip(monkeypatch)

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
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text
    data = r.json()
    errors = data.get("detail", [])
    assert isinstance(errors, list)
    assert any("food_id" in str(err.get("loc", [])).lower() for err in errors)


def test_generate_negative_quantity_returns_422(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative quantity value should be rejected by Pydantic validation (ge=0)."""
    _enable_vip(monkeypatch)

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
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text
    data = r.json()
    errors = data.get("detail", [])
    assert isinstance(errors, list)
    assert any(
        "greater than or equal to 0" in str(err.get("msg", "")).lower()
        or "value" in str(err.get("loc", [])).lower()
        for err in errors
    )


def test_generate_vip_module_disabled_returns_404(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VIP module disabled (feature flag off) should return 404."""
    _disable_vip(monkeypatch)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ]
    }

    # client_with_vip_access bypasses VIP tier, but require_vip_module_enabled
    # should still check the feature flag and return 404
    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text
    data = r.json()
    assert "not found" in str(data["detail"]).lower()


def test_generate_missing_api_key_returns_401_or_403(
    app_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Missing API key should return 401 or 403.

    RU: Проверяем, что require_vip_tier реально работает.
    EN: Verify that require_vip_tier is enforced.
    Статус может быть 401 или 403 — не фиксируем жёстко.
    """
    _enable_vip(monkeypatch)
    app_main_module = resolve_module("app.main")

    # Create client WITHOUT VIP access (no dependency override)
    client = TestClient(app_main_module.app)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "G"}, "form": "RAW"},
        ]
    }

    r = client.post("/api/v1/vip/shoplist/generate", json=payload)
    # VIP = feature-gate, returns 403
    assert (
        r.status_code == status.HTTP_403_FORBIDDEN
    ), f"Expected 403, got {r.status_code}: {r.text}"
    data = r.json()
    detail = str(data.get("detail", ""))
    detail_lower = detail.lower()
    assert "vip access" in detail_lower


def test_generate_invalid_api_key_tier_returns_403(
    app_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid API key (insufficient tier) should return 403 Forbidden."""
    _enable_vip(monkeypatch)
    app_main_module = resolve_module("app.main")

    # Create client WITHOUT VIP access override
    client = TestClient(app_main_module.app)

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
    assert r.status_code == status.HTTP_403_FORBIDDEN, r.text
    data = r.json()
    # legacy_app may return generic "Invalid API Key" or specific tier message
    detail = str(data.get("detail", ""))
    detail_lower = detail.lower()
    assert "api key" in detail_lower or "vip" in detail_lower or "invalid" in detail_lower


def test_generate_missing_items_field_returns_200_with_empty_result(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing 'items' field uses default_factory=list, returns 200 with empty result."""
    _enable_vip(monkeypatch)

    payload = {}  # Missing 'items' field (defaults to [])

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    # items has default_factory=list, so empty list is valid
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["packed"] == []
    assert data["unpacked"] == []
    # Verify analytics for empty input
    assert data["analytics"]["total_lines"] == 0
    assert data["analytics"]["packed_lines"] == 0
    assert data["analytics"]["unpacked_lines"] == 0
    assert data["analytics"]["total_overage_by_unit"] == {}


def test_generate_empty_items_list_returns_200(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty items list should return 200 with empty packed/unpacked (edge case)."""
    _enable_vip(monkeypatch)

    payload = {
        "items": [],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["packed"] == []
    assert data["unpacked"] == []
    assert data["analytics"]["total_lines"] == 0
    assert data["analytics"]["packed_lines"] == 0
    assert data["analytics"]["unpacked_lines"] == 0
    assert data["analytics"]["total_overage_by_unit"] == {}


# --- Fail-fast tests: engine must not be called on invalid input ---


@pytest.mark.parametrize(
    "patch_field,bad_value",
    [
        ("unit", "INVALID"),
        ("form", "NOT_A_FORM"),
        ("rounding", "WRONG"),
    ],
)
def test_generate_invalid_input_returns_422_and_engine_not_called(
    patch_field: str,
    bad_value: str,
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid input -> 422; engine must not be invoked (fail-fast)."""
    _enable_vip(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Engine must not be called on invalid input")

    monkeypatch.setattr(
        "app.routers.vip_shoplist.ShoplistEngine.generate",
        fail_if_called,
    )

    payload = _payload_one_item()
    if patch_field == "unit":
        payload["items"][0]["qty"]["unit"] = bad_value
    elif patch_field == "form":
        payload["items"][0]["form"] = bad_value
    elif patch_field == "rounding":
        payload["packaging_rules"][0]["rounding"] = bad_value

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)

    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_generate_min_packs_zero_returns_422_dto_validation_and_engine_not_called(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """min_packs=0 should fail DTO validation -> 422; engine must not be invoked."""
    _enable_vip(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Engine must not be called on invalid DTO")

    monkeypatch.setattr(
        "app.routers.vip_shoplist.ShoplistEngine.generate",
        fail_if_called,
    )

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

    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
