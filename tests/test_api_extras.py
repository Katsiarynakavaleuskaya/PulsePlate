# -*- coding: utf-8 -*-
from collections.abc import Iterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import app
from tests._client import open_test_client


@pytest.fixture
def api_extras_client() -> Iterator[TestClient]:
    """Open one function-scoped managed client for the canonical app."""
    with open_test_client(app) as managed_client:
        yield managed_client


def test_bmi_422_missing_fields(api_extras_client: TestClient):
    # пустой payload -> 422
    r = api_extras_client.post("/api/v1/bmi", json={}, headers={"X-API-Key": "test_key"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert isinstance(r.json()["detail"], list)

    # отрицательные значения -> 422
    bad = {"weight_kg": -1, "height_cm": 0, "group": "general"}
    r2 = api_extras_client.post("/api/v1/bmi", json=bad, headers={"X-API-Key": "test_key"})
    assert r2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
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
def test_bmi_categories_via_api(api_extras_client: TestClient, weight, height, expected_cat):
    r = api_extras_client.post(
        "/api/v1/bmi",
        json={"weight_kg": weight, "height_cm": height, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["category"].startswith(expected_cat)


def test_openapi_and_docs_exist(api_extras_client: TestClient):
    # /openapi.json
    r = api_extras_client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data and isinstance(data["paths"], dict)

    # /docs (Swagger UI)
    r2 = api_extras_client.get("/docs")
    assert r2.status_code == status.HTTP_200_OK
    assert r2.headers["content-type"].startswith("text/html")
    # /redoc (ReDoc UI)
    r3 = api_extras_client.get("/redoc")
    assert r3.status_code == status.HTTP_200_OK
    assert r3.headers["content-type"].startswith("text/html")
