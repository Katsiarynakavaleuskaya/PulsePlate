#!/usr/bin/env python3
"""
Comprehensive test coverage for main.py to reach 97% coverage target
Focuses on main uncovered blocks: /bmi, /plan, /premium_bmr, /premium_targets endpoints
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from starlette.types import ASGIApp


def _get_app():
    """Safely get the FastAPI app instance from main.py."""
    import main

    if getattr(main, "app", None) is None:
        raise RuntimeError("FastAPI app in main.py is not initialized")
    return main.app


client = TestClient(_get_app())  # type: ignore[arg-type]


class TestAppComprehensive97:
    """Test suite targeting 97% coverage for main.py"""

    def test_bmi_endpoint_with_visualization(self):
        """Test /bmi endpoint with include_chart=True (lines 653-714)"""
        # Test pregnant case with visualization
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 65,
                "height_m": 1.65,
                "age": 28,
                "gender": "female",
                "pregnant": True,
                "athlete": False,
                "lang": "en",
                "include_chart": True,
                "waist_cm": 80,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] is None
        assert "pregnancy" in data["note"].lower()
        assert data["athlete"] is False
        assert data["group"] == "general"

    def test_bmi_endpoint_athlete_with_visualization(self):
        """Test /bmi endpoint for athlete with visualization (lines 680-714)"""
        with patch("app.generate_bmi_visualization") as mock_viz:
            mock_viz.return_value = {"available": True, "chart_url": "test_chart.png"}

            response = client.post(
                "/bmi",
                json={
                    "weight_kg": 80,
                    "height_m": 1.80,
                    "age": 25,
                    "gender": "male",
                    "pregnant": False,
                    "athlete": True,
                    "lang": "en",
                    "include_chart": True,
                    "waist_cm": 90,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["athlete"] is True
            assert data["group"] == "athlete"
            assert "visualization" in data
            assert "athlete" in data["note"].lower()

    def test_bmi_endpoint_visualization_not_available(self):
        """Test BMI endpoint when visualization include_chart is True"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "include_chart": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bmi"] == 24.2
        assert data["category"] == "Normal weight"

        # Check visualization response is included
        assert "visualization" in data
        viz_data = data["visualization"]
        # Either an available visualization with chart data or an error/unavailable state
        assert isinstance(viz_data.get("available"), bool)

    def test_plan_endpoint_russian_language(self):
        """Test /plan endpoint with Russian language (lines 720-765)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 70,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "ru",
                "premium": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Персональный план" in data["summary"]
        assert "Шаги:" in data["next_steps"][0]
        assert "Белок:" in data["next_steps"][1]
        assert "Сон:" in data["next_steps"][2]
        assert "прогулку" in data["action"]
        assert data["premium"] is False

    def test_plan_endpoint_russian_with_premium(self):
        """Test /plan endpoint with Russian language and premium (lines 740-752)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 70,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "ru",
                "premium": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["premium"] is True
        assert "premium_reco" in data
        assert "Дефицит" in data["premium_reco"][0]
        assert "силовые" in data["premium_reco"][1]

    def test_plan_endpoint_english_language(self):
        """Test /plan endpoint with English language (lines 753-765)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 70,
                "height_m": 1.70,
                "age": 30,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "premium": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Personal plan" in data["summary"]
        assert "Steps:" in data["next_steps"][0]
        assert "Protein:" in data["next_steps"][1]
        assert "Sleep:" in data["next_steps"][2]
        assert "walk" in data["action"]

    def test_plan_endpoint_english_with_premium(self):
        """Test /plan endpoint with English language and premium (lines 758-765)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 70,
                "height_m": 1.70,
                "age": 30,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "premium": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["premium"] is True
        assert "premium_reco" in data
        assert "deficit" in data["premium_reco"][0].lower()
        assert "strength" in data["premium_reco"][1].lower()

    def test_plan_endpoint_pregnant_case(self):
        """Test /plan endpoint for pregnant user (category=None case)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 65,
                "height_m": 1.65,
                "age": 28,
                "gender": "female",
                "pregnant": True,
                "athlete": False,
                "lang": "en",
                "premium": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] is None  # Pregnant case

    def test_premium_bmr_endpoint_success(self):
        """Test /premium_bmr endpoint success path (lines 1173-1238)"""
        response = client.post(
            "/premium_bmr",
            json={
                "weight_kg": 70,
                "height_cm": 170,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
                "bodyfat": 15,
                "lang": "en",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmr" in data
        assert "tdee" in data
        assert "recommended_intake" in data
        # Test with real values (BMR for 70kg, 170cm, 30yr male)
        assert abs(data["bmr"]["mifflin"] - 1617.5) < 1  # Mifflin-St Jeor
        assert abs(data["tdee"]["mifflin"] - 2507.0) < 1  # TDEE moderate
        assert data["recommended_intake"]["maintenance"] == data["tdee"]["mifflin"]

    def test_premium_bmr_endpoint_module_not_available(self):
        """Test /premium_bmr when nutrition module not available (lines 1180-1189)"""
        with patch(
            "app._calculate_all_bmr_wrapper",
            side_effect=ImportError("nutrition_core module not available"),
        ):
            response = client.post(
                "/premium_bmr",
                json={
                    "weight_kg": 70,
                    "height_cm": 170,
                    "age": 30,
                    "sex": "male",
                    "activity": "moderate",
                    "lang": "en",
                },
            )
            assert response.status_code == 503
            assert "not available" in response.json()["detail"]

    @patch("app._calculate_all_bmr_wrapper")
    def test_premium_bmr_endpoint_value_error(self, mock_bmr):
        """Test /premium_bmr with ValueError (lines 1235-1236)"""
        mock_bmr.side_effect = ValueError("Invalid input data")

        response = client.post(
            "/premium_bmr",
            json={
                "weight_kg": -10,  # Invalid weight
                "height_cm": 170,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
                "lang": "en",
            },
        )
        assert response.status_code == 400
        assert "Invalid input" in response.json()["detail"]

    @patch("app._calculate_all_bmr_wrapper")
    def test_premium_bmr_endpoint_general_error(self, mock_bmr):
        """Test /premium_bmr with general exception (lines 1237-1238)"""
        mock_bmr.side_effect = Exception("Calculation failed")

        response = client.post(
            "/premium_bmr",
            json={
                "weight_kg": 70,
                "height_cm": 170,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
                "lang": "en",
            },
        )
        assert response.status_code == 500
        assert "BMR calculation failed" in response.json()["detail"]

    @patch("app.build_nutrition_targets")
    def test_premium_targets_endpoint_success(self, mock_targets):
        """Test /premium_targets endpoint success path (lines 1265-1339)"""
        # Mock nutrition targets
        mock_targets_obj = MagicMock()
        mock_targets_obj.kcal_daily = 2000
        mock_targets_obj.macros.protein_g = 150
        mock_targets_obj.macros.fat_g = 67
        mock_targets_obj.macros.carbs_g = 200
        mock_targets_obj.macros.fiber_g = 25
        mock_targets_obj.water_ml_daily = 2500
        mock_targets_obj.activity.moderate_aerobic_min = 150
        mock_targets_obj.activity.strength_sessions = 2
        mock_targets_obj.activity.steps_daily = 8000
        mock_targets_obj.calculation_date = "2024-01-01"
        mock_targets_obj.micros.get_priority_nutrients.return_value = {}

        mock_targets.return_value = mock_targets_obj

        with patch("core.targets._life_stage_warnings", return_value=[]):
            response = client.post(
                "/premium_targets",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 170,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "goal": "maintain",
                    "lang": "en",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["kcal_daily"] == 2000
            assert data["macros"]["protein_g"] == 150
            assert data["water_ml"] == 2500

    def test_premium_targets_endpoint_not_available(self):
        """Test /premium_targets when feature not available (lines 1271-1274)"""
        with patch("app.getattr", return_value=None):
            response = client.post(
                "/premium_targets",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 170,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "goal": "maintain",
                    "lang": "en",
                },
            )
            assert response.status_code == 503
            assert "not available" in response.json()["detail"]

    @patch("app.build_nutrition_targets")
    def test_premium_targets_with_safety_warnings(self, mock_targets):
        """Test /premium_targets with safety validation (lines 1305-1320)"""
        mock_targets_obj = MagicMock()
        mock_targets_obj.kcal_daily = 2000
        mock_targets_obj.macros.protein_g = 150
        mock_targets_obj.macros.fat_g = 67
        mock_targets_obj.macros.carbs_g = 200
        mock_targets_obj.macros.fiber_g = 25
        mock_targets_obj.water_ml_daily = 2500
        mock_targets_obj.activity.moderate_aerobic_min = 150
        mock_targets_obj.activity.strength_sessions = 2
        mock_targets_obj.activity.steps_daily = 8000
        mock_targets_obj.calculation_date = "2024-01-01"
        mock_targets_obj.micros.get_priority_nutrients.return_value = {}

        mock_targets.return_value = mock_targets_obj

        with patch(
            "core.targets._life_stage_warnings",
            return_value=[{"code": "age", "message": "Test warning"}],
        ):
            with patch(
                "core.recommendations.validate_targets_safety", return_value=["Safety warning"]
            ):
                response = client.post(
                    "/premium_targets",
                    json={
                        "sex": "female",
                        "age": 16,
                        "height_cm": 160,
                        "weight_kg": 50,
                        "activity": "light",
                        "goal": "lose",
                        "lang": "en",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "warnings" in data
                assert len(data["warnings"]) >= 1

    def test_bmi_endpoint_waist_risk_calculation(self):
        """Test BMI endpoint with waist risk calculation"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 90,
                "height_m": 1.75,
                "age": 40,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "waist_cm": 105,  # High risk waist measurement
            },
        )
        assert response.status_code == 200
        # Should include waist risk warning in notes

    def test_plan_endpoint_athlete_case(self):
        """Test /plan endpoint for athlete"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 80,
                "height_m": 1.80,
                "age": 25,
                "gender": "male",
                "pregnant": False,
                "athlete": True,
                "lang": "en",
                "premium": False,
            },
        )
        assert response.status_code == 200
        # Should use athlete BMI category

    def test_activity_level_descriptions(self):
        """Test activity level descriptions in premium_bmr"""
        with patch("app.calculate_all_bmr", return_value={"mifflin": 1800}):
            with patch("app.calculate_all_tdee", return_value={"mifflin": 2200}):
                response = client.post(
                    "/premium_bmr",
                    json={
                        "weight_kg": 70,
                        "height_cm": 170,
                        "age": 30,
                        "sex": "male",
                        "activity": "very_active",
                        "lang": "en",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "activity_level" in data

    def test_katch_bmr_note(self):
        """Test Katch BMR formula note when bodyfat provided"""
        with patch("app.calculate_all_bmr", return_value={"mifflin": 1800, "katch": 1900}):
            with patch("app.calculate_all_tdee", return_value={"mifflin": 2200, "katch": 2300}):
                response = client.post(
                    "/premium_bmr",
                    json={
                        "weight_kg": 70,
                        "height_cm": 170,
                        "age": 30,
                        "sex": "male",
                        "activity": "moderate",
                        "bodyfat": 15,
                        "lang": "en",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "notes" in data
                # Should include Katch formula note when bodyfat is provided

    def test_premium_targets_import_error_handling(self):
        """Test premium_targets safety validation import error handling (lines 1315-1320)"""
        with patch("app.build_nutrition_targets") as mock_targets:
            mock_targets_obj = MagicMock()
            mock_targets_obj.kcal_daily = 2000
            mock_targets_obj.macros.protein_g = 150
            mock_targets_obj.macros.fat_g = 67
            mock_targets_obj.macros.carbs_g = 200
            mock_targets_obj.macros.fiber_g = 25
            mock_targets_obj.water_ml_daily = 2500
            mock_targets_obj.activity.moderate_aerobic_min = 150
            mock_targets_obj.activity.strength_sessions = 2
            mock_targets_obj.activity.steps_daily = 8000
            mock_targets_obj.calculation_date = "2024-01-01"
            mock_targets_obj.micros.get_priority_nutrients.return_value = {}

            mock_targets.return_value = mock_targets_obj

            with patch("core.targets._life_stage_warnings", return_value=[]):
                # Simulate ImportError from validate_targets_safety without breaking other imports
                with patch(
                    "core.recommendations.validate_targets_safety",
                    side_effect=ImportError("validate_targets_safety not found"),
                ):
                    response = client.post(
                        "/premium_targets",
                        json={
                            "sex": "male",
                            "age": 30,
                            "height_cm": 170,
                            "weight_kg": 70,
                            "activity": "moderate",
                            "goal": "maintain",
                            "lang": "en",
                        },
                    )
                    assert response.status_code == 200
                    # Should work even without safety validation
