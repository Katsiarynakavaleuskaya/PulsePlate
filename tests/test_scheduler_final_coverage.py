"""
Final tests to cover remaining lines in core/food_apis/scheduler.py.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.scheduler import DatabaseUpdateScheduler


class TestSchedulerFinalCoverage:
    """Final tests to cover remaining lines in scheduler.py."""

    def test_setup_signal_handlers_exception_detailed(self):
        """Test _setup_signal_handlers with exception in signal.signal."""
        scheduler = DatabaseUpdateScheduler()

        # Mock signal.signal to raise an exception on the first call but not the second
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            # Second call should succeed (we don't need to test it specifically)

        with patch('core.food_apis.scheduler.signal.signal', side_effect=side_effect):
            with patch('core.food_apis.scheduler.logger') as mock_logger:
                scheduler._setup_signal_handlers()
                # Should log warning when exception occurs
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_update_check_exception_detailed(self):
        """Test _run_update_check with exception in check_for_updates."""
        scheduler = DatabaseUpdateScheduler()

        # Mock update_manager.check_for_updates to raise an exception
        scheduler.update_manager.check_for_updates = AsyncMock(side_effect=Exception("Test error"))

        with patch('core.food_apis.scheduler.logger') as mock_logger:
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

        with patch('core.food_apis.scheduler.logger'):
            await scheduler._run_source_update("test_source")
            # Should log warning when exception occurs in _handle_update_failure
            # We need to check that retry count was incremented
            assert scheduler.retry_counts.get("test_source", 0) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
