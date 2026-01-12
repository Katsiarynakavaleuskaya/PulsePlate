"""PR-519 parity tests: deprecated premium aliases match canonical PRO contracts.

These tests intentionally avoid asserting business correctness; they assert that
deprecated `/api/v1/premium/*` endpoints are thin proxies to canonical `/api/v1/pro/*`
contracts (same request → same response).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO


def _premium_headers() -> dict[str, str]:
    # tests/conftest.py sets API_KEY="test_key" for the session
    return {"X-API-Key": "test_key"}


def _pro_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_KEY_PRO}


def test_premium_targets_matches_pro_targets(client: TestClient) -> None:
    payload = {
        "sex": "female",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    r_premium = client.post("/api/v1/premium/targets", json=payload, headers=_premium_headers())
    assert r_premium.status_code == 200, r_premium.text

    r_pro = client.post("/api/v1/pro/nutrition/targets", json=payload, headers=_pro_headers())
    assert r_pro.status_code == 200, r_pro.text

    assert r_premium.json() == r_pro.json()


def test_premium_plate_matches_pro_plate(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "1")

    # Keep test deterministic and fast: force fallback path by disabling backend helpers.
    import legacy_app

    monkeypatch.setattr(legacy_app, "make_plate", None, raising=False)
    monkeypatch.setattr(legacy_app, "calculate_all_bmr", None, raising=False)
    monkeypatch.setattr(legacy_app, "calculate_all_tdee", None, raising=False)

    payload = {
        "sex": "female",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    r_premium = client.post("/api/v1/premium/plate", json=payload, headers=_premium_headers())
    assert r_premium.status_code == 200, r_premium.text

    r_pro = client.post("/api/v1/pro/nutrition/plate", json=payload, headers=_pro_headers())
    assert r_pro.status_code == 200, r_pro.text

    assert r_premium.json() == r_pro.json()


def test_week_flexible_is_deprecated_in_openapi(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    op = spec["paths"]["/api/v1/premium/plan/week-flexible"]["post"]
    assert op.get("deprecated") is True


def test_guard_divergence_targets_premium_is_legacy_guarded_pro_is_pro_tier_guarded(
    client: TestClient,
) -> None:
    payload = {
        "sex": "female",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    # Deprecated premium alias: legacy guard accepts API_KEY="test_key" in test session.
    r_premium = client.post("/api/v1/premium/targets", json=payload, headers=_premium_headers())
    assert r_premium.status_code == 200, r_premium.text

    # Canonical PRO endpoint: PRO tier guard rejects non-PRO keys (e.g. legacy "test_key").
    r_pro_wrong_key = client.post(
        "/api/v1/pro/nutrition/targets", json=payload, headers=_premium_headers()
    )
    assert r_pro_wrong_key.status_code == 403, r_pro_wrong_key.text

    r_pro = client.post("/api/v1/pro/nutrition/targets", json=payload, headers=_pro_headers())
    assert r_pro.status_code == 200, r_pro.text


def test_guard_divergence_plate_premium_is_legacy_guarded_pro_is_pro_tier_guarded(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "1")

    # Keep deterministic/fast: force fallback path for the plate implementation.
    import legacy_app

    monkeypatch.setattr(legacy_app, "make_plate", None, raising=False)
    monkeypatch.setattr(legacy_app, "calculate_all_bmr", None, raising=False)
    monkeypatch.setattr(legacy_app, "calculate_all_tdee", None, raising=False)

    payload = {
        "sex": "female",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    r_premium = client.post("/api/v1/premium/plate", json=payload, headers=_premium_headers())
    assert r_premium.status_code == 200, r_premium.text

    # Canonical PRO endpoint: PRO tier guard rejects non-PRO keys (e.g. legacy "test_key").
    r_pro_wrong_key = client.post(
        "/api/v1/pro/nutrition/plate", json=payload, headers=_premium_headers()
    )
    assert r_pro_wrong_key.status_code == 403, r_pro_wrong_key.text

    r_pro = client.post("/api/v1/pro/nutrition/plate", json=payload, headers=_pro_headers())
    assert r_pro.status_code == 200, r_pro.text
