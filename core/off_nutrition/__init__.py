"""
OFF nutrition helpers.

RU: Вспомогательные сущности provenance/confidence для OFF.
EN: Provenance/confidence helpers for OFF nutrition.
"""

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
    "project_scalar_compat",
    "resolve_nutrition",
]
