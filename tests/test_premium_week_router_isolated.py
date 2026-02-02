# -*- coding: utf-8 -*-
"""
RU: Изолированные тесты deprecated premium_week router для diff-cover.
EN: Isolated tests for deprecated premium_week router for diff-cover.

Covers:
- Defensive TypeError path when weekly pipeline returns unexpected type.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_premium_week_pipeline_type_mismatch_raises_typeerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import premium_week as premium_mod
    from app.middleware.api_tiers import require_pro_tier

    app = FastAPI()
    app.include_router(premium_mod.router)
    app.dependency_overrides[require_pro_tier] = lambda: None

    # Avoid reading data/ CSVs in unit tests.
    monkeypatch.setattr(premium_mod, "_get_food_db", lambda: object())
    monkeypatch.setattr(premium_mod, "_get_recipe_db", lambda: object())

    # Bypass profile/targets validation to focus on pipeline contract.
    monkeypatch.setattr(premium_mod, "_is_complete_targets", lambda _d: True)

    def _fake_pipeline(**_kwargs: Any) -> str:
        return "not-a-week-plan-response"

    monkeypatch.setattr(premium_mod, "run_weekly_pipeline_guarded", _fake_pipeline)

    client = TestClient(app)
    try:
        with pytest.raises(TypeError, match=r"Expected PremiumWeekPlanResponse"):
            _ = client.post("/api/v1/premium/plan/week-flexible", json={})
    finally:
        client.close()
        app.dependency_overrides.clear()
