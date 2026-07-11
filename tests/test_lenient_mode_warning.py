"""Test that the canonical lenient API-key warning is process-once."""

import logging
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator

import pytest
from app.routers import api_key as canonical_api_key


@pytest.fixture(autouse=True)
def reset_lenient_warning() -> Iterator[None]:
    canonical_api_key._reset_lenient_mode_warning_for_tests()
    yield
    canonical_api_key._reset_lenient_mode_warning_for_tests()


class TestLenientModeWarning:
    """Test lenient API key mode warning behavior.

    Note: Tests patch module __dict__ directly to isolate global state.
    We reset the flag to False before AND after each test to ensure proper isolation.
    """

    @staticmethod
    def _configure_lenient_env(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "dev")
        for name in (
            "API_KEY",
            "ENVIRONMENT",
            "API_KEY_REQUIRED",
            "ALLOW_DEV_API_KEY",
            "ALLOW_DEV_API_KEY_NORMALIZE",
        ):
            monkeypatch.delenv(name, raising=False)

    def test_lenient_mode_warning_logged_only_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify that lenient mode warning is logged only once, not on every call."""
        self._configure_lenient_env(monkeypatch)

        with caplog.at_level(logging.WARNING):
            for _ in range(5):
                canonical_api_key.get_api_key("test-valid-key")

        warning_messages = [
            record.message
            for record in caplog.records
            if "Lenient API key mode enabled" in record.message
        ]

        assert len(warning_messages) == 1

    def test_lenient_mode_warning_is_thread_safe(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        self._configure_lenient_env(monkeypatch)

        with caplog.at_level(logging.WARNING):
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(
                    executor.map(
                        canonical_api_key.get_api_key,
                        ["test-valid-key"] * 32,
                    )
                )

        assert results == ["test-valid-key"] * 32
        assert (
            sum("Lenient API key mode enabled" in record.message for record in caplog.records) == 1
        )

    def test_lenient_mode_warning_content(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify the warning message contains the expected security notice."""
        self._configure_lenient_env(monkeypatch)

        caplog.clear()

        with caplog.at_level(logging.WARNING):
            canonical_api_key.get_api_key("test-valid-key")

        warning_messages = [
            record.message
            for record in caplog.records
            if "Lenient API key mode enabled" in record.message
        ]

        assert warning_messages
        assert "development only" in warning_messages[0]
        assert "no real security" in warning_messages[0]
