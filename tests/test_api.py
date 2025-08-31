# -*- coding: utf-8 -*-
import importlib

from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)


def test_v1_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_v1_bmi_happy():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "general"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] == 24.22
    assert data["category"] == "Normal"


def test_v1_bmi_invalid_height():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 0, "group": "general"}
    )
    # Pydantic validation returns 422 for invalid field values
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_invalid_weight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": -50, "height_cm": 170, "group": "general"}
    )
    # Pydantic validation returns 422 for invalid field values
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_invalid_group():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "invalid"}
    )
    # Since we allow any string for group, this should work
    assert r.status_code == 200
    data = r.json()
    assert "bmi" in data


def test_v1_bmi_underweight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 45, "height_cm": 170, "group": "general"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] < 18.5
    assert data["category"] == "Underweight"


def test_v1_bmi_overweight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 85, "height_cm": 170, "group": "general"}
    )
    assert r.status_code == 200
    data = r.json()
    assert 25 <= data["bmi"] < 30
    assert data["category"] == "Overweight"


def test_v1_bmi_obese():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 100, "height_cm": 170, "group": "general"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] >= 30
    assert data["category"] == "Obese"


def test_v1_bodyfat():
    r = client.post(
        "/api/v1/bodyfat",
        json={
            "height_m": 1.70,
            "weight_kg": 65,
            "age": 28,
            "gender": "female",
            "neck_cm": 34,
            "waist_cm": 74,
            "hip_cm": 94,
            "language": "en"
        }
    )
    assert r.status_code == 200
    data = r.json()
    assert "methods" in data
    assert "median" in data
    assert "labels" in data


def test_v1_bodyfat_missing_hip():
    r = client.post(
        "/api/v1/bodyfat",
        json={
            "height_m": 1.70,
            "weight_kg": 65,
            "age": 28,
            "gender": "female",
            "neck_cm": 34,
            "waist_cm": 74,
            "language": "en"
        }
    )
    assert r.status_code == 200
    data = r.json()
    assert "methods" in data
    # Since hip_cm missing, us_navy should not be in methods
    assert "us_navy" not in data["methods"]
