# -*- coding: utf-8 -*-
"""
Tests for defensive fallback branches in _get_bmi_breakpoints() and _upper_for().

RU: Тесты для защитных fallback веток в _get_bmi_breakpoints() и _upper_for().
EN: Tests for defensive fallback branches in _get_bmi_breakpoints() and _upper_for().

Covers coverage tail from PR-490B:
- core/bmi/engine.py:257-258 (fallback to age_band-specific general)
- core/bmi/engine.py:261 (final fallback to adult general)
- core/bmi/engine.py:361 (ValueError in _upper_for when category missing)
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

    # Copy current registry and inject a synthetic age_band
    patched: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined, unused-ignore]

    # Provide only (adult2, general), but request (adult2, athlete)
    patched[("adult2", "general")] = patched[("adult", "general")]
    monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", patched)

    bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]  # Synthetic age_band for test
    assert bp == patched[("adult", "general")]
    assert len(bp) == 6


def test_get_bmi_breakpoints_final_fallback_to_adult_general(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    # Copy registry, but DO NOT define (adult2, general)
    patched: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined, unused-ignore]
    monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", patched)

    bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]  # Synthetic age_band for test
    assert bp == patched[("adult", "general")]
    assert len(bp) == 6
    # Verify it's actually adult/general thresholds (25.0 normal_max)
    assert bp[1][0] == 25.0  # adult normal_max


def test_upper_for_raises_when_missing_category() -> None:
    """
    RU: Покрывает raise ValueError в _upper_for() когда категория отсутствует.
    EN: Covers raise ValueError in _upper_for() when category is missing.

    Test strategy:
    - Provide breakpoints without "normal" category
    - Request "normal" → should raise ValueError → covers line 361
    """
    from core.bmi.engine import _upper_for

    breakpoints = [
        (18.5, "underweight"),
        (25.0, "overweight"),  # intentionally missing "normal"
        (float("inf"), "obesity_3"),
    ]
    with pytest.raises(ValueError, match="Missing breakpoint"):
        _upper_for(breakpoints, "normal")  # type: ignore[arg-type]  # Intentionally missing category for test
