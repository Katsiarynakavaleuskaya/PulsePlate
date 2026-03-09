"""
Tests for PRO Router using isolated TestClient

RU: Тесты роутера PRO через изолированный TestClient.
EN: PRO router tests via isolated TestClient.

Covers:
- POST /api/v1/pro/meal/weekly (profile fallback, validation, missing fields)
- GET /api/v1/pro/nutrition/daily (date validation, profile validation, core exception)
- require_pro_tier guard override
- Mock heavy core logic (build_week, build_nutrition_targets, DBs)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

EXPECTED_DAILY_SEGMENTS = ["vegetables", "protein", "carbs", "fats"]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent time.sleep in any core logic to avoid test hangs."""
    import time

    monkeypatch.setattr(time, "sleep", lambda _: None)


class TestProRouterIsolated:
    """Isolated TestClient tests for app/routers/pro.py endpoints."""

    def setup_method(self) -> None:
        """Set up test client with isolated router and PRO tier override."""
        from app.routers import pro as pro_mod

        self.pro_mod = pro_mod
        self.router = pro_mod.router

        self.app = FastAPI()
        self.app.include_router(self.router)

        # Override PRO guard to bypass authentication
        from app.middleware.api_tiers import require_pro_tier

        self.app.dependency_overrides[require_pro_tier] = lambda: None

        self.client = TestClient(self.app)

    def teardown_method(self) -> None:
        """Clean up test client and dependency overrides."""
        self.client.close()
        self.app.dependency_overrides.clear()

    def _patch_week_core(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mock heavy weekly plan dependencies: DBs + build_week."""
        monkeypatch.setattr(self.pro_mod, "get_food_db", lambda: object())
        monkeypatch.setattr(self.pro_mod, "get_recipe_db", lambda: object())

        def _fake_build_week(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "daily_menus": [
                    {
                        "meals": [
                            {
                                "title": "salmon_bowl",
                                "title_translated": "Salmon bowl",
                                "grams": {"salmon": 150.0},
                                "kcal": 420.0,
                                "macros": {"protein_g": 35.0, "fat_g": 18.0, "carbs_g": 12.0},
                                "micros": {"omega3_mg": 900.0},
                                "price_est": "5.25",
                            }
                        ],
                        "kcal": 420.0,
                        "macros": {"protein_g": 35.0, "fat_g": 18.0, "carbs_g": 12.0},
                        "micros": {"omega3_mg": 900.0},
                        "coverage": {"omega3_mg": 85.0},
                        "tips": ["Add greens"],
                    }
                ],
                "weekly_coverage": {"protein_g": 1.0},
                "shopping_list": {"rice_g": 500.0},
                "total_cost": 5.25,
                "adherence_score": 1.0,
            }

        monkeypatch.setattr(self.pro_mod, "build_week", _fake_build_week)

    def _patch_daily_core_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mock build_nutrition_targets + segment i18n for deterministic tests."""

        @dataclass(frozen=True)
        class _Macros:
            protein_g: float
            carbs_g: float
            fat_g: float

        @dataclass(frozen=True)
        class _Targets:
            macros: _Macros

        def _fake_build_targets(profile: Any) -> _Targets:
            return _Targets(macros=_Macros(protein_g=50.0, carbs_g=60.0, fat_g=20.0))

        monkeypatch.setattr(self.pro_mod, "build_nutrition_targets", _fake_build_targets)
        monkeypatch.setattr(self.pro_mod, "translate_nutrition_segment", lambda lang, key: f"{key}")

    def test_weekly_meal_plan_happy_path_with_profile(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /meal/weekly with valid profile returns 200."""
        self._patch_week_core(monkeypatch)

        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }

        resp = self.client.post("/api/v1/pro/meal/weekly", json=payload)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert "daily_menus" in data
        assert "weekly_coverage" in data
        assert "shopping_list" in data
        assert "total_cost" in data
        assert "adherence_score" in data
        assert data["daily_menus"][0]["meals"][0]["price_est"] == 5.25
        assert data["daily_menus"][0]["total_cost"] == 5.25

    def test_weekly_meal_plan_pipeline_type_mismatch_raises_typeerror(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Covers defensive TypeError path when weekly pipeline returns unexpected type."""
        # Avoid DB reads and other heavy deps.
        monkeypatch.setattr(self.pro_mod, "get_food_db", lambda: object())
        monkeypatch.setattr(self.pro_mod, "get_recipe_db", lambda: object())

        # Bypass profile/targets validation to focus on pipeline contract.
        monkeypatch.setattr(self.pro_mod, "_is_complete_targets", lambda _d: True)

        def _fake_pipeline(**_kwargs: Any) -> str:
            return "not-a-week-plan-response"

        monkeypatch.setattr(self.pro_mod, "run_weekly_pipeline_guarded", _fake_pipeline)

        with pytest.raises(TypeError, match=r"Expected ProWeekPlanResponse"):
            _ = self.client.post("/api/v1/pro/meal/weekly", json={})

    def test_weekly_meal_plan_invalid_payload_surfaces_postprocess_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed build output must fail closed in the postprocess stage."""
        monkeypatch.setattr(self.pro_mod, "get_food_db", lambda: object())
        monkeypatch.setattr(self.pro_mod, "get_recipe_db", lambda: object())
        monkeypatch.setattr(self.pro_mod, "_is_complete_targets", lambda _d: True)

        def _fake_pipeline(**kwargs: Any) -> dict[str, Any]:
            postprocess_fn = kwargs["postprocess_fn"]
            try:
                postprocess_fn({"weekly_coverage": {}, "shopping_list": {}})
            except ValueError:
                return {
                    "status": "error",
                    "code": "weekly_postprocess_failed",
                    "message": "Failed to build weekly plan response",
                }
            raise AssertionError("postprocess_fn should fail for malformed weekly payloads")

        monkeypatch.setattr(self.pro_mod, "run_weekly_pipeline_guarded", _fake_pipeline)

        response = self.client.post("/api/v1/pro/meal/weekly", json={})
        assert response.status_code == 500, response.text
        assert response.json()["code"] == "weekly_postprocess_failed"

    def test_weekly_meal_plan_missing_profile_field_400(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /meal/weekly with missing sex field returns 400."""
        self._patch_week_core(monkeypatch)

        payload = {
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        }

        resp = self.client.post("/api/v1/pro/meal/weekly", json=payload)
        assert resp.status_code == 400, resp.text
        assert "Missing user profile data" in resp.text

    def test_weekly_meal_plan_422_validation(self) -> None:
        """POST /meal/weekly with invalid age (<= 10) returns 422."""
        payload = {"sex": "female", "age": 5, "height_cm": 170, "weight_kg": 65}

        resp = self.client.post("/api/v1/pro/meal/weekly", json=payload)
        assert resp.status_code == 422, resp.text

    def test_weekly_meal_plan_happy_path_with_targets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /meal/weekly with profile + explicit targets uses targets path."""
        self._patch_week_core(monkeypatch)

        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 80,
            "activity": "moderate",
            "goal": "maintain",
            "targets": {  # Explicit targets override profile-derived values
                "kcal": 1800.0,
                "macros": {
                    "protein_g": 80.0,
                    "carbs_g": 200.0,
                    "fat_g": 60.0,
                },
                "micro": {},
            },
        }

        resp = self.client.post("/api/v1/pro/meal/weekly", json=payload)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert "daily_menus" in data
        assert "weekly_coverage" in data
        assert "shopping_list" in data
        assert "total_cost" in data
        assert "adherence_score" in data

    def test_weekly_meal_plan_missing_profile_and_targets_400(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /meal/weekly with missing profile and targets returns 400."""
        self._patch_week_core(monkeypatch)

        resp = self.client.post("/api/v1/pro/meal/weekly", json={})
        assert resp.status_code == 400, resp.text

        data = resp.json()
        assert isinstance(data, dict)
        assert "detail" in data

    def test_daily_nutrition_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GET /nutrition/daily with valid params returns 200 with segments."""
        self._patch_daily_core_success(monkeypatch)

        params = {
            "date": "2025-12-20",
            "sex": "male",
            "age": 35,
            "height_cm": 180,
            "weight_kg": 85,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
        }

        resp = self.client.get("/api/v1/pro/nutrition/daily", params=params)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["date"] == "2025-12-20"
        assert data["total_progress"] == 0.0

        segments = data["segments"]
        assert isinstance(segments, list)
        assert len(segments) == len(EXPECTED_DAILY_SEGMENTS)
        assert [segment["name"] for segment in segments] == EXPECTED_DAILY_SEGMENTS

        for s in segments:
            assert "name" in s
            assert "current_value" in s
            assert "target_value" in s
            assert "percentage" in s
            assert "color" in s
            assert "icon" in s

    def test_daily_nutrition_invalid_date_pattern_422(self) -> None:
        """GET /nutrition/daily with wrong date format returns 422."""
        params = {"date": "20-12-2025", "sex": "male", "age": 35, "height_cm": 180, "weight_kg": 85}

        resp = self.client.get("/api/v1/pro/nutrition/daily", params=params)
        assert resp.status_code == 422, resp.text

    def test_daily_nutrition_invalid_date_value_400(self) -> None:
        """GET /nutrition/daily with invalid date value (Feb 30) returns 400."""
        params = {"date": "2025-02-30", "sex": "male", "age": 35, "height_cm": 180, "weight_kg": 85}

        resp = self.client.get("/api/v1/pro/nutrition/daily", params=params)
        assert resp.status_code == 400, resp.text
        assert "Invalid date format" in resp.text

    def test_daily_nutrition_missing_required_query_422(self) -> None:
        """GET /nutrition/daily without required params returns 422."""
        params = {"date": "2025-12-20"}

        resp = self.client.get("/api/v1/pro/nutrition/daily", params=params)
        assert resp.status_code == 422, resp.text

    def test_daily_nutrition_build_targets_failure_500(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GET /nutrition/daily when build_nutrition_targets raises returns 500."""
        monkeypatch.setattr(self.pro_mod, "translate_nutrition_segment", lambda lang, key: f"{key}")

        def _boom(profile: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(self.pro_mod, "build_nutrition_targets", _boom)

        params = {
            "date": "2025-12-20",
            "sex": "male",
            "age": 35,
            "height_cm": 180,
            "weight_kg": 85,
        }

        resp = self.client.get("/api/v1/pro/nutrition/daily", params=params)
        assert resp.status_code == 500, resp.text
        assert "Failed to calculate nutrition targets" in resp.text
