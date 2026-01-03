# -*- coding: utf-8 -*-
"""
Diff coverage tests for weekly plan endpoints error envelope.

Covers:
- PRO endpoint returns error envelope on generation failure
- Premium endpoint returns error envelope on generation failure
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO


def test_pro_weekly_returns_error_envelope_on_generation_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test PRO weekly endpoint returns error envelope when build_week fails."""
    import app.routers.pro as pro_router

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("generation failed")

    # Patch the symbol used by the endpoint
    monkeypatch.setattr(pro_router, "build_week", boom, raising=True)

    resp = client.post(
        "/api/v1/pro/meal/weekly",
        json={
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        },
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert resp.status_code == 500
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "weekly_generation_failed"
    assert data.get("stage") == "generation"
    assert "detail" in data
    assert "message" in data


def test_premium_weekly_returns_error_envelope_on_generation_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Premium weekly endpoint returns error envelope when build_week fails."""
    import app.routers.premium_week as premium_router

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("generation failed")

    monkeypatch.setattr(premium_router, "build_week", boom, raising=True)

    resp = client.post(
        "/api/v1/premium/plan/week-flexible",
        json={
            "sex": "female",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        },
        headers={"X-API-Key": TEST_KEY_PRO},  # premium also uses require_pro_tier
    )
    assert resp.status_code == 500
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "weekly_generation_failed"
    assert data.get("stage") == "generation"
    assert "detail" in data
    assert "message" in data
