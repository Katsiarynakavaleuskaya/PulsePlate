from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, Any, List

import pytest

import core.weekly_plan as wp
from core.weekly_plan import WeeklyPlanResult


def _make_fake_day(index: int, kcal: int) -> Dict[str, Any]:
    return {
        "meals": [
            {
                "name": f"Meal {index}",
                "kcal": kcal / 2,
                "ingredients": {"apple": 100.0, "banana": 50.0},
            }
        ],
        "micro_coverage": {"iron_mg": 0.5 * (index + 1)},
    }


def test_generate_weekly_plan_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover happy path returning aggregated weekly plan."""
    food_db = {
        "apple": SimpleNamespace(price_per_unit=2.0),
        "banana": SimpleNamespace(price_per_unit=1.5),
    }
    monkeypatch.setattr(wp, "parse_food_db", lambda: food_db)
    monkeypatch.setattr(wp, "parse_recipe_db", lambda **kwargs: {"dummy": {}})

    def fake_create_daily_plate(**kwargs: Any) -> Dict[str, Any]:
        idx = fake_create_daily_plate.counter
        fake_create_daily_plate.counter += 1
        return _make_fake_day(idx, kwargs["kcal_total"])

    fake_create_daily_plate.counter = 0  # type: ignore[attr-defined]

    monkeypatch.setattr(wp, "create_daily_plate", fake_create_daily_plate)

    targets = SimpleNamespace(kcal_daily=2000)
    plan: WeeklyPlanResult = wp.generate_weekly_plan(targets)

    assert len(plan["days"]) == 7
    assert "iron_mg" in plan["weekly_coverage"]
    assert plan["total_cost"] >= 0.0
    assert plan["shopping_list"]["apple"] > 0.0
