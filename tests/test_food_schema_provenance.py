"""Tests for additive provenance fields on app food schema."""

import math

import pytest

from app.schemas.food import (
    FoodItem,
    _parse_json_float_mapping,
    _parse_json_inputs,
    _parse_json_mapping,
)


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


def test_parse_json_float_mapping_helper_coerces_numeric_and_rejects_bad_values() -> None:
    assert _parse_json_float_mapping(None) == {}
    assert _parse_json_float_mapping('{"kcal":0.7,"protein_g":true}') == {"kcal": 0.7}
    assert _parse_json_float_mapping("not-json") == {}
    assert _parse_json_float_mapping('["bad"]') == {}
    assert _parse_json_float_mapping({"a": 1, "b": "x", "c": float("nan")}) == {"a": 1.0}
    assert _parse_json_float_mapping("null") == {}
    assert _parse_json_float_mapping("none") == {}
    assert _parse_json_float_mapping("   ") == {}


def test_food_item_parses_nutrition_nutrient_confidence() -> None:
    food = FoodItem(
        id="food-nc",
        canonical_name="quinoa",
        group="grain",
        kcal=120.0,
        protein_g=4.4,
        fat_g=1.9,
        carbs_g=21.3,
        source="USDA",
        version_date="2024-01-01",
        nutrition_nutrient_confidence='{"kcal":0.7,"protein_g":0.6}',
    )
    assert food.nutrition_nutrient_confidence["kcal"] == pytest.approx(0.7)
    assert food.nutrition_nutrient_confidence["protein_g"] == pytest.approx(0.6)


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


def test_food_item_nutrition_confidence_coerces_none_int_and_bad_strings() -> None:
    explicit_none = FoodItem(
        id="food-c3",
        canonical_name="millet",
        group="grain",
        kcal=378.0,
        protein_g=11.0,
        fat_g=4.2,
        carbs_g=72.9,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence=None,
    )
    assert explicit_none.nutrition_confidence == 0.0

    as_int = FoodItem(
        id="food-c4",
        canonical_name="buckwheat",
        group="grain",
        kcal=343.0,
        protein_g=13.3,
        fat_g=3.4,
        carbs_g=71.5,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence=1,
    )
    assert as_int.nutrition_confidence == 1.0

    empty_str = FoodItem(
        id="food-c5",
        canonical_name="quinoa",
        group="grain",
        kcal=368.0,
        protein_g=14.1,
        fat_g=6.1,
        carbs_g=64.2,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence="   ",
    )
    assert empty_str.nutrition_confidence == 0.0

    bad_str = FoodItem(
        id="food-c6",
        canonical_name="amaranth",
        group="grain",
        kcal=371.0,
        protein_g=13.6,
        fat_g=7.0,
        carbs_g=65.2,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence="not-a-float",
    )
    assert bad_str.nutrition_confidence == 0.0


def test_food_item_nutrition_confidence_rejects_non_finite_floats() -> None:
    nan_food = FoodItem(
        id="food-c8",
        canonical_name="teff",
        group="grain",
        kcal=367.0,
        protein_g=13.3,
        fat_g=2.4,
        carbs_g=73.1,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence=float("nan"),
    )
    assert nan_food.nutrition_confidence == 0.0

    inf_food = FoodItem(
        id="food-c9",
        canonical_name="fonio",
        group="grain",
        kcal=368.0,
        protein_g=11.0,
        fat_g=3.8,
        carbs_g=74.0,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence=float("inf"),
    )
    assert inf_food.nutrition_confidence == 0.0

    nan_str = FoodItem(
        id="food-c10",
        canonical_name="sorghum",
        group="grain",
        kcal=329.0,
        protein_g=10.6,
        fat_g=3.5,
        carbs_g=72.1,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence=str(float("nan")),
    )
    assert nan_str.nutrition_confidence == 0.0
    assert math.isfinite(nan_str.nutrition_confidence)


def test_food_item_nutrition_confidence_unknown_type_falls_back_to_zero() -> None:
    food = FoodItem(
        id="food-c7",
        canonical_name="spelt",
        group="grain",
        kcal=338.0,
        protein_g=14.6,
        fat_g=2.4,
        carbs_g=70.2,
        source="USDA",
        version_date="2024-01-01",
        nutrition_confidence=["0.5"],
    )
    assert food.nutrition_confidence == 0.0
