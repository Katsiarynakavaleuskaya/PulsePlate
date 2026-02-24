import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Set, TypedDict

from .daily_plate import create_daily_plate
from .food_db import parse_food_db
from .recipe_db import parse_recipe_db
from .targets import NutritionTargets


class MealEntry(TypedDict):
    """RU: Запись блюда в плане. EN: Meal entry in plan."""

    name: str
    kcal: float
    ingredients: Dict[str, float]


class DayPlanEntry(TypedDict):
    """RU: Запись плана на один день. EN: Single day plan entry."""

    day: int
    kcal_target: int
    meals: List[MealEntry]
    micro_coverage: Dict[str, float]


class WeeklyPlanResult(TypedDict):
    """RU: Результат генерации недельного плана. EN: Weekly plan generation result."""

    days: List[DayPlanEntry]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float


def generate_weekly_plan(
    targets: NutritionTargets, diet_flags: Optional[Set[str]] = None
) -> WeeklyPlanResult:
    """
    RU: Генерирует недельный план питания.
    EN: Generates weekly meal plan.

    Args:
        targets: Nutrition targets for the user
        diet_flags: Dietary restrictions/preferences

    Returns:
        Complete weekly plan with meals, coverage, and shopping list
    """
    if diet_flags is None:
        diet_flags = set()

    # Load databases
    food_db = parse_food_db()
    recipe_db = parse_recipe_db(food_db=food_db)

    # Generate 7 days of meal plans
    days: List[DayPlanEntry] = []
    weekly_micro_coverage: Dict[str, List[float]] = {}

    for day_index in range(7):
        # Add slight variation to prevent monotony (±5%)
        variation = 1 + (0.05 * ((day_index % 3) - 1))  # -5%, 0%, +5% variation
        kcal_target = int(targets.kcal_daily * variation)

        # Generate daily plate
        day_plan = create_daily_plate(
            kcal_total=kcal_target,
            diet_flags=diet_flags,
            food_db=food_db,
            recipe_db=recipe_db,
        )

        # Defensive access with defaults matching expected types
        meals = day_plan.get("meals", [])
        micro_coverage = day_plan.get("micro_coverage", {})

        day_entry: DayPlanEntry = {
            "day": day_index + 1,
            "kcal_target": kcal_target,
            "meals": meals,
            "micro_coverage": micro_coverage,
        }

        days.append(day_entry)

        # Aggregate micro coverage for weekly average
        for micro, coverage in micro_coverage.items():
            if micro not in weekly_micro_coverage:
                weekly_micro_coverage[micro] = []
            weekly_micro_coverage[micro].append(coverage)

    # Calculate weekly average coverage
    weekly_coverage: Dict[str, float] = {}
    for micro, coverages in weekly_micro_coverage.items():
        if (
            not coverages
        ):  # pragma: no cover - defensive guard; coverages is always non-empty by construction
            raise ValueError(
                f"Empty coverages list for micro '{micro}': "
                f"expected at least one coverage value for weekly average calculation"
            )
        weekly_coverage[micro] = statistics.mean(coverages)

    # Generate shopping list (simple implementation)
    shopping_list: defaultdict[str, float] = defaultdict(float)
    for day in days:
        for meal in day["meals"]:
            if "ingredients" in meal:
                for ingredient, amount in meal["ingredients"].items():
                    shopping_list[ingredient] += amount

    # Calculate total cost (rough estimate)
    total_cost = 0.0
    for food_name, amount_g in shopping_list.items():
        if food_name in food_db:
            food_item = food_db[food_name]
            # Calculate cost based on price per 100g
            cost = (amount_g / 100.0) * food_item.price_per_unit
            total_cost += cost

    return {
        "days": days,
        "weekly_coverage": weekly_coverage,
        "shopping_list": dict(shopping_list),
        "total_cost": round(total_cost, 2),
    }


def calculate_weekly_nutrition(
    weekly_plan: Dict[str, object],
) -> Optional[Dict[str, float | int]]:
    """
    RU: Агрегирует нутриентные показатели по недельному плану.
    EN: Aggregates nutrition stats across a weekly plan.

    Args:
        weekly_plan: Dict with day keys mapping to per-day nutrition data.

    Returns:
        Aggregated nutrition dict, or None on invalid input.
    """
    if not isinstance(weekly_plan, dict) or not weekly_plan:
        return None

    total_calories = 0.0
    total_protein = 0.0
    day_count = 0

    for _day_key, day_data in weekly_plan.items():
        if not isinstance(day_data, dict):
            continue
        try:
            total_calories += float(day_data.get("calories", 0))
        except (ValueError, TypeError):
            pass
        try:
            total_protein += float(day_data.get("protein", 0))
        except (ValueError, TypeError):
            pass
        day_count += 1

    if day_count == 0:
        return None

    return {
        "total_calories": round(total_calories, 2),
        "avg_calories": round(total_calories / day_count, 2),
        "total_protein": round(total_protein, 2),
        "avg_protein": round(total_protein / day_count, 2),
        "day_count": day_count,
    }


def optimize_weekly_variety(weekly_plan: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    RU: Оптимизирует разнообразие блюд в недельном плане.
    EN: Optimizes meal variety across a weekly plan.

    Args:
        weekly_plan: Dict with day keys mapping to per-day meal data.

    Returns:
        Optimized plan dict (currently returns input unchanged), or None on invalid input.
    """
    if not isinstance(weekly_plan, dict) or not weekly_plan:
        return None

    # Thin facade: return a copy of the plan with a variety_score marker
    return {**weekly_plan, "variety_optimized": True}


def validate_weekly_plan(weekly_plan: Dict[str, object]) -> Optional[bool]:
    """
    RU: Валидирует структуру и полноту недельного плана-черновика.
    EN: Validates structure and completeness of a weekly plan sketch.

    Validates raw plan sketches (dict of day-keyed dicts), not the
    WeeklyPlanResult TypedDict produced by generate_weekly_plan.

    Args:
        weekly_plan: Dict representing a weekly meal plan sketch.

    Returns:
        True if valid, False if invalid, None on non-dict input.
    """
    if not isinstance(weekly_plan, dict):
        return None

    if not weekly_plan:
        return False

    for _day_key, day_data in weekly_plan.items():
        if not isinstance(day_data, dict):
            return False

    return True
