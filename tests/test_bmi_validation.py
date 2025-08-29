# -*- coding: utf-8 -*-
import importlib
from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)

def test_bmi_height_as_string_invalid():
    r = client.post("/api/v1/bmi", json={"weight_kg": 70, "height_cm": "170"})
    assert r.status_code == 422

def test_bmi_weight_as_string_invalid():
    r = client.post("/api/v1/bmi", json={"weight_kg": "70", "height_cm": 170})
    assert r.status_code == 422

def test_bmi_group_unknown_still_ok():
    r = client.post("/api/v1/bmi", json={"weight_kg": 70, "height_cm": 170, "group": "ALIEN"})
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] == 24.22
    assert data["category"] == "Normal"
    assert isinstance(data.get("interpretation",""), str)
