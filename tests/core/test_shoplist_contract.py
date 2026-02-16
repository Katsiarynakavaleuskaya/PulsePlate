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


def test_create_shopping_list_skips_invalid_entries() -> None:
    meal_plan = {
        "day0": "not-a-mapping",
        "day1": {
            "lunch": "not-a-list",
            "breakfast": [
                {"name": "oats", "amount": 50, "unit": "g"},
                "not-a-mapping",
                {"amount": 10, "unit": "g"},
                {"name": "", "amount": 10, "unit": "g"},
                {"name": "   ", "amount": 10, "unit": "g"},
                {"name": "rice", "amount": 10},
                {"name": "rice", "amount": 10, "unit": ""},
                {"name": "rice", "amount": 10, "unit": "   "},
                {"name": "lentils", "amount": {"bad": "type"}, "unit": "g"},
                {"name": "lentils", "amount": None, "unit": "g"},
                {"name": "beans", "amount": "abc", "unit": "g"},
                {"name": "oats", "amount": "25", "unit": "g"},
            ],
        },
    }

    out = create_shopping_list(meal_plan)
    assert len(out) == 1
    assert out[0].name == "oats"
    assert out[0].unit == "g"
    assert out[0].quantity == 75.0


def test_group_by_category_accepts_dataclasses_and_mappings() -> None:
    items: list[ShoppingItem | Mapping[str, object]] = [
        ShoppingItem(name="flour", quantity=350.0, unit="g", category=None),
        {"name": "meat", "quantity": 1, "unit": "kg", "category": "protein"},
        {"name": "blank", "quantity": 1, "unit": "x", "category": "   "},
    ]
    grouped = group_by_category(items)
    assert "protein" in grouped
    assert "uncategorized" in grouped
    assert len(grouped["protein"]) == 1
    assert len(grouped["uncategorized"]) == 2


def test_optimize_packaging_normalizes_dataclass_and_filters_invalid() -> None:
    items: list[object] = [
        {"name": "flour", "quantity": 350, "unit": "g"},
        ShoppingItem(name="oats", quantity=50.0, unit="g", category="grains"),
        ShoppingItem(name="rice", quantity=100.0, unit="g", category=None),
        {"name": "bad-qty", "quantity": {"unexpected": "mapping"}, "unit": "g"},
        "not-a-mapping",
        123,
        {"name": "sugar", "quantity": 150, "unit": "g"},
    ]
    out = optimize_packaging(cast(list[ShoppingItem | Mapping[str, object]], items))
    assert isinstance(out, list)
    assert len(out) == 4
    assert set(out[0].keys()) == {"name", "quantity", "unit", "category"}
    assert out[0]["name"] == "flour"
    assert out[0]["category"] == "uncategorized"
    assert set(out[1].keys()) == {"name", "quantity", "unit", "category"}
    assert out[1]["name"] == "oats"
    assert out[1]["category"] == "grains"
    assert set(out[2].keys()) == {"name", "quantity", "unit", "category"}
    assert out[2]["name"] == "rice"
    assert out[2]["category"] == "uncategorized"
    assert set(out[3].keys()) == {"name", "quantity", "unit", "category"}
    assert out[3]["name"] == "sugar"
