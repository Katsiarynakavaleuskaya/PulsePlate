# -*- coding: utf-8 -*-
"""Coverage closure tests for VIP shoplist router.

RU: Тесты для закрытия coverage защитных веток в роутере.
EN: Tests to close coverage for defensive branches in router.

These tests directly exercise defensive code paths that are not reached
by integration tests (e.g., mapper exception handlers, VIP module check).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from core.shoplist_engine.models import FoodRef, PackPlan, Quantity, Unit
from core.shoplist_engine.packager import PackagingResult

# --- Mapper functions: direct exception handler coverage ---


@pytest.mark.parametrize(
    "mapper_func,bad_value",
    [
        ("_map_unit", "INVALID_UNIT"),
        ("_map_rounding", "INVALID_ROUNDING"),
        ("_map_form", "INVALID_FORM"),
    ],
)
def test_mapper_functions_raise_422_on_invalid_input(
    mapper_func: str,
    bad_value: str,
) -> None:
    """Mapper functions raise 422 on invalid input (defense-in-depth coverage)."""
    from app.routers import vip_shoplist

    mapper = getattr(vip_shoplist, mapper_func)

    with pytest.raises(HTTPException) as exc_info:
        mapper(bad_value)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_value.lower() in exc_info.value.detail.lower()


# --- VIP module enabled check: direct function coverage ---


def test_require_vip_module_enabled_off_raises_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """require_vip_module_enabled raises 404 when VIP module is disabled."""
    from app.routers.vip_shoplist import require_vip_module_enabled

    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        lambda: False,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_vip_module_enabled()

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# --- Contract check: packed without rule → 500 ---


def test_generate_packed_without_rule_triggers_500(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packed item without corresponding packaging rule should return 500 (contract violation)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    def mock_generate(*_args, **_kwargs) -> PackagingResult:
        return PackagingResult(
            packed=[
                PackPlan(
                    food=FoodRef(food_id="flour"),
                    requested=Quantity(Decimal("100"), Unit.G),
                    pack_size=Quantity(Decimal("100"), Unit.G),
                    packs=1,
                    provided=Quantity(Decimal("100"), Unit.G),
                    overage=Quantity(Decimal("0"), Unit.G),
                )
            ],
            unpacked=[],
        )

    monkeypatch.setattr("app.routers.vip_shoplist.ShoplistEngine.generate", mock_generate)

    # No packaging_rules provided -> rules_index empty -> must hit 500 branch.
    r = client_with_vip_access.post(
        "/api/v1/vip/shoplist/generate",
        json={
            "items": [{"food_id": "flour", "qty": {"value": "100", "unit": "G"}, "form": "RAW"}],
            "packaging_rules": [],
        },
    )

    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert isinstance(r.json().get("detail"), str)
    assert "missing packaging rule" in r.json()["detail"].lower()


# --- Preview endpoint: direct coverage ---


def test_vip_shoplist_preview_endpoint_coverage(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preview endpoint should return 200 with items list (coverage closure)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    r = client_with_vip_access.get("/api/v1/vip/shoplist/preview")

    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert isinstance(body.get("items"), list)


# --- Additional coverage for helper functions ---


def test_generate_with_multiple_packed_items_different_units(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _sum_overage_by_unit with multiple packed items (different units) - coverage for lines 119-120."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    # Request with multiple items that will be packed with different units
    payload = {
        "items": [
            {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"},
            {"food_id": "milk", "qty": {"value": "1500", "unit": "ML"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "chicken",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "milk",
                "pack_size": {"value": "1000", "unit": "ML"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()

    # Verify analytics has overage totals for both units
    assert "analytics" in data
    assert "total_overage_by_unit" in data["analytics"]
    overage_by_unit = data["analytics"]["total_overage_by_unit"]
    # Should have overage for both G and ML
    assert len(overage_by_unit) >= 1  # At least one unit has overage


def test_build_shoplist_response_without_analytics() -> None:
    """Test _build_shoplist_response with include_analytics=False - coverage for branch 247->257."""
    from app.routers import vip_shoplist
    from core.shoplist_engine.models import (
        FoodRef,
        PackPlan,
        PackageRule,
        Quantity,
        RoundingMode,
        Unit,
    )
    from core.shoplist_engine.packager import PackagingResult

    # Create minimal result
    result = PackagingResult(
        packed=[
            PackPlan(
                food=FoodRef(food_id="chicken"),
                requested=Quantity(Decimal("1200"), Unit.G),
                pack_size=Quantity(Decimal("500"), Unit.G),
                packs=3,
                provided=Quantity(Decimal("1500"), Unit.G),
                overage=Quantity(Decimal("300"), Unit.G),
            )
        ],
        unpacked=[],
    )

    rules = [
        PackageRule(
            food_id="chicken",
            pack_size=Quantity(Decimal("500"), Unit.G),
            rounding=RoundingMode.CEIL,
            min_packs=1,
        )
    ]

    # Call with include_analytics=False
    response = vip_shoplist._build_shoplist_response(result, rules, include_analytics=False)

    # Verify response structure
    assert response.packed is not None
    assert response.unpacked is not None
    # Analytics should be None when include_analytics=False
    assert response.analytics is None


def test_build_shoplist_response_raises_500_when_package_rule_missing() -> None:
    """
    RU: Adapter обязан падать с 500, если packed item не имеет PackageRule.
    EN: Adapter must raise 500 when packed item has no matching PackageRule.

    This is an invariant violation: engine returned "packed", but adapter
    cannot find the corresponding packaging rule. This is NOT a user error → 500.
    """
    from app.routers import vip_shoplist

    # Create result with packed item that has NO matching rule
    result = PackagingResult(
        packed=[
            PackPlan(
                food=FoodRef(food_id="missing-food-id"),
                requested=Quantity(Decimal("1200"), Unit.G),
                pack_size=Quantity(Decimal("500"), Unit.G),
                packs=3,
                provided=Quantity(Decimal("1500"), Unit.G),
                overage=Quantity(Decimal("300"), Unit.G),
            )
        ],
        unpacked=[],
    )

    # Deliberately empty rules (missing-food-id has no rule)
    rules: list[vip_shoplist.PackageRule] = []

    with pytest.raises(HTTPException) as exc_info:
        vip_shoplist._build_shoplist_response(result, rules, include_analytics=False)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "missing packaging rule" in exc_info.value.detail.lower()
    assert "missing-food-id" in exc_info.value.detail


def test_generate_with_packaging_rules_not_none(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test branch when packaging_rules is not None - coverage for line 168."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [  # Not None - should hit line 168
            {
                "food_id": "flour",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert len(data["packed"]) == 1
    assert data["packed"][0]["food_id"] == "flour"
    # Verify _build_reasons was called (coverage for line 98)
    assert "reasons" in data["packed"][0]
    assert len(data["packed"][0]["reasons"]) > 0


def test_generate_with_multiple_packed_items_same_unit(
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test multiple packed items to cover loop branch (line 187->186)."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"},
            {"food_id": "rice", "qty": {"value": "2000", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "chicken",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "rice",
                "pack_size": {"value": "1000", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    # Should have 2 packed items
    assert len(data["packed"]) == 2
    # Both should have reasons (coverage for _build_reasons line 98)
    for packed_item in data["packed"]:
        assert "reasons" in packed_item
        assert len(packed_item["reasons"]) > 0
