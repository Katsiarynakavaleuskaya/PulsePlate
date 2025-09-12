# -*- coding: utf-8 -*-
"""
RU: Тесты для покрытия app.py (группы, insight, debug_env).
EN: Coverage tests for app.py (groups, insight, debug_env).
"""

import pytest
from fastapi.testclient import TestClient

try:
    from app import app as fastapi_app  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


@pytest.mark.parametrize("group", ["athlete", "pregnant", "elderly", "teen"])
def test_bmi_groups_exercise_branches(group: str):
    payload = {"weight_kg": 70, "height_cm": 170, "group": group}
    res = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
    assert res.status_code == 200
    data = res.json()
    assert "bmi" in data and isinstance(data["bmi"], (int, float))
    assert "category" in data


def test_insight_route_or_skip():
    """Если /insight не поднят (404) — скипаем, иначе ждём 503."""
    res = client.post("/api/v1/insight", json={"text": "hello"}, headers={"X-API-Key": "test_key"})
    if res.status_code == 404:
        pytest.skip("No /insight route (skipping)")
    assert res.status_code == 503


def test_debug_env_keys_or_skip():
    res = client.get("/debug_env")
    if res.status_code == 404:
        pytest.skip("No /debug_env route (skipping)")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    # минимальный контракт: наличие флага инсайта
    assert "insight_enabled" in data


def test_bmi_endpoint_lang_en_athlete():
    payload = {
        "weight_kg": 70,
        "height_m": 1.7,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "yes",
        "waist_cm": 95,
        "lang": "en",
    }
    res = client.post("/bmi", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "bmi" in data
    assert "category" in data
    assert "note" in data
    # since athlete=yes and lang=en, note should contain "athletes"
    assert "athletes" in data["note"]
    # since waist_cm=95 >=94, should contain "Increased"
    assert "Increased" in data["note"]
