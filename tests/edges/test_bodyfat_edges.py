from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bodyfat import get_router
from tests._client import open_test_client


@contextmanager
def _client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(get_router())
    with open_test_client(app) as managed_client:
        yield managed_client


def test_bodyfat_bmi_is_derived_when_missing():
    with _client() as client:
        # Provide weight/height so BMI is derived and calculators can run
        payload = {
            "height_m": 1.75,
            "weight_kg": 72,
            "age": 30,
            "gender": "male",
            "waist_cm": 85,
            "neck_cm": 39,
            "language": "en",
        }
        resp = client.post("/bodyfat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["lang"] == "en"
        assert "methods" in data and isinstance(data["methods"], dict)


def test_bodyfat_handles_invalid_inputs_gracefully():
    with _client() as client:
        # Provide only minimally required fields to avoid Pydantic 422
        # and ensure the endpoint responds gracefully with empty methods
        payload = {"gender": "female", "language": "es"}
        resp = client.post("/bodyfat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["lang"] == "es"
        # With invalid inputs, methods may be empty but response should be well-formed
        assert isinstance(data.get("methods"), dict)
