"""VIP Guard Consistency Tests

RU: Тесты для проверки единообразного применения VIP tier guard на всех endpoints.
EN: Tests for consistent VIP tier guard enforcement across all endpoints.

This test suite ensures that all VIP endpoints enforce VIP tier access control
via require_vip_tier() middleware, not api-key-only guards.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP


@pytest.fixture
def headers_for_tier():
    """Return headers dict for tier.

    RU: Возвращает заголовки для указанного tier.
    EN: Returns headers dict for specified tier.

    For FREE tier, returns empty dict (no API key header) - FREE = no key required.
    For PRO/VIP, returns X-API-Key header with respective test key.
    """

    def _get_headers(tier: str) -> dict[str, str]:
        if tier == "VIP":
            return {"X-API-Key": TEST_KEY_VIP}
        elif tier == "PRO":
            return {"X-API-Key": TEST_KEY_PRO}
        elif tier == "FREE":
            return {}  # No API key header - FREE tier doesn't require a key
        else:
            raise ValueError(f"Unknown tier: {tier}")

    return _get_headers


def _fill_path_params(url: str) -> str:
    """Fill path parameters with test values."""
    return url.replace("{region}", "es").replace("{product_name}", "milk")


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
@pytest.mark.parametrize(
    "tier,expected",
    [
        ("FREE", 403),
        ("PRO", 403),
    ],
)
def test_vip_guard_get_denies_non_vip(
    client: TestClient,
    headers_for_tier,
    path: str,
    tier: str,
    expected: int,
) -> None:
    """Test that GET endpoints deny access to FREE/PRO tiers."""
    headers = headers_for_tier(tier)
    actual_path = _fill_path_params(path)
    # Add query params for search endpoint
    if "{region}/search" in path:
        actual_path = f"{actual_path}?query=test"
    resp = client.get(actual_path, headers=headers)
    assert (
        resp.status_code == expected
    ), f"Expected {expected} for {tier} tier on {path}, got {resp.status_code}: {resp.text}"
    # Guard contract tests: only check status code, not response body details


@pytest.mark.parametrize("path", VIP_ENDPOINTS_GET)
def test_vip_guard_get_allows_vip(
    client: TestClient,
    headers_for_tier,
    path: str,
) -> None:
    """Test that GET endpoints allow access to VIP tier."""
    headers = headers_for_tier("VIP")
    actual_path = _fill_path_params(path)
    # Add query params for search endpoint
    if "{region}/search" in path:
        actual_path = f"{actual_path}?query=test"
    resp = client.get(actual_path, headers=headers)
    assert (
        resp.status_code < 400
    ), f"Expected 2xx for VIP tier on {path}, got {resp.status_code}: {resp.text}"


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
@pytest.mark.parametrize(
    "tier,expected",
    [
        ("FREE", 403),
        ("PRO", 403),
    ],
)
def test_vip_guard_post_denies_non_vip(
    client: TestClient,
    headers_for_tier,
    path: str,
    tier: str,
    expected: int,
) -> None:
    """Test that POST endpoints deny access to FREE/PRO tiers."""
    headers = headers_for_tier(tier)
    payload = POST_PAYLOADS[path]
    resp = client.post(path, json=payload, headers=headers)
    assert (
        resp.status_code == expected
    ), f"Expected {expected} for {tier} tier on {path}, got {resp.status_code}: {resp.text}"
    # Guard contract tests: only check status code, not response body details


@pytest.mark.parametrize("path", VIP_ENDPOINTS_POST)
def test_vip_guard_post_allows_vip_and_returns_2xx(
    client: TestClient,
    headers_for_tier,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    """Test that POST endpoints allow VIP access and return 2xx.

    Mocks internal business calls to ensure stable 200 responses.
    """
    # Mock internal calls for endpoints that require them
    if path == "/api/v1/vip/menu/weekly/plan":
        # Conditional mock: only return success for expected function name
        def mock_safe_call(func_name: str, **kwargs: Any) -> dict[str, Any]:
            if func_name == "make_weekly_menu":
                return {"status": "success", "menu": {"days": []}}
            return {
                "status": "error",
                "code": "unexpected_call",
                "message": "unexpected adapter call",
            }

        monkeypatch.setattr("app.routers.vip._safe_call_with_adapter", mock_safe_call)
    elif path == "/api/v1/vip/shoplist/weekly":
        # Mock all three functions in the chain
        monkeypatch.setattr("app.routers.vip.aggregate_ingredients", lambda req: [])
        monkeypatch.setattr("app.routers.vip.round_to_packages", lambda aggregated: [])
        monkeypatch.setattr("app.routers.vip.format_export", lambda shopping_list, **kwargs: [])
    elif path == "/api/v1/vip/shoplist/daily":
        # Mock all three functions in the chain
        monkeypatch.setattr("app.routers.vip.aggregate_ingredients", lambda req: [])
        monkeypatch.setattr("app.routers.vip.round_to_packages", lambda aggregated: [])
        monkeypatch.setattr("app.routers.vip.format_export", lambda shopping_list, **kwargs: [])
    elif path == "/api/v1/vip/recipes/weekly":
        # Conditional mock: only return success for expected function name
        def mock_safe_call(func_name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
            if func_name == "synthesize_recipes_for_week":
                return {"monday": [{"recipe_id": "test", "name": "Test Recipe"}]}
            return {
                "status": "error",
                "code": "unexpected_call",
                "message": "unexpected adapter call",
            }

        monkeypatch.setattr("app.routers.vip._safe_call_with_adapter", mock_safe_call)
    elif path == "/api/v1/vip/auto-repair/weekly":
        # Mock MicronutrientTargets to avoid validation errors with empty dict
        # Use simple lambda instead of MagicMock for guard tests
        monkeypatch.setattr("core.targets.MicronutrientTargets", lambda **_: object())

        # Mock auto_repair_week_plan function
        def mock_auto_repair(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {
                "status": "repaired",
                "repaired_plan": {},
                "original_plan": {},
                "changes_made": [],
                "remaining_gaps": [],
            }

        monkeypatch.setattr("app.routers.vip.auto_repair_week_plan", mock_auto_repair)
    # Echo mode endpoints (/menu/weekly/repair, /recipes/synthesize, /auto-repair/suggestions)
    # don't need mocks - they return echo immediately

    headers = headers_for_tier("VIP")
    payload = POST_PAYLOADS[path]
    resp = client.post(path, json=payload, headers=headers)
    assert (
        200 <= resp.status_code < 300
    ), f"Expected 2xx for VIP tier on {path}, got {resp.status_code}: {resp.text}"
