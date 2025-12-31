# -*- coding: utf-8 -*-
"""Tests for VIP shoplist explainability (reasons for packed/unpacked lines).

RU: Тесты для explainability VIP списка покупок (причины упаковки/неупаковки).
EN: Tests for VIP shoplist explainability (reasons for packed/unpacked lines).

These tests verify that the explainability layer (reasons) is correctly
added to packed and unpacked lines without modifying core engine logic.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest

from app.schemas.vip_shoplist import REASON_NO_PACKAGING_RULE

if TYPE_CHECKING:
    from core.shoplist_engine.packager import PackagingResult


def _enable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable VIP module flag via router module patch."""
    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        lambda: True,
    )


def _mock_engine_result_with_one_packed_one_unpacked() -> PackagingResult:
    """
    RU: Возвращаем реальный core-модельный результат, чтобы роутер прошёл свой mapping как в проде.
    EN: Return real core model objects to exercise router mapping (adapter-only tests).
    """
    from core.shoplist_engine.models import (
        FoodRef,
        PackPlan,
        Quantity,
        ShoplistLine,
        Unit,
    )
    from core.shoplist_engine.packager import PackagingResult

    return PackagingResult(
        packed=[
            PackPlan(
                food=FoodRef(food_id="flour"),
                requested=Quantity(Decimal("1800"), Unit.G),
                pack_size=Quantity(Decimal("1000"), Unit.G),
                packs=2,
                provided=Quantity(Decimal("2000"), Unit.G),
                overage=Quantity(Decimal("200"), Unit.G),
            )
        ],
        unpacked=[
            ShoplistLine(
                food=FoodRef(food_id="salt"),
                qty=Quantity(Decimal("10"), Unit.G),
            )
        ],
    )


def _payload_one_rule() -> dict[str, Any]:
    """RU: Держим payload минимальным, но валидным для текущего request DTO."""
    return {
        "items": [
            {"food_id": "flour", "qty": {"value": "1.8", "unit": "KG"}, "form": "RAW"},
            {"food_id": "salt", "qty": {"value": "10", "unit": "G"}, "form": "RAW"},
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


def _extract_packed_and_unpacked(data: dict) -> tuple[list[dict], list[dict]]:
    """
    RU: На всякий случай поддерживаем оба ключа ответа:
        - packed/unpacked
        - packed_lines/unpacked_lines
    """
    packed = data.get("packed", data.get("packed_lines", []))
    unpacked = data.get("unpacked", data.get("unpacked_lines", []))
    assert isinstance(packed, list), "packed must be a list"
    assert isinstance(unpacked, list), "unpacked must be a list"
    return packed, unpacked


def test_generate_returns_reasons_for_packed_lines(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that packed lines include reasons."""
    _enable_vip(monkeypatch)

    mock_result = _mock_engine_result_with_one_packed_one_unpacked()

    def mock_generate(specs, packaging_rules=None):
        return mock_result

    monkeypatch.setattr(
        "app.routers.vip_shoplist.ShoplistEngine.generate",
        mock_generate,
    )

    r = client_with_vip_access.post(
        "/api/v1/vip/shoplist/generate",
        json=_payload_one_rule(),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    packed, _ = _extract_packed_and_unpacked(data)
    assert len(packed) >= 1

    p0 = packed[0]
    assert "reasons" in p0
    assert isinstance(p0["reasons"], list)
    assert len(p0["reasons"]) > 0

    reasons = p0["reasons"]
    assert any(str(x).startswith("rounding=") for x in reasons)
    assert any(str(x).startswith("min_packs=") for x in reasons)
    assert any(str(x).startswith("overage=") for x in reasons)


def test_generate_sets_reason_for_unpacked_lines(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that unpacked lines include reason."""
    _enable_vip(monkeypatch)

    mock_result = _mock_engine_result_with_one_packed_one_unpacked()

    def mock_generate(specs, packaging_rules=None):
        return mock_result

    monkeypatch.setattr(
        "app.routers.vip_shoplist.ShoplistEngine.generate",
        mock_generate,
    )

    r = client_with_vip_access.post(
        "/api/v1/vip/shoplist/generate",
        json=_payload_one_rule(),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    _, unpacked = _extract_packed_and_unpacked(data)
    assert len(unpacked) >= 1

    u0 = unpacked[0]
    assert u0.get("reason") == REASON_NO_PACKAGING_RULE


def test_generate_reasons_are_deterministic(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that reasons are deterministic (same input -> same output)."""
    _enable_vip(monkeypatch)

    mock_result = _mock_engine_result_with_one_packed_one_unpacked()

    def mock_generate(specs, packaging_rules=None):
        return mock_result

    monkeypatch.setattr(
        "app.routers.vip_shoplist.ShoplistEngine.generate",
        mock_generate,
    )

    payload = _payload_one_rule()

    r1 = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r1.status_code == 200, r1.text
    j1 = r1.json()

    r2 = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r2.status_code == 200, r2.text
    j2 = r2.json()

    # RU: В этом endpoint не должно быть случайных полей (timestamps/ids) → строгое равенство.
    assert j1 == j2

    packed, _ = _extract_packed_and_unpacked(j1)
    assert len(packed) >= 1
    reasons = packed[0]["reasons"]

    # RU: Если в роутере зафиксируешь порядок reasons — это цементируем.
    assert reasons[0].startswith("rounding=")
    assert reasons[1].startswith("min_packs=")

