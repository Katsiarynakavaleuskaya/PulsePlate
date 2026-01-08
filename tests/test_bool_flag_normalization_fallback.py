# -*- coding: utf-8 -*-
"""
Tests for bool flag normalization fallback in router.

RU: Тесты для fallback нормализации булевых флагов в роутере.
EN: Tests for bool flag normalization fallback in router.

Guard tests to ensure router fallback normalization matches schema normalization.
"""

from __future__ import annotations

import pytest
from app.routers import bmi as bmi_router


class TestFallbackBoolFlagNormalization:
    """Tests for _fallback_normalize_bool_flag function."""

    def test_fallback_normalize_bool_flag_accepts_istina(self) -> None:
        """
        Guard: fallback normalization must recognize 'истина' (RU truthy token).

        RU: Проверка, что fallback нормализация распознаёт токен 'истина'.
        EN: Verify that fallback normalization recognizes 'истина' token.
        """
        assert bmi_router._fallback_normalize_bool_flag("истина") is True
        assert bmi_router._fallback_normalize_bool_flag("ИСТИНА") is True
        assert bmi_router._fallback_normalize_bool_flag("  истина  ") is True

    def test_fallback_normalize_bool_flag_matches_schema_truthy_tokens(self) -> None:
        """
        Guard: fallback normalization must match schema _TRUE_STRINGS.

        RU: Проверка, что fallback использует те же truthy токены, что и schema.
        EN: Verify that fallback uses same truthy tokens as schema.
        """
        from app.schemas.bmi import _TRUE_STRINGS

        # All schema truthy tokens must be recognized by fallback
        for token in _TRUE_STRINGS:
            assert (
                bmi_router._fallback_normalize_bool_flag(token) is True
            ), f"Fallback must recognize schema truthy token: {token!r}"

    def test_fallback_normalize_bool_flag_matches_schema_falsy_tokens(self) -> None:
        """
        Guard: fallback normalization must match schema _FALSE_STRINGS.

        RU: Проверка, что fallback использует те же falsy токены, что и schema.
        EN: Verify that fallback uses same falsy tokens as schema.
        """
        from app.schemas.bmi import _FALSE_STRINGS

        # All schema falsy tokens must be recognized by fallback
        for token in _FALSE_STRINGS:
            assert (
                bmi_router._fallback_normalize_bool_flag(token) is False
            ), f"Fallback must recognize schema falsy token: {token!r}"

    def test_fallback_normalize_bool_flag_unknown_token_defaults_to_false(self) -> None:
        """
        Guard: unknown tokens must default to False (safe default).

        RU: Проверка, что неизвестные токены по умолчанию трактуются как False.
        EN: Verify that unknown tokens default to False.
        """
        assert bmi_router._fallback_normalize_bool_flag("unknown_token") is False
        assert bmi_router._fallback_normalize_bool_flag("xyz") is False
        assert bmi_router._fallback_normalize_bool_flag("") is False

    def test_fallback_normalize_bool_flag_handles_bool_input(self) -> None:
        """Guard: bool input must be returned as-is."""
        assert bmi_router._fallback_normalize_bool_flag(True) is True
        assert bmi_router._fallback_normalize_bool_flag(False) is False

    def test_fallback_normalize_bool_flag_handles_non_string_non_bool(self) -> None:
        """Guard: non-string, non-bool input must default to False."""
        assert bmi_router._fallback_normalize_bool_flag(None) is False
        assert bmi_router._fallback_normalize_bool_flag(123) is False
        assert bmi_router._fallback_normalize_bool_flag([]) is False
