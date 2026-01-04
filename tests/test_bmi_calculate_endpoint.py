# -*- coding: utf-8 -*-
"""
RU: Тесты для публичного Free BMI endpoint `/api/v1/bmi/calculate`.
EN: Tests for the public Free BMI endpoint `/api/v1/bmi/calculate`.

PR-454: shim + thin adapter wiring.
- Engine пока stub -> 501
- Маппинг dataclass -> Pydantic schema (waist_risk)
- Нормализация bool-флагов (pregnant/athlete) проверяется через monkeypatch
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.bmi.engine import BMICalculateResult
from core.bmi.risk import WaistRiskResult


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    """
    RU: Валидный payload для BMICalculateRequest (и совместимый с shim-потоком).
    EN: Valid payload for BMICalculateRequest (also compatible with shim flow).
    """
    base: dict[str, Any] = {
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 80.0,
        "lang": "en",
    }
    base.update(overrides)
    return base


def test_bmi_calculate_returns_501_when_engine_not_implemented(
    client: TestClient,
) -> None:
    """
    RU: Пока engine = stub, endpoint должен быть детерминированно 501.
    EN: While engine is a stub, the endpoint must deterministically return 501.
    """
    resp = client.post("/api/v1/bmi/calculate", json=_valid_payload())
    assert resp.status_code == 501
    # Default FastAPI HTTPException shape
    assert resp.json() == {"detail": "BMI engine is not available"}


def test_bmi_calculate_happy_path_maps_result_and_serializes_waist_risk(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем маппинг BMICalculateResult -> BMICalculateResponse и сериализацию waist_risk.
    EN: Validate mapping BMICalculateResult -> BMICalculateResponse and waist_risk serialization.
    """

    captured: dict[str, Any] = {}

    def _fake_engine(**kwargs: Any) -> BMICalculateResult:
        captured.update(kwargs)
        waist_risk = WaistRiskResult(
            wht_ratio=0.52,
            risk_level="moderate",
            notes=("Increased waist-related risk",),
        )
        return BMICalculateResult(
            bmi=24.22,
            category="normal",
            group="general",
            group_display="General",
            interpretation="Within normal range.",
            wht_ratio=0.52,
            waist_risk=waist_risk,
            notes=("Test note",),
            age_band="adult",
        )

    # Patch engine call used by router handler
    import app.routers.bmi as bmi_router  # noqa: F401 (explicit import for monkeypatch)

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine)

    resp = client.post(
        "/api/v1/bmi/calculate",
        json=_valid_payload(pregnant="yes", athlete=True),
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["bmi"] == 24.22
    assert data["category"] == "normal"
    assert data["group"] == "general"
    assert data["group_display"] == "General"
    assert data["interpretation"] == "Within normal range."
    assert data["wht_ratio"] == 0.52
    assert data["notes"] == ["Test note"]
    assert data["age_band"] == "adult"

    # waist_risk is strict schema -> JSON should include fields
    assert data["waist_risk"]["risk_level"] == "moderate"
    assert data["waist_risk"]["wht_ratio"] == 0.52

    # Tuple -> JSON list
    assert data["waist_risk"]["notes"] == ["Increased waist-related risk"]

    # Ensure bool normalization happened before engine call
    assert captured["pregnant"] is True
    assert captured["athlete"] is True


def test_bmi_calculate_validation_422(client: TestClient) -> None:
    """
    RU: Pydantic validation должна отдавать 422.
    EN: Pydantic validation should return 422.
    """
    resp = client.post("/api/v1/bmi/calculate", json=_valid_payload(weight_kg=-1))
    assert resp.status_code == 422
