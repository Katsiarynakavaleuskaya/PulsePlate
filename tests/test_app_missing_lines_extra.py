import os
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

import app as app_mod


class TestAppMissingLinesExtra:
    def setup_method(self):
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app_mod.app)

    def teardown_method(self):
        os.environ.pop("API_KEY", None)

    def test_get_update_scheduler_late_import_path(self):
        # Force late import branch by nulling the cached getter
        app_mod._scheduler_getter = None  # type: ignore[attr-defined]

        async def _fake_getter():
            class _Dummy:
                pass

            return _Dummy()

        # Patch the real module symbol that late import will read
        import asyncio

        import core.food_apis.scheduler as sched

        with patch.object(sched, "get_update_scheduler", _fake_getter):
            obj = asyncio.get_event_loop().run_until_complete(app_mod.get_update_scheduler())
            assert obj is not None

    def test_lifespan_error_branches(self):
        # Make startup/shutdown raise to hit except blocks (112-125)
        async def _boom_start(*a, **kw):
            raise RuntimeError("boom-start")

        async def _boom_stop(*a, **kw):
            raise RuntimeError("boom-stop")

        with (
            patch.object(app_mod, "start_background_updates", _boom_start),
            patch.object(app_mod, "stop_background_updates", _boom_stop),
        ):
            with TestClient(app_mod.app) as c:
                r = c.get("/health")
                assert r.status_code == 200

    def test_bmi_pregnancy_visualization_branch(self):
        # include_chart True + pregnant path should attach visualization (405-410)
        with patch.object(
            app_mod,
            "generate_bmi_visualization",
            lambda **kw: {"available": True, "x": 1},
        ):
            payload = {
                "weight_kg": 60.0,
                "height_m": 1.65,
                "age": 29,
                "gender": "female",
                "pregnant": "yes",
                "athlete": "no",
                "waist_cm": 80.0,
                "lang": "en",
                "include_chart": True,
            }
            r = self.client.post("/bmi", json=payload)
            assert r.status_code == 200
            data = r.json()
            assert "visualization" in data

    def test_insight_implicit_disabled_flag_branch(self):
        # Ensure provider exists so we get to flag check at line 605
        class _Stub:
            name = "stub"

            def generate(self, text: str) -> str:
                return "ok"

        with (
            patch.dict(os.environ, {"FEATURE_INSIGHT": "maybe"}, clear=False),
            patch("llm.get_provider", return_value=_Stub()),
        ):
            r = self.client.post("/insight", json={"text": "x"})
            assert r.status_code == 503
            assert "disabled" in r.json().get("detail", "").lower()

    def test_premium_bmr_value_and_http_errors(self):
        # Trigger ValueError path (820)
        with (
            patch.object(app_mod, "calculate_all_bmr", side_effect=ValueError("bad")),
            patch.object(app_mod, "calculate_all_tdee", lambda *a, **k: {}),
            patch.object(app_mod, "get_activity_descriptions", lambda: {}),
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

        # Trigger HTTPException passthrough re-raise (818)
        with (
            patch.object(
                app_mod,
                "calculate_all_bmr",
                side_effect=HTTPException(status_code=418, detail="teapot"),
            ),
            patch.object(app_mod, "calculate_all_tdee", lambda *a, **k: {}),
            patch.object(app_mod, "get_activity_descriptions", lambda: {}),
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

    def test_premium_plate_missing_bmr_tdee_check(self):
        # Force the early 503 guard (974)
        with (
            patch.object(app_mod, "calculate_all_bmr", None),
            patch.object(app_mod, "calculate_all_tdee", None),
            patch.object(app_mod, "make_plate", lambda **k: {}),
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
            assert r.status_code == 503

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
            assert r.status_code == 400

    def test_bmi_pro_error_handlers(self):
        # Trigger ValueError branch (1519-1523)
        with patch.object(app_mod, "stage_obesity", side_effect=ValueError("oops")):
            payload = {
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 80.0,
                "hip_cm": 95.0,
                "lang": "en",
            }
            r = self.client.post("/api/v1/bmi/pro", json=payload, headers={"X-API-Key": "test_key"})
            assert r.status_code == 400

        # Trigger generic Exception branch (1524-1525)
        with patch.object(app_mod, "stage_obesity", side_effect=RuntimeError("boom")):
            payload = {
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 80.0,
                "hip_cm": 95.0,
                "lang": "en",
            }
            r = self.client.post("/api/v1/bmi/pro", json=payload, headers={"X-API-Key": "test_key"})
            assert r.status_code == 500

    def test_export_pdf_generic_errors(self):
        # Hit 1677-1678 and 1740-1741 by raising generic exceptions from to_pdf_*
        with patch.object(app_mod, "to_pdf_day", side_effect=RuntimeError("x")):
            r = self.client.get(
                "/api/v1/premium/exports/day/plan123.pdf",
                headers={"X-API-Key": "test_key"},
            )
            assert r.status_code == 500

        with patch.object(app_mod, "to_pdf_week", side_effect=RuntimeError("y")):
            r = self.client.get(
                "/api/v1/premium/exports/week/plan123.pdf",
                headers={"X-API-Key": "test_key"},
            )
            assert r.status_code == 500
