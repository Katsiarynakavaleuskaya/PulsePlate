# -*- coding: utf-8 -*-
"""Tests for VIP shoplist analytics (overage totals).

RU: Тесты для аналитики перерасхода (overage) в VIP shoplist generate.
EN: Tests for waste/overage analytics in VIP shoplist generate.

These tests verify that analytics is computed in the adapter layer (router)
based on the core engine result, without modifying core logic.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from core.shoplist_engine.packager import PackagingResult


def _enable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable VIP module flag via router module patch."""
    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        lambda: True,
    )


def _payload_with_rule(food_id: str, unit: str = "G") -> dict[str, Any]:
    """RU: Payload с packaging_rule для food_id (нужно для packed items)."""
    return {
        "items": [
            {"food_id": food_id, "qty": {"value": "1", "unit": "PCS"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": food_id,
                "pack_size": {"value": "1", "unit": unit},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }


def _mock_result_with_overage(
    *,
    food_id: str,
    overage_value: Decimal,
    overage_unit: str,
) -> PackagingResult:
    """
    Build a PackagingResult with a single packed line and given overage.

    RU: Возвращаем реальный core результат, чтобы роутер прошёл mapping как в проде.
    EN: Return real core result to exercise router mapping.
    """
    from core.shoplist_engine.models import FoodRef, PackPlan, Quantity, Unit
    from core.shoplist_engine.packager import PackagingResult

    unit_enum = Unit[overage_unit]

    # PackPlan invariants:
    # - provided.value == packs * pack_size.value
    # - overage.value == provided.value - requested.value
    # For analytics tests, we set:
    # - requested = 1
    # - pack_size = 1 + overage_value (to allow overage)
    # - packs = 1
    # - provided = packs * pack_size = 1 + overage_value
    # - overage = provided - requested = overage_value
    pack_size_value = Decimal("1") + overage_value
    provided_value = pack_size_value  # packs=1
    return PackagingResult(
        packed=[
            PackPlan(
                food=FoodRef(food_id=food_id),
                requested=Quantity(Decimal("1"), unit_enum),
                pack_size=Quantity(pack_size_value, unit_enum),
                packs=1,
                provided=Quantity(provided_value, unit_enum),
                overage=Quantity(overage_value, unit_enum),
            )
        ],
        unpacked=[],
    )


def _assert_analytics_shape(data: dict) -> dict:
    assert "analytics" in data, "response must include analytics"
    analytics = data["analytics"]
    assert isinstance(analytics, dict)
    assert isinstance(analytics.get("total_lines"), int)
    assert isinstance(analytics.get("packed_lines"), int)
    assert isinstance(analytics.get("unpacked_lines"), int)
    assert isinstance(analytics.get("total_overage_by_unit"), dict)
    return analytics


def test_analytics_overage_zero_returns_string_zero(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overage 0 should be reported as '0' (string) for stable JSON."""
    _enable_vip(monkeypatch)

    mock_result = _mock_result_with_overage(
        food_id="flour",
        overage_value=Decimal("0"),
        overage_unit="G",
    )

    def mock_generate(
        specs: list,
        packaging_rules: list | None = None,
    ) -> PackagingResult:
        return mock_result

    monkeypatch.setattr("app.routers.vip_shoplist.ShoplistEngine.generate", mock_generate)

    r = client_with_vip_access.post(
        "/api/v1/vip/shoplist/generate",
        json=_payload_with_rule("flour", "G"),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    analytics = _assert_analytics_shape(data)
    totals = analytics["total_overage_by_unit"]
    assert totals.get("G") == "0"
    assert analytics["total_lines"] == 1
    assert analytics["packed_lines"] == 1
    assert analytics["unpacked_lines"] == 0


def test_analytics_overage_positive_sums_correctly(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overage > 0 should be summed and returned as string."""
    _enable_vip(monkeypatch)

    mock_result = _mock_result_with_overage(
        food_id="flour",
        overage_value=Decimal("200"),
        overage_unit="G",
    )

    def mock_generate(
        specs: list,
        packaging_rules: list | None = None,
    ) -> PackagingResult:
        return mock_result

    monkeypatch.setattr("app.routers.vip_shoplist.ShoplistEngine.generate", mock_generate)

    r = client_with_vip_access.post(
        "/api/v1/vip/shoplist/generate",
        json=_payload_with_rule("flour", "G"),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    analytics = _assert_analytics_shape(data)
    totals = analytics["total_overage_by_unit"]
    assert totals.get("G") == "200"
    assert analytics["total_lines"] == 1
    assert analytics["packed_lines"] == 1
    assert analytics["unpacked_lines"] == 0


def test_analytics_overage_multi_unit_is_reported_separately(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overage totals should be grouped by unit (e.g., G and ML)."""
    _enable_vip(monkeypatch)

    from core.shoplist_engine.models import FoodRef, PackPlan, Quantity, Unit
    from core.shoplist_engine.packager import PackagingResult

    mock_result = PackagingResult(
        packed=[
            PackPlan(
                food=FoodRef(food_id="flour"),
                requested=Quantity(Decimal("1"), Unit.G),
                pack_size=Quantity(
                    Decimal("201"), Unit.G
                ),  # pack_size = 201, provided = 201, overage = 201-1 = 200
                packs=1,
                provided=Quantity(Decimal("201"), Unit.G),
                overage=Quantity(Decimal("200"), Unit.G),
            ),
            PackPlan(
                food=FoodRef(food_id="milk"),
                requested=Quantity(Decimal("1"), Unit.ML),
                pack_size=Quantity(
                    Decimal("51"), Unit.ML
                ),  # pack_size = 51, provided = 51, overage = 51-1 = 50
                packs=1,
                provided=Quantity(Decimal("51"), Unit.ML),
                overage=Quantity(Decimal("50"), Unit.ML),
            ),
        ],
        unpacked=[],
    )

    def mock_generate(
        specs: list,
        packaging_rules: list | None = None,
    ) -> PackagingResult:
        return mock_result

    monkeypatch.setattr("app.routers.vip_shoplist.ShoplistEngine.generate", mock_generate)

    # items are arbitrary; engine is mocked
    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "PCS"}, "form": "RAW"},
            {"food_id": "milk", "qty": {"value": "1", "unit": "PCS"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "flour",
                "pack_size": {"value": "1", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "milk",
                "pack_size": {"value": "1", "unit": "ML"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    analytics = _assert_analytics_shape(data)
    totals = analytics["total_overage_by_unit"]

    assert totals.get("G") == "200"
    assert totals.get("ML") == "50"
    assert analytics["packed_lines"] == 2
    assert analytics["unpacked_lines"] == 0
    assert analytics["total_lines"] == 2


def _mock_result_with_multiple_overages(
    food_id: str,
    overages: list[tuple[Decimal, str]],
) -> PackagingResult:
    """
    Build a PackagingResult with multiple packed lines and given overages.

    RU: Используется для тестирования агрегации overage по одной unit.
    EN: Used for testing overage aggregation for the same unit.
    """
    from core.shoplist_engine.models import FoodRef, PackPlan, Quantity, Unit
    from core.shoplist_engine.packager import PackagingResult

    packed = []
    for i, (amount, unit) in enumerate(overages):
        unit_enum = Unit[unit]
        # PackPlan invariants: provided = packs * pack_size, overage = provided - requested
        # We set requested=1000, pack_size=1000+amount, packs=1, provided=1000+amount, overage=amount
        requested_value = Decimal("1000")
        pack_size_value = requested_value + amount
        packed.append(
            PackPlan(
                food=FoodRef(food_id=f"{food_id}_{i}"),
                requested=Quantity(requested_value, unit_enum),
                pack_size=Quantity(pack_size_value, unit_enum),
                packs=1,
                provided=Quantity(pack_size_value, unit_enum),  # packs=1, so provided = pack_size
                overage=Quantity(amount, unit_enum),
            )
        )

    return PackagingResult(packed=packed, unpacked=[])


def test_analytics_only_unpacked_lines_have_empty_overage_totals(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When nothing is packed, analytics should report empty overage totals."""
    _enable_vip(monkeypatch)

    from core.shoplist_engine.models import FoodRef, Quantity, ShoplistLine, Unit
    from core.shoplist_engine.packager import PackagingResult

    mock_result = PackagingResult(
        packed=[],
        unpacked=[
            ShoplistLine(
                food=FoodRef(food_id="salt"),
                qty=Quantity(Decimal("10"), Unit.G),
            ),
            ShoplistLine(
                food=FoodRef(food_id="water"),
                qty=Quantity(Decimal("1"), Unit.L),
            ),
        ],
    )

    def mock_generate(
        specs: list,
        packaging_rules: list | None = None,
    ) -> PackagingResult:
        return mock_result

    monkeypatch.setattr("app.routers.vip_shoplist.ShoplistEngine.generate", mock_generate)

    payload = {
        "items": [
            {"food_id": "salt", "qty": {"value": "10", "unit": "G"}, "form": "RAW"},
            {"food_id": "water", "qty": {"value": "1", "unit": "L"}, "form": "RAW"},
        ]
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200, r.text

    analytics = _assert_analytics_shape(r.json())
    assert analytics["packed_lines"] == 0
    assert analytics["unpacked_lines"] == 2
    assert analytics["total_lines"] == 2
    assert analytics["total_overage_by_unit"] == {}


def test_analytics_overage_positive_sums_multiple_lines_same_unit(
    client_with_vip_access,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple packed lines with same unit should aggregate overage correctly."""
    _enable_vip(monkeypatch)

    mock_result = _mock_result_with_multiple_overages(
        food_id="flour",
        overages=[
            (Decimal("100"), "G"),
            (Decimal("150"), "G"),
        ],
    )

    def mock_generate(
        specs: list,
        packaging_rules: list | None = None,
    ) -> PackagingResult:
        return mock_result

    monkeypatch.setattr("app.routers.vip_shoplist.ShoplistEngine.generate", mock_generate)

    # Need packaging_rules for all food_ids that appear in packed result (flour_0, flour_1)
    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1", "unit": "KG"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "flour_0",
                "pack_size": {"value": "1100", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "flour_1",
                "pack_size": {"value": "1150", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200, r.text

    analytics = _assert_analytics_shape(r.json())
    totals = analytics["total_overage_by_unit"]

    assert totals["G"] == "250"
    assert analytics["packed_lines"] == 2
    assert analytics["unpacked_lines"] == 0
    assert analytics["total_lines"] == 2
