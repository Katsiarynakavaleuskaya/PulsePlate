"""Test that lenient API key mode warning is logged only once."""

import logging
import os
from unittest.mock import patch

import pytest


class TestLenientModeWarning:
    """Test lenient API key mode warning behavior."""

    def test_lenient_mode_warning_logged_only_once(self, monkeypatch, caplog):
        """Verify that lenient mode warning is logged only once, not on every call."""
        # Set up environment for lenient mode
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.delenv("API_KEY", raising=False)

        # Import fresh to reset the warning flag
        import importlib
        import app as app_module

        # Reset the warning flag
        app_module._lenient_mode_warning_logged = False
        importlib.reload(app_module)

        # Capture logs at WARNING level
        with caplog.at_level(logging.WARNING):
            # Call get_api_key multiple times
            for _ in range(5):
                try:
                    app_module.get_api_key("test-valid-key")
                except Exception:
                    pass  # Ignore exceptions, we're testing logging

        # Check that warning appears exactly once
        warning_messages = [
            record.message
            for record in caplog.records
            if "Lenient API key mode enabled" in record.message
        ]

        assert len(warning_messages) == 1, (
            f"Expected warning to be logged exactly once, "
            f"but found {len(warning_messages)} occurrences"
        )

    def test_lenient_mode_warning_content(self, monkeypatch, caplog):
        """Verify the warning message contains the expected security notice."""
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.delenv("API_KEY", raising=False)

        # Import fresh
        import importlib
        import app as app_module

        # Reset the warning flag
        app_module._lenient_mode_warning_logged = False
        importlib.reload(app_module)

        with caplog.at_level(logging.WARNING):
            try:
                app_module.get_api_key("test-valid-key")
            except Exception:
                pass

        # Verify warning message content
        warning_messages = [
            record.message
            for record in caplog.records
            if "Lenient API key mode enabled" in record.message
        ]

        assert len(warning_messages) > 0, "Expected warning to be logged"
        assert "development only" in warning_messages[0]
        assert "no real security" in warning_messages[0]
