"""
Additional tests to improve coverage for scheduler.py to reach 97%+.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.scheduler import (
    DatabaseUpdateScheduler,
    get_update_scheduler,
    start_background_updates,
    stop_background_updates,
)
from core.food_apis.update_manager import UpdateResult


class TestSchedulerCoverage:
    """Additional tests to improve coverage for DatabaseUpdateScheduler."""

    def test_setup_signal_handlers_exception(self):
        """Test signal handler setup with exception."""
        scheduler = DatabaseUpdateScheduler()

        # Mock signal.signal to raise an exception
        with patch('core.food_apis.scheduler.signal.signal', side_effect=Exception("Test error")):
            # Should not crash
            scheduler._setup_signal_handlers()
            # Should log warning (we can't easily test logging, but at least it shouldn't crash)

    @pytest.mark.asyncio
    async def test_update_loop_cancelled_error(self):
        """Test update loop handling of CancelledError."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        # Mock datetime.now to return consistent values
        with patch('core.food_apis.scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock _should_check_for_updates to return True
            scheduler._should_check_for_updates = MagicMock(return_value=True)

            # Mock _run_update_check to raise CancelledError
            scheduler._run_update_check = AsyncMock(side_effect=asyncio.CancelledError())

            # Mock asyncio.sleep to avoid waiting
            with patch('core.food_apis.scheduler.asyncio.sleep', new_callable=AsyncMock):
                # Should not crash
                await scheduler._update_loop()

    @pytest.mark.asyncio
    async def test_update_loop_general_exception(self):
        """Test update loop handling of general exceptions."""
        scheduler = DatabaseUpdateScheduler()
        scheduler.is_running = True

        # Mock datetime.now to return consistent values
        with patch('core.food_apis.scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock _should_check_for_updates to return True
            scheduler._should_check_for_updates = MagicMock(return_value=True)

            # Mock _run_update_check to raise a general exception
            scheduler._run_update_check = AsyncMock(side_effect=Exception("Test error"))

            # Mock asyncio.sleep to control execution
            with patch('core.food_apis.scheduler.asyncio.sleep', new_callable=AsyncMock):
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
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates to raise an exception
        scheduler.update_manager.check_for_updates = AsyncMock(side_effect=Exception("Test error"))

        # Should not crash
        await scheduler._run_update_check()

    @pytest.mark.asyncio
    async def test_run_source_update_exception(self):
        """Test _run_source_update handling of exceptions."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.update_database to raise an exception
        scheduler.update_manager.update_database = AsyncMock(side_effect=Exception("Test error"))

        # Should handle the exception gracefully
        await scheduler._run_source_update("test_source")

        # Should increment retry count
        assert scheduler.retry_counts.get("test_source", 0) == 1

    def test_handle_update_failure_max_retries(self):
        """Test _handle_update_failure when max retries exceeded."""
        scheduler = DatabaseUpdateScheduler(max_retries=2)
        scheduler.retry_counts["test_source"] = 2  # Already at max retries

        # Should reset retry count when max exceeded
        scheduler._handle_update_failure("test_source", ["Test error"])
        assert scheduler.retry_counts.get("test_source", 0) == 0

    def test_handle_update_failure_increment(self):
        """Test _handle_update_failure incrementing retry count."""
        scheduler = DatabaseUpdateScheduler(max_retries=3)
        scheduler.retry_counts["test_source"] = 1

        # Should increment retry count
        scheduler._handle_update_failure("test_source", ["Test error"])
        assert scheduler.retry_counts.get("test_source", 0) == 2

    def test_on_update_complete(self):
        """Test _on_update_complete callback."""
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
            duration_seconds=1.0
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
            duration_seconds=1.0
        )

        # Should not crash
        scheduler._on_update_complete(failure_result)

    @pytest.mark.asyncio
    async def test_force_update_specific_source(self):
        """Test force_update with specific source."""
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
            duration_seconds=1.0
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        # Test with specific source
        results = await scheduler.force_update("test_source")

        assert "test_source" in results
        assert results["test_source"].success is True

    @pytest.mark.asyncio
    async def test_force_update_all_sources(self):
        """Test force_update with all sources."""
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
            duration_seconds=1.0
        )
        scheduler.update_manager.update_database = AsyncMock(return_value=mock_result)

        # Test with all sources
        results = await scheduler.force_update()

        assert "test_source" in results
        assert results["test_source"].success is True

    def test_get_status(self):
        """Test get_status method."""
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
            metadata={"test": "data"}
        )
        scheduler.update_manager.versions["test_source"] = test_version

        # Mock update_manager.get_database_status
        scheduler.update_manager.get_database_status = MagicMock(return_value={
            "test_source": {
                "version": "1.0",
                "last_updated": "2023-01-01T10:00:00",
                "hours_since_update": 2.0,
                "record_count": 100,
                "checksum": "abc123...",
                "metadata": {"test": "data"}
            }
        })

        status = scheduler.get_status()

        assert "scheduler" in status
        assert "databases" in status
        assert status["scheduler"]["is_running"] is False
        assert status["scheduler"]["retry_counts"]["test_source"] == 2

    @pytest.mark.asyncio
    async def test_global_scheduler_functions(self):
        """Test global scheduler functions."""
        # Test get_update_scheduler
        scheduler1 = await get_update_scheduler()
        scheduler2 = await get_update_scheduler()

        # Should return the same instance
        assert scheduler1 is scheduler2

        # Test start_background_updates
        with patch('core.food_apis.scheduler.logger') as mock_logger:
            await start_background_updates(1)  # 1 hour interval
            # Should log that updates started
            mock_logger.info.assert_called()

        # Test stop_background_updates
        with patch('core.food_apis.scheduler.logger') as mock_logger:
            await stop_background_updates()
            # Should log that updates stopped
            mock_logger.info.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
