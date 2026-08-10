import os
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.routers import premium_week
from tests._client import open_test_client


@contextmanager
def _make_client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(premium_week.router)
    with open_test_client(app) as managed_client:
        yield managed_client


@contextmanager
def _make_pro_client() -> Iterator[TestClient]:
    from app.routers import pro

    app = FastAPI()
    app.include_router(pro.router)
    with open_test_client(app) as managed_client:
        yield managed_client


def _complete_targets() -> dict[str, Any]:
    return {
        "kcal": 2100,
        "macros": {
            "protein_g": 120.0,
            "fat_g": 70.0,
            "carbs_g": 230.0,
            "fiber_g": 31.0,
        },
        "micro": {"vitamin_c_mg": 90.0, "iron_mg": 14.0},
        "water_ml": 2300,
        "activity_week": {
            "moderate_aerobic_min": 150,
            "vigorous_aerobic_min": 75,
            "strength_sessions": 2,
            "steps_daily": 8500,
        },
    }


def _canonical_week_payload() -> dict[str, Any]:
    return {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "lentil_bowl",
                        "title_translated": "Lentil bowl",
                        "grams": {"lentils": 180.0},
                        "kcal": 430.0,
                        "macros": {
                            "protein_g": 26.0,
                            "fat_g": 12.0,
                            "carbs_g": 58.0,
                        },
                        "micros": {"iron_mg": 6.0},
                        "price_est": "4.50",
                    }
                ],
                "kcal": 430.0,
                "macros": {
                    "protein_g": 26.0,
                    "fat_g": 12.0,
                    "carbs_g": 58.0,
                },
                "micros": {"iron_mg": 6.0},
                "coverage": {"iron_mg": 60.0},
                "tips": ["Add greens"],
            }
        ],
        "weekly_coverage": {"protein_g": 1.0},
        "shopping_list": {"lentils_g": 500.0},
        "total_cost": 4.5,
        "adherence_score": 1.0,
    }


@patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
def test_premium_week_missing_profile_fields_returns_400() -> None:
    # Missing height/weight triggers the first 400 branch
    payload = {
        "sex": "male",
        "age": 30,
        # height_cm missing
        # weight_kg missing
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en",
    }
    with _make_client() as client:
        resp = client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_pro_key"},
        )
        assert resp.status_code == 400
        assert resp.headers["content-type"].startswith("application/json")
        # Now returns specific field name in error message
        detail = resp.json()["detail"]
        assert "Missing required field" in detail


@patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
def test_premium_week_explicit_null_activity_returns_400() -> None:
    # Explicit null does not activate model defaults; activity fails first.
    payload = {
        "sex": "female",
        "age": 28,
        "height_cm": 165,
        "weight_kg": 58,
        "activity": None,  # Explicit null is rejected before goal is evaluated.
        "goal": None,  # Unreachable because activity fails first.
        "diet_flags": [],
        "lang": "en",
    }
    with _make_client() as client:
        resp = client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_pro_key"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {
            "detail": "Missing user profile data (Missing required field: activity)"
        }


@patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
def test_premium_week_with_explicit_targets_happy_path_200() -> None:
    # Use explicit targets path to avoid relying on data-derived estimation
    payload = {
        "targets": {
            "kcal": 2000,
            "macros": {
                "protein_g": 110.0,
                "fat_g": 70.0,
                "carbs_g": 220.0,
                "fiber_g": 30.0,
            },
            "micro": {"vitamin_c_mg": 90.0, "iron_mg": 14.0},
            "water_ml": 0,
            "activity_week": {
                "moderate_aerobic_min": 150,
                "vigorous_aerobic_min": 75,
                "strength_sessions": 2,
                "steps_daily": 8000,
            },
        },
        "diet_flags": [],
        "lang": "en",
    }
    with _make_client() as client:
        resp = client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_pro_key"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        body = resp.json()
        assert "daily_menus" in body and isinstance(body["daily_menus"], list)
        assert "weekly_coverage" in body and isinstance(body["weekly_coverage"], dict)


def test_planning_target_service_validation_branches_for_ci_coverage() -> None:
    from app.services import nutrition_targets

    assert not nutrition_targets.is_complete_planning_targets({})
    assert not nutrition_targets.is_complete_planning_targets(
        {"kcal": 2000, "macros": "bad", "micro": {"iron_mg": 14.0}, "water_ml": 2000}
    )
    assert not nutrition_targets.is_complete_planning_targets(
        {"kcal": 2000, "macros": {"protein_g": 100.0}, "micro": "bad", "water_ml": 2000}
    )
    assert not nutrition_targets.is_complete_planning_targets(
        {
            "kcal": 2000,
            "macros": {"protein_g": 100.0},
            "micro": {"iron_mg": 14.0},
            "water_ml": 2000,
            "activity_week": "bad",
        }
    )
    assert not nutrition_targets.is_complete_planning_targets(
        {"kcal": 2000, "macros": {"protein_g": 100.0}, "micro": {}, "water_ml": 2000}
    )
    assert not nutrition_targets.is_complete_planning_targets(
        {"kcal": 2000, "macros": {}, "micro": {"iron_mg": 14.0}, "water_ml": 2000}
    )
    assert nutrition_targets.is_complete_planning_targets(_complete_targets())


def test_estimate_targets_from_profile_maps_core_payload_for_ci_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import nutrition_targets

    captured_profiles: list[Any] = []

    targets = SimpleNamespace(
        kcal_daily=2100,
        macros=SimpleNamespace(
            protein_g=120.0,
            fat_g=70.0,
            carbs_g=230.0,
            fiber_g=31.0,
        ),
        micros=SimpleNamespace(
            get_priority_nutrients=lambda: {"vitamin_c_mg": 90.0, "iron_mg": 14.0},
        ),
        water_ml_daily=2300,
        activity=SimpleNamespace(
            moderate_aerobic_min=150,
            vigorous_aerobic_min=75,
            strength_sessions=2,
            steps_daily=8500,
        ),
    )

    def _fake_build_nutrition_targets(profile: Any) -> Any:
        captured_profiles.append(profile)
        return targets

    monkeypatch.setattr(
        nutrition_targets,
        "build_nutrition_targets",
        _fake_build_nutrition_targets,
    )

    payload = nutrition_targets.estimate_targets_from_profile(
        sex="female",
        age=34,
        height_cm=168.0,
        weight_kg=64.0,
        activity="active",
        goal="maintain",
    )

    assert len(captured_profiles) == 1
    assert captured_profiles[0].sex == "female"
    assert captured_profiles[0].activity == "active"
    assert payload == _complete_targets()


@patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
def test_premium_week_profile_derived_targets_branch_is_ci_covered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import nutrition_targets

    monkeypatch.setattr(premium_week, "_get_food_db", lambda: object())
    monkeypatch.setattr(premium_week, "_get_recipe_db", lambda: object())
    monkeypatch.setattr(
        premium_week, "build_week", lambda *_args, **_kwargs: _canonical_week_payload()
    )
    monkeypatch.setattr(
        nutrition_targets,
        "estimate_targets_from_profile",
        lambda **_kwargs: _complete_targets(),
    )

    with _make_client() as client:
        resp = client.post(
            "/api/v1/premium/plan/week-flexible",
            json={
                "sex": "female",
                "age": 34,
                "height_cm": 168,
                "weight_kg": 64,
                "activity": "active",
                "goal": "maintain",
                "diet_flags": [],
                "lang": "en",
            },
            headers={"X-API-Key": "test_pro_key"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json()["daily_menus"][0]["meals"][0]["price_est"] == 4.5


@patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
def test_pro_week_profile_derived_targets_branch_is_ci_covered(
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
) -> None:
    from app.routers import pro
    from app.services import nutrition_targets

    monkeypatch.setattr(pro, "get_food_db", lambda: object())
    monkeypatch.setattr(pro, "get_recipe_db", lambda: object())
    monkeypatch.setattr(pro, "build_week", lambda *_args, **_kwargs: _canonical_week_payload())
    monkeypatch.setattr(
        nutrition_targets,
        "estimate_targets_from_profile",
        lambda **_kwargs: _complete_targets(),
    )

    with _make_pro_client() as client:
        resp = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 34,
                "height_cm": 168,
                "weight_kg": 64,
                "activity": "active",
                "goal": "maintain",
                "diet_flags": [],
                "lang": "en",
            },
            headers=pro_headers,
        )

        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json()["daily_menus"][0]["meals"][0]["price_est"] == 4.5
