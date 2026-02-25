"""
Nutrition analysis facade module.

RU: Модуль фасада для анализа питания.
EN: Facade module for nutrition analysis.

This module provides thin wrapper functions for nutrition analysis operations
as part of the planner_engines_advanced feature flag enablement.
"""

from typing import Any, Dict, List, Optional


def analyze_nutrition(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyze nutrition data and return computed metrics.

    RU: Анализирует данные о питании и возвращает вычисленные метрики.
    EN: Analyzes nutrition data and returns computed metrics.

    Args:
        data: Dictionary containing nutrition information with optional keys:
              - protein: float (grams)
              - carbs: float (grams)
              - fat: float (grams)
              - calories: float (kcal)

    Returns:
        Dictionary with analysis results including macro percentages,
        or None if input is invalid.

    Example:
        >>> analyze_nutrition({"protein": 50, "carbs": 200, "fat": 70})
        {"macros": {"protein_pct": 15.6, "carbs_pct": 62.5, "fat_pct": 21.9}, ...}
    """
    if not isinstance(data, dict):
        return None

    if not data:
        return {"macros": {}, "totals": {}, "status": "empty"}

    # Extract macros with defaults
    protein = data.get("protein", 0)
    carbs = data.get("carbs", 0)
    fat = data.get("fat", 0)

    # Validate numeric types
    try:
        protein = float(protein) if protein else 0.0
        carbs = float(carbs) if carbs else 0.0
        fat = float(fat) if fat else 0.0
    except (TypeError, ValueError):
        return {"macros": {}, "totals": {}, "status": "invalid_values"}

    # Calculate calories from macros (4 cal/g protein, 4 cal/g carbs, 9 cal/g fat)
    calories_from_protein = protein * 4
    calories_from_carbs = carbs * 4
    calories_from_fat = fat * 9
    total_calories = calories_from_protein + calories_from_carbs + calories_from_fat

    # Calculate percentages
    if total_calories > 0:
        protein_pct = round((calories_from_protein / total_calories) * 100, 1)
        carbs_pct = round((calories_from_carbs / total_calories) * 100, 1)
        fat_pct = round((calories_from_fat / total_calories) * 100, 1)
    else:
        protein_pct = 0.0
        carbs_pct = 0.0
        fat_pct = 0.0

    return {
        "macros": {
            "protein_pct": protein_pct,
            "carbs_pct": carbs_pct,
            "fat_pct": fat_pct,
        },
        "totals": {
            "protein_g": protein,
            "carbs_g": carbs,
            "fat_g": fat,
            "calories": round(total_calories, 1),
        },
        "status": "analyzed",
    }


def calculate_nutrition_score(data: Dict[str, Any]) -> Optional[float]:
    """
    Calculate a nutrition score from 0-100 based on macro balance.

    RU: Вычисляет оценку питания от 0 до 100 на основе баланса макронутриентов.
    EN: Calculates a nutrition score from 0-100 based on macronutrient balance.

    Args:
        data: Dictionary containing nutrition information with keys:
              - protein: float (grams)
              - carbs: float (grams)
              - fat: float (grams)

    Returns:
        Float score from 0-100, or None if input is invalid.
        Higher scores indicate better macro balance relative to ideal ratios.

    Note:
        Ideal ratios used: 30% protein, 40% carbs, 30% fat (by calories).
    """
    if not isinstance(data, dict):
        return None

    if not data:
        return 0.0

    # Get analysis first
    analysis = analyze_nutrition(data)
    if analysis is None or analysis.get("status") == "invalid_values":
        return None

    macros = analysis.get("macros", {})

    # Ideal ratios (by calories): 30% protein, 40% carbs, 30% fat
    ideal_protein = 30.0
    ideal_carbs = 40.0
    ideal_fat = 30.0

    protein_pct = macros.get("protein_pct", 0.0)
    carbs_pct = macros.get("carbs_pct", 0.0)
    fat_pct = macros.get("fat_pct", 0.0)

    # Calculate deviation from ideal (lower is better)
    protein_dev = abs(protein_pct - ideal_protein)
    carbs_dev = abs(carbs_pct - ideal_carbs)
    fat_dev = abs(fat_pct - ideal_fat)

    # Total deviation (max possible is ~200 if completely off)
    total_deviation = protein_dev + carbs_dev + fat_dev

    # Convert to score (0-100, where 100 is perfect)
    # Max deviation ~100 (e.g., 100% fat would be 30+40+70=140, but realistic max ~100)
    score = max(0.0, 100.0 - total_deviation)

    return float(round(score, 1))


def get_nutrition_recommendations(data: Dict[str, Any]) -> Optional[List[str]]:
    """
    Generate nutrition recommendations based on analysis.

    RU: Генерирует рекомендации по питанию на основе анализа.
    EN: Generates nutrition recommendations based on analysis.

    Args:
        data: Dictionary containing nutrition information.

    Returns:
        List of recommendation strings, or None if input is invalid.
    """
    if not isinstance(data, dict):
        return None

    if not data:
        return ["Add nutrition data to receive recommendations."]

    analysis = analyze_nutrition(data)
    if analysis is None or analysis.get("status") == "invalid_values":
        return None

    macros = analysis.get("macros", {})

    recommendations: List[str] = []

    protein_pct = macros.get("protein_pct", 0.0)
    carbs_pct = macros.get("carbs_pct", 0.0)
    fat_pct = macros.get("fat_pct", 0.0)

    # Check protein
    if protein_pct < 20:
        recommendations.append("Consider increasing protein intake for better satiety.")
    elif protein_pct > 40:
        recommendations.append("Protein intake is high; ensure adequate hydration.")

    # Check carbs
    if carbs_pct < 30:
        recommendations.append("Consider adding more complex carbohydrates for energy.")
    elif carbs_pct > 55:
        recommendations.append("Carbohydrate intake is high; consider balancing with protein.")

    # Check fat
    if fat_pct < 20:
        recommendations.append("Consider adding healthy fats for nutrient absorption.")
    elif fat_pct > 40:
        recommendations.append("Fat intake is elevated; consider reducing saturated fats.")

    if not recommendations:
        recommendations.append("Macronutrient balance looks good!")

    return recommendations


def validate_nutrition_data(data: Any) -> bool:
    """
    Validate that nutrition data is properly formatted.

    RU: Проверяет, что данные о питании правильно отформатированы.
    EN: Validates that nutrition data is properly formatted.

    Args:
        data: Data to validate.

    Returns:
        True if data is a valid nutrition dictionary, False otherwise.
    """
    if not isinstance(data, dict):
        return False

    # Check for expected nutrient keys
    valid_keys = {"protein", "carbs", "fat", "calories", "fiber", "sugar", "sodium"}

    # At least one nutrient key should be present for meaningful data
    has_nutrient = any(key in data for key in valid_keys)

    if not has_nutrient and data:
        # Non-empty dict but no recognized keys
        return False

    # Validate numeric values if present
    for key in valid_keys:
        if key in data:
            value = data[key]
            if value is not None:
                try:
                    float(value)
                except (TypeError, ValueError):
                    return False

    return True
