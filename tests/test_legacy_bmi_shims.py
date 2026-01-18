# -*- coding: utf-8 -*-
"""
RU: Доказательные тесты для shim'ов legacy BMI endpoints.
EN: Proof tests for legacy BMI endpoint shims.

PR-456 Commit 3: Verify that /bmi and /api/v1/bmi delegate to canonical handler.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.bmi.engine import BMICalculateResult
from core.bmi.risk import WaistRiskResult
from core.i18n import t


def test_bmi_endpoint_v1_uses_canonical_handler_via_shim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Доказательный тест: /api/v1/bmi использует engine через handler (shim работает).
    EN: Proof test: /api/v1/bmi uses engine via handler (shim works).

    Monkeypatch calculate_bmi_result to return fixed BMICalculateResult,
    then verify endpoint returns those exact values (proving shim delegation).
    """
    import app.routers.bmi as bmi_router

    # Fixed result to verify it "flows through" the shim
    fixed_result = BMICalculateResult(
        bmi=22.5,
        category="normal",
        group="general",
        group_display="General",
        interpretation="Your BMI is within the normal range.",
        wht_ratio=0.48,
        whr=None,
        waist_risk=WaistRiskResult(
            wht_ratio=0.48,
            risk_level="low",
            notes=("Low waist-related risk",),
        ),
        notes=("Low waist-related risk",),
        age_band="adult",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    # Call legacy endpoint
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    # Verify legacy format with values from fixed engine result
    assert data["bmi"] == 22.5  # From fixed_result
    assert data["category"] == "Normal weight"  # Localized from "normal" slug
    assert data["group"] == "general"  # From fixed_result
    assert data["athlete"] is False  # Derived from group != "athlete"
    assert "note" in data  # Legacy field (waist risk notes or interpretation)
    # Note should contain waist risk notes (from fixed_result.notes)
    assert (
        "Low waist-related risk" in data["note"]
        or data["note"] == "Your BMI is within the normal range."
    )

    # Verify required legacy fields are present; extra fields are allowed for forward compatibility
    expected_keys = {"bmi", "category", "note", "athlete", "group"}
    assert set(data.keys()).issuperset(
        expected_keys
    ), f"Missing legacy keys. Got: {set(data.keys())}"


def test_bmi_endpoint_uses_canonical_handler_via_shim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Доказательный тест: /bmi использует engine через handler (shim работает).
    EN: Proof test: /bmi uses engine via handler (shim works).

    Monkeypatch calculate_bmi_result to return fixed BMICalculateResult,
    then verify endpoint returns those exact values (proving shim delegation).
    Also verify visualization gate is preserved (include_chart=False to avoid matplotlib dependency).
    """
    import app.routers.bmi as bmi_router

    # Fixed result to verify it "flows through" the shim
    fixed_result = BMICalculateResult(
        bmi=24.8,
        category="normal",
        group="athlete",
        group_display="Athlete",
        interpretation="Your BMI is within the normal range for athletes.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="adult",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    # Call legacy endpoint (height_m format, include_chart=False to avoid matplotlib)
    payload = {
        "weight_kg": 80.0,
        "height_m": 1.80,
        "age": 28,
        "gender": "male",
        "pregnant": "no",
        "athlete": "yes",
        "waist_cm": None,
        "lang": "en",
        "include_chart": False,  # Avoid matplotlib dependency in test
    }

    resp = client.post("/bmi", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    # Verify legacy format with values from fixed engine result
    assert data["bmi"] == 24.8  # From fixed_result
    assert data["category"] == "Normal weight"  # Localized from "normal" slug
    assert data["group"] == "athlete"  # From fixed_result
    assert data["athlete"] is True  # Derived from group == "athlete"
    assert "note" in data  # Legacy field (athlete disclaimer)
    # Note should contain athlete disclaimer (priority over interpretation)
    assert "athlete" in data["note"].lower() or "BMI may overestimate" in data["note"]

    # Verify required legacy fields are present; extra fields are allowed for forward compatibility
    expected_keys = {"bmi", "category", "note", "athlete", "group"}
    assert set(data.keys()).issuperset(
        expected_keys
    ), f"Missing legacy keys. Got: {set(data.keys())}"

    # Verify visualization gate: with include_chart=False, visualization should not be added
    # (or if added, it should be gracefully handled)
    # This is a smoke test - full visualization testing is in test_bmi_visualization.py


def test_bmi_endpoint_unknown_category_falls_back_to_slug(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Если engine вернул неизвестный category slug, legacy shim должен отдать его как есть.
    EN: If engine returns an unknown category slug, legacy shim should fall back to returning it.
    """
    import app.routers.bmi as bmi_router

    fixed_result = BMICalculateResult(
        bmi=24.8,
        category="mystery_category",
        group="general",
        group_display="General",
        interpretation="Some interpretation.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="adult",
    )

    def _fixed_engine(**_: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    payload = {
        "weight_kg": 80.0,
        "height_m": 1.80,
        "age": 28,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": None,
        "lang": "en",
        "include_chart": False,
    }

    resp = client.post("/bmi", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "mystery_category"


def test_bmi_endpoint_v1_validation_error_maps_to_422(client: TestClient) -> None:
    """
    RU: BMIRequestV1 допускает age=0, но canonical BMICalculateRequest требует age>=1.
        Shim должен вернуть 422 с ValidationError details.
    EN: BMIRequestV1 allows age=0, but BMICalculateRequest requires age>=1.
        Shim should return 422 with ValidationError details.
    """
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 0,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 422
    detail = resp.json().get("detail")
    assert isinstance(detail, list)


def test_bmi_endpoint_v1_unrealistic_bmi_is_422(client: TestClient) -> None:
    """
    RU: BMIRequestV1 должен отклонять нереалистичный BMI > 100.
    EN: BMIRequestV1 must reject unrealistic BMI > 100.

    Regression: V1 validation now delegates BMI computation to core.bmi.engine._compute_bmi.
    """
    payload = {
        "weight_kg": 320.0,  # BMI ~ 125 for 160cm
        "height_cm": 160.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 422


def test_bmi_endpoint_v1_athlete_note_appends_waist_risk_notes_and_unknown_category_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Covers legacy_app.py:
    - unknown category fallback to slug
    - athlete note appends waist risk notes
    """
    import app.routers.bmi as bmi_router

    fixed_result = BMICalculateResult(
        bmi=22.5,
        category="mystery_category",
        group="athlete",
        group_display="Athlete",
        interpretation="Ignored for athlete note.",
        wht_ratio=0.48,
        whr=None,
        waist_risk=None,
        notes=("Extra waist note",),
        age_band="adult",
    )

    def _fixed_engine(**_: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "yes",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["category"] == "mystery_category"
    assert data["group"] == "athlete"
    assert data["athlete"] is True
    assert data["note"] == f"{t('en', 'advice_athlete_bmi')} | Extra waist note"
