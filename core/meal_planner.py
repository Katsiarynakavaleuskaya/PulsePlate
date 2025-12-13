"""
Meal Planner - Core Meal Planning Logic

RU: Модуль планирования приемов пищи.
EN: Module for meal planning functionality.

This module provides the core meal planning engine that creates daily
and weekly meal plans based on calorie targets, dietary restrictions,
and nutrient coverage optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .calorie_distributor import distribute_calories, apply_weekly_variation
from .dietary_constraints import normalize_diet_flags, is_recipe_compatible


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
    boosters: List[Dict] = field(default_factory=list)
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
    except (AttributeError, TypeError):
        return None

    # Filter by compatibility
    compatible_recipes = []
    for recipe in recipes:
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
    """Convert recipe object to dictionary format."""
    if isinstance(recipe, dict):
        return recipe

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

    return recipe_dict


def _create_fallback_meal(
    meal_name: str,
    kcal_target: int,
    diet_flags: Set[str],
) -> MealPlan:
    """
    RU: Создает запасной вариант приема пищи.
    EN: Creates fallback meal option.
    """
    # Adjust macro distribution for key dietary patterns first
    normalized_flags = normalize_diet_flags(diet_flags)

    if "KETO" in normalized_flags:
        # Very low carb, high fat pattern
        protein_pct = 0.25
        carbs_pct = 0.05
        fat_pct = 0.70
    elif "LOW_CARB" in normalized_flags:
        # Moderately low carb, higher fat and protein
        protein_pct = 0.35
        carbs_pct = 0.20
        fat_pct = 0.45
    elif meal_name == "breakfast":
        # Higher carbs for morning energy
        protein_pct = 0.25
        carbs_pct = 0.50
        fat_pct = 0.25
    elif meal_name == "snack":
        # Balanced, smaller portions
        protein_pct = 0.30
        carbs_pct = 0.40
        fat_pct = 0.30
    else:  # lunch, dinner
        # Balanced meal
        protein_pct = 0.30
        carbs_pct = 0.40
        fat_pct = 0.30

    protein_g = (kcal_target * protein_pct) / 4
    carbs_g = (kcal_target * carbs_pct) / 4
    fat_g = (kcal_target * fat_pct) / 9

    return MealPlan(
        name=meal_name,
        kcal_target=kcal_target,
        recipe_name=f"Balanced {meal_name}",
        macros={
            "protein_g": round(protein_g, 1),
            "carbs_g": round(carbs_g, 1),
            "fat_g": round(fat_g, 1),
            "fiber_g": 8.0,
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
    shopping_list: Dict[str, float] = {}

    for day in days:
        for meal in day.meals:
            for ingredient, amount in meal.ingredients.items():
                if ingredient in shopping_list:
                    shopping_list[ingredient] += amount
                else:
                    shopping_list[ingredient] = amount

    return shopping_list
