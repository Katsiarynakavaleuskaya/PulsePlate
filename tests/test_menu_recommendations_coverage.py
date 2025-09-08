# -*- coding: utf-8 -*-
from core import menu_engine, recommendations


def test_menu_engine_estimate_daily_cost_branches():
    meals = [
        {"title": "Dinner: Salmon Fillet", "kcal": 600},
        {"title": "Lunch: Beef Bowl", "kcal": 700},
        {"title": "Breakfast: Oatmeal (budget)", "kcal": 400},
    ]
    cost = menu_engine._estimate_daily_cost(meals, {})  # noqa: SLF001
    assert isinstance(cost, float) and cost > 0


def test_menu_engine_empty_coverage_and_adherence():
    # _calculate_weekly_coverage_simple handles empty list
    weekly = menu_engine._calculate_weekly_coverage_simple([])  # noqa: SLF001
    assert weekly == {}

    # _calculate_adherence_score handles empty dict
    score = menu_engine._calculate_adherence_score({})  # noqa: SLF001
    assert score == 0.0


def test_recommendations_calculate_weekly_coverage_empty():
    weekly = recommendations.calculate_weekly_coverage([])
    assert weekly == {}
