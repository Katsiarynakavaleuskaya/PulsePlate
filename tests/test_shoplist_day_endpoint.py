"""Tests for day shopping list endpoint (MVP placeholder).

RU: Тесты для эндпоинта списка покупок на день (MVP заглушка).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Import app and dependency
import app as app_module
from app.middleware.api_tiers import require_pro_tier


@pytest.fixture
def client_with_pro_access():
    """Create test client with PRO tier access bypassed."""
    # Override PRO tier requirement for testing
    app_module.app.dependency_overrides[require_pro_tier] = lambda: "test_api_key"

    client = TestClient(app_module.app)
    yield client

    # Cleanup: remove override after test
    app_module.app.dependency_overrides.pop(require_pro_tier, None)


def test_shoplist_day_ok(client_with_pro_access):
    """Test successful day shoplist request returns empty placeholder."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17&lang=ru")

    assert r.status_code == 200
    body = r.json()
    assert body["date"] == "2025-12-17"
    assert body["lang"] == "ru"
    assert body["items"] == []
    assert body["warnings"] == []


def test_shoplist_day_default_lang(client_with_pro_access):
    """Test default language is 'en' when not specified."""
    r = client_with_pro_access.get("/api/v1/pro/shoplist/day?date=2025-12-17")

    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "en"


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


def test_shoplist_day_requires_pro_tier():
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
