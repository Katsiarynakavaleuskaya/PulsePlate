"""Tests for legacy_app scheduler path without PYTEST_CURRENT_TEST.

Covers the normal (non-pytest) scheduler initialization path where
resolve_scheduler_starter and resolve_stop_callable are called.
"""

from __future__ import annotations

import importlib
import os
from types import ModuleType
from typing import Any
from unittest.mock import Mock

import pytest

import legacy_app


def test_scheduler_path_without_pytest_current_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that scheduler resolvers are called when PYTEST_CURRENT_TEST is not set."""
    # Ensure PYTEST_CURRENT_TEST is not set
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # Mock the resolver functions to track calls
    mock_resolve_starter = Mock(name="resolve_scheduler_starter", return_value=Mock())
    mock_resolve_stopper = Mock(name="resolve_stop_callable", return_value=Mock())

    # Mock execute_async_starter and safe_stop_with_cleanup to prevent actual execution
    mock_execute_starter = Mock(name="execute_async_starter")
    mock_safe_stop = Mock(name="safe_stop_with_cleanup")

    # Patch the resolver functions in legacy_app module
    monkeypatch.setattr(legacy_app, "resolve_scheduler_starter", mock_resolve_starter, raising=True)
    monkeypatch.setattr(legacy_app, "resolve_stop_callable", mock_resolve_stopper, raising=True)
    monkeypatch.setattr(legacy_app, "execute_async_starter", mock_execute_starter, raising=True)
    monkeypatch.setattr(legacy_app, "safe_stop_with_cleanup", mock_safe_stop, raising=True)

    # Verify that functions are available
    assert hasattr(legacy_app, "resolve_scheduler_starter")
    assert hasattr(legacy_app, "resolve_stop_callable")
    assert hasattr(legacy_app, "start_background_updates")
    assert hasattr(legacy_app, "stop_background_updates")

    # Call the functions to trigger resolver calls (normal mode, not pytest sync mode)
    legacy_app.start_background_updates(update_interval_hours=24)
    legacy_app.stop_background_updates()

    # Verify resolvers were called (they are called in normal mode, not in pytest sync mode)
    assert mock_resolve_starter.called, "resolve_scheduler_starter should be called in normal mode"
    assert mock_resolve_stopper.called, "resolve_stop_callable should be called in normal mode"


def test_scheduler_pytest_sync_prefers_package_ref_for_app_module_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover scheduler sync-mode fallback when sys.modules['app'] is the alias module."""
    alias_app = ModuleType("app")
    package_app = ModuleType("app_package")
    package_app.__path__ = []  # mark as package-like for legacy_app fallback logic
    called: list[Any] = []

    def starter(update_interval_hours: int) -> None:
        called.append(("start", update_interval_hours))

    def stopper() -> None:
        called.append(("stop", None))

    package_app._scheduler_start_background_updates = starter
    package_app._scheduler_stop_background_updates = stopper
    monkeypatch.setitem(importlib.import_module("sys").modules, "app", alias_app)
    monkeypatch.setattr(legacy_app, "_APP_PACKAGE_REF", package_app, raising=False)

    legacy_app.start_background_updates(update_interval_hours=6)
    legacy_app.stop_background_updates()

    assert called == [("start", 6), 6, ("stop", None), "stop"]


def test_scheduler_pytest_sync_skips_noncallable_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover sync-mode candidate iteration before falling back to module globals."""
    called: list[Any] = []

    def starter(update_interval_hours: int) -> None:
        called.append(("start", update_interval_hours))

    def stopper() -> None:
        called.append(("stop", None))

    pkg = ModuleType("app")
    pkg.__path__ = []
    pkg._scheduler_start_background_updates = object()
    pkg._scheduler_stop_background_updates = object()
    app_module = ModuleType("app_module")
    app_module._scheduler_start_background_updates = object()
    app_module._scheduler_stop_background_updates = object()
    pkg.app_module = app_module

    monkeypatch.setitem(importlib.import_module("sys").modules, "app", pkg)
    monkeypatch.setattr(legacy_app, "_scheduler_start_background_updates", starter, raising=False)
    monkeypatch.setattr(legacy_app, "_scheduler_stop_background_updates", stopper, raising=False)

    legacy_app.start_background_updates(update_interval_hours=3)
    legacy_app.stop_background_updates()

    assert called == [("start", 3), 3, ("stop", None), "stop"]


def test_stop_background_updates_schedules_stopper_on_running_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover non-pytest stop path when an event loop is already running."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    scheduled: list[Any] = []

    async def stopper() -> None:
        scheduled.append("ran")

    class FakeLoop:
        def create_task(self, coro: Any) -> None:
            scheduled.append(coro)
            coro.close()

    class FakeAsyncio:
        @staticmethod
        def get_running_loop() -> FakeLoop:
            return FakeLoop()

    monkeypatch.setattr(legacy_app, "resolve_stop_callable", lambda *args: stopper, raising=True)
    monkeypatch.setattr(legacy_app, "asyncio", FakeAsyncio, raising=True)

    legacy_app.stop_background_updates()

    assert len(scheduled) == 1
