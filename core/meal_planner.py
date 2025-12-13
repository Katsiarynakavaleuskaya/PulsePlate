"""
Meal Planner - Core Meal Planning Logic

RU: Модуль планирования приемов пищи.
EN: Module for meal planning functionality.

This module provides the core meal planning engine that creates daily
and weekly meal plans based on calorie targets, dietary restrictions,
and nutrient coverage optimization.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .calorie_distributor import distribute_calories, apply_weekly_variation
from .dietary_constraints import normalize_diet_flags, is_recipe_compatible
from .targets import LOW_CARB_MAX_PERCENT
from .rules_who import WHO_MACRONUTRIENT_RANGES

logger = logging.getLogger(__name__)


@dataclass
class MealPlan:
    """
    RU: План одного приема пищи.
    EN: Single meal plan.
    """

    name: str
    kcal_target: int
    recipe_name: Optional[str] = None
    ingredients: Dict[str, float] = field(default_factory=dict)
    macros: Dict[str, float] = field(default_factory=dict)
    micros: Dict[str, float] = field(default_factory=dict)
    boosters: List[Dict[str, Any]] = field(default_factory=list)
    estimated_cost: float = 0.0


@dataclass
class DailyMealPlan:
    """
    RU: План питания на день.
    EN: Daily meal plan.
    """

    day: int
    total_kcal: int
    meals: List[MealPlan]
    total_macros: Dict[str, float] = field(default_factory=dict)
    total_micros: Dict[str, float] = field(default_factory=dict)
    micro_coverage: Dict[str, float] = field(default_factory=dict)
    tips: List[str] = field(default_factory=list)
    total_cost: float = 0.0


@dataclass
class WeeklyMealPlan:
    """
    RU: План питания на неделю.
    EN: Weekly meal plan.
    """

    days: List[DailyMealPlan]
    average_kcal: int
    shopping_list: Dict[str, float] = field(default_factory=dict)
    total_cost: float = 0.0


def create_meal_plan(
    meal_name: str,
    kcal_target: int,
    diet_flags: Optional[Set[str]] = None,
    recipe_db: Optional[Any] = None,
) -> MealPlan:
    """
    RU: Создает план для одного приема пищи.
    EN: Creates a plan for a single meal.

    Args:
        meal_name: Name of the meal (breakfast, lunch, dinner, snack)
        kcal_target: Target calories for this meal
        diet_flags: Dietary restrictions/preferences
        recipe_db: Recipe database (optional)

    Returns:
        MealPlan with selected recipe and nutrients
    """
    if diet_flags is None:
        diet_flags = set()

    normalized_flags = normalize_diet_flags(diet_flags)

    meal = MealPlan(
        name=meal_name,
        kcal_target=kcal_target,
    )

    # Try to find suitable recipe from database
    if recipe_db is not None:
        recipe = _select_recipe_for_meal(meal_name, kcal_target, normalized_flags, recipe_db)
        if recipe:
            meal.recipe_name = recipe.get("name", "Unknown")
            meal.ingredients = recipe.get("ingredients", {})
            meal.macros = recipe.get("macros", {})
            meal.micros = recipe.get("micros", {})
            meal.estimated_cost = recipe.get("cost", 0.0)

    # If no recipe found, create simple fallback
    if not meal.recipe_name:
        meal = _create_fallback_meal(meal_name, kcal_target, normalized_flags)

    return meal


def _select_recipe_for_meal(
    meal_name: str,
    kcal_target: int,
    diet_flags: Set[str],
    recipe_db: Any,
) -> Optional[Dict[str, Any]]:
    """
    RU: Выбирает подходящий рецепт для приема пищи.
    EN: Selects suitable recipe for a meal.
    """
    # Map meal names to recipe categories
    meal_preferences = {
        "breakfast": ["breakfast", "oatmeal", "eggs", "smoothie"],
        "lunch": ["lunch", "salad", "bowl", "main"],
        "dinner": ["dinner", "main", "protein"],
        "snack": ["snack", "fruit", "nuts", "bar"],
    }

    preferred_categories = meal_preferences.get(meal_name, ["main"])

    # Try to get recipes from database
    try:
        if hasattr(recipe_db, "get_recipes_by_category"):
            recipes = recipe_db.get_recipes_by_category(preferred_categories)
        elif hasattr(recipe_db, "pick_base_recipe"):
            # Legacy interface (menu_engine_new.py style)
            meal_index = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}.get(meal_name, 0)
            recipe = recipe_db.pick_base_recipe(list(diet_flags), meal_index)
            if recipe:
                return _convert_recipe_to_dict(recipe)
            return None
        else:
            # Fallback: iterate all recipes
            if isinstance(recipe_db, dict):
                recipes = list(recipe_db.values())
            elif isinstance(recipe_db, list):
                recipes = recipe_db
            else:
                recipes = []
    except AttributeError as e:
        # Expected: recipe_db doesn't support the interface
        logger.debug(f"Recipe DB does not support expected interface: {e}")
        return None
    except TypeError as e:
        # Unexpected type error - log and return None (graceful degradation)
        logger.error(f"Unexpected TypeError in recipe selection: {e}", exc_info=True)
        return None

    # Filter by compatibility
    compatible_recipes = []
    for recipe in recipes:
        # Guard against non-dict items
        if not isinstance(recipe, dict):
            logger.warning(f"Skipping non-dict recipe item: {type(recipe).__name__}")
            continue

        # Safely extract recipe attributes with defaults
        recipe_flags = set(recipe.get("flags", []))
        recipe_name = recipe.get("name", "")

        if is_recipe_compatible(recipe_flags, diet_flags, recipe_name):
            compatible_recipes.append(recipe)

    # Select recipe closest to calorie target
    if compatible_recipes:
        best_recipe: Dict[str, Any] = min(
            compatible_recipes, key=lambda r: abs(r.get("kcal", 0) - kcal_target)
        )
        return best_recipe

    return None


def _convert_recipe_to_dict(recipe: Any) -> Dict[str, Any]:
    """Convert recipe object to dictionary format.

    Ensures 'cost' key is always present for downstream code.
    Returns a new dict without mutating the input.
    """
    if isinstance(recipe, dict):
        # Return new dict with cost defaulted (avoid mutating input)
        return {**recipe, "cost": recipe.get("cost", 0.0)}

    recipe_dict = {}
    if hasattr(recipe, "name"):
        recipe_dict["name"] = recipe.name
    if hasattr(recipe, "ingredients"):
        recipe_dict["ingredients"] = recipe.ingredients
    if hasattr(recipe, "macros"):
        recipe_dict["macros"] = recipe.macros
    if hasattr(recipe, "micros"):
        recipe_dict["micros"] = recipe.micros
    if hasattr(recipe, "kcal"):
        recipe_dict["kcal"] = recipe.kcal
    # Always set cost key (from object attribute or default)
    recipe_dict["cost"] = recipe.cost if hasattr(recipe, "cost") else 0.0

    return recipe_dict


def _create_fallback_meal(
    meal_name: str,
    kcal_target: int,
    diet_flags: Set[str],
) -> MealPlan:
    """
    RU: Создает запасной вариант приема пищи.
    EN: Creates fallback meal option.

    Note:
        Expects diet_flags to already be normalized by the caller.
        Uses WHO-based macro percentages from core/targets.py and core/rules_who.py.
    """
    # Adjust macro distribution for key dietary patterns
    # diet_flags should already be normalized by caller
    if "KETO" in diet_flags:
        # Very low carb, high fat pattern (using KETO_MAX_CARB_PERCENT from targets.py)
        protein_pct = 0.25  # 25% protein
        carbs_pct = 0.05  # 5% carbs (stricter than KETO_MAX_CARB_PERCENT for fallback)
        fat_pct = 0.70  # 70% fat (high fat emphasis)
    elif "LOW_CARB" in diet_flags:
        # Moderately low carb (using LOW_CARB_MAX_PERCENT from targets.py)
        protein_pct = 0.35  # 35% protein (at WHO upper range)
        carbs_pct = LOW_CARB_MAX_PERCENT  # 25% carbs (from targets.py)
        fat_pct = 1.0 - protein_pct - carbs_pct  # Remaining for fat (40%)
    elif meal_name == "breakfast":
        # Higher carbs for morning energy (WHO balanced range)
        protein_pct = 0.25  # 25% protein
        carbs_pct = 0.50  # 50% carbs (mid WHO range)
        fat_pct = 0.25  # 25% fat
    elif meal_name == "snack":
        # Balanced, smaller portions (WHO balanced range)
        protein_pct = 0.30  # 30% protein
        carbs_pct = 0.40  # 40% carbs
        fat_pct = 0.30  # 30% fat
    else:  # lunch, dinner
        # Balanced meal (WHO balanced range)
        protein_pct = 0.30  # 30% protein
        carbs_pct = 0.40  # 40% carbs
        fat_pct = 0.30  # 30% fat

    protein_g = (kcal_target * protein_pct) / 4
    carbs_g = (kcal_target * carbs_pct) / 4
    fat_g = (kcal_target * fat_pct) / 9

    # Calculate fiber based on WHO recommendation: 14g per 1000 kcal
    # Reference: WHO_MACRONUTRIENT_RANGES["fiber_g_per_1000_cal"] = 14
    fiber_per_1000_cal = WHO_MACRONUTRIENT_RANGES["fiber_g_per_1000_cal"]
    fiber_g = round((kcal_target / 1000.0) * fiber_per_1000_cal, 1)

    return MealPlan(
        name=meal_name,
        kcal_target=kcal_target,
        recipe_name=f"Balanced {meal_name}",
        macros={
            "protein_g": round(protein_g, 1),
            "carbs_g": round(carbs_g, 1),
            "fat_g": round(fat_g, 1),
            "fiber_g": fiber_g,
        },
    )


def create_daily_meal_plan(
    total_kcal: int,
    diet_flags: Optional[Set[str]] = None,
    num_meals: int = 4,
    recipe_db: Optional[Any] = None,
) -> DailyMealPlan:
    """
    RU: Создает план питания на день.
    EN: Creates a daily meal plan.

    Args:
        total_kcal: Total daily calorie target
        diet_flags: Dietary restrictions/preferences
        num_meals: Number of meals (3 or 4)
        recipe_db: Recipe database (optional)

    Returns:
        DailyMealPlan with all meals for the day
    """
    if diet_flags is None:
        diet_flags = set()

    # Distribute calories across meals
    distribution = distribute_calories(total_kcal, num_meals=num_meals)

    # Create individual meals
    meals: List[MealPlan] = []
    total_macros = {"protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0, "fiber_g": 0.0}
    total_cost = 0.0

    for meal_cal in distribution.meals:
        meal = create_meal_plan(
            meal_name=meal_cal.name,
            kcal_target=meal_cal.kcal,
            diet_flags=diet_flags,
            recipe_db=recipe_db,
        )
        meals.append(meal)

        # Aggregate macros and cost
        for macro, value in meal.macros.items():
            if macro in total_macros:
                total_macros[macro] += value
        total_cost += meal.estimated_cost

    return DailyMealPlan(
        day=1,
        total_kcal=total_kcal,
        meals=meals,
        total_macros=total_macros,
        total_cost=total_cost,
    )


def create_weekly_meal_plan(
    daily_kcal_target: int,
    diet_flags: Optional[Set[str]] = None,
    num_meals: int = 4,
    recipe_db: Optional[Any] = None,
) -> WeeklyMealPlan:
    """
    RU: Создает план питания на неделю.
    EN: Creates a weekly meal plan.

    Args:
        daily_kcal_target: Average daily calorie target
        diet_flags: Dietary restrictions/preferences
        num_meals: Number of meals per day (3 or 4)
        recipe_db: Recipe database (optional)

    Returns:
        WeeklyMealPlan with 7 days of meal plans
    """
    if diet_flags is None:
        diet_flags = set()

    days: List[DailyMealPlan] = []
    total_weekly_kcal = 0

    for day_index in range(7):
        # Apply slight variation to prevent monotony
        day_kcal = apply_weekly_variation(daily_kcal_target, day_index)

        daily_plan = create_daily_meal_plan(
            total_kcal=day_kcal,
            diet_flags=diet_flags,
            num_meals=num_meals,
            recipe_db=recipe_db,
        )
        daily_plan.day = day_index + 1
        days.append(daily_plan)
        total_weekly_kcal += day_kcal

    # Generate shopping list
    shopping_list = _generate_shopping_list(days)

    # Calculate total cost
    total_cost = sum(day.total_cost for day in days)

    return WeeklyMealPlan(
        days=days,
        average_kcal=total_weekly_kcal // 7,
        shopping_list=shopping_list,
        total_cost=total_cost,
    )


def _generate_shopping_list(days: List[DailyMealPlan]) -> Dict[str, float]:
    """
    RU: Генерирует список покупок на неделю.
    EN: Generates shopping list for the week.
    """
    shopping_list: defaultdict[str, float] = defaultdict(float)

    for day in days:
        for meal in day.meals:
            for ingredient, amount in meal.ingredients.items():
                shopping_list[ingredient] += amount

    return dict(shopping_list)
