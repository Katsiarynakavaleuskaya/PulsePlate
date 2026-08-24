"""VIP Guard Consistency Tests

RU: Тесты для проверки единообразного применения VIP tier guard на всех endpoints.
EN: Tests for consistent VIP tier guard enforcement across all endpoints.

This test suite ensures that all VIP endpoints enforce VIP tier access control
via require_vip_tier() middleware, not api-key-only guards.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP
from tests._helpers.vip_contracts import (
    assert_json_response_payload,
    build_auto_repair_weekly_request_payload,
    build_weekly_recipes_request_payload,
)
from tests.helpers.fitchef_runtime_helpers import make_mock_run_weekly_plan_task

HeaderFactory = Callable[[str], dict[str, str]]


@pytest.fixture
def headers_for_tier() -> HeaderFactory:
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
    headers_for_tier: HeaderFactory,
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
    headers_for_tier: HeaderFactory,
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
    "/api/v1/vip/shoplist/daily": {"items": [], "packaging_rules": None},
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
    headers_for_tier: HeaderFactory,
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
    headers_for_tier: HeaderFactory,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    """Test that POST endpoints allow VIP access and return 2xx.

    Mocks internal business calls to ensure stable 200 responses.
    """
    payload = POST_PAYLOADS[path]
    if path == "/api/v1/vip/recipes/weekly":
        payload = build_weekly_recipes_request_payload()
    elif path == "/api/v1/vip/auto-repair/weekly":
        payload = build_auto_repair_weekly_request_payload()

    # Mock internal calls for endpoints that require them
    if path == "/api/v1/vip/menu/weekly/plan":
        monkeypatch.setattr(
            "app.services.fitchef_runtime.run_weekly_plan_task",
            make_mock_run_weekly_plan_task(),
        )
    elif path == "/api/v1/vip/recipes/weekly":
        # Conditional mock: only return success for expected function name
        def mock_safe_call(func_name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
            if func_name == "synthesize_recipes_for_week":
                return {
                    "Monday": [
                        {
                            "recipe_id": "guard-recipe",
                            "title": "Guard Recipe",
                            "description": "Deterministic guard contract recipe",
                            "cuisine_type": "test",
                            "difficulty_level": "easy",
                            "prep_time_minutes": 0,
                            "cook_time_minutes": 0,
                            "total_time_minutes": 0,
                            "servings": 1,
                            "ingredients": [{"name": "rice", "amount": 100.0, "unit": "g"}],
                            "steps": [
                                {
                                    "step_number": 1,
                                    "instruction": "Serve the prepared ingredients",
                                }
                            ],
                            "nutrition_per_serving": {
                                "calories": 100.0,
                                "protein": 2.0,
                                "carbs": 20.0,
                                "fat": 1.0,
                            },
                            "tags": [],
                            "image_url": None,
                        }
                    ]
                }
            return {
                "status": "error",
                "code": "unexpected_call",
                "message": "unexpected adapter call",
            }

        monkeypatch.setattr("app.routers.vip._safe_call_with_adapter", mock_safe_call)
    elif path == "/api/v1/vip/auto-repair/weekly":
        auto_repair_payload = build_auto_repair_weekly_request_payload()

        # Mock auto_repair_week_plan function
        def mock_auto_repair(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {
                "status": "success",
                "repaired_plan": auto_repair_payload["week_plan"],
                "original_plan": auto_repair_payload["week_plan"],
                "changes_made": [],
                "remaining_gaps": {},
                "strategy_used": "balanced",
                "iterations": 0,
                "message": "Already compliant",
                "suggestions": [],
            }

        monkeypatch.setattr("app.routers.vip.get_auto_repair_engine", None)
        monkeypatch.setattr("app.routers.vip.auto_repair_week_plan", mock_auto_repair)
    # Echo mode endpoints (/menu/weekly/repair, /recipes/synthesize, /auto-repair/suggestions)
    # don't need mocks - they return echo immediately

    headers = headers_for_tier("VIP")
    resp = client.post(path, json=payload, headers=headers)
    if path in {
        "/api/v1/vip/recipes/weekly",
        "/api/v1/vip/auto-repair/weekly",
    }:
        assert resp.status_code == 200, resp.text
        response_payload = assert_json_response_payload(resp)
        assert response_payload["status"] == "success"
        assert response_payload["echo"] == payload
        if path == "/api/v1/vip/recipes/weekly":
            assert response_payload["total_recipes"] == 1
        else:
            assert response_payload["repair_result"]["status"] == "success"
    else:
        assert (
            200 <= resp.status_code < 300
        ), f"Expected 2xx for VIP tier on {path}, got {resp.status_code}: {resp.text}"
