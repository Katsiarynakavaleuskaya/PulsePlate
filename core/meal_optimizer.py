"""
Meal Optimizer - Optimization Logic for Meal Plans

RU: Модуль оптимизации планов питания.
EN: Module for optimizing meal plans.

This module provides optimization algorithms to improve meal plans based on
macro balance, micronutrient coverage, cost, and user preferences.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class BoosterFood:
    """
    RU: Информация о продукте-бустере.
    EN: Booster food information.

    Attributes:
        name: Food name
        compatible_diets: Set of diet flags this food is compatible with
        allergens: Set of common allergens present in this food
    """

    name: str
    compatible_diets: Set[str]
    allergens: Set[str]


# Booster food database with diet and allergen metadata
BOOSTER_FOODS: Dict[str, List[BoosterFood]] = {
    "iron_mg": [
        BoosterFood("Spinach", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()),
        BoosterFood("Lentils", {"VEGAN", "VEG", "MEDITERRANEAN"}, set()),
        BoosterFood("Beef", {"PALEO", "KETO"}, set()),
    ],
    "calcium_mg": [
        BoosterFood("Kale", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()),
        BoosterFood("Dairy yogurt", {"VEG", "KETO", "MEDITERRANEAN"}, {"DAIRY"}),
        BoosterFood("Fortified plant milk", {"VEGAN", "VEG", "DAIRY_FREE"}, set()),
    ],
    "vitamin_d_iu": [
        BoosterFood("Mushrooms", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()),
        BoosterFood("Fatty fish", {"PALEO", "KETO", "MEDITERRANEAN"}, set()),
    ],
    "b12_ug": [
        BoosterFood("Nutritional yeast", {"VEGAN", "VEG", "PALEO", "KETO", "GF"}, set()),
        BoosterFood("Eggs", {"VEG", "PALEO", "KETO"}, {"EGG"}),
        BoosterFood("Fortified cereals", {"VEGAN", "VEG"}, set()),
    ],
    "folate_ug": [
        BoosterFood("Lentils", {"VEGAN", "VEG", "MEDITERRANEAN"}, set()),
        BoosterFood("Asparagus", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()),
    ],
    "magnesium_mg": [
        BoosterFood(
            "Pumpkin seeds", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()
        ),
        BoosterFood("Dark chocolate", {"VEGAN", "VEG", "PALEO", "KETO"}, set()),
        BoosterFood("Almonds", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, {"NUT"}),
    ],
    "potassium_mg": [
        BoosterFood("Banana", {"VEGAN", "VEG", "PALEO", "GF", "MEDITERRANEAN"}, set()),
        BoosterFood("Avocado", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()),
    ],
    "zinc_mg": [
        BoosterFood("Chickpeas", {"VEGAN", "VEG", "MEDITERRANEAN"}, set()),
        BoosterFood(
            "Pumpkin seeds", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()
        ),
    ],
    "vitamin_c_mg": [
        BoosterFood(
            "Bell peppers", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()
        ),
        BoosterFood("Citrus fruits", {"VEGAN", "VEG", "PALEO", "GF", "MEDITERRANEAN"}, set()),
    ],
    "vitamin_a_iu": [
        BoosterFood("Carrots", {"VEGAN", "VEG", "PALEO", "KETO", "GF", "MEDITERRANEAN"}, set()),
        BoosterFood("Sweet potato", {"VEGAN", "VEG", "PALEO", "GF", "MEDITERRANEAN"}, set()),
    ],
}


def optimize_macro_balance(
    meals: List[Dict[str, Any]],
    target_macros: Dict[str, float],
    tolerance_pct: float = 0.10,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    RU: Оптимизирует макробаланс в плане питания.
    EN: Optimizes macro balance in meal plan.

    Args:
        meals: List of meal dictionaries
        target_macros: Target macros {"protein_g", "fat_g", "carbs_g", "fiber_g"}
        tolerance_pct: Acceptable deviation percentage (default 10%)

    Returns:
        Tuple of (optimized_meals, balance_score)
        balance_score: 0.0 (worst) to 1.0 (perfect)

    Examples:
        >>> meals = [{"macros": {"protein_g": 30, "fat_g": 10, "carbs_g": 40}}]
        >>> target = {"protein_g": 150, "fat_g": 50, "carbs_g": 200}
        >>> optimized, score = optimize_macro_balance(meals, target)
        >>> score
        0.85
    """
    if not meals or not target_macros:
        return meals, 0.0

    # Calculate current totals
    current_macros = _aggregate_macros(meals)

    # Calculate deviation from targets
    deviations = {}
    for macro, target in target_macros.items():
        if target > 0:
            current = current_macros.get(macro, 0)
            deviation = abs(current - target) / target
            deviations[macro] = deviation

    # Calculate balance score (inverse of average deviation)
    avg_deviation = sum(deviations.values()) / len(deviations) if deviations else 0
    balance_score = max(0.0, 1.0 - avg_deviation)

    # If within tolerance, no optimization needed
    if balance_score >= (1.0 - tolerance_pct):
        return meals, balance_score

    # Simple optimization: scale meal portions
    optimized_meals = _scale_meals_to_targets(meals, current_macros, target_macros)

    # Recalculate score
    new_macros = _aggregate_macros(optimized_meals)
    new_deviations = {}
    for macro, target in target_macros.items():
        if target > 0:
            current = new_macros.get(macro, 0)
            deviation = abs(current - target) / target
            new_deviations[macro] = deviation

    new_avg_deviation = sum(new_deviations.values()) / len(new_deviations) if new_deviations else 0
    new_score = max(0.0, 1.0 - new_avg_deviation)

    return optimized_meals, new_score


def optimize_micro_coverage(
    meals: List[Dict[str, Any]],
    target_micros: Dict[str, float],
    min_coverage_pct: float = 80.0,
    diet_flags: Optional[Set[str]] = None,
    allergens: Optional[Set[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    RU: Оптимизирует покрытие микронутриентов.
    EN: Optimizes micronutrient coverage.

    Args:
        meals: List of meal dictionaries
        target_micros: Target micronutrients (RDA values)
        min_coverage_pct: Minimum acceptable coverage (default 80%)
        diet_flags: User's dietary flags (e.g., {"VEGAN", "GF"})
        allergens: User's allergen restrictions (e.g., {"NUT", "DAIRY"})

    Returns:
        Tuple of (optimized_meals, coverage_report)
        coverage_report: {micronutrient: coverage_percentage}

    Note:
        Booster suggestions respect dietary restrictions and allergens.
        If no compatible booster is found, no suggestion is added.
    """
    if not meals or not target_micros:
        return meals, {}

    # Calculate current coverage
    current_micros = _aggregate_micros(meals)
    coverage = _calculate_coverage(current_micros, target_micros)

    # Find deficient micronutrients
    deficient_micros = {micro: pct for micro, pct in coverage.items() if pct < min_coverage_pct}

    if not deficient_micros:
        return meals, coverage

    # Add boosters for deficient micros (advisory only – no nutrient changes)
    optimized_meals = [meal.copy() for meal in meals]

    # Priority order: most deficient first
    sorted_deficient = sorted(deficient_micros.items(), key=lambda x: x[1])

    for micro, current_pct in sorted_deficient[:3]:  # Limit to top 3 deficiencies
        # Add booster suggestion to last meal (usually dinner)
        if not optimized_meals:
            break
        last_meal = optimized_meals[-1]
        if "booster_suggestions" not in last_meal:
            last_meal["booster_suggestions"] = []

        # Get compatible booster respecting dietary restrictions
        booster = suggest_booster_food(micro, diet_flags, allergens)
        if booster:  # Only add if compatible booster found
            last_meal["booster_suggestions"].append(
                {
                    "micronutrient": micro,
                    "current_coverage": current_pct,
                    "target_coverage": min_coverage_pct,
                    "suggested_food": booster,
                }
            )

    # Boosters are advisory only and do not alter micronutrient totals,
    # so we return the original coverage numbers.
    return optimized_meals, coverage


def optimize_cost(
    meals: List[Dict[str, Any]],
    max_budget: Optional[float] = None,
    min_quality_score: float = 0.7,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    RU: Оптимизирует стоимость плана питания.
    EN: Optimizes meal plan cost.

    Args:
        meals: List of meal dictionaries
        max_budget: Maximum budget (optional)
        min_quality_score: Minimum nutrition quality score (0-1)

    Returns:
        Tuple of (optimized_meals, total_cost)
    """
    if not meals:
        return meals, 0.0

    # Calculate current cost
    current_cost = sum(meal.get("estimated_cost", 0) for meal in meals)

    # If no budget constraint, return as is
    if max_budget is None:
        return meals, current_cost

    # If under budget, return as is
    if current_cost <= max_budget:
        return meals, current_cost

    # Need to reduce cost while maintaining quality
    optimized_meals = _reduce_cost_preserving_quality(meals, max_budget, min_quality_score)

    new_cost = sum(meal.get("estimated_cost", 0) for meal in optimized_meals)

    return optimized_meals, new_cost


def _aggregate_macros(meals: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate macros from all meals."""
    totals: Dict[str, float] = {"protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0, "fiber_g": 0.0}

    for meal in meals:
        macros = meal.get("macros", {})
        for macro in totals:
            totals[macro] += macros.get(macro, 0)

    return totals


def _aggregate_micros(meals: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate micronutrients from all meals."""
    totals: Dict[str, float] = {}

    for meal in meals:
        micros = meal.get("micros", {})
        for micro, value in micros.items():
            if micro in totals:
                totals[micro] += value
            else:
                totals[micro] = value

    return totals


def _calculate_coverage(
    current_micros: Dict[str, float],
    target_micros: Dict[str, float],
) -> Dict[str, float]:
    """Calculate coverage percentage for each micronutrient."""
    coverage = {}

    for micro, target in target_micros.items():
        if target > 0:
            current = current_micros.get(micro, 0)
            pct = min(200.0, (current / target) * 100)
            coverage[micro] = pct
        else:
            coverage[micro] = 0.0

    return coverage


def _scale_meals_to_targets(
    meals: List[Dict[str, Any]],
    current_macros: Dict[str, float],
    target_macros: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Scale meal portions to better match target macros."""
    optimized = []

    # Calculate scaling factor based on protein (usually most important)
    protein_scale = 1.0
    if current_macros.get("protein_g", 0) > 0:
        protein_scale = target_macros.get("protein_g", 0) / current_macros["protein_g"]

    # Limit scaling to reasonable range (0.8 to 1.2)
    protein_scale = max(0.8, min(1.2, protein_scale))

    for meal in meals:
        scaled_meal = meal.copy()
        if "macros" in scaled_meal:
            scaled_macros = {k: v * protein_scale for k, v in scaled_meal["macros"].items()}
            scaled_meal["macros"] = scaled_macros

        if "kcal" in scaled_meal:
            scaled_meal["kcal"] = int(scaled_meal["kcal"] * protein_scale)

        optimized.append(scaled_meal)

    return optimized


def suggest_booster_food(
    micronutrient: str,
    diet_flags: Optional[Set[str]] = None,
    allergens: Optional[Set[str]] = None,
) -> Optional[str]:
    """
    RU: Предлагает продукт с учетом диетических ограничений и аллергий.
    EN: Suggests food rich in specific micronutrient respecting dietary restrictions.

    Args:
        micronutrient: Micronutrient to boost (e.g., "iron_mg", "calcium_mg")
        diet_flags: User's dietary flags (e.g., {"VEGAN", "GF"})
        allergens: User's allergen restrictions (e.g., {"NUT", "DAIRY", "EGG"})

    Returns:
        Food name that is compatible, or None if no compatible food found

    Examples:
        >>> _suggest_booster_food("iron_mg", {"VEGAN"}, set())
        'Spinach'
        >>> _suggest_booster_food("calcium_mg", {"VEGAN"}, set())
        'Kale'
        >>> _suggest_booster_food("calcium_mg", {"VEGAN"}, {"DAIRY"})
        'Fortified plant milk'
        >>> _suggest_booster_food("magnesium_mg", {"VEGAN"}, {"NUT"})
        'Pumpkin seeds'
    """
    if diet_flags is None:
        diet_flags = set()
    if allergens is None:
        allergens = set()

    # Get candidate boosters for this micronutrient
    candidates = BOOSTER_FOODS.get(micronutrient, [])

    if not candidates:
        return None

    # Filter by diet compatibility and allergens
    for booster in candidates:
        # Check if user's diet flags are compatible with this food
        # If user has VEGAN flag, food must have VEGAN in compatible_diets
        is_diet_compatible = True
        if diet_flags:
            # Check key restrictive diets
            if "VEGAN" in diet_flags and "VEGAN" not in booster.compatible_diets:
                is_diet_compatible = False
            elif (
                "VEG" in diet_flags
                and "VEG" not in booster.compatible_diets
                and "VEGAN" not in booster.compatible_diets
            ):
                is_diet_compatible = False
            # For other diets (KETO, PALEO), just prefer compatible options
            # but don't strictly require (they're preferences, not restrictions)

        # Check allergens - strict requirement
        has_allergen = bool(booster.allergens.intersection(allergens))

        if is_diet_compatible and not has_allergen:
            return booster.name

    # No compatible booster found
    return None


def _reduce_cost_preserving_quality(
    meals: List[Dict[str, Any]],
    max_budget: float,
    min_quality_score: float,
) -> List[Dict[str, Any]]:
    """Reduce meal plan cost while preserving nutritional quality."""
    # Simple implementation: proportionally reduce portions
    current_cost = sum(meal.get("estimated_cost", 0) for meal in meals)

    if current_cost <= max_budget:
        return meals

    # Calculate reduction factor based purely on budget
    reduction_factor = max_budget / current_cost

    # If meeting the budget would require reducing portions below the
    # allowed quality threshold, keep the original meals and let the
    # caller decide how to handle the budget shortfall.
    if reduction_factor < min_quality_score:
        return meals

    optimized = []
    for meal in meals:
        reduced_meal = meal.copy()

        # Reduce cost
        if "estimated_cost" in reduced_meal:
            reduced_meal["estimated_cost"] *= reduction_factor

        # Scale nutrients proportionally
        if "macros" in reduced_meal:
            reduced_meal["macros"] = {
                k: v * reduction_factor for k, v in reduced_meal["macros"].items()
            }

        if "kcal" in reduced_meal:
            reduced_meal["kcal"] = int(reduced_meal["kcal"] * reduction_factor)

        optimized.append(reduced_meal)

    return optimized
