from typing import Dict, Set

from .daily_plate import create_daily_plate
from .food_db import parse_food_db
from .recipe_db import parse_recipe_db
from .targets import NutritionTargets


def generate_weekly_plan(
    targets: NutritionTargets, diet_flags: Set[str] = None
) -> Dict:
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
    days = []
    weekly_micro_coverage = {}

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

        day_entry = {
            "day": day_index + 1,
            "kcal_target": kcal_target,
            "meals": day_plan["meals"],
            "micro_coverage": day_plan["micro_coverage"],
        }

        days.append(day_entry)

        # Aggregate micro coverage for weekly average
        for micro, coverage in day_plan["micro_coverage"].items():
            if micro not in weekly_micro_coverage:
                weekly_micro_coverage[micro] = []
            weekly_micro_coverage[micro].append(coverage)

    # Calculate weekly average coverage
    weekly_coverage = {}
    for micro, coverages in weekly_micro_coverage.items():
        weekly_coverage[micro] = sum(coverages) / len(coverages)

    # Generate shopping list (simple implementation)
    shopping_list = {}
    for day in days:
        for meal in day["meals"]:
            if "ingredients" in meal:
                for ingredient, amount in meal["ingredients"].items():
                    if ingredient in shopping_list:
                        shopping_list[ingredient] += amount
                    else:
                        shopping_list[ingredient] = amount

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
        "shopping_list": shopping_list,
        "total_cost": round(total_cost, 2),
    }
