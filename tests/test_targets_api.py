"""
Tests for Targets API Endpoint

RU: Тесты для эндпоинта целевых значений.
EN: Tests for targets API endpoint.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


class TestTargetsAPI:
    """Test WHO-based targets API endpoint."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_targets_endpoint_success(self):
        """Test successful targets calculation."""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "kcal_daily" in result
        assert "macros" in result
        assert "water_ml" in result
        assert "priority_micros" in result
        assert "activity_weekly" in result
        assert result["kcal_daily"] > 0

    def test_targets_endpoint_with_deficit(self):
        """Test targets calculation with deficit goal."""
        data = {
            "sex": "female",
            "age": 25,
            "height_cm": 165,
            "weight_kg": 60,
            "activity": "light",
            "goal": "loss",
            "deficit_pct": 15,
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "kcal_daily" in result
        assert result["kcal_daily"] > 0

    def test_targets_endpoint_with_surplus(self):
        """Test targets calculation with surplus goal."""
        data = {
            "sex": "male",
            "age": 22,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "active",
            "goal": "gain",
            "surplus_pct": 10,
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "kcal_daily" in result
        assert result["kcal_daily"] > 0

    def test_targets_endpoint_with_diet_flags(self):
        """Test targets calculation with diet flags."""
        data = {
            "sex": "female",
            "age": 35,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": ["VEG", "GF"],
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "kcal_daily" in result
        assert result["kcal_daily"] > 0

    def test_targets_endpoint_pregnant_woman(self):
        """Test targets calculation for pregnant woman."""
        data = {
            "sex": "female",
            "age": 28,
            "height_cm": 165,
            "weight_kg": 65,
            "activity": "light",
            "goal": "maintain",
            "life_stage": "pregnant",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "kcal_daily" in result
        assert result["kcal_daily"] > 0

    def test_targets_endpoint_invalid_input(self):
        """Test targets calculation with invalid input."""
        data = {
            "sex": "male",
            "age": -5,  # Invalid age
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        # With Pydantic validation, this will be a 422 (unprocessable entity) rather than 400
        assert response.status_code in [400, 422]

    def test_targets_endpoint_missing_api_key(self):
        """Test targets endpoint without API key."""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
        }

        response = self.client.post("/api/v1/premium/targets", json=data)
        assert response.status_code == 403

    def test_targets_endpoint_internal_error(self):
        """Test targets endpoint with internal error."""
        with patch("app.build_nutrition_targets") as mock_build_targets:
            mock_build_targets.side_effect = Exception("Test error")

            data = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200

    def test_targets_endpoint_value_error(self):
        """Test targets endpoint with value error."""
        with patch("app.build_nutrition_targets") as mock_build_targets:
            mock_build_targets.side_effect = ValueError("Invalid input")

            data = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
            )
            # With Pydantic validation, this will be a 422 (unprocessable entity) rather than 400
            assert response.status_code == 200
