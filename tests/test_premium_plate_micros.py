# -*- coding: utf-8 -*-
"""
RU: Тест агрегации микронутриентов в /api/v1/premium/plate.
EN: Test micronutrient aggregation in /api/v1/premium/plate.
"""
import pytest
from fastapi.testclient import TestClient

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(app_mod.app)  # type: ignore


def test_plate_endpoint_has_day_micros():
    """Test that plate endpoint returns day_micros field."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "day_micros" in data
    assert isinstance(data["day_micros"], dict)


def test_day_micros_aggregation():
    """Test that day_micros aggregates micronutrients from all meals."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    day_micros = data["day_micros"]

    # Check that we have expected micronutrients
    expected_micros = [
        "iron_mg",
        "calcium_mg",
        "magnesium_mg",
        "potassium_mg",
        "vitamin_c_mg",
        "folate_ug",
        "vitamin_d_iu",
        "b12_ug",
    ]

    for nutrient in expected_micros:
        assert nutrient in day_micros
        assert isinstance(day_micros[nutrient], (int, float))
        assert day_micros[nutrient] > 0


def test_meals_contain_micros():
    """Test that individual meals contain micros field."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    meals = data["meals"]

    assert len(meals) > 0

    for meal in meals:
        assert "micros" in meal
        assert isinstance(meal["micros"], dict)

        # Check that each meal has the expected micronutrients
        expected_micros = [
            "iron_mg",
            "calcium_mg",
            "magnesium_mg",
            "potassium_mg",
            "vitamin_c_mg",
            "folate_ug",
            "vitamin_d_iu",
            "b12_ug",
        ]

        for nutrient in expected_micros:
            assert nutrient in meal["micros"]
            assert isinstance(meal["micros"][nutrient], (int, float))


def test_day_micros_calculation():
    """Test that day_micros values are correctly calculated from meals."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    meals = data["meals"]
    day_micros = data["day_micros"]

    # Calculate expected totals from meals
    expected_totals = {}
    for meal in meals:
        for nutrient, amount in meal["micros"].items():
            expected_totals[nutrient] = expected_totals.get(nutrient, 0) + amount

    # Compare with actual day_micros
    for nutrient, expected_total in expected_totals.items():
        assert nutrient in day_micros
        # Allow small floating point differences
        assert abs(day_micros[nutrient] - expected_total) < 0.01


def test_plate_endpoint_with_different_goals():
    """Test that day_micros works with different goals."""
    test_cases = [
        {"goal": "loss", "deficit_pct": 15},
        {"goal": "gain", "surplus_pct": 10},
        {"goal": "maintain"},
    ]

    for case in test_cases:
        payload = {
            "sex": "male",
            "age": 25,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "active",
            **case,
        }

        resp = client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "day_micros" in data
        assert isinstance(data["day_micros"], dict)
        assert len(data["day_micros"]) > 0
