"""
Tests for the premium week plan API endpoint.
"""

import importlib.util
import os

import pytest
from fastapi.testclient import TestClient

# Import the app correctly from app.py
spec = importlib.util.spec_from_file_location("app", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
client = TestClient(app_module.app)

class TestPremiumWeekAPI:
    """Test the premium week plan API endpoint."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_premium_week_endpoint_multilingual(self):
        """Test the premium week endpoint with different languages."""
        # Test data with user profile
        test_data = {
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en"  # Will change this for each test
        }

        # Test with different languages
        for lang in ["en", "ru", "es"]:
            test_data["lang"] = lang

            # Make request to the API
            response = client.post(
                "/api/v1/premium/plan/week",
                json=test_data,
                headers={"X-API-Key": "test_key"}
            )

            # Check that the response is successful
            assert response.status_code == 200, f"Failed for language {lang}"

            # Parse the response
            result = response.json()

            # Check that we have the expected structure
            assert "days" in result
            assert "weekly_coverage" in result
            assert "shopping_list" in result

            # Check that we have 7 days
            assert len(result["days"]) == 7

            # Check that each day has the expected structure
            for day in result["days"]:
                assert "meals" in day
                assert "kcal" in day
                assert "macros" in day
                assert "micros" in day
                assert "coverage" in day
                assert "tips" in day

                # Check that meals have translated titles
                for meal in day["meals"]:
                    assert "title" in meal
                    assert "title_translated" in meal

            # Check that shopping list has translated names
            for item in result["shopping_list"]:
                assert "name" in item
                assert "name_translated" in item
                assert "grams" in item
                assert "price_est" in item

    def test_premium_week_endpoint_with_targets(self):
        """Test the premium week endpoint with pre-calculated targets."""
        # Test data with pre-calculated targets
        test_data = {
            "targets": {
                "kcal": 2000,
                "macros": {
                    "protein_g": 100,
                    "fat_g": 70,
                    "carbs_g": 250,
                    "fiber_g": 30
                },
                "micro": {
                    "Fe_mg": 18.0,
                    "Ca_mg": 1000.0,
                    "VitD_IU": 600.0,
                    "B12_ug": 2.4,
                    "Folate_ug": 400.0,
                    "Iodine_ug": 150.0,
                    "K_mg": 3500.0,
                    "Mg_mg": 400.0
                }
            },
            "diet_flags": [],
            "lang": "es"
        }

        # Make request to the API
        response = client.post(
            "/api/v1/premium/plan/week",
            json=test_data,
            headers={"X-API-Key": "test_key"}
        )

        # Check that the response is successful
        assert response.status_code == 200

        # Parse the response
        result = response.json()

        # Check that we have the expected structure
        assert "days" in result
        assert "weekly_coverage" in result
        assert "shopping_list" in result

if __name__ == "__main__":
    pytest.main([__file__])
