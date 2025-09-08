import os

from fastapi.testclient import TestClient

from app import app
from core.menu_engine import make_daily_menu, make_weekly_menu
from core.targets import UserProfile


def _profile():
    return UserProfile(
        sex="male",
        age=30,
        height_cm=175,
        weight_kg=70,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
        life_stage="adult",
    )


def test_make_daily_menu_smoke():
    prof = _profile()
    day = make_daily_menu(prof)
    assert day is not None
    assert isinstance(day.meals, list)
    assert isinstance(day.coverage, dict)


def test_make_weekly_menu_smoke():
    prof = _profile()
    week = make_weekly_menu(prof)
    assert week is not None
    assert isinstance(week.weekly_coverage, dict)
    assert hasattr(week, "daily_menus") and len(week.daily_menus) == 7


def test_weekly_menu_endpoint_smoke():
    # Ensure API key is optional if not set; if set, pass header
    client = TestClient(app)
    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 70,
        "activity": "moderate",
        "goal": "maintain",
    }
    headers = {}
    if os.getenv("API_KEY"):
        headers["X-API-Key"] = os.getenv("API_KEY")
    r = client.post("/api/v1/premium/plan/week", json=payload, headers=headers)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        data = r.json()
        assert "weekly_coverage" in data or "week_summary" in data
