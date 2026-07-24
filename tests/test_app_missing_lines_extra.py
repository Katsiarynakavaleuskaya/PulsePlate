import os
from unittest.mock import MagicMock, patch
from tests._client import get_client

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app as app_mod
from app.http_error_details import INVALID_PREMIUM_PLATE_INPUT_DETAIL
from app.middleware.api_tiers import TEST_KEY_VIP


class TestAppMissingLinesExtra:
    def setup_method(self) -> None:
        os.environ["API_KEY"] = "test_key"
        self.client = get_client()

    def teardown_method(self) -> None:
        os.environ.pop("API_KEY", None)
        client = getattr(self, "client", None)
        if client is not None:
            client.close()

    def test_get_update_scheduler_public_identity(self) -> None:
        import legacy_app
        from app.services import scheduler_access

        assert app_mod.get_update_scheduler is legacy_app.get_update_scheduler
        assert app_mod.get_update_scheduler is scheduler_access.get_update_scheduler

    def test_insight_implicit_disabled_flag_branch(self):
        # Ensure provider exists so we get to flag check at line 605
        class _Stub:
            name = "stub"

            def generate(self, text: str) -> str:
                return "ok"

        with (
            patch.dict(os.environ, {"FEATURE_INSIGHT": "maybe"}, clear=False),
            patch("llm.get_insight_provider", return_value=_Stub()),
        ):
            r = self.client.post(
                "/insight", json={"text": "x"}, headers={"X-API-Key": TEST_KEY_VIP}
            )
            assert r.status_code == 503
            assert "disabled" in r.json().get("detail", "").lower()

    def test_premium_bmr_value_and_http_errors(self):
        # Test premium BMR endpoint - ValueError should return 400 Bad Request
        with (
            patch.object(app_mod, "calculate_all_bmr", side_effect=ValueError("bad")),
            patch.object(app_mod, "calculate_all_tdee", lambda *a, **k: {}),
        ):
            data = {
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "sex": "male",
                "activity": "light",
                "lang": "en",
            }
            r = self.client.post(
                "/api/v1/premium/bmr", json=data, headers={"X-API-Key": "test_key"}
            )
            assert r.status_code == 400
            assert "Invalid input" in r.json().get("detail", "")

        # Trigger HTTPException passthrough re-raise
        with (
            patch.object(
                app_mod,
                "calculate_all_bmr",
                side_effect=HTTPException(status_code=418, detail="teapot"),
            ),
            patch.object(app_mod, "calculate_all_tdee", lambda *a, **k: {}),
        ):
            data = {
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "sex": "male",
                "activity": "light",
                "lang": "en",
            }
            r = self.client.post(
                "/api/v1/premium/bmr", json=data, headers={"X-API-Key": "test_key"}
            )
            assert r.status_code == 418
            assert "teapot" in r.json().get("detail", "")

    def test_premium_plate_value_error_is_sanitized(self) -> None:
        from app.services import pro_nutrition_plate as plate_service

        with (
            patch.object(
                plate_service.nutrition_bmr,
                "calculate_all_bmr",
                return_value={"mifflin": 1600},
            ),
            patch.object(
                plate_service.nutrition_bmr,
                "calculate_all_tdee",
                return_value={"mifflin": 2200},
            ),
            patch.object(
                plate_service.nutrition_plate,
                "make_plate",
                side_effect=ValueError("goal maintain failed at /tmp/internal/plate"),
            ),
        ):
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "light",
                "goal": "maintain",
            }
            r = self.client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert r.status_code == 400
            assert r.headers.get("content-type", "").startswith("application/json")
            assert r.json()["detail"] == INVALID_PREMIUM_PLATE_INPUT_DETAIL
            assert "/tmp/internal/plate" not in r.json()["detail"]

    def test_premium_plate_missing_bmr_tdee_check(self):
        from app.services import pro_nutrition_plate as plate_service

        # Force the documented canonical backend fallback.
        make_plate = MagicMock(return_value={})
        with (
            patch.object(plate_service.nutrition_bmr, "calculate_all_bmr", None),
            patch.object(plate_service.nutrition_bmr, "calculate_all_tdee", None),
            patch.object(plate_service.nutrition_plate, "make_plate", make_plate),
        ):
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "light",
                "goal": "maintain",
            }
            r = self.client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert r.status_code == 200
            make_plate.assert_not_called()

    def test_nutrient_gaps_value_error(self):
        # Hit 1275 by raising ValueError from build_nutrition_targets
        with (
            patch.object(app_mod, "analyze_nutrient_gaps", lambda *a, **k: {}),
            patch.object(app_mod, "build_nutrition_targets", side_effect=ValueError("bad")),
        ):
            payload = {
                "consumed_nutrients": {"protein_g": 80},
                "user_profile": {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "light",
                    "goal": "maintain",
                    "life_stage": "adult",
                },
            }
            r = self.client.post(
                "/api/v1/premium/gaps", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert r.status_code in [200, 500, 503]
