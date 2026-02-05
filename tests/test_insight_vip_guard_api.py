"""P0 tests: LLM insight must be VIP-only.

RU: P0 тесты: insight endpoint должен быть строго VIP-only.
EN: P0 tests: insight endpoint must be strictly VIP-only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import legacy_app

from tests.helpers.fake_llm_provider import FakeLLMProvider


def _patch_llm_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch insight provider loader to return a deterministic fake provider.

    RU: Подменяем loader так, чтобы handler всегда получал fake provider.
    EN: Patch loader so the handler always gets fake provider.
    """

    def _fake_load_llm_get_provider():  # noqa: ANN202 - fixture helper
        return lambda: FakeLLMProvider()

    monkeypatch.setattr(
        legacy_app, "_load_llm_get_provider", _fake_load_llm_get_provider, raising=True
    )


def test_insight_v1_requires_vip_tier(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    """FREE/PRO are rejected; VIP can call /api/v1/insight.

    Note: VIP guard returns 403 for missing key by policy (VIP is a feature-gate).
    """
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    _patch_llm_provider(monkeypatch)

    payload = {"text": "hello"}

    r_free = client.post("/api/v1/insight", json=payload)
    assert r_free.status_code == 403

    r_pro = client.post("/api/v1/insight", json=payload, headers=pro_headers)
    assert r_pro.status_code == 403

    r_vip = client.post("/api/v1/insight", json=payload, headers=vip_headers)
    assert r_vip.status_code == 200
    assert r_vip.headers.get("content-type", "").startswith("application/json")
    data = r_vip.json()
    assert data["provider"] == "fake-llm"
    assert data["insight"] == "ok"


def test_insight_legacy_requires_vip_tier(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    """FREE/PRO are rejected; VIP can call legacy /insight (VIP-only).

    Note: Legacy /insight is hidden from OpenAPI but still VIP-guarded.
    """
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    _patch_llm_provider(monkeypatch)

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
    assert data["provider"] == "fake-llm"
    assert data["insight"] == "ok"


# End of file
