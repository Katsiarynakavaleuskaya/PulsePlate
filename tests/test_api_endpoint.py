"""
Test the API endpoint for weekly meal planning.
"""

import os
from fastapi.testclient import TestClient

import app


def test_api_endpoint_multilingual() -> None:
    """Test the API endpoint with different languages."""
    # Set up test client
    client = TestClient(app.app)  # type: ignore[arg-type]

    # Mock API key with proper cleanup
    api_key = "test_api_key"
    prev_api_key = os.environ.get("API_KEY")
    os.environ["API_KEY"] = api_key

    try:
        # Test data with user profile
        test_data = {
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",  # Will change this for each test
        }

        # Test with different languages
        for lang in ["en", "ru", "es"]:
            print(f"\nTesting with language: {lang}")
            test_data["lang"] = lang

            # Make request to the API
            response = client.post(
                "/api/v1/premium/plan/week", json=test_data, headers={"X-API-Key": api_key}
            )

            # Check that the response is successful
            assert (
                response.status_code == 200
            ), f"Failed for language {lang}\nResponse body: {response.json()}"

            # Parse the response
            result = response.json()

            # Check that we have the expected structure
            assert "daily_menus" in result
            assert "week_summary" in result

            # Check that we have 7 days
            assert len(result["daily_menus"]) == 7

            # Check that each day has the expected structure
            for day in result["daily_menus"]:
                assert "meals" in day
                assert "kcal" in day
                assert "total_cost" in day
                assert "macros" in day

                # Check that meals have the expected structure
                for meal in day["meals"]:
                    assert "macros" in meal
                    assert "kcal" in meal
                    assert "grams" in meal

            print(f"✓ Language {lang} test passed")

    finally:
        # Restore previous API key or remove it
        if prev_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = prev_api_key


def test_api_endpoint_with_targets() -> None:
    """Test the API endpoint with pre-calculated targets."""
    # Set up test client
    client = TestClient(app.app)  # type: ignore[arg-type]

    # Mock API key with proper cleanup
    api_key = "test_api_key"
    prev_api_key = os.environ.get("API_KEY")
    os.environ["API_KEY"] = api_key

    try:
        # Test data with pre-calculated targets
        test_data = {
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "moderate",
            "goal": "maintain",
            "targets": {
                "kcal": 2000,
                "protein_g": 150,
                "carbs_g": 250,
                "fat_g": 67,
                "fiber_g": 25,
                "sodium_mg": 2300,
                "calcium_mg": 1000,
                "iron_mg": 18,
                "potassium_mg": 3500,
            },
            "diet_flags": [],
            "lang": "en",
        }

        # Make request to the API
        response = client.post(
            "/api/v1/premium/plan/week", json=test_data, headers={"X-API-Key": api_key}
        )

        # Check that the response is successful
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200, "Failed with pre-calculated targets"

        # Parse the response
        result = response.json()

        # Check that we have the expected structure
        assert "daily_menus" in result
        assert "week_summary" in result

        print("✓ Pre-calculated targets test passed")

    finally:
        # Restore previous API key or remove it
        if prev_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = prev_api_key
