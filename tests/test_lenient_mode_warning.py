"""Test that lenient API key mode warning is logged only once."""

import logging


import pytest


class TestLenientModeWarning:
    """Test lenient API key mode warning behavior."""

    def test_lenient_mode_warning_logged_only_once(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify that lenient mode warning is logged only once, not on every call."""
        # Set up environment for lenient mode
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.delenv("API_KEY", raising=False)

        # Import fresh to reset the warning flag
        import importlib
        import app as app_module

        # Reload resets module state including the warning flag
        importlib.reload(app_module)

        # Capture logs at WARNING level
        with caplog.at_level(logging.WARNING):
            # Call get_api_key multiple times
            for i in range(5):
                # get_api_key should not raise in lenient mode
                app_module.get_api_key("test-valid-key")  # type: ignore[misc]

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

    def test_lenient_mode_warning_content(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify the warning message contains the expected security notice."""
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.delenv("API_KEY", raising=False)

        # Import fresh
        import importlib
        import app as app_module

        # Reload resets module state including the warning flag
        importlib.reload(app_module)

        with caplog.at_level(logging.WARNING):
            # get_api_key should not raise in lenient mode
            app_module.get_api_key("test-valid-key")  # type: ignore[misc]

        # Verify warning message content
        warning_messages = [
            record.message
            for record in caplog.records
            if "Lenient API key mode enabled" in record.message
        ]

        assert len(warning_messages) > 0, "Expected warning to be logged"
        assert "development only" in warning_messages[0]
        assert "no real security" in warning_messages[0]
