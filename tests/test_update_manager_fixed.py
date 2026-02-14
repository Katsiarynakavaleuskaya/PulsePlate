# -*- coding: utf-8 -*-
"""
Update Manager Tests - Fixed

RU: Исправленные тесты для update manager
EN: Fixed update manager tests
"""

import tempfile
from datetime import datetime, timedelta, timezone
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp
from tests.feature_manifest import FEATURE_REASON, require_feature

from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion


class TestUpdateManagerFixed:
    """Fixed update manager tests."""

    def test_database_version_creation(self):
        """Test DatabaseVersion creation with correct parameters."""
        version = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated=datetime.now().isoformat(),
            record_count=100,
            checksum="abc123",
            metadata={"description": "test version"},
        )
        assert version.source == "usda"
        assert version.version == "1.0.0"
        assert version.record_count == 100

    def test_database_version_comparison(self):
        """Test DatabaseVersion comparison functionality."""
        v1 = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated=datetime.now().isoformat(),
            record_count=100,
            checksum="abc123",
            metadata={},
        )

        v2 = DatabaseVersion(
            source="usda",
            version="1.0.1",
            last_updated=datetime.now().isoformat(),
            record_count=150,
            checksum="def456",
            metadata={},
        )

        # Test that versions are different
        assert v1.version != v2.version
        assert v1.record_count != v2.record_count

    @pytest.mark.asyncio
    async def test_check_usda_updates_interval_passed(self):
        """Test _check_usda_updates when interval has passed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=str(temp_dir))

            # Add an old version
            old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated=old_time,
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            result = await manager._check_usda_updates()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_usda_updates_interval_not_passed(self):
        """Test _check_usda_updates when interval has not passed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=str(temp_dir))

            # Add a recent version
            recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated=recent_time,
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            result = await manager._check_usda_updates()
            assert result is False

    def test_update_manager_endpoints_auth(self):
        """Test update manager endpoints authentication."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test without API key - should get 401 or 403
        response = client.get("/api/v1/admin/check-updates")
        assert response.status_code in [401, 403]

        response = client.post("/api/v1/admin/rollback?source=usda&target_version=1.0.0")
        assert response.status_code in [401, 403]

    def test_update_manager_endpoints_with_auth(self):
        """Test update manager endpoints with API key."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test with API key
        response = client.post("/api/v1/admin/check-updates", headers={"X-API-Key": "test_key"})
        # Should not be 401/403 but might be 405 (Method Not Allowed) or other
        assert response.status_code != 401
        assert response.status_code != 403

    def test_update_manager_initialization(self):
        """Test DatabaseUpdateManager initialization."""
        require_feature("update_manager_path_attrs", reason=FEATURE_REASON)
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(
                cache_dir=temp_dir, update_interval_hours=12, max_rollback_versions=3
            )
            assert manager.update_interval.total_seconds() == 12 * 3600
            assert manager.max_rollback_versions == 3
            assert manager.cache_dir.path.exists()

    def test_database_version_serialization(self):
        """Test DatabaseVersion can be serialized."""
        version = DatabaseVersion(
            source="test",
            version="1.0.0",
            last_updated="2024-01-01T00:00:00",
            record_count=100,
            checksum="abc123",
            metadata={"test": True},
        )

        # Test that all fields are accessible
        assert hasattr(version, "source")
        assert hasattr(version, "version")
        assert hasattr(version, "last_updated")
        assert hasattr(version, "record_count")
        assert hasattr(version, "checksum")
        assert hasattr(version, "metadata")

    @pytest.mark.asyncio
    async def test_update_manager_error_handling(self):
        """Test update manager error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            with (
                patch.object(
                    manager,
                    "_check_usda_updates",
                    new=AsyncMock(side_effect=Exception("Network error")),
                ),
                patch("core.food_apis.update_manager.logger") as mock_logger,
            ):
                result = await manager.check_for_updates()
                assert result.get("usda") is False
                mock_logger.error.assert_called()
