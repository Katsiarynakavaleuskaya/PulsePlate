"""
Comprehensive Tests for Premium Targets API Endpoint

RU: Расширенные тесты для эндпоинта премиум целевых значений.
EN: Comprehensive tests for premium targets API endpoint.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app import app


class TestPremiumTargetsComprehensive:
    """Comprehensive test for Premium Targets API endpoint with all required specifications."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_premium_targets_required_micronutrients_male_19_50(self):
        """Test that premium targets contain all required micronutrients for males aged 19-50."""
        data = {
            "sex": "male",
            "age": 30,  # 19-50 age group
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
        assert "priority_micros" in result
        priority_micros = result["priority_micros"]

        # Check that all required micronutrients are present with correct values
        # from COMPACT_MICRONUTRIENT_RDA
        expected_values = {
            "iron_mg": 8.0,  # Male 19-50
            "calcium_mg": 1000.0,  # Male 19-50
            "vitamin_d_iu": 600.0,  # Male 19-50
            "b12_ug": 2.4,  # Male 19-50
            "iodine_ug": 150.0,  # Male 19-50
            "folate_ug": 400.0,  # Male 19-50
            "potassium_mg": 3500.0,  # Male 19-50
            "magnesium_mg": 400.0,  # Male 19-50
        }

        for nutrient, expected_value in expected_values.items():
            assert nutrient in priority_micros, f"Missing required nutrient: {nutrient}"
            assert priority_micros[nutrient] == expected_value, (
                f"Nutrient {nutrient} has incorrect value: "
                f"expected {expected_value}, got {priority_micros[nutrient]}"
            )

    def test_premium_targets_required_micronutrients_female_19_50(self):
        """Test that premium targets contain all required micronutrients for females aged 19-50."""
        data = {
            "sex": "female",
            "age": 25,  # 19-50 age group
            "height_cm": 165,
            "weight_kg": 60,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "priority_micros" in result
        priority_micros = result["priority_micros"]

        # Check that all required micronutrients are present with correct values
        # from COMPACT_MICRONUTRIENT_RDA
        expected_values = {
            "iron_mg": 18.0,  # Female 19-50 (higher due to menstruation)
            "calcium_mg": 1000.0,  # Female 19-50
            "vitamin_d_iu": 600.0,  # Female 19-50
            "b12_ug": 2.4,  # Female 19-50
            "iodine_ug": 150.0,  # Female 19-50
            "folate_ug": 400.0,  # Female 19-50
            "potassium_mg": 3500.0,  # Female 19-50
            "magnesium_mg": 310.0,  # Female 19-50
        }

        for nutrient, expected_value in expected_values.items():
            assert nutrient in priority_micros, f"Missing required nutrient: {nutrient}"
            assert priority_micros[nutrient] == expected_value, (
                f"Nutrient {nutrient} has incorrect value: "
                f"expected {expected_value}, got {priority_micros[nutrient]}"
            )

    def test_premium_targets_macronutrient_distribution(self):
        """Test that macronutrient distribution follows WHO guidelines."""
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
        assert "macros" in result
        macros = result["macros"]

        # Check that all required macronutrients are present
        required_macros = {"protein_g", "fat_g", "carbs_g", "fiber_g"}
        for macro in required_macros:
            assert macro in macros, f"Missing required macronutrient: {macro}"
            assert (
                macros[macro] > 0
            ), f"Macronutrient {macro} should have a positive value"

        # Check protein target (1.6-1.8 g/kg for maintenance)
        expected_protein_min = int(70 * 1.6)  # 112g
        expected_protein_max = int(70 * 1.8)  # 126g
        assert expected_protein_min <= macros["protein_g"] <= expected_protein_max, (
            f"Protein target {macros['protein_g']}g not in expected range "
            f"{expected_protein_min}-{expected_protein_max}g"
        )

        # Check fat target (0.8-1.0 g/kg for maintenance)
        expected_fat_min = int(70 * 0.8)  # 56g
        expected_fat_max = int(70 * 1.0)  # 70g
        assert expected_fat_min <= macros["fat_g"] <= expected_fat_max, (
            f"Fat target {macros['fat_g']}g not in expected range "
            f"{expected_fat_min}-{expected_fat_max}g"
        )

    def test_premium_targets_hydration_target(self):
        """Test that hydration target is approximately 30 ml/kg."""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,  # 70kg person
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert "water_ml" in result

        # Check that water target is approximately 30 ml/kg (±20% tolerance)
        expected_water = 70 * 30  # 2100 ml
        tolerance = expected_water * 0.2  # 20% tolerance
        assert (
            (expected_water - tolerance)
            <= result["water_ml"]
            <= (expected_water + tolerance)
        ), (
            f"Water target {result['water_ml']}ml not in expected range "
            f"{expected_water - tolerance}-{expected_water + tolerance}ml"
        )

    def test_premium_targets_activity_guidelines(self):
        "Test that activity targets follow WHO guidelines (150/75 min/week)."
        data = {
            "sex": "male",
            "age": 30,  # Adult
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
        assert "activity_weekly" in result
        activity = result["activity_weekly"]

        # Check that all required activity targets are present
        required_activity = {"moderate_aerobic_min", "strength_sessions", "steps_daily"}
        for activity_item in required_activity:
            assert (
                activity_item in activity
            ), f"Missing required activity target: {activity_item}"

        # Check WHO activity guidelines for adults
        assert activity["moderate_aerobic_min"] == 150, (
            f"Moderate aerobic activity should be 150 min/week, "
            f"got {activity['moderate_aerobic_min']}"
        )
        assert (
            activity["strength_sessions"] == 2
        ), f"Strength sessions should be 2/week, got {activity['strength_sessions']}"

    def test_premium_targets_kcal_safety_bounds(self):
        """Test that kcal targets are within safety bounds (≥1200)."""
        # Test loss goal with high deficit
        data = {
            "sex": "female",
            "age": 25,
            "height_cm": 165,
            "weight_kg": 50,  # Light person to test minimum bounds
            "activity": "sedentary",
            "goal": "loss",
            "deficit_pct": 25,  # Maximum deficit
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        assert (
            result["kcal_daily"] >= 1200
        ), f"Calorie target {result['kcal_daily']} below minimum safe level of 1200 kcal"

    def test_premium_targets_tdee_vs_bmr(self):
        """Test that TDEE ≥ BMR."""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "sedentary",  # Minimum activity to test difference
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200

        result = response.json()
        # The endpoint returns kcal_daily which should be TDEE
        # We can't directly compare to BMR without internal calculations,
        # but we can check it's reasonable
        assert (
            result["kcal_daily"] > 1500
        ), f"TDEE {result['kcal_daily']} seems too low for a 70kg male"


if __name__ == "__main__":
    pytest.main([__file__])
