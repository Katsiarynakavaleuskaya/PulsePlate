# -*- coding: utf-8 -*-
"""
RU: Diff-coverage тест — покрываем postprocess stage (WeekPlanResponse construction)
    для PRO и deprecated Premium weekly endpoints.
EN: Diff-coverage test — cover postprocess stage (WeekPlanResponse construction)
    for PRO and deprecated Premium weekly endpoints.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO


def _valid_weekly_req() -> dict[str, Any]:
    """Minimal valid request that triggers targets derivation path."""
    return {
        "sex": "female",
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en",
    }


def test_pro_weekly_returns_error_envelope_on_postprocess_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test PRO weekly endpoint returns error envelope when WeekPlanResponse construction fails."""
    import app.routers.pro as pro_router

    # Force generation to succeed quickly without touching core.
    monkeypatch.setattr(
        pro_router,
        "build_week",
        lambda *_a, **_k: {
            "daily_menus": [],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 0.0,
            "adherence_score": 0.0,
        },
        raising=True,
    )

    # Force postprocess (ProWeekPlanResponse(**week)) to fail.
    class BoomWeekPlanResponse:
        def __init__(self, **_kwargs: Any) -> None:
            raise ValueError("postprocess failed")

    monkeypatch.setattr(pro_router, "ProWeekPlanResponse", BoomWeekPlanResponse, raising=True)

    resp = client.post(
        "/api/v1/pro/meal/weekly",
        json=_valid_weekly_req(),
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert resp.status_code == 500
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "weekly_postprocess_failed"
    assert data.get("stage") == "postprocess"
    assert "detail" in data
    assert "message" in data


def test_premium_weekly_returns_error_envelope_on_postprocess_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Premium weekly endpoint returns error envelope when WeekPlanResponse construction fails."""
    import app.routers.premium_week as premium_router

    monkeypatch.setattr(
        premium_router,
        "build_week",
        lambda *_a, **_k: {
            "daily_menus": [],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 0.0,
            "adherence_score": 0.0,
        },
        raising=True,
    )

    class BoomWeekPlanResponse:
        def __init__(self, **_kwargs: Any) -> None:
            raise ValueError("postprocess failed")

    monkeypatch.setattr(
        premium_router, "PremiumWeekPlanResponse", BoomWeekPlanResponse, raising=True
    )

    resp = client.post(
        "/api/v1/premium/plan/week-flexible",
        json=_valid_weekly_req(),
        headers={"X-API-Key": TEST_KEY_PRO},  # premium also uses require_pro_tier
    )
    assert resp.status_code == 500
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "weekly_postprocess_failed"
    assert data.get("stage") == "postprocess"
    assert "detail" in data
    assert "message" in data
