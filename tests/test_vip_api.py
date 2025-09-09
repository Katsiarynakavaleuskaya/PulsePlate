# -*- coding: utf-8 -*-
"""
VIP API Tests

RU: Тесты для VIP API эндпоинтов
EN: Tests for VIP API endpoints
"""
from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app)


def test_vip_health():
    """Test VIP health endpoint returns 200"""
    r = client.get("/api/v1/vip/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["module"] == "vip"
    assert "features" in data


def test_vip_weekly_plan_echo():
    """Test VIP weekly plan endpoint returns echo structure"""
    payload = {
        "goals": {"calories": 2000, "protein": 150},
        "constraints": {"diet_flags": ["VEG"]},
    }
    r = client.post("/api/v1/vip/menu/weekly/plan", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "planned"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_weekly_repair_echo():
    """Test VIP weekly repair endpoint returns echo structure"""
    payload = {"menu": {"days": 7, "meals": []}, "deficits": {"Ca": 200, "VitD": 100}}
    r = client.post("/api/v1/vip/menu/weekly/repair", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "repaired"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_module_disabled():
    """Test that VIP endpoints return 404 when module is disabled"""
    import importlib
    import os

    # Temporarily disable VIP module
    original_value = os.environ.get("VIP_MODULE_ENABLED")
    os.environ["VIP_MODULE_ENABLED"] = "false"

    try:
        # Reimport app with disabled VIP
        importlib.reload(app_module)

        client_disabled = TestClient(app_module.app)
        r = client_disabled.get("/api/v1/vip/health")
        assert r.status_code == 404
    finally:
        # Restore original value
        if original_value is not None:
            os.environ["VIP_MODULE_ENABLED"] = original_value
        else:
            os.environ.pop("VIP_MODULE_ENABLED", None)
        # Reimport app with VIP enabled
        importlib.reload(app_module)
