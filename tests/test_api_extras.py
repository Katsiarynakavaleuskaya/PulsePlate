# -*- coding: utf-8 -*-
import pytest
from fastapi import status
from fastapi.testclient import TestClient


def test_bmi_422_missing_fields(client: TestClient) -> None:
    # пустой payload -> 422
    r = client.post("/api/v1/bmi", json={}, headers={"X-API-Key": "test_key"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert r.headers["content-type"].startswith("application/json")
    assert isinstance(r.json()["detail"], list)

    # отрицательные значения -> 422
    bad = {"weight_kg": -1, "height_cm": 0, "group": "general"}
    r2 = client.post("/api/v1/bmi", json=bad, headers={"X-API-Key": "test_key"})
    assert r2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert r2.headers["content-type"].startswith("application/json")
    assert isinstance(r2.json()["detail"], list)


@pytest.mark.parametrize(
    "weight,height,expected_cat",
    [
        (50, 170, "Underweight"),  # ~17.3
        (70, 170, "Normal"),  # ~24.2 (v1 endpoint returns "Normal")
        (80, 170, "Overweight"),  # ~27.7
        (95, 170, "Obese"),  # ~32.9 (v1 endpoint returns "Obese")
    ],
)
def test_bmi_categories_via_api(
    client: TestClient,
    weight: float,
    height: float,
    expected_cat: str,
) -> None:
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": weight, "height_cm": height, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["category"].startswith(expected_cat)


def test_openapi_and_docs_exist(client: TestClient) -> None:
    # /openapi.json
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = r.json()
    assert "paths" in data and isinstance(data["paths"], dict)

    # /docs (Swagger UI)
    r2 = client.get("/docs")
    assert r2.status_code == status.HTTP_200_OK
    assert r2.headers["content-type"].startswith("text/html")
    # /redoc (ReDoc UI)
    r3 = client.get("/redoc")
    assert r3.status_code == status.HTTP_200_OK
    assert r3.headers["content-type"].startswith("text/html")
