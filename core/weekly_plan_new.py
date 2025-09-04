"""
Weekly Plan Generator

RU: Генератор недельного плана питания.
EN: Weekly meal plan generator.

This module generates a 7-day meal plan with nutrient coverage analysis
and shopping list aggregation.
"""

from typing import List

from .food_db_new import FoodDB
from .meal_i18n import Language
from .menu_engine_new import build_plate_day
from .recipe_db_new import RecipeDB


def build_week(targets: dict, diet_flags: List[str], lang: Language, fooddb: FoodDB, recipedb: RecipeDB) -> dict:
    days = []
    for _ in range(7):
        d = build_plate_day(targets, diet_flags, lang, fooddb, recipedb)
        # лёгкая вариативность (±5% уже в scale_recipe, этого достаточно)
        days.append(d.__dict__)
    # усредняем покрытие
    MICRO_KEYS = list(days[0]["coverage"].keys())
    weekly_cov = {k: round(sum(d["coverage"][k] for d in days)/7.0, 1) for k in MICRO_KEYS}
    shopping = fooddb.aggregate_shopping(days, lang)
    return {"days": days, "weekly_coverage": weekly_cov, "shopping_list": shopping}
