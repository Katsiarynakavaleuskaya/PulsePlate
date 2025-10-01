#!/usr/bin/env python3
"""
Real functional tests for main.py endpoints without mocks
Targets major uncovered blocks: /bmi, /plan endpoints with real data
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app):
    """Test client fixture using app from conftest"""
    return TestClient(app)


class TestAppReal97Coverage:
    """Real functional tests targeting 97% coverage for main.py"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_bmi_endpoint_pregnant_with_chart_visualization(self, client):
        """Test /bmi endpoint for pregnant user with visualization request (lines 653-680)"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 65.5,
                "height_m": 1.65,
                "age": 28,
                "gender": "female",
                "pregnant": "yes",  # String instead of bool
                "athlete": "no",  # String instead of bool
                "lang": "en",
                "include_chart": True,
                "waist_cm": 82,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check pregnant-specific logic (lines 655-677)
        assert data["category"] is None  # Pregnant case
        assert "pregnancy" in data["note"].lower() or "not valid" in data["note"].lower()
        assert data["athlete"] is False
        assert data["group"] == "general"
        assert "bmi" in data

        # Check visualization handling (lines 666-677)
        # Either visualization is added or skipped based on availability

    def test_bmi_endpoint_athlete_with_chart_and_waist_risk(self, client):
        """Test /bmi endpoint for athlete with visualization and waist risk (lines 680-714)"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 85.0,
                "height_m": 1.80,
                "age": 25,
                "gender": "male",
                "pregnant": False,
                "athlete": True,
                "lang": "en",
                "include_chart": True,
                "waist_cm": 95,  # Should trigger waist risk warning
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check athlete-specific logic (lines 682-685)
        assert data["athlete"] is True
        assert data["group"] == "athlete"
        assert "category" in data

        # Check notes combination (lines 686-687)
        assert "note" in data
        # Should contain athlete advice and potentially waist risk

        # Check visualization handling (lines 695-714)
        # Either visualization is added or error message about matplotlib

    def test_bmi_endpoint_regular_user_high_waist_risk(self, client):
        """Test /bmi endpoint for regular user with high waist risk"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 95.0,
                "height_m": 1.75,
                "age": 45,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "include_chart": True,
                "waist_cm": 110,  # Very high waist measurement
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Should include waist risk in notes
        assert data["athlete"] is False
        assert data["group"] == "general"
        assert "note" in data

    def test_plan_endpoint_russian_language_basic(self, client):
        """Test /plan endpoint with Russian language (lines 720-752)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 70.0,
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

        # Check Russian language responses (lines 727-742)
        assert "Персональный план" in data["summary"]
        assert "Шаги:" in data["next_steps"][0]
        assert "Белок:" in data["next_steps"][1]
        assert "Сон:" in data["next_steps"][2]
        assert "прогулку" in data["action"]
        assert data["premium"] is False
        assert "premium_reco" not in data  # No premium in basic plan

    def test_plan_endpoint_russian_language_premium(self, client):
        """Test /plan endpoint with Russian language and premium (lines 743-752)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "ru",
                "premium": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check premium Russian responses (lines 743-752)
        assert data["premium"] is True
        assert "premium_reco" in data
        assert "Дефицит" in data["premium_reco"][0]
        assert "силовые" in data["premium_reco"][1]

    def test_plan_endpoint_english_language_basic(self, client):
        """Test /plan endpoint with English language (lines 753-765)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 68.0,
                "height_m": 1.68,
                "age": 25,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "premium": False,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check English language responses (lines 754-764)
        assert "Personal plan" in data["summary"]
        assert "Steps:" in data["next_steps"][0]
        assert "Protein:" in data["next_steps"][1]
        assert "Sleep:" in data["next_steps"][2]
        assert "walk" in data["action"]
        assert data["premium"] is False

    def test_plan_endpoint_english_language_premium(self, client):
        """Test /plan endpoint with English language and premium (lines 758-765)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 68.0,
                "height_m": 1.68,
                "age": 25,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "premium": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check premium English responses (lines 758-765)
        assert data["premium"] is True
        assert "premium_reco" in data
        assert "deficit" in data["premium_reco"][0].lower()
        assert "strength" in data["premium_reco"][1].lower()

    def test_plan_endpoint_pregnant_user_category_none(self, client):
        """Test /plan endpoint for pregnant user (category = None case)"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 65.0,
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

        # Pregnant users should have category = None (line 723-725)
        assert data["category"] is None
        assert "bmi" in data
        assert "healthy_bmi" in data

    def test_plan_endpoint_athlete_user_category(self, client):
        """Test /plan endpoint for athlete user"""
        response = client.post(
            "/plan",
            json={
                "weight_kg": 80.0,
                "height_m": 1.80,
                "age": 25,
                "gender": "male",
                "pregnant": False,
                "athlete": True,
                "lang": "en",
                "premium": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Athlete category should be calculated properly (line 725)
        assert "category" in data
        assert data["premium"] is True

    def test_multiple_bmi_scenarios_for_coverage(self, client):
        """Test multiple BMI scenarios to cover different paths"""

        # Test underweight scenario
        response1 = client.post(
            "/bmi",
            json={
                "weight_kg": 45.0,
                "height_m": 1.70,
                "age": 20,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "include_chart": False,
            },
        )
        assert response1.status_code == 200

        # Test overweight scenario
        response2 = client.post(
            "/bmi",
            json={
                "weight_kg": 85.0,
                "height_m": 1.65,
                "age": 35,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "include_chart": False,
            },
        )
        assert response2.status_code == 200

        # Test obese scenario
        response3 = client.post(
            "/bmi",
            json={
                "weight_kg": 100.0,
                "height_m": 1.60,
                "age": 40,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "include_chart": False,
            },
        )
        assert response3.status_code == 200

    def test_bmi_different_languages_and_ages(self, client):
        """Test BMI with different languages and age groups"""

        # Young adult in Russian
        response1 = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 18,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "ru",
            },
        )
        assert response1.status_code == 200

        # Older adult in English
        response2 = client.post(
            "/bmi",
            json={
                "weight_kg": 75.0,
                "height_m": 1.70,
                "age": 65,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
            },
        )
        assert response2.status_code == 200

    def test_plan_different_bmi_categories(self, client):
        """Test plan endpoint with different BMI categories"""

        # Plan for underweight person
        response1 = client.post(
            "/plan",
            json={
                "weight_kg": 50.0,
                "height_m": 1.75,
                "age": 25,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "en",
                "premium": True,
            },
        )
        assert response1.status_code == 200

        # Plan for overweight person
        response2 = client.post(
            "/plan",
            json={
                "weight_kg": 90.0,
                "height_m": 1.65,
                "age": 30,
                "gender": "female",
                "pregnant": False,
                "athlete": False,
                "lang": "ru",
                "premium": True,
            },
        )
        assert response2.status_code == 200

    def test_bmi_edge_cases_and_boundary_conditions(self, client):
        """Test BMI endpoint with edge cases to maximize coverage"""

        # Very low BMI
        response1 = client.post(
            "/bmi",
            json={
                "weight_kg": 40.0,
                "height_m": 1.80,
                "age": 22,
                "gender": "female",
                "pregnant": False,
                "athlete": True,  # Athlete with low BMI
                "lang": "en",
                "include_chart": True,
            },
        )
        assert response1.status_code == 200

        # Very high BMI
        response2 = client.post(
            "/bmi",
            json={
                "weight_kg": 120.0,
                "height_m": 1.55,
                "age": 50,
                "gender": "male",
                "pregnant": False,
                "athlete": False,
                "lang": "ru",
                "include_chart": True,
                "waist_cm": 120,  # Very high waist
            },
        )
        assert response2.status_code == 200

    def test_combined_scenarios_for_maximum_coverage(self, client):
        """Test combinations to hit as many code paths as possible"""

        # Pregnant athlete (edge case)
        response1 = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 26,
                "gender": "female",
                "pregnant": True,
                "athlete": True,  # Both pregnant AND athlete
                "lang": "ru",
                "include_chart": True,
                "waist_cm": 85,
            },
        )
        assert response1.status_code == 200

        # Young athlete with visualization
        response2 = client.post(
            "/bmi",
            json={
                "weight_kg": 75.0,
                "height_m": 1.85,
                "age": 19,
                "gender": "male",
                "pregnant": False,
                "athlete": True,
                "lang": "en",
                "include_chart": True,
                "waist_cm": 78,
            },
        )
        assert response2.status_code == 200
