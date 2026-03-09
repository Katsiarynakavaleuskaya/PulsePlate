"""Unit tests for weekly-plan DTO normalization helpers."""

from __future__ import annotations

import pytest

from app.schemas.weekly_plan import (
    WeeklyMealPlanResponse,
    normalize_weekly_plan_payload,
    require_weekly_plan_payload_shape,
)


def _valid_week_payload() -> dict[str, object]:
    return {
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


def test_normalize_weekly_plan_payload_normalizes_valid_numeric_like_values() -> None:
    payload = normalize_weekly_plan_payload(_valid_week_payload())

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


def test_normalize_weekly_plan_payload_rejects_non_mapping_root_payload() -> None:
    with pytest.raises(ValueError, match=r"weekly_plan must be a mapping"):
        normalize_weekly_plan_payload(["not", "a", "mapping"])


def test_normalize_weekly_plan_payload_rejects_non_mapping_day_payload() -> None:
    with pytest.raises(ValueError, match=r"daily_menus\[\] must be a mapping"):
        normalize_weekly_plan_payload(
            {
                "daily_menus": ["bad-day-payload"],
                "adherence_score": "0.9",
            }
        )


def test_normalize_weekly_plan_payload_rejects_non_mapping_meal_payload() -> None:
    with pytest.raises(
        ValueError,
        match=r"daily_menus\[\]\.meals\[\] must be a mapping",
    ):
        normalize_weekly_plan_payload(
            {
                "daily_menus": [
                    {
                        "meals": ["bad-meal-payload"],
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


def test_normalize_weekly_plan_payload_rejects_invalid_total_cost_scalars() -> None:
    with pytest.raises(ValueError, match=r"daily_menus\[\]\.total_cost must be a finite number"):
        normalize_weekly_plan_payload(
            {
                "daily_menus": [
                    {
                        "meals": [],
                        "kcal": "350",
                        "macros": {},
                        "micros": {},
                        "coverage": {},
                        "total_cost": "bad",
                    }
                ],
                "adherence_score": "0.9",
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


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda payload: payload["daily_menus"][0]["meals"].__setitem__(
                0,
                {
                    "title": 42,
                    "grams": {"oats": "50"},
                    "kcal": "350",
                    "macros": {"carbs": "30"},
                    "micros": {"iron": "2.5"},
                },
            ),
            r"daily_menus\[\]\.meals\[\]\.title must be a non-empty string",
        ),
        (
            lambda payload: payload["daily_menus"][0]["meals"].__setitem__(
                0,
                {
                    "title": "Breakfast",
                    "title_translated": 42,
                    "grams": {"oats": "50"},
                    "kcal": "350",
                    "macros": {"carbs": "30"},
                    "micros": {"iron": "2.5"},
                },
            ),
            r"daily_menus\[\]\.meals\[\]\.title_translated must be a non-empty string",
        ),
        (
            lambda payload: payload["daily_menus"][0]["meals"].__setitem__(
                0,
                {
                    "title": "Breakfast",
                    "grams": {1: "50"},
                    "kcal": "350",
                    "macros": {"carbs": "30"},
                    "micros": {"iron": "2.5"},
                },
            ),
            r"daily_menus\[\]\.meals\[\]\.grams keys must be strings",
        ),
        (
            lambda payload: payload["daily_menus"][0].__setitem__("meals", {}),
            r"daily_menus\[\]\.meals must be a list",
        ),
        (
            lambda payload: payload["daily_menus"][0].__setitem__("tips", "hydrate"),
            r"daily_menus\[\]\.tips must be a list of strings",
        ),
        (
            lambda payload: payload.__setitem__("daily_menus", {}),
            r"weekly plan payload missing required daily_menus list",
        ),
        (
            lambda payload: payload.__setitem__("total_cost", "bad"),
            r"weekly_plan.total_cost must be a finite number",
        ),
    ],
)
def test_normalize_weekly_plan_payload_covers_fail_closed_branches(mutator, message) -> None:
    payload = _valid_week_payload()
    mutator(payload)

    with pytest.raises(ValueError, match=message):
        normalize_weekly_plan_payload(payload)


def test_require_weekly_plan_payload_shape_rejects_non_mapping() -> None:
    with pytest.raises(ValueError, match=r"weekly plan payload must be a mapping"):
        require_weekly_plan_payload_shape(None)
