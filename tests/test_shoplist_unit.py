"""
Focused unit tests for core.shoplist to raise coverage on key paths.

Covers:
- unit conversions
- ingredient aggregation (two shapes)
- categorization
- package rounding strategies
- export formatting (json/csv/text)
- end-to-end get_shoplist wrapper
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import csv

import pytest

from core.shoplist import (
    PackagingRule,
    ShoplistGenerator,
    aggregate_ingredients as agg_api,
    format_export as fmt_api,
    get_shoplist,
)


@pytest.fixture()
def generator() -> ShoplistGenerator:
    return ShoplistGenerator()


def test_convert_to_grams(generator: ShoplistGenerator) -> None:
    # Basic units
    assert generator._convert_to_grams(100, "g") == 100
    assert generator._convert_to_grams(1, "kg") == 1000
    assert generator._convert_to_grams(250, "ml") == 250
    assert generator._convert_to_grams(2, "l") == 2000
    # Heuristics
    assert generator._convert_to_grams(3, "pcs") == 300
    assert generator._convert_to_grams(2, "tbsp") == 30
    assert generator._convert_to_grams(3, "tsp") == 15
    assert generator._convert_to_grams(1, "cup") == 250


def test_packaging_rules_load_error_fallback(tmp_path: Path) -> None:
    # Use a path that "exists" but is a directory to trigger open() error
    dir_path = tmp_path / "as_dir"
    dir_path.mkdir()
    gen = ShoplistGenerator(packaging_rules_file=str(dir_path))
    # Should fall back to default rules and include known categories
    assert "vegetables" in gen.packaging_rules and "default" in gen.packaging_rules


def test_aggregate_ingredients_days_shape(generator: ShoplistGenerator) -> None:
    week_plan: Dict = {
        "days": [
            {
                "day": "Mon",
                "meals": [
                    {
                        "name": "m1",
                        "ingredients": [
                            {"name": "Tomato", "amount": 100, "unit": "g"},
                            {"name": "Milk", "amount": 1, "unit": "l"},
                        ],
                    },
                    {
                        "name": "m2",
                        "ingredients": [
                            {"name": "Tomato", "amount": 50, "unit": "g"},
                        ],
                    },
                ],
            }
        ]
    }
    aggregated = generator.aggregate_ingredients(week_plan)
    assert aggregated["Tomato"] == 150
    assert aggregated["Milk"] == 1000


def test_aggregate_ingredients_flat_shape(generator: ShoplistGenerator) -> None:
    plan: Dict = {
        "ingredients": [
            {"name": "Sugar", "amount": 250, "unit": "g"},
            {"name": "Sugar", "amount": 1, "unit": "kg"},
        ]
    }
    aggregated = generator.aggregate_ingredients(plan)
    assert aggregated["Sugar"] == 1250


@pytest.mark.parametrize(
    "name,expected",
    [
        ("beef steak", "meat"),
        ("salmon filet", "fish"),
        ("Greek yogurt", "dairy"),
        ("fresh tomato", "vegetables"),
        ("banana", "fruits"),
        ("brown rice", "grains"),
        ("almond", "nuts"),
        ("olive oil", "oils"),
        ("black pepper", "spices"),
        ("mystery", "default"),
    ],
)
def test_categorize(name: str, expected: str, generator: ShoplistGenerator) -> None:
    assert generator._categorize_ingredient(name) == expected


def test_find_best_package_up_down_nearest(generator: ShoplistGenerator) -> None:
    # up strategy
    size, count = generator._find_best_package(260, [100, 250], "up")
    assert size == 100 and count >= 3
    # down strategy
    size, count = generator._find_best_package(260, [100, 250], "down")
    assert size == 250 and count == 1
    # nearest strategy
    size, count = generator._find_best_package(260, [100, 250], "nearest")
    assert size in (100, 250) and count >= 1


def test_find_best_package_edge_cases(generator: ShoplistGenerator) -> None:
    # Empty typical packages -> returns total_amount, 1
    size, count = generator._find_best_package(123, [], "up")
    assert size == 123 and count == 1
    # Down strategy with too-small total leads to fallback branch
    size, count = generator._find_best_package(10, [50, 100], "down")
    assert size == 50 and count == 1
    # Nearest strategy with tiny total sets at least one package
    size, count = generator._find_best_package(10, [100, 250], "nearest")
    assert count == 1


def test_round_to_packages_and_export_json_text_csv(generator: ShoplistGenerator) -> None:
    aggregated = {"beef": 600.0, "olive oil": 200.0, "water": 1500.0, "flour": 1200.0}
    # Custom simple rules to make behavior deterministic
    rules = {
        "meat": PackagingRule("meat", "g", [200, 400], "up"),
        "oils": PackagingRule("oils", "ml", [100, 200], "up"),
        "default": PackagingRule("default", "g", [100], "up"),
    }
    items = generator.round_to_packages(aggregated, rules=rules)
    assert len(items) == 4
    names = {it.name for it in items}
    assert {"beef", "olive oil", "water", "flour"} == names

    # json export
    j = generator.format_export(items, locale="en", format_type="json")
    assert isinstance(j, dict)
    assert len(j["shopping_list"]) == 4

    # text export
    t = generator.format_export(items, locale="en", format_type="text")
    assert "Shopping List:" in t
    assert "pcs of" in t
    # RU header path
    t_ru = generator.format_export(items, locale="ru", format_type="text")
    assert t_ru.splitlines()[0] == "Список покупок:"
    # Unknown locale falls back to English header
    t_x = generator.format_export(items, locale="xx", format_type="text")
    assert t_x.splitlines()[0] == "Shopping List:"
    # ES locale
    t_es = generator.format_export(items, locale="es", format_type="text")
    assert t_es.splitlines()[0] == "Lista de compras:"

    # csv export
    c = generator.format_export(items, locale="en", format_type="csv")
    # quick CSV sniff: header present and two data lines
    rows: List[List[str]] = list(csv.reader(c.splitlines()))
    assert rows[0] == [
        "name",
        "quantity",
        "unit",
        "category",
        "package_size",
        "packages_needed",
        "total_weight",
    ]
    assert len(rows) == 5

    # Unsupported format raises
    with pytest.raises(ValueError):
        generator.format_export(items, locale="en", format_type="unknown")


def test_high_level_helpers_end_to_end() -> None:
    week_plan = {
        "ingredients": [
            {"name": "chicken", "amount": 300, "unit": "g"},
            {"name": "tomato", "amount": 2, "unit": "pcs"},
        ]
    }
    # aggregate via module-level API
    aggregated = agg_api(week_plan)
    assert aggregated["chicken"] == 300
    assert aggregated["tomato"] == 200

    # format via module-level API
    gen = ShoplistGenerator()
    items = gen.round_to_packages(aggregated)
    out = fmt_api(items, locale="en", format_type="json")
    assert isinstance(out, dict) and "shopping_list" in out

    # wrapper round_to_packages + get_shoplist
    wrapped_items = ShoplistGenerator().round_to_packages(aggregated)
    assert wrapped_items and hasattr(wrapped_items[0], "name")
    # wrapper get_shoplist
    rendered = get_shoplist(week_plan, format_type="text", locale="en")
    assert isinstance(rendered, str)
    assert "Shopping List:" in rendered


def test_round_to_packages_wrapper_api() -> None:
    plan = {"ingredients": [{"name": "chicken", "amount": 1000, "unit": "g"}]}
    aggregated = agg_api(plan)
    from core.shoplist import round_to_packages as wrapper

    items = wrapper(aggregated)
    assert items and items[0].name == "chicken"


def test_round_to_packages_rule_fallback_on_bad_rule(generator: ShoplistGenerator) -> None:
    aggregated = {"mystery": 120}
    bad_rules = {"default": {"not": "a rule"}}
    items = generator.round_to_packages(aggregated, rules=bad_rules)  # triggers fallback rule
    assert items and items[0].package_size in (100, 250)


def test_round_to_packages_ml_unit_branch(generator: ShoplistGenerator) -> None:
    aggregated = {"olive oil": 1200.0}
    items = generator.round_to_packages(aggregated)
    assert items[0].unit in ("l", "ml")  # ml path with >= 1000 converts to liters
