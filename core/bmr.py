"""
BMR / TDEE calculations (core).

RU: Расчёт BMR / TDEE (ядро доменной логики).
EN: Basal Metabolic Rate (BMR) and Total Daily Energy Expenditure (TDEE) calculations.

This module is the canonical home for BMR/TDEE math and constants.
It is intentionally import-safe (no env reads, no I/O).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Dict, Literal, Union

# Type definitions
Sex = Literal["female", "male"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Physical Activity Level (PAL) factors.
# RU: Коэффициенты активности (PAL).
# EN: Activity multipliers used for TDEE.
_PAL_FACTORS: Dict[str, float] = {
    "sedentary": 1.2,  # Little to no exercise
    "light": 1.375,  # Light exercise 1-3 days/week
    "moderate": 1.55,  # Moderate exercise 3-5 days/week
    "active": 1.725,  # Heavy exercise 6-7 days/week
    "very_active": 1.9,  # Very heavy exercise / training twice a day
}

# RU: Неизменяемая карта коэффициентов активности (SoT).
# EN: Immutable activity factor mapping (single source of truth).
PAL_FACTORS = MappingProxyType(_PAL_FACTORS)

# Backward-compat alias (some older code refers to PAL).
PAL = PAL_FACTORS

# Fallback estimate used when premium BMR backends are runtime-disabled in legacy shims.
# RU: Упрощённая оценка BMR (ккал/кг/день) для fallback-ответов.
# EN: Simple BMR estimate (kcal/kg/day) for deterministic fallbacks.
FALLBACK_BMR_KCAL_PER_KG_PER_DAY: float = 24.0

# Goal multipliers used in fallback recommended intake.
# RU: Мультипликаторы для целей (fallback).
# EN: Multipliers for goal-based recommended intake (fallback).
WEIGHT_LOSS_MULTIPLIER: float = 0.8
WEIGHT_GAIN_MULTIPLIER: float = 1.2

# Mifflin–St Jeor coefficients
_MIFFLIN_WEIGHT_COEFF: float = 10.0
_MIFFLIN_HEIGHT_COEFF: float = 6.25
_MIFFLIN_AGE_COEFF: float = 5.0
_MIFFLIN_SEX_MALE: float = 5.0
_MIFFLIN_SEX_FEMALE: float = -161.0

# Harris–Benedict (revised 1984) coefficients
_HARRIS_MALE_BASE: float = 66.5
_HARRIS_MALE_WEIGHT_COEFF: float = 13.75
_HARRIS_MALE_HEIGHT_COEFF: float = 5.003
_HARRIS_MALE_AGE_COEFF: float = 6.755

_HARRIS_FEMALE_BASE: float = 655.1
_HARRIS_FEMALE_WEIGHT_COEFF: float = 9.563
_HARRIS_FEMALE_HEIGHT_COEFF: float = 1.850
_HARRIS_FEMALE_AGE_COEFF: float = 4.676

# Katch–McArdle coefficients
_KATCH_BASE: float = 370.0
_KATCH_LEAN_MASS_COEFF: float = 21.6


def _validate_sex(sex: object) -> str:
    """Validate sex value to avoid silent fall-through.

    RU: Явная валидация, чтобы не было silent fall-through.
    EN: Explicit validation to avoid silent fall-through.
    """
    value = str(sex).strip().lower()
    if value not in ("male", "female"):
        raise ValueError("sex must be 'male' or 'female'")
    return value


def bmr_mifflin(weight: float, height: float, age: int, sex: Sex) -> float:
    """
    Calculate BMR using Mifflin-St Jeor equation.

    Formula:
        Men:    BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(years) + 5
        Women:  BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(years) - 161
    """
    if weight <= 0 or height <= 0 or age <= 0:
        raise ValueError("Weight, height, and age must be positive values")
    if age > 120:
        raise ValueError("Age must be realistic (≤120 years)")

    sex_value = _validate_sex(sex)
    sex_factor = _MIFFLIN_SEX_MALE if sex_value == "male" else _MIFFLIN_SEX_FEMALE
    bmr = (
        _MIFFLIN_WEIGHT_COEFF * weight
        + _MIFFLIN_HEIGHT_COEFF * height
        - _MIFFLIN_AGE_COEFF * age
        + sex_factor
    )
    return round(bmr, 1)


def bmr_harris(weight: float, height: float, age: int, sex: Sex) -> float:
    """
    Calculate BMR using Harris-Benedict equation (revised 1984).

    Formula:
        Men:    BMR = 66.5 + (13.75 × weight) + (5.003 × height) - (6.755 × age)
        Women:  BMR = 655.1 + (9.563 × weight) + (1.850 × height) - (4.676 × age)
    """
    if weight <= 0 or height <= 0 or age <= 0:
        raise ValueError("Weight, height, and age must be positive values")
    if age > 120:
        raise ValueError("Age must be realistic (≤120 years)")

    sex_value = _validate_sex(sex)
    if sex_value == "male":
        bmr = (
            _HARRIS_MALE_BASE
            + _HARRIS_MALE_WEIGHT_COEFF * weight
            + _HARRIS_MALE_HEIGHT_COEFF * height
            - _HARRIS_MALE_AGE_COEFF * age
        )
    else:
        bmr = (
            _HARRIS_FEMALE_BASE
            + _HARRIS_FEMALE_WEIGHT_COEFF * weight
            + _HARRIS_FEMALE_HEIGHT_COEFF * height
            - _HARRIS_FEMALE_AGE_COEFF * age
        )

    return round(bmr, 1)


def bmr_katch(weight: float, bodyfat_percent: float) -> float:
    """
    Calculate BMR using Katch-McArdle equation.

    Formula:
        BMR = 370 + (21.6 × lean_mass_kg)
        where lean_mass = weight × (1 - bodyfat_percent/100)
    """
    if weight <= 0:
        raise ValueError("Weight must be a positive value")
    if not 0 <= bodyfat_percent <= 50:
        raise ValueError("Body fat percentage must be between 0 and 50")

    lean_mass = weight * (1 - bodyfat_percent / 100)
    bmr = _KATCH_BASE + _KATCH_LEAN_MASS_COEFF * lean_mass
    return round(bmr, 1)


def tdee(bmr: float, activity: ActivityLevel) -> float:
    """Calculate Total Daily Energy Expenditure (TDEE) as (BMR × PAL)."""
    if bmr <= 0:
        raise ValueError("BMR must be a positive value")
    if activity not in PAL_FACTORS:
        raise ValueError(f"Activity level must be one of: {list(PAL_FACTORS.keys())}")

    tdee_value = bmr * PAL_FACTORS[activity]
    return round(tdee_value, 0)


def calculate_all_bmr(
    weight: float,
    height: float,
    age: int,
    sex: Sex,
    bodyfat_percent: Union[float, None] = None,
) -> Dict[str, float]:
    """Calculate BMR using all available formulas."""
    results = {
        "mifflin": bmr_mifflin(weight, height, age, sex),
        "harris": bmr_harris(weight, height, age, sex),
    }

    if bodyfat_percent is not None:
        results["katch"] = bmr_katch(weight, bodyfat_percent)

    return results


def calculate_all_tdee(bmr_results: Dict[str, float], activity: ActivityLevel) -> Dict[str, float]:
    """Calculate TDEE for all BMR formula results."""
    return {formula: tdee(bmr_value, activity) for formula, bmr_value in bmr_results.items()}


def get_activity_descriptions() -> Dict[str, str]:
    """Return human-readable activity descriptions (EN)."""
    return {
        "sedentary": "Little to no exercise, desk job",
        "light": "Light exercise 1-3 days/week",
        "moderate": "Moderate exercise 3-5 days/week",
        "active": "Heavy exercise 6-7 days/week",
        "very_active": "Very heavy exercise, physical job, or training twice a day",
    }
