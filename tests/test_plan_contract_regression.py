# -*- coding: utf-8 -*-
"""
RU: Регрессионные тесты для сохранения контракта /plan endpoint.
EN: Regression tests for preserving /plan endpoint contract.

PR-457 Commit 2: Verify that /plan contract is preserved after migration to canonical handler.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.bmi.engine import BMICalculateResult

# Required keys for /plan contract (from legacy_app.py and test_app_comprehensive_97_final.py)
REQUIRED_KEYS = {
    "summary",
    "bmi",
    "category",
    "premium",
    "next_steps",
    "healthy_bmi",
    "action",
}

# Conditional key (only when premium=True)
PREMIUM_KEY = "premium_reco"


def _assert_plan_contract_shape(data: dict, lang: str, premium: bool) -> None:
    """
    RU: Проверка формы контракта /plan (все обязательные поля присутствуют и правильных типов).
    EN: Assert /plan contract shape (all required fields present and correct types).
    """
    # Check all required keys are present
    assert set(data.keys()).issuperset(
        REQUIRED_KEYS
    ), f"Missing required keys. Got: {set(data.keys())}, Expected: {REQUIRED_KEYS}"

    # Check types
    assert isinstance(data["summary"], str), f"summary must be str, got {type(data['summary'])}"
    assert isinstance(data["bmi"], (int, float)), f"bmi must be number, got {type(data['bmi'])}"
    assert data["category"] is None or isinstance(
        data["category"], str
    ), f"category must be str | None, got {type(data['category'])}"
    assert isinstance(data["premium"], bool), f"premium must be bool, got {type(data['premium'])}"
    assert isinstance(
        data["next_steps"], list
    ), f"next_steps must be list, got {type(data['next_steps'])}"
    assert all(isinstance(step, str) for step in data["next_steps"]), "next_steps must be list[str]"
    assert isinstance(
        data["healthy_bmi"], dict
    ), f"healthy_bmi must be dict, got {type(data['healthy_bmi'])}"
    assert "min" in data["healthy_bmi"] and "max" in data["healthy_bmi"]
    assert isinstance(data["healthy_bmi"]["min"], (int, float))
    assert isinstance(data["healthy_bmi"]["max"], (int, float))
    assert isinstance(data["action"], str), f"action must be str, got {type(data['action'])}"

    # Check conditional premium_reco
    if premium:
        assert PREMIUM_KEY in data, "premium_reco must be present when premium=True"
        assert isinstance(data[PREMIUM_KEY], list), "premium_reco must be list"
        assert all(
            isinstance(reco, str) for reco in data[PREMIUM_KEY]
        ), "premium_reco must be list[str]"
    else:
        # premium_reco may or may not be present when premium=False (backward compat)
        pass

    # Check localization (summary and action should be localized)
    if lang == "ru":
        assert "Персональный план" in data["summary"] or "план" in data["summary"].lower()
        assert len(data["summary"]) > 0
        assert len(data["action"]) > 0
    elif lang == "en":
        assert "plan" in data["summary"].lower() or "Personal" in data["summary"]
        assert len(data["summary"]) > 0
        assert len(data["action"]) > 0


def _base_payload(**overrides: Any) -> dict:
    """Helper to build base /plan payload."""
    base = {
        "weight_kg": 70.0,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "premium": False,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_plan_contract_shape_by_language(client: TestClient, lang: str) -> None:
    """
    RU: Проверка контракта /plan для разных языков (EN/RU).
    EN: Verify /plan contract shape for different languages (EN/RU).
    """
    payload = _base_payload(lang=lang)
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    _assert_plan_contract_shape(data, lang=lang, premium=False)

    # Verify localized content differs between languages
    if lang == "ru":
        assert "Персональный план" in data["summary"] or "план" in data["summary"].lower()
    else:
        assert "plan" in data["summary"].lower() or "Personal" in data["summary"]


def test_plan_contract_shape_es_falls_back_to_en(client: TestClient) -> None:
    """
    RU: Проверка, что ES запросы fallback к EN (legacy поведение).
    EN: Verify ES requests fallback to EN (legacy behavior).
    """
    payload_en = _base_payload(lang="en")
    payload_es = _base_payload(lang="es")

    resp_en = client.post("/plan", json=payload_en)
    resp_es = client.post("/plan", json=payload_es)

    assert resp_en.status_code == 200
    assert resp_es.status_code == 200

    en_data = resp_en.json()
    es_data = resp_es.json()

    # ES should fallback to EN (legacy behavior)
    assert es_data["summary"] == en_data["summary"], "ES should fallback to EN summary"
    assert es_data["action"] == en_data["action"], "ES should fallback to EN action"


@pytest.mark.parametrize("pregnant_value", ["yes", "pregnant", "беременна", "беременная"])
def test_plan_contract_category_none_for_pregnant(client: TestClient, pregnant_value: str) -> None:
    """
    RU: Проверка, что category=None для pregnant пользователей (legacy parity: только female).
    EN: Verify category=None for pregnant users (legacy parity: female only).
    """
    payload = _base_payload(gender="female", pregnant=pregnant_value)
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["category"] is None, "category must be None for pregnant users"


def test_plan_contract_male_pregnant_flag_does_not_clear_category(client: TestClient) -> None:
    """
    RU: Legacy parity: pregnant=True не должен работать для male (category остаётся строкой).
    EN: Legacy parity: pregnant=True must not apply to male (category remains a string).
    """
    payload = _base_payload(gender="male", pregnant="yes", age=30, lang="en")
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["category"] is not None, "male + pregnant=yes must NOT force category=None"
    assert isinstance(data["category"], str)


def test_plan_contract_minors_legacy_behavior_is_preserved(client: TestClient) -> None:
    """
    RU: Проверка, что legacy поведение для minors сохранено (category не None).
    EN: Verify legacy behavior for minors is preserved (category is not None).

    This is legacy /plan contract. PR-457=A must preserve it.
    Canonical engine returns category=None for minors, but legacy /plan returns a string category.
    """
    payload = _base_payload(age=15)  # Minor
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # Legacy /plan contract: minors receive a string category (not None)
    assert "category" in data, "category field must exist"
    # Legacy contract: minors must get string category (not None)
    assert isinstance(data["category"], str), "legacy /plan must return string category for minors"
    assert len(data["category"]) > 0, "category string must not be empty"


def test_plan_contract_premium_reco_when_premium(client: TestClient) -> None:
    """
    RU: Проверка, что premium_reco присутствует когда premium=True.
    EN: Verify premium_reco is present when premium=True.
    """
    payload = _base_payload(premium=True)
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert PREMIUM_KEY in data, "premium_reco must be present when premium=True"
    assert isinstance(data[PREMIUM_KEY], list)
    assert len(data[PREMIUM_KEY]) > 0


def test_plan_pregnant_flag_does_not_accept_athlete_keywords(client: TestClient) -> None:
    """
    RU: pregnant не должен принимать athlete/спортсмен как truthy.
    EN: pregnant must not treat athlete keywords as truthy.

    Regression test: если pregnant="athlete", это НЕ должно давать pregnant=True.
    """
    payload = _base_payload(
        pregnant="athlete",  # BUG bait: must be treated as False
        athlete="no",
        age=30,
        lang="en",
    )
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # If pregnant was mis-normalized to True, legacy contract would return category=None
    assert data["category"] is not None, (
        "pregnant='athlete' must NOT normalize to True. "
        "If category is None, pregnant was incorrectly normalized."
    )
    assert isinstance(data["category"], str), "category must be string (not None)"


def test_plan_contract_teen_threshold_uses_canonical_group(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверка, что /plan использует canonical group для пороговых значений.
    EN: Verify /plan uses canonical group for threshold values.

    Regression test: teen (age=15) с BMI=24.7 должен использовать teen threshold 24.5,
    а не adult threshold 25.0. Если group пересчитывается локально, teen будет классифицирован
    как "normal" вместо "overweight".
    """
    # Patch engine to return teen group and BMI=24.7
    import core.bmi.engine as engine
    import app.routers.bmi as bmi_router

    fixed_result = BMICalculateResult(
        bmi=24.7,
        category=None,  # Canonical engine returns None for minors
        group="teen",  # Engine decides group based on age
        group_display="Teen",
        interpretation="Test teen threshold regression.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="teen",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    # Patch at source (engine module)
    monkeypatch.setattr(engine, "calculate_bmi_result", _fixed_engine, raising=True)
    # Patch the already-imported reference in bmi_router (required for runtime)
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine, raising=True)

    # Request for 15-year-old (teen)
    payload = _base_payload(age=15, weight_kg=70.0, height_m=1.70)  # BMI ≈ 24.7
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    # Legacy /plan must return string category for minors
    assert isinstance(data["category"], str), "legacy /plan must return string category for minors"
    assert len(data["category"]) > 0

    # With teen threshold 24.5, BMI=24.7 should be "overweight" (not "normal")
    category_lower = data["category"].lower()
    # Check for overweight indicators (EN: "overweight", "избыточ" for RU)
    assert "over" in category_lower or "избыточ" in category_lower or "избыт" in category_lower, (
        f"Expected overweight category for teen BMI=24.7 (threshold 24.5), "
        f"got '{data['category']}'. This indicates group was not taken from canonical engine."
    )


def test_plan_contract_too_young_returns_category_none(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Проверка, что group="too_young" (age < 12) возвращает category=None.
    EN: Verify group="too_young" (age < 12) returns category=None.

    Regression test: canonical engine returns group="too_young" for children under 12.
    The compat layer must NOT apply adult thresholds and must return category=None.
    """
    import core.bmi.engine as engine
    import app.routers.bmi as bmi_router

    # Fixed result for too_young child (age < 12)
    fixed_result = BMICalculateResult(
        bmi=18.8,  # Would be "Normal" with adult thresholds (18.5-25.0)
        category=None,  # Canonical engine returns None for too_young
        group="too_young",  # Engine returns too_young for age < 12
        group_display="Too young",
        interpretation="Too young for standard BMI classification.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="too_young",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    # Patch at source (engine module)
    monkeypatch.setattr(engine, "calculate_bmi_result", _fixed_engine, raising=True)
    # Patch the already-imported reference in bmi_router (required for runtime)
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine, raising=True)

    # Request for 10-year-old (too_young)
    payload = _base_payload(age=10, weight_kg=30.0, height_m=1.30)
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    # too_young should return category=None (no adult thresholds applied)
    assert data["category"] is None, (
        f"Expected category=None for too_young (age < 12), "
        f"got '{data['category']}'. This indicates adult thresholds were incorrectly applied."
    )


def test_plan_contract_athlete_minor_allows_obesity_tiers_via_compat(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Для minors athlete compat-категоризация должна уметь underweight/obesity tiers.
    EN: Athlete minors must be able to hit underweight/obesity tiers via compat mapping.

    Regression: previously athlete mapping only returned normal/overweight, which broke legacy parity
    for minors when engine_category=None.
    """
    import app.routers.bmi as bmi_router
    import core.bmi.engine as engine
    from core.i18n import t

    fixed_result = BMICalculateResult(
        bmi=35.1,  # should map to obesity_2 (adult buckets)
        category=None,  # force compat mapping for minors
        group="athlete",
        group_display="Athlete",
        interpretation="Athlete minor obesity-tier regression marker.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="teen",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    # Patch canonical engine entrypoint + router reference (handler wiring)
    monkeypatch.setattr(engine, "calculate_bmi_result", _fixed_engine, raising=True)
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine, raising=True)

    payload = _base_payload(
        age=15,  # minor => compat mapping active when category=None
        athlete="yes",
        lang="en",
    )
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # BMI=35.1 maps to obesity_2 tier (adult bucket: 35.0–40.0).
    assert data["category"] == t("en", "bmi_obese_2")


def test_plan_contract_allows_bmi_above_50_without_422(client: TestClient) -> None:
    """
    RU: Регрессия: legacy /plan не должен внезапно ужесточаться (BMI>50 → 422).
    EN: Regression: legacy /plan must not unexpectedly tighten validation (BMI>50 → 422).

    Canonical engine allows BMI up to 100.0; /plan should accept BMI≈50.1.
    """
    payload = _base_payload(
        height_m=1.6,
        weight_kg=128.3,  # BMI ~= 50.12
        lang="en",
    )
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    _assert_plan_contract_shape(data, lang="en", premium=False)
