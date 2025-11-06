from typing import Any, Dict, List, Mapping, Optional, Union

import pytest

from core import shoplist
from core.shoplist import ShoppingItem


def test_get_shoplist_uses_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[str] = []

    class DummyGenerator:
        def __init__(self) -> None:
            calls.append("init")

        def aggregate_ingredients(self, week_plan: Dict[str, Any]) -> Dict[str, float]:
            calls.append("aggregate")
            assert week_plan == {"week": True}
            return {"ingredient": 100.0}

        def round_to_packages(
            self,
            aggregated: Dict[str, float],
            packaging_db: Optional[Dict[str, Any]],
            rules: Optional[Mapping[str, Any]],
        ) -> List[ShoppingItem]:
            calls.append("round")
            assert aggregated == {"ingredient": 100.0}
            assert packaging_db == {"db": True}
            assert rules == {"rule": True}
            return [
                ShoppingItem(
                    name="ingredient",
                    quantity=1.0,
                    unit="g",
                    category="default",
                    package_size=100.0,
                    packages_needed=1,
                    total_weight=100.0,
                )
            ]

        def format_export(
            self,
            shopping_list: List[ShoppingItem],
            locale: str = "ru",
            format_type: str = "json",
        ) -> Union[str, Dict[str, Any]]:
            calls.append("format")
            assert len(shopping_list) == 1
            assert shopping_list[0].name == "ingredient"
            assert locale == "en"
            assert format_type == "csv"
            return {"ok": True}

    # Patch the singleton instance, not the class
    dummy_instance = DummyGenerator()
    monkeypatch.setattr(shoplist, "_generator", dummy_instance)
    result = shoplist.get_shoplist(
        {"week": True},
        format_type="csv",
        locale="en",
        packaging_db={"db": True},
        rules={"rule": True},
    )
    assert result == {"ok": True}
    assert calls == ["init", "aggregate", "round", "format"]


def test_aggregate_ingredients_supports_direct_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the branch for week plans with top-level ingredients is covered."""

    def fake_load(self: shoplist.ShoplistGenerator) -> Dict[str, shoplist.PackagingRule]:
        # Avoid reading CSV from disk
        return {"default": shoplist.PackagingRule("default", "g", [100], "up")}

    monkeypatch.setattr(
        shoplist.ShoplistGenerator, "_load_packaging_rules", fake_load, raising=False
    )

    generator = shoplist.ShoplistGenerator()
    plan = {
        "ingredients": [
            {"name": "Apple", "amount": 2, "unit": "kg"},
            {"name": "Milk", "amount": 1, "unit": "l"},
        ]
    }
    aggregated = generator.aggregate_ingredients(plan)
    # 2 kg -> 2000 g, 1 l -> 1000 ml assuming _convert_to_grams handles l
    assert aggregated["Apple"] == 2000
    assert aggregated["Milk"] == 1000.0


def test_round_to_packages_filters_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that round_to_packages filters invalid package sizes via public API."""

    # Monkeypatch to return a PackagingRule with sizes including invalid values (0, -1)
    def fake_load(self: shoplist.ShoplistGenerator) -> Dict[str, shoplist.PackagingRule]:
        return {"default": shoplist.PackagingRule("default", "g", [0, -1, 100, 250], "up")}

    monkeypatch.setattr(
        shoplist.ShoplistGenerator, "_load_packaging_rules", fake_load, raising=False
    )

    generator = shoplist.ShoplistGenerator()
    aggregated = {"test_item": 200.0}
    shopping_list = generator.round_to_packages(aggregated)

    assert len(shopping_list) == 1
    item = shopping_list[0]
    assert item.name == "test_item"
    assert item.package_size == 100
    assert item.packages_needed == 2
