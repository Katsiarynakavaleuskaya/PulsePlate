"""PR-519 parity tests: deprecated premium aliases match canonical PRO contracts.

These tests intentionally avoid asserting business correctness; they assert that
deprecated `/api/v1/premium/*` endpoints are thin proxies to canonical `/api/v1/pro/*`
contracts (same request → same response).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO


def _normalize_422_detail(detail: Any) -> Any:
    if not isinstance(detail, list):
        return detail

    normalized: list[dict[str, Any]] = []
    for entry in detail:
        if not isinstance(entry, dict):
            continue
        normalized_entry: dict[str, Any] = dict(entry)
        normalized_entry.pop("url", None)

        loc = normalized_entry.get("loc")
        if isinstance(loc, (list, tuple)) and list(loc)[:1] == ["body"]:
            normalized_entry["loc"] = list(loc)[1:]

        normalized.append(normalized_entry)

    normalized.sort(key=lambda e: (tuple(e.get("loc") or ()), e.get("type", "")))
    return normalized


def _normalized_422_json(response: Any) -> dict[str, Any]:
    payload = response.json()
    if not isinstance(payload, dict):
        return {"detail": payload}

    if "detail" not in payload:
        return payload

    normalized = dict(payload)
    normalized["detail"] = _normalize_422_detail(normalized["detail"])
    return normalized


def _premium_headers() -> dict[str, str]:
    return {"X-API-Key": "test_key"}  # pragma: allowlist secret


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

    r_premium = client.post("/api/v1/premium/targets", json=payload, headers=_premium_headers())
    assert r_premium.status_code == 200, r_premium.text

    # Canonical PRO endpoint: PRO tier guard rejects non-PRO tier headers.
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

    # Canonical PRO endpoint: PRO tier guard rejects non-PRO tier headers.
    r_pro_wrong_key = client.post(
        "/api/v1/pro/nutrition/plate", json=payload, headers=_premium_headers()
    )
    assert r_pro_wrong_key.status_code == 403, r_pro_wrong_key.text

    r_pro = client.post("/api/v1/pro/nutrition/plate", json=payload, headers=_pro_headers())
    assert r_pro.status_code == 200, r_pro.text


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {
            "age": 0,
            "sex": "female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "light",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": "en",
        },
        {
            "age": 25,
            "sex": "female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "light",
            "goal": "invalid_goal",
            "life_stage": "adult",
            "lang": "en",
        },
        {
            "age": 25,
            "sex": "female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "light",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": "en",
            "unexpected_field": "value",
        },
    ],
)
def test_premium_targets_422_parity_pro_targets(
    client: TestClient, invalid_payload: dict[str, object]
) -> None:
    """Parity test: premium and PRO targets return same 422 errors for invalid payloads."""
    r_premium = client.post(
        "/api/v1/premium/targets", json=invalid_payload, headers=_premium_headers()
    )
    assert r_premium.status_code == 422, r_premium.text

    r_pro = client.post(
        "/api/v1/pro/nutrition/targets", json=invalid_payload, headers=_pro_headers()
    )
    assert r_pro.status_code == 422, r_pro.text

    # Thin proxy invariant: same semantic validation errors (normalized for FastAPI/Pydantic v2 shape).
    assert _normalized_422_json(r_premium) == _normalized_422_json(r_pro)


@pytest.mark.parametrize(
    "endpoint_path",
    [
        "/api/v1/premium/targets",
        "/api/v1/premium/plate",
        "/api/v1/premium/plan/week",
        "/api/v1/premium/plan/week-flexible",
    ],
)
def test_premium_endpoints_hidden_from_openapi(client: TestClient, endpoint_path: str) -> None:
    """Assert deprecated premium aliases are hidden from canonical OpenAPI schema."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    spec = r.json()
    assert endpoint_path not in spec["paths"], f"{endpoint_path} must be hidden from OpenAPI"
