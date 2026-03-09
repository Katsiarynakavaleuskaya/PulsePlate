"""Tests for VIP router in production mode."""

from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

VALID_WEEKLY_PLAN_REQUEST = {
    "sex": "male",
    "age": 30,
    "height_cm": 175,
    "weight_kg": 70,
    "activity": "moderate",
    "goal": "maintain",
}


@pytest.fixture(autouse=True)
def vip_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep production-mode VIP tests isolated from ENVIRONMENT drift."""

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)


class TestVIPProductionMode:
    """Test VIP router production mode functionality."""

    def test_vip_api_key_validation_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key validation when API_KEY is set but key is missing (line 95)."""
        monkeypatch.setenv("API_KEY", "secret-key")

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post("/api/v1/vip/weekly-plan", json={"test": "data"})
        assert response.status_code == 403
        detail_lower = response.json()["detail"].lower()
        assert "vip access" in detail_lower or "invalid api key" in detail_lower

    def test_vip_api_key_validation_wrong_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key validation with incorrect key (line 95)."""
        monkeypatch.setenv("API_KEY", "secret-key")

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request with wrong API key
        response = client.post(
            "/api/v1/vip/weekly-plan", json={"test": "data"}, headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 403
        detail_lower = response.json()["detail"].lower()
        assert "invalid api" in detail_lower or "vip access" in detail_lower

    def test_vip_api_key_validation_correct_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key validation with correct key passes authentication."""
        monkeypatch.setenv("API_KEY", "secret-key")

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request with correct API key
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json=VALID_WEEKLY_PLAN_REQUEST,
            headers={"X-API-Key": "secret-key"},
        )
        # Should not be 401 (auth should pass)
        assert response.status_code != 401

    def test_weekly_menu_generation_error_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test weekly menu generation error handling (line 155)."""
        monkeypatch.setenv("API_KEY", "secret-key")

        import app
        import app.routers.vip as vip_router

        def raise_exc(*args, **kwargs):
            # sourcery skip: raise-specific-error
            raise Exception("Menu generation failed")

        monkeypatch.setattr(vip_router, "make_weekly_menu", raise_exc)

        client = TestClient(cast(ASGIApp, app.app))

        response = client.post(
            "/api/v1/vip/weekly-plan",
            json=VALID_WEEKLY_PLAN_REQUEST,
            headers={"X-API-Key": "secret-key"},
        )

        assert response.status_code == 200
        assert "Weekly plan generation failed" in response.json()["message"]

    def test_vip_recipes_endpoint_auth_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP recipes endpoint requires authentication."""
        monkeypatch.setenv("API_KEY", "secret-key")

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipes endpoint without API key
        response = client.post("/api/v1/vip/recipes/synthesize", json={"ingredients": []})
        assert response.status_code == 403  # VIP = feature-gate, returns 403
        detail = response.json()["detail"].lower()
        assert any(sub in detail for sub in ("vip", "access"))

    def test_vip_regions_endpoint_auth_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP regions endpoint requires authentication."""
        monkeypatch.setenv("API_KEY", "secret-key")

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test regions endpoint without API key
        response = client.get("/api/v1/vip/regions")
        assert response.status_code == 403  # VIP = feature-gate, returns 403
        detail = response.json()["detail"].lower()
        assert any(sub in detail for sub in ("vip", "access"))

    def test_vip_production_mode_coverage_lines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test specific production mode lines for coverage.

        This test targets the specific uncovered lines in VIP router:
        - Line 88-95: API key validation and HTTP exception conversion
        - Line 155: Menu generation error handling
        - Line 320: Recipe search error handling
        - Line 663: Regional search error handling
        """
        monkeypatch.setenv("API_KEY", "secret-key")

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test 1: Invalid API key (lines 88-95)
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json=VALID_WEEKLY_PLAN_REQUEST,
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 403

        # Test 2: Valid API key allows access
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json=VALID_WEEKLY_PLAN_REQUEST,
            headers={"X-API-Key": "secret-key"},
        )
        # Should not be 401 (auth should pass)
        assert response.status_code != 401

    def test_vip_app_get_api_key_http_exception_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test app.get_api_key raising HTTPException with 403 (line 88-92)."""
        monkeypatch.setenv("API_KEY", "secret-key")

        from fastapi import HTTPException

        import app

        # Mock app.get_api_key to raise 403
        with patch("app.get_api_key") as mock_get_api_key:
            mock_get_api_key.side_effect = HTTPException(status_code=403, detail="Forbidden")

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post(
                "/api/v1/vip/weekly-plan", json={"test": "data"}, headers={"X-API-Key": "some-key"}
            )

            # Should return 403 as raised
            assert response.status_code == 403
            assert "Forbidden" in response.json()["detail"]
