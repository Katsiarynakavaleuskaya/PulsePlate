# -*- coding: utf-8 -*-
"""
RU: Тест агрегации микронутриентов в /api/v1/premium/plate.
EN: Test micronutrient aggregation in /api/v1/premium/plate.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.services import pro_nutrition_plate
from tests._client import open_test_client

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)


_TEST_MICROS: dict[str, float] = {
    "iron_mg": 3.0,
    "calcium_mg": 120.0,
    "magnesium_mg": 40.0,
    "potassium_mg": 350.0,
    "vitamin_c_mg": 12.0,
    "folate_ug": 55.0,
    "vitamin_d_iu": 80.0,
    "b12_ug": 0.8,
}


async def _deterministic_day_micros(
    meals: list[dict[str, object]],
) -> dict[str, float]:
    """Attach deterministic per-meal micros and return their exact sum."""
    totals = {nutrient: 0.0 for nutrient in _TEST_MICROS}

    for meal_index, meal in enumerate(meals, start=1):
        meal_micros = {nutrient: amount * meal_index for nutrient, amount in _TEST_MICROS.items()}
        meal["micros"] = meal_micros

        for nutrient, amount in meal_micros.items():
            totals[nutrient] += amount

    return totals


@pytest.fixture
def premium_plate_micros_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Open one managed client with deterministic micronutrient evidence."""
    monkeypatch.setattr(
        pro_nutrition_plate,
        "_aggregate_day_micronutrients",
        _deterministic_day_micros,
    )

    with open_test_client(app_mod.app) as managed_client:
        yield managed_client


def _assert_deterministic_micros(data: dict[str, object]) -> None:
    """Prove each meal and the day total use the deterministic aggregation seam."""
    meals = data["meals"]
    day_micros = data["day_micros"]

    assert isinstance(meals, list)
    assert meals
    assert isinstance(day_micros, dict)

    expected_totals = {nutrient: 0.0 for nutrient in _TEST_MICROS}

    for meal_index, meal in enumerate(meals, start=1):
        assert isinstance(meal, dict)
        expected_meal = {nutrient: amount * meal_index for nutrient, amount in _TEST_MICROS.items()}
        assert meal["micros"] == pytest.approx(expected_meal)

        for nutrient, amount in expected_meal.items():
            expected_totals[nutrient] += amount

    assert day_micros == pytest.approx(expected_totals)


def test_plate_endpoint_has_day_micros(premium_plate_micros_client: TestClient):
    """Test that plate endpoint returns day_micros field."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = premium_plate_micros_client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "day_micros" in data
    assert isinstance(data["day_micros"], dict)
    _assert_deterministic_micros(data)


def test_day_micros_aggregation(premium_plate_micros_client: TestClient):
    """Test that day_micros aggregates micronutrients from all meals."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = premium_plate_micros_client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    _assert_deterministic_micros(data)
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


def test_meals_contain_micros(premium_plate_micros_client: TestClient):
    """Test that individual meals contain micros field."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = premium_plate_micros_client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    _assert_deterministic_micros(data)
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


def test_day_micros_calculation(premium_plate_micros_client: TestClient):
    """Test that day_micros values are correctly calculated from meals."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    resp = premium_plate_micros_client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()
    _assert_deterministic_micros(data)
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


def test_plate_endpoint_with_different_goals(premium_plate_micros_client: TestClient):
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

        resp = premium_plate_micros_client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "day_micros" in data
        assert isinstance(data["day_micros"], dict)
        assert len(data["day_micros"]) > 0
        _assert_deterministic_micros(data)
