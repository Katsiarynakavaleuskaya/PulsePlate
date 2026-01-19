# -*- coding: utf-8 -*-
"""
Tests for shared router helpers.

RU: Тесты для общих вспомогательных функций роутеров.
EN: Tests for shared router helper functions.
"""

from __future__ import annotations

import pytest

from app.routers import _helpers


class TestEnvBool:
    """Tests for _env_bool helper."""

    def test_env_bool_default_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _env_bool returns default when env var is not set."""
        monkeypatch.delenv("X_TEST_BOOL", raising=False)
        assert _helpers._env_bool("X_TEST_BOOL", default=True) is True
        assert _helpers._env_bool("X_TEST_BOOL", default=False) is False

    @pytest.mark.parametrize("raw", ["1", "true", "t", "yes", "y", "on", " TRUE "])
    def test_env_bool_true_values(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        """Test _env_bool recognizes truthy values."""
        monkeypatch.setenv("X_TEST_BOOL", raw)
        assert _helpers._env_bool("X_TEST_BOOL", default=False) is True

    @pytest.mark.parametrize("raw", ["0", "false", "f", "no", "n", "off", " FALSE "])
    def test_env_bool_false_values(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        """Test _env_bool recognizes falsey values."""
        monkeypatch.setenv("X_TEST_BOOL", raw)
        assert _helpers._env_bool("X_TEST_BOOL", default=True) is False

    def test_env_bool_garbage_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _env_bool falls back to default for unrecognized values."""
        monkeypatch.setenv("X_TEST_BOOL", "maybe")
        assert _helpers._env_bool("X_TEST_BOOL", default=True) is True
        assert _helpers._env_bool("X_TEST_BOOL", default=False) is False


class TestNormalizeBoolFlag:
    """Tests for _normalize_bool_flag helper."""

    def test_normalize_bool_flag_engine_path_smoke(self) -> None:
        """Test _normalize_bool_flag happy path (uses engine implementation)."""
        assert _helpers._normalize_bool_flag(True) is True
        assert _helpers._normalize_bool_flag(False) is False
        assert _helpers._normalize_bool_flag("yes") is True
        assert _helpers._normalize_bool_flag("no") is False

    def test_normalize_bool_flag_empty_set_preserved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty yes_values set() is preserved (not replaced with default)."""
        # Force fallback path to test fallback behavior
        monkeypatch.setattr(_helpers, "_get_engine_normalize_bool_flag", lambda: None)

        # Empty set means no values match (fallback preserves empty set)
        assert _helpers._normalize_bool_flag("yes", yes_values=set()) is False
        assert _helpers._normalize_bool_flag("y", yes_values=set()) is False

    def test_normalize_bool_flag_fallback_accepts_russian_istina(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback accepts Russian 'истина' token (aligned with engine defaults)."""
        # Force fallback without mocking builtins import
        monkeypatch.setattr(_helpers, "_get_engine_normalize_bool_flag", lambda: None)

        assert _helpers._normalize_bool_flag("истина") is True
        assert _helpers._normalize_bool_flag(" ИСТИНА ") is True  # with whitespace
        assert _helpers._normalize_bool_flag("ИСТИНА") is True  # uppercase

    def test_normalize_bool_flag_custom_yes_values(self) -> None:
        """Test that custom yes_values work correctly."""
        # Custom set should work (engine uses yes_values as-is, input is normalized)
        assert _helpers._normalize_bool_flag("yes", yes_values={"yes", "ok"}) is True
        assert _helpers._normalize_bool_flag("ok", yes_values={"yes", "ok"}) is True
        assert _helpers._normalize_bool_flag("no", yes_values={"yes", "ok"}) is False

    def test_normalize_bool_flag_non_str_non_bool(self) -> None:
        """Test _normalize_bool_flag with non-str, non-bool input."""
        from typing import cast

        # Test with int (not bool, not str)
        assert _helpers._normalize_bool_flag(cast("str | bool", 0)) is False
        assert _helpers._normalize_bool_flag(cast("str | bool", 1)) is False
        # Test with None
        assert _helpers._normalize_bool_flag(cast("str | bool", None)) is False
        # Test with empty string
        assert _helpers._normalize_bool_flag("") is False
        # Test with whitespace-only string
        assert _helpers._normalize_bool_flag("   ") is False

    def test_normalize_bool_flag_default_yes_values(self) -> None:
        """Test _normalize_bool_flag with default yes_values."""
        assert _helpers._normalize_bool_flag("yes") is True
        assert _helpers._normalize_bool_flag("y") is True
        assert _helpers._normalize_bool_flag("true") is True
        assert _helpers._normalize_bool_flag("1") is True
        assert _helpers._normalize_bool_flag("да") is True
        assert _helpers._normalize_bool_flag("д") is True
        assert _helpers._normalize_bool_flag("si") is True
        assert _helpers._normalize_bool_flag("sí") is True
        assert _helpers._normalize_bool_flag("no") is False


class TestBuildSoftPaywallHook:
    """Tests for _build_soft_paywall_hook helper."""

    @pytest.mark.parametrize(
        ("default_enabled", "expected"),
        [(True, True), (False, False)],
    )
    def test_soft_paywall_default_enabled(
        self, monkeypatch: pytest.MonkeyPatch, default_enabled: bool, expected: bool
    ) -> None:
        """Test _build_soft_paywall_hook respects default_enabled when env var is not set."""
        monkeypatch.delenv("SOFT_PAYWALL_ENABLED", raising=False)
        hook = _helpers._build_soft_paywall_hook("en", default_enabled=default_enabled)
        assert (hook is not None) is expected

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("1", True),
            ("true", True),
            ("yes", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("off", False),
        ],
    )
    def test_soft_paywall_env_overrides_default(
        self, monkeypatch: pytest.MonkeyPatch, env_value: str, expected: bool
    ) -> None:
        """Test _build_soft_paywall_hook env var overrides default_enabled."""
        monkeypatch.setenv("SOFT_PAYWALL_ENABLED", env_value)
        hook = _helpers._build_soft_paywall_hook("en", default_enabled=False)
        assert (hook is not None) is expected

    def test_soft_paywall_shape_when_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _build_soft_paywall_hook returns correct structure when enabled."""
        monkeypatch.setenv("SOFT_PAYWALL_ENABLED", "1")
        hook = _helpers._build_soft_paywall_hook("en", default_enabled=False)
        assert hook is not None
        assert hook.id == "bmi.pro_interpretation_v1"
        assert hook.target == "pro_paywall"
        assert hook.message.title_key == "soft_paywall.title"
        assert hook.message.body_key == "soft_paywall.body"
        assert hook.message.cta_key == "soft_paywall.cta"
        assert hook.availability.pro_available is True

    def test_soft_paywall_disabled_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _build_soft_paywall_hook returns None when disabled."""
        monkeypatch.setenv("SOFT_PAYWALL_ENABLED", "0")
        hook = _helpers._build_soft_paywall_hook("en", default_enabled=True)
        assert hook is None
