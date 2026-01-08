# -*- coding: utf-8 -*-
"""
Ready-to-use test for PR-490C: Cover fallback branches in _get_bmi_breakpoints().

RU: Готовый тест для PR-490C: покрытие fallback веток в _get_bmi_breakpoints().
EN: Ready-to-use test for PR-490C: cover fallback branches in _get_bmi_breakpoints().

Copy this to: tests/test_bmi_engine_breakpoints_fallbacks.py
"""

from __future__ import annotations

from typing import Any

import pytest


def test_get_bmi_breakpoints_fallback_to_age_band_general(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    RU: Покрывает ветку fallback (age_band, "general") в _get_bmi_breakpoints().
    EN: Covers (age_band, "general") fallback branch in _get_bmi_breakpoints().

    Test strategy:
    - Inject synthetic age_band "adult2" with only ("adult2", "general") in registry
    - Request ("adult2", "athlete") which doesn't exist
    - Should fallback to ("adult2", "general") → covers lines 257-258
    """
    import core.bmi.engine as eng

    # Make a copy and inject a synthetic age_band key
    original: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined]
    try:
        # Add ("adult2", "general") but NOT ("adult2", "athlete")
        original[("adult2", "general")] = original[("adult", "general")]  # type: ignore[assignment]
        monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", original)

        # Request ("adult2", "athlete") - doesn't exist, should fallback to ("adult2", "general")
        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]
        assert bp == original[("adult", "general")]
        assert len(bp) == 6
    finally:
        # monkeypatch will restore automatically
        pass


def test_get_bmi_breakpoints_final_fallback_to_adult_general(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    RU: Покрывает финальный fallback ("adult","general") в _get_bmi_breakpoints().
    EN: Covers final ("adult","general") fallback branch in _get_bmi_breakpoints().

    Test strategy:
    - Use synthetic age_band "adult2" with NO entries in registry
    - Request ("adult2", "athlete") which doesn't exist
    - Should fallback to ("adult2", "general") which also doesn't exist
    - Should use final fallback ("adult", "general") → covers line 261
    """
    import core.bmi.engine as eng

    # Use original registry (no "adult2" entries)
    original: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined]
    monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", original)

    # Request ("adult2", "athlete") - doesn't exist
    # Fallback to ("adult2", "general") - also doesn't exist
    # Final fallback to ("adult", "general") → covers line 261
    bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]
    assert bp == original[("adult", "general")]
    assert len(bp) == 6
    # Verify it's actually adult/general thresholds (25.0 normal_max)
    assert bp[1][0] == 25.0  # adult normal_max

