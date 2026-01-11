"""VIP Guard Order Test: 403 (tier gate) wins over 422 (validation)

RU: Тест порядка проверок: tier guard (403) должен срабатывать раньше валидации payload (422).
EN: Test that tier guard (403) is checked before payload validation (422).

This test ensures the principle "tier wins over payload" is enforced.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP


def test_vip_guard_403_before_422_no_key(client: TestClient) -> None:
    """Test that missing API key returns 403 (tier gate), not 422 (validation).

    RU: Тест, что отсутствие API ключа возвращает 403 (tier gate), а не 422 (валидация).
    EN: Test that missing API key returns 403 (tier gate), not 422 (validation).
    """
    # Invalid payload that would normally cause 422
    invalid_payload = {"invalid": "data", "missing_required_fields": True}

    # Without API key header
    response = client.post("/api/v1/vip/menu/weekly/plan", json=invalid_payload, headers={})
    assert response.status_code == 403, "Tier guard (403) should win over payload validation (422)"
    assert (
        "vip" in response.json().get("detail", "").lower()
        or "access" in response.json().get("detail", "").lower()
    )


def test_vip_guard_403_before_422_invalid_tier(client: TestClient) -> None:
    """Test that invalid tier (PRO key) returns 403, not 422.

    RU: Тест, что неверный tier (PRO ключ) возвращает 403, а не 422.
    EN: Test that invalid tier (PRO key) returns 403, not 422.
    """
    # Invalid payload that would normally cause 422
    invalid_payload = {"invalid": "data", "missing_required_fields": True}

    # With PRO key (valid key, but insufficient tier)
    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=invalid_payload,
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert response.status_code == 403, "Tier guard (403) should win over payload validation (422)"
    assert (
        "vip" in response.json().get("detail", "").lower()
        or "access" in response.json().get("detail", "").lower()
    )


def test_vip_guard_422_after_valid_tier(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that with valid VIP key, invalid payload returns 422 (validation error).

    RU: Тест, что с валидным VIP ключом невалидный payload возвращает 422 (ошибка валидации).
    EN: Test that with valid VIP key, invalid payload returns 422 (validation error).
    """
    # Invalid payload
    invalid_payload = {"invalid": "data", "missing_required_fields": True}

    # Mock internal call to avoid 500
    monkeypatch.setattr(
        "app.routers.vip._safe_call_with_adapter",
        lambda func_name, **kwargs: {"status": "error", "code": "validation_failed"},
    )

    # With valid VIP key
    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=invalid_payload,
        headers={"X-API-Key": TEST_KEY_VIP},
    )
    # With valid tier, validation should run and return 422
    assert response.status_code == 422, "With valid VIP key, invalid payload should return 422"


def test_vip_guard_200_with_valid_tier_and_payload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that with valid VIP key and valid payload, endpoint returns 200.

    RU: Тест, что с валидным VIP ключом и валидным payload endpoint возвращает 200.
    EN: Test that with valid VIP key and valid payload, endpoint returns 200.
    """
    # Valid payload
    valid_payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "activity": "moderate",
        "goal": "maintain",
    }

    # Mock internal call
    monkeypatch.setattr(
        "app.routers.vip._safe_call_with_adapter",
        lambda func_name, **kwargs: {"status": "success", "menu": {"days": []}},
    )

    # With valid VIP key
    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=valid_payload,
        headers={"X-API-Key": TEST_KEY_VIP},
    )
    assert response.status_code == 200, "With valid VIP key and payload, should return 200"
