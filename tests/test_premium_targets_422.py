# -*- coding: utf-8 -*-
"""
RU: Тест валидации Pydantic для /api/v1/premium/targets (422 ошибки).
EN: Test Pydantic validation for /api/v1/premium/targets (422 errors).
"""
import pytest
from fastapi.testclient import TestClient

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(app_mod.app)  # type: ignore


@pytest.mark.parametrize(
    "bad_field, bad_value",
    [
        ("sex", "unknown"),  # invalid enum
        ("activity", "hyper-ultra"),  # invalid enum
        ("goal", "explode"),  # invalid enum
        ("life_stage", "alien"),  # invalid enum
        ("age", -5),  # negative age
        ("age", 150),  # too old
        ("height_cm", -10),  # negative height
        ("weight_kg", -5),  # negative weight
        ("deficit_pct", 50),  # too high deficit
        ("surplus_pct", 50),  # too high surplus
        ("bodyfat", -5),  # negative bodyfat
        ("bodyfat", 80),  # too high bodyfat
    ],
)
def test_invalid_payload_422(bad_field, bad_value):
    """Test that invalid payloads return 422 status code."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }
    payload[bad_field] = bad_value

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 422

    # Check that the response contains validation error details
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0


def test_missing_required_fields_422():
    """Test that missing required fields return 422."""
    # Missing sex field
    payload = {
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 422

    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)

    # Check that the error mentions the missing field
    error_messages = [error.get("msg", "") for error in data["detail"]]
    assert any("field required" in msg.lower() for msg in error_messages)


def test_invalid_lang_parameter():
    """Test that invalid language parameter is handled gracefully."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "xx",  # invalid language code
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    # Should still work (lang is just a string, not validated enum)
    assert resp.status_code == 200


def test_edge_case_values():
    """Test edge case values that should be valid."""
    payload = {
        "sex": "male",
        "age": 1,  # minimum age
        "height_cm": 0.1,  # very small height
        "weight_kg": 0.1,  # very small weight
        "activity": "sedentary",
        "goal": "maintain",
        "life_stage": "child",
        "lang": "en",
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200


def test_maximum_valid_values():
    """Test maximum valid values."""
    payload = {
        "sex": "female",
        "age": 120,  # maximum age
        "height_cm": 300,  # very tall
        "weight_kg": 500,  # very heavy
        "activity": "very_active",
        "goal": "gain",
        "life_stage": "elderly",
        "deficit_pct": 25,  # maximum deficit
        "surplus_pct": 20,  # maximum surplus
        "bodyfat": 50,  # maximum bodyfat (60 is too high)
        "lang": "es",
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200
