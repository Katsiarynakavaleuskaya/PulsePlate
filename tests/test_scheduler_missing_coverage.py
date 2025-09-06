"""
Additional tests to cover missing lines in core/food_apis/scheduler.py.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.scheduler import (
    DatabaseUpdateScheduler,
    start_background_updates,
    stop_background_updates,
)


class TestSchedulerMissingCoverage:
    """Tests to cover missing lines in scheduler.py."""

    def test_setup_signal_handlers_success(self):
        """Test _setup_signal_handlers success case."""
        scheduler = DatabaseUpdateScheduler()

        # Mock signal.signal to succeed
        with patch("core.food_apis.scheduler.signal.signal") as mock_signal:
            scheduler._setup_signal_handlers()
            # Should call signal.signal twice (for SIGTERM and SIGINT)
            assert mock_signal.call_count == 2

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test start when already running."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await scheduler.start()
            # Should log warning that scheduler is already running
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test start success case."""
        scheduler = DatabaseUpdateScheduler()

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await scheduler.start()
            # Should set is_running to True
            assert scheduler.is_running is True
            # Should log that scheduler started
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop when not running."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = False

        # Should not crash and should return immediately
        await scheduler.stop()
        # is_running should still be False
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_stop_with_running_task(self):
        """Test stop with running task."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        # Create a proper async task that we can cancel
        async def dummy_task():
            await asyncio.sleep(0.1)

        task = asyncio.create_task(dummy_task())
        scheduler._update_task = task

        # Mock update_manager.close
        scheduler.update_manager.close = AsyncMock()

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await scheduler.stop()
            # Should close update manager
            scheduler.update_manager.close.assert_called_once()
            # Should log that scheduler stopped
            mock_logger.info.assert_called_with("Database update scheduler stopped")

    @pytest.mark.asyncio
    async def test_update_loop_sleep_path(self):
        """Test _update_loop sleep path when no updates needed."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        # Mock datetime.now
        with patch("core.food_apis.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            # Mock _should_check_for_updates to return False
            scheduler._should_check_for_updates = MagicMock(return_value=False)
            scheduler.last_update_check = datetime(2023, 1, 1, 11, 0, 0)

            # Mock asyncio.sleep to break the loop after one iteration
            with patch(
                "core.food_apis.scheduler.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()  # Break the loop

                try:
                    await scheduler._update_loop()
                except asyncio.CancelledError:
                    pass

    def test_should_check_for_updates_none_last_check(self):
        """Test _should_check_for_updates with None last_update_check."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.last_update_check = None

        result = scheduler._should_check_for_updates(datetime(2023, 1, 1, 12, 0, 0))
        # Should return True when last_update_check is None
        assert result is True

    def test_should_check_for_updates_interval_not_passed(self):
        """Test _should_check_for_updates when interval has not passed."""
        scheduler = DatabaseUpdateScheduler()

        # Set last check to recent time
        scheduler.last_update_check = datetime(2023, 1, 1, 12, 0, 0)
        current_time = datetime(2023, 1, 1, 12, 30, 0)  # 30 minutes later

        result = scheduler._should_check_for_updates(current_time)
        # Should return False when interval has not passed (default is 24 hours)
        assert result is False

    def test_should_check_for_updates_interval_passed(self):
        """Test _should_check_for_updates when interval has passed."""
        scheduler = DatabaseUpdateScheduler()

        # Set last check to old time
        scheduler.last_update_check = datetime(2023, 1, 1, 12, 0, 0)
        current_time = datetime(2023, 1, 2, 13, 0, 0)  # 25 hours later

        result = scheduler._should_check_for_updates(current_time)
        # Should return True when interval has passed
        assert result is True

    @pytest.mark.asyncio
    async def test_run_update_check_no_updates_available(self):
        """Test _run_update_check when no updates available."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates to return no updates
        scheduler.update_manager.check_for_updates = AsyncMock(
            return_value={"usda": False}
        )

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await scheduler._run_update_check()
            # Should log that no updates are available
            mock_logger.info.assert_called_with("No database updates available")

    @pytest.mark.asyncio
    async def test_run_source_update_success(self):
        """Test _run_source_update success case."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.update_database to return success
        from core.food_apis.update_manager import UpdateResult

        mock_result = UpdateResult(
            success=True,
            source="usda",
            old_version="1.0",
            new_version="1.1",
            records_added=10,
            records_updated=5,
            records_removed=0,
            errors=[],
            duration_seconds=1.0,
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await scheduler._run_source_update("usda")
            # Should reset retry count on success
            assert scheduler.retry_counts.get("usda", 0) == 0
            # Should log success message
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_run_source_update_failure(self):
        """Test _run_source_update failure case."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.update_database to return failure
        from core.food_apis.update_manager import UpdateResult

        mock_result = UpdateResult(
            success=False,
            source="usda",
            old_version="1.0",
            new_version=None,
            records_added=0,
            records_updated=0,
            records_removed=0,
            errors=["Test error"],
            duration_seconds=1.0,
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        await scheduler._run_source_update("usda")
        # Should increment retry count on failure
        assert scheduler.retry_counts.get("usda", 0) == 1

    def test_on_update_complete_success(self):
        """Test _on_update_complete with success result."""
        scheduler = DatabaseUpdateScheduler()

        from core.food_apis.update_manager import UpdateResult

        success_result = UpdateResult(
            success=True,
            source="usda",
            old_version="1.0",
            new_version="1.1",
            records_added=0,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=1.0,
        )

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            scheduler._on_update_complete(success_result)
            # Should log success message
            mock_logger.info.assert_called()

    def test_on_update_complete_failure(self):
        """Test _on_update_complete with failure result."""
        scheduler = DatabaseUpdateScheduler()

        from core.food_apis.update_manager import UpdateResult

        failure_result = UpdateResult(
            success=False,
            source="usda",
            old_version="1.0",
            new_version=None,
            records_added=0,
            records_updated=0,
            records_removed=0,
            errors=["Test error"],
            duration_seconds=1.0,
        )

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            scheduler._on_update_complete(failure_result)
            # Should log warning message
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_force_update_all_sources_path(self):
        """Test force_update with all sources path."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates
        scheduler.update_manager.check_for_updates = AsyncMock(
            return_value={"usda": True}
        )

        # Mock update_manager.update_database
        from core.food_apis.update_manager import UpdateResult

        mock_result = UpdateResult(
            success=True,
            source="usda",
            old_version="1.0",
            new_version="1.1",
            records_added=0,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=1.0,
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        results = await scheduler.force_update()  # No source specified
        # Should return results for all sources
        assert "usda" in results
        assert results["usda"].success is True

    def test_get_status_with_none_last_update_check(self):
        """Test get_status with None last_update_check."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.last_update_check = None

        status = scheduler.get_status()
        # Should handle None last_update_check gracefully
        assert status["scheduler"]["last_update_check"] is None

    @pytest.mark.asyncio
    async def test_start_background_updates_already_running(self):
        """Test start_background_updates when already running."""
        # First call to get the global instance
        from core.food_apis.scheduler import get_update_scheduler

        scheduler = await get_update_scheduler()
        scheduler.is_running = True  # Mark as running

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await start_background_updates(1)
            # Should not start if already running
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_background_updates_not_running(self):
        """Test stop_background_updates when not running."""
        # First call to get the global instance
        from core.food_apis.scheduler import get_update_scheduler

        scheduler = await get_update_scheduler()
        scheduler.is_running = False  # Mark as not running

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await stop_background_updates()
            # Should not log stop message if not running
            mock_logger.info.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
