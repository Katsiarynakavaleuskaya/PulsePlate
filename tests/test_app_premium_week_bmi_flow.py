from __future__ import annotations

from typing import Dict, Generator

import pytest
from fastapi import status

from app.routers import premium_week


@pytest.fixture
def set_strict_api_key(
    monkeypatch: pytest.MonkeyPatch, app_module, app
) -> Generator[None, None, None]:
    """Включаем строгий режим API-ключей (RU/EN)."""
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("API_KEY", "test_key")

    original_guard = app.dependency_overrides.get(app_module._get_api_key_dynamic)
    app.dependency_overrides[app_module._get_api_key_dynamic] = app_module.get_api_key
    yield
    if original_guard is not None:
        app.dependency_overrides[app_module._get_api_key_dynamic] = original_guard
    else:
        app.dependency_overrides.pop(app_module._get_api_key_dynamic, None)


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

    def test_requires_valid_api_key(self, client, set_strict_api_key):
        """Без ключа / неверный ключ получаем 403."""
        payload = _make_profile_payload()
        response = client.post("/api/v1/premium/plan/week-flexible", json=payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "wrong"},
            json=payload,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_profile_fields(self, client, set_strict_api_key):
        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            headers={"X-API-Key": "test_key"},
            json={"sex": "female"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing user profile" in response.text

    def test_success_profile_flow(self, client, set_strict_api_key, monkeypatch):
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
            headers={"X-API-Key": "test_key"},
            json=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["total_cost"] == pytest.approx(37.5)
        assert captured["targets"]["kcal"] > 0
        assert captured["lang"] == "en"

    def test_success_explicit_targets(self, client, set_strict_api_key, monkeypatch):
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
            headers={"X-API-Key": "test_key"},
            json=explicit_targets,
        )
        assert response.status_code == status.HTTP_200_OK
        assert recorded["targets"]["macros"]["protein_g"] == 120
        assert recorded["diet_flags"] == ["plant_based"]
        assert recorded["lang"] == "en"
        assert response.json()["daily_menus"][0]["kcal"] == 2500

    def test_invalid_macro_values(self, client, set_strict_api_key):
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
            headers={"X-API-Key": "test_key"},
            json=payload,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "macros" in response.text
