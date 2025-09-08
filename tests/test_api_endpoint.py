"""
Test script for the premium week plan API endpoint.

This script tests the /api/v1/premium/plan/week endpoint with different languages.
"""

import os

from fastapi.testclient import TestClient

import app as app_module


def test_api_endpoint_multilingual():
    """Test the API endpoint with different languages."""
    # Set up test client
    client = TestClient(app_module.app)

    # Mock API key
    api_key = "test_api_key"
    os.environ["API_KEY"] = api_key

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
        assert response.status_code == 200, f"Failed for language {lang}"

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
            assert "total_kcal" in day
            assert "daily_cost" in day
            assert "date" in day

            # Check that meals have the expected structure
            for meal in day["meals"]:
                assert "carbs_g" in meal
                assert "fat_g" in meal
                assert "ingredients" in meal
                assert "detailed_nutrients" in meal

        # Check that week summary exists
        assert "week_summary" in result

        print(f"✓ Language {lang} test passed")


def test_api_endpoint_with_targets():
    """Test the API endpoint with pre-calculated targets."""
    # Set up test client
    client = TestClient(app_module.app)

    # Mock API key
    api_key = "test_api_key"
    os.environ["API_KEY"] = api_key

    # Test data with pre-calculated targets
    test_data = {
        "targets": {
            "kcal": 2000,
            "protein": 100,
            "carbs": 250,
            "fat": 70,
            "fiber": 30,
            "iron": 18.0,
            "calcium": 1000.0,
            "vitamin_d": 600.0,
            "vitamin_b12": 2.4,
            "folate": 400.0,
            "iodine": 150.0,
            "potassium": 3500.0,
            "magnesium": 400.0,
        },
        "sex": "female",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "es",
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
