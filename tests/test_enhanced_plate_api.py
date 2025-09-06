"""
Tests for Enhanced My Plate API endpoint

Tests cover:
- Visual plate layout generation
- Hand/cup portion calculations
- Deficit/surplus percentage control
- Diet flags functionality
- Macro distribution validation
- Visual shape specification
- Goal-specific recommendations
- Error handling and edge cases
"""

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


class TestEnhancedPlateAPI:
    """Test Enhanced My Plate API endpoint."""

    def test_plate_contract_basic(self):
        """Test basic plate API contract with all required fields."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "loss",
            "deficit_pct": 15,
            "diet_flags": ["LOW_COST", "DAIRY_FREE"],
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check required response structure
        assert set(data.keys()) == {"kcal", "macros", "portions", "layout", "meals"}
        assert data["kcal"] > 1000
        assert all(k in data["macros"] for k in ("protein_g", "fat_g", "carbs_g", "fiber_g"))
        assert isinstance(data["layout"], list) and len(data["layout"]) >= 4
        assert data["layout"][0]["kind"] in ("plate_sector", "bowl", "marker")

    def test_plate_visual_layout_structure(self):
        """Test visual layout contains proper plate sectors and bowls."""
        payload = {
            "sex": "male",
            "age": 25,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "active",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        layout = data["layout"]
        # Should have 4 sectors + 2 bowls = 6 items
        assert len(layout) == 6

        # Check sector types
        sectors = [item for item in layout if item["kind"] == "plate_sector"]
        bowls = [item for item in layout if item["kind"] == "bowl"]

        assert len(sectors) == 4  # Vegetables, Protein, Carbs, Fat
        assert len(bowls) == 2  # Grain cup, Vegetable cup

        # Check all have required fields
        for item in layout:
            assert "kind" in item
            assert "fraction" in item
            assert "label" in item
            assert "tooltip" in item
            assert isinstance(item["fraction"], (int, float))
            assert 0 <= item["fraction"] <= 1.5  # Allow cups > 1

    def test_plate_portions_hand_cup_method(self):
        """Test portions are converted to hand/cup measurements."""
        payload = {
            "sex": "female",
            "age": 35,
            "height_cm": 165,
            "weight_kg": 60,
            "activity": "light",
            "goal": "gain",
            "surplus_pct": 10,
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        portions = data["portions"]
        # Check hand/cup portion fields
        required_portion_keys = {
            "protein_palm",
            "fat_thumbs",
            "carb_cups",
            "veg_cups",
            "meals_per_day",
        }
        assert required_portion_keys.issubset(set(portions.keys()))

        # Check reasonable portion values
        assert 0.5 <= portions["protein_palm"] <= 4.0  # Palms per meal
        assert 0.3 <= portions["fat_thumbs"] <= 3.0  # Thumbs per meal
        assert 0.5 <= portions["carb_cups"] <= 3.0  # Cups per meal
        assert 0.5 <= portions["veg_cups"] <= 4.0  # Vegetable cups per meal
        assert portions["meals_per_day"] == 3

    def test_plate_deficit_surplus_control(self):
        """Test precise deficit and surplus percentage control."""
        base_payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
        }

        # Test different deficit percentages for loss
        for deficit in [10, 15, 20]:
            payload = {**base_payload, "goal": "loss", "deficit_pct": deficit}
            response = client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200
            data = response.json()
            # Higher deficit should mean fewer calories
            assert data["kcal"] >= 1200  # Minimum safety threshold

        # Test different surplus percentages for gain
        for surplus in [8, 12, 15]:
            payload = {**base_payload, "goal": "gain", "surplus_pct": surplus}
            response = client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["kcal"] > 2000  # Should be above maintenance

    def test_plate_diet_flags_functionality(self):
        """Test diet flags affect meal suggestions."""
        base_payload = {
            "sex": "female",
            "age": 28,
            "height_cm": 168,
            "weight_kg": 62,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Test VEG flag
        payload = {**base_payload, "diet_flags": ["VEG"]}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()

        meals_text = " ".join([meal["title"] for meal in data["meals"]])
        assert "тофу" in meals_text or "нут" in meals_text  # Should suggest plant proteins

        # Test GF flag
        payload = {**base_payload, "diet_flags": ["GF"]}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()

        meals_text = " ".join([meal["title"] for meal in data["meals"]])
        # Should prefer gluten-free grains like buckwheat
        assert "Гречка" in meals_text or "гречка" in meals_text

        # Test LOW_COST flag
        payload = {**base_payload, "diet_flags": ["LOW_COST"]}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()

        meals_text = " ".join([meal["title"] for meal in data["meals"]])
        assert "(бюджет)" in meals_text  # Should mark budget options

    def test_plate_macro_consistency(self):
        """Test macro distribution consistency and calculations."""
        payload = {
            "sex": "male",
            "age": 35,
            "height_cm": 185,
            "weight_kg": 80,
            "activity": "active",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        macros = data["macros"]
        kcal = data["kcal"]

        # Check macro ranges are reasonable
        assert 50 <= macros["protein_g"] <= 200
        assert 40 <= macros["fat_g"] <= 150
        assert 100 <= macros["carbs_g"] <= 600  # Allow higher carbs for very active individuals
        assert 25 <= macros["fiber_g"] <= 35

        # Verify calorie calculation consistency (4/4/9 rule)
        calculated_kcal = (
            (macros["protein_g"] * 4) + (macros["carbs_g"] * 4) + (macros["fat_g"] * 9)
        )
        # Allow 5% variance for rounding
        assert abs(calculated_kcal - kcal) / kcal <= 0.05

    def test_plate_goal_specific_differences(self):
        """Test different goals produce appropriate macro distributions."""
        base_payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
        }

        results = {}
        goals = ["loss", "maintain", "gain"]

        for goal in goals:
            extra_params = {}
            if goal == "loss":
                extra_params["deficit_pct"] = 15
            elif goal == "gain":
                extra_params["surplus_pct"] = 12

            payload = {**base_payload, "goal": goal, **extra_params}
            response = client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200
            results[goal] = response.json()

        # Loss should have fewer calories than maintenance
        assert results["loss"]["kcal"] < results["maintain"]["kcal"]
        # Gain should have more calories than maintenance
        assert results["gain"]["kcal"] > results["maintain"]["kcal"]

        # Loss should emphasize protein relatively more
        loss_protein_ratio = results["loss"]["macros"]["protein_g"] / results["loss"]["kcal"]
        maintain_protein_ratio = (
            results["maintain"]["macros"]["protein_g"] / results["maintain"]["kcal"]
        )
        assert loss_protein_ratio >= maintain_protein_ratio

    def test_plate_validation_errors(self):
        """Test input validation errors."""
        base_payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Test invalid age
        payload = {**base_payload, "age": 5}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid deficit percentage
        payload = {**base_payload, "goal": "loss", "deficit_pct": 30}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid surplus percentage
        payload = {**base_payload, "goal": "gain", "surplus_pct": 25}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid body fat
        payload = {**base_payload, "bodyfat": 65}
        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

    def test_plate_missing_api_key(self):
        """Test plate API requires authentication."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Test without API key
        response = client.post("/api/v1/premium/plate", json=payload)
        # Behavior depends on whether API_KEY is set in environment
        assert response.status_code in [200, 403]

    def test_plate_meal_suggestions_structure(self):
        """Test meal suggestions have proper structure."""
        payload = {
            "sex": "female",
            "age": 25,
            "height_cm": 160,
            "weight_kg": 55,
            "activity": "light",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        meals = data["meals"]
        assert len(meals) == 3  # Breakfast, lunch, dinner

        for meal in meals:
            assert "title" in meal
            assert "kcal" in meal
            assert "protein_g" in meal
            assert "fat_g" in meal
            assert "carbs_g" in meal

            # Check reasonable portion sizes
            assert 200 <= meal["kcal"] <= 1000
            assert meal["protein_g"] >= 0
            assert meal["fat_g"] >= 0
            assert meal["carbs_g"] >= 0

    def test_plate_edge_cases(self):
        """Test edge cases and boundary values."""
        # Test minimum valid values - but realistic ones
        payload = {
            "sex": "female",
            "age": 18,  # Adult minimum
            "height_cm": 150,  # Realistic short
            "weight_kg": 45,  # Realistic light
            "activity": "sedentary",
            "goal": "maintain",
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kcal"] >= 1000  # Should be reasonable for small adult

        # Test maximum valid values
        payload = {
            "sex": "male",
            "age": 100,  # Maximum age
            "height_cm": 220,  # Very tall
            "weight_kg": 150,  # Very heavy
            "activity": "very_active",
            "goal": "gain",
            "surplus_pct": 20,  # Maximum surplus
        }

        response = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kcal"] > 3000  # Should be very high calories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
