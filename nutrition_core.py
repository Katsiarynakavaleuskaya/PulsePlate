"""
Nutrition Core Module - Basic BMR/TDEE Calculations

This module provides basic basal metabolic rate (BMR) and total daily energy expenditure (TDEE)
calculations using multiple validated formulas.

Supported BMR formulas:
- Mifflin-St Jeor (most accurate for general population)
- Harris-Benedict (traditional formula)
- Katch-McArdle (for athletes with known body fat percentage)

Note: Activity level calculations and higher-level convenience functions
(calculate_all_bmr, calculate_all_tdee) are delegated to core.metabolism module
to avoid circular imports and ensure consistency.
"""

from typing import Dict, Literal

# Import activity multipliers from core.metabolism to ensure consistency
# This is imported directly to avoid circular imports with core modules
from core.metabolism import ACTIVITY_MULTIPLIERS

# Type definitions
Sex = Literal["female", "male"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]

# Physical Activity Level (PAL) factors - delegated from core.metabolism.ACTIVITY_MULTIPLIERS
# Only includes the standard activity levels (not backward compatibility aliases)
PAL: Dict[str, float] = {
    activity: multiplier
    for activity, multiplier in ACTIVITY_MULTIPLIERS.items()
    if activity in ["sedentary", "light", "moderate", "active", "very_active"]
}


def bmr_mifflin(weight: float, height: float, age: int, sex: Sex) -> float:
    """
    Calculate BMR using Mifflin-St Jeor equation.

    This is considered the most accurate formula for the general population.

    Args:
        weight: Weight in kilograms
        height: Height in centimeters
        age: Age in years
        sex: Biological sex ("male" or "female")

    Returns:
        BMR in calories per day

    Formula:
        Men: BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(years) + 5
        Women: BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(years) - 161
    """
    if weight <= 0 or height <= 0 or age <= 0:
        raise ValueError("Weight, height, and age must be positive values")
    if age > 120:
        raise ValueError("Age must be realistic (≤120 years)")

    sex_factor = 5 if sex == "male" else -161
    bmr = 10 * weight + 6.25 * height - 5 * age + sex_factor
    return round(bmr, 1)


def bmr_harris(weight: float, height: float, age: int, sex: Sex) -> float:
    """
    Calculate BMR using Harris-Benedict equation (revised 1984).

    Traditional formula, slightly less accurate than Mifflin-St Jeor.

    Args:
        weight: Weight in kilograms
        height: Height in centimeters
        age: Age in years
        sex: Biological sex ("male" or "female")

    Returns:
        BMR in calories per day

    Formula:
        Men: BMR = 66.5 + (13.75 × weight) + (5.003 × height) - (6.755 × age)
        Women: BMR = 655.1 + (9.563 × weight) + (1.850 × height) - (4.676 × age)
    """
    if weight <= 0 or height <= 0 or age <= 0:
        raise ValueError("Weight, height, and age must be positive values")
    if age > 120:
        raise ValueError("Age must be realistic (≤120 years)")

    if sex == "male":
        bmr = 66.5 + 13.75 * weight + 5.003 * height - 6.755 * age
    else:
        bmr = 655.1 + 9.563 * weight + 1.850 * height - 4.676 * age

    return round(bmr, 1)


def bmr_katch(weight: float, bodyfat_percent: float) -> float:
    """
    Calculate BMR using Katch-McArdle equation.

    Most accurate for athletes and people with known body fat percentage.
    Requires lean body mass calculation.

    Args:
        weight: Weight in kilograms
        bodyfat_percent: Body fat percentage (0-50)

    Returns:
        BMR in calories per day

    Formula:
        BMR = 370 + (21.6 × lean_mass_kg)
        where lean_mass = weight × (1 - bodyfat_percent/100)
    """
    if weight <= 0:
        raise ValueError("Weight must be a positive value")
    if not 0 <= bodyfat_percent <= 50:
        raise ValueError("Body fat percentage must be between 0 and 50")

    lean_mass = weight * (1 - bodyfat_percent / 100)
    bmr = 370 + 21.6 * lean_mass
    return round(bmr, 1)


def tdee(bmr: float, activity: ActivityLevel) -> float:
    """
    Calculate Total Daily Energy Expenditure (TDEE).

    TDEE represents the total calories burned per day including all activities.

    Args:
        bmr: Basal Metabolic Rate in calories
        activity: Activity level (sedentary, light, moderate, active, very_active)

    Returns:
        TDEE in calories per day

    Note:
        This function uses PAL factors from core.metabolism for consistency.
    """
    if bmr <= 0:
        raise ValueError("BMR must be a positive value")
    if activity not in PAL:
        raise ValueError(f"Activity level must be one of: {list(PAL.keys())}")

    tdee_value = bmr * PAL[activity]
    return round(tdee_value, 0)


def get_activity_descriptions() -> Dict[str, str]:
    """
    Get human-readable descriptions for activity levels.

    Returns:
        Dictionary mapping activity levels to descriptions
    """
    return {
        "sedentary": "Little to no exercise, desk job",
        "light": "Light exercise 1-3 days/week",
        "moderate": "Moderate exercise 3-5 days/week",
        "active": "Heavy exercise 6-7 days/week",
        "very_active": "Very heavy exercise, physical job, or training twice a day",
    }
