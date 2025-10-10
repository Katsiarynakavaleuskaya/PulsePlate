"""
Menu Engine - Daily Plate Algorithm

RU: Движок генерации меню на основе алгоритма тарелки.
EN: Menu generation engine based on plate algorithm.

This module implements the daily plate algorithm that distributes calories
across meals, selects recipes, scales them to kcal goals, and adds boosters
for nutrient deficiencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .food_db_new import MICRO_KEYS, FoodDB
from .meal_i18n import Language, translate_tip
from .recipe_db_new import Meal as RMeal
from .recipe_db_new import RecipeDB


@dataclass
class DayPlan:
    meals: list[dict]
    kcal: int
    macros: dict[str, float]
    micros: dict[str, float]
    coverage: dict[str, float]
    tips: list[str]
    total_cost: float = 0.0


def _percent(got: float, need: float) -> float:
    return 0.0 if need <= 0 else min(200.0, 100.0 * got / need)


def build_plate_day(
    targets: dict,
    diet_flags: list[str],
    lang: Language,
    fooddb: FoodDB,
    recipedb: RecipeDB,
) -> DayPlan:
    splits = [0.25, 0.35, 0.30, 0.10]
    kcal_split = [int(targets["kcal"] * s) for s in splits]

    meals: list[RMeal] = []
    total_kcal = 0.0
    macros_sum = {"protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0, "fiber_g": 0.0}
    micros_sum = dict.fromkeys(MICRO_KEYS, 0.0)

    for i, kcal_goal in enumerate(kcal_split):
        r = recipedb.pick_base_recipe(diet_flags, i)
        if r is None:
            continue
        m = recipedb.scale_recipe_to_kcal(r, kcal_goal, lang, prefer_fiber=True)
        meals.append(m)
        total_kcal += m.kcal
        for k in macros_sum:
            macros_sum[k] += m.macros[k]
        for mk in MICRO_KEYS:
            micros_sum[mk] += m.micros.get(mk, 0.0)

    # покрытие микро до бустеров
    cov = {k: _percent(micros_sum[k], targets["micro"].get(k, 0.0)) for k in MICRO_KEYS}
    tips: list[str] = []

    # бустеры для провалов <80%
    kcal_limit = int(0.05 * targets["kcal"])
    tolerance = int(round(0.15 * targets["kcal"]))
    for mk, pct in cov.items():
        if pct < 80.0:
            donor = fooddb.pick_booster_for(mk, diet_flags)
            if not donor:
                continue
            fi = fooddb.get_food(donor)
            # подберем минимальную порцию, чтобы попасть ≤ лимита kcal
            # грубо прикинем из соотношений 4/9 ккал на г белков/углей и жир
            # возьмем порцию 100 г и масштабируем:
            kcal_100 = fi.protein_g * 4 + fi.carbs_g * 4 + fi.fat_g * 9
            if kcal_100 <= 0:
                continue
            grams = min(200.0, max(30.0, (kcal_limit / kcal_100) * 100.0))
            # собираем "мини-блюдо"
            raw_macros = {
                "protein_g": fi.protein_g * (grams / fi.per_g),
                "fat_g": fi.fat_g * (grams / fi.per_g),
                "carbs_g": fi.carbs_g * (grams / fi.per_g),
                "fiber_g": fi.fiber_g * (grams / fi.per_g),
            }
            raw_kcal = (
                raw_macros["protein_g"] * 4 + raw_macros["carbs_g"] * 4 + raw_macros["fat_g"] * 9
            )
            if raw_kcal <= 0:
                continue  # pragma: no cover

            allowed_above = tolerance - max(0.0, total_kcal - targets["kcal"])
            if allowed_above <= 0:
                continue

            if raw_kcal > allowed_above:
                ratio = allowed_above / raw_kcal
                if ratio <= 0:
                    continue  # pragma: no cover
                grams *= ratio
                raw_macros = {k: v * ratio for k, v in raw_macros.items()}
                raw_kcal *= ratio
            m_kcal = int(round(raw_kcal))
            if m_kcal <= 0 or grams < 5.0:
                continue

            m_micros = {k: fi.micros.get(k, 0.0) * (grams / fi.per_g) for k in MICRO_KEYS}
            # Get translated booster food name
            translated_donor = fooddb.get_translated_food_name(donor, lang)
            meals.append(
                RMeal(
                    title=f"booster_{donor}",
                    title_translated=f"booster_{translated_donor}",
                    grams={donor: round(grams, 1)},
                    kcal=m_kcal,
                    macros={k: round(v, 1) for k, v in raw_macros.items()},
                    micros={k: round(v, 1) for k, v in m_micros.items()},
                )
            )
            total_kcal += m_kcal
            for k in macros_sum:
                macros_sum[k] += raw_macros[k]
            for k in MICRO_KEYS:
                micros_sum[k] += m_micros.get(k, 0.0)
            # Use translated tip
            tip_key = f"low_{mk}"
            tips.append(translate_tip(lang, tip_key, donor))

    cov = {k: _percent(micros_sum[k], targets["micro"].get(k, 0.0)) for k in MICRO_KEYS}

    out_meals = []
    for m in meals:
        meal_dict = {
            "title": m.title,
            "title_translated": m.title_translated,
            "grams": m.grams,
            "kcal": m.kcal,
            "macros": m.macros,
            "micros": m.micros,
        }
        # Optionally propagate estimated price if provided by recipe scaler
        price_est = getattr(m, "price_est", None)
        if price_est is not None:
            meal_dict["price_est"] = price_est
        out_meals.append(meal_dict)

    # Calculate total cost (simplified - just sum of meal costs)
    total_cost = 0.0
    for meal in out_meals:
        price_est = meal.get("price_est", 0.0)
        if isinstance(price_est, (int, float)):
            total_cost += float(price_est)
        elif isinstance(price_est, str):
            try:
                total_cost += float(price_est)
            except ValueError:
                pass  # Skip invalid price strings

    return DayPlan(
        meals=out_meals,
        kcal=int(round(sum(m.kcal for m in meals))),
        macros={k: round(v, 1) for k, v in macros_sum.items()},
        micros={k: round(v, 1) for k, v in micros_sum.items()},
        coverage={k: round(v, 1) for k, v in cov.items()},
        tips=tips,
        total_cost=round(total_cost, 2),
    )
