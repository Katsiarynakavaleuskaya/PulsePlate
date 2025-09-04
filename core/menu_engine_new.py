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
    meals: List[dict]
    kcal: int
    macros: Dict[str, float]
    micros: Dict[str, float]
    coverage: Dict[str, float]
    tips: List[str]

def _percent(got: float, need: float) -> float:
    return 0.0 if need <= 0 else min(200.0, 100.0 * got / need)

def build_plate_day(
    targets: dict, diet_flags: List[str], lang: Language,
    fooddb: FoodDB, recipedb: RecipeDB
) -> DayPlan:
    splits = [0.25, 0.35, 0.30, 0.10]
    kcal_split = [int(targets["kcal"] * s) for s in splits]

    meals: List[RMeal] = []
    macros_sum = {"protein_g":0.0,"fat_g":0.0,"carbs_g":0.0,"fiber_g":0.0}
    micros_sum = {k:0.0 for k in MICRO_KEYS}

    for i, kcal_goal in enumerate(kcal_split):
        r = recipedb.pick_base_recipe(diet_flags, i)
        if r is None:
            continue
        m = recipedb.scale_recipe_to_kcal(r, kcal_goal, lang, prefer_fiber=True)
        meals.append(m)
        for k in macros_sum: macros_sum[k] += m.macros[k]
        for mk in MICRO_KEYS: micros_sum[mk] += m.micros.get(mk,0.0)

    # покрытие микро до бустеров
    cov = {k: _percent(micros_sum[k], targets["micro"].get(k,0.0)) for k in MICRO_KEYS}
    tips: List[str] = []

    # бустеры для провалов <80%
    kcal_limit = int(0.05 * targets["kcal"])
    for mk, pct in cov.items():
        if pct < 80.0:
            donor = fooddb.pick_booster_for(mk, diet_flags)
            if not donor:
                continue
            fi = fooddb.get_food(donor)
            # подберем минимальную порцию, чтобы попасть ≤ лимита kcal
            # грубо прикинем из соотношений 4/9 ккал на г белков/углей и жир
            # возьмем порцию 100 г и масштабируем:
            kcal_100 = fi.protein_g*4 + fi.carbs_g*4 + fi.fat_g*9
            if kcal_100 <= 0:
                continue
            grams = min(200.0, max(30.0, (kcal_limit / kcal_100) * 100.0))
            # собираем "мини-блюдо"
            m_macros = {
                "protein_g": fi.protein_g * (grams/fi.per_g),
                "fat_g":     fi.fat_g     * (grams/fi.per_g),
                "carbs_g":   fi.carbs_g   * (grams/fi.per_g),
                "fiber_g":   fi.fiber_g   * (grams/fi.per_g),
            }
            m_kcal = int(round(m_macros["protein_g"]*4 + m_macros["carbs_g"]*4 + m_macros["fat_g"]*9))
            m_micros = {k: fi.micros.get(k,0.0) * (grams/fi.per_g) for k in MICRO_KEYS}
            # Get translated booster food name
            translated_donor = fooddb.get_translated_food_name(donor, lang)
            meals.append(RMeal(
                title=f"booster_{donor}",
                title_translated=f"booster_{translated_donor}",
                grams={donor: round(grams,1)},
                kcal=m_kcal,
                macros={k: round(v,1) for k,v in m_macros.items()},
                micros={k: round(v,1) for k,v in m_micros.items()},
            ))
            for k in macros_sum: macros_sum[k] += m_macros[k]
            for k in MICRO_KEYS: micros_sum[k] += m_micros.get(k,0.0)
            # Use translated tip
            tip_key = f"low_{mk}"
            tips.append(translate_tip(lang, tip_key, donor))

    cov = {k: _percent(micros_sum[k], targets["micro"].get(k,0.0)) for k in MICRO_KEYS}

    out_meals = [{
        "title": m.title,
        "title_translated": m.title_translated,
        "grams": m.grams,
        "kcal": m.kcal,
        "macros": m.macros,
        "micros": m.micros
    } for m in meals]

    return DayPlan(
        meals=out_meals,
        kcal=int(round(sum(m.kcal for m in meals))),
        macros={k: round(v,1) for k,v in macros_sum.items()},
        micros={k: round(v,1) for k,v in micros_sum.items()},
        coverage={k: round(v,1) for k,v in cov.items()},
        tips=tips
    )
