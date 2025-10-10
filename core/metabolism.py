"""Metabolism and Energy Expenditure Calculations.

This module provides functions for calculating Basal Metabolic Rate (BMR),
Total Daily Energy Expenditure (TDEE), macronutrient distributions, and
related metabolic calculations based on WHO/EFSA guidelines.

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


# Approximate kcal per kg of body fat (used for weight change estimates)
# Note: This is a rough approximation; actual values vary (7000-8000 kcal/kg)
KCAL_PER_KG_FAT = 7700


def calculate_bmr(
    age: int,
    weight: float,
    height: int,
    gender: str,
    body_fat: Optional[float] = None,
    formula: str = "mifflin",
) -> float:
    """Calculate Basal Metabolic Rate using various formulas.

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
    if age <= 0:
        raise ValueError("Age must be positive")
    if weight <= 0:
        raise ValueError("Weight must be positive")
    if height <= 0:
        raise ValueError("Height must be positive")
    if body_fat is not None and not (0 <= body_fat <= 100):
        raise ValueError("Body fat percentage must be between 0 and 100")

    # Normalize and validate gender
    gender_norm = gender.strip().lower()
    if gender_norm not in ("male", "female"):
        raise ValueError(f"Gender must be 'male' or 'female', got: {gender}")

    if formula == "mifflin":
        if gender_norm == "male":
            return 10 * weight + 6.25 * height - 5 * age + 5
        else:
            return 10 * weight + 6.25 * height - 5 * age - 161
    elif formula == "harris":
        if gender_norm == "male":
            return 66.5 + 13.75 * weight + 5.003 * height - 6.755 * age
        else:
            return 655.1 + 9.563 * weight + 1.85 * height - 4.676 * age
    elif formula in ("katch", "cunningham"):
        if body_fat is None:
            raise ValueError(f"body_fat required for {formula} formula")  # noqa: TRY003
        if formula == "katch":
            lean_mass = weight * (1 - body_fat / 100)
            return 370 + 21.6 * lean_mass
        else:  # cunningham
            lean_mass = weight * (1 - body_fat / 100)
            return 500 + 22 * lean_mass
    else:
        raise ValueError(f"Unknown BMR formula: {formula}")  # noqa: TRY003


def get_bmr_formula(user_data: Dict[str, Any]) -> str:
    """Get recommended BMR formula based on available data.

    EN: Get recommended BMR formula based on available data.

    Args:
        user_data: Dictionary with user data

    Returns:
        Best formula name ("katch" if body_fat available, otherwise "mifflin")
    """
    return "katch" if "body_fat" in user_data and user_data["body_fat"] is not None else "mifflin"


def adjust_for_activity(bmr: float, activity: Activity) -> float:
    """Adjust BMR for activity level to get TDEE.

    EN: Adjust BMR for activity level to get TDEE.

    Args:
        bmr: Basal metabolic rate in kcal/day
        activity: Activity level

    Returns:
        TDEE in kcal/day
    """
    if activity not in ACTIVITY_MULTIPLIERS:
        raise ValueError(f"Invalid activity: {activity}")  # noqa: TRY003
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
    if goal not in ratios:
        raise ValueError(f"Invalid goal: {goal}")  # noqa: TRY003
    return ratios[goal]


def calculate_macros(
    tdee: float,
    goal: Goal,
    protein_grams_per_kg: float = 1.6,
    body_weight: Optional[float] = None,
) -> Dict[str, float]:
    """Calculate macronutrient targets in grams.

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
        if remaining_kcal <= 0:
            raise ValueError(
                "Protein target exceeds available calories; adjust protein_grams_per_kg or increase tdee."
            )
        else:
            # Renormalize carbs/fat split to use all remaining calories
            residual_ratio = ratios["carbs"] + ratios["fat"]
            if residual_ratio <= 0:
                carbs_g = 0.0
                fat_g = 0.0
            else:
                carbs_kcal = remaining_kcal * (ratios["carbs"] / residual_ratio)
                fat_kcal = remaining_kcal * (ratios["fat"] / residual_ratio)
                carbs_g = carbs_kcal / 4
                fat_g = fat_kcal / 9
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


def adjust_calories_for_goal(
    tdee: float,
    goal: Goal,
    deficit_pct: Optional[float] = None,
    surplus_pct: Optional[float] = None,
) -> float:
    """Adjust TDEE based on goal (weight loss/maintenance/gain).

    EN: Adjust TDEE based on goal.

    Args:
        tdee: Total daily energy expenditure
        goal: Fitness goal
        deficit_pct: Deficit percentage for weight loss (5-25%)
        surplus_pct: Surplus percentage for weight gain (5-20%)

    Returns:
        Adjusted daily calories
    """
    if goal == "maintain":
        return tdee
    elif goal == "loss":
        deficit = deficit_pct or 15  # Default 15% deficit
        if deficit < 5 or deficit > 25:
            raise ValueError("Deficit percentage must be between 5 and 25")
        return tdee * (1 - deficit / 100)
    elif goal == "gain":
        surplus = surplus_pct or 10  # Default 10% surplus for muscle gain
        if surplus < 5 or surplus > 20:
            raise ValueError("Surplus percentage must be between 5 and 20")
        return tdee * (1 + surplus / 100)
    else:
        raise ValueError(f"Unknown goal: {goal}")  # noqa: TRY003


def calculate_deficit_surplus(current_kcal: float, target_kcal: float) -> Dict[str, float]:
    """Calculate deficit/surplus information.

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
        "weekly_change_kg": (difference * 7) / KCAL_PER_KG_FAT,
        "is_deficit": difference < 0,
        "is_surplus": difference > 0,
    }


# Higher-level convenience functions for BMR/TDEE calculations
# These are moved here from nutrition_core.py to avoid circular imports


def calculate_all_bmr(
    weight: float,
    height: float,
    age: int,
    sex: str,
    bodyfat_percent: Optional[float] = None,
) -> Dict[str, float]:
    """
    Calculate BMR using all available formulas.

    EN: Calculate BMR using all available formulas.

    Args:
        weight: Weight in kilograms
        height: Height in centimeters
        age: Age in years
        sex: Biological sex ("male" or "female")
        bodyfat_percent: Optional body fat percentage for Katch-McArdle

    Returns:
        Dictionary with BMR values from different formulas
    """
    results = {
        "mifflin": calculate_bmr(age, weight, int(height), sex, formula="mifflin"),
        "harris": calculate_bmr(age, weight, int(height), sex, formula="harris"),
    }

    if bodyfat_percent is not None:
        results["katch"] = calculate_bmr(
            age, weight, int(height), sex, bodyfat_percent, formula="katch"
        )
        results["cunningham"] = calculate_bmr(
            age, weight, int(height), sex, bodyfat_percent, formula="cunningham"
        )
    return results


def calculate_all_tdee(
    bmr_results: Dict[str, float],
    activity: Activity,
) -> Dict[str, float]:
    """
    Calculate TDEE for all BMR formulas.

    EN: Calculate TDEE for all BMR formulas.

    Args:
        bmr_results: Dictionary of BMR values from different formulas
        activity: Activity level

    Returns:
        Dictionary with TDEE values for each formula
    """
    return {
        formula: round(adjust_for_activity(bmr_value, activity), 0)
        for formula, bmr_value in bmr_results.items()
    }
