import os

"""
Final tests to cover remaining lines in core/food_apis/scheduler.py.
"""

from unittest.mock import AsyncMock, patch

import pytest

from core.food_apis.scheduler import DatabaseUpdateScheduler


class TestSchedulerFinalCoverage:
    """Final tests to cover remaining lines in scheduler.py."""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_setup_signal_handlers_skipped_in_test_runtime(self):
        """Test _setup_signal_handlers is skipped in test runtime."""
        scheduler = DatabaseUpdateScheduler()

        with patch("core.food_apis.scheduler.signal.signal") as mock_signal:
            with patch("core.food_apis.scheduler.logger") as mock_logger:
                scheduler._setup_signal_handlers()
                # RU: В тестах signal handlers не устанавливаются (ранний return).
                # EN: In test runtime signal handlers are not set up (early return).
                mock_signal.assert_not_called()
                mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_update_check_exception_detailed(self):
        """Test _run_update_check with exception in check_for_updates."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates to raise an exception
        scheduler.update_manager.check_for_updates = AsyncMock(side_effect=Exception("Test error"))

        with patch("core.food_apis.scheduler.logger") as mock_logger:
            await scheduler._run_update_check()
            # Should log error when exception occurs
            mock_logger.error.assert_called_once()
            # Error message should contain the exception details
            call_args = mock_logger.error.call_args
            assert "Test error" in str(call_args)

    @pytest.mark.asyncio
    async def test_run_source_update_exception_detailed(self):
        """Test _run_source_update with exception in update_database."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.update_database to raise an exception
        scheduler.update_manager.update_database = AsyncMock(side_effect=Exception("Test error"))

        with patch("core.food_apis.scheduler.logger"):
            await scheduler._run_source_update("test_source")
            # Should log warning when exception occurs in _handle_update_failure
            # We need to check that retry count was incremented
            assert scheduler.retry_counts.get("test_source", 0) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
