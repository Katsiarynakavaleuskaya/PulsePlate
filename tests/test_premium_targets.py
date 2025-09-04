"""
Tests for Premium Targets API Endpoint

RU: Тесты для эндпоинта премиум целевых значений.
EN: Tests for premium targets API endpoint.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import app


class TestPremiumTargetsAPI:
    """Test Premium Targets API endpoint with specific micronutrients."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_premium_targets_contains_required_micronutrients(self):
        """Test that premium targets contain the required micronutrients: Fe, Ca, VitD, B12, I, Folate, K, Mg."""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain"
        }

        response = self.client.post("/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200

        result = response.json()
        assert "priority_micros" in result
        priority_micros = result["priority_micros"]

        # Check that all required micronutrients are present
        required_nutrients = {
            "iron_mg",      # Fe
            "calcium_mg",   # Ca
            "vitamin_d_iu", # VitD
            "b12_ug",       # B12
            "iodine_ug",    # I
            "folate_ug",    # Folate
            "potassium_mg", # K
            "magnesium_mg"  # Mg
        }

        # Check that all required nutrients are in the response
        for nutrient in required_nutrients:
            assert nutrient in priority_micros, f"Missing required nutrient: {nutrient}"
            assert priority_micros[nutrient] > 0, f"Nutrient {nutrient} should have a positive value"

    def test_premium_targets_values_in_reasonable_ranges(self):
        """Test that premium targets values are in reasonable ranges."""
        data = {
            "sex": "female",
            "age": 25,
            "height_cm": 165,
            "weight_kg": 60,
            "activity": "light",
            "goal": "maintain"
        }

        response = self.client.post("/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200

        result = response.json()
        assert result["kcal_daily"] >= 1200, "Calorie target should be at least 1200 kcal"
        assert result["kcal_daily"] <= 4000, "Calorie target should not exceed 4000 kcal"
        assert result["water_ml"] >= 1500, "Water target should be at least 1500 ml"
        assert result["water_ml"] <= 4000, "Water target should not exceed 4000 ml"

    def test_premium_targets_loss_goal_calorie_check(self):
        """Test that loss goal produces appropriate calorie target."""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "loss",
            "deficit_pct": 15
        }

        response = self.client.post("/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200

        result = response.json()
        assert result["kcal_daily"] >= 1200, "Calorie target for loss should be at least 1200 kcal"
        assert result["kcal_daily"] <= 4000, "Calorie target for loss should not exceed 4000 kcal"

if __name__ == "__main__":
    pytest.main([__file__])
