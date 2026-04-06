"""
OFF nutrition helpers.

RU: Вспомогательные сущности provenance/confidence для OFF.
EN: Provenance/confidence helpers for OFF nutrition.
"""

from .bridge import merge_wire_nutrition_sources, nutrition_inputs_from_unified_wire
from .contracts import NutritionInput, NutritionResolved
from .resolver import (
    DEFAULT_SOURCE_PRIORITY,
    SOURCE_CONFIDENCE_WEIGHTS,
    is_valid_nutrient_scalar,
    project_scalar_compat,
    resolve_nutrition,
)

__all__ = [
    "DEFAULT_SOURCE_PRIORITY",
    "SOURCE_CONFIDENCE_WEIGHTS",
    "NutritionInput",
    "NutritionResolved",
    "is_valid_nutrient_scalar",
    "merge_wire_nutrition_sources",
    "nutrition_inputs_from_unified_wire",
    "project_scalar_compat",
    "resolve_nutrition",
]
