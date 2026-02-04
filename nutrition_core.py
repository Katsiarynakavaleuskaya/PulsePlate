"""
Nutrition Core Module - BMR/TDEE Calculations (compat layer).

RU: Совместимый слой: старый импортный путь `nutrition_core` остаётся рабочим.
EN: Compatibility layer: keep `nutrition_core` as a stable import path.

Canonical implementation lives in `core/bmr.py`.
"""

from __future__ import annotations

from core.bmr import (  # noqa: F401 (re-export)
    ActivityLevel,
    PAL,
    PAL_FACTORS,
    Sex,
    bmr_harris,
    bmr_katch,
    bmr_mifflin,
    calculate_all_bmr,
    calculate_all_tdee,
    get_activity_descriptions,
    tdee,
)

__all__ = [
    "ActivityLevel",
    "PAL",
    "PAL_FACTORS",
    "Sex",
    "bmr_harris",
    "bmr_katch",
    "bmr_mifflin",
    "calculate_all_bmr",
    "calculate_all_tdee",
    "get_activity_descriptions",
    "tdee",
]
