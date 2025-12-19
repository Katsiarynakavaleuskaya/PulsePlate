"""Tests for day shopping list endpoint (MVP placeholder).

RU: Тесты для эндпоинта списка покупок на день (MVP заглушка).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import require_pro_tier
from app.schemas.shopping_list import ShopAisle, ShopUnit


@pytest.fixture
def client_with_pro_access(app_module: ModuleType):
    """Create test client with PRO tier access bypassed.

    Uses app_module fixture from conftest for better test isolation.
    """
    # Override PRO tier requirement for testing
    app_module.app.dependency_overrides[require_pro_tier] = lambda: "test_api_key"

    client = TestClient(app_module.app)
    yield client

    # Cleanup: remove override after test
    app_module.app.dependency_overrides.pop(require_pro_tier, None)


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
    from app.routers import shoplist_day as shoplist_day_module

    day_plan = {
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

    async def _fake_fetch_day_plan(day, pro_ctx):  # type: ignore[unused-argument]
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


def test_shoplist_day_requires_pro_tier(app_module: ModuleType):
    """Test endpoint requires PRO tier authentication."""
    client = TestClient(app_module.app)

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
