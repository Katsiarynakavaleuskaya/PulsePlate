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
