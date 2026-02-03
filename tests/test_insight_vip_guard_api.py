"""P0 tests: LLM insight must be VIP-only.

RU: P0 тесты: insight endpoint должен быть строго VIP-only.
EN: P0 tests: insight endpoint must be strictly VIP-only.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


class _EchoProvider:
    """Deterministic mock provider for insight tests."""

    name: str = "echo"

    async def generate(self, text: str) -> str:
        return f"ok:{text}"


@patch("llm.get_provider", return_value=_EchoProvider())
def test_insight_v1_requires_vip_tier(
    mock_get_provider: Mock,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    """FREE/PRO are rejected; VIP can call /api/v1/insight.

    Note: VIP guard returns 403 for missing key by policy (VIP is a feature-gate).
    """
    monkeypatch.setenv("FEATURE_INSIGHT", "true")

    payload = {"text": "hello"}

    r_free = client.post("/api/v1/insight", json=payload)
    assert r_free.status_code == 403

    r_pro = client.post("/api/v1/insight", json=payload, headers=pro_headers)
    assert r_pro.status_code == 403

    r_vip = client.post("/api/v1/insight", json=payload, headers=vip_headers)
    assert r_vip.status_code == 200
    assert r_vip.headers.get("content-type", "").startswith("application/json")
    data = r_vip.json()
    assert data["provider"] == "echo"
    assert data["insight"].startswith("ok:")


@patch("llm.get_provider", return_value=_EchoProvider())
def test_insight_legacy_requires_vip_tier(
    mock_get_provider: Mock,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    """FREE/PRO are rejected; VIP can call legacy /insight (VIP-only).

    Note: Legacy /insight is hidden from OpenAPI but still VIP-guarded.
    """
    monkeypatch.setenv("FEATURE_INSIGHT", "true")

    payload = {"text": "hello"}

    # FREE → 403
    r_free = client.post("/insight", json=payload)
    assert r_free.status_code == 403

    # PRO → 403
    r_pro = client.post("/insight", json=payload, headers=pro_headers)
    assert r_pro.status_code == 403

    # VIP → 200
    r_vip = client.post("/insight", json=payload, headers=vip_headers)
    assert r_vip.status_code == 200
    assert r_vip.headers.get("content-type", "").startswith("application/json")
    data = r_vip.json()
    assert data["provider"] == "echo"
    assert data["insight"].startswith("ok:")


# End of file
