# -*- coding: utf-8 -*-
"""
RU: Регрессионные тесты для сохранения контракта /plan endpoint.
EN: Regression tests for preserving /plan endpoint contract.

PR-457 Commit 2: Verify that /plan contract is preserved after migration to canonical handler.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


def _base_payload(**overrides: dict) -> dict:
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


def test_plan_contract_category_none_for_pregnant(client: TestClient) -> None:
    """
    RU: Проверка, что category=None для pregnant пользователей (canonical поведение).
    EN: Verify category=None for pregnant users (canonical behavior).
    """
    payload = _base_payload(pregnant="yes")
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["category"] is None, "category must be None for pregnant users"


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
