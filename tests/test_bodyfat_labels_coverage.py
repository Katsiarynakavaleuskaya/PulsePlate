# -*- coding: utf-8 -*-
import importlib

from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)


def test_bodyfat_labels_ru_and_es():
    # Use male to avoid hip_cm requirement in US Navy branch
    base_payload = {
        "height_m": 1.75,
        "weight_kg": 70,
        "age": 30,
        "gender": "male",
        "neck_cm": 38,
        "waist_cm": 82,
        "bmi": 22.9,
    }

    # RU labels
    r_ru = client.post(
        "/api/v1/bodyfat",
        json={**base_payload, "language": "ru"},
        headers={"X-API-Key": "test_key"},
    )
    assert r_ru.status_code == 200
    data_ru = r_ru.json()
    assert data_ru.get("lang") == "ru"
    assert data_ru.get("labels", {}).get("methods") == "методы"
    assert data_ru.get("labels", {}).get("median") == "медиана"

    # ES labels
    r_es = client.post(
        "/api/v1/bodyfat",
        json={**base_payload, "language": "es"},
        headers={"X-API-Key": "test_key"},
    )
    assert r_es.status_code == 200
    data_es = r_es.json()
    assert data_es.get("lang") == "es"
    assert data_es.get("labels", {}).get("methods") == "métodos"
    assert data_es.get("labels", {}).get("median") == "mediana"

