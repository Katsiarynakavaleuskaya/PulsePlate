import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict) and data.get("status") == "ok"


def test_bmi_smoke_ok():
    payload = {
        "height_m": 1.70,
        "weight_kg": 65,
        "age": 28,
        "gender": "female",
        "pregnant": "no",
        "athlete": "no",
        "user_group": "general",
        "language": "en",
    }
    r = client.post("/bmi", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "bmi" in data and 0 < float(data["bmi"]) < 100


def test_v1_bmi_smoke():
    payload = {"weight_kg": 70, "height_cm": 170, "group": "general"}
    r = client.post(
        "/api/v1/bmi",
        json=payload,
        headers={"X-API-Key": "test_key"}
    )
    assert r.status_code == 200
    data = r.json()
    assert "bmi" in data and 0 < float(data["bmi"]) < 100
    assert "category" in data


class _StubProvider:
    name = "stub-test"

    def generate(self, text: str) -> str:
        return f"insight::{text[::-1]}"


def test_v1_insight_smoke():
    with patch('llm.get_provider', return_value=_StubProvider()):
        r = client.post(
            "/api/v1/insight",
            json={"text": "hello"},
            headers={"X-API-Key": "test_key"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "insight" in data


def test_metrics_smoke():
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "uptime_seconds" in data
