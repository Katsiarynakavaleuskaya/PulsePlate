import os
from typing import cast

from fastapi.testclient import TestClient
from starlette.types import ASGIApp


def test_vip_plate_and_targets_smoke(monkeypatch):
    import app as apppkg

    # Enable premium features and provide API key
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("APP_ENV", "test")

    client = TestClient(cast(ASGIApp, apppkg.app))

    headers = {"X-API-Key": os.getenv("API_KEY", "test-key")}

    plate_payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "activity": "moderate",
        "goal": "maintain",
    }
    r1 = client.post("/api/v1/premium/plate", json=plate_payload, headers=headers)
    assert r1.status_code in (200, 503)

    targets_payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
    }
    r2 = client.post("/api/v1/premium/targets", json=targets_payload, headers=headers)
    assert r2.status_code in (200, 503)

    # Admin status path to execute scheduler branch
    r3 = client.get("/api/v1/admin/status", headers=headers)
    assert r3.status_code in (200, 503)
