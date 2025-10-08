"""Metabolism and Energy Expenditure Calculations.

This module provides functions for calculating Basal Metabolic Rate (BMR),
Total Daily Energy Expenditure (TDEE), macronutrient distributions, and
related metabolic calculations based on WHO/EFSA guidelines.

RU: Расчёты метаболизма и энергозатрат.
EN: Metabolism and energy expenditure calculations.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

# Type definitions
Sex = Literal["female", "male"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["loss", "maintain", "gain"]

# Activity level multipliers for TDEE calculation
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
    # Support both naming schemes for backward compatibility
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "extremely_active": 1.9,
}


def calculate_bmr(
    age: int,
    weight: float,
    height: int,
    gender: str,
    body_fat: Optional[float] = None,
    formula: str = "mifflin",
) -> float:
    """Calculate Basal Metabolic Rate using various formulas.

    RU: Расчёт базового метаболизма различными формулами.
    EN: Calculate basal metabolic rate using various formulas.

    Args:
        age: Age in years
        weight: Weight in kg
        height: Height in cm
        gender: "male" or "female"
        body_fat: Optional body fat percentage (for Katch-McArdle formula)
        formula: Formula to use ("mifflin", "harris", "katch", "cunningham")

    Returns:
        BMR in kcal/day

    Raises:
        ValueError: If unknown formula or missing body_fat for katch/cunningham
    """
    if formula == "mifflin":
        if gender == "male":
            return 10 * weight + 6.25 * height - 5 * age + 5
        else:
            return 10 * weight + 6.25 * height - 5 * age - 161
    elif formula == "harris":
        if gender == "male":
            return 66.5 + 13.75 * weight + 5.003 * height - 6.755 * age
        else:
            return 655.1 + 9.563 * weight + 1.85 * height - 4.676 * age
    elif formula in ("katch", "cunningham"):
        if body_fat is None:
            raise ValueError(f"body_fat required for {formula} formula")
        if formula == "katch":
            lean_mass = weight * (1 - body_fat / 100)
            return 370 + 21.6 * lean_mass
        else:  # cunningham
            lean_mass = weight * (1 - body_fat / 100)
            return 500 + 22 * lean_mass
    else:
        raise ValueError(f"Unknown BMR formula: {formula}")


def get_bmr_formula(user_data: Dict[str, Any]) -> str:
    """Get recommended BMR formula based on available data.

    RU: Получить рекомендуемую формулу BMR на основе доступных данных.
    EN: Get recommended BMR formula based on available data.

    Args:
        user_data: Dictionary with user data

    Returns:
        Best formula name ("katch" if body_fat available, otherwise "mifflin")
    """
    return "katch" if "body_fat" in user_data and user_data["body_fat"] is not None else "mifflin"


def adjust_for_activity(bmr: float, activity: Activity) -> float:
    """Adjust BMR for activity level to get TDEE.

    RU: Корректировка BMR для уровня активности для получения TDEE.
    EN: Adjust BMR for activity level to get TDEE.

    Args:
        bmr: Basal metabolic rate in kcal/day
        activity: Activity level

    Returns:
        TDEE in kcal/day
    """
    return bmr * ACTIVITY_MULTIPLIERS[activity]


def calculate_tdee(
    age: int,
    weight: float,
    height: int,
    gender: str,
    activity: Activity,
    body_fat: Optional[float] = None,
    formula: str = "mifflin",
) -> float:
    """Calculate Total Daily Energy Expenditure.

    RU: Расчёт общего дневного энергозатрата.
    EN: Calculate total daily energy expenditure.

    Args:
        age: Age in years
        weight: Weight in kg
        height: Height in cm
        gender: "male" or "female"
        activity: Activity level
        body_fat: Optional body fat percentage
        formula: BMR formula to use

    Returns:
        TDEE in kcal/day
    """
    bmr = calculate_bmr(age, weight, height, gender, body_fat, formula)
    return adjust_for_activity(bmr, activity)


def get_macro_ratios(goal: Goal) -> Dict[str, float]:
    """Get macronutrient ratios for different goals.

    RU: Получить соотношения макронутриентов для разных целей.
    EN: Get macronutrient ratios for different goals.

    Args:
        goal: Fitness goal ("loss", "maintain", "gain")

    Returns:
        Dict with protein/carbs/fat ratios (summing to 1.0)
    """
    ratios = {
        "loss": {"protein": 0.35, "carbs": 0.40, "fat": 0.25},
        "maintain": {"protein": 0.30, "carbs": 0.45, "fat": 0.25},
        "gain": {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
    }
    return ratios[goal]


def calculate_macros(
    tdee: float,
    goal: Goal,
    protein_grams_per_kg: float = 1.6,
    body_weight: Optional[float] = None,
) -> Dict[str, float]:
    """Calculate macronutrient targets in grams.

    RU: Расчёт целевых значений макронутриентов в граммах.
    EN: Calculate macronutrient targets in grams.

    Args:
        tdee: Total daily energy expenditure in kcal
        goal: Fitness goal
        protein_grams_per_kg: Protein per kg body weight (default 1.6g/kg)
        body_weight: Body weight in kg (optional, for protein calculation)

    Returns:
        Dict with protein/carbs/fat in grams
    """
    ratios = get_macro_ratios(goal)

    # Calculate protein first if body weight available
    if body_weight and goal in ("loss", "maintain"):
        protein_g = protein_grams_per_kg * body_weight
        protein_kcal = protein_g * 4
        remaining_kcal = tdee - protein_kcal
        carbs_g = (remaining_kcal * ratios["carbs"]) / 4
        fat_g = (remaining_kcal * ratios["fat"]) / 9
    else:
        # Standard calculation
        protein_g = (tdee * ratios["protein"]) / 4
        carbs_g = (tdee * ratios["carbs"]) / 4
        fat_g = (tdee * ratios["fat"]) / 9

    return {
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_g, 1),
        "fat_g": round(fat_g, 1),
    }


def adjust_calories_for_goal(tdee: float, goal: Goal, deficit_pct: Optional[float] = None) -> float:
    """Adjust TDEE based on goal (weight loss/maintenance/gain).

    RU: Корректировка TDEE на основе цели (похудение/поддержание/набор).
    EN: Adjust TDEE based on goal.

    Args:
        tdee: Total daily energy expenditure
        goal: Fitness goal
        deficit_pct: Deficit percentage for weight loss (5-25%)

    Returns:
        Adjusted daily calories
    """
    if goal == "maintain":
        return tdee
    elif goal == "loss":
        deficit = deficit_pct or 15  # Default 15% deficit
        return tdee * (1 - deficit / 100)
    elif goal == "gain":
        surplus = 10  # 10% surplus for muscle gain
        return tdee * (1 + surplus / 100)
    else:
        raise ValueError(f"Unknown goal: {goal}")


def calculate_deficit_surplus(current_kcal: float, target_kcal: float) -> Dict[str, float]:
    """Calculate deficit/surplus information.

    RU: Расчёт информации о дефиците/профиците.
    EN: Calculate deficit/surplus information.

    Args:
        current_kcal: Current daily calories
        target_kcal: Target daily calories

    Returns:
        Dict with deficit/surplus info
    """
    difference = target_kcal - current_kcal
    pct = (difference / current_kcal) * 100 if current_kcal > 0 else 0

    return {
        "kcal_difference": difference,
        "pct_difference": round(pct, 1),
        "weekly_change_kg": difference / 7700,  # 7700 kcal ≈ 1 kg fat
        "is_deficit": difference < 0,
        "is_surplus": difference > 0,
    }
