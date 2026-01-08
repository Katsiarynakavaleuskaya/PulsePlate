"""
Tests for JSON serialization of legacy BMI endpoint validation errors.

RU: Тесты JSON-сериализуемости ошибок валидации legacy BMI endpoints.
EN: Tests for JSON serialization of legacy BMI endpoint validation errors.

This guards against non-serializable objects (e.g., ValueError in Pydantic error ctx)
that could cause 500 errors or invalid JSON responses in production.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import app


def _assert_jsonable(x: Any) -> None:
    """
    RU: Рекурсивно проверяет, что значение JSON-сериализуемо (примитивы, dict, list).
    EN: Recursively checks that value is JSON-serializable (primitives, dict, list).

    Raises:
        AssertionError: If value contains non-JSON-serializable types (e.g., Exception, set, tuple).
    """
    # Allowed JSON primitives
    if x is None or isinstance(x, (str, int, float, bool)):
        return
    if isinstance(x, list):
        for v in x:
            _assert_jsonable(v)
        return
    if isinstance(x, dict):
        for k, v in x.items():
            # JSON keys must be strings
            assert isinstance(k, str), f"JSON key must be string, got {type(k).__name__}"
            _assert_jsonable(v)
        return

    # Anything else is a bug (e.g., ValueError, Exception, set, tuple, etc.)
    raise AssertionError(f"Non-JSON-serializable value in response: {type(x).__name__} {x!r}")


@pytest.fixture()
def client() -> TestClient:
    """TestClient fixture for legacy BMI API tests."""
    return TestClient(app)


def test_legacy_bmi_male_pregnant_422_is_json_serializable(client: TestClient) -> None:
    """
    RU: Legacy endpoint /api/v1/bmi должен возвращать JSON-сериализуемый 422 при male+pregnant.
    EN: Legacy endpoint /api/v1/bmi must return JSON-serializable 422 for male+pregnant.

    This guards against non-serializable objects in Pydantic error ctx (e.g., ValueError).
    """
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "male",
        "pregnant": True,
        "athlete": False,
        "waist_cm": None,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 422

    # This must not raise (guards against non-serializable objects)
    body = resp.json()
    assert isinstance(body, dict)
    assert "detail" in body

    # Recursively check that detail is JSON-serializable
    _assert_jsonable(body["detail"])


def test_legacy_bmi_prefix_male_pregnant_422_is_json_serializable(client: TestClient) -> None:
    """
    RU: Legacy endpoint /api/v1/bmi должен возвращать JSON-сериализуемый 422 при prefix-based male+pregnant.
    EN: Legacy endpoint /api/v1/bmi must return JSON-serializable 422 for prefix-based male+pregnant.

    Tests prefix-based gender matching (e.g., "hombre_fullform", "мужик").
    """
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "hombre_fullform",
        "pregnant": True,
        "athlete": False,
        "waist_cm": None,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 422

    body = resp.json()
    assert isinstance(body, dict)
    assert "detail" in body

    _assert_jsonable(body["detail"])


def test_legacy_bmi_v0_male_pregnant_422_is_json_serializable(client: TestClient) -> None:
    """
    RU: Legacy endpoint /bmi (v0) должен возвращать JSON-сериализуемый 422 при male+pregnant.
    EN: Legacy endpoint /bmi (v0) must return JSON-serializable 422 for male+pregnant.
    """
    payload = {
        "weight_kg": 70.0,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": True,
        "athlete": False,
        "waist_cm": None,
        "lang": "en",
    }

    resp = client.post("/bmi", json=payload)
    assert resp.status_code == 422

    body = resp.json()
    assert isinstance(body, dict)
    assert "detail" in body

    _assert_jsonable(body["detail"])


def test_canonical_bmi_male_pregnant_422_is_json_serializable(client: TestClient) -> None:
    """
    RU: Canonical endpoint /api/v1/bmi/calculate должен возвращать JSON-сериализуемый 422 при male+pregnant.
    EN: Canonical endpoint /api/v1/bmi/calculate must return JSON-serializable 422 for male+pregnant.

    This ensures the canonical endpoint also guards against non-serializable error objects.
    """
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "male",
        "pregnant": True,
        "athlete": False,
        "waist_cm": None,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi/calculate", json=payload)
    assert resp.status_code == 422

    body = resp.json()
    assert isinstance(body, dict)
    assert "detail" in body

    _assert_jsonable(body["detail"])
