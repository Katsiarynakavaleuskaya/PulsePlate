from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from app.routers import bmi as bmi_router
from app.schemas.bmi import BMICalculateRequest, BMICalculateResponse
from core.bmi.engine import BMICalculateResult, calculate_bmi_result
from core.i18n import t


@dataclass(frozen=True)
class _WaistRisk:
    wht_ratio: float
    risk_level: str
    notes: list[str]


def test_engine_returns_result_after_implementation() -> None:
    """Test that engine is now implemented and returns BMICalculateResult."""
    result = calculate_bmi_result(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )
    assert isinstance(result, BMICalculateResult)
    assert result.bmi > 0
    assert result.group == "general"
    assert result.category == "normal"


def test_fallback_normalize_bool_flag() -> None:
    assert bmi_router._fallback_normalize_bool_flag(True) is True
    assert bmi_router._fallback_normalize_bool_flag(False) is False

    # Fail-soft: non-boolean/non-string inputs return False rather than raising.
    assert bmi_router._fallback_normalize_bool_flag(123) is False  # type: ignore[arg-type]

    # Empty/whitespace string → False
    assert bmi_router._fallback_normalize_bool_flag("   ") is False

    # Default allowed values
    assert bmi_router._fallback_normalize_bool_flag("да") is True
    assert bmi_router._fallback_normalize_bool_flag("no") is False

    # Custom allowlist
    assert bmi_router._fallback_normalize_bool_flag("ok", yes_values={"ok"}) is True
    assert bmi_router._fallback_normalize_bool_flag("yes", yes_values={"ok"}) is False


@pytest.mark.anyio
async def test_router_uses_core_i18n_normalize_lang_indirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Косвенно проверяем, что router использует core.i18n.normalize_lang,
    нормализуя lang перед локализацией сообщений об ошибке.
    EN: Indirectly verify router uses core.i18n.normalize_lang via localized error detail.

    Note: Pydantic schema validates lang as Literal["ru","en","es"], so we use valid values.
    The handler normalizes them via normalize_lang() before calling t(lang, key).
    """
    # Force engine-unavailable path
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", None)

    # Use valid Pydantic schema values (handler normalizes via normalize_lang before t())
    req_ru = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="ru")
    req_es = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="es")
    req_en = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="en")

    with pytest.raises(HTTPException) as exc_ru:
        await bmi_router.bmi_calculate_handler(req_ru)
    with pytest.raises(HTTPException) as exc_es:
        await bmi_router.bmi_calculate_handler(req_es)
    with pytest.raises(HTTPException) as exc_en:
        await bmi_router.bmi_calculate_handler(req_en)

    assert exc_ru.value.status_code == 501
    assert exc_ru.value.detail == t("ru", "bmi_engine_unavailable")

    assert exc_es.value.status_code == 501
    assert exc_es.value.detail == t("es", "bmi_engine_unavailable")

    assert exc_en.value.status_code == 501
    assert exc_en.value.detail == t("en", "bmi_engine_unavailable")


@pytest.mark.anyio
async def test_handler_returns_501_when_engine_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", None)
    req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="ru")

    with pytest.raises(HTTPException) as exc:
        await bmi_router.bmi_calculate_handler(req)

    assert exc.value.status_code == 501
    assert exc.value.detail == t("ru", "bmi_engine_unavailable")


@pytest.mark.anyio
async def test_handler_maps_not_implemented_to_501(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_not_implemented(**_: Any) -> BMICalculateResult:
        raise NotImplementedError("stub")

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _raise_not_implemented)
    req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="en")

    with pytest.raises(HTTPException) as exc:
        await bmi_router.bmi_calculate_handler(req)

    assert exc.value.status_code == 501
    assert exc.value.detail == t("en", "bmi_engine_unavailable")


@pytest.mark.anyio
async def test_handler_maps_value_error_to_400(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_value_error(**_: Any) -> BMICalculateResult:
        raise ValueError("bad params")

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _raise_value_error)
    req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="es")

    with pytest.raises(HTTPException) as exc:
        await bmi_router.bmi_calculate_handler(req)

    assert exc.value.status_code == 400
    assert exc.value.detail == t("es", "bmi_invalid_parameters")


@pytest.mark.anyio
async def test_handler_maps_unexpected_error_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_runtime_error(**_: Any) -> BMICalculateResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _raise_runtime_error)
    req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="en")

    with pytest.raises(HTTPException) as exc:
        await bmi_router.bmi_calculate_handler(req)

    assert exc.value.status_code == 500
    assert exc.value.detail == t("en", "bmi_calculation_failed")


@pytest.mark.anyio
async def test_handler_success_with_waist_risk_from_dict_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _ok(**_: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=22.86,
            category="normal",
            group="general",
            group_display="General",
            interpretation="OK",
            wht_ratio=0.5,
            whr=None,
            waist_risk=_WaistRisk(wht_ratio=0.5, risk_level="moderate", notes=["n1"]),
            notes=("n1",),
            age_band="adult",
        )

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _ok)

    data = await bmi_router.bmi_calculate_handler(
        {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 90,
            "lang": "en",
        }
    )

    assert data["bmi"] == 22.86
    assert data["waist_risk"]["risk_level"] == "moderate"


@pytest.mark.anyio
async def test_handler_success_with_model_dump_input(monkeypatch: pytest.MonkeyPatch) -> None:
    class _LegacyReq(BaseModel):
        weight_kg: float
        height_cm: float
        age: int
        gender: str = "male"
        pregnant: str | bool = "yes"
        athlete: str | bool = "no"
        waist_cm: float | None = None
        lang: str = "en"

    def _ok(**_: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=23.0,
            category="normal",
            group="general",
            group_display="General",
            interpretation="OK",
            wht_ratio=None,
            whr=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _ok)

    legacy = _LegacyReq(weight_kg=70, height_cm=175, age=30)
    data = await bmi_router.bmi_calculate_handler(legacy)

    assert data["bmi"] == 23.0
    assert data["waist_risk"] is None


@pytest.mark.anyio
async def test_route_returns_response_model(monkeypatch: pytest.MonkeyPatch) -> None:
    def _ok(**_: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=21.0,
            category="normal",
            group="general",
            group_display="General",
            interpretation="OK",
            wht_ratio=None,
            whr=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _ok)

    req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="en")
    resp = await bmi_router.calculate_bmi(req)

    assert isinstance(resp, BMICalculateResponse)
    assert resp.bmi == 21.0
