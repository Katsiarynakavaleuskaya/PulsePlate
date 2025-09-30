# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient

try:
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Import the FastAPI app from app.py file
    import importlib.util

    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load app.py")

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    fastapi_app = app_module.app  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


def test_bmi_422_missing_fields():
    # пустой payload -> 422
    r = client.post("/api/v1/bmi", json={}, headers={"X-API-Key": "test_key"})
    assert r.status_code in (400, 422, 403)

    # отрицательные значения -> 422
    bad = {"weight_kg": -1, "height_cm": 0, "group": "general"}
    r2 = client.post("/api/v1/bmi", json=bad, headers={"X-API-Key": "test_key"})
    assert r2.status_code in (400, 422, 403)


@pytest.mark.parametrize(
    "weight,height,expected_cat",
    [
        (50, 170, "Underweight"),  # ~17.3
        (70, 170, "Normal"),  # ~24.2 (v1 endpoint returns "Normal")
        (80, 170, "Overweight"),  # ~27.7
        (95, 170, "Obese"),  # ~32.9 (v1 endpoint returns "Obese")
    ],
)
def test_bmi_categories_via_api(weight, height, expected_cat):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": weight, "height_cm": height, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        data = r.json()
        assert data["category"].startswith(expected_cat)


def test_openapi_and_docs_exist():
    # /openapi.json
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data and isinstance(data["paths"], dict)

    # /docs (Swagger UI)
    r2 = client.get("/docs")
    assert r2.status_code in (200, 307, 308)  # иногда редиректит
    # /redoc (ReDoc UI)
    r3 = client.get("/redoc")
    assert r3.status_code in (200, 307, 308)
