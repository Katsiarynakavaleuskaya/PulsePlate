"""Deterministic 429 tests for rate-limiting (PR-628).

RU: Детерминированные тесты 429 для rate-limiting (PR-628).
EN: Deterministic 429 tests for rate-limiting (PR-628).

Key constraint:
- RATE_LIMIT_* values are captured at import-time (decorator argument), therefore tests must
  set env BEFORE importing/reloading `app.security.rate_limit` and `legacy_app`.

Test strategy (canonical for this repo):
- Build a dedicated TestClient after env is set by reloading modules.
- Mock LLM provider loader so /api/v1/insight and /insight return 200 (before limit).
- Use trusted proxy + X-Forwarded-For to ensure stable client key.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def rl_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Create a TestClient with rate-limits applied deterministically.

    RU: Создаёт TestClient с детерминированно применёнными rate-limit (через reload).
    EN: Creates TestClient with rate-limits applied deterministically (via reload).
    """
    # Deterministic low limits (captured at import-time by decorators)
    monkeypatch.setenv("RATE_LIMIT_INSIGHT", "2/minute")
    monkeypatch.setenv("RATE_LIMIT_EXPORTS", "2/minute")

    # Enable LLM endpoint + configure auth for /api/v1/insight and protected routers
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("APP_ENV", "test")

    # Ensure proxy-aware key_func trusts XFF/CF headers in TestClient
    monkeypatch.setenv("TRUSTED_PROXIES", "testclient,testserver,127.0.0.1")

    # Ensure VIP routes are registered if they are env-gated at registration time
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")

    # Reload rate_limit after env is set so backward-compat constants are refreshed.
    import app.security.rate_limit as rate_limit_mod

    importlib.reload(rate_limit_mod)

    # Ensure legacy_app reload will re-import routers so their decorators capture new env values.
    # (We don't reload router modules directly; we just evict them so legacy_app pulls them fresh.)
    for name in (
        "app.routers.plan_export",
        "app.routers.shoplist_export",
        "app.routers.vip_shoplist",
        "app.routers.vip",
        "app.routers.vip_registration",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

    import legacy_app

    importlib.reload(legacy_app)

    # Mock LLM provider loader to ensure endpoints return 200 before hitting 429.
    class DummyProvider:
        name = "dummy"

        async def generate(self, prompt: str) -> str:
            return "ok"

    def dummy_get_provider() -> DummyProvider:
        return DummyProvider()

    legacy_app._load_llm_get_provider = lambda: (lambda: dummy_get_provider())  # noqa: E731

    yield TestClient(legacy_app.app)


def test_insight_v1_rate_limited_200_then_429(rl_client: TestClient) -> None:
    headers = {"x-api-key": "test-key", "x-forwarded-for": "1.2.3.4"}
    payload = {"text": "hello"}

    r1 = rl_client.post("/api/v1/insight", json=payload, headers=headers)
    r2 = rl_client.post("/api/v1/insight", json=payload, headers=headers)
    r3 = rl_client.post("/api/v1/insight", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json() == {"detail": "Rate limit exceeded"}


def test_insight_legacy_rate_limited_200_then_429(rl_client: TestClient) -> None:
    headers = {"x-forwarded-for": "1.2.3.4"}
    payload = {"text": "hello"}

    r1 = rl_client.post("/insight", json=payload, headers=headers)
    r2 = rl_client.post("/insight", json=payload, headers=headers)
    r3 = rl_client.post("/insight", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json() == {"detail": "Rate limit exceeded"}


def test_shoplist_export_rate_limited_200_then_429(rl_client: TestClient) -> None:
    headers = {"x-api-key": "test-key", "x-forwarded-for": "1.2.3.4"}

    r1 = rl_client.get("/api/v1/shoplist/export.csv", headers=headers)
    r2 = rl_client.get("/api/v1/shoplist/export.csv", headers=headers)
    r3 = rl_client.get("/api/v1/shoplist/export.csv", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json() == {"detail": "Rate limit exceeded"}


def test_plan_week_export_csv_rate_limited_200_then_429(rl_client: TestClient) -> None:
    # Plan exports are token-protected when PRIVATE_EXPORTS_ENABLED=true, so we obtain a signed URL first.
    # IMPORTANT: Use a different client key for signing vs exporting to avoid consuming the export rate budget.
    headers_sign = {"x-api-key": "test-key", "x-forwarded-for": "1.2.3.1"}
    headers_export = {"x-api-key": "test-key", "x-forwarded-for": "1.2.3.4"}

    sign_payload = {"path": "/api/v1/plan/week/export.csv", "ttl_seconds": 60}
    signed = rl_client.post("/api/v1/export/sign", json=sign_payload, headers=headers_sign)
    assert signed.status_code == 200
    url = signed.json()["url"]

    r1 = rl_client.get(url, headers=headers_export)
    r2 = rl_client.get(url, headers=headers_export)
    r3 = rl_client.get(url, headers=headers_export)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json() == {"detail": "Rate limit exceeded"}


def test_export_sign_rate_limited_200_then_429(rl_client: TestClient) -> None:
    headers = {"x-api-key": "test-key", "x-forwarded-for": "1.2.3.4"}

    sign_payload = {"path": "/api/v1/plan/week/export.csv", "ttl_seconds": 60}
    s1 = rl_client.post("/api/v1/export/sign", json=sign_payload, headers=headers)
    s2 = rl_client.post("/api/v1/export/sign", json=sign_payload, headers=headers)
    s3 = rl_client.post("/api/v1/export/sign", json=sign_payload, headers=headers)

    assert s1.status_code == 200
    assert s2.status_code == 200
    assert s3.status_code == 429
    assert s3.json() == {"detail": "Rate limit exceeded"}
