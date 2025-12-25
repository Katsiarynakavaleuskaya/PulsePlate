from __future__ import annotations

import math
from typing import Any, Dict, Set

import pytest

from core import disclaimers as disclaimers_mod
from core import food_db as food_db_mod
from core import menu_engine_new as menu_engine_new_mod


def _food_item(name: str, *, flags: Set[str]) -> food_db_mod.FoodItem:
    """RU: Минимальный FoodItem для тестов ветвлений. EN: Minimal FoodItem for branch tests."""
    return food_db_mod.FoodItem(
        name=name,
        unit_per=100,
        unit="g",
        protein_g=0.0,
        fat_g=0.0,
        carbs_g=0.0,
        fiber_g=0.0,
        Fe_mg=0.0,
        Ca_mg=0.0,
        VitD_IU=0.0,
        B12_ug=0.0,
        Folate_ug=0.0,
        Iodine_ug=0.0,
        K_mg=0.0,
        Mg_mg=0.0,
        price_per_unit=0.0,
        flags=flags,
    )


def test_menu_engine_new_coerce_float_non_finite_returns_none() -> None:
    """Cover _coerce_float: non-finite values should return None."""
    assert menu_engine_new_mod._coerce_float(math.inf) is None
    assert menu_engine_new_mod._coerce_float(float("nan")) is None


def test_food_db_pick_booster_for_exercises_flag_branches() -> None:
    """Cover pick_booster_for branch parts (empty/subset/disjoint/overlap-not-subset)."""
    food_db: Dict[str, food_db_mod.FoodItem] = {
        # First candidate: overlaps with flags but is NOT a superset → should be rejected in last case.
        "lentils": _food_item("lentils", flags={"VEGAN"}),
        # Second candidate: superset → accepted for subset-case.
        "spinach_raw": _food_item("spinach_raw", flags={"VEGAN", "KETO"}),
        # Third candidate: present but not needed for these checks.
        "tofu": _food_item("tofu", flags=set()),
    }

    # 1) Empty flags: accepted via "not flags"
    assert food_db_mod.pick_booster_for("iron_mg", set(), food_db) in {
        "lentils",
        "spinach_raw",
        "tofu",
    }

    # 2) Subset: accepted via "flags.issubset(food.flags)"
    assert food_db_mod.pick_booster_for("iron_mg", {"VEGAN"}, food_db) in {"lentils", "spinach_raw"}

    # 3) Disjoint: accepted via "not flags.intersection(food.flags)"
    assert food_db_mod.pick_booster_for("iron_mg", {"GLUTEN_FREE"}, food_db) in {
        "lentils",
        "spinach_raw",
        "tofu",
    }

    # 4) Overlap but not subset: first candidate rejected, next candidate chosen
    assert food_db_mod.pick_booster_for("iron_mg", {"VEGAN", "KETO"}, food_db) == "spinach_raw"


def test_food_db_aggregate_shopping_ignores_missing_keys() -> None:
    """Cover aggregate_shopping false-branches for missing meals/ingredients keys."""
    days: list[dict[str, Any]] = [
        {},  # no "meals"
        {"meals": [{}]},  # meal without "ingredients"
        {"meals": [{"ingredients": {}}]},  # empty ingredients
        {"meals": [{"ingredients": {"rice": 100.0}}]},
    ]
    assert food_db_mod.aggregate_shopping(days) == {"rice": 100.0}


def test_disclaimers_comprehensive_ignores_unknown_population() -> None:
    """Cover disclaimer branch: unknown population is ignored (no KeyError)."""
    text = disclaimers_mod.get_comprehensive_disclaimer(["unknown_population"], language="en")
    assert "unknown_population" not in text
