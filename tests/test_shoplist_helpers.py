from typing import Any, Dict, List, Mapping, Optional, Union

from core import shoplist


def test_get_shoplist_uses_generator(monkeypatch):
    calls: List[str] = []

    class DummyGenerator:
        def __init__(self) -> None:
            calls.append("init")

        def aggregate_ingredients(self, week_plan: Dict[str, Any]) -> List[str]:
            calls.append("aggregate")
            assert week_plan == {"week": True}
            return ["ingredient"]

        def round_to_packages(
            self,
            aggregated: List[str],
            packaging_db: Optional[Dict[str, Any]],
            rules: Optional[Mapping[str, Any]],
        ) -> List[str]:
            calls.append("round")
            assert aggregated == ["ingredient"]
            assert packaging_db == {"db": True}
            assert rules == {"rule": True}
            return ["rounded"]

        def format_export(
            self, shopping_list: List[str], locale: str = "ru", format_type: str = "json"
        ) -> Union[str, Dict[str, Any]]:
            calls.append("format")
            assert shopping_list == ["rounded"]
            assert locale == "en"
            assert format_type == "csv"
            return {"ok": True}

    monkeypatch.setattr(shoplist, "ShoplistGenerator", DummyGenerator)
    result = shoplist.get_shoplist(
        {"week": True},
        format_type="csv",
        locale="en",
        packaging_db={"db": True},
        rules={"rule": True},
    )
    assert result == {"ok": True}
    assert calls == ["init", "aggregate", "round", "format"]


def test_aggregate_ingredients_supports_direct_list(monkeypatch):
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
    assert aggregated["Milk"] > 0


def test_round_to_packages_filters_invalid(monkeypatch):
    monkeypatch.setattr(shoplist.ShoplistGenerator, "_load_packaging_rules", lambda self: {})
    generator = shoplist.ShoplistGenerator()
    size, count = generator._find_best_package(200, [0, -1, 100, 250], "up")
    assert size == 100
    assert count == 2
