# -*- coding: utf-8 -*-
"""
RU: Доказательный тест для делегации /plan в canonical BMI engine.
EN: Proof test for /plan delegation to canonical BMI engine.

PR-457 Commit 1: Verify that /plan delegates to canonical handler before migration.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.bmi.engine import BMICalculateResult


def test_plan_delegates_to_canonical_engine(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Доказательный тест: /plan использует engine через handler (shim работает).
    EN: Proof test: /plan uses engine via handler (shim works).

    Monkeypatch calculate_bmi_result to return fixed BMICalculateResult with marker BMI,
    then verify endpoint returns those exact values (proving shim delegation).
    """
    # Patch the actual engine function (most reliable)
    import core.bmi.engine as engine

    # Marker BMI to prove delegation (unlikely to occur naturally)
    # Use value that survives rounding: 12.3 (1 decimal) or 12.35 (2 decimals)
    marker_bmi = 12.35

    # Fixed result to verify it "flows through" the shim
    fixed_result = BMICalculateResult(
        bmi=marker_bmi,
        category="underweight",
        group="general",
        group_display="General",
        interpretation="Test marker BMI for delegation proof.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="adult",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    # Patch engine at source (most reliable)
    monkeypatch.setattr(engine, "calculate_bmi_result", _fixed_engine, raising=True)
    # Optional fallback: patch module-level alias in router (if handler keeps ref)
    try:
        import app.routers.bmi as bmi_router

        monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine, raising=False)
    except (AttributeError, ImportError):
        # Router may not have module-level alias, that's OK
        pass

    payload = {
        "weight_kg": 70.0,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "premium": False,
    }

    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Verify marker BMI flows through (proves canonical handler was called)
    assert data["bmi"] == marker_bmi, (
        f"Expected marker BMI {marker_bmi}, got {data['bmi']}. "
        "This means /plan is NOT delegating to canonical engine (yet)."
    )
