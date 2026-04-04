"""
Tests for OFF nutrition resolver.

RU: Тесты resolver-слоя provenance/confidence для питания.
EN: Tests for nutrition provenance/confidence resolver.
"""

from core.off_nutrition import NutritionInput, project_scalar_compat, resolve_nutrition


def test_resolve_nutrition_prefers_explicit_source_priority() -> None:
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


def test_project_scalar_compat_adds_legacy_defaults() -> None:
    resolved = resolve_nutrition(
        inputs=[NutritionInput(source="estimate", nutrients={"protein_g": 9.5}, record_id="off-1")],
        nutrient_keys=["protein_g"],
    )

    compat = project_scalar_compat(resolved, required_keys=["protein_g", "fat_g", "carbs_g"])

    assert compat["protein_g"] == 9.5
    assert compat["fat_g"] == 0.0
    assert compat["carbs_g"] == 0.0
