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

    @pytest.mark.asyncio
    async def test_get_update_scheduler_late_import(self) -> None:
        """Test get_update_scheduler when _scheduler_getter is None (late import path)."""
        import app

        original_getter = app._scheduler_getter
        try:
            app._scheduler_getter = None
            # This triggers the late import path (lines 210-213)
            scheduler = await app.get_update_scheduler()  # type: ignore[misc]
            assert scheduler is not None
        finally:
            app._scheduler_getter = original_getter

    @pytest.mark.asyncio
    async def test_get_update_scheduler_test_override(self) -> None:
        """Test get_update_scheduler with _test_scheduler_override set."""
        import app

        mock_scheduler = AsyncMock()
        original_override = app._test_scheduler_override

        async def fake_override():
            return mock_scheduler

        try:
            app._test_scheduler_override = fake_override
            result = await app.get_update_scheduler()  # type: ignore[misc]
            assert result is mock_scheduler
        finally:
            app._test_scheduler_override = original_override

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

    def test_resolve_app_callable_fallback(self) -> None:
        """Test _resolve_app_callable when attribute not found, returns default."""
        import app

        result = app._resolve_app_callable("nonexistent_attr_12345", default=lambda: "default")
        assert callable(result)
        assert result() == "default"

    def test_reset_safety_failure_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset_safety_failure_count resets the global counter."""
        import app

        # Increment counter (simulate failures)
        monkeypatch.setattr(app, "_safety_failure_count", 5)

        app.reset_safety_failure_count()
        assert app._safety_failure_count == 0

    def test_reset_targets_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset_targets_cache clears the cache."""
        import app

        # Set cache values
        monkeypatch.setattr(app, "_targets_disabled_cache", True)
        monkeypatch.setattr(app, "_targets_disabled_cache_time", 123.0)

        app.reset_targets_cache()

        assert app._targets_disabled_cache is None
        assert app._targets_disabled_cache_time == 0.0
