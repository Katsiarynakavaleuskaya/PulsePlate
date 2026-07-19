"""
Targeted tests for app.py error paths and edge cases to reach 97%+ coverage.

Focuses on:
- Import error fallbacks in wrappers
- Background update sync/async paths
- Scheduler late-init path
- DB fallback production safety paths
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from tests.helpers.fast_update_stubs import patch_background_update_scheduler_targets


class TestAppErrorPaths97:
    """Tests for app.py error paths and edge cases."""

    def test_start_background_updates_no_running_loop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test start_background_updates when no event loop is running (sync path)."""
        import app

        mock_start = AsyncMock()
        patch_background_update_scheduler_targets(monkeypatch, start=mock_start)

        try:
            asyncio.get_running_loop()
            pytest.skip("Event loop already running, can't test sync path")
        except RuntimeError:
            pass

        app.start_background_updates(update_interval_hours=1)
        mock_start.assert_called_once()

    def test_stop_background_updates_no_running_loop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test stop_background_updates when no event loop is running (sync path)."""
        import app

        mock_stop = AsyncMock()
        patch_background_update_scheduler_targets(monkeypatch, stop=mock_stop)

        try:
            asyncio.get_running_loop()
            pytest.skip("Event loop already running, can't test sync path")
        except RuntimeError:
            pass

        app.stop_background_updates()
        mock_stop.assert_called_once()

    def test_reset_targets_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset_targets_cache clears the cache."""
        import app

        # Set cache values
        monkeypatch.setattr(app, "_targets_disabled_cache", True)
        monkeypatch.setattr(app, "_targets_disabled_cache_time", 123.0)

        app.reset_targets_cache()

        assert app._targets_disabled_cache is None
        assert app._targets_disabled_cache_time == 0.0
