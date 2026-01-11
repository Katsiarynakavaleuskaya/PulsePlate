"""VIP Guard Consistency Tests

RU: Тесты для проверки единообразного применения VIP tier guard на всех endpoints.
EN: Tests for consistent VIP tier guard enforcement across all endpoints.

This test suite ensures that all VIP endpoints enforce VIP tier access control
via require_vip_tier() middleware, not api-key-only guards.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP


@pytest.fixture
def api_key_for_tier(monkeypatch: pytest.MonkeyPatch):
    """Return API key for tier.

    RU: Возвращает API ключ для указанного tier.
    EN: Returns API key for specified tier.

    For FREE tier, uses TEST_KEY_PRO (which doesn't grant VIP access).
    This ensures we test tier denial (403), not "unknown key" behavior.
    """
    def _get_key(tier: str) -> str:
        if tier == "VIP":
            return TEST_KEY_VIP
        elif tier == "PRO":
            return TEST_KEY_PRO
        elif tier == "FREE":
            # Use PRO key for FREE tests (it's valid but doesn't grant VIP)
            # This ensures we get 403 "tier denial", not "unknown key"
            return TEST_KEY_PRO
        else:
            raise ValueError(f"Unknown tier: {tier}")
    return _get_key


def _fill_path_params(url: str) -> str:
    """Fill path parameters with test values."""
    return (
        url.replace("{region}", "es")
        .replace("{product_name}", "milk")
    )


# GET endpoints (9 total)
VIP_ENDPOINTS_GET = [
    "/api/v1/vip/health",
    "/api/v1/vip/shoplist/formats",
    "/api/v1/vip/regions",
    "/api/v1/vip/regions/{region}/search",
    "/api/v1/vip/regions/{region}/categories",
    "/api/v1/vip/regions/{region}/stores",
    "/api/v1/vip/regions/compare/{product_name}",
    "/api/v1/vip/recipes/templates",
    "/api/v1/vip/auto-repair/strategies",
]


@pytest.mark.parametrize("path", VIP_ENDPOINTS_GET)
@pytest.mark.parametrize("tier,expected", [
    ("FREE", 403),
    ("PRO", 403),
])
def test_vip_guard_get_denies_non_vip(
    client: TestClient,
    api_key_for_tier,
    path: str,
    tier: str,
    expected: int,
) -> None:
    """Test that GET endpoints deny access to FREE/PRO tiers."""
    key = api_key_for_tier(tier)
    actual_path = _fill_path_params(path)
    # Add query params for search endpoint
    if "{region}/search" in path:
        actual_path = f"{actual_path}?query=test"
    resp = client.get(actual_path, headers={"X-API-Key": key})
    assert resp.status_code == expected, f"Expected {expected} for {tier} tier on {path}, got {resp.status_code}: {resp.text}"
    if expected == 403:
        assert "VIP" in resp.json().get("detail", "").upper() or "forbidden" in resp.json().get("detail", "").lower()


@pytest.mark.parametrize("path", VIP_ENDPOINTS_GET)
def test_vip_guard_get_allows_vip(
    client: TestClient,
    api_key_for_tier,
    path: str,
) -> None:
    """Test that GET endpoints allow access to VIP tier."""
    key = api_key_for_tier("VIP")
    actual_path = _fill_path_params(path)
    # Add query params for search endpoint
    if "{region}/search" in path:
        actual_path = f"{actual_path}?query=test"
    resp = client.get(actual_path, headers={"X-API-Key": key})
    assert resp.status_code < 400, f"Expected 2xx for VIP tier on {path}, got {resp.status_code}: {resp.text}"


# POST endpoints (8 total)
VIP_ENDPOINTS_POST = [
    "/api/v1/vip/menu/weekly/plan",
    "/api/v1/vip/menu/weekly/repair",
    "/api/v1/vip/shoplist/weekly",
    "/api/v1/vip/shoplist/daily",
    "/api/v1/vip/recipes/synthesize",
    "/api/v1/vip/recipes/weekly",
    "/api/v1/vip/auto-repair/weekly",
    "/api/v1/vip/auto-repair/suggestions",
]

# Minimal payloads for POST endpoints (explicit, no autogen)
POST_PAYLOADS = {
    "/api/v1/vip/menu/weekly/plan": {
        "sex": "male",
        "age": 30,
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "activity": "moderate",
        "goal": "maintain",
    },
    "/api/v1/vip/menu/weekly/repair": {"week_plan": {}},
    "/api/v1/vip/shoplist/weekly": {"days": []},
    "/api/v1/vip/shoplist/daily": {"day_plan": {}},
    "/api/v1/vip/recipes/synthesize": {"ingredients": []},
    "/api/v1/vip/recipes/weekly": {"week_plan": {}, "recipes_per_day": 1},
    "/api/v1/vip/auto-repair/weekly": {"week_plan": {}, "targets": {}},
    "/api/v1/vip/auto-repair/suggestions": {"week_plan": {}, "targets": {}},
}


@pytest.mark.parametrize("path", VIP_ENDPOINTS_POST)
@pytest.mark.parametrize("tier,expected", [
    ("FREE", 403),
    ("PRO", 403),
])
def test_vip_guard_post_denies_non_vip(
    client: TestClient,
    api_key_for_tier,
    path: str,
    tier: str,
    expected: int,
) -> None:
    """Test that POST endpoints deny access to FREE/PRO tiers."""
    key = api_key_for_tier(tier)
    payload = POST_PAYLOADS[path]
    resp = client.post(path, json=payload, headers={"X-API-Key": key})
    assert resp.status_code == expected, f"Expected {expected} for {tier} tier on {path}, got {resp.status_code}: {resp.text}"
    if expected == 403:
        assert "VIP" in resp.json().get("detail", "").upper() or "forbidden" in resp.json().get("detail", "").lower()


@pytest.mark.parametrize("path", VIP_ENDPOINTS_POST)
def test_vip_guard_post_allows_vip_and_returns_2xx(
    client: TestClient,
    api_key_for_tier,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    """Test that POST endpoints allow VIP access and return 2xx.

    Mocks internal business calls to ensure stable 200 responses.
    """
    # Mock internal calls for endpoints that require them
    if path == "/api/v1/vip/menu/weekly/plan":
        monkeypatch.setattr(
            "app.routers.vip._safe_call_with_adapter",
            lambda func_name, **kwargs: {"status": "success", "menu": {"days": []}},
        )
    elif path == "/api/v1/vip/shoplist/weekly":
        monkeypatch.setattr("app.routers.vip.format_export", lambda data, **kwargs: [])
    elif path == "/api/v1/vip/shoplist/daily":
        monkeypatch.setattr("app.routers.vip.format_export", lambda data, **kwargs: [])
    elif path == "/api/v1/vip/recipes/weekly":
        monkeypatch.setattr(
            "app.routers.vip._safe_call_with_adapter",
            lambda func_name, *args, **kwargs: {"monday": [{"recipe_id": "test", "name": "Test Recipe"}]},
        )
    elif path == "/api/v1/vip/auto-repair/weekly":
        monkeypatch.setattr(
            "app.routers.vip.auto_repair_week_plan",
            lambda *args, **kwargs: {
                "status": "repaired",
                "repaired_plan": {},
                "original_plan": {},
                "changes_made": [],
                "remaining_gaps": [],
            },
        )
    # Echo mode endpoints (/menu/weekly/repair, /recipes/synthesize, /auto-repair/suggestions)
    # don't need mocks - they return echo immediately

    key = api_key_for_tier("VIP")
    payload = POST_PAYLOADS[path]
    resp = client.post(path, json=payload, headers={"X-API-Key": key})
    assert 200 <= resp.status_code < 300, f"Expected 2xx for VIP tier on {path}, got {resp.status_code}: {resp.text}"
