from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from app.routers import premium_week


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(premium_week.router)
    return TestClient(cast(ASGIApp, app))


def test_premium_week_missing_profile_fields_returns_400():
    client = _make_client()
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
    resp = client.post("/api/v1/premium/plan/week-flexible", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Missing user profile data"


def test_premium_week_activity_goal_required_branch_returns_400():
    client = _make_client()
    # Provide core fields, but set activity/goal to null to hit second 400 branch
    payload = {
        "sex": "female",
        "age": 28,
        "height_cm": 165,
        "weight_kg": 58,
        "activity": None,
        "goal": None,
        "diet_flags": [],
        "lang": "en",
    }
    resp = client.post("/api/v1/premium/plan/week-flexible", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "All profile fields are required"


def test_premium_week_with_explicit_targets_happy_path_200():
    client = _make_client()
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
    resp = client.post("/api/v1/premium/plan/week-flexible", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "daily_menus" in body and isinstance(body["daily_menus"], list)
    assert "weekly_coverage" in body and isinstance(body["weekly_coverage"], dict)
