"""Unit tests for weekly-plan DTO normalization helpers."""

from __future__ import annotations

from app.schemas.weekly_plan import normalize_weekly_plan_payload


def test_normalize_weekly_plan_payload_skips_invalid_numeric_entries() -> None:
    payload = normalize_weekly_plan_payload(
        {
            "daily_menus": [
                {
                    "meals": [
                        {
                            "title": "Breakfast",
                            "grams": {"oats": "50", 7: "10"},
                            "kcal": "bad",
                            "macros": {"protein": "nan", "carbs": "30"},
                            "micros": {"iron": object()},
                            "price_est": "oops",
                        }
                    ],
                    "total_cost": None,
                }
            ],
            "total_cost": None,
        }
    )

    meal = payload["daily_menus"][0]["meals"][0]
    assert meal["grams"] == {"oats": 50.0}
    assert meal["kcal"] == 0.0
    assert meal["macros"] == {"carbs": 30.0}
    assert meal["micros"] == {}
    assert meal["price_est"] is None
    assert payload["daily_menus"][0]["total_cost"] == 0.0
    assert payload["total_cost"] == 0.0


def test_normalize_weekly_plan_payload_rejects_non_finite_numbers() -> None:
    payload = normalize_weekly_plan_payload(
        {
            "daily_menus": [
                {
                    "kcal": "inf",
                    "coverage": {"fiber": "-inf", "protein": "25"},
                    "total_cost": "12.5",
                }
            ],
            "adherence_score": "nan",
        }
    )

    day = payload["daily_menus"][0]
    assert day["kcal"] == 0.0
    assert day["coverage"] == {"protein": 25.0}
    assert payload["adherence_score"] == 0.0
