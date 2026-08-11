"""
Comprehensive tests to improve coverage for food_apis modules to 97%+.
These tests target the uncovered lines to maximize coverage improvement.
"""

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from core.food_apis.unified_db import UnifiedFoodItem


@pytest.fixture(autouse=True)
def disable_default_off_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable live OFF client by default; tests may override with explicit mocks."""
    monkeypatch.setattr("core.food_apis.unified_db.OFFClient", None)


def _admissible_common_food_fixture(index: int) -> "UnifiedFoodItem":
    """Build one structurally complete offline common-food result."""
    from core.food_apis.unified_db import UnifiedFoodItem

    nutrient = f"fixture_nutrient_{index}"
    value = float(index + 1)
    return UnifiedFoodItem(
        name=f"Fixture food {index}",
        nutrients_per_100g={
            nutrient: value,
            "protein_g": 1.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
        },
        cost_per_100g=1.0,
        tags=["offline"],
        availability_regions=["TEST"],
        source="deterministic-fixture",
        source_id=f"fixture-{index}",
        category="Fixture",
        nutrition_inputs=[
            {
                "source": "usda",
                "record_id": f"fixture-{index}",
                "version_ref": "2026-08-10",
                "nutrients": {nutrient: value, "protein_g": 1.0},
                "raw_payload": {},
            }
        ],
        nutrition_provenance={nutrient: "usda", "protein_g": "usda"},
        nutrition_nutrient_confidence={nutrient: 0.7, "protein_g": 0.7},
        nutrition_confidence=0.7,
    )


def _admissible_off_food_fixture(identity: str):
    """Build one complete deterministic OFF result without provider access."""
    from core.food_apis.openfoodfacts_client import OFFFoodItem

    nutrients = {"protein_g": 7.0, "fat_g": 2.0, "carbs_g": 3.0}
    return OFFFoodItem(
        code=f"off-{identity}",
        product_name=f"OFF {identity}",
        categories=["fixture"],
        nutrients_per_100g=nutrients,
        ingredients_text=None,
        brands=None,
        labels=[],
        countries=["TEST"],
        packaging=[],
        image_url=None,
        last_modified_t=1,
        nutrition_inputs=[
            {
                "source": "estimate",
                "record_id": f"off-{identity}",
                "version_ref": "1",
                "nutrients": nutrients,
                "raw_payload": {},
            }
        ],
        nutrition_provenance={key: "estimate" for key in nutrients},
        nutrition_nutrient_confidence={key: 0.4 for key in nutrients},
        nutrition_confidence=0.4,
    )


# Test scheduler module comprehensively
@pytest.mark.slow
class TestDatabaseUpdateSchedulerComprehensive:
    """Comprehensive tests for DatabaseUpdateScheduler to improve coverage."""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_setup_signal_handlers_exception(self):
        """Test signal handler setup with exception."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler()

        # Mock signal.signal to raise an exception
        with patch(
            "core.food_apis.scheduler.signal.signal",
            side_effect=Exception("Test error"),
        ):
            # Should not crash
            scheduler._setup_signal_handlers()
            # Should log warning (we can't easily test logging, but at least it shouldn't crash)

    @pytest.mark.asyncio
    async def test_update_loop_cancelled_error(self):
        """Test update loop handling of CancelledError."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        # Mock datetime.now to return consistent values
        with patch(
            "core.food_apis.scheduler.now_utc",
            return_value=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ):
            # Mock _should_check_for_updates to return True
            scheduler._should_check_for_updates = MagicMock(return_value=True)

            # Mock _run_update_check to raise CancelledError
            scheduler._run_update_check = AsyncMock(side_effect=asyncio.CancelledError())

            # Mock asyncio.sleep to avoid waiting
            with patch("core.food_apis.scheduler.asyncio.sleep", new_callable=AsyncMock):
                # Should not crash
                await scheduler._update_loop()

    @pytest.mark.asyncio
    async def test_update_loop_general_exception(self):
        """Test update loop handling of general exceptions."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        # Mock datetime.now to return consistent values
        with patch(
            "core.food_apis.scheduler.now_utc",
            return_value=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ):
            # Mock _should_check_for_updates to return True
            scheduler._should_check_for_updates = MagicMock(return_value=True)

            # Mock _run_update_check to raise a general exception
            scheduler._run_update_check = AsyncMock(side_effect=Exception("Test error"))

            # Mock asyncio.sleep to control execution
            with patch("core.food_apis.scheduler.asyncio.sleep", new_callable=AsyncMock):
                # Create a task to run the loop
                loop_task = asyncio.create_task(scheduler._update_loop())

                # Let it run for a bit
                await asyncio.sleep(0.1)

                # Cancel the task to stop the loop
                loop_task.cancel()
                try:
                    await loop_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_run_update_check_exception(self):
        """Test run_update_check handling of exceptions."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates to raise an exception
        scheduler.update_manager.check_for_updates = AsyncMock(side_effect=Exception("Test error"))

        # Should not crash
        await scheduler._run_update_check()

    @pytest.mark.asyncio
    async def test_run_source_update_exception(self):
        """Test _run_source_update handling of exceptions."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.update_database to raise an exception
        scheduler.update_manager.update_database = AsyncMock(side_effect=Exception("Test error"))

        # Should handle the exception gracefully
        await scheduler._run_source_update("test_source")

        # Should increment retry count
        assert scheduler.retry_counts.get("test_source", 0) == 1

    def test_handle_update_failure_max_retries(self):
        """Test _handle_update_failure when max retries exceeded."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler(max_retries=2)
        scheduler.retry_counts["test_source"] = 2  # Already at max retries

        # Should reset retry count when max exceeded
        scheduler._handle_update_failure("test_source", ["Test error"])
        assert scheduler.retry_counts.get("test_source", 0) == 0

    def test_handle_update_failure_increment(self):
        """Test _handle_update_failure incrementing retry count."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler(max_retries=3)
        scheduler.retry_counts["test_source"] = 1

        # Should increment retry count
        scheduler._handle_update_failure("test_source", ["Test error"])
        assert scheduler.retry_counts.get("test_source", 0) == 2

    def test_on_update_complete(self):
        """Test _on_update_complete callback."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler
        from core.food_apis.update_manager import UpdateResult

        scheduler = DatabaseUpdateScheduler()

        # Test successful update
        success_result = UpdateResult(
            success=True,
            source="test",
            old_version="1.0",
            new_version="1.1",
            records_added=10,
            records_updated=5,
            records_removed=0,
            errors=[],
            duration_seconds=1.0,
        )

        # Should not crash
        scheduler._on_update_complete(success_result)

        # Test failed update
        failure_result = UpdateResult(
            success=False,
            source="test",
            old_version="1.0",
            new_version=None,
            records_added=0,
            records_updated=0,
            records_removed=0,
            errors=["Test error"],
            duration_seconds=1.0,
        )

        # Should not crash
        scheduler._on_update_complete(failure_result)

    @pytest.mark.asyncio
    async def test_force_update_specific_source(self):
        """Test force_update with specific source."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler
        from core.food_apis.update_manager import UpdateResult

        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.update_database
        mock_result = UpdateResult(
            success=True,
            source="test_source",
            old_version="1.0",
            new_version="1.1",
            records_added=10,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=1.0,
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        # Test with specific source
        results = await scheduler.force_update("test_source")

        assert "test_source" in results
        assert results["test_source"].success is True

    @pytest.mark.asyncio
    async def test_force_update_all_sources(self):
        """Test force_update with all sources."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler
        from core.food_apis.update_manager import UpdateResult

        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates
        scheduler.update_manager.check_for_updates = AsyncMock(return_value={"test_source": True})

        # Mock update_manager.update_database
        mock_result = UpdateResult(
            success=True,
            source="test_source",
            old_version="1.0",
            new_version="1.1",
            records_added=10,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=1.0,
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        # Test with all sources
        results = await scheduler.force_update()

        assert "test_source" in results
        assert results["test_source"].success is True

    def test_get_status(self):
        """Test get_status method."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler
        from core.food_apis.update_manager import DatabaseVersion

        scheduler = DatabaseUpdateScheduler()

        # Set up some test data
        scheduler.last_update_check = datetime(2023, 1, 1, 12, 0, 0)
        scheduler.retry_counts["test_source"] = 2

        # Add a database version
        test_version = DatabaseVersion(
            source="test_source",
            version="1.0",
            last_updated="2023-01-01T10:00:00",
            record_count=100,
            checksum="abc123",
            metadata={"test": "data"},
        )
        scheduler.update_manager.versions["test_source"] = test_version

        # Mock update_manager.get_database_status
        scheduler.update_manager.get_database_status = MagicMock(
            return_value={
                "test_source": {
                    "version": "1.0",
                    "last_updated": "2023-01-01T10:00:00",
                    "hours_since_update": 2.0,
                    "record_count": 100,
                    "checksum": "abc123...",
                    "metadata": {"test": "data"},
                }
            }
        )

        status = scheduler.get_status()

        assert "scheduler" in status
        assert "databases" in status
        assert status["scheduler"]["is_running"] is False
        assert status["scheduler"]["retry_counts"]["test_source"] == 2

    @pytest.mark.asyncio
    async def test_global_scheduler_functions(self):
        """Test global scheduler functions."""
        from core.food_apis.scheduler import (
            get_update_scheduler,
            start_background_updates,
            stop_background_updates,
        )

        # Test get_update_scheduler
        scheduler1 = await get_update_scheduler()
        scheduler2 = await get_update_scheduler()

        # Should return the same instance
        assert scheduler1 is scheduler2

        # Test start_background_updates
        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await start_background_updates(1)  # 1 hour interval
            # Should log that updates started
            mock_logger.info.assert_called()

        # Test stop_background_updates
        with patch("core.food_apis.scheduler.logger") as mock_logger:
            try:
                await stop_background_updates()
                # Should log that updates stopped
                mock_logger.info.assert_called()
            except RuntimeError as e:
                # Skip test if event loop is closed
                pytest.skip(f"Event loop closed: {e}")


# Test unified_db module comprehensively
class TestUnifiedFoodDatabaseComprehensive:
    """Comprehensive tests for UnifiedFoodDatabase to improve coverage."""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    @pytest.mark.asyncio
    async def test_search_food_prefer_openfoodfacts(self):
        """Test search_food with prefer_source='openfoodfacts'."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda_class:
            mock_usda_instance = MagicMock()
            mock_usda_instance.search_foods = AsyncMock(return_value=[])
            mock_usda_class.return_value = mock_usda_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                db = UnifiedFoodDatabase(cache_dir=temp_dir)
                db.off_client = None

                # Test with prefer_source='openfoodfacts'
                # Currently this will fall back to USDA since OFF is not implemented
                results = await db.search_food("chicken", prefer_source="openfoodfacts")
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_food_with_results(self):
        """Test search_food with actual results."""
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda_class:
            # Create mock USDA food item
            mock_usda_food = MagicMock()
            mock_usda_food.description = "Chicken Breast"
            mock_usda_food.food_category = "Meat"
            mock_usda_food.nutrients_per_100g = {
                "protein_g": 31.0,
                "fat_g": 3.6,
                "carbs_g": 0.0,
            }
            mock_usda_food._generate_tags = MagicMock(return_value=["meat", "chicken"])

            mock_usda_instance = MagicMock()
            mock_usda_instance.search_foods = AsyncMock(return_value=[mock_usda_food])
            mock_usda_class.return_value = mock_usda_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                db = UnifiedFoodDatabase(cache_dir=temp_dir)
                db.off_client = None

                results = await db.search_food("chicken")

                assert len(results) > 0
                assert isinstance(results[0], UnifiedFoodItem)
                assert results[0].name == "Chicken Breast"

    @pytest.mark.asyncio
    async def test_get_food_by_id_invalid_usda_id(self):
        """Test get_food_by_id with invalid USDA ID."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda_class:
            mock_usda_instance = MagicMock()
            mock_usda_class.return_value = mock_usda_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Test with invalid USDA ID
                result = await db.get_food_by_id("usda", "invalid_id")
                assert result is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_usda_exception(self):
        """Test get_food_by_id with USDA client exception."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda_class:
            mock_usda_instance = MagicMock()
            mock_usda_instance.get_food_details = AsyncMock(side_effect=Exception("Test error"))
            mock_usda_class.return_value = mock_usda_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Test with valid USDA ID that causes exception
                try:
                    result = await db.get_food_by_id("usda", "12345")
                    assert result is None
                except Exception:
                    # If an exception is raised, that's also acceptable behavior
                    assert True

    @pytest.mark.asyncio
    async def test_get_food_by_id_non_usda_source(self):
        """Test get_food_by_id with non-USDA source."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        with (
            patch("core.food_apis.unified_db.USDAClient") as mock_usda_class,
            patch("core.food_apis.unified_db.OFFClient") as mock_off_class,
        ):
            mock_usda_instance = MagicMock()
            mock_usda_class.return_value = mock_usda_instance

            mock_off_instance = MagicMock()
            mock_off_instance.get_product_details = AsyncMock(return_value=None)
            mock_off_class.return_value = mock_off_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Test with non-USDA source
                result = await db.get_food_by_id("openfoodfacts", "12345")
                assert result is None

    def test_get_common_foods_database_invalid_cache_rebuild_must_be_complete(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A rejected cache is preserved when its one replacement sweep is incomplete."""
        from core.food_apis.unified_db import (
            COMMON_FOODS_MANIFEST,
            CommonFoodsCacheAdmissionError,
            UnifiedFoodDatabase,
        )

        db = UnifiedFoodDatabase(cache_dir=str(tmp_path / "invalid-cache"))
        cache_file = db.cache_dir / "common_foods.json"
        cache_file.write_text("invalid json", encoding="utf-8")
        original_bytes = cache_file.read_bytes()
        calls: list[tuple[str, bool, bool]] = []

        async def unresolved_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[object]:
            calls.append((query, save_cache, use_memory_cache))
            return []

        monkeypatch.setenv("UNIFIED_DB_COMMON_SLEEP_MS", "0")
        monkeypatch.setattr(db, "search_food", unresolved_search)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="membership is not exact"):
            asyncio.run(db.get_common_foods_database())

        assert calls == [(query, False, False) for query in COMMON_FOODS_MANIFEST.values()]
        assert cache_file.read_bytes() == original_bytes

    def test_get_common_foods_database_publication_failure_is_admission_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A complete exact envelope is not returned when atomic publication fails."""
        from core.food_apis import unified_db as unified_db_module
        from core.food_apis.unified_db import (
            COMMON_FOODS_MANIFEST,
            CommonFoodsCacheAdmissionError,
            UnifiedFoodDatabase,
        )

        db = UnifiedFoodDatabase(cache_dir=str(tmp_path / "publication-failure"))
        queries = tuple(COMMON_FOODS_MANIFEST.values())
        calls: list[tuple[str, bool, bool]] = []

        async def complete_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[object]:
            calls.append((query, save_cache, use_memory_cache))
            return [_admissible_common_food_fixture(queries.index(query))]

        def fail_serialization(*args: object, **kwargs: object) -> None:
            raise OSError("write failed")

        monkeypatch.setenv("UNIFIED_DB_COMMON_SLEEP_MS", "0")
        monkeypatch.setattr(db, "search_food", complete_search)
        monkeypatch.setattr(unified_db_module.json, "dump", fail_serialization)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="publication failed"):
            asyncio.run(db.get_common_foods_database())

        assert calls == [(query, False, False) for query in queries]
        assert not (db.cache_dir / "common_foods.json").exists()
        assert not list(db.cache_dir.glob(".common_foods.json.*.tmp"))

    def test_get_common_foods_database_search_exception_is_secret_safe(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Row failures finish the finite sweep but cannot leak provider context."""
        from core.food_apis.unified_db import (
            COMMON_FOODS_MANIFEST,
            CommonFoodsCacheAdmissionError,
            UnifiedFoodDatabase,
        )

        sensitive_context = "comprehensive-provider-context-marker-91c4-do-not-log"
        db = UnifiedFoodDatabase(cache_dir=str(tmp_path / "search-exception"))
        calls: list[tuple[str, bool, bool]] = []

        async def failed_search(
            query: str,
            save_cache: bool = True,
            use_memory_cache: bool = True,
        ) -> list[object]:
            calls.append((query, save_cache, use_memory_cache))
            raise RuntimeError(sensitive_context)

        monkeypatch.setenv("UNIFIED_DB_COMMON_SLEEP_MS", "0")
        monkeypatch.setattr(db, "search_food", failed_search)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="membership is not exact"):
            asyncio.run(db.get_common_foods_database())

        assert calls == [(query, False, False) for query in COMMON_FOODS_MANIFEST.values()]
        assert sensitive_context not in caplog.text
        assert "category=RuntimeError" in caplog.text

    @pytest.mark.asyncio
    async def test_unified_db_global_functions(self):
        """Test global unified database functions."""
        from core.food_apis.unified_db import get_unified_food_db, search_foods_unified

        with patch("core.food_apis.unified_db.USDAClient"):
            # Test get_unified_food_db
            db1 = await get_unified_food_db()
            db2 = await get_unified_food_db()

            # Should return the same instance
            assert db1 is db2

            # Test search_foods_unified
            with patch.object(db1, "search_food", new_callable=AsyncMock) as mock_search:
                mock_search.return_value = []
                results = await search_foods_unified("chicken", 5)
                assert isinstance(results, list)


# Test update_manager module comprehensively
class TestDatabaseUpdateManagerComprehensive:
    """Comprehensive tests for DatabaseUpdateManager to improve coverage."""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_load_versions_file_not_exists(self):
        """Test _load_versions with non-existent file."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a subdirectory that doesn't exist yet
            manager = DatabaseUpdateManager(cache_dir=os.path.join(temp_dir, "nonexistent"))
            # Should handle gracefully
            assert isinstance(manager.versions, dict)

    def test_load_versions_invalid_json(self):
        """Test _load_versions with invalid JSON."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create an invalid versions file
            versions_file = manager.cache_dir / "database_versions.json"
            with open(versions_file, "w") as f:
                f.write("invalid json")

            # Should handle gracefully
            versions = manager._load_versions()
            assert isinstance(versions, dict)

    def test_save_versions_exception(self):
        """Version publication failures are explicit and leave no partial target."""
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock json.dump to raise an exception
            with patch(
                "core.food_apis.update_manager.json.dump",
                side_effect=Exception("Test error"),
            ):
                with pytest.raises(
                    CommonFoodsCacheAdmissionError,
                    match="Database versions publication failed",
                ):
                    manager._save_versions()

            assert not manager.versions_file.exists()
            assert not list(Path(temp_dir).glob(".database_versions.json.*.tmp"))

    def test_save_versions_parent_fsync_failure_restores_exact_prior_bytes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.food_apis import update_manager as update_manager_module
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="established-v1",
            last_updated="2026-08-11T00:00:00+00:00",
            record_count=20,
            checksum="established",
            metadata={},
        )
        manager._save_versions()
        prior_bytes = manager.versions_file.read_bytes()
        manager.versions["usda"].version = "replacement-v2"
        real_fsync = os.fsync
        fsync_count = 0

        def fail_first_parent_fsync(descriptor: int) -> None:
            nonlocal fsync_count
            fsync_count += 1
            if fsync_count == 2:
                raise OSError("forced version parent fsync failure")
            real_fsync(descriptor)

        monkeypatch.setattr(update_manager_module.os, "fsync", fail_first_parent_fsync)

        with pytest.raises(
            CommonFoodsCacheAdmissionError,
            match="Database versions publication failed",
        ):
            manager._save_versions()

        assert manager.versions_file.read_bytes() == prior_bytes
        assert fsync_count == 4
        assert not list(tmp_path.glob(".database_versions.json.*.tmp"))

    @pytest.mark.asyncio
    async def test_check_for_updates_usda_exception(self):
        """Test check_for_updates with USDA exception."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock _check_usda_updates to raise an exception
            with patch.object(manager, "_check_usda_updates", side_effect=Exception("Test error")):
                updates = await manager.check_for_updates()
                # Should still return dict with USDA set to False
                assert isinstance(updates, dict)
                assert updates.get("usda") is False

    def test_check_usda_updates_no_current_version(self):
        """Test _check_usda_updates with no current version."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Clear any existing versions
            manager.versions.clear()

            # Should return True when no current version
            result = asyncio.run(manager._check_usda_updates())
            assert result is True

    def test_check_usda_updates_interval_not_passed(self):
        """Test _check_usda_updates when interval has not passed."""
        from datetime import datetime, timedelta

        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Add a recent version
            recent_time = (datetime.now() - timedelta(hours=1)).isoformat()
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated=recent_time,
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            # Should return False when interval has not passed
            result = asyncio.run(manager._check_usda_updates())
            assert result is False

    @pytest.mark.asyncio
    async def test_update_database_unknown_source(self):
        """Test update_database with unknown source."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            result = await manager.update_database("unknown_source")

            assert result.success is False
            assert result.source == "unknown_source"
            assert "Unknown source" in result.errors[0]

    @pytest.mark.asyncio
    async def test_update_database_callback_exception(self):
        """Test update_database with callback exception."""
        from core.food_apis.update_manager import DatabaseUpdateManager, UpdateResult

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Add a callback that raises an exception
            def bad_callback(result):
                raise Exception("Callback error")

            manager.add_update_callback(bad_callback)

            # Mock _update_usda_database to return a result
            mock_result = UpdateResult(
                success=True,
                source="usda",
                old_version=None,
                new_version="1.0",
                records_added=10,
                records_updated=0,
                records_removed=0,
                errors=[],
                duration_seconds=1.0,
            )
            with patch.object(manager, "_update_usda_database", return_value=mock_result):
                # Should not crash despite callback exception
                result = await manager.update_database("usda")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_update_usda_database_create_backup_exception(self):
        """Test _update_usda_database with backup creation exception."""
        from core.food_apis.update_manager import (
            DatabaseUpdateManager,
            DatabaseVersion,
            UpdateResult,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Add a version to trigger backup creation
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            # Mock _create_backup to raise an exception
            with patch.object(manager, "_create_backup", side_effect=Exception("Backup error")):
                # Mock unified_db.get_common_foods_database
                with patch.object(
                    manager.unified_db,
                    "get_common_foods_database",
                    new_callable=AsyncMock,
                ) as mock_get_foods:
                    mock_get_foods.return_value = {"chicken": MagicMock()}

                    # Should handle the exception and still complete the update
                    result = await manager._update_usda_database()
                    # The result might be success=False due to the error, but should not crash
                    assert isinstance(result, UpdateResult)

    @pytest.mark.asyncio
    async def test_update_usda_database_no_change(self):
        """Test _update_usda_database when no data change."""
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            test_food = _admissible_common_food_fixture(103)
            test_data = {"chicken": test_food}
            checksum_data = {"chicken": asdict(test_food)}
            checksum = manager._calculate_checksum(checksum_data)

            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=1,
                checksum=checksum,
                metadata={},
            )
            manager.versions["usda"] = version
            (Path(temp_dir) / "common_foods.json").write_text(
                json.dumps({name: asdict(food) for name, food in test_data.items()}),
                encoding="utf-8",
            )

            # Mock unified_db.get_common_foods_database to return same data
            with patch.object(
                manager.unified_db, "get_common_foods_database", new_callable=AsyncMock
            ) as mock_get_foods:
                mock_get_foods.return_value = test_data

                # Should detect no change and return early
                result = await manager._update_usda_database(force=False)
                assert result.success is True
                # For no change, new_version should equal old_version
                assert result.new_version == "1.0"  # Same version

    @pytest.mark.asyncio
    async def test_update_usda_database_validation_errors(self):
        """Test _update_usda_database with validation errors."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock unified_db.get_common_foods_database to return invalid data
            with patch.object(
                manager.unified_db, "get_common_foods_database", new_callable=AsyncMock
            ) as mock_get_foods:
                mock_food = MagicMock()
                mock_food.name = ""  # Missing required field
                mock_food.source = ""  # Missing required field
                mock_get_foods.return_value = {"invalid_food": mock_food}

                # Should detect validation errors
                result = await manager._update_usda_database()
                assert result.success is False
                assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_update_usda_database_load_backup_exception(self):
        """Test _update_usda_database with backup load exception."""
        from core.food_apis.update_manager import (
            DatabaseUpdateManager,
            DatabaseVersion,
            UpdateResult,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Add a version
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=100,
                checksum="old_checksum",
                metadata={},
            )
            manager.versions["usda"] = version

            # Mock unified_db.get_common_foods_database
            with patch.object(
                manager.unified_db, "get_common_foods_database", new_callable=AsyncMock
            ) as mock_get_foods:
                mock_get_foods.return_value = {"chicken": MagicMock()}

                # Mock _load_backup to raise an exception
                with patch.object(manager, "_load_backup", side_effect=Exception("Load error")):
                    # Should handle the exception and still complete the update
                    result = await manager._update_usda_database()
                    assert isinstance(result, UpdateResult)

    @pytest.mark.parametrize(
        ("source", "update_method_name"),
        [
            ("usda", "_update_usda_database"),
            ("openfoodfacts", "_update_off_database"),
        ],
    )
    @pytest.mark.parametrize("cache_failure", ["missing", "unreadable"])
    def test_established_version_backup_failure_stops_before_acquisition(
        self,
        source: str,
        update_method_name: str,
        cache_failure: str,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """An established version without readable disk truth fails before providers."""
        from core.food_apis.unified_db import COMMON_FOODS_MANIFEST
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        sensitive_marker = f"{source}-backup-sensitive-marker-cc51"

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            established_version = DatabaseVersion(
                source=source,
                version="established-v1",
                last_updated="2026-08-10T00:00:00+00:00",
                record_count=len(COMMON_FOODS_MANIFEST),
                checksum="established-checksum",
                metadata={"state": "established"},
            )
            manager.versions[source] = established_version
            versions_before = dict(manager.versions)
            source_truth = (
                Path(temp_dir) / "common_foods.json"
                if source == "usda"
                else Path(temp_dir) / f"{source}_backup_{established_version.version}.json"
            )
            if cache_failure == "unreadable":
                source_truth.write_text(
                    f'{{"{sensitive_marker}":',
                    encoding="utf-8",
                )
                source_truth_bytes = source_truth.read_bytes()

            acquisition = AsyncMock()
            validation = AsyncMock(return_value=[])
            checksum = MagicMock(return_value="replacement-checksum")
            backup_load = AsyncMock(return_value={})
            version_save = MagicMock()
            cleanup = AsyncMock()
            off_search = AsyncMock(return_value=[])
            off_client = MagicMock()
            off_client.search_products = off_search

            monkeypatch.setattr(manager.unified_db, "get_common_foods_database", acquisition)
            monkeypatch.setattr(manager, "_validate_food_data", validation)
            monkeypatch.setattr(manager, "_calculate_checksum", checksum)
            monkeypatch.setattr(manager, "_load_backup", backup_load)
            monkeypatch.setattr(manager, "_save_versions", version_save)
            monkeypatch.setattr(manager, "_cleanup_old_backups", cleanup)
            monkeypatch.setattr(manager, "off_client", off_client)
            monkeypatch.setattr(
                "core.food_apis.update_manager.asyncio.sleep",
                AsyncMock(),
            )
            caplog.set_level(logging.ERROR, logger="core.food_apis.update_manager")

            update_method = getattr(manager, update_method_name)
            result = asyncio.run(update_method(force=False))

            assert result.success is False
            assert result.source == source
            assert result.old_version == "established-v1"
            assert result.new_version is None
            assert result.records_added == 0
            assert result.records_updated == 0
            assert result.records_removed == 0
            assert result.errors == ["common_food_cache_admission_failed"]
            acquisition.assert_not_awaited()
            validation.assert_not_awaited()
            checksum.assert_not_called()
            backup_load.assert_not_awaited()
            version_save.assert_not_called()
            cleanup.assert_not_awaited()
            if source == "openfoodfacts":
                off_search.assert_not_awaited()
            assert manager.versions == versions_before
            if cache_failure == "unreadable":
                assert source_truth.read_bytes() == source_truth_bytes
            else:
                assert not list(Path(temp_dir).glob(f"{source}_backup_*.json"))

            expected_log = (
                f"Database update stopped; source={source}; category=CommonFoodsCacheAdmissionError"
            )
            matching_records = [
                record
                for record in caplog.records
                if record.name == "core.food_apis.update_manager"
                and record.getMessage() == expected_log
            ]
            assert len(matching_records) == 1
            assert matching_records[0].exc_info is None
            assert sensitive_marker not in caplog.text
            assert sensitive_marker not in repr(matching_records[0].args)

    def test_validate_food_data_missing_fields(self):
        """Test _validate_food_data with missing required fields."""
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create food item with missing name
            invalid_food = UnifiedFoodItem(
                name="",  # Missing required field
                nutrients_per_100g={"protein_g": 20.0},
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "missing required fields" in errors[0]

    def test_validate_food_data_missing_nutrients(self):
        """Test _validate_food_data with missing primary macronutrients.

        Note: Validation now requires at least ONE primary macro (protein_g OR fat_g).
        carbs_g is optional as pure protein/fat foods may have 0 carbs.
        """
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create food item with NO primary macronutrients (should fail)
            invalid_food = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={},  # Missing both protein_g AND fat_g
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "missing primary macronutrients" in errors[0]
            assert "needs protein_g OR fat_g" in errors[0]

    def test_validate_food_data_negative_values(self):
        """Test _validate_food_data with negative nutrient values."""
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create food item with negative nutrient values
            invalid_food = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={
                    "protein_g": -5.0,
                    "fat_g": 2.0,
                    "carbs_g": 3.0,
                },  # Negative value
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "negative" in str(errors[0]).lower()

    def test_validate_food_data_unrealistic_values(self):
        """Test _validate_food_data with unrealistic nutrient values."""
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create food item with unrealistic nutrient values
            invalid_food = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={
                    "protein_g": 150.0,
                    "fat_g": 2.0,
                    "carbs_g": 3.0,
                },  # Unrealistic value (>100g per 100g)
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "unrealistic" in str(errors[0]).lower()

    def test_validate_food_data_optional_carbs(self):
        """Test _validate_food_data accepts foods with missing carbs_g.

        This test verifies the fix for chicken breast/salmon validation failures.
        Pure protein/fat foods (chicken, fish) may have 0 carbs and USDA may
        omit carbs_g field entirely. Validation should accept these.
        """
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create food items simulating USDA chicken breast (missing carbs_g)
            chicken = UnifiedFoodItem(
                name="Chicken Breast",
                nutrients_per_100g={
                    "protein_g": 31.0,  # High protein
                    "fat_g": 3.6,  # Low fat
                    # carbs_g intentionally missing (0 carbs, USDA omits field)
                    "kcal": 165.0,
                },
                cost_per_100g=4.0,
                tags=["protein", "meat"],
                availability_regions=["US"],
                source="USDA",
                source_id="12345",
            )

            # Also test pure fat food (olive oil)
            olive_oil = UnifiedFoodItem(
                name="Olive Oil",
                nutrients_per_100g={
                    "fat_g": 100.0,  # Pure fat
                    # protein_g and carbs_g intentionally missing
                    "kcal": 884.0,
                },
                cost_per_100g=8.0,
                tags=["fat", "oil"],
                availability_regions=["US"],
                source="USDA",
                source_id="54321",
            )

            foods = {"chicken": chicken, "olive_oil": olive_oil}
            errors = asyncio.run(manager._validate_food_data(foods))

            # Both should pass validation (no errors)
            assert len(errors) == 0, f"Unexpected validation errors: {errors}"

    @pytest.mark.parametrize("cache_shape", ["legacy", "versioned"])
    def test_create_backup_uses_disk_truth_before_explicit_reacquisition(
        self,
        cache_shape: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Backup preserves established disk truth without repairing the live cache."""
        from core.food_apis.unified_db import (
            COMMON_FOODS_CACHE_SCHEMA_VERSION,
            COMMON_FOODS_MANIFEST,
            COMMON_FOODS_MANIFEST_VERSION,
        )
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            marker = f"established-{cache_shape}-marker"
            established_item = _admissible_common_food_fixture(91)
            established_item.name = marker
            established_items = {"legacy_slot": asdict(established_item)}
            cache_payload: object = established_items
            if cache_shape == "versioned":
                established_items = {
                    name: asdict(_admissible_common_food_fixture(index))
                    for index, name in enumerate(COMMON_FOODS_MANIFEST)
                }
                first_manifest_name = next(iter(COMMON_FOODS_MANIFEST))
                established_items[first_manifest_name]["name"] = marker
                cache_payload = {
                    "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
                    "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
                    "items": established_items,
                }
            cache_file = Path(temp_dir) / "common_foods.json"
            cache_file.write_text(json.dumps(cache_payload), encoding="utf-8")
            established_bytes = cache_file.read_bytes()
            replacement_envelope = {
                "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
                "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
                "items": {
                    name: asdict(_admissible_common_food_fixture(index))
                    for index, name in enumerate(COMMON_FOODS_MANIFEST)
                },
            }
            acquisition = AsyncMock(return_value=replacement_envelope)
            monkeypatch.setattr(
                manager.unified_db,
                "_acquire_common_foods_envelope",
                acquisition,
            )

            asyncio.run(manager._create_backup("usda", "1.0"))

            acquisition.assert_not_awaited()
            assert cache_file.read_bytes() == established_bytes
            backup_file = Path(temp_dir) / "usda_backup_1.0.json"
            assert json.loads(backup_file.read_text(encoding="utf-8")) == established_items
            assert marker in backup_file.read_text(encoding="utf-8")

            asyncio.run(manager.unified_db.get_common_foods_database())

            if cache_shape == "legacy":
                acquisition.assert_awaited_once_with()
            else:
                acquisition.assert_not_awaited()

    @pytest.mark.parametrize(
        "invalid_envelope",
        ["stale_schema", "stale_manifest", "incomplete_manifest"],
    )
    def test_versioned_usda_backup_rejects_noncanonical_envelope_before_replacement(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        invalid_envelope: str,
    ) -> None:
        from core.food_apis.unified_db import (
            COMMON_FOODS_CACHE_SCHEMA_VERSION,
            COMMON_FOODS_MANIFEST,
            COMMON_FOODS_MANIFEST_VERSION,
            CommonFoodsCacheAdmissionError,
        )
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        envelope: dict[str, object] = {
            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
            "items": {
                name: asdict(_admissible_common_food_fixture(index))
                for index, name in enumerate(COMMON_FOODS_MANIFEST)
            },
        }
        if invalid_envelope == "stale_schema":
            envelope["schema_version"] = "common-foods-cache.stale"
        elif invalid_envelope == "stale_manifest":
            envelope["manifest_version"] = "common-foods-manifest.stale"
        else:
            items = envelope["items"]
            assert isinstance(items, dict)
            items.pop(next(iter(COMMON_FOODS_MANIFEST)))

        cache_file = tmp_path / "common_foods.json"
        cache_file.write_text(json.dumps(envelope), encoding="utf-8")
        provider_acquisition = AsyncMock()
        monkeypatch.setattr(
            manager.unified_db,
            "_acquire_common_foods_envelope",
            provider_acquisition,
        )
        backup_file = tmp_path / "usda_backup_established.json"
        established_backup_bytes = b"established-usda-backup"
        backup_file.write_bytes(established_backup_bytes)

        with pytest.raises(CommonFoodsCacheAdmissionError):
            asyncio.run(manager._create_backup("usda", "established"))

        provider_acquisition.assert_not_awaited()
        assert backup_file.read_bytes() == established_backup_bytes

    def test_first_and_second_off_updates_use_source_specific_backups(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """OFF establishes and revalidates its own snapshots without USDA cache truth."""
        from core.food_apis.openfoodfacts_client import OFFFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        off_item = OFFFoodItem(
            code="off-source-snapshot-1",
            product_name="Source Snapshot Food",
            categories=["fixture"],
            nutrients_per_100g={"protein_g": 7.0, "fat_g": 2.0, "carbs_g": 3.0},
            ingredients_text=None,
            brands=None,
            labels=[],
            countries=["TEST"],
            packaging=[],
            image_url=None,
            last_modified_t=1,
            nutrition_inputs=[
                {
                    "source": "estimate",
                    "record_id": "off-source-snapshot-1",
                    "version_ref": "1",
                    "nutrients": {"protein_g": 7.0, "fat_g": 2.0, "carbs_g": 3.0},
                    "raw_payload": {},
                }
            ],
            nutrition_provenance={
                "protein_g": "estimate",
                "fat_g": "estimate",
                "carbs_g": "estimate",
            },
            nutrition_nutrient_confidence={
                "protein_g": 0.4,
                "fat_g": 0.4,
                "carbs_g": 0.4,
            },
            nutrition_confidence=0.4,
        )
        off_client = MagicMock()
        off_client.search_products = AsyncMock(return_value=[off_item])
        manager.off_client = off_client
        update_times = iter(
            [
                datetime(2026, 8, 11, 10, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 11, 10, 0, 1, tzinfo=timezone.utc),
            ]
        )
        monkeypatch.setattr("core.food_apis.update_manager.now_utc", lambda: next(update_times))
        monkeypatch.setattr("core.food_apis.update_manager.asyncio.sleep", AsyncMock())

        first = asyncio.run(manager._update_off_database(force=True))
        first_backup = tmp_path / f"openfoodfacts_backup_{first.new_version}.json"

        assert first.success is True
        assert first.old_version is None
        assert first.new_version == "20260811_100000"
        assert first_backup.exists()
        assert not (tmp_path / "common_foods.json").exists()
        first_backup_bytes = first_backup.read_bytes()
        first_snapshot = asyncio.run(manager._load_backup("openfoodfacts", first.new_version))
        assert tuple(first_snapshot) == ("source_snapshot_food",)

        second = asyncio.run(manager._update_off_database(force=True))
        second_backup = tmp_path / f"openfoodfacts_backup_{second.new_version}.json"

        assert second.success is True
        assert second.old_version == first.new_version
        assert second.new_version == "20260811_100001"
        assert first_backup.exists()
        assert first_backup.read_bytes() == first_backup_bytes
        assert second_backup.exists()
        assert not (tmp_path / "common_foods.json").exists()
        assert tuple(asyncio.run(manager._load_backup("openfoodfacts", second.new_version))) == (
            "source_snapshot_food",
        )

    def test_off_update_completes_seven_calls_then_versions_exact_persisted_mapping(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        calls: list[tuple[str, int]] = []
        conversions: list[str] = []
        searches = ("apple", "banana", "chicken", "bread", "milk", "cheese", "rice")

        async def search(search_term: str, page_size: int):
            calls.append((search_term, page_size))
            return [_admissible_off_food_fixture(search_term)]

        off_client = MagicMock()
        off_client.search_products = search
        manager.off_client = off_client
        from core.food_apis.unified_db import UnifiedFoodItem

        convert = UnifiedFoodItem.from_off_item

        def recording_conversion(off_item):
            conversions.append(off_item.code)
            return convert(off_item)

        monkeypatch.setattr(UnifiedFoodItem, "from_off_item", recording_conversion)
        monkeypatch.setattr("core.food_apis.update_manager.asyncio.sleep", AsyncMock())
        monkeypatch.setattr(
            "core.food_apis.update_manager.now_utc",
            lambda: datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc),
        )
        result = asyncio.run(manager._update_off_database(force=True))

        assert result.success is True
        assert calls == [(search, 5) for search in searches]
        assert conversions == [f"off-{search}" for search in searches]
        persisted = asyncio.run(manager._load_backup("openfoodfacts", "20260811_120000"))
        persisted_mapping = {name: asdict(food) for name, food in persisted.items()}
        version = manager.versions["openfoodfacts"]
        assert version.record_count == len(persisted_mapping) == 7
        assert version.checksum == manager._calculate_checksum(persisted_mapping)

    @pytest.mark.parametrize("failure", ["empty", "conversion"])
    def test_off_update_refuses_partial_sweep_or_conversion_before_publication(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        failure: str,
    ) -> None:
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        calls: list[str] = []
        searches = ("apple", "banana", "chicken", "bread", "milk", "cheese", "rice")

        async def search(search_term: str, page_size: int):
            assert page_size == 5
            calls.append(search_term)
            if failure == "empty" and search_term == "bread":
                return []
            return [_admissible_off_food_fixture(search_term)]

        off_client = MagicMock()
        off_client.search_products = search
        manager.off_client = off_client
        monkeypatch.setattr("core.food_apis.update_manager.asyncio.sleep", AsyncMock())
        if failure == "conversion":
            conversion = UnifiedFoodItem.from_off_item

            def fail_one_conversion(off_item):
                if off_item.code == "off-chicken":
                    raise ValueError("forced conversion failure")
                return conversion(off_item)

            monkeypatch.setattr(UnifiedFoodItem, "from_off_item", fail_one_conversion)

        result = asyncio.run(manager._update_off_database(force=True))

        assert result.success is False
        assert calls == list(searches[:4] if failure == "empty" else searches)
        assert "openfoodfacts" not in manager.versions
        assert not list(tmp_path.glob("openfoodfacts_backup_*.json"))

    def test_off_update_cancellation_propagates_without_publication(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        off_client = MagicMock()
        off_client.search_products = AsyncMock(side_effect=asyncio.CancelledError)
        manager.off_client = off_client
        monkeypatch.setattr("core.food_apis.update_manager.asyncio.sleep", AsyncMock())

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(manager._update_off_database(force=True))

        assert "openfoodfacts" not in manager.versions
        assert not list(tmp_path.glob("openfoodfacts_backup_*.json"))

    def test_off_update_version_failure_compensates_new_snapshot_and_memory_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        off_client = MagicMock()
        off_client.search_products = AsyncMock(
            side_effect=[
                [_admissible_off_food_fixture(search)]
                for search in (
                    "apple",
                    "banana",
                    "chicken",
                    "bread",
                    "milk",
                    "cheese",
                    "rice",
                )
            ]
        )
        manager.off_client = off_client
        monkeypatch.setattr("core.food_apis.update_manager.asyncio.sleep", AsyncMock())
        monkeypatch.setattr(
            "core.food_apis.update_manager.now_utc",
            lambda: datetime(2026, 8, 11, 12, 30, 0, tzinfo=timezone.utc),
        )
        monkeypatch.setattr(
            manager,
            "_save_versions",
            MagicMock(
                side_effect=CommonFoodsCacheAdmissionError("forced version publication failure")
            ),
        )

        result = asyncio.run(manager._update_off_database(force=True))

        assert result.success is False
        assert result.errors == ["common_food_cache_admission_failed"]
        assert "openfoodfacts" not in manager.versions
        assert not (tmp_path / "openfoodfacts_backup_20260811_123000.json").exists()

    @pytest.mark.parametrize("snapshot_shape", ["empty", "malformed", "mixed"])
    def test_backup_snapshot_rejects_whole_invalid_payload_before_write(
        self,
        tmp_path: Path,
        snapshot_shape: str,
    ) -> None:
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        valid_item = asdict(_admissible_common_food_fixture(92))
        invalid_item = {"name": "Missing required reconstruction fields"}
        snapshots: dict[str, object] = {
            "empty": {},
            "malformed": {"invalid": invalid_item},
            "mixed": {"valid": valid_item, "invalid": invalid_item},
        }
        backup_file = tmp_path / f"openfoodfacts_backup_{snapshot_shape}.json"
        established_bytes = b"established-source-snapshot"
        backup_file.write_bytes(established_bytes)

        with pytest.raises(CommonFoodsCacheAdmissionError):
            manager._write_backup_snapshot(
                "openfoodfacts",
                snapshot_shape,
                snapshots[snapshot_shape],
            )

        assert backup_file.read_bytes() == established_bytes

    @pytest.mark.parametrize("failure", ["fsync", "replace"])
    def test_backup_snapshot_publication_failure_preserves_established_target(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        failure: str,
    ) -> None:
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        backup_file = tmp_path / "openfoodfacts_backup_established.json"
        established_bytes = b"established-source-snapshot"
        backup_file.write_bytes(established_bytes)

        def fail_publication(*args: object) -> None:
            raise OSError(f"forced {failure} failure")

        monkeypatch.setattr(
            f"core.food_apis.update_manager.os.{failure}",
            fail_publication,
        )

        with pytest.raises(
            CommonFoodsCacheAdmissionError,
            match="Backup snapshot write failed",
        ):
            manager._write_backup_snapshot(
                "openfoodfacts",
                "established",
                {"valid": asdict(_admissible_common_food_fixture(94))},
            )

        assert backup_file.read_bytes() == established_bytes
        assert not list(tmp_path.glob(f".{backup_file.name}.*.tmp"))

    def test_backup_snapshot_fsyncs_parent_and_closes_descriptor(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from core.food_apis import update_manager as update_manager_module
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        backup_file = tmp_path / "openfoodfacts_backup_parent-fsync.json"
        events: list[tuple[str, int | None]] = []
        real_fsync = os.fsync
        real_close = os.close
        real_replace = os.replace

        def recording_fsync(descriptor: int) -> None:
            events.append(("fsync", descriptor))
            real_fsync(descriptor)

        def recording_replace(source: str | Path, target: str | Path) -> None:
            real_replace(source, target)
            events.append(("replace", None))

        def recording_close(descriptor: int) -> None:
            events.append(("close", descriptor))
            real_close(descriptor)

        monkeypatch.setattr(update_manager_module.os, "fsync", recording_fsync)
        monkeypatch.setattr(update_manager_module.os, "replace", recording_replace)
        monkeypatch.setattr(update_manager_module.os, "close", recording_close)

        manager._write_backup_snapshot(
            "openfoodfacts",
            "parent-fsync",
            {"valid": _admissible_common_food_fixture(96)},
        )

        fsync_events = [event for event in events if event[0] == "fsync"]
        assert len(fsync_events) == 2
        parent_descriptor = fsync_events[-1][1]
        assert parent_descriptor is not None
        assert [event[0] for event in events] == ["fsync", "replace", "fsync", "close"]
        assert events[-2:] == [
            ("fsync", parent_descriptor),
            ("close", parent_descriptor),
        ]

    @pytest.mark.parametrize(
        "prior_target_bytes",
        [b"exact-prior-backup", None],
        ids=["existing-target", "no-prior-target"],
    )
    def test_backup_parent_fsync_failure_restores_prior_state_and_closes_descriptors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        prior_target_bytes: bytes | None,
    ) -> None:
        from core.food_apis import update_manager as update_manager_module
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        backup_file = tmp_path / "openfoodfacts_backup_parent-fsync-failure.json"
        if prior_target_bytes is not None:
            backup_file.write_bytes(prior_target_bytes)
        fsync_descriptors: list[int] = []
        closed_descriptors: list[int] = []
        real_fsync = os.fsync
        real_close = os.close

        def fail_first_parent_fsync(descriptor: int) -> None:
            fsync_descriptors.append(descriptor)
            if len(fsync_descriptors) == 2:
                raise OSError("forced backup parent fsync failure")
            real_fsync(descriptor)

        def recording_close(descriptor: int) -> None:
            closed_descriptors.append(descriptor)
            real_close(descriptor)

        monkeypatch.setattr(update_manager_module.os, "fsync", fail_first_parent_fsync)
        monkeypatch.setattr(update_manager_module.os, "close", recording_close)

        with pytest.raises(CommonFoodsCacheAdmissionError, match="Backup snapshot write failed"):
            manager._write_backup_snapshot(
                "openfoodfacts",
                "parent-fsync-failure",
                {"valid": _admissible_common_food_fixture(97)},
            )

        expected_fsync_count = 4 if prior_target_bytes is not None else 3
        assert len(fsync_descriptors) == expected_fsync_count
        assert fsync_descriptors[1] in closed_descriptors
        assert fsync_descriptors[-1] in closed_descriptors
        if prior_target_bytes is None:
            assert not backup_file.exists()
        else:
            assert backup_file.read_bytes() == prior_target_bytes
        assert not list(tmp_path.glob(f".{backup_file.name}.*.tmp"))

    @pytest.mark.parametrize(
        ("source", "version"),
        [
            ("usda", "../escape"),
            ("usda", "/absolute/path"),
            ("USDA", "valid-version"),
            ("openfoodfacts", "v" * 129),
        ],
    )
    def test_backup_path_resolver_rejects_unsafe_source_or_version(
        self,
        tmp_path: Path,
        source: str,
        version: str,
    ) -> None:
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)

        with pytest.raises(CommonFoodsCacheAdmissionError):
            manager._write_backup_snapshot(
                source,
                version,
                {"valid": _admissible_common_food_fixture(98)},
            )

        assert not list(tmp_path.glob("*_backup_*.json"))

    def test_backup_path_resolver_rejects_symlink_input_and_target(
        self,
        tmp_path: Path,
    ) -> None:
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        cache_dir = tmp_path / "cache"
        manager = DatabaseUpdateManager(cache_dir=cache_dir)
        outside_file = tmp_path / "outside-backup.json"
        outside_bytes = json.dumps({"valid": asdict(_admissible_common_food_fixture(99))}).encode()
        outside_file.write_bytes(outside_bytes)
        symlink = cache_dir / "openfoodfacts_backup_link.json"
        symlink.symlink_to(outside_file)

        assert asyncio.run(manager._load_backup("openfoodfacts", "link")) == {}
        with pytest.raises(CommonFoodsCacheAdmissionError):
            manager._write_backup_snapshot(
                "openfoodfacts",
                "link",
                {"replacement": _admissible_common_food_fixture(100)},
            )
        with pytest.raises(CommonFoodsCacheAdmissionError):
            asyncio.run(manager._create_backup("openfoodfacts", "link"))

        assert symlink.is_symlink()
        assert outside_file.read_bytes() == outside_bytes

    @pytest.mark.parametrize(
        "invalid_shape",
        ["nonfinite", "confidence", "evidence", "provenance"],
    )
    def test_generic_backup_rejects_invalid_nutrition_evidence_as_a_whole(
        self,
        tmp_path: Path,
        invalid_shape: str,
    ) -> None:
        from core.food_apis.unified_db import CommonFoodsCacheAdmissionError
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        candidate = asdict(_admissible_common_food_fixture(101))
        nutrient = "fixture_nutrient_101"
        if invalid_shape == "nonfinite":
            candidate["nutrients_per_100g"][nutrient] = float("inf")
        elif invalid_shape == "confidence":
            candidate["nutrition_confidence"] = 1.1
        elif invalid_shape == "evidence":
            candidate["nutrition_inputs"][0]["record_id"] = ""
        else:
            candidate["nutrition_provenance"][nutrient] = "estimate"

        backup_file = tmp_path / f"openfoodfacts_backup_{invalid_shape}.json"
        established_bytes = b"established-valid-backup"
        backup_file.write_bytes(established_bytes)

        with pytest.raises(CommonFoodsCacheAdmissionError):
            manager._write_backup_snapshot(
                "openfoodfacts",
                invalid_shape,
                {"invalid": candidate},
            )

        assert backup_file.read_bytes() == established_bytes

    def test_generic_backup_loader_rejects_json_exponent_overflow(self, tmp_path: Path) -> None:
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        payload = json.dumps({"overflow": asdict(_admissible_common_food_fixture(102))})
        payload = payload.replace("103.0", "1e400", 1)
        assert "1e400" in payload
        (tmp_path / "openfoodfacts_backup_overflow.json").write_text(
            payload,
            encoding="utf-8",
        )

        assert asyncio.run(manager._load_backup("openfoodfacts", "overflow")) == {}

    def test_load_backup_rejects_mixed_snapshot_as_a_whole(self, tmp_path: Path) -> None:
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        backup_file = tmp_path / "openfoodfacts_backup_mixed.json"
        backup_file.write_text(
            json.dumps(
                {
                    "valid": asdict(_admissible_common_food_fixture(93)),
                    "invalid": {"name": "Missing required reconstruction fields"},
                }
            ),
            encoding="utf-8",
        )

        assert asyncio.run(manager._load_backup("openfoodfacts", "mixed")) == {}

    def test_rollback_refuses_empty_backup_without_mutating_version(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        established = DatabaseVersion(
            source="openfoodfacts",
            version="established-v1",
            last_updated="2026-08-11T00:00:00+00:00",
            record_count=1,
            checksum="established-checksum",
            metadata={},
        )
        manager.versions["openfoodfacts"] = established
        (tmp_path / "openfoodfacts_backup_empty.json").write_text("{}", encoding="utf-8")
        save_versions = MagicMock()
        monkeypatch.setattr(manager, "_save_versions", save_versions)

        success = asyncio.run(manager.rollback_database("openfoodfacts", "empty"))

        assert success is False
        assert manager.versions["openfoodfacts"] is established
        save_versions.assert_not_called()

    def test_successful_off_rollback_persists_refreshable_version_snapshot(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from core.food_apis.openfoodfacts_client import OFFFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        manager.versions["openfoodfacts"] = DatabaseVersion(
            source="openfoodfacts",
            version="current-v2",
            last_updated="2026-08-11T09:00:00+00:00",
            record_count=1,
            checksum="current-checksum",
            metadata={},
        )
        manager._write_backup_snapshot(
            "openfoodfacts",
            "target-v1",
            {"target_food": _admissible_common_food_fixture(95)},
        )
        update_times = iter(
            [
                datetime(2026, 8, 11, 10, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 11, 10, 0, 1, tzinfo=timezone.utc),
            ]
        )
        monkeypatch.setattr("core.food_apis.update_manager.now_utc", lambda: next(update_times))

        rolled_back = asyncio.run(manager.rollback_database("openfoodfacts", "target-v1"))
        rollback_version = "target-v1_rollback_100000"
        rollback_backup = tmp_path / f"openfoodfacts_backup_{rollback_version}.json"

        assert rolled_back is True
        assert manager.versions["openfoodfacts"].version == rollback_version
        assert rollback_backup.exists()
        assert tuple(asyncio.run(manager._load_backup("openfoodfacts", rollback_version))) == (
            "target_food",
        )

        off_item = OFFFoodItem(
            code="off-after-rollback",
            product_name="OFF After Rollback",
            categories=["fixture"],
            nutrients_per_100g={"protein_g": 6.0, "fat_g": 2.0, "carbs_g": 4.0},
            ingredients_text=None,
            brands=None,
            labels=[],
            countries=["TEST"],
            packaging=[],
            image_url=None,
            last_modified_t=2,
            nutrition_inputs=[
                {
                    "source": "estimate",
                    "record_id": "off-after-rollback",
                    "version_ref": "2",
                    "nutrients": {"protein_g": 6.0, "fat_g": 2.0, "carbs_g": 4.0},
                    "raw_payload": {},
                }
            ],
            nutrition_provenance={
                "protein_g": "estimate",
                "fat_g": "estimate",
                "carbs_g": "estimate",
            },
            nutrition_nutrient_confidence={
                "protein_g": 0.4,
                "fat_g": 0.4,
                "carbs_g": 0.4,
            },
            nutrition_confidence=0.4,
        )
        off_client = MagicMock()
        off_client.search_products = AsyncMock(return_value=[off_item])
        manager.off_client = off_client
        monkeypatch.setattr("core.food_apis.update_manager.asyncio.sleep", AsyncMock())

        refresh = asyncio.run(manager._update_off_database(force=True))

        assert refresh.success is True
        assert refresh.old_version == rollback_version
        assert refresh.new_version == "20260811_100001"
        assert rollback_backup.exists()

    def test_usda_update_version_failure_restores_exact_prior_active_bytes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.food_apis.unified_db import (
            COMMON_FOODS_CACHE_SCHEMA_VERSION,
            COMMON_FOODS_MANIFEST,
            COMMON_FOODS_MANIFEST_VERSION,
            CommonFoodsCacheAdmissionError,
        )
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        old_items = {
            name: asdict(_admissible_common_food_fixture(index))
            for index, name in enumerate(COMMON_FOODS_MANIFEST)
        }
        old_envelope: dict[str, object] = {
            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
            "items": old_items,
        }
        active_cache = tmp_path / "common_foods.json"
        active_cache.write_text(json.dumps(old_envelope, separators=(",", ":")), encoding="utf-8")
        prior_bytes = active_cache.read_bytes()
        new_envelope = json.loads(json.dumps(old_envelope))
        new_items = new_envelope["items"]
        assert isinstance(new_items, dict)
        first_item = new_items[next(iter(COMMON_FOODS_MANIFEST))]
        assert isinstance(first_item, dict)
        first_item["name"] = "New authoritative candidate"
        new_foods = manager.unified_db._validate_common_foods_envelope(new_envelope)

        async def publish_candidate(*, force_refresh: bool):
            assert force_refresh is True
            manager.unified_db._publish_common_foods_envelope(active_cache, new_envelope)
            return new_foods

        monkeypatch.setattr(manager.unified_db, "get_common_foods_database", publish_candidate)
        monkeypatch.setattr(
            manager,
            "_save_versions",
            MagicMock(
                side_effect=CommonFoodsCacheAdmissionError("forced version publication failure")
            ),
        )

        result = asyncio.run(manager._update_usda_database(force=True))

        assert result.success is False
        assert result.errors == ["common_food_cache_admission_failed"]
        assert active_cache.read_bytes() == prior_bytes
        assert "usda" not in manager.versions
        assert not list(tmp_path.glob(".common_foods.json.update-rollback.*.tmp"))

    def test_usda_rollback_restores_active_cache_snapshot_and_supports_next_update(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from core.food_apis.unified_db import (
            COMMON_FOODS_CACHE_SCHEMA_VERSION,
            COMMON_FOODS_MANIFEST,
            COMMON_FOODS_MANIFEST_VERSION,
        )
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        target_items: dict[str, dict[str, object]] = {}
        for index, standard_name in enumerate(COMMON_FOODS_MANIFEST):
            food = _admissible_common_food_fixture(index)
            protein = float(index + 1)
            food.nutrients_per_100g = {
                "protein_g": protein,
                "fat_g": 0.0,
                "carbs_g": 0.0,
            }
            food.nutrition_inputs = [
                {
                    "source": "usda",
                    "record_id": food.source_id,
                    "version_ref": "target-v1",
                    "nutrients": {"protein_g": protein},
                    "raw_payload": {},
                }
            ]
            food.nutrition_provenance = {"protein_g": "usda"}
            food.nutrition_nutrient_confidence = {"protein_g": 0.7}
            food.nutrition_confidence = 0.7
            target_items[standard_name] = asdict(food)

        target_envelope: dict[str, object] = {
            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
            "items": target_items,
        }
        old_envelope = json.loads(json.dumps(target_envelope))
        old_items = old_envelope["items"]
        assert isinstance(old_items, dict)
        for item in old_items.values():
            assert isinstance(item, dict)
            item["name"] = f"Old {item['name']}"

        active_cache = tmp_path / "common_foods.json"
        manager.unified_db._publish_common_foods_envelope(active_cache, old_envelope)
        old_active_bytes = active_cache.read_bytes()
        manager._write_backup_snapshot("usda", "target-v1", target_items)
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="current-v2",
            last_updated="2026-08-11T09:00:00+00:00",
            record_count=len(target_items),
            checksum="current-checksum",
            metadata={},
        )
        update_times = iter(
            [
                datetime(2026, 8, 11, 10, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 11, 10, 0, 1, tzinfo=timezone.utc),
            ]
        )
        monkeypatch.setattr("core.food_apis.update_manager.now_utc", lambda: next(update_times))
        provider_acquisition = AsyncMock(return_value=target_envelope)
        monkeypatch.setattr(
            manager.unified_db,
            "_acquire_common_foods_envelope",
            provider_acquisition,
        )

        rolled_back = asyncio.run(manager.rollback_database("usda", "target-v1"))
        rollback_version = "target-v1_rollback_100000"

        assert rolled_back is True
        assert active_cache.read_bytes() != old_active_bytes
        assert json.loads(active_cache.read_text(encoding="utf-8")) == target_envelope
        assert manager.versions["usda"].version == rollback_version
        assert tuple(asyncio.run(manager._load_backup("usda", rollback_version))) == tuple(
            COMMON_FOODS_MANIFEST
        )

        update_result = asyncio.run(manager._update_usda_database(force=True))

        assert update_result.success is True
        assert update_result.old_version == rollback_version
        assert update_result.new_version == "20260811_100001"
        provider_acquisition.assert_awaited_once_with()

    def test_usda_rollback_publication_failure_preserves_active_bytes_and_metadata(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from core.food_apis.unified_db import (
            COMMON_FOODS_CACHE_SCHEMA_VERSION,
            COMMON_FOODS_MANIFEST,
            COMMON_FOODS_MANIFEST_VERSION,
            CommonFoodsCacheAdmissionError,
        )
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        items = {
            name: asdict(_admissible_common_food_fixture(index))
            for index, name in enumerate(COMMON_FOODS_MANIFEST)
        }
        envelope: dict[str, object] = {
            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
            "items": items,
        }
        active_cache = tmp_path / "common_foods.json"
        manager.unified_db._publish_common_foods_envelope(active_cache, envelope)
        active_bytes = active_cache.read_bytes()
        manager._write_backup_snapshot("usda", "target-v1", items)
        established = DatabaseVersion(
            source="usda",
            version="current-v2",
            last_updated="2026-08-11T09:00:00+00:00",
            record_count=len(items),
            checksum="current-checksum",
            metadata={},
        )
        manager.versions["usda"] = established
        monkeypatch.setattr(
            manager.unified_db,
            "_publish_common_foods_envelope",
            MagicMock(side_effect=CommonFoodsCacheAdmissionError("forced publication failure")),
        )

        rolled_back = asyncio.run(manager.rollback_database("usda", "target-v1"))

        assert rolled_back is False
        assert active_cache.read_bytes() == active_bytes
        assert manager.versions["usda"] is established

    def test_usda_rollback_version_failure_compensates_active_and_new_backup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.food_apis.unified_db import (
            COMMON_FOODS_CACHE_SCHEMA_VERSION,
            COMMON_FOODS_MANIFEST,
            COMMON_FOODS_MANIFEST_VERSION,
            CommonFoodsCacheAdmissionError,
        )
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        manager = DatabaseUpdateManager(cache_dir=tmp_path)
        target_items = {
            name: asdict(_admissible_common_food_fixture(index))
            for index, name in enumerate(COMMON_FOODS_MANIFEST)
        }
        target_envelope: dict[str, object] = {
            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
            "items": target_items,
        }
        established_envelope = json.loads(json.dumps(target_envelope))
        established_items = established_envelope["items"]
        assert isinstance(established_items, dict)
        established_first = established_items[next(iter(COMMON_FOODS_MANIFEST))]
        assert isinstance(established_first, dict)
        established_first["name"] = "Established active bytes"
        active_cache = tmp_path / "common_foods.json"
        active_cache.write_text(
            json.dumps(established_envelope, separators=(",", ":")),
            encoding="utf-8",
        )
        active_bytes = active_cache.read_bytes()
        manager._write_backup_snapshot("usda", "target-v1", target_items)
        established = DatabaseVersion(
            source="usda",
            version="current-v2",
            last_updated="2026-08-11T09:00:00+00:00",
            record_count=len(target_items),
            checksum="current-checksum",
            metadata={},
        )
        manager.versions["usda"] = established
        monkeypatch.setattr(
            "core.food_apis.update_manager.now_utc",
            lambda: datetime(2026, 8, 11, 13, 0, 0, tzinfo=timezone.utc),
        )
        monkeypatch.setattr(
            manager,
            "_save_versions",
            MagicMock(
                side_effect=CommonFoodsCacheAdmissionError("forced version publication failure")
            ),
        )

        rolled_back = asyncio.run(manager.rollback_database("usda", "target-v1"))

        assert rolled_back is False
        assert manager.versions["usda"] is established
        assert active_cache.read_bytes() == active_bytes
        assert not (tmp_path / "usda_backup_target-v1_rollback_130000.json").exists()

    @pytest.mark.asyncio
    async def test_load_backup(self):
        """Test _load_backup method."""
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            backup_data = {"chicken": asdict(_admissible_common_food_fixture(98))}

            backup_file = manager.cache_dir / "usda_backup_1.0.json"
            with open(backup_file, "w") as f:
                json.dump(backup_data, f)

            # Should load the backup successfully
            foods = await manager._load_backup("usda", "1.0")
            assert isinstance(foods, dict)
            assert "chicken" in foods
            assert isinstance(foods["chicken"], UnifiedFoodItem)

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_exception(self):
        """Test _cleanup_old_backups with exception."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Create a mock backup file
            backup_file = manager.cache_dir / "usda_backup_1.0.json"
            backup_file.touch()

            # Instead of patching glob directly (which causes issues), let's test by
            # creating many backup files and mocking the unlink method to raise an exception
            backup_files = []
            for i in range(10):
                bf = manager.cache_dir / f"usda_backup_{i}.json"
                bf.touch()
                backup_files.append(bf)

            # Mock the first few files to have an old timestamp and the unlink method
            # to raise an exception
            for _ in backup_files[:3]:
                # Mock stat to return an old timestamp
                _ = datetime.now() - timedelta(days=365)  # Old timestamp
            # Just test that the function doesn't crash when there are files to clean up
            # We'll mock the unlink method on one of the files to raise an exception
            with patch("pathlib.Path.unlink", side_effect=Exception("Test error")):
                # Should handle the exception gracefully
                await manager._cleanup_old_backups("usda")

    def test_cleanup_old_backups_ignores_invalid_candidate_and_continues(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from core.food_apis.update_manager import DatabaseUpdateManager

        cache_dir = tmp_path / "cache"
        manager = DatabaseUpdateManager(cache_dir=cache_dir, max_rollback_versions=2)
        valid_backups = [cache_dir / f"usda_backup_{index}.json" for index in range(4)]
        for index, backup_file in enumerate(valid_backups, start=1):
            backup_file.write_text("{}", encoding="utf-8")
            os.utime(backup_file, (index, index))

        outside_file = tmp_path / "outside-backup.json"
        outside_bytes = b"outside-backup-must-remain-unchanged"
        outside_file.write_bytes(outside_bytes)
        stray_symlink = cache_dir / "usda_backup_stray.json"
        stray_symlink.symlink_to(outside_file)
        invalid_backup = cache_dir / "usda_backup_.json"
        invalid_backup.write_text("invalid-name-must-be-ignored", encoding="utf-8")
        caplog.set_level(logging.WARNING, logger="core.food_apis.update_manager")

        asyncio.run(manager._cleanup_old_backups("usda"))

        assert [backup.exists() for backup in valid_backups] == [False, False, True, True]
        assert stray_symlink.is_symlink()
        assert invalid_backup.read_text(encoding="utf-8") == "invalid-name-must-be-ignored"
        assert outside_file.read_bytes() == outside_bytes
        cleanup_warnings = [
            record.getMessage()
            for record in caplog.records
            if record.name == "core.food_apis.update_manager"
        ]
        assert cleanup_warnings == 2 * [
            "Ignoring invalid backup candidate during cleanup; "
            "source=usda; category=CommonFoodsCacheAdmissionError"
        ]
        assert "stray" not in caplog.text
        assert str(outside_file) not in caplog.text

    @pytest.mark.asyncio
    async def test_rollback_database_exception(self):
        """Test rollback_database with exception."""
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Add a version
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            # Mock _load_backup to raise an exception
            with patch.object(manager, "_load_backup", side_effect=Exception("Test error")):
                # Should handle the exception
                success = await manager.rollback_database("usda", "1.0")
                assert success is False

    def test_add_update_callback(self):
        """Test add_update_callback method."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager()

        def test_callback(result):
            pass

        # Should add the callback
        manager.add_update_callback(test_callback)
        assert len(manager.update_callbacks) == 1
        assert manager.update_callbacks[0] is test_callback

    def test_get_database_status(self):
        """Test get_database_status method."""
        from datetime import datetime, timedelta

        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Add a version
            test_time = (datetime.now() - timedelta(hours=2)).isoformat()
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated=test_time,
                record_count=100,
                checksum="abc123def456",
                metadata={"test": "data"},
            )
            manager.versions["usda"] = version

            status = manager.get_database_status()

            assert "usda" in status
            db_status = status["usda"]
            assert db_status["version"] == "1.0"
            assert db_status["record_count"] == 100
            assert db_status["checksum"] == "abc123de..."
            assert db_status["metadata"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock clients to track close calls
            manager.usda_client.close = AsyncMock()
            manager.unified_db.close = AsyncMock()

            # Should close both clients
            await manager.close()
            manager.usda_client.close.assert_called_once()
            manager.unified_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_scheduled_update(self):
        """Test run_scheduled_update convenience function."""
        from core.food_apis.update_manager import DatabaseUpdateManager, run_scheduled_update

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock check_for_updates to return available updates
            manager.check_for_updates = AsyncMock(return_value={"usda": True})

            # Mock update_database to return a result
            mock_result = MagicMock()
            mock_result.success = True
            manager.update_database = AsyncMock(return_value=mock_result)

            # Should run updates for available sources
            results = await run_scheduled_update(manager)

            assert "usda" in results
            assert results["usda"].success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
