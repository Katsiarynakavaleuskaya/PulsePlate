"""Tests for core.off_nutrition.bridge (wire rebuild + dual-source merge)."""

from __future__ import annotations

from core.off_nutrition.bridge import (
    merge_wire_nutrition_sources,
    nutrition_inputs_from_unified_wire,
)
from core.off_nutrition.contracts import NutritionInput


def test_nutrition_inputs_skips_non_mapping_wire_rows() -> None:
    inputs = nutrition_inputs_from_unified_wire(
        nutrition_inputs_wire=[42],
        nutrients_per_100g={"protein_g": 5.0},
        fallback_source="usda",
        record_id="x",
    )
    assert len(inputs) == 1
    assert inputs[0].nutrients["protein_g"] == 5.0


def test_nutrition_inputs_skips_when_nutrients_not_mapping() -> None:
    inputs = nutrition_inputs_from_unified_wire(
        nutrition_inputs_wire=({"source": "usda", "nutrients": "bad"},),
        nutrients_per_100g={"kcal": 100.0},
        fallback_source="usda",
        record_id="y",
    )
    assert len(inputs) == 1
    assert inputs[0].nutrients["kcal"] == 100.0


def test_nutrition_inputs_skips_wire_when_all_nutrient_values_invalid() -> None:
    inputs = nutrition_inputs_from_unified_wire(
        nutrition_inputs_wire=({"nutrients": {"protein_g": None, "kcal": "x"}},),
        nutrients_per_100g={"fiber_g": 2.0},
        fallback_source="estimate",
        record_id="z",
    )
    assert len(inputs) == 1
    assert inputs[0].nutrients["fiber_g"] == 2.0


def test_nutrition_inputs_from_unified_wire_empty_wire_uses_flat() -> None:
    inputs = nutrition_inputs_from_unified_wire(
        nutrition_inputs_wire=(),
        nutrients_per_100g={"protein_g": 12.0},
        fallback_source="usda",
        record_id="fdc-1",
    )
    assert len(inputs) == 1
    assert inputs[0].source == "usda"
    assert inputs[0].nutrients["protein_g"] == 12.0
    assert inputs[0].record_id == "fdc-1"


def test_merge_wire_prefers_usda_over_estimate_for_shared_key() -> None:
    primary = [
        NutritionInput(
            source="usda",
            nutrients={"protein_g": 31.0},
            record_id="1",
        )
    ]
    secondary = [
        NutritionInput(
            source="estimate",
            nutrients={"protein_g": 10.0, "fiber_g": 3.0},
            record_id="off-1",
        )
    ]
    resolved = merge_wire_nutrition_sources(
        primary_inputs=primary,
        secondary_inputs=secondary,
        nutrient_keys=("protein_g", "fiber_g"),
    )
    assert resolved.nutrients["protein_g"] == 31.0
    assert resolved.provenance["protein_g"] == "usda"
    assert resolved.nutrients["fiber_g"] == 3.0
    assert resolved.provenance["fiber_g"] == "estimate"
