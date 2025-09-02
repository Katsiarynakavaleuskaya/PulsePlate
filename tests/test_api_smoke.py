from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    return TestClient(app)

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200

def test_bmi_smoke_ok(client):
    r = client.post("/bmi", json={
        "weight_kg": 70,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
    })
    assert r.status_code == 200

def test_v1_bmi_smoke(client):
    r = client.post("/api/v1/bmi", json={
        "weight_kg": 70,
        "height_cm": 175,
    }, headers={"X-API-Key": "test_key"})
    assert r.status_code == 200

def test_v1_insight_smoke(client):
    # Mock the LLM provider to avoid external dependencies
    with patch("llm.get_provider") as mock_get_provider:
        mock_provider = Mock()
        mock_provider.generate.return_value = "Test insight"
        mock_provider.name = "test_provider"
        mock_get_provider.return_value = mock_provider

        r = client.post("/api/v1/insight", json={"text": "hello"}, headers={"X-API-Key": "test_key"})
        assert r.status_code == 200
        assert r.json()["insight"] == "Test insight"
        assert r.json()["provider"] == "test_provider"

def test_metrics_smoke(client):
    r = client.get("/metrics")
    assert r.status_code == 200
