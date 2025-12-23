from __future__ import annotations

import os
import sys
from typing import Dict
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.routers import premium_week


def _get_test_client() -> TestClient:
    """Get test client with fresh app import."""
    # Ensure we're in test mode
    os.environ["APP_ENV"] = "test"
    os.environ["DEBUG"] = "true"

    # Reload app module to pick up environment changes
    if "app" in sys.modules:
        del sys.modules["app"]

    import app as app_mod

    return TestClient(app_mod.app)


def _make_profile_payload(extra: Dict[str, object] | None = None) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "sex": "female",
        "age": 34,
        "height_cm": 168,
        "weight_kg": 62,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": ["high_protein"],
        "lang": "en",
    }
    if extra:
        payload |= extra
    return payload


class TestPremiumWeekPlanEndToEnd:
    """Интеграционные тесты премиального недельного плана."""

    @patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
    def test_requires_valid_api_key(self):
        """Без ключа / неверный ключ получаем 401/403."""
        client = _get_test_client()
        payload = _make_profile_payload()
        response = client.post("/api/v1/premium/plan/week-flexible", json=payload)
        # Without API key, we get 401 (Unauthorized) - but in dev mode with lenient keys
        # we might get through to PRO tier check which returns 403
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "wrong"},
            json=payload,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
    def test_missing_profile_fields(self):
        client = _get_test_client()
        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "test_pro_key"},
            json={"sex": "female"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing user profile" in response.text

    @patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
    def test_success_profile_flow(self, monkeypatch):
        client = _get_test_client()
        captured = {}

        def fake_build_week(targets, diet_flags, lang, fooddb, recipedb):
            captured.update({"targets": targets, "diet_flags": diet_flags, "lang": lang})
            return {
                "daily_menus": [{"kcal": 2200}],
                "weekly_coverage": {"protein": 0.9},
                "shopping_list": {"eggs": 12},
                "total_cost": 37.5,
                "adherence_score": 0.8,
            }

        monkeypatch.setattr(premium_week, "build_week", fake_build_week)
        monkeypatch.setattr(premium_week, "FoodDB", lambda *_args, **_kwargs: object())
        monkeypatch.setattr(premium_week, "RecipeDB", lambda *_args, **_kwargs: object())

        payload = _make_profile_payload()
        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "test_pro_key"},
            json=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["total_cost"] == pytest.approx(37.5)
        assert captured["targets"]["kcal"] > 0
        assert captured["lang"] == "en"

    @patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
    def test_success_explicit_targets(self, monkeypatch):
        client = _get_test_client()
        recorded = {}

        def fake_build_week(targets, diet_flags, lang, fooddb, recipedb):
            recorded.update(
                {
                    "targets": targets,
                    "diet_flags": diet_flags,
                    "lang": lang,
                }
            )
            return {
                "daily_menus": [{"kcal": 2500}],
                "weekly_coverage": {"fiber": 1.1},
                "shopping_list": {"avocado": 4},
                "total_cost": 44.0,
                "adherence_score": 0.82,
            }

        monkeypatch.setattr(premium_week, "build_week", fake_build_week)
        monkeypatch.setattr(premium_week, "FoodDB", lambda *_args, **_kwargs: object())
        monkeypatch.setattr(premium_week, "RecipeDB", lambda *_args, **_kwargs: object())

        explicit_targets = {
            "targets": {
                "kcal": 2300,
                "macros": {"protein_g": 120, "fat_g": 60, "carbs_g": 250, "fiber_g": 30},
                "micro": {"vitamin_c_mg": 90},
                "water_ml": 2200,
                "activity_week": {
                    "moderate_aerobic_min": 150,
                    "vigorous_aerobic_min": 75,
                    "strength_sessions": 3,
                    "steps_daily": 9000,
                },
            },
            "diet_flags": ["plant_based"],
            "lang": "en",
        }

        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "test_pro_key"},
            json=explicit_targets,
        )
        assert response.status_code == status.HTTP_200_OK
        assert recorded["targets"]["macros"]["protein_g"] == 120
        assert recorded["diet_flags"] == ["plant_based"]
        assert recorded["lang"] == "en"
        assert response.json()["daily_menus"][0]["kcal"] == 2500

    @patch.dict(os.environ, {"APP_ENV": "test", "DEBUG": "true"})
    def test_invalid_macro_values(self):
        client = _get_test_client()
        payload = {
            "targets": {
                "kcal": 2200,
                "macros": {"protein_g": "oops"},
                "micro": {},
                "water_ml": 2000,
            }
        }

        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "test_pro_key"},
            json=payload,
        )
        # Use non-deprecated 422 constant to avoid DeprecationWarning
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "macros" in response.text
