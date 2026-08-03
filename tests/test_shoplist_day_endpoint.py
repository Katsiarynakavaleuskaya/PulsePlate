"""Tests for day shopping list endpoint (MVP placeholder).

RU: Тесты для эндпоинта списка покупок на день (MVP заглушка).
"""

from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from typing import Callable, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.api_tiers import require_pro_tier
from app.schemas.shopping_list import ShopAisle, ShopUnit
from tests._client import open_test_client


class _ClientBodyFailure(RuntimeError):
    """Sentinel raised while a managed fixture body owns the client."""


@contextmanager
def _open_pro_client(
    app_instance: FastAPI,
    override: Callable[..., object],
) -> Generator[TestClient, None, None]:
    """Temporarily install PRO access while preserving prior override ownership."""
    overrides_owner = app_instance.dependency_overrides
    overrides_snapshot = dict(overrides_owner)
    overrides_owner[require_pro_tier] = override
    try:
        with open_test_client(app_instance) as client:
            yield client
    finally:
        app_instance.dependency_overrides = overrides_owner
        overrides_owner.clear()
        overrides_owner.update(overrides_snapshot)


@pytest.fixture
def client_with_pro_access(app_module: ModuleType) -> Generator[TestClient, None, None]:
    """Create test client with PRO tier access bypassed.

    Uses canonical entrypoint (app.main:app) with observability bootstrap.
    """
    import app.main

    # Override PRO tier requirement for testing
    # Must be async and match signature (no params needed for override)
    async def _mock_pro_tier() -> str:
        return "test_key"

    app_instance = app.main.app
    with _open_pro_client(app_instance, _mock_pro_tier) as client:
        yield client


@pytest.mark.parametrize("body_fails", [False, True])
def test_pro_client_restores_preexisting_override(body_fails: bool) -> None:
    """Normal and exceptional client exit restore the exact prior override."""
    app_instance = FastAPI()

    async def original_override() -> str:
        return "original"

    async def fixture_override() -> str:
        return "fixture"

    overrides_owner = app_instance.dependency_overrides
    overrides_owner[require_pro_tier] = original_override

    if body_fails:
        with pytest.raises(_ClientBodyFailure):
            with _open_pro_client(app_instance, fixture_override):
                assert overrides_owner[require_pro_tier] is fixture_override
                raise _ClientBodyFailure("fixture body failed")
    else:
        with _open_pro_client(app_instance, fixture_override):
            assert overrides_owner[require_pro_tier] is fixture_override

    assert app_instance.dependency_overrides is overrides_owner
    assert overrides_owner == {require_pro_tier: original_override}


def test_shoplist_day_no_day_plan_returns_warning(client_with_pro_access):
    """When no day plan is available, return empty items and no_day_plan warning."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17&lang=ru")

    assert r.status_code == 200
    body = r.json()
    assert body["date"] == "2025-12-17"
    assert body["lang"] == "ru"
    assert body["items"] == []
    assert "no_day_plan" in body["warnings"]


def test_shoplist_day_default_lang(client_with_pro_access):
    """Test default language is 'en' when not specified."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17")

    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "en"
    assert body["warnings"] == ["no_day_plan"]


def test_shoplist_day_generates_items_when_plan_available(client_with_pro_access, monkeypatch):
    """When a day plan is available, endpoint returns non-empty items with valid aisles/units."""
    from typing import Any

    from app.routers import shoplist_day as shoplist_day_module

    day_plan: dict[str, Any] = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "oatmeal_banana",
                        "grams": {
                            "oats": 80.0,
                            "banana": 120.0,
                            "milk": 200.0,
                        },
                    }
                ]
            }
        ]
    }

    async def _fake_fetch_day_plan(day: str, pro_ctx: Any) -> dict[str, Any]:
        return day_plan

    monkeypatch.setattr(shoplist_day_module, "fetch_day_plan", _fake_fetch_day_plan)

    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17&lang=en")

    assert r.status_code == 200
    body = r.json()
    assert body["items"], "Expected non-empty items when day plan is available"
    assert body["warnings"] == []

    for item in body["items"]:
        assert item["qty"] > 0
        assert item["unit"] in {u.value for u in ShopUnit}
        assert item["aisle"] in {a.value for a in ShopAisle}


@pytest.mark.parametrize("lang_code", ["ru", "en", "es"])
def test_shoplist_day_all_supported_langs(client_with_pro_access, lang_code):
    """Test all supported language codes (ru/en/es) work correctly."""
    r = client_with_pro_access.get(f"/api/v1/pro/shoplist/day?date=2025-12-17&lang={lang_code}")

    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == lang_code
    assert body["date"] == "2025-12-17"
    assert isinstance(body["items"], list)


def test_shoplist_day_invalid_lang_422(client_with_pro_access):
    """Test invalid language code returns 422."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17&lang=de")

    assert r.status_code == 422


def test_shoplist_day_invalid_date_422(client_with_pro_access):
    """Test invalid date format returns 422."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=not-a-date&lang=ru")

    assert r.status_code == 422


def test_shoplist_day_missing_date_422(client_with_pro_access):
    """Test missing required date parameter returns 422."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?lang=ru")

    assert r.status_code == 422


def test_shoplist_day_requires_pro_tier(client: TestClient) -> None:
    """Test endpoint requires PRO tier authentication."""
    # Request without PRO tier override should fail
    r = client.get("/api/v1/pro/shoplist/day?date=2025-12-17&lang=ru")

    assert r.status_code in (401, 403)  # Either unauthorized or forbidden


def test_shoplist_day_url_correctness(client_with_pro_access):
    """Test that endpoint is accessible at documented URL path.

    Verifies correct URL works; old URL check is informational only
    (may become redirect/alias in future without breaking this test).
    """
    # Correct URL must work
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17")
    assert r.status_code == 200
    assert r.json()["date"] == "2025-12-17"

    # Document that old prefix doesn't exist (may change if alias added)
    r_old = client_with_pro_access.get("/api/v1/pro/meal/shoplist/day?date=2025-12-17")
    # Currently 404, but could become 301/302 redirect in future
    assert r_old.status_code in (404, 301, 302, 308)  # Not found or redirect
