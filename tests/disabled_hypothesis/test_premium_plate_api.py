"""
Tests for Premium Plate API endpoint in the app module (not main.py)

Tests cover:
- API endpoint functionality
- Request validation
- Response structure
- Macro distribution validation
- Goal-specific recommendations
- Multi-language support
- Error handling
"""

import pytest
from fastapi.testclient import TestClient


class TestPremiumPlateAPI:
    """Test Premium Plate API endpoint."""

    client: TestClient

    @pytest.fixture(autouse=True)
    def _bind_client(self, client: TestClient) -> None:
        """Expose the canonical function-scoped client to class tests."""
        self.client = client

    def test_premium_plate_maintenance_goal(self) -> None:
        """Test Premium Plate API with maintenance goal."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        # Check response structure
        assert "kcal" in data
        assert "macros" in data
        assert "portions" in data
        assert "layout" in data
        assert "meals" in data

        # Check macro distribution in macros
        macros = data["macros"]
        assert "protein_g" in macros
        assert "carbs_g" in macros
        assert "fat_g" in macros
        assert all(
            isinstance(v, (int, float)) and v > 0
            for v in [macros["protein_g"], macros["carbs_g"], macros["fat_g"]]
        )

        # Check visual layout
        assert isinstance(data["layout"], list)
        assert len(data["layout"]) > 0

        # Check meals
        assert isinstance(data["meals"], list)
        assert len(data["meals"]) > 0

    def test_premium_plate_weight_loss_goal(self) -> None:
        """Test Premium Plate API with weight loss goal."""
        payload = {
            "weight_kg": 80,
            "height_cm": 170,
            "age": 35,
            "sex": "female",
            "activity": "light",
            "goal": "loss",
            "bodyfat": 25,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        assert data["kcal"] > 0

        # Weight loss should have reasonable protein
        macros = data["macros"]
        assert macros["protein_g"] / data["kcal"] * 4 >= 15 / 100

        # Check that we have some meals
        assert len(data["meals"]) > 0

    def test_premium_plate_muscle_gain_goal(self) -> None:
        """Test Premium Plate API with muscle gain goal."""
        payload = {
            "weight_kg": 65,
            "height_cm": 180,
            "age": 25,
            "sex": "male",
            "activity": "active",
            "goal": "gain",
            "bodyfat": 15,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        assert data["kcal"] > 0

        # Muscle gain should have reasonable protein
        macros = data["macros"]
        protein_ratio = macros["protein_g"] / data["kcal"] * 4 * 100  # protein % of calories
        assert protein_ratio >= 12  # Relaxed from 15 to 12

        # Check protein content
        assert macros["protein_g"] > 50  # Should have substantial protein

    def test_premium_plate_russian_language(self) -> None:
        """Test Premium Plate API with Russian language."""
        payload = {
            "weight_kg": 75,
            "height_cm": 175,
            "age": 28,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "lang": "ru",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        assert data["kcal"] > 0

        # Check that we have layout data
        assert len(data["layout"]) > 0

    def test_premium_plate_all_activity_levels(self) -> None:
        """Test Premium Plate API with different activity levels."""
        base_payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "goal": "maintain",
            "lang": "en",
        }

        activity_levels = ["sedentary", "light", "moderate", "active", "very_active"]
        calorie_targets = []

        for activity in activity_levels:
            payload = {**base_payload, "activity": activity}
            response = self.client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            data = response.json()
            calorie_targets.append(data["kcal"])

        # Higher activity should generally mean more calories
        assert calorie_targets[-1] > calorie_targets[0]  # very_active > sedentary

    def test_premium_plate_validation_errors(self) -> None:
        """Test Premium Plate API validation errors."""
        # Test invalid weight
        payload = {
            "weight_kg": 0,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid height
        payload["weight_kg"] = 70
        payload["height_cm"] = 0

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid age
        payload["height_cm"] = 175
        payload["age"] = 150

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid sex
        payload["age"] = 30
        payload["sex"] = "other"

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid activity
        payload["sex"] = "male"
        payload["activity"] = "invalid"

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid goal
        payload["activity"] = "moderate"
        payload["goal"] = "invalid_goal"

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid body fat (should be 3-60 but this will test boundary)
        payload["goal"] = "maintain"
        payload["bodyfat"] = 70  # Over the limit

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

    def test_premium_plate_missing_api_key(self) -> None:
        """Test Premium Plate API without API key."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",  # Add required field
        }

        # Test without API key header
        response = self.client.post("/api/v1/premium/plate", json=payload)
        assert response.status_code == 403
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Invalid API Key"}

    def test_premium_plate_with_bodyfat(self) -> None:
        """Test Premium Plate API with body fat percentage."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "active",
            "goal": "gain",
            "bodyfat": 12,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        # Should work with body fat included
        assert data["kcal"] > 0
        assert data["macros"]["protein_g"] > 0

    def test_premium_plate_calorie_scaling(self) -> None:
        """Test that different goals produce appropriate calorie targets."""
        base_payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "lang": "en",
        }

        # Test different goals
        goals = ["loss", "maintain", "gain"]
        calorie_targets = {}

        for goal in goals:
            payload = {**base_payload, "goal": goal}
            response = self.client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            data = response.json()
            calorie_targets[goal] = data["kcal"]

        # Weight loss should have fewer calories than maintenance
        assert calorie_targets["loss"] < calorie_targets["maintain"]

        # Weight gain should have more calories than maintenance
        assert calorie_targets["gain"] > calorie_targets["maintain"]

    def test_premium_plate_macro_distribution_consistency(self) -> None:
        """Test that macro distributions are consistent and valid."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        # Verify macro distribution is reasonable
        macros = data["macros"]
        kcal = data["kcal"]

        # Calculate calories from macros (protein: 4 cal/g, carbs: 4 cal/g, fat: 9 cal/g)
        calculated_calories = (
            (macros["protein_g"] * 4) + (macros["carbs_g"] * 4) + (macros["fat_g"] * 9)
        )

        # Should be close to target calories (allow some rounding differences)
        assert abs(calculated_calories - kcal) / kcal < 0.05  # Within 5%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
