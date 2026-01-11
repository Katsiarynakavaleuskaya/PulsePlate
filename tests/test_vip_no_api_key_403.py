"""VIP No API Key Test

RU: Тест для проверки 403 при отсутствии API ключа.
EN: Test for 403 when API key is missing.

This is a separate test from the tier matrix, as the contract is different:
- No API key → 403 "VIP access required"
- Invalid/PRO key → 403 "Upgrade to VIP" message
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_vip_health_without_api_key_is_403_access_required(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """Test that VIP endpoint without API key returns 403 with 'VIP access required' message.

    RU: Тест, что VIP endpoint без API ключа возвращает 403 с сообщением 'VIP access required'.
    EN: Test that VIP endpoint without API key returns 403 with 'VIP access required' message.
    """
    monkeypatch.setenv("VIP_MODULE_ENABLED", "1")
    r = client.get("/api/v1/vip/health", headers={})
    assert r.status_code == 403
    data = r.json()
    assert data.get("detail") == "VIP access required"
