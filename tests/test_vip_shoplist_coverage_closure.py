# -*- coding: utf-8 -*-
"""Coverage closure tests for VIP shoplist router.

RU: Тесты для закрытия coverage защитных веток в роутере.
EN: Tests to close coverage for defensive branches in router.

These tests directly exercise defensive code paths that are not reached
by integration tests (e.g., mapper exception handlers, VIP module check).
"""

from __future__ import annotations

from decimal import Decimal
from types import ModuleType

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

import app.main as app_main_module
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
