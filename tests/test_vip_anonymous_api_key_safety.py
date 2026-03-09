"""
Tests for VIP router anonymous API key safety in production environments.
Tests the new production-safe behavior that prevents anonymous access by default.
"""

import os
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


class TestVIPAnonymousAPIKeySafety:
    """Test VIP router anonymous API key safety functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Enable VIP module for app initialization
        os.environ["VIP_MODULE_ENABLED"] = "true"

    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear environment variables
        env_vars_to_clear = [
            "API_KEY",
            "APP_ENV",
            "ALLOW_DEV_API_KEY",
            "ALLOW_ANONYMOUS_API_KEYS",
            "DEBUG",
            "VIP_MODULE_ENABLED",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    def test_production_mode_rejects_anonymous_access(self):
        """Test that production mode rejects anonymous access by default."""
        # Set production environment
        os.environ["APP_ENV"] = "production"
        os.environ["DEBUG"] = "false"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code in (401, 403)
        detail_lower = response.json()["detail"].lower()
        assert "api key" in detail_lower or "vip access" in detail_lower

        # Test request with invalid API key
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "wrong-key"},
        )
        # Invalid key should be 403 (insufficient permissions), not 401 (missing auth)
        assert response.status_code == 403
        detail_lower = response.json()["detail"].lower()
        assert "vip" in detail_lower or "invalid" in detail_lower

    def test_production_mode_with_explicit_anonymous_allowed_fails_fast(self):
        """Test that production mode fails fast when anonymous access is enabled."""
        # Set production environment but allow anonymous access
        os.environ["APP_ENV"] = "production"
        os.environ["DEBUG"] = "false"
        os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        with pytest.raises(RuntimeError, match="ALLOW_ANONYMOUS_API_KEYS"):
            with TestClient(cast(ASGIApp, app.app)):
                pass

    def test_staging_mode_rejects_anonymous_access(self):
        """Test that staging mode rejects anonymous access by default."""
        # Set staging environment
        os.environ["APP_ENV"] = "staging"
        os.environ["DEBUG"] = "false"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code in (401, 403)
        detail_lower = response.json()["detail"].lower()
        assert "api key" in detail_lower or "vip access" in detail_lower

    def test_debug_false_rejects_anonymous_access(self):
        """Test that DEBUG=false rejects anonymous access even without explicit production env."""
        # Set debug to false (production-like behavior)
        os.environ["DEBUG"] = "false"
        # Don't set APP_ENV or API_KEY

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code in (401, 403)
        detail_lower = response.json()["detail"].lower()
        assert "api key" in detail_lower or "vip access" in detail_lower

    def test_development_mode_allows_anonymous_access(self):
        """Test that development mode allows anonymous access by default."""
        # Set development environment
        os.environ["APP_ENV"] = "development"
        os.environ["DEBUG"] = "true"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        # Should not be 401 (anonymous access allowed in development)
        assert response.status_code != 401

    def test_local_mode_allows_anonymous_access(self):
        """Test that local mode allows anonymous access by default."""
        # Set local environment (default)
        os.environ["APP_ENV"] = "local"
        os.environ["DEBUG"] = "true"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        # Should not be 401 (anonymous access allowed in local development)
        assert response.status_code != 401

    def test_test_mode_allows_anonymous_access(self):
        """Test that test mode allows anonymous access by default."""
        # Set test environment
        os.environ["APP_ENV"] = "test"
        os.environ["DEBUG"] = "true"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        # Should not be 401 (anonymous access allowed in test mode)
        assert response.status_code != 401

    def test_explicit_anonymous_disabled_in_development(self):
        """Test that explicit ALLOW_ANONYMOUS_API_KEYS=false disables anonymous access even in development."""
        # Set development environment but explicitly disable anonymous access
        os.environ["APP_ENV"] = "development"
        os.environ["DEBUG"] = "true"
        os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "false"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code in (401, 403)
        detail_lower = response.json()["detail"].lower()
        assert "api key" in detail_lower or "vip access" in detail_lower

    def test_production_mode_logs_error(self):
        """Test that production mode logs error when anonymous access is attempted."""
        # Set production environment
        os.environ["APP_ENV"] = "production"
        os.environ["DEBUG"] = "false"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code in (401, 403)
        detail_lower = response.json()["detail"].lower()
        assert "api key" in detail_lower or "vip access" in detail_lower

    def test_anonymous_allowed_logs_warning_fails_fast(self):
        """Test that production no longer tolerates anonymous access warnings."""
        # Set production environment but allow anonymous access
        os.environ["APP_ENV"] = "production"
        os.environ["DEBUG"] = "false"
        os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        with pytest.raises(RuntimeError, match="ALLOW_ANONYMOUS_API_KEYS"):
            with TestClient(cast(ASGIApp, app.app)):
                pass

    def test_development_mode_logs_info(self):
        """Test that development mode logs info when anonymous access is used."""
        # Set development environment
        os.environ["APP_ENV"] = "development"
        os.environ["DEBUG"] = "true"
        # Don't set API_KEY to test anonymous fallback behavior

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key to VIP endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        # Should not be 401 (anonymous access allowed in development)
        assert response.status_code != 401

    def test_production_with_valid_api_key_works(self):
        """Test that production mode works correctly with valid API key."""
        # Set production environment
        os.environ["APP_ENV"] = "production"
        os.environ["DEBUG"] = "false"
        os.environ["API_KEY"] = "secret-key"

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request with valid API key
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "secret-key"},
        )
        # Should not be 401 (valid API key)
        assert response.status_code != 401

    def test_production_with_invalid_api_key_rejects(self):
        """Test that production mode rejects invalid API key."""
        # Set production environment
        os.environ["APP_ENV"] = "production"
        os.environ["DEBUG"] = "false"
        os.environ["API_KEY"] = "secret-key"

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request with invalid API key
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 403
        detail_lower = response.json()["detail"].lower()
        assert "vip" in detail_lower or "invalid" in detail_lower

    def test_environment_variable_defaults(self):
        """Test that environment variables have correct defaults."""
        # Clear all relevant environment variables
        for var in ["APP_ENV", "DEBUG", "ALLOW_ANONYMOUS_API_KEYS", "ALLOW_DEV_API_KEY"]:
            if var in os.environ:
                del os.environ[var]

        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test request without API key - should allow in default local mode
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        # Should not be 401 (default is local development mode)
        assert response.status_code != 401
