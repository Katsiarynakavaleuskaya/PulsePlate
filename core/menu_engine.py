"""
Menu Engine - WHO-Based Daily and Weekly Menu Generation

RU: Движок генерации меню на основе целевых значений ВОЗ.
EN: Menu generation engine based on WHO-derived targets.

This module integrates WHO-based nutrition targets with practical meal planning,
generating daily and weekly menus that meet nutrient requirements while
considering dietary preferences, budget constraints, and food availability.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .food_apis.unified_db import get_unified_food_db
from .plate import make_plate
from .recommendations import (
    build_nutrition_targets,
    generate_deficiency_recommendations,
    score_nutrient_coverage,
)
from .targets import NutritionTargets, UserProfile


@dataclass
class FoodItem:
    """
    RU: Элемент базы данных продуктов.
    EN: Food database item.
    """
    name: str
    nutrients_per_100g: Dict[str, float]  # Nutrient content per 100g
    cost_per_100g: float  # Cost in local currency
    tags: List[str]  # VEG, GF, DAIRY_FREE, etc.
    availability_regions: List[str]  # BY, RU, etc.


@dataclass
class Recipe:
    """
    RU: Рецепт с ингредиентами и питательной ценностью.
    EN: Recipe with ingredients and nutritional value.
    """
    name: str
    ingredients: Dict[str, float]  # ingredient_name: amount_in_grams
    servings: int
    preparation_time_min: int
    difficulty: str  # easy, medium, hard
    tags: List[str]  # VEG, GF, DAIRY_FREE, LOW_COST
    instructions: List[str]

    def calculate_nutrients_per_serving(self, food_db: Dict[str, FoodItem]) -> Dict[str, float]:
        """Calculate nutrients per serving from ingredients."""
        total_nutrients = {}

        for ingredient_name, amount_g in self.ingredients.items():
            if ingredient_name in food_db:
                food_item = food_db[ingredient_name]
                for nutrient, value_per_100g in food_item.nutrients_per_100g.items():
                    nutrient_amount = (value_per_100g * amount_g) / 100
                    total_nutrients[nutrient] = total_nutrients.get(nutrient, 0) + nutrient_amount

        # Divide by servings
        return {k: v / self.servings for k, v in total_nutrients.items()}


@dataclass
class DayMenu:
    """
    RU: Меню на один день с оценкой покрытия нутриентов.
    EN: Single day menu with nutrient coverage assessment.
    """
    date: str
    meals: List[Dict[str, Any]]  # List of meal objects
    total_nutrients: Dict[str, float]
    targets: NutritionTargets
    coverage: Dict[str, Any]
    recommendations: List[str]
    estimated_cost: float


@dataclass
class WeekMenu:
    """
    RU: Недельное меню с планом покупок.
    EN: Weekly menu with shopping plan.
    """
    week_start: str
    daily_menus: List[DayMenu]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]  # ingredient: total_amount_needed
    total_cost: float
    adherence_score: float  # How well it meets targets (0-100)


def make_daily_menu(profile: UserProfile,
                   food_db: Optional[Dict[str, FoodItem]] = None,
                   recipe_db: Optional[Dict[str, Recipe]] = None,
                   target_date: Optional[str] = None) -> DayMenu:
    """
    RU: Генерирует меню на один день на основе целей ВОЗ.
    EN: Generates single day menu based on WHO targets.

    Args:
        profile: User profile with preferences and goals
        food_db: Food database (uses default if None)
        recipe_db: Recipe database (uses default if None)
        target_date: Date for the menu (today if None)

    Returns:
        Complete daily menu with nutrient analysis
    """
    # 1. Build WHO-based nutrition targets
    targets = build_nutrition_targets(profile)

    # 2. Use existing plate logic as foundation, but extend with micro tracking
    plate_result = make_plate(
        weight_kg=profile.weight_kg,
        tdee_val=targets.kcal_daily,
        goal=profile.goal,
        deficit_pct=profile.deficit_pct,
        surplus_pct=profile.surplus_pct,
        diet_flags=profile.diet_flags
    )

    # 3. Enhance meals with micronutrient data
    if food_db is None:
        food_db = _get_default_food_db()
    if recipe_db is None:
        recipe_db = _get_default_recipe_db()

    enhanced_meals = _enhance_meals_with_micros(
        plate_result["meals"], food_db, recipe_db, profile.diet_flags
    )

    # 4. Calculate total nutrient content
    total_nutrients = _calculate_total_nutrients(enhanced_meals, food_db)

    # 5. Score nutrient coverage
    coverage = score_nutrient_coverage(total_nutrients, targets)

    # 6. Generate recommendations for deficiencies
    recommendations = generate_deficiency_recommendations(coverage, profile)

    # 7. Estimate cost
    estimated_cost = _estimate_daily_cost(enhanced_meals, food_db)

    return DayMenu(
        date=target_date or "today",
        meals=enhanced_meals,
        total_nutrients=total_nutrients,
        targets=targets,
        coverage={k: v.__dict__ for k, v in coverage.items()},
        recommendations=recommendations,
        estimated_cost=estimated_cost
    )


def make_weekly_menu(profile: UserProfile,
                    food_db: Optional[Dict[str, FoodItem]] = None,
                    recipe_db: Optional[Dict[str, Recipe]] = None) -> WeekMenu:
    """
    RU: Генерирует недельное меню с оптимизацией покрытия микронутриентов.
    EN: Generates weekly menu optimized for micronutrient coverage.

    Weekly planning allows for day-to-day variation while ensuring
    adequate average intake of all nutrients over the week.
    """
    daily_menus = []

    # Generate 7 daily menus with some variation
    for day in range(7):
        # Add slight variation to prevent monotony
        varied_profile = _add_daily_variation(profile, day)
        daily_menu = make_daily_menu(varied_profile, food_db, recipe_db, f"day_{day+1}")
        daily_menus.append(daily_menu)

    # Calculate weekly averages
    daily_coverages = [menu.coverage for menu in daily_menus]
    weekly_coverage = _calculate_weekly_coverage_simple(daily_coverages)

    # Generate shopping list
    shopping_list = _generate_shopping_list(daily_menus, food_db)

    # Calculate total cost
    total_cost = sum(menu.estimated_cost for menu in daily_menus)

    # Calculate adherence score (% of nutrients meeting targets)
    adherence_score = _calculate_adherence_score(weekly_coverage)

    return WeekMenu(
        week_start="week_1",
        daily_menus=daily_menus,
        weekly_coverage=weekly_coverage,
        shopping_list=shopping_list,
        total_cost=total_cost,
        adherence_score=adherence_score
    )


def _get_default_food_db() -> Dict[str, FoodItem]:
    """
    RU: Получает реальную базу данных продуктов из USDA.
    EN: Gets real food database from USDA.

    This function now uses real USDA nutrition data instead of mock values.
    """
    # Try to get cached common foods first
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        unified_db = loop.run_until_complete(get_unified_food_db())
        common_foods = loop.run_until_complete(unified_db.get_common_foods_database())

        # Convert to FoodItem format
        foods_db = {}
        for key, unified_item in common_foods.items():
            foods_db[key] = FoodItem(
                name=unified_item.name,
                nutrients_per_100g=unified_item.nutrients_per_100g,
                cost_per_100g=unified_item.cost_per_100g,
                tags=unified_item.tags,
                availability_regions=unified_item.availability_regions
            )

        if foods_db:
            return foods_db

    except Exception as e:
        # Fall back to basic mock data if API fails
        print(f"Warning: Could not load USDA data, using fallback: {e}")

    # Fallback mock data (reduced set)
    return {
        "chicken_breast": FoodItem(
            name="Chicken Breast (Mock)",
            nutrients_per_100g={
                "protein_g": 23.0, "fat_g": 3.6, "carbs_g": 0.0,
                "iron_mg": 0.7, "zinc_mg": 0.9, "b12_ug": 0.3,
                "selenium_ug": 14.0
            },
            cost_per_100g=2.50,
            tags=[],
            availability_regions=["BY", "RU"]
        ),
        "lentils": FoodItem(
            name="Lentils (Mock)",
            nutrients_per_100g={
                "protein_g": 9.0, "fat_g": 0.4, "carbs_g": 20.0, "fiber_g": 8.0,
                "iron_mg": 3.3, "folate_ug": 180.0, "magnesium_mg": 36.0
            },
            cost_per_100g=0.80,
            tags=["VEG", "GF"],
            availability_regions=["BY", "RU"]
        )
    }


def _get_default_recipe_db() -> Dict[str, Recipe]:
    """
    RU: Базовая база рецептов для демонстрации.
    EN: Basic recipe database for demonstration.
    """
    return {
        "lentil_spinach_salad": Recipe(
            name="Lentil Spinach Salad",
            ingredients={"lentils": 100, "spinach": 150},
            servings=2,
            preparation_time_min=15,
            difficulty="easy",
            tags=["VEG", "GF", "DAIRY_FREE"],
            instructions=["Cook lentils", "Mix with fresh spinach", "Add dressing"]
        ),
        "grilled_chicken_oats": Recipe(
            name="Grilled Chicken with Oats",
            ingredients={"chicken_breast": 120, "oats": 80},
            servings=1,
            preparation_time_min=25,
            difficulty="medium",
            tags=[],
            instructions=["Grill chicken", "Cook oats", "Serve together"]
        )
    }


def _enhance_meals_with_micros(base_meals: List[Dict],
                              food_db: Dict[str, FoodItem],
                              recipe_db: Dict[str, Recipe],
                              diet_flags: set) -> List[Dict]:
    """
    RU: Дополняет базовые блюда информацией о микронутриентах.
    EN: Enhances base meals with micronutrient information.
    """
    enhanced = []

    for meal in base_meals:
        # Map meal titles to actual recipes/foods
        enhanced_meal = meal.copy()

        # Add detailed nutrient breakdown (simplified for demo)
        enhanced_meal["detailed_nutrients"] = _estimate_meal_nutrients(
            meal["title"], food_db, diet_flags
        )
        enhanced_meal["ingredients"] = _estimate_meal_ingredients(meal["title"], diet_flags)

        enhanced.append(enhanced_meal)

    return enhanced


def _estimate_meal_nutrients(meal_title: str,
                           food_db: Dict[str, FoodItem],
                           diet_flags: set) -> Dict[str, float]:
    """
    RU: Оценивает содержание нутриентов в блюде по названию.
    EN: Estimates nutrient content of a meal based on title.

    This is a simplified approach - in production, would use actual recipes.
    """
    # Basic nutrient estimates based on meal type
    base_nutrients = {
        "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fiber_g": 0,
        "iron_mg": 0, "calcium_mg": 0, "folate_ug": 0, "vitamin_d_iu": 0,
        "b12_ug": 0, "magnesium_mg": 0, "zinc_mg": 0, "selenium_ug": 0,
        "vitamin_c_mg": 0, "iodine_ug": 0, "potassium_mg": 0, "vitamin_a_ug": 0
    }

    # Simple pattern matching for nutrient estimation
    title_lower = meal_title.lower()

    if "курица" in title_lower or "chicken" in title_lower:
        if "VEG" not in diet_flags:
            base_nutrients.update({
                "protein_g": 25, "b12_ug": 0.3, "selenium_ug": 14, "zinc_mg": 1
            })

    if "тофу" in title_lower or "tofu" in title_lower:
        base_nutrients.update({
            "protein_g": 15, "calcium_mg": 200, "magnesium_mg": 30
        })

    if "гречка" in title_lower or "buckwheat" in title_lower:
        base_nutrients.update({
            "carbs_g": 30, "fiber_g": 5, "magnesium_mg": 80, "iron_mg": 2
        })

    if "овсянка" in title_lower or "oatmeal" in title_lower:
        base_nutrients.update({
            "carbs_g": 25, "fiber_g": 4, "iron_mg": 2, "magnesium_mg": 60
        })

    if "салат" in title_lower or "салad" in title_lower:
        base_nutrients.update({
            "vitamin_c_mg": 15, "folate_ug": 50, "calcium_mg": 50
        })

    return base_nutrients


def _estimate_meal_ingredients(meal_title: str, diet_flags: set) -> List[str]:
    """
    RU: Оценивает ингредиенты блюда по названию.
    EN: Estimates meal ingredients based on title.
    """
    ingredients = []
    title_lower = meal_title.lower()

    if "овсянка" in title_lower:
        ingredients.append("oats")
    if "гречка" in title_lower:
        ingredients.append("buckwheat")
    if "курица" in title_lower and "VEG" not in diet_flags:
        ingredients.append("chicken_breast")
    if "тофу" in title_lower:
        ingredients.append("tofu")
    if "салат" in title_lower:
        ingredients.extend(["lettuce", "tomato", "cucumber"])

    return ingredients


def _calculate_total_nutrients(meals: List[Dict], food_db: Dict[str, FoodItem]) -> Dict[str, float]:
    """
    RU: Рассчитывает общее содержание нутриентов за день.
    EN: Calculates total daily nutrient content.
    """
    total = {
        "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fiber_g": 0,
        "iron_mg": 0, "calcium_mg": 0, "folate_ug": 0, "vitamin_d_iu": 0,
        "b12_ug": 0, "magnesium_mg": 0, "zinc_mg": 0, "selenium_ug": 0,
        "vitamin_c_mg": 0, "iodine_ug": 0, "potassium_mg": 0, "vitamin_a_ug": 0
    }

    for meal in meals:
        if "detailed_nutrients" in meal:
            for nutrient, amount in meal["detailed_nutrients"].items():
                total[nutrient] = total.get(nutrient, 0) + amount

    return total


def _estimate_daily_cost(meals: List[Dict], food_db: Dict[str, FoodItem]) -> float:
    """
    RU: Оценивает стоимость дневного рациона.
    EN: Estimates daily menu cost.
    """
    total_cost = 0.0

    for meal in meals:
        # Simple cost estimation based on meal type
        base_cost = meal.get("kcal", 400) * 0.002  # ~0.002 per calorie as base

        # Adjust for premium ingredients
        title_lower = meal["title"].lower()
        if "лосось" in title_lower or "salmon" in title_lower:
            base_cost *= 2.0
        elif "говядина" in title_lower or "beef" in title_lower:
            base_cost *= 1.5
        elif any(flag in meal["title"] for flag in ["(бюджет)", "budget"]):
            base_cost *= 0.7

        total_cost += base_cost

    return round(total_cost, 2)


def _add_daily_variation(profile: UserProfile, day_index: int) -> UserProfile:
    """
    RU: Добавляет небольшие вариации для разнообразия меню.
    EN: Adds slight variations for menu diversity.
    """
    # For now, just return the original profile
    # In production, could vary diet_flags, preferences, etc.
    return profile


def _generate_shopping_list(daily_menus: List[DayMenu],
                           food_db: Dict[str, FoodItem]) -> Dict[str, float]:
    """
    RU: Генерирует список покупок на неделю.
    EN: Generates weekly shopping list.
    """
    shopping_list = {}

    for daily_menu in daily_menus:
        for meal in daily_menu.meals:
            if "ingredients" in meal:
                for ingredient in meal["ingredients"]:
                    # Estimate amounts needed (simplified)
                    estimated_amount = 100  # grams as default
                    shopping_list[ingredient] = shopping_list.get(ingredient, 0) + estimated_amount

    return shopping_list


def _calculate_weekly_coverage_simple(daily_coverages: List[Dict[str, Dict]]) -> Dict[str, float]:
    """
    RU: Рассчитывает среднее покрытие нутриентов за неделю (упрощённая версия).
    EN: Calculates average nutrient coverage over a week (simplified version).
    """
    if not daily_coverages:
        return {}

    # Get all nutrient names from first day
    nutrient_names = list(daily_coverages[0].keys())
    weekly_averages = {}

    for nutrient in nutrient_names:
        total_coverage = sum(
            day_coverage[nutrient].get('coverage_percent', 0)
            for day_coverage in daily_coverages
            if nutrient in day_coverage
        )
        weekly_averages[nutrient] = round(total_coverage / len(daily_coverages), 1)

    return weekly_averages


def _calculate_adherence_score(weekly_coverage: Dict[str, float]) -> float:
    """
    RU: Рассчитывает общий балл соответствия целям.
    EN: Calculates overall adherence score to targets.
    """
    if not weekly_coverage:
        return 0.0

    # Count nutrients meeting 80%+ of targets
    adequate_nutrients = sum(1 for coverage in weekly_coverage.values() if coverage >= 80)
    total_nutrients = len(weekly_coverage)

    return round((adequate_nutrients / total_nutrients) * 100, 1) if total_nutrients > 0 else 0.0


def analyze_nutrient_gaps(targets: NutritionTargets,
                         consumed: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """
    RU: Анализирует пробелы в питании и предлагает решения.
    EN: Analyzes nutrient gaps and suggests solutions.

    This function provides detailed gap analysis that can be used
    by the /api/v1/premium/gaps endpoint.
    """
    coverage = score_nutrient_coverage(consumed, targets)
    gaps = {}

    for nutrient_name, nutrient_coverage in coverage.items():
        if nutrient_coverage.status == "deficient":
            gaps[nutrient_name] = {
                "current_intake": nutrient_coverage.consumed_amount,
                "target_intake": nutrient_coverage.target_amount,
                "coverage_percent": nutrient_coverage.coverage_percent,
                "shortfall": nutrient_coverage.target_amount - nutrient_coverage.consumed_amount,
                "unit": nutrient_coverage.unit,
                "priority": "high" if nutrient_coverage.coverage_percent < 50 else "medium"
            }

    return gaps
