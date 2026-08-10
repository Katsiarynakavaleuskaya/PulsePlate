# -*- coding: utf-8 -*-
"""
RU: Тест предупреждений по жизненным этапам для /api/v1/premium/targets.
EN: Test life stage warnings for /api/v1/premium/targets.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app as app_mod
from tests._client import open_test_client


@pytest.fixture
def premium_targets_lifestage_client() -> Iterator[TestClient]:
    """Open one managed client for the exact imported application."""
    with open_test_client(app_mod.app) as managed_client:
        yield managed_client


@pytest.mark.parametrize(
    "case",
    [
        {"age": 16, "life_stage": "teen", "code": "teen"},
        {"age": 30, "life_stage": "pregnant", "code": "pregnant"},
        {"age": 30, "life_stage": "lactating", "code": "lactating"},
        {"age": 55, "life_stage": "elderly", "code": "elderly"},
        {"age": 8, "life_stage": "child", "code": "child"},
    ],
)
@pytest.mark.parametrize("lang", ["ru", "en", "es"])
def test_life_stage_warnings(
    premium_targets_lifestage_client: TestClient,
    case: dict[str, object],
    lang: str,
) -> None:
    """Test that life stage warnings are generated correctly."""
    payload = {
        "sex": "female",
        "age": case["age"],
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "light",
        "goal": "maintain",
        "life_stage": case["life_stage"],
        "lang": lang,
    }
    resp = premium_targets_lifestage_client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()

    # Check that warnings are present
    assert "warnings" in data
    assert isinstance(data["warnings"], list)

    # Check that the expected warning code is present
    codes = [w.get("code") for w in data["warnings"]]
    assert case["code"] in codes

    # Check that the warning has a message
    warning = next(w for w in data["warnings"] if w.get("code") == case["code"])
    assert "message" in warning
    assert len(warning["message"]) > 0


def test_life_stage_warnings_no_warnings(
    premium_targets_lifestage_client: TestClient,
) -> None:
    """Test that no life-stage warnings are generated for a normal adult."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }
    resp = premium_targets_lifestage_client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()

    # Other warning categories may still be present for a normal adult.
    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    life_stage_warning_codes = {"teen", "pregnant", "lactating", "elderly", "child"}
    assert life_stage_warning_codes.isdisjoint(warning.get("code") for warning in data["warnings"])


def test_life_stage_warnings_localization(
    premium_targets_lifestage_client: TestClient,
) -> None:
    """Test that warnings are properly localized."""
    payload = {
        "sex": "female",
        "age": 16,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "teen",
        "lang": "ru",
    }
    resp = premium_targets_lifestage_client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()

    # Find the teen warning
    teen_warning = next(w for w in data["warnings"] if w.get("code") == "teen")
    message = teen_warning["message"]

    # Check that the message contains Russian text
    assert "Подростковая" in message or "специализированные" in message
