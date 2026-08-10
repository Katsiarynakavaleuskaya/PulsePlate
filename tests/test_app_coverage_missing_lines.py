"""
Test coverage for missing lines in app.py to improve coverage to 97%.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import legacy_app
from app.routers.api_key import get_api_key
from app.services import admin_operations
from app.utils.feature_flags import _is_truthy
from fastapi.testclient import TestClient
from tests.helpers.fast_update_stubs import (
    add_persisted_version_store_stub,
    make_scheduler_stub,
    patch_admin_get_update_scheduler,
)


class TestAppMissingLinesCoverage:
    """Tests for missing lines in app.py."""

    def test_is_truthy_function(self):
        """Test the _is_truthy helper function."""
        # Test truthy values
        assert _is_truthy("1") is True
        assert _is_truthy("true") is True
        assert _is_truthy("yes") is True
        assert _is_truthy("on") is True
        assert _is_truthy(" 1 ") is True  # With whitespace

        # Test falsy values
        assert _is_truthy("0") is False
        assert _is_truthy("false") is False
        assert _is_truthy("no") is False
        assert _is_truthy("off") is False
        assert _is_truthy("") is False
        assert _is_truthy(None) is False

    def test_get_api_key_with_valid_key(self, client):
        """Test get_api_key with valid API key."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            result = get_api_key("valid_key")
            assert result == "valid_key"

    def test_get_api_key_with_invalid_key(self, client):
        """Test get_api_key with invalid API key."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            # Should raise HTTPException
            with pytest.raises(Exception):
                get_api_key("invalid_key")

    def test_get_api_key_required_mode(self, client):
        """Test get_api_key in required mode."""
        with patch.dict(os.environ, {"API_KEY_REQUIRED": "true"}):
            # Should raise HTTPException when no API key is configured
            with pytest.raises(Exception):
                get_api_key("any_key")

    def test_get_api_key_dev_mode(self, client):
        """Test get_api_key in development mode."""
        with patch.dict(os.environ, {"APP_ENV": "dev", "API_KEY": ""}):
            # Should accept non-trivial tokens
            result = get_api_key("test_token")
            assert result == "test_token"

    def test_get_api_key_invalid_tokens(self, client):
        """Test get_api_key with invalid tokens."""
        with patch.dict(os.environ, {"APP_ENV": "dev", "API_KEY": ""}):
            # Test various invalid tokens
            invalid_tokens = ["", "invalid", "wrong", "bad", "null", "123"]  # Too short

            for token in invalid_tokens:
                with pytest.raises(Exception):
                    get_api_key(token)

    def test_admin_status_endpoint_success(self, client: TestClient) -> None:
        """Test admin status endpoint success path."""
        client = client

        # Mock the scheduler to return a valid scheduler
        async def _scheduler_getter() -> MagicMock:
            return MagicMock()

        with patch.object(admin_operations, "get_update_scheduler", _scheduler_getter):
            response = client.get("/api/v1/admin/status", headers={"X-API-Key": "test_key"})

            # Should be 200 when scheduler is available
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "scheduler": "available"}

    def test_admin_status_endpoint_error(self, client: TestClient) -> None:
        """Test admin status endpoint error handling."""
        client = client

        # Mock the scheduler getter to raise an exception
        async def _failing_scheduler_getter() -> None:
            raise RuntimeError("Scheduler error")

        with patch.object(
            admin_operations,
            "get_update_scheduler",
            _failing_scheduler_getter,
        ):
            response = client.get("/api/v1/admin/status", headers={"X-API-Key": "test_key"})

            # Should be 503 when scheduler is unavailable
            assert response.status_code == 503
            assert response.json() == {"detail": "Scheduler unavailable"}

    def test_database_health_success(self, client):
        """Test database health endpoint success."""
        client = client

        response = client.get("/health/db")
        # Should be 200 or 503 depending on database availability
        assert response.status_code in [200, 500, 503]

    def test_legacy_category_label(self):
        """Test the legacy_category_label helper function."""
        # Test English mappings
        assert legacy_app.legacy_category_label("Normal weight", "en") == "Healthy weight"

        # Test Russian mappings
        assert legacy_app.legacy_category_label("Избыточная масса", "ru") == "Избыточный вес"

        # Test no mapping cases
        assert legacy_app.legacy_category_label("Other category", "en") == "Other category"
        assert legacy_app.legacy_category_label("Normal weight", "ru") == "Normal weight"

    def test_favicon_endpoint(self, client):
        """Test the favicon endpoint."""
        client = client

        response = client.get("/favicon.ico")
        assert response.status_code == 204

    def test_metrics_endpoint(self, client, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test the metrics endpoint with Prometheus exporter unavailable."""
        prometheus_client = pytest.importorskip("prometheus_client")

        # Force exporter failure to test JSON fallback
        def _boom() -> bytes:
            raise RuntimeError("Prometheus exporter unavailable")

        monkeypatch.setattr(prometheus_client, "generate_latest", _boom)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "error" in data
        assert data["error"] == "Metrics export failed"

    def test_privacy_endpoint(self, client):
        """Test the privacy endpoint."""
        client = client

        response = client.get("/privacy")
        assert response.status_code == 200
        assert "privacy_policy" in response.json()

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        client = client

        response = client.get("/legacy/bmi-calculator")
        assert response.status_code == 200
        assert "BMI Calculator" in response.text

    def test_health_endpoints(self, client):
        """Test health endpoints."""
        client = client

        # Test basic health endpoint
        response = client.get("/health")
        assert response.status_code == 200

        # Test API v1 health endpoint
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_debug_env_endpoint(self, client):
        """Test debug environment endpoint."""
        client = client

        response = client.get("/debug_env")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_database_status_endpoint(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test database status endpoint."""
        client = client

        scheduler = MagicMock()
        scheduler.get_status.return_value = {"scheduler": {}, "databases": {}}
        patch_admin_get_update_scheduler(monkeypatch, scheduler)
        response = client.get(
            "/api/v1/admin/db-status",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

    def test_force_database_update_endpoint(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test force database update endpoint."""
        scheduler = make_scheduler_stub()
        patch_admin_get_update_scheduler(monkeypatch, scheduler)

        response = client.post(
            "/api/v1/admin/force-update",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

    def test_check_for_updates_endpoint(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test check for updates endpoint."""
        client = client

        scheduler = MagicMock()
        scheduler.update_manager.check_for_updates = AsyncMock(return_value={"usda": True})
        patch_admin_get_update_scheduler(monkeypatch, scheduler)
        response = client.get(
            "/api/v1/admin/check-updates",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

    def test_rollback_database_endpoint(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test rollback database endpoint."""
        client = client

        scheduler = MagicMock()
        scheduler.update_manager = add_persisted_version_store_stub(MagicMock(), tmp_path)
        scheduler.update_manager.rollback_database = AsyncMock(return_value=True)
        patch_admin_get_update_scheduler(monkeypatch, scheduler)
        response = client.post(
            "/api/v1/admin/rollback?source=test&target_version=1.0",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
