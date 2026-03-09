"""Unit tests for weekly-plan DTO normalization helpers."""

from __future__ import annotations

import pytest

from app.schemas.weekly_plan import WeeklyMealPlanResponse, normalize_weekly_plan_payload


def test_normalize_weekly_plan_payload_normalizes_valid_numeric_like_values() -> None:
    payload = normalize_weekly_plan_payload(
        {
            "daily_menus": [
                {
                    "meals": [
                        {
                            "title": "Breakfast",
                            "title_translated": "Breakfast",
                            "grams": {"oats": "50"},
                            "kcal": "350",
                            "macros": {"carbs": "30"},
                            "micros": {"iron": "2.5"},
                            "price_est": "4.5",
                        }
                    ],
                    "kcal": "350",
                    "macros": {"carbs": "30"},
                    "micros": {"iron": "2.5"},
                    "coverage": {"protein": "80"},
                    "tips": ["Add fruit"],
                    "total_cost": None,
                }
            ],
            "weekly_coverage": {"protein": "92"},
            "shopping_list": {"oats": "50"},
            "total_cost": None,
            "adherence_score": "0.9",
        }
    )

    meal = payload["daily_menus"][0]["meals"][0]
    assert meal["grams"] == {"oats": 50.0}
    assert meal["kcal"] == 350.0
    assert meal["macros"] == {"carbs": 30.0}
    assert meal["micros"] == {"iron": 2.5}
    assert meal["price_est"] == 4.5
    assert payload["daily_menus"][0]["total_cost"] == 4.5
    assert payload["total_cost"] == 4.5
    WeeklyMealPlanResponse.model_validate(payload)


def test_normalize_weekly_plan_payload_rejects_invalid_numeric_entries() -> None:
    with pytest.raises(
        ValueError, match=r"daily_menus\[\]\.meals\[\]\.kcal must be a finite number"
    ):
        normalize_weekly_plan_payload(
            {
                "daily_menus": [
                    {
                        "meals": [
                            {
                                "title": "Breakfast",
                                "grams": {"oats": "50"},
                                "kcal": "bad",
                            }
                        ],
                        "kcal": "350",
                        "macros": {},
                        "micros": {},
                        "coverage": {},
                        "total_cost": None,
                    }
                ],
                "adherence_score": "0.9",
            }
        )


def test_normalize_weekly_plan_payload_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match=r"daily_menus\[\]\.kcal must be a finite number"):
        normalize_weekly_plan_payload(
            {
                "daily_menus": [
                    {
                        "meals": [],
                        "kcal": "inf",
                        "macros": {},
                        "micros": {},
                        "coverage": {"fiber": "-inf", "protein": "25"},
                        "total_cost": "12.5",
                    }
                ],
                "adherence_score": "nan",
            }
        )


def test_normalize_weekly_plan_payload_rejects_missing_meal_title() -> None:
    with pytest.raises(
        ValueError, match=r"daily_menus\[\]\.meals\[\]\.title must be a non-empty string"
    ):
        normalize_weekly_plan_payload(
            {
                "daily_menus": [
                    {
                        "meals": [
                            {
                                "title": "",
                                "grams": {"oats": "50"},
                                "kcal": "350",
                                "macros": {"carbs": "30"},
                                "micros": {"iron": "2.5"},
                            }
                        ],
                        "kcal": "350",
                        "macros": {},
                        "micros": {},
                        "coverage": {},
                        "total_cost": None,
                    }
                ],
                "adherence_score": "0.9",
            }
        )


def test_normalize_weekly_plan_payload_rejects_invalid_adherence_score() -> None:
    with pytest.raises(ValueError, match=r"adherence_score must be a finite number"):
        normalize_weekly_plan_payload(
            {
                "daily_menus": [
                    {
                        "meals": [],
                        "kcal": "350",
                        "macros": {},
                        "micros": {},
                        "coverage": {},
                        "total_cost": None,
                    }
                ],
                "adherence_score": "nan",
            }
        )
