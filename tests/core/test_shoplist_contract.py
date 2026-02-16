from __future__ import annotations

from typing import Mapping, cast

from core.shoplist import (
    PackagingRule,
    ShoppingItem,
    create_shopping_list,
    group_by_category,
    optimize_packaging,
)


def test_packaging_rule_contract() -> None:
    rule = PackagingRule(
        category="grains",
        unit="g",
        typical_packages=[100, 250, 500],
        rounding_strategy="up",
    )
    assert rule.category == "grains"
    assert rule.unit == "g"
    assert rule.typical_packages == [100, 250, 500]
    assert rule.rounding_strategy == "up"


def test_shopping_item_contract() -> None:
    item = ShoppingItem(name="oats", quantity=50.0, unit="g", category="grains")
    assert item.name == "oats"
    assert item.quantity == 50.0
    assert item.unit == "g"
    assert item.category == "grains"


def test_create_shopping_list_aggregates_and_sorts() -> None:
    meal_plan = {
        "day1": {
            "breakfast": [{"name": "oats", "amount": 50, "unit": "g"}],
            "lunch": [{"name": "oats", "amount": 25, "unit": "g"}],
            "dinner": [{"name": "rice", "amount": 100, "unit": "g"}],
        }
    }
    out = create_shopping_list(meal_plan)
    assert [item.name for item in out] == ["oats", "rice"]
    assert out[0].quantity == 75.0
    assert out[0].unit == "g"
    assert out[1].quantity == 100.0
    assert out[1].unit == "g"


def test_group_by_category_fallbacks_to_uncategorized() -> None:
    items: list[Mapping[str, object]] = [
        {"name": "flour", "quantity": 350, "unit": "g"},
        {"name": "meat", "quantity": 1, "unit": "kg", "category": "protein"},
        {"name": "blank", "quantity": 1, "unit": "x", "category": "   "},
    ]
    grouped = group_by_category(items)
    assert "protein" in grouped
    assert "uncategorized" in grouped
    assert len(grouped["protein"]) == 1
    assert len(grouped["uncategorized"]) == 2


def test_optimize_packaging_filters_non_mappings() -> None:
    items: list[object] = [
        {"name": "flour", "quantity": 350, "unit": "g"},
        "not-a-mapping",
        123,
        {"name": "sugar", "quantity": 150, "unit": "g"},
    ]
    out = optimize_packaging(cast(list[Mapping[str, object]], items))
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]["name"] == "flour"
    assert out[1]["name"] == "sugar"
