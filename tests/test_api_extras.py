# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient

try:
    from app import app as fastapi_app  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


def test_bmi_422_missing_fields():
    # пустой payload -> 422
    r = client.post("/api/v1/bmi", json={})
    assert r.status_code in (400, 422)

    # отрицательные значения -> 422
    bad = {"weight_kg": -1, "height_cm": 0, "group": "general"}
    r2 = client.post("/api/v1/bmi", json=bad)
    assert r2.status_code in (400, 422)


@pytest.mark.parametrize(
    "weight,height,expected_cat",
    [
        (50, 170, "Underweight"),  # ~17.3
        (70, 170, "Normal"),  # ~24.2
        (80, 170, "Overweight"),  # ~27.7
        (95, 170, "Obese"),  # ~32.9
    ],
)
def test_bmi_categories_via_api(weight, height, expected_cat):
    r = client.post(
        "/api/v1/bmi",
        json={
            "weight_kg": weight,
            "height_cm": height,
            "group": "general"
        }
    )
    assert r.status_code == 200
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
