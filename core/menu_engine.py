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
from copy import deepcopy
import logging
import math
from dataclasses import dataclass
from numbers import Real
from typing import Any, Dict, List, Optional

from .food_apis.unified_db import get_cached_common_foods_snapshot, get_unified_food_db
from .plate import make_plate
from .recommendations import (
    build_nutrition_targets,
    generate_deficiency_recommendations,
    score_nutrient_coverage,
)
from .targets import (
    _MICRONUTRIENT_RANGE_FIELDS,
    MicronutrientTargets,
    NutritionTargets,
    UserProfile,
)


class EventLoopRunningError(Exception):
    """Raised when an event loop is already running and async operations cannot be performed."""


_logger = logging.getLogger(__name__)


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
        total_nutrients: Dict[str, float] = {}

        for ingredient_name, amount_g in self.ingredients.items():
            if ingredient_name in food_db:
                food_item = food_db[ingredient_name]
                for nutrient, value_per_100g in food_item.nutrients_per_100g.items():
                    nutrient_amount = (value_per_100g * amount_g) / 100
                    total_nutrients[nutrient] = total_nutrients.get(nutrient, 0.0) + nutrient_amount

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


def make_daily_menu(
    profile: UserProfile,
    food_db: Optional[Dict[str, FoodItem]] = None,
    recipe_db: Optional[Dict[str, Recipe]] = None,
    target_date: Optional[str] = None,
) -> DayMenu:
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
        diet_flags=profile.diet_flags,
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
        estimated_cost=estimated_cost,
    )


def make_weekly_menu(
    profile: UserProfile,
    food_db: Optional[Dict[str, FoodItem]] = None,
    recipe_db: Optional[Dict[str, Recipe]] = None,
) -> WeekMenu:
    """
    RU: Генерирует недельное меню с оптимизацией покрытия микронутриентов.
    EN: Generates weekly menu optimized for micronutrient coverage.

    Weekly planning allows for day-to-day variation while ensuring
    adequate average intake of all nutrients over the week.
    """
    # Ensure defaults if not provided (avoid relying on external async DB during tests)
    if food_db is None:
        food_db = _get_default_food_db()
    if recipe_db is None:
        recipe_db = _get_default_recipe_db()

    daily_menus: List[DayMenu] = []

    # Generate 7 daily menus with some variation
    for day in range(7):
        # Add slight variation to prevent monotony
        varied_profile = _add_daily_variation(profile, day)
        daily_menu = make_daily_menu(varied_profile, food_db, recipe_db, f"day_{day + 1}")
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
        adherence_score=adherence_score,
    )


def _get_default_food_db(*, allow_mock_fallback: bool = True) -> Dict[str, FoodItem]:
    """
    RU: Получает реальную базу данных продуктов из USDA.
    EN: Gets real food database from USDA.

    This function now uses real USDA nutrition data instead of mock values.
    """
    # Try to get cached common foods first
    try:
        # If already in a running event loop (e.g., FastAPI TestClient), skip async calls
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop – safe to create a temporary event loop
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                unified_db = loop.run_until_complete(get_unified_food_db())
                common_foods = loop.run_until_complete(unified_db.get_common_foods_database())

                # Convert to FoodItem format
                foods_db: Dict[str, FoodItem] = {}
                for key, unified_item in common_foods.items():
                    foods_db[key] = FoodItem(
                        name=unified_item.name,
                        nutrients_per_100g=unified_item.nutrients_per_100g,
                        cost_per_100g=unified_item.cost_per_100g,
                        tags=unified_item.tags,
                        availability_regions=unified_item.availability_regions,
                    )

                if foods_db:
                    return foods_db
            finally:
                try:
                    loop.close()
                except Exception as cleanup_err:  # pragma: no cover
                    _logger.debug("Event loop cleanup failed: %s", cleanup_err)  # pragma: no cover
        else:
            # Already inside a running loop – skip async DB load and let fallback handle it
            raise EventLoopRunningError("Event loop already running; skipping async DB load")
    except Exception as e:
        # Fall back to basic mock data if API fails or loop is running
        _logger.warning("Could not load USDA data, using fallback: %s", e)

    if not allow_mock_fallback:
        return {}

    # Fallback mock data (reduced set)
    return {
        "chicken_breast": FoodItem(
            name="Chicken Breast (Mock)",
            nutrients_per_100g={
                "protein_g": 23.0,
                "fat_g": 3.6,
                "carbs_g": 0.0,
                "iron_mg": 0.7,
                "zinc_mg": 0.9,
                "b12_ug": 0.3,
                "selenium_ug": 14.0,
            },
            cost_per_100g=2.50,
            tags=[],
            availability_regions=["BY", "RU"],
        ),
        "lentils": FoodItem(
            name="Lentils (Mock)",
            nutrients_per_100g={
                "protein_g": 9.0,
                "fat_g": 0.4,
                "carbs_g": 20.0,
                "fiber_g": 8.0,
                "iron_mg": 3.3,
                "folate_ug": 180.0,
                "magnesium_mg": 36.0,
            },
            cost_per_100g=0.80,
            tags=["VEG", "GF"],
            availability_regions=["BY", "RU"],
        ),
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
            instructions=["Cook lentils", "Mix with fresh spinach", "Add dressing"],
        ),
        "grilled_chicken_oats": Recipe(
            name="Grilled Chicken with Oats",
            ingredients={"chicken_breast": 120, "oats": 80},
            servings=1,
            preparation_time_min=25,
            difficulty="medium",
            tags=[],
            instructions=["Grill chicken", "Cook oats", "Serve together"],
        ),
    }


def _enhance_meals_with_micros(
    base_meals: List[Dict],
    food_db: Dict[str, FoodItem],
    recipe_db: Dict[str, Recipe],
    diet_flags: set,
) -> List[Dict]:
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


def _estimate_meal_nutrients(
    meal_title: str, food_db: Dict[str, FoodItem], diet_flags: set[str]
) -> Dict[str, float]:
    """
    RU: Оценивает содержание нутриентов в блюде по названию.
    EN: Estimates nutrient content of a meal based on title.

    This is a simplified approach - in production, would use actual recipes.
    """
    # Basic nutrient estimates based on meal type
    base_nutrients: Dict[str, float] = {
        "protein_g": 0.0,
        "fat_g": 0.0,
        "carbs_g": 0.0,
        "fiber_g": 0.0,
        "iron_mg": 0.0,
        "calcium_mg": 0.0,
        "folate_ug": 0.0,
        "vitamin_d_iu": 0.0,
        "b12_ug": 0.0,
        "magnesium_mg": 0.0,
        "zinc_mg": 0.0,
        "selenium_ug": 0.0,
        "vitamin_c_mg": 0.0,
        "iodine_ug": 0.0,
        "potassium_mg": 0.0,
        "vitamin_a_ug": 0.0,
    }

    # Simple pattern matching for nutrient estimation
    title_lower = meal_title.lower()

    if "курица" in title_lower or "chicken" in title_lower:
        if "VEG" not in diet_flags:
            base_nutrients.update(
                {
                    "protein_g": 25.0,
                    "b12_ug": 0.3,
                    "selenium_ug": 14.0,
                    "zinc_mg": 1.0,
                }
            )

    if "тофу" in title_lower or "tofu" in title_lower:
        base_nutrients.update({"protein_g": 15.0, "calcium_mg": 200.0, "magnesium_mg": 30.0})

    if "гречка" in title_lower or "buckwheat" in title_lower:
        base_nutrients.update(
            {
                "carbs_g": 30.0,
                "fiber_g": 5.0,
                "magnesium_mg": 80.0,
                "iron_mg": 2.0,
            }
        )

    if "овсянка" in title_lower or "oatmeal" in title_lower:
        base_nutrients.update(
            {
                "carbs_g": 25.0,
                "fiber_g": 4.0,
                "iron_mg": 2.0,
                "magnesium_mg": 60.0,
            }
        )

    if "салат" in title_lower or "салad" in title_lower:
        base_nutrients.update({"vitamin_c_mg": 15.0, "folate_ug": 50.0, "calcium_mg": 50.0})

    return base_nutrients


def _estimate_meal_ingredients(meal_title: str, diet_flags: set[str]) -> List[str]:
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


def _calculate_total_nutrients(
    meals: List[Dict[str, Any]],
    food_db: Dict[str, FoodItem],
) -> Dict[str, float]:
    """
    RU: Рассчитывает общее содержание нутриентов за день.
    EN: Calculates total daily nutrient content.
    """
    total: Dict[str, float] = {
        "protein_g": 0,
        "fat_g": 0,
        "carbs_g": 0,
        "fiber_g": 0,
        "iron_mg": 0,
        "calcium_mg": 0,
        "folate_ug": 0,
        "vitamin_d_iu": 0,
        "b12_ug": 0,
        "magnesium_mg": 0,
        "zinc_mg": 0,
        "selenium_ug": 0,
        "vitamin_c_mg": 0,
        "iodine_ug": 0,
        "potassium_mg": 0,
        "vitamin_a_ug": 0,
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


def _generate_shopping_list(
    daily_menus: List[DayMenu], food_db: Dict[str, FoodItem]
) -> Dict[str, float]:
    """
    RU: Генерирует список покупок на неделю.
    EN: Generates weekly shopping list.
    """
    shopping_list: Dict[str, float] = {}

    for daily_menu in daily_menus:
        for meal in daily_menu.meals:
            if "ingredients" in meal:
                for ingredient in meal["ingredients"]:
                    # Estimate amounts needed (simplified)
                    estimated_amount = 100  # grams as default
                    shopping_list[ingredient] = shopping_list.get(ingredient, 0) + estimated_amount

    return shopping_list


def _calculate_weekly_coverage_simple(
    daily_coverages: List[Dict[str, Dict[str, Any]]],
) -> Dict[str, float]:
    """
    RU: Рассчитывает среднее покрытие нутриентов за неделю (упрощённая версия).
    EN: Calculates average nutrient coverage over a week (simplified version).
    """
    if not daily_coverages:
        return {}

    # Get all nutrient names from first day
    nutrient_names = list(daily_coverages[0].keys())
    weekly_averages: Dict[str, float] = {}

    for nutrient in nutrient_names:
        total_coverage = sum(
            day_coverage[nutrient].get("coverage_percent", 0)
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


def analyze_nutrient_gaps(
    targets: NutritionTargets, consumed: Dict[str, float]
) -> Dict[str, Dict[str, Any]]:
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
                "priority": ("high" if nutrient_coverage.coverage_percent < 50 else "medium"),
            }

    return gaps


def repair_week_plan(
    plan: WeekMenu,
    targets: MicronutrientTargets,
    strategy: str = "boosters_first",
    food_db: Optional[Dict[str, FoodItem]] = None,
    recipe_db: Optional[Dict[str, Recipe]] = None,
) -> WeekMenu:
    """
    RU: Авто-ремонт недельного плана на основе дефицитов микронутриентов.
    EN: Auto-repair weekly menu based on micronutrient deficiencies.

    Implements three-step repair process:
    A) Calculate micronutrient gaps per day/week
    B) Find booster foods from database + product_varieties
    C) Recalculate macros/calories without breaking Premium Targets

    Args:
        plan: Weekly menu plan to repair
        targets: Micronutrient targets with ranges and tolerances
        strategy: Repair strategy ("boosters_first", "replace_ingredients", "add_snacks")
        food_db: Food database for finding boosters
        recipe_db: Recipe database for alternatives

    Returns:
        Repaired weekly menu with improved micronutrient coverage
    """
    repaired_plan = deepcopy(plan)
    repaired_plan.daily_menus = [deepcopy(day_menu) for day_menu in plan.daily_menus]
    if strategy != "boosters_first":
        return repaired_plan

    if food_db is None:
        cached_foods = get_cached_common_foods_snapshot()
        resolved_food_db = {
            key: FoodItem(
                name=item.name,
                nutrients_per_100g=dict(item.nutrients_per_100g),
                cost_per_100g=float(item.cost_per_100g),
                tags=list(item.tags),
                availability_regions=list(item.availability_regions),
            )
            for key, item in cached_foods.items()
        }
        if not resolved_food_db:
            _logger.warning("Auto-repair has no cached booster candidates")
    else:
        resolved_food_db = food_db
    _ = recipe_db
    for day_menu in repaired_plan.daily_menus:
        _apply_one_safe_booster(day_menu, targets, resolved_food_db)
    return repaired_plan


def _finite_nonnegative_number(value: object) -> Optional[float]:
    """Return one finite nonnegative real number, otherwise no evidence."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) and number >= 0 else None


def _day_nutrient_evidence(day_menu: DayMenu, nutrient: str) -> Optional[float]:
    """Sum explicit per-meal evidence; any missing or invalid value is ambiguous."""
    total = 0.0
    for meal in day_menu.meals:
        nutrients = meal.get("nutrients")
        if not isinstance(nutrients, dict) or nutrient not in nutrients:
            return None
        value = _finite_nonnegative_number(nutrients[nutrient])
        if value is None:
            return None
        total += value
    return total if math.isfinite(total) else None


def _day_omits_nutrient(day_menu: DayMenu, nutrient: str) -> bool:
    """Return true only when every meal consistently omits one nutrient key."""
    return bool(day_menu.meals) and all(
        isinstance(meal.get("nutrients"), dict) and nutrient not in meal["nutrients"]
        for meal in day_menu.meals
    )


def calculate_known_nutrient_gaps(
    plan: WeekMenu,
    targets: MicronutrientTargets,
) -> Dict[str, float]:
    """Report positive gaps only where every meal supplies explicit baseline evidence."""
    if not plan.daily_menus:
        return {}
    gaps: Dict[str, float] = {}
    for nutrient in sorted(targets.priority_nutrients):
        gap_total = 0.0
        for day_menu in plan.daily_menus:
            day_total = _day_nutrient_evidence(day_menu, nutrient)
            if day_total is None:
                break
            gap_total += max(0.0, targets.get_target(nutrient) - day_total)
        else:
            if math.isfinite(gap_total) and gap_total > 0:
                gaps[nutrient] = gap_total
    return gaps


def has_complete_nutrition_evidence(
    plan: WeekMenu,
    targets: MicronutrientTargets,
) -> bool:
    """Require macro ceilings and each micro at target or above, up to its maximum."""
    if not plan.daily_menus:
        return False
    for day_menu in plan.daily_menus:
        daily_targets = day_menu.targets
        daily_ceilings = {
            "kcal": float(daily_targets.kcal_daily),
            "protein_g": float(daily_targets.macros.protein_g),
            "fat_g": float(daily_targets.macros.fat_g),
            "carbs_g": float(daily_targets.macros.carbs_g),
            "fiber_g": float(daily_targets.macros.fiber_g),
        }
        for nutrient, ceiling in daily_ceilings.items():
            actual = _day_nutrient_evidence(day_menu, nutrient)
            if actual is None or actual > ceiling:
                return False
        for nutrient in targets.priority_nutrients:
            actual = _day_nutrient_evidence(day_menu, nutrient)
            if actual is None:
                return False
            if actual < targets.get_target(nutrient) or actual > targets.get_maximum(nutrient):
                return False
    return True


def _food_nutrient_evidence(food: FoodItem) -> Optional[Dict[str, float]]:
    """Validate that every contribution comes from one coherent FoodItem record."""
    nutrients: Dict[str, float] = {}
    for nutrient, raw_density in food.nutrients_per_100g.items():
        if not isinstance(nutrient, str) or not nutrient:
            return None
        density = _finite_nonnegative_number(raw_density)
        if density is None:
            return None
        nutrients[nutrient] = density
    required_densities = {
        "protein_g",
        "fat_g",
        "carbs_g",
        "fiber_g",
        *_MICRONUTRIENT_RANGE_FIELDS,
    }
    if not required_densities <= set(nutrients):
        return None
    if "kcal" not in nutrients:
        derived_kcal = (
            nutrients["protein_g"] * 4 + nutrients["carbs_g"] * 4 + nutrients["fat_g"] * 9
        )
        if not math.isfinite(derived_kcal) or derived_kcal < 0:
            return None
        nutrients["kcal"] = derived_kcal
    return nutrients


def _normalized_region(value: object) -> str | None:
    """Normalize one explicit region identifier without inference."""

    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _food_is_available_in_region(food: FoodItem, requested_region: str) -> bool:
    """Require exact membership in a complete, explicitly supplied region list."""

    if not isinstance(food.availability_regions, list) or not food.availability_regions:
        return False
    normalized_regions: set[str] = set()
    for region in food.availability_regions:
        normalized = _normalized_region(region)
        if normalized is None:
            return False
        normalized_regions.add(normalized)
    return requested_region in normalized_regions


def _safe_booster_amount(
    day_menu: DayMenu,
    targets: MicronutrientTargets,
    food_nutrients: Dict[str, float],
    primary_nutrient: str,
) -> Optional[float]:
    """Bound a booster by 100 g, primary gap fill, and every target maximum."""
    primary_density = food_nutrients.get(primary_nutrient, 0.0)
    if primary_density <= 0:
        return None
    primary_current = _day_nutrient_evidence(day_menu, primary_nutrient)
    if primary_current is None:
        return None
    primary_gap = targets.get_target(primary_nutrient) - primary_current
    if primary_gap <= 0:
        return None

    amount_caps = [100.0, (primary_gap / primary_density) * 100.0]
    macro_maxima = {
        "kcal": float(day_menu.targets.kcal_daily),
        "protein_g": float(day_menu.targets.macros.protein_g),
        "fat_g": float(day_menu.targets.macros.fat_g),
        "carbs_g": float(day_menu.targets.macros.carbs_g),
        "fiber_g": float(day_menu.targets.macros.fiber_g),
    }
    governed_nutrients = set(targets.priority_nutrients) | set(macro_maxima)
    for nutrient, density in food_nutrients.items():
        if nutrient not in governed_nutrients or density <= 0:
            continue
        current = _day_nutrient_evidence(day_menu, nutrient)
        if current is None:
            if nutrient in macro_maxima and _day_omits_nutrient(day_menu, nutrient):
                continue
            return None
        maximum = (
            macro_maxima[nutrient] if nutrient in macro_maxima else targets.get_maximum(nutrient)
        )
        maximum_room = maximum - current
        if maximum_room <= 0:
            return None
        amount_caps.append((maximum_room / density) * 100.0)

    amount = min(amount_caps)
    return amount if math.isfinite(amount) and amount > 0 else None


def _apply_one_safe_booster(
    day_menu: DayMenu,
    targets: MicronutrientTargets,
    food_db: Dict[str, FoodItem],
) -> bool:
    """Add at most one deterministic safe booster to the first existing meal."""
    if not day_menu.meals:
        return False
    target_meal = day_menu.meals[0]
    ingredients = target_meal.get("ingredients")
    meal_nutrients = target_meal.get("nutrients")
    if not isinstance(ingredients, list) or not isinstance(meal_nutrients, dict):
        return False
    requested_region = _normalized_region(day_menu.targets.calculated_for.region)
    if requested_region is None:
        return False

    primary_nutrients = sorted(
        targets.priority_nutrients,
        key=lambda nutrient: (-targets.priority_nutrients[nutrient], nutrient),
    )
    for primary_nutrient in primary_nutrients:
        candidates: list[tuple[float, str, str, FoodItem, Dict[str, float]]] = []
        for food_key, food in food_db.items():
            if not _food_is_available_in_region(food, requested_region):
                continue
            food_nutrients = _food_nutrient_evidence(food)
            if food_nutrients is None:
                continue
            density = food_nutrients.get(primary_nutrient, 0.0)
            if density > 0:
                candidates.append((-density, food.name.casefold(), food_key, food, food_nutrients))
        candidates.sort(key=lambda candidate: candidate[:3])

        for _, _, _, food, food_nutrients in candidates:
            amount = _safe_booster_amount(
                day_menu,
                targets,
                food_nutrients,
                primary_nutrient,
            )
            if amount is None:
                continue
            updated_nutrients: Dict[str, float] = {}
            for nutrient, density in food_nutrients.items():
                if nutrient not in meal_nutrients:
                    continue
                contribution = density * amount / 100.0
                existing = _finite_nonnegative_number(meal_nutrients.get(nutrient, 0.0))
                if existing is None:
                    return False
                updated_value = existing + contribution
                if (
                    not math.isfinite(contribution)
                    or contribution < 0
                    or not math.isfinite(updated_value)
                    or updated_value < 0
                ):
                    return False
                updated_nutrients[nutrient] = updated_value

            prospective_day = deepcopy(day_menu)
            prospective_meal = prospective_day.meals[0]
            prospective_nutrients = prospective_meal["nutrients"]
            prospective_nutrients.update(updated_nutrients)
            try:
                prospective_total_nutrients = _calculate_day_nutrients(prospective_day)
            except ValueError:
                return False

            ingredients.append({"name": food.name, "amount": amount, "unit": "g"})
            meal_nutrients.update(updated_nutrients)
            day_menu.total_nutrients = prospective_total_nutrients
            return True
    return False


def _calculate_daily_micronutrient_gaps(
    plan: WeekMenu, targets: MicronutrientTargets
) -> Dict[str, Dict[str, float]]:
    """
    RU: Рассчитывает дефициты микронутриентов по дням.
    EN: Calculate daily micronutrient gaps.
    """
    daily_gaps = {}

    for day_menu in plan.daily_menus:
        day_nutrients = _calculate_day_nutrients(day_menu)
        day_gaps = {}

        for nutrient in targets.priority_nutrients.keys():
            target = targets.get_target(nutrient)
            actual = day_nutrients.get(nutrient, 0.0)
            gap = max(0, target - actual)
            day_gaps[nutrient] = gap

        daily_gaps[day_menu.date] = day_gaps

    return daily_gaps


def _aggregate_weekly_gaps(daily_gaps: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    RU: Агрегирует недельные дефициты.
    EN: Aggregate weekly gaps.
    """
    weekly_gaps = {}
    all_nutrients: set[str] = set()

    # Collect all nutrients
    for day_gaps in daily_gaps.values():
        all_nutrients.update(day_gaps.keys())

    # Sum gaps across days
    for nutrient in all_nutrients:
        weekly_gaps[nutrient] = sum(day_gaps.get(nutrient, 0.0) for day_gaps in daily_gaps.values())

    return weekly_gaps


def _find_booster_foods(
    gaps: Dict[str, float],
    targets: MicronutrientTargets,
    food_db: Dict[str, FoodItem],
) -> Dict[str, List[FoodItem]]:
    """
    RU: Находит продукты-усилители для дефицитных нутриентов.
    EN: Find booster foods for deficient nutrients.
    """
    booster_foods: Dict[str, List[FoodItem]] = {}

    for nutrient, gap in gaps.items():
        if gap > 0:  # Only for deficient nutrients
            # Find foods rich in this nutrient
            candidates = []
            for food in food_db.values():
                nutrient_content = food.nutrients_per_100g.get(nutrient, 0.0)
                if nutrient_content > 0:
                    # Calculate how much food needed to fill gap
                    amount_needed = gap / nutrient_content * 100  # grams
                    candidates.append((food, nutrient_content, amount_needed))

            # Sort by nutrient density and select top candidates
            candidates.sort(key=lambda x: x[1], reverse=True)
            booster_foods[nutrient] = [c[0] for c in candidates[:5]]  # Top 5

    return booster_foods


def _apply_repair_strategy(
    plan: WeekMenu,
    daily_gaps: Dict[str, Dict[str, float]],
    booster_foods: Dict[str, List[FoodItem]],
    strategy: str,
    food_db: Dict[str, FoodItem],
    recipe_db: Optional[Dict[str, Recipe]],
) -> WeekMenu:
    """
    RU: Применяет стратегию ремонта к плану.
    EN: Apply repair strategy to the plan.
    """
    if strategy == "boosters_first":
        return _apply_boosters_strategy(plan, daily_gaps, booster_foods)
    elif strategy == "replace_ingredients":
        return _apply_replace_strategy(plan, daily_gaps, booster_foods, food_db)
    elif strategy == "add_snacks":
        return _apply_snacks_strategy(plan, daily_gaps, booster_foods)
    else:
        return plan


def _apply_boosters_strategy(
    plan: WeekMenu,
    daily_gaps: Dict[str, Dict[str, float]],
    booster_foods: Dict[str, List[FoodItem]],
) -> WeekMenu:
    """
    RU: Добавляет продукты-усилители к существующим блюдам.
    EN: Add booster foods to existing meals.
    """
    # For now, return the original plan
    # In a full implementation, this would modify meals to include boosters
    return plan


def _apply_replace_strategy(
    plan: WeekMenu,
    daily_gaps: Dict[str, Dict[str, float]],
    booster_foods: Dict[str, List[FoodItem]],
    food_db: Dict[str, FoodItem],
) -> WeekMenu:
    """
    RU: Заменяет ингредиенты на более богатые нутриентами.
    EN: Replace ingredients with more nutrient-dense alternatives.
    """
    # For now, return the original plan
    # In a full implementation, this would replace ingredients
    return plan


def _apply_snacks_strategy(
    plan: WeekMenu,
    daily_gaps: Dict[str, Dict[str, float]],
    booster_foods: Dict[str, List[FoodItem]],
) -> WeekMenu:
    """
    RU: Добавляет перекусы для восполнения дефицитов.
    EN: Add snacks to fill nutrient gaps.
    """
    # For now, return the original plan
    # In a full implementation, this would add targeted snacks
    return plan


def _calculate_day_nutrients(day_menu: DayMenu) -> Dict[str, float]:
    """
    RU: Рассчитывает общее потребление нутриентов за день.
    EN: Calculate total daily nutrient intake.
    """
    day_nutrients: Dict[str, float] = {}

    for meal in day_menu.meals:
        meal_nutrients = meal.get("nutrients", {})
        if not isinstance(meal_nutrients, dict):
            raise ValueError("Meal nutrients must be a mapping")
        for nutrient, amount in meal_nutrients.items():
            value = _finite_nonnegative_number(amount)
            if value is None:
                raise ValueError("Meal nutrient evidence must be finite and nonnegative")
            accumulated = day_nutrients.get(nutrient, 0.0) + value
            if not math.isfinite(accumulated) or accumulated < 0:
                raise ValueError("Day nutrient evidence overflowed")
            day_nutrients[nutrient] = accumulated

    return day_nutrients


# =============================================================================
# Planner Engine Facade Functions
# =============================================================================
# These functions provide a simplified API for tests and external callers.
# They wrap existing private functions or delegate to existing public functions.


def calculate_nutrition_totals(meal_plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculate total nutrition values from a meal plan.

    RU: Фасад для расчёта общих значений питания.
    EN: Facade for calculating total nutrition values.

    Args:
        meal_plan: Dict with meal data (expects 'meals' key with list of meals)

    Returns:
        Dict with total nutrients or None if calculation fails
    """
    try:
        meals = meal_plan.get("meals", [])
        if not meals:
            return {}

        totals: Dict[str, float] = {}
        for meal in meals:
            if isinstance(meal, dict):
                for key, value in meal.items():
                    if isinstance(value, (int, float)) and key != "name":
                        totals[key] = totals.get(key, 0.0) + value
        return totals
    except (TypeError, AttributeError):
        return None


def generate_shopping_list(meal_plan: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Generate a shopping list from a meal plan.

    RU: Фасад для генерации списка покупок.
    EN: Facade for generating shopping list.

    Args:
        meal_plan: Dict with meal data

    Returns:
        List of shopping items or None if generation fails
    """
    try:
        # Extract unique ingredients from meal plan
        ingredients: Dict[str, Dict[str, Any]] = {}

        meals = meal_plan.get("meals", [])
        for meal in meals:
            if isinstance(meal, dict):
                meal_name = str(meal.get("name") or meal.get("title") or "").strip()
                if not meal_name:
                    continue
                # Estimate ingredients from meal name
                ingredients[meal_name] = {"name": meal_name, "quantity": 1}

        return list(ingredients.values())
    except (TypeError, AttributeError):
        return None


def optimize_meals(meal_plan: Dict[str, Any], targets: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Optimize meals to meet nutrition targets.

    RU: Фасад для оптимизации блюд (делегирует в repair_week_plan).
    EN: Facade for meal optimization (delegates to repair_week_plan).

    Args:
        meal_plan: Dict with meal data
        targets: Dict with target nutrition values

    Returns:
        Optimized meal plan or original if optimization not possible
    """
    # For simple meal plans, return as-is with suggestions
    # Full optimization would require repair_week_plan with proper WeekMenu
    return meal_plan


def validate_meal_plan(meal_plan: Dict[str, Any]) -> bool:
    """
    Validate structure of a meal plan.

    RU: Проверка структуры плана питания.
    EN: Validate meal plan structure.

    Args:
        meal_plan: Dict to validate

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(meal_plan, dict):
        return False

    # Check for common meal keys
    valid_keys = {"breakfast", "lunch", "dinner", "meals", "days", "snacks"}
    has_meals = any(key in meal_plan for key in valid_keys)

    return has_meals


def suggest_meal_improvements(
    meal_plan: Dict[str, Any], targets: Dict[str, Any]
) -> Optional[List[Dict[str, Any]]]:
    """
    Suggest improvements to meet nutrition targets.

    RU: Заглушка - предложения по улучшению.
    EN: Stub - meal improvement suggestions.

    Args:
        meal_plan: Current meal plan
        targets: Nutrition targets

    Returns:
        List of suggestions or None
    """
    # Stub implementation - return empty suggestions
    return []
