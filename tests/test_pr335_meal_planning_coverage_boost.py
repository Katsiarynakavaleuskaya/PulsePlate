"""
Targeted tests to restore/boost coverage for the meal planning engine PR (#335).

Focus: core/menu_engine_new.py, core/meal_planner.py, core/meal_optimizer.py,
core/calorie_distributor.py, and early-import coverage quirks for core/targets.py
and core/dietary_constraints.py.
"""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_targets_module_level_constants_count_for_coverage() -> None:
    ns = runpy.run_path(str(_repo_root() / "core" / "targets.py"))
    assert ns["DEFAULT_CARB_FLOOR_G"] == 50.0
    assert ns["HIGH_PROTEIN_MIN_G_PER_KG"] == 2.0


def test_dietary_constraints_module_level_constants_count_for_coverage() -> None:
    ns = runpy.run_path(str(_repo_root() / "core" / "dietary_constraints.py"))
    assert "VEGAN" in ns["DIET_FLAGS"]
    assert any({"LOW_FAT", "KETO"}.issubset(pair) for pair in ns["INCOMPATIBLE_COMBINATIONS"])


def test_micronutrient_targets_get_minimum_and_maximum_are_callable() -> None:
    from core.targets import MicronutrientTargets

    targets = MicronutrientTargets(
        iron_mg=(1.0, 2.0, 3.0),
        calcium_mg=(1.0, 2.0, 3.0),
        magnesium_mg=(1.0, 2.0, 3.0),
        zinc_mg=(1.0, 2.0, 3.0),
        potassium_mg=(1.0, 2.0, 3.0),
        iodine_ug=(1.0, 2.0, 3.0),
        selenium_ug=(1.0, 2.0, 3.0),
        folate_ug=(1.0, 2.0, 3.0),
        b12_ug=(1.0, 2.0, 3.0),
        vitamin_d_iu=(1.0, 2.0, 3.0),
        vitamin_a_ug=(1.0, 2.0, 3.0),
        vitamin_c_mg=(1.0, 2.0, 3.0),
    )

    assert targets.get_minimum("iron_mg") == 1.0
    assert targets.get_maximum("iron_mg") == 3.0


def test_calorie_distributor_covers_missing_else_branch() -> None:
    from core.calorie_distributor import get_meal_split_list

    kcal_list = get_meal_split_list(1000, meal_splits={"breakfast": 0.5, "lunch": 0.5})
    assert kcal_list == [500, 500, 0, 0]


def test_calorie_distributor_handles_zero_splits_by_falling_back() -> None:
    from core.calorie_distributor import distribute_calories

    dist = distribute_calories(
        2000,
        meal_splits={"breakfast": 0.0, "lunch": 0.0, "dinner": 0.0, "snack": 0.0},
        num_meals=4,
    )
    assert dist.total_kcal == 2000
    assert sum(m.kcal for m in dist.meals) == 2000


def test_meal_planner_select_recipe_handles_typeerror_gracefully() -> None:
    from core.meal_planner import _select_recipe_for_meal

    class BadRecipeDB:
        def get_recipes_by_category(self, _categories: Any) -> Any:
            raise TypeError("boom")

    assert _select_recipe_for_meal("lunch", 600, set(), BadRecipeDB()) is None


def test_meal_planner_daily_plan_ignores_unknown_macro_keys() -> None:
    from core.meal_planner import create_daily_meal_plan

    recipe_db = [
        {
            "name": "Test Meal",
            "kcal": 500,
            "flags": [],
            "macros": {"protein_g": 10.0, "unknown_macro": 1.0},
            "micros": {},
            "ingredients": {},
            "cost": 0.0,
        }
    ]

    plan = create_daily_meal_plan(2000, diet_flags=set(), num_meals=4, recipe_db=recipe_db)
    assert "unknown_macro" not in plan.total_macros
    assert plan.total_macros["protein_g"] == 40.0


def test_menu_engine_new_coercion_and_normalization_helpers() -> None:
    from core.menu_engine_new import _coerce_float, _normalize_micro_targets

    assert _coerce_float(True) is None
    assert _coerce_float(" 1.5 ") == 1.5
    assert _coerce_float("not-a-number") is None

    assert _normalize_micro_targets(None) == {}
    normalized = _normalize_micro_targets({"iron_mg": "18"})
    assert normalized.get("Fe_mg") == 18.0


def test_menu_engine_new_total_cost_parses_string_price_estimates() -> None:
    from core.menu_engine_new import build_plate_day
    from core.recipe_db_new import Meal as RMeal

    class FakeFoodDB:
        def pick_booster_for(self, _mk: str, _diet_flags: list[str]) -> str | None:
            return None

    class FakeRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], meal_index: int) -> object:
            return object()

        def scale_recipe_to_kcal(self, _recipe: object, _kcal_goal: int, _lang: str, **_kw: Any):
            meal = RMeal(
                title="base",
                title_translated="base",
                grams={"x": 100.0},
                kcal=250,
                macros={"protein_g": 10.0, "fat_g": 10.0, "carbs_g": 10.0, "fiber_g": 5.0},
                micros={},
            )
            meal.price_est = "2.5" if _kcal_goal == 350 else "bad"  # type: ignore[attr-defined]
            return meal

    day = build_plate_day(
        {"kcal": 1000, "micro": {}},
        diet_flags=[],
        lang="en",
        fooddb=FakeFoodDB(),  # type: ignore[arg-type]
        recipedb=FakeRecipeDB(),  # type: ignore[arg-type]
    )
    assert day.total_cost == 2.5


def test_menu_engine_new_booster_can_be_skipped_when_allowed_above_too_small() -> None:
    from core.food_db_new import MICRO_KEYS
    from core.menu_engine_new import build_plate_day
    from core.recipe_db_new import Meal as RMeal

    class FakeFoodItem:
        per_g = 100.0
        protein_g = 50.0
        fat_g = 50.0
        carbs_g = 50.0
        fiber_g = 0.0

        def __init__(self) -> None:
            self.micros = {k: 0.0 for k in MICRO_KEYS}

    class FakeFoodDB:
        def pick_booster_for(self, mk: str, _diet_flags: list[str]) -> str | None:
            return "donor" if mk == MICRO_KEYS[0] else None

        def get_food(self, _name: str) -> FakeFoodItem:
            return FakeFoodItem()

        def get_translated_food_name(self, name: str, _lang: str) -> str:
            return name

    class FakeRecipeDB:
        def pick_base_recipe(self, _diet_flags: list[str], _meal_index: int) -> object:
            return object()

        def scale_recipe_to_kcal(self, _recipe: object, _kcal_goal: int, _lang: str, **_kw: Any):
            # Return fixed kcal to control total_kcal and allowed_above.
            meal = RMeal(
                title="base",
                title_translated="base",
                grams={"x": 100.0},
                kcal=287,
                macros={"protein_g": 1.0, "fat_g": 1.0, "carbs_g": 1.0, "fiber_g": 0.0},
                micros={k: 0.0 for k in MICRO_KEYS},
            )
            return meal

    # targets["kcal"]=1000 => tolerance=150.
    # With four meals of 287 kcal, total_kcal=1148 so allowed_above=150-(1148-1000)=2.
    # The donor food is deliberately calorie-dense so the scaled grams drop below 5g and is skipped.
    day = build_plate_day(
        {"kcal": 1000, "micro": {MICRO_KEYS[0]: 10.0}},
        diet_flags=[],
        lang="en",
        fooddb=FakeFoodDB(),  # type: ignore[arg-type]
        recipedb=FakeRecipeDB(),  # type: ignore[arg-type]
    )
    assert all(not m["title"].startswith("booster_") for m in day.meals)


def test_meal_optimizer_branch_coverage_for_scoring_and_diet_filters() -> None:
    from core.meal_optimizer import (
        BoosterFood,
        _reduce_cost_preserving_quality,
        _score_pct_in_range,
    )

    assert _score_pct_in_range(5.0, 10.0, 20.0) == 0.5

    meals = [
        {
            "estimated_cost": 10.0,
            "kcal": 1000,
            "macros": {"protein_g": 50.0, "fat_g": 30.0, "carbs_g": 100.0, "fiber_g": 10.0},
        }
    ]
    optimized = _reduce_cost_preserving_quality(meals, max_budget=1.0, min_quality_score=0.0)
    assert optimized[0]["estimated_cost"] < meals[0]["estimated_cost"]

    with patch(
        "core.meal_optimizer.BOOSTER_FOODS",
        {"x": [BoosterFood("Beef", {"KETO"}, set())]},
    ):
        from core.meal_optimizer import suggest_booster_food

        assert suggest_booster_food("x", diet_flags={"VEG"}, allergens=set()) is None
