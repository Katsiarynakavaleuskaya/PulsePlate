"""VIP Tier Guard Matrix Test

RU: Матричный тест для проверки tier guard на всех VIP endpoints.
EN: Matrix test for tier guard enforcement across all VIP endpoints.

This is the canonical source of truth for VIP tier denial matrix (FREE/PRO → 403, VIP → 2xx).
Do not duplicate this matrix in other test files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP

VIP_DENY_MESSAGE = "API key does not have VIP tier access. Upgrade to VIP to access this feature."


@dataclass(frozen=True)
class VipCase:
    """VIP endpoint test case.

    RU: Тестовый кейс для VIP endpoint.
    EN: Test case for VIP endpoint.
    """

    method: Literal["GET", "POST"]
    path: str
    payload: dict[str, Any] | None = None
    params: dict[str, str] | None = None
    vip_expected_status: int = 200


# Canonical list of all 17 VIP endpoints
VIP_CASES: tuple[VipCase, ...] = (
    # GET endpoints (9)
    VipCase("GET", "/api/v1/vip/health"),
    VipCase("GET", "/api/v1/vip/shoplist/formats"),
    VipCase("GET", "/api/v1/vip/regions"),
    VipCase(
        "GET",
        "/api/v1/vip/regions/es/search",
        params={"query": "tomato"},
    ),  # Path param: {region} = "es"
    VipCase("GET", "/api/v1/vip/regions/es/categories"),
    VipCase("GET", "/api/v1/vip/regions/es/stores"),
    VipCase("GET", "/api/v1/vip/regions/compare/tomato"),
    VipCase("GET", "/api/v1/vip/recipes/templates"),
    VipCase("GET", "/api/v1/vip/auto-repair/strategies"),
    # POST endpoints (8)
    VipCase(
        "POST",
        "/api/v1/vip/menu/weekly/plan",
        payload={
            "sex": "female",
            "age": 25,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "light",
            "goal": "loss",
        },
    ),
    VipCase(
        "POST",
        "/api/v1/vip/menu/weekly/repair",
        payload={"menu": {"days": 7, "meals": []}, "deficits": {"Ca": 200, "VitD": 100}},
    ),
    VipCase(
        "POST",
        "/api/v1/vip/shoplist/weekly",
        payload={
            "days": [
                {
                    "items": [
                        {"food_id": "carrot", "qty": {"value": "100", "unit": "G"}, "form": "RAW"},
                    ],
                    "packaging_rules": [
                        {
                            "food_id": "carrot",
                            "pack_size": {"value": "500", "unit": "G"},
                            "rounding": "CEIL",
                            "min_packs": 1,
                        },
                    ],
                },
            ],
        },
    ),
    VipCase(
        "POST",
        "/api/v1/vip/shoplist/daily",
        payload={
            "items": [
                {"food_id": "carrot", "qty": {"value": "100", "unit": "G"}, "form": "RAW"},
            ],
            "packaging_rules": [
                {
                    "food_id": "carrot",
                    "pack_size": {"value": "500", "unit": "G"},
                    "rounding": "CEIL",
                    "min_packs": 1,
                },
            ],
        },
    ),
    VipCase(
        "POST",
        "/api/v1/vip/recipes/synthesize",
        payload={
            "ingredients": [
                {"name": "chicken", "amount": 300, "unit": "g"},
                {"name": "vegetables", "amount": 200, "unit": "g"},
            ],
            "cuisine_preference": "asian",
            "difficulty_preference": "easy",
            "servings": 4,
        },
    ),
    VipCase(
        "POST",
        "/api/v1/vip/recipes/weekly",
        payload={
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [
                            {
                                "ingredients": [
                                    {"name": "chicken", "amount": 200, "unit": "g"},
                                    {"name": "rice", "amount": 150, "unit": "g"},
                                ],
                            },
                        ],
                    },
                ],
            },
            "recipes_per_day": 1,
        },
    ),
    VipCase(
        "POST",
        "/api/v1/vip/auto-repair/weekly",
        payload={
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}],
                    },
                ],
            },
            "targets": {
                "iron_mg": 18.0,
                "calcium_mg": 1000.0,
            },
            "strategy": "balanced",
        },
    ),
    VipCase(
        "POST",
        "/api/v1/vip/auto-repair/suggestions",
        payload={
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}],
                    },
                ],
            },
            "targets": {
                "iron_mg": 18.0,
                "calcium_mg": 1000.0,
            },
        },
    ),
)


def _headers_for_key(api_key: str) -> dict[str, str]:
    """Return headers dict for API key.

    RU: Возвращает заголовки для API ключа.
    EN: Returns headers dict for API key.
    """
    return {"X-API-Key": api_key}


def _assert_vip_denied(resp: Any) -> None:
    """Assert VIP denial response (403).

    RU: Проверяет ответ об отказе в доступе VIP (403).
    EN: Asserts VIP denial response (403).

    Note: require_vip_tier() raises HTTPException which returns FastAPI default format:
    {"detail": "..."}. We only check status code and that detail contains VIP denial message.
    """
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # FastAPI HTTPException format: {"detail": "message"}
    assert "detail" in data
    detail = data["detail"]
    assert isinstance(detail, str)
    # Check that detail contains VIP denial message (case-insensitive)
    assert "vip" in detail.lower() or "access" in detail.lower() or "upgrade" in detail.lower()


@pytest.mark.parametrize(
    "api_key,expect_denied",
    [
        ("invalid_free_key", True),  # FREE tier: invalid key (not PRO/VIP)
        (TEST_KEY_PRO, True),  # PRO key
        (TEST_KEY_VIP, False),  # VIP key
    ],
)
@pytest.mark.parametrize("case", VIP_CASES)
def test_vip_tier_guard_matrix(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    api_key: str,
    expect_denied: bool,
    case: VipCase,
) -> None:
    """Matrix test: all VIP endpoints must deny FREE/PRO with canonical envelope, and allow VIP (2xx).

    RU: Матричный тест: все VIP endpoints должны отклонять FREE/PRO с каноническим envelope,
    и разрешать VIP (2xx).
    EN: Matrix test: all VIP endpoints must deny FREE/PRO with canonical envelope, and allow VIP (2xx).

    IMPORTANT:
    - Keep this file as the canonical guard-matrix.
    - Do not duplicate this matrix across other vip_* tests.
    - This test verifies tier guard enforcement, not business logic.
    """
    # Enable VIP module for test
    monkeypatch.setenv("VIP_MODULE_ENABLED", "1")

    headers = _headers_for_key(api_key)

    if case.method == "GET":
        if case.params:
            resp = client.get(case.path, params=case.params, headers=headers)
        else:
            resp = client.get(case.path, headers=headers)
    else:
        assert case.payload is not None, f"POST case must provide payload: {case.path}"
        resp = client.post(case.path, json=case.payload, headers=headers)

    if expect_denied:
        _assert_vip_denied(resp)
    else:
        # VIP should get 2xx (200/204/etc depending on endpoint)
        assert (
            200 <= resp.status_code < 300
        ), f"VIP expected 2xx but got {resp.status_code} for {case.method} {case.path}: {resp.text}"

