"""
Daily Plate Algorithm

RU: Алгоритм формирования «тарелки» на день.
EN: Daily "plate" formation algorithm.

This module implements the algorithm for creating a daily meal plan based on
calorie splits, dietary flags, and nutrient coverage optimization.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .food_db import FoodItem, parse_food_db, pick_booster_for
from .recipe_db import Recipe, calculate_recipe_nutrients, parse_recipe_db, scale_recipe_to_kcal


def create_daily_plate(kcal_total: int, diet_flags: Set[str],
                      food_db: Dict[str, FoodItem] | None = None,
                      recipe_db: Dict[str, Recipe] | None = None) -> Dict:
    """
    RU: Создает план питания на день.
    EN: Creates a daily meal plan.
    
    Args:
        kcal_total: Total daily calories
        diet_flags: Dietary restrictions/preferences
        food_db: Food database (will be loaded if None)
        recipe_db: Recipe database (will be loaded if None)
        
    Returns:
        Dictionary with meal plan and nutrient analysis
    """
    if food_db is None:
        food_db = parse_food_db()
    if recipe_db is None:
        recipe_db = parse_recipe_db(food_db=food_db)

    # Define calorie splits for meals
    meal_splits = {
        "breakfast": 0.25,
        "lunch": 0.35,
        "dinner": 0.30,
        "snack": 0.10
    }

    meals = []
    total_micro_coverage = {}

    # Create meals for each time slot
    for meal_name, split in meal_splits.items():
        kcal_target = int(kcal_total * split)
        meal = create_meal(meal_name, kcal_target, diet_flags, food_db, recipe_db)
        meals.append(meal)

        # Track micro coverage
        if "micro_coverage" in meal:
            for micro, coverage in meal["micro_coverage"].items():
                if micro not in total_micro_coverage:
                    total_micro_coverage[micro] = 0
                total_micro_coverage[micro] += coverage

    # Apply boosters if needed
    meals, total_micro_coverage = apply_boosters_if_needed(
        meals, total_micro_coverage, diet_flags, food_db
    )

    return {
        "meals": meals,
        "total_kcal": kcal_total,
        "micro_coverage": total_micro_coverage
    }


def create_meal(meal_name: str, kcal_target: int, diet_flags: Set[str],
               food_db: Dict[str, FoodItem], recipe_db: Dict[str, Recipe]) -> Dict:
    """
    RU: Создает отдельный прием пищи.
    EN: Creates an individual meal.
    """
    # Find suitable recipe for this meal
    recipe = find_recipe_for_meal(meal_name, kcal_target, diet_flags, recipe_db)

    if recipe:
        # Scale recipe to calorie target
        scaled_recipe = scale_recipe_to_kcal(recipe, kcal_target, food_db)

        # Calculate nutrients
        nutrients = calculate_recipe_nutrients(scaled_recipe, food_db)

        # Calculate micro coverage (simplified)
        micro_coverage = calculate_micro_coverage(nutrients, kcal_target)

        return {
            "name": meal_name,
            "recipe": scaled_recipe.name,
            "kcal": kcal_target,
            "ingredients": scaled_recipe.ingredients,
            "nutrients": nutrients,
            "micro_coverage": micro_coverage
        }

    # Fallback to simple food item if no recipe found
    return create_fallback_meal(meal_name, kcal_target, diet_flags, food_db)


def find_recipe_for_meal(meal_name: str, kcal_target: int, diet_flags: Set[str],
                        recipe_db: Dict[str, Recipe]) -> Recipe | None:
    """
    RU: Находит подходящий рецепт для приема пищи.
    EN: Finds suitable recipe for a meal.
    """
    # Map meal names to recipe categories
    meal_to_category = {
        "breakfast": ["Овсянка с орехами"],
        "lunch": ["Гречка с тофу", "Рис с курицей"],
        "dinner": ["Гречка с тофу", "Рис с курицей"],
        "snack": ["Овсянка с орехами"]
    }

    candidates = meal_to_category.get(meal_name, [])

    # Filter by dietary flags
    for candidate_name in candidates:
        if candidate_name in recipe_db:
            recipe = recipe_db[candidate_name]
            # Check dietary flags compatibility
            if is_compatible_with_flags(recipe.flags, diet_flags):
                return recipe

    # If no specific recipe found, return any compatible recipe
    for recipe in recipe_db.values():
        if is_compatible_with_flags(recipe.flags, diet_flags):
            return recipe

    return None


def is_compatible_with_flags(recipe_flags: Set[str], diet_flags: Set[str]) -> bool:
    """
    RU: Проверяет совместимость флагов рецепта с диетическими ограничениями.
    EN: Checks recipe flag compatibility with dietary restrictions.
    """
    # If user has VEG flag, recipe must not contain non-vegetarian items
    if "VEG" in diet_flags and not recipe_flags.intersection({"VEG"}):
        # Check if recipe contains non-vegetarian ingredients
        non_veg_indicators = {"курица", "лосось", "рыба", "мясо"}
        if any(indicator in ",".join(recipe_flags).lower() for indicator in non_veg_indicators):
            return False

    # Check other flags
    incompatible_pairs = [
        ("GF", "Глютен"),  # If user is gluten-free, recipe shouldn't contain gluten
    ]

    for user_flag, recipe_indicator in incompatible_pairs:
        if user_flag in diet_flags and recipe_indicator in ",".join(recipe_flags):
            return False

    return True


def calculate_micro_coverage(nutrients: Dict[str, float], kcal_target: int) -> Dict[str, float]:
    """
    RU: Рассчитывает покрытие микронутриентов (упрощенная версия).
    EN: Calculates micronutrient coverage (simplified version).
    """
    # Simplified coverage calculation - assuming RDA per 2000 kcal
    rda_per_2000kcal = {
        "iron_mg": 18,      # mg
        "calcium_mg": 1000, # mg
        "folate_ug": 400,   # μg
        "vitamin_d_iu": 600, # IU
        "b12_ug": 2.4,      # μg
        "iodine_ug": 150,   # μg
        "magnesium_mg": 400, # mg
        "potassium_mg": 3500 # mg
    }

    coverage = {}
    for nutrient, rda in rda_per_2000kcal.items():
        actual_amount = nutrients.get(nutrient, 0)
        coverage_percent = (actual_amount / rda) * (2000 / kcal_target) * 100
        coverage[nutrient] = min(coverage_percent, 200)  # Cap at 200%

    return coverage


def create_fallback_meal(meal_name: str, kcal_target: int, diet_flags: Set[str],
                        food_db: Dict[str, FoodItem]) -> Dict:
    """
    RU: Создает запасной вариант приема пищи.
    EN: Creates fallback meal option.
    """
    # Simple implementation - just return basic info
    return {
        "name": meal_name,
        "kcal": kcal_target,
        "estimated": True
    }


def apply_boosters_if_needed(meals: List[Dict], total_micro_coverage: Dict[str, float],
                           diet_flags: Set[str], food_db: Dict[str, FoodItem]) -> Tuple[List[Dict], Dict[str, float]]:
    """
    RU: Применяет бустеры, если покрытие микронутриентов недостаточно.
    EN: Applies boosters if micronutrient coverage is insufficient.
    """
    # Check if any micronutrient coverage is below 80%
    insufficient_micros = [
        micro for micro, coverage in total_micro_coverage.items()
        if coverage < 80
    ]

    if not insufficient_micros:
        return meals, total_micro_coverage

    # Add boosters for insufficient micronutrients
    for micro in insufficient_micros[:3]:  # Limit to 3 boosters
        booster_food = pick_booster_for(micro, diet_flags, food_db)
        if booster_food:
            # Add booster to one of the meals (preferably lunch or dinner)
            for meal in meals:
                if meal["name"] in ["lunch", "dinner"]:
                    if "boosters" not in meal:
                        meal["boosters"] = []
                    meal["boosters"].append({
                        "food": booster_food,
                        "amount_g": 50  # 50g booster portion
                    })

                    # Update micro coverage
                    if booster_food in food_db:
                        food_item = food_db[booster_food]
                        nutrient_amount = food_item.get_nutrient_amount(micro, 50)
                        # Simplified update to coverage
                        total_micro_coverage[micro] += (nutrient_amount / 10)  # Rough estimate

                    break

    return meals, total_micro_coverage
