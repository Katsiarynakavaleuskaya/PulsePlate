"""
Tests for Week Plan API

RU: Тесты для API недельного плана.
EN: Tests for the weekly plan API.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app import app

# Set up test client
client = TestClient(app)

def test_week_plan_with_targets():
    """Test generating a week plan with pre-calculated targets."""
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
        "lang": "en"
    }

    # Make request to the API
    response = client.post("/api/v1/premium/plan/week", json=test_data)

    # Check that the response is successful
    assert response.status_code == 200

    # Check that the response has the expected structure
    data = response.json()
    assert "days" in data
    assert "weekly_coverage" in data
    assert "shopping_list" in data

    # Check that we have 7 days
    assert isinstance(data["days"], list)
    assert len(data["days"]) == 7

    # Check that weekly_coverage has all required keys
    micro_keys = ["Fe_mg", "Ca_mg", "VitD_IU", "B12_ug", "Folate_ug", "Iodine_ug", "K_mg", "Mg_mg"]
    for key in micro_keys:
        assert key in data["weekly_coverage"]

    # Check that shopping_list is not empty
    assert isinstance(data["shopping_list"], list)
    assert len(data["shopping_list"]) > 0

def test_week_plan_with_profile():
    """Test generating a week plan with user profile."""
    # Test data with user profile
    test_data = {
        "sex": "female",
        "age": 30,
        "height_cm": 165,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en"
    }

    # Make request to the API
    response = client.post("/api/v1/premium/plan/week", json=test_data)

    # Check that the response is successful
    assert response.status_code == 200

    # Check that the response has the expected structure
    data = response.json()
    assert "days" in data
    assert "weekly_coverage" in data
    assert "shopping_list" in data

def test_week_plan_multilingual():
    """Test that the API works with different languages."""
    # Test data with pre-calculated targets
    targets_data = {
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
    }

    # Test with different languages
    for lang in ["en", "ru", "es"]:
        test_data = targets_data.copy()
        test_data["lang"] = lang

        # Make request to the API
        response = client.post("/api/v1/premium/plan/week", json=test_data)

        # Check that the response is successful
        assert response.status_code == 200

        # Check structure
        data = response.json()
        assert "days" in data
        assert "weekly_coverage" in data
        assert "shopping_list" in data

def test_week_plan_missing_data():
    """Test that the API handles missing data correctly."""
    # Test data with missing required fields
    test_data = {
        "diet_flags": [],
        "lang": "en"
    }

    # Make request to the API
    response = client.post("/api/v1/premium/plan/week", json=test_data)

    # Should fail with 400 Bad Request
    assert response.status_code == 422  # FastAPI validation error

if __name__ == "__main__":
    pytest.main([__file__])
