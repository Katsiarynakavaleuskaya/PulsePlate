"""Tests for additive provenance fields on app food schema."""

import pytest

from app.schemas.food import FoodItem, _parse_json_inputs, _parse_json_mapping


def test_food_item_parses_additive_nutrition_metadata_from_strings() -> None:
    food = FoodItem(
        id="food-1",
        canonical_name="apple",
        group="fruit",
        kcal=52.0,
        protein_g=0.3,
        fat_g=0.2,
        carbs_g=14.0,
        source="USDA",
        version_date="2024-01-01",
        nutrition_inputs='[{"source":"estimate","record_id":"off-1"}, 1, "skip-me"]',
        nutrition_provenance='{"protein_g":"estimate","kcal":"usda"}',
    )

    assert food.nutrition_inputs == [{"source": "estimate", "record_id": "off-1"}]
    assert food.nutrition_provenance == {"protein_g": "estimate", "kcal": "usda"}


def test_food_item_handles_null_and_invalid_additive_nutrition_metadata() -> None:
    food = FoodItem(
        id="food-2",
        canonical_name="pear",
        group="fruit",
        kcal=57.0,
        protein_g=0.4,
        fat_g=0.1,
        carbs_g=15.0,
        source="OFF",
        version_date="2024-01-01",
        nutrition_inputs="not-json",
        nutrition_provenance="null",
    )

    assert food.nutrition_inputs == []
    assert food.nutrition_provenance == {}


def test_food_item_accepts_mapping_and_none_for_additive_metadata() -> None:
    food = FoodItem(
        id="food-3",
        canonical_name="banana",
        group="fruit",
        kcal=89.0,
        protein_g=1.1,
        fat_g=0.3,
        carbs_g=22.8,
        source="OFF",
        version_date="2024-01-01",
        nutrition_inputs=None,
        nutrition_provenance={"protein_g": "estimate", "kcal": 123},
    )

    assert food.nutrition_inputs == []
    assert food.nutrition_provenance == {"protein_g": "estimate", "kcal": "123"}


def test_parse_json_mapping_helper_covers_none_invalid_and_non_dict_cases() -> None:
    assert _parse_json_mapping(None) == {}
    assert _parse_json_mapping('{"protein_g":"estimate"}') == {"protein_g": "estimate"}
    assert _parse_json_mapping("not-json") == {}
    assert _parse_json_mapping('["bad"]') == {}


def test_parse_json_inputs_helper_covers_list_and_string_edge_cases() -> None:
    assert _parse_json_inputs([{"source": "estimate"}, "skip"]) == [{"source": "estimate"}]
    assert _parse_json_inputs("null") == []
    assert _parse_json_inputs('{"source":"estimate"}') == []
    assert _parse_json_inputs("not-json") == []


def test_food_item_nutrition_confidence_coerces_and_defaults() -> None:
    food = FoodItem(
        id="food-c1",
        canonical_name="oat",
        group="grain",
        kcal=389.0,
        protein_g=16.9,
        fat_g=6.9,
        carbs_g=66.3,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence="0.75",
    )
    assert food.nutrition_confidence == pytest.approx(0.75, 0.001)

    food_default = FoodItem(
        id="food-c2",
        canonical_name="rye",
        group="grain",
        kcal=335.0,
        protein_g=10.3,
        fat_g=1.6,
        carbs_g=69.8,
        source="USDA",
        version_date="2024-01-01",
    )
    assert food_default.nutrition_confidence == 0.0
