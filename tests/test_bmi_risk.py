# -*- coding: utf-8 -*-
"""
RU: Golden tests для core/bmi/risk.py (фиксируют поведение legacy).
EN: Golden tests for core/bmi/risk.py (preserve legacy behavior).
"""

from __future__ import annotations

import pytest

from core.bmi.engine import _compute_wht_ratio
from core.bmi.risk import WaistRiskResult, calculate_waist_risk


@pytest.mark.parametrize(
    ("gender", "waist_cm", "expected_level"),
    [
        # Male thresholds
        ("male", 70.0, "low"),
        ("male", 93.9, "low"),
        ("male", 94.0, "moderate"),  # Exactly on threshold
        ("male", 95.0, "moderate"),
        ("male", 101.9, "moderate"),
        ("male", 102.0, "high"),  # Exactly on threshold
        ("male", 110.0, "high"),
        # Female thresholds
        ("female", 70.0, "low"),
        ("female", 79.9, "low"),
        ("female", 80.0, "moderate"),  # Exactly on threshold
        ("female", 85.0, "moderate"),
        ("female", 87.9, "moderate"),
        ("female", 88.0, "high"),  # Exactly on threshold
        ("female", 95.0, "high"),
    ],
)
@pytest.mark.parametrize("lang", ["ru", "en", "es"])
def test_waist_risk_thresholds_and_localization(
    gender: str, waist_cm: float, expected_level: str, lang: str
) -> None:
    """Test waist risk thresholds and localization for all languages."""
    height_m = 1.70
    res = calculate_waist_risk(waist_cm=waist_cm, height_m=height_m, gender=gender, lang=lang)
    assert res is not None
    assert res.risk_level == expected_level
    assert res.wht_ratio == _compute_wht_ratio(waist_cm, height_m)

    # notes: empty tuple for low, non-empty tuple for moderate/high
    if expected_level == "low":
        assert res.notes == ()
    else:
        assert isinstance(res.notes, tuple)
        assert len(res.notes) == 1
        assert isinstance(res.notes[0], str)
        assert res.notes[0] != ""

    # Verify localization
    if lang == "ru":
        if expected_level == "high":
            assert "Высокий" in res.notes[0]
        elif expected_level == "moderate":
            assert "Повышенный" in res.notes[0]
    elif lang == "en":
        if expected_level == "high":
            assert "High" in res.notes[0]
        elif expected_level == "moderate":
            assert "Increased" in res.notes[0]
    elif lang == "es":
        if expected_level == "high":
            assert "Alto" in res.notes[0]
        elif expected_level == "moderate":
            assert "aumentado" in res.notes[0]


def test_waist_risk_none_returns_none() -> None:
    """Test that None waist_cm returns None."""
    res = calculate_waist_risk(waist_cm=None, height_m=1.70, gender="male", lang="en")
    assert res is None


@pytest.mark.parametrize(
    ("waist_cm", "height_m"),
    [
        (0, 1.70),
        (-10, 1.70),
        (90, 0),
        (90, -1.0),
    ],
)
def test_wht_ratio_fail_soft_matches_core(waist_cm: float, height_m: float) -> None:
    """Test that wht_ratio matches compute_wht_ratio() behavior (fail-soft)."""
    res = calculate_waist_risk(waist_cm=waist_cm, height_m=height_m, gender="male", lang="en")
    assert res is not None
    assert res.wht_ratio == _compute_wht_ratio(waist_cm, height_m)


@pytest.mark.parametrize("gender", ["Female", "жен", "UNKNOWN", "f", "F"])
@pytest.mark.parametrize("lang", ["EN", "Ru", "xx", "ES"])
def test_normalization_fail_soft(gender: str, lang: str) -> None:
    """Test that gender/lang normalization works (fail-soft)."""
    res = calculate_waist_risk(waist_cm=90.0, height_m=1.70, gender=gender, lang=lang)
    assert res is not None
    assert res.risk_level in {"low", "moderate", "high"}
    assert isinstance(res.notes, tuple)


def test_waist_risk_result_structure() -> None:
    """Test WaistRiskResult dataclass structure."""
    waist_cm = 100.0
    height_m = 1.70
    res = calculate_waist_risk(waist_cm=waist_cm, height_m=height_m, gender="male", lang="en")
    assert res is not None
    assert isinstance(res, WaistRiskResult)
    # Verify wht_ratio matches compute_wht_ratio contract
    assert res.wht_ratio == _compute_wht_ratio(waist_cm, height_m)
    assert res.risk_level in {"low", "moderate", "high"}
    assert isinstance(res.notes, tuple)
    assert all(isinstance(note, str) for note in res.notes)
