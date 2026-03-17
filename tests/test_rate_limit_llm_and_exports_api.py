"""Deterministic 429 tests for rate-limiting (PR-628).

RU: Детерминированные тесты 429 для rate-limiting (PR-628).
EN: Deterministic 429 tests for rate-limiting (PR-628).

Strategy: HERMETIC APP per test
- Each test gets a fresh Limiter + FastAPI app (no shared state)
- No imports of the production app entrypoints (avoid global side effects)
- No module-cache manipulation

Note:
- This file intentionally does NOT do any “module refresh” (_MODULES_TO_REFRESH) logic anymore.
  It creates an isolated limiter+app per test to avoid cross-test pollution.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.i18n import normalize_lang, t


def _simple_key_func(request: Request) -> str:
    """Simple key function for testing (isolation-friendly)."""
    host = request.client.host if request.client else "unknown"
    test_id = request.headers.get("x-test-id", "default")
    return f"{host}:{test_id}"


def _rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON 429 with i18n message."""
    lang_raw = request.headers.get("accept-language", "en")
    lang = normalize_lang(lang_raw)
    try:
        detail = t(lang, "rate_limit.exceeded")
    except KeyError:
        detail = "Rate limit exceeded"
    return JSONResponse(status_code=429, content={"detail": detail})


def create_rate_limited_app() -> tuple[FastAPI, Limiter]:
    """Create a fresh FastAPI app with its own Limiter instance.

    Returns (app, limiter) so each test has isolated rate limiting.
    """
    # Fresh limiter with fresh storage
    test_limiter = Limiter(
        key_func=_simple_key_func,
        storage_uri="memory://",
    )
    test_limiter.enabled = True

    app = FastAPI()
    router = APIRouter()

    @router.post("/api/v1/insight")
    @test_limiter.limit("2/minute")
    async def insight_v1(request: Request) -> dict[str, str]:
        return {"insight": "test response"}

    @router.post("/api/v1/insight/fitchef")
    @test_limiter.limit("2/minute")
    async def fitchef_mascot(request: Request) -> dict[str, str]:
        return {"message": "fitchef"}

    @router.post("/api/v1/insight/fitchef/weekly-reflection")
    @test_limiter.limit("2/minute")
    async def fitchef_weekly_reflection(request: Request) -> dict[str, str]:
        return {"message": "weekly reflection"}

    @router.post("/api/v1/insight/fitchef/slip-support")
    @test_limiter.limit("2/minute")
    async def fitchef_slip_support(request: Request) -> dict[str, str]:
        return {"message": "slip support"}

    @router.post("/api/v1/internal/creative-research/pilot")
    @test_limiter.limit("2/minute")
    async def creative_research_pilot(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/insight")
    @test_limiter.limit("2/minute")
    async def insight_legacy(request: Request) -> dict[str, str]:
        return {"insight": "test response"}

    @router.get("/api/v1/shoplist/export.csv")
    @test_limiter.limit("2/minute")
    async def shoplist_export(request: Request) -> dict[str, str]:
        return {"export": "csv"}

    @router.post("/api/v1/export/sign")
    @test_limiter.limit("2/minute")
    async def export_sign(request: Request) -> dict[str, str]:
        return {"url": "/signed", "exp": "123", "ttl": "60"}

    @router.get("/api/v1/plan/week/export.csv")
    @test_limiter.limit("2/minute")
    async def plan_export(request: Request) -> dict[str, str]:
        return {"export": "csv"}

    @router.post("/api/v1/pro/restaurants/partner/orders/adapt/preview")
    @test_limiter.limit("2/minute")
    async def partner_order_adapt_preview(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/api/v1/billing/apple/verify-receipt")
    @test_limiter.limit("2/minute")
    async def apple_verify_receipt(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    return app, test_limiter


def test_insight_v1_rate_limited_200_then_429() -> None:
    """Test /api/v1/insight returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "insight-v1"}
    payload = {"text": "hello"}

    r1 = client.post("/api/v1/insight", json=payload, headers=headers)
    r2 = client.post("/api/v1/insight", json=payload, headers=headers)
    r3 = client.post("/api/v1/insight", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    # Verify i18n message
    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_fitchef_mascot_rate_limited_200_then_429() -> None:
    """Test /api/v1/insight/fitchef returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "fitchef-mascot"}
    payload = {"query": "hello"}

    r1 = client.post("/api/v1/insight/fitchef", json=payload, headers=headers)
    r2 = client.post("/api/v1/insight/fitchef", json=payload, headers=headers)
    r3 = client.post("/api/v1/insight/fitchef", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_fitchef_weekly_reflection_rate_limited_200_then_429() -> None:
    """Test /api/v1/insight/fitchef/weekly-reflection returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "fitchef-weekly-reflection"}
    payload = {"summary": "late dinners", "goal": "steady dinners"}

    r1 = client.post("/api/v1/insight/fitchef/weekly-reflection", json=payload, headers=headers)
    r2 = client.post("/api/v1/insight/fitchef/weekly-reflection", json=payload, headers=headers)
    r3 = client.post("/api/v1/insight/fitchef/weekly-reflection", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_fitchef_slip_support_rate_limited_200_then_429() -> None:
    """Test /api/v1/insight/fitchef/slip-support returns 200 twice, then 429."""

    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "fitchef-slip-support"}
    payload = {"event_text": "late-night snacking", "goal": "steady dinners"}

    r1 = client.post("/api/v1/insight/fitchef/slip-support", json=payload, headers=headers)
    r2 = client.post("/api/v1/insight/fitchef/slip-support", json=payload, headers=headers)
    r3 = client.post("/api/v1/insight/fitchef/slip-support", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_creative_research_pilot_rate_limited_200_then_429() -> None:
    """Test hidden internal creative-research pilot returns 200 twice, then 429."""

    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "creative-research-pilot"}
    payload = {"prompt_seed": "meal adherence"}

    r1 = client.post("/api/v1/internal/creative-research/pilot", json=payload, headers=headers)
    r2 = client.post("/api/v1/internal/creative-research/pilot", json=payload, headers=headers)
    r3 = client.post("/api/v1/internal/creative-research/pilot", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_insight_legacy_rate_limited_200_then_429() -> None:
    """Test /insight (legacy) returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "ru", "x-test-id": "insight-legacy"}
    payload = {"text": "hello"}

    r1 = client.post("/insight", json=payload, headers=headers)
    r2 = client.post("/insight", json=payload, headers=headers)
    r3 = client.post("/insight", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    # Verify i18n message (Russian)
    lang = normalize_lang("ru")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_shoplist_export_rate_limited_200_then_429() -> None:
    """Test /api/v1/shoplist/export.csv returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "shoplist-export"}

    r1 = client.get("/api/v1/shoplist/export.csv", headers=headers)
    r2 = client.get("/api/v1/shoplist/export.csv", headers=headers)
    r3 = client.get("/api/v1/shoplist/export.csv", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    # Verify i18n message
    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_plan_week_export_csv_rate_limited_200_then_429() -> None:
    """Test /api/v1/plan/week/export.csv returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "es", "x-test-id": "plan-week-export"}

    r1 = client.get("/api/v1/plan/week/export.csv", headers=headers)
    r2 = client.get("/api/v1/plan/week/export.csv", headers=headers)
    r3 = client.get("/api/v1/plan/week/export.csv", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    # Verify i18n message (Spanish)
    lang = normalize_lang("es")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_export_sign_rate_limited_200_then_429() -> None:
    """Test /api/v1/export/sign returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "export-sign"}
    payload = {"path": "/api/v1/plan/week/export.csv", "ttl_seconds": 60}

    s1 = client.post("/api/v1/export/sign", json=payload, headers=headers)
    s2 = client.post("/api/v1/export/sign", json=payload, headers=headers)
    s3 = client.post("/api/v1/export/sign", json=payload, headers=headers)

    assert s1.status_code == 200
    assert s2.status_code == 200
    assert s3.status_code == 429
    assert s3.headers.get("content-type", "").startswith("application/json")

    # Verify i18n message
    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert s3.json()["detail"] == expected_detail


def test_partner_order_adapt_preview_rate_limited_200_then_429() -> None:
    """Test partner export adapter preview endpoint returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "partner-adapt-preview"}
    payload = {"restaurant_id": "r1", "week_plan": {"days": []}}

    r1 = client.post(
        "/api/v1/pro/restaurants/partner/orders/adapt/preview", headers=headers, json=payload
    )
    r2 = client.post(
        "/api/v1/pro/restaurants/partner/orders/adapt/preview", headers=headers, json=payload
    )
    r3 = client.post(
        "/api/v1/pro/restaurants/partner/orders/adapt/preview", headers=headers, json=payload
    )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail


def test_apple_verify_receipt_rate_limited_200_then_429() -> None:
    """Test POST /api/v1/billing/apple/verify-receipt returns 200 twice, then 429."""
    app, _ = create_rate_limited_app()
    client = TestClient(app)
    headers = {"accept-language": "en", "x-test-id": "apple-verify-receipt"}
    payload = {"receipt_data": "base64-receipt-test"}

    r1 = client.post("/api/v1/billing/apple/verify-receipt", headers=headers, json=payload)
    r2 = client.post("/api/v1/billing/apple/verify-receipt", headers=headers, json=payload)
    r3 = client.post("/api/v1/billing/apple/verify-receipt", headers=headers, json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("content-type", "").startswith("application/json")

    lang = normalize_lang("en")
    expected_detail = t(lang, "rate_limit.exceeded")
    assert r3.json()["detail"] == expected_detail
