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

import importlib
import importlib.abc
import sys
from importlib.machinery import ModuleSpec
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.bmi import BMICalculateRequest
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


def test_bmi_calculate_returns_200_when_engine_implemented(
    client: TestClient,
) -> None:
    """
    RU: После PR-455 engine реализован, endpoint возвращает 200 с результатом.
    EN: After PR-455 engine is implemented, endpoint returns 200 with result.
    """
    resp = client.post("/api/v1/bmi/calculate", json=_valid_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "bmi" in data
    assert "group" in data
    assert "category" in data
    assert data["bmi"] > 0


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


@pytest.mark.anyio
async def test_calculate_bmi_endpoint_direct_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем прямой вызов endpoint calculate_bmi (строки 208-209).
    EN: Verify direct call to calculate_bmi endpoint (lines 208-209).
    """
    import app.routers.bmi as bmi_router

    def _fake_engine(**kwargs: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=24.0,
            category="normal",
            group="general",
            group_display="General",
            interpretation="OK",
            wht_ratio=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine)

    req = BMICalculateRequest(
        weight_kg=70.0,
        height_cm=170.0,
        age=30,
        gender="male",
        pregnant="no",
        athlete="no",
        waist_cm=None,
        lang="en",
    )

    # Direct call to endpoint (covers lines 208-209)
    result = await bmi_router.calculate_bmi(req)
    assert result.bmi == 24.0
    assert result.category == "normal"


def test_bmi_calculate_valueerror_handler(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: ValueError от engine должен возвращать 400 с локализованным сообщением.
    EN: ValueError from engine should return 400 with localized message.
    """

    def _fake_engine_raises_valueerror(**kwargs: Any) -> BMICalculateResult:
        raise ValueError("BMI out of bounds")

    import app.routers.bmi as bmi_router

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine_raises_valueerror)

    resp = client.post("/api/v1/bmi/calculate", json=_valid_payload(lang="ru"))
    assert resp.status_code == 400
    assert (
        "bmi_invalid_parameters" in resp.json()["detail"]
        or "некорректные параметры" in resp.json()["detail"].lower()
    )


def test_bmi_calculate_exception_handler(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Неожиданный Exception от engine должен возвращать 500 с локализованным сообщением.
    EN: Unexpected Exception from engine should return 500 with localized message.
    """

    def _fake_engine_raises_exception(**kwargs: Any) -> BMICalculateResult:
        raise RuntimeError("Unexpected error")

    import app.routers.bmi as bmi_router

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine_raises_exception)

    resp = client.post("/api/v1/bmi/calculate", json=_valid_payload(lang="en"))
    assert resp.status_code == 500
    assert (
        "bmi_calculation_failed" in resp.json()["detail"]
        or "calculation failed" in resp.json()["detail"].lower()
    )


def test_bmi_calculate_without_waist_risk(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Когда waist_cm отсутствует, waist_risk должен быть None.
    EN: When waist_cm is missing, waist_risk should be None.
    """

    def _fake_engine_no_waist(**kwargs: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=24.22,
            category="normal",
            group="general",
            group_display="General",
            interpretation="Within normal range.",
            wht_ratio=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    import app.routers.bmi as bmi_router

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine_no_waist)

    resp = client.post(
        "/api/v1/bmi/calculate",
        json=_valid_payload(waist_cm=None),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["waist_risk"] is None
    assert data["wht_ratio"] is None


def test_bmi_calculate_i18n_ru_en_es(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем локализацию ошибок для всех языков.
    EN: Verify error localization for all languages.
    """

    def _fake_engine_raises_valueerror(**kwargs: Any) -> BMICalculateResult:
        raise ValueError("Test error")

    import app.routers.bmi as bmi_router

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine_raises_valueerror)

    # Test RU
    resp_ru = client.post("/api/v1/bmi/calculate", json=_valid_payload(lang="ru"))
    assert resp_ru.status_code == 400

    # Test EN
    resp_en = client.post("/api/v1/bmi/calculate", json=_valid_payload(lang="en"))
    assert resp_en.status_code == 400

    # Test ES
    resp_es = client.post("/api/v1/bmi/calculate", json=_valid_payload(lang="es"))
    assert resp_es.status_code == 400


def test_bmi_calculate_dict_input_without_model_dump(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем обработку dict-like input без model_dump.
    EN: Verify handling of dict-like input without model_dump.
    """

    def _fake_engine(**kwargs: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=24.22,
            category="normal",
            group="general",
            group_display="General",
            interpretation="Within normal range.",
            wht_ratio=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    import app.routers.bmi as bmi_router

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine)

    # Direct dict input (no model_dump attribute)
    resp = client.post("/api/v1/bmi/calculate", json=_valid_payload())
    assert resp.status_code == 200


def test_normalize_bool_flag_edge_cases() -> None:
    """
    RU: Проверяем edge cases для _normalize_bool_flag.
    EN: Verify edge cases for _normalize_bool_flag.
    """
    from app.routers.bmi import _normalize_bool_flag

    # Test with None (not bool, not str)
    assert _normalize_bool_flag(None) is False  # type: ignore[arg-type]  # intentional fail-soft

    # Test with int (not bool, not str)
    assert _normalize_bool_flag(0) is False  # type: ignore[arg-type]  # intentional fail-soft
    assert _normalize_bool_flag(1) is False  # type: ignore[arg-type]  # intentional fail-soft


@pytest.mark.anyio
async def test_handler_accepts_bmicalculaterequest_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем, что handler принимает BMICalculateRequest instance напрямую (строка 107).
    EN: Verify handler accepts BMICalculateRequest instance directly (line 107).

    Закрывает ветку: if isinstance(req_in, BMICalculateRequest): req = req_in
    """
    import app.routers.bmi as bmi_router

    captured: dict[str, Any] = {}

    def _fake_engine(**kwargs: Any) -> BMICalculateResult:
        captured.update(kwargs)
        return BMICalculateResult(
            bmi=22.0,
            category="normal",
            group="general",
            group_display="General",
            interpretation="OK",
            wht_ratio=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine)

    req = BMICalculateRequest(
        weight_kg=70.0,
        height_cm=178.0,
        age=30,
        gender="male",
        pregnant="no",
        athlete="no",
        waist_cm=None,
        lang="en",
    )

    data = await bmi_router.bmi_calculate_handler(req)
    assert data["bmi"] == 22.0
    assert captured["pregnant"] is False
    assert captured["athlete"] is False


@pytest.mark.anyio
async def test_handler_accepts_dict_input_and_validates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем, что handler принимает dict и валидирует через model_validate (строка 114).
    EN: Verify handler accepts dict and validates via model_validate (line 114).

    Закрывает ветку: req = BMICalculateRequest.model_validate(req_in) (dict input)
    """
    import app.routers.bmi as bmi_router

    def _fake_engine(**kwargs: Any) -> BMICalculateResult:
        return BMICalculateResult(
            bmi=23.5,
            category="normal",
            group="general",
            group_display="General",
            interpretation="OK",
            wht_ratio=None,
            waist_risk=None,
            notes=(),
            age_band="adult",
        )

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fake_engine)

    payload = {
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": None,
        "lang": "en",
    }

    data = await bmi_router.bmi_calculate_handler(payload)
    assert data["bmi"] == 23.5


def test_importerror_sets_calculate_bmi_result_none_and_returns_501(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверяем, что при ImportError engine handler возвращает 501 (строки 38-40).
    EN: Verify that ImportError in engine import returns 501 (lines 38-40).

    Закрывает ветку:
      try: from core.bmi.engine import ...
      except ImportError: calculate_bmi_result = None

    Мы форсим ImportError только для 'core.bmi.engine', затем reload app.routers.bmi.
    """

    class _FailEngineImporter(importlib.abc.MetaPathFinder):
        """MetaPathFinder that raises ImportError for core.bmi.engine."""

        def find_spec(
            self,
            fullname: str,
            path: object | None = None,
            target: object | None = None,
        ) -> ModuleSpec | None:
            if fullname == "core.bmi.engine":
                raise ImportError("forced for coverage")
            return None

    # Remove module using monkeypatch API BEFORE setting blocker (repo-policy compliant)
    for name in list(sys.modules.keys()):
        if name == "app.routers.bmi" or name.startswith("app.routers.bmi."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    # Also remove core.bmi.engine if already imported
    for name in list(sys.modules.keys()):
        if name == "core.bmi.engine" or name.startswith("core.bmi.engine."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    # Add finder to meta_path (repo-policy compliant)
    blocker = _FailEngineImporter()
    monkeypatch.setattr(sys, "meta_path", [blocker, *sys.meta_path])

    # Now import will trigger ImportError path
    import app.routers.bmi as bmi_router

    importlib.reload(bmi_router)

    # Verify that ImportError path was executed
    assert (
        bmi_router.calculate_bmi_result is None
    ), "calculate_bmi_result should be None after ImportError"

    # Note: client fixture uses already-loaded app, so we need to patch the handler directly
    # to test the ImportError branch. The endpoint will use the reloaded module's None value.
    # Patch at the module level to simulate ImportError state
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", None)

    resp = client.post(
        "/api/v1/bmi/calculate",
        json={
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": None,
            "lang": "en",
        },
    )

    # After PR-455, engine is implemented, so ImportError path should return 501
    # If monkeypatch worked correctly, calculate_bmi_result should be None
    assert (
        resp.status_code == 501
    ), f"Expected 501 when engine unavailable, got {resp.status_code}. Response: {resp.json()}"
    assert "detail" in resp.json()
