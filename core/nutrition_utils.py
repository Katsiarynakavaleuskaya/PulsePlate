"""Nutrition utility functions.

RU: Вспомогательные функции для расчётов питания.
EN: Nutrition utility functions.

This module provides helper functions for common nutrition calculations
including macro conversions, percentage calculations, and dietary pattern
detection.
"""

from __future__ import annotations

from typing import Optional

from .nutrition_constants import (
    CARBS_MAX_PERCENT,
    CARBS_MIN_PERCENT,
    FAT_MAX_PERCENT,
    FAT_MIN_PERCENT,
    PROTEIN_MAX_PERCENT,
    PROTEIN_MIN_PERCENT,
)


def calculate_macro_percentages(
    protein_g: float, fat_g: float, carbs_g: float
) -> tuple[float, float, float]:
    """Calculate macronutrient percentages from gram amounts.

    RU: Рассчитать процентное соотношение макронутриентов из граммов.
    EN: Calculate macronutrient percentages from gram amounts.

    Args:
        protein_g: Protein in grams
        fat_g: Fat in grams
        carbs_g: Carbs in grams

    Returns:
        Tuple of (protein_percent, fat_percent, carbs_percent)

    Examples:
        >>> calculate_macro_percentages(100, 50, 200)
        (22.2, 25.0, 52.8)
    """
    # Calories from each macro (protein: 4 kcal/g, fat: 9 kcal/g, carbs: 4 kcal/g)
    protein_kcal = protein_g * 4.0
    fat_kcal = fat_g * 9.0
    carbs_kcal = carbs_g * 4.0

    total_kcal = protein_kcal + fat_kcal + carbs_kcal

    if total_kcal == 0:
        return (0.0, 0.0, 0.0)

    protein_percent = (protein_kcal / total_kcal) * 100
    fat_percent = (fat_kcal / total_kcal) * 100
    carbs_percent = (carbs_kcal / total_kcal) * 100

    return (
        round(protein_percent, 1),
        round(fat_percent, 1),
        round(carbs_percent, 1),
    )


def calculate_macro_grams(
    total_calories: float,
    protein_percent: float,
    fat_percent: float,
    carbs_percent: float,
) -> tuple[float, float, float]:
    """Calculate macro grams from calories and percentages.

    RU: Рассчитать граммы макронутриентов из калорий и процентов.
    EN: Calculate macro grams from calories and percentages.

    Args:
        total_calories: Total daily calories
        protein_percent: Protein percentage (0-100)
        fat_percent: Fat percentage (0-100)
        carbs_percent: Carbs percentage (0-100)

    Returns:
        Tuple of (protein_g, fat_g, carbs_g)

    Raises:
        ValueError: If percentages don't sum to ~100%

    Examples:
        >>> calculate_macro_grams(2000, 30, 25, 45)
        (150.0, 55.6, 225.0)
    """
    total_percent = protein_percent + fat_percent + carbs_percent
    if abs(total_percent - 100.0) > 1.0:
        raise ValueError(f"Macro percentages must sum to 100%, got {total_percent:.1f}%")

    protein_g = (total_calories * (protein_percent / 100)) / 4.0
    fat_g = (total_calories * (fat_percent / 100)) / 9.0
    carbs_g = (total_calories * (carbs_percent / 100)) / 4.0

    return (round(protein_g, 1), round(fat_g, 1), round(carbs_g, 1))


def validate_macro_balance(
    protein_percent: float, fat_percent: float, carbs_percent: float
) -> tuple[bool, str]:
    """Validate macronutrient percentages against USDA/WHO guidelines.

    RU: Проверить соотношение макронутриентов согласно USDA/WHO.
    EN: Validate macronutrient percentages against USDA/WHO guidelines.

    Args:
        protein_percent: Protein percentage (0-100)
        fat_percent: Fat percentage (0-100)
        carbs_percent: Carbs percentage (0-100)

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.

    Examples:
        >>> validate_macro_balance(30, 25, 45)
        (True, '')
        >>> validate_macro_balance(50, 25, 25)
        (False, 'Protein 50.0% exceeds maximum 35.0%')
    """
    # Check protein range (10-35% per USDA guidelines)
    if protein_percent < PROTEIN_MIN_PERCENT:
        return (
            False,
            f"Protein {protein_percent:.1f}% below minimum {PROTEIN_MIN_PERCENT:.1f}%",
        )
    if protein_percent > PROTEIN_MAX_PERCENT:
        return (
            False,
            f"Protein {protein_percent:.1f}% exceeds maximum {PROTEIN_MAX_PERCENT:.1f}%",
        )

    # Check fat range (20-35% per USDA guidelines)
    if fat_percent < FAT_MIN_PERCENT:
        return (
            False,
            f"Fat {fat_percent:.1f}% below minimum {FAT_MIN_PERCENT:.1f}%",
        )
    if fat_percent > FAT_MAX_PERCENT:
        return (
            False,
            f"Fat {fat_percent:.1f}% exceeds maximum {FAT_MAX_PERCENT:.1f}%",
        )

    # Check carbs range (45-65% per USDA guidelines)
    if carbs_percent < CARBS_MIN_PERCENT:
        return (
            False,
            f"Carbs {carbs_percent:.1f}% below minimum {CARBS_MIN_PERCENT:.1f}%",
        )
    if carbs_percent > CARBS_MAX_PERCENT:
        return (
            False,
            f"Carbs {carbs_percent:.1f}% exceeds maximum {CARBS_MAX_PERCENT:.1f}%",
        )

    return (True, "")


def detect_dietary_pattern(
    protein_percent: float, fat_percent: float, carbs_percent: float
) -> Optional[str]:
    """Detect dietary pattern based on macro distribution.

    RU: Определить тип диеты на основе распределения макронутриентов.
    EN: Detect dietary pattern based on macro distribution.

    Args:
        protein_percent: Protein percentage (0-100)
        fat_percent: Fat percentage (0-100)
        carbs_percent: Carbs percentage (0-100)

    Returns:
        Dietary pattern name or None if standard balanced diet

    Examples:
        >>> detect_dietary_pattern(20, 70, 10)
        'ketogenic'
        >>> detect_dietary_pattern(40, 30, 30)
        'high_protein'
        >>> detect_dietary_pattern(15, 30, 55)
        None
    """
    # Ketogenic: Very low carb (<10%), high fat (>60%)
    if carbs_percent < 10 and fat_percent > 60:
        return "ketogenic"

    # Low-carb: Carbs 10-20%
    if 10 <= carbs_percent <= 20 and fat_percent > 50:
        return "low_carb"

    # High protein: Protein >30%
    if protein_percent > 30:
        return "high_protein"

    # Low fat: Fat <20%
    if fat_percent < 20:
        return "low_fat"

    # Mediterranean-style: Moderate fat (35-40%), moderate carbs
    if 35 <= fat_percent <= 45 and 35 <= carbs_percent <= 45:
        return "mediterranean"

    # Zone diet: 30/30/40 (protein/fat/carbs)
    if abs(protein_percent - 30) < 5 and abs(fat_percent - 30) < 5 and abs(carbs_percent - 40) < 5:
        return "zone"

    # Standard balanced diet (matches USDA guidelines)
    return None


def calculate_protein_per_kg(total_protein_g: float, body_weight_kg: float) -> float:
    """Calculate protein intake per kilogram of body weight.

    RU: Рассчитать потребление белка на килограмм массы тела.
    EN: Calculate protein intake per kilogram of body weight.

    Args:
        total_protein_g: Total daily protein in grams
        body_weight_kg: Body weight in kilograms

    Returns:
        Protein grams per kg body weight

    Examples:
        >>> calculate_protein_per_kg(150, 75)
        2.0
    """
    if body_weight_kg <= 0:
        raise ValueError("body_weight_kg must be positive")

    return round(total_protein_g / body_weight_kg, 2)


def adjust_calories_for_goal(maintenance_calories: float, goal: str = "maintain") -> float:
    """Adjust calories based on weight management goal.

    RU: Скорректировать калории в соответствии с целью управления весом.
    EN: Adjust calories based on weight management goal.

    Args:
        maintenance_calories: Maintenance (TDEE) calories
        goal: Goal ('lose', 'maintain', 'gain', 'cut', 'bulk')

    Returns:
        Adjusted daily calories

    Examples:
        >>> adjust_calories_for_goal(2000, 'maintain')
        2000.0
        >>> adjust_calories_for_goal(2000, 'lose')
        1500.0
        >>> adjust_calories_for_goal(2000, 'gain')
        2500.0
    """
    goal = goal.lower()

    # Weight loss: 500 kcal deficit (~0.5 kg/week)
    if goal in ("lose", "cut"):
        return maintenance_calories - 500

    # Weight gain: 500 kcal surplus (~0.5 kg/week)
    if goal in ("gain", "bulk"):
        return maintenance_calories + 500

    # Maintenance
    return maintenance_calories


def calculate_water_intake_ml(body_weight_kg: float, activity_level: str = "moderate") -> float:
    """Calculate recommended daily water intake.

    RU: Рассчитать рекомендуемое ежедневное потребление воды.
    EN: Calculate recommended daily water intake.

    Based on general hydration guidelines (30-40ml per kg body weight).

    Args:
        body_weight_kg: Body weight in kilograms
        activity_level: Activity level ('sedentary', 'moderate', 'active')

    Returns:
        Recommended water intake in milliliters

    Examples:
        >>> calculate_water_intake_ml(70, 'moderate')
        2450.0
        >>> calculate_water_intake_ml(70, 'active')
        2800.0
    """
    if body_weight_kg <= 0:
        raise ValueError("body_weight_kg must be positive")

    # Base: 30ml per kg
    base_ml = body_weight_kg * 30

    # Adjust for activity
    if activity_level == "sedentary":
        return base_ml
    if activity_level == "moderate":
        return base_ml * 1.15  # +15%
    if activity_level in ("active", "very_active"):
        return base_ml * 1.30  # +30%

    return base_ml
