"""Tests for legacy_app scheduler path without PYTEST_CURRENT_TEST.

Covers the normal (non-pytest) scheduler initialization path where
resolve_scheduler_starter and resolve_stop_callable are called.
"""

from __future__ import annotations

import importlib
import os
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
