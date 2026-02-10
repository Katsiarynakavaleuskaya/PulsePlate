"""P0 tests: LLM insight must be VIP-only.

RU: P0 тесты: insight endpoint должен быть строго VIP-only.
EN: P0 tests: insight endpoint must be strictly VIP-only.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.helpers.fake_llm_provider import FakeLLMProvider
from tests.helpers.module_resolve import resolve_legacy_app, resolve_llm


def _patch_insight_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make VIP insight guard tests CI-deterministic.

    RU: Для этого теста важно только VIP-gate (403/200). Мокаем квоту/хендлер,
    чтобы тест не зависел от БД-квоты/провайдера.
    EN: This test only validates VIP gating (403/200). Mock quota/handler to avoid
    coupling to DB quota/provider internals.
    """

    def _noop_quota(*_args: object, **_kwargs: object) -> None:
        return None

    # IMPORTANT: resolve modules at runtime to avoid stale module references.
    # Some tests intentionally purge/reload modules (see module_purge), and under xdist this can
    # create multiple module instances. Patching a stale module object is a common CI-only flake.
    legacy_app = resolve_legacy_app()
    llm = resolve_llm()

    monkeypatch.setattr(legacy_app, "_enforce_vip_llm_monthly_quota", _noop_quota, raising=True)
    # Provider mocking must be robust across CI import paths.
    # RU: В CI реальный путь резолва провайдера идёт через legacy_app._load_llm_get_provider().
    # EN: In CI the effective provider resolution path goes through legacy_app._load_llm_get_provider().
    monkeypatch.setattr(
        legacy_app,
        "_load_llm_get_provider",
        lambda: (lambda: FakeLLMProvider()),
        raising=True,
    )
    # Keep llm.get_provider patched as a secondary safety net.
    monkeypatch.setattr(llm, "get_provider", lambda: FakeLLMProvider(), raising=True)


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
    assert (
        r_vip.status_code == 200
    ), f"status={r_vip.status_code} content-type={r_vip.headers.get('content-type')} body={r_vip.text}"
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
    assert (
        r_vip.status_code == 200
    ), f"status={r_vip.status_code} content-type={r_vip.headers.get('content-type')} body={r_vip.text}"
    assert r_vip.headers.get("content-type", "").startswith("application/json")
    data = r_vip.json()
    assert data["provider"] == "fake-llm"
    assert data["insight"] == "ok"


# --- Guards for loader extraction (PR-A) ---


def test_core_llm_provider_loader_resolves_llm_get_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: canonical loader must stay lazy and patchable.

    We patch `llm.get_provider` first, then assert the loader returns the patched symbol.
    This ensures `core.insight.llm_provider_loader.load_llm_get_provider()` is executed (diff-cover)
    without relying on endpoint behavior.
    """
    llm = resolve_llm()

    def _sentinel_get_provider() -> object:
        return object()

    monkeypatch.setattr(llm, "get_provider", _sentinel_get_provider, raising=True)

    from core.insight.llm_provider_loader import load_llm_get_provider

    assert load_llm_get_provider() is _sentinel_get_provider


# End of file
