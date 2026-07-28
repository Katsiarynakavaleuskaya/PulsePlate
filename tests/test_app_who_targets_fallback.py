"""Compatibility-path tests for WHO targets fallback and safety handling."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import app
from app.services import pro_nutrition_targets as service
from core.bmr import FALLBACK_BMR_KCAL_PER_KG_PER_DAY
from core.utils import get_activity_factor


def _request(
    *,
    sex: str = "female",
    weight_kg: float = 65,
    activity: str = "moderate",
    goal: str = "maintain",
    life_stage: str = "adult",
) -> app.WHOTargetsRequest:
    return app.WHOTargetsRequest(
        sex=sex,
        age=34,
        height_cm=168,
        weight_kg=weight_kg,
        activity=activity,
        goal=goal,
        life_stage=life_stage,
    )


def test_api_who_targets_value_error_uses_loss_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject(_profile: object) -> object:
        raise ValueError("invalid profile")

    monkeypatch.setattr(service.nutrition_recommendations, "build_nutrition_targets", _reject)
    request = _request(goal="loss", life_stage="pregnant")

    response = asyncio.run(app.api_who_targets(request.model_dump()))

    tdee = int(
        FALLBACK_BMR_KCAL_PER_KG_PER_DAY * request.weight_kg * get_activity_factor(request.activity)
    )
    expected = max(1200, int(tdee * 0.85))
    assert response.kcal_daily == expected
    assert any(warning["code"] == "pregnant" for warning in response.warnings)


def test_api_who_targets_import_error_uses_gain_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(_profile: object) -> object:
        raise ImportError("optional target backend unavailable")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unavailable,
    )
    request = _request(sex="male", weight_kg=78, activity="light", goal="gain")

    response = asyncio.run(app.api_who_targets(request.model_dump()))

    tdee = int(
        FALLBACK_BMR_KCAL_PER_KG_PER_DAY * request.weight_kg * get_activity_factor(request.activity)
    )
    assert response.kcal_daily == int(tdee * 1.1)
    assert response.warnings == []


def test_api_who_targets_unexpected_failure_is_not_false_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _crash(_profile: object) -> object:
        raise RuntimeError("sensitive backend details")

    monkeypatch.setattr(service.nutrition_recommendations, "build_nutrition_targets", _crash)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(app.api_who_targets(_request().model_dump()))

    assert raised.value.status_code == 500
    assert raised.value.detail == service.WHO_TARGETS_CALCULATION_FAILED_DETAIL
    assert "sensitive backend details" not in str(raised.value.detail)


def test_api_who_targets_returns_safety_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: ["hydrate more"],
    )

    response = asyncio.run(app.api_who_targets(_request().model_dump()))

    assert {"code": "safety", "message": "hydrate more"} in response.warnings


def test_api_who_targets_safety_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail_closed(_targets: object) -> object:
        raise ValueError("sensitive validator payload")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        _fail_closed,
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(app.api_who_targets(_request().model_dump()))

    assert raised.value.status_code == 500
    assert raised.value.detail == service.WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL
    assert "sensitive validator payload" not in str(raised.value.detail)
