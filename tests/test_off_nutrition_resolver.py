"""
Tests for OFF nutrition resolver.

RU: Тесты resolver-слоя provenance/confidence для питания.
EN: Tests for nutrition provenance/confidence resolver.
"""

import math

from core.off_nutrition import (
    NutritionInput,
    is_valid_nutrient_scalar,
    project_scalar_compat,
    resolve_nutrition,
)
from core.off_nutrition.resolver import _is_valid_numeric, _normalize_source_name


def test_is_valid_nutrient_scalar_accepts_finite_nonneg_numbers() -> None:
    assert is_valid_nutrient_scalar(1) is True
    assert is_valid_nutrient_scalar(0.0) is True
    assert is_valid_nutrient_scalar(-1.0) is False
    assert is_valid_nutrient_scalar(None) is False
    assert is_valid_nutrient_scalar(True) is False
    assert is_valid_nutrient_scalar(False) is False


def test_normalize_source_name_off_and_merged_collapses_to_estimate() -> None:
    assert _normalize_source_name("Open Food Facts") == "estimate"
    assert _normalize_source_name("off") == "estimate"
    assert _normalize_source_name("OFF") == "estimate"
    assert _normalize_source_name("MERGED(usda, off)") == "estimate"
    assert _normalize_source_name("merged(USDA, OFF)") == "estimate"
    assert _normalize_source_name("usda") == "usda"


def test_is_valid_numeric_rejects_nan_inf_negative_and_bool() -> None:
    assert _is_valid_numeric(0.0) is True
    assert _is_valid_numeric(3.14) is True
    assert _is_valid_numeric(float("nan")) is False
    assert _is_valid_numeric(float("inf")) is False
    assert _is_valid_numeric(float("-inf")) is False
    assert _is_valid_numeric(-1.0) is False
    assert _is_valid_numeric(True) is False


def test_resolve_nutrition_auto_discovers_nutrient_keys() -> None:
    inputs = [
        NutritionInput(source="estimate", nutrients={"protein_g": 5.0}, record_id="a"),
        NutritionInput(source="estimate", nutrients={"fat_g": 1.0}, record_id="b"),
    ]
    result = resolve_nutrition(inputs=inputs, nutrient_keys=None)
    assert result.nutrients["protein_g"] == 5.0
    assert result.nutrients["fat_g"] == 1.0
    assert result.provenance["protein_g"] == "estimate"
    assert result.provenance["fat_g"] == "estimate"


def test_resolve_nutrition_skips_invalid_numeric_values() -> None:
    inputs = [
        NutritionInput(
            source="usda",
            nutrients={
                "protein_g": float("nan"),
                "fat_g": float("inf"),
                "carbs_g": -1.0,
            },
            record_id="usda-invalid",
        ),
        NutritionInput(
            source="estimate",
            nutrients={"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 2.0},
            record_id="off-valid",
        ),
    ]
    result = resolve_nutrition(
        inputs=inputs,
        nutrient_keys=["protein_g", "fat_g", "carbs_g"],
    )
    assert math.isclose(result.nutrients["protein_g"], 10.0)
    assert math.isclose(result.nutrients["fat_g"], 5.0)
    assert math.isclose(result.nutrients["carbs_g"], 2.0)
    assert result.provenance["protein_g"] == "estimate"
    assert result.provenance["fat_g"] == "estimate"
    assert result.provenance["carbs_g"] == "estimate"


def test_resolve_nutrition_prefers_default_source_priority() -> None:
    inputs = [
        NutritionInput(source="estimate", nutrients={"protein_g": 8.0}, record_id="off-1"),
        NutritionInput(source="usda", nutrients={"protein_g": 12.0}, record_id="usda-1"),
    ]

    result = resolve_nutrition(inputs=inputs, nutrient_keys=["protein_g"])

    assert result.nutrients["protein_g"] == 12.0
    assert result.provenance["protein_g"] == "usda"
    assert 0.0 <= result.confidence <= 1.0


def test_resolve_nutrition_is_order_independent() -> None:
    ordered = [
        NutritionInput(source="estimate", nutrients={"kcal": 101.0}, record_id="off-1"),
        NutritionInput(source="usda", nutrients={"kcal": 95.0}, record_id="usda-1"),
    ]
    reversed_inputs = list(reversed(ordered))

    left = resolve_nutrition(inputs=ordered, nutrient_keys=["kcal"])
    right = resolve_nutrition(inputs=reversed_inputs, nutrient_keys=["kcal"])

    assert left.nutrients == right.nutrients
    assert left.provenance == right.provenance
    assert left.confidence == right.confidence


def test_resolve_nutrition_treats_explicit_zero_as_present() -> None:
    inputs = [
        NutritionInput(source="estimate", nutrients={"fat_g": 2.0}, record_id="off-1"),
        NutritionInput(source="usda", nutrients={"fat_g": 0.0}, record_id="usda-1"),
    ]

    result = resolve_nutrition(inputs=inputs, nutrient_keys=["fat_g"])

    assert result.nutrients["fat_g"] == 0.0
    assert result.provenance["fat_g"] == "usda"


def test_nutrition_resolved_to_dict_includes_raw_inputs() -> None:
    result = resolve_nutrition(
        inputs=[NutritionInput(source="estimate", nutrients={"protein_g": 9.5}, record_id="off-1")],
        nutrient_keys=["protein_g"],
    )
    payload = result.to_dict()
    assert payload["nutrients"] == {"protein_g": 9.5}
    assert payload["provenance"] == {"protein_g": "estimate"}
    assert len(payload["raw_inputs"]) == 1
    assert payload["raw_inputs"][0]["record_id"] == "off-1"


def test_project_scalar_compat_adds_legacy_defaults() -> None:
    resolved = resolve_nutrition(
        inputs=[NutritionInput(source="estimate", nutrients={"protein_g": 9.5}, record_id="off-1")],
        nutrient_keys=["protein_g"],
    )

    compat = project_scalar_compat(resolved, required_keys=["protein_g", "fat_g", "carbs_g"])

    assert compat["protein_g"] == 9.5
    assert compat["fat_g"] == 0.0
    assert compat["carbs_g"] == 0.0
