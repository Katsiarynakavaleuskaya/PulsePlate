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
import math
import warnings
from typing import Any, Dict, List, NotRequired, TypedDict

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
    total_cost: float = 0.0


class PlateDayTargets(TypedDict):
    """Input targets for day plan generation.

    Required keys:
        kcal: Daily calorie target.

    Optional keys:
        micro: Micronutrient targets keyed by DB or alias names.
        macros: Macronutrient targets in grams.
        water_ml: Daily hydration target in ml.
        activity_week: Weekly activity targets (minutes/sessions).
    """

    kcal: float
    micro: NotRequired[Dict[str, float]]
    macros: NotRequired[Dict[str, float]]
    water_ml: NotRequired[float]
    activity_week: NotRequired[Dict[str, int]]


def _percent(got: Any, need: Any) -> float:
    got_f = _coerce_float(got)
    need_f = _coerce_float(need)

    if got_f is None or need_f is None or need_f <= 0:
        return 0.0

    return min(200.0, 100.0 * got_f / need_f)


_DB_MICRO_TO_ALIAS: Dict[str, str] = {
    "Fe_mg": "iron_mg",
    "Ca_mg": "calcium_mg",
    "Mg_mg": "magnesium_mg",
    "K_mg": "potassium_mg",
    "Iodine_ug": "iodine_ug",
    "VitD_IU": "vitamin_d_iu",
    "B12_ug": "b12_ug",
    "Folate_ug": "folate_ug",
}


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _normalize_micro_targets(micro_targets: Any) -> Dict[str, float]:
    """Normalize micronutrient target keys to DB format expected by MICRO_KEYS.

    Accepts either DB keys (Fe_mg/Ca_mg/...) or WHO/alias keys (iron_mg/calcium_mg/...).
    """
    if not isinstance(micro_targets, dict):
        return {}

    normalized: Dict[str, float] = {}
    # Prefer DB keys when present; otherwise fall back to alias keys.
    for db_key in MICRO_KEYS:
        raw = micro_targets.get(db_key)
        if raw is None:
            alias_key = _DB_MICRO_TO_ALIAS.get(db_key)
            if alias_key is not None:
                raw = micro_targets.get(alias_key)
        value = _coerce_float(raw)
        if value is not None and value >= 0:
            normalized[db_key] = value
    return normalized


def build_plate_day(
    targets: PlateDayTargets,
    diet_flags: List[str],
    lang: Language,
    fooddb: FoodDB,
    recipedb: RecipeDB,
) -> DayPlan:
    """Build a day plan from plate targets.

    Args:
        targets: Daily targets (kcal required, micro/macros optional).
        diet_flags: Dietary flags for recipe selection.
        lang: Language code.
        fooddb: Food database accessor.
        recipedb: Recipe database accessor.
    """
    micro_targets = _normalize_micro_targets(targets.get("micro", {}))
    splits = [0.25, 0.35, 0.30, 0.10]
    kcal_split = [int(targets["kcal"] * s) for s in splits]

    meals: List[RMeal] = []
    total_kcal = 0.0
    macros_sum = {"protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0, "fiber_g": 0.0}
    micros_sum = {k: 0.0 for k in MICRO_KEYS}

    for i, kcal_goal in enumerate(kcal_split):
        r = recipedb.pick_base_recipe(diet_flags, i)
        if r is None:
            continue
        m = recipedb.scale_recipe_to_kcal(r, kcal_goal, lang, prefer_fiber=True)

        raw_kcal = getattr(m, "kcal", None)
        m_kcal = _coerce_float(raw_kcal)

        if m_kcal is None:
            # RU/EN: Invalid kcal from recipe scaler. This should not happen in production data.
            # We warn (observability) and skip to keep the engine robust (tests may use MagicMock).
            warnings.warn(
                f"Skipping meal with non-numeric kcal from scaler: {raw_kcal!r}",
                RuntimeWarning,
                stacklevel=2,
            )
            continue

        if m_kcal <= 0:
            # RU/EN: kcal <= 0 is invalid for a meal; warn and skip to avoid hiding data issues silently.
            warnings.warn(
                f"Skipping meal with non-positive kcal from scaler: {m_kcal}",
                RuntimeWarning,
                stacklevel=2,
            )
            continue

        # Normalize kcal on the meal object to avoid divergence between totals and meal fields.
        try:
            # keep type consistent with other code paths (int kcal)
            m.kcal = int(round(m_kcal))
        except Exception:  # nosec B110
            # If the object is immutable, we still keep totals consistent via total_kcal.
            pass

        meals.append(m)
        total_kcal += float(m_kcal)
        for k in macros_sum:
            macros_sum[k] += m.macros[k]
        for mk in MICRO_KEYS:
            micros_sum[mk] += m.micros.get(mk, 0.0)

    # покрытие микро до бустеров
    cov = {k: _percent(micros_sum[k], micro_targets.get(k, 0.0)) for k in MICRO_KEYS}
    tips: List[str] = []

    # бустеры для провалов <80%
    kcal_limit = int(0.05 * targets["kcal"])
    tolerance = int(round(0.15 * targets["kcal"]))
    for mk, pct in cov.items():
        if pct < 80.0:
            donor = fooddb.pick_booster_for(mk, diet_flags)
            if not donor:
                continue
            fi = fooddb.get_food(donor)
            if fi is None:
                continue
            # Safely coerce macros to float (handles MagicMock/None/invalid values)
            protein_g = _coerce_float(fi.protein_g) or 0.0
            carbs_g = _coerce_float(fi.carbs_g) or 0.0
            fat_g = _coerce_float(fi.fat_g) or 0.0
            fiber_g = _coerce_float(fi.fiber_g) or 0.0
            per_g = _coerce_float(fi.per_g) or 100.0
            if per_g <= 0:
                per_g = 100.0
            # подберем минимальную порцию, чтобы попасть ≤ лимита kcal
            # грубо прикинем из соотношений 4/9 ккал на г белков/углей и жир
            # возьмем порцию 100 г и масштабируем:
            kcal_100 = protein_g * 4 + carbs_g * 4 + fat_g * 9
            if kcal_100 <= 0:
                continue
            grams = min(200.0, max(30.0, (kcal_limit / kcal_100) * 100.0))
            # собираем "мини-блюдо"
            raw_macros = {
                "protein_g": protein_g * (grams / per_g),
                "fat_g": fat_g * (grams / per_g),
                "carbs_g": carbs_g * (grams / per_g),
                "fiber_g": fiber_g * (grams / per_g),
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

            m_micros = {
                k: (_coerce_float(fi.micros.get(k, 0.0)) or 0.0) * (grams / per_g)
                for k in MICRO_KEYS
            }
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

    cov = {k: _percent(micros_sum[k], micro_targets.get(k, 0.0)) for k in MICRO_KEYS}

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
        kcal=int(round(total_kcal)),
        macros={k: round(v, 1) for k, v in macros_sum.items()},
        micros={k: round(v, 1) for k, v in micros_sum.items()},
        coverage={k: round(v, 1) for k, v in cov.items()},
        tips=tips,
        total_cost=round(total_cost, 2),
    )
