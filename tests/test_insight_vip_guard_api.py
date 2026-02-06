"""P0 tests: LLM insight must be VIP-only.

RU: P0 тесты: insight endpoint должен быть строго VIP-only.
EN: P0 tests: insight endpoint must be strictly VIP-only.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

import legacy_app


def _patch_insight_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make VIP insight guard tests CI-deterministic.

    RU: Для этого теста важно только VIP-gate (403/200). Мокаем квоту/хендлер,
    чтобы тест не зависел от БД-квоты/провайдера.
    EN: This test only validates VIP gating (403/200). Mock quota/handler to avoid
    coupling to DB quota/provider internals.
    """

    def _noop_quota(_: str) -> None:
        return None

    async def _ok_v1(_: legacy_app.InsightRequest) -> legacy_app.InsightResponse:
        return legacy_app.InsightResponse(provider="fake-llm", insight="ok")

    async def _ok_legacy(_: legacy_app.InsightRequest) -> legacy_app.InsightResponse:
        return legacy_app.InsightResponse(provider="fake-llm", insight="ok")

    monkeypatch.setattr(legacy_app, "_enforce_vip_llm_monthly_quota", _noop_quota, raising=True)
    monkeypatch.setattr(legacy_app, "insight_v1", _ok_v1, raising=True)
    monkeypatch.setattr(legacy_app, "insight", _ok_legacy, raising=True)


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
    _patch_insight_success(monkeypatch)

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
    _patch_insight_success(monkeypatch)

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
