"""Test that lenient API key mode warning is logged only once.

Note: These tests patch module __dict__ directly to isolate global module state
instead of using importlib.reload() to avoid breaking parallel tests.
"""

import logging

import pytest


class TestLenientModeWarning:
    """Test lenient API key mode warning behavior.

    Note: Tests patch module __dict__ directly to isolate global state.
    We reset the flag to False before AND after each test to ensure proper isolation.
    """

    def test_lenient_mode_warning_logged_only_once(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify that lenient mode warning is logged only once, not on every call."""
        # Set up environment for lenient mode
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.delenv("API_KEY", raising=False)

        import app as app_module
        import sys

        # The actual module with get_api_key is 'app_module', not the 'app' package
        actual_module = sys.modules.get("app_module") or app_module
        module_dict = actual_module.__dict__

        try:
            # Always reset to False before test
            module_dict["_lenient_mode_warning_logged"] = False

            # Capture logs at WARNING level
            with caplog.at_level(logging.WARNING):
                # Call get_api_key multiple times
                for i in range(5):
                    # get_api_key should not raise in lenient mode
                    actual_module.get_api_key("test-valid-key")

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
        finally:
            # Reset to False after test for next test isolation
            module_dict["_lenient_mode_warning_logged"] = False

    def test_lenient_mode_warning_content(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify the warning message contains the expected security notice."""
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.delenv("API_KEY", raising=False)

        import app as app_module
        import sys

        # The actual module with get_api_key is 'app_module', not the 'app' package
        actual_module = sys.modules.get("app_module") or app_module
        module_dict = actual_module.__dict__

        try:
            # Always reset to False before test
            module_dict["_lenient_mode_warning_logged"] = False

            # Clear any cached logs from previous tests
            caplog.clear()

            with caplog.at_level(logging.WARNING):
                # get_api_key should not raise in lenient mode
                actual_module.get_api_key("test-valid-key")

            # Verify warning message content
            warning_messages = [
                record.message
                for record in caplog.records
                if "Lenient API key mode enabled" in record.message
            ]

            assert len(warning_messages) > 0, "Expected warning to be logged"
            assert "development only" in warning_messages[0]
            assert "no real security" in warning_messages[0]
        finally:
            # Reset to False after test for next test isolation
            module_dict["_lenient_mode_warning_logged"] = False
