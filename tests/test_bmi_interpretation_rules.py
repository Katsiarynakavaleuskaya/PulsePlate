# -*- coding: utf-8 -*-
"""
Tests for BMI interpretation rules (v1).

RU: Тесты правил интерпретации BMI (v1).
EN: Tests for BMI interpretation rules (v1).

All outputs are i18n keys only.
"""

from __future__ import annotations

import pytest

from core.bmi.interpretation_rules import build_interpretation_v1


@pytest.mark.parametrize(
    ("group", "bmi", "athlete", "expected_none"),
    [
        ("too_young", 16.0, False, True),
        ("pregnant", 22.0, False, False),  # Changed: pregnant now returns interpretation
        ("pregnant", 22.0, True, False),
    ],
)
def test_none_contract(group: str, bmi: float, athlete: bool, expected_none: bool) -> None:
    """Test that certain groups return None interpretation."""
    got = build_interpretation_v1(group=group, bmi=bmi, athlete=athlete)
    assert (got is None) is expected_none


def test_pregnant_without_athlete_returns_interpretation() -> None:
    """Test that pregnant (without athlete) returns interpretation."""
    got = build_interpretation_v1(group="pregnant", bmi=24.0, athlete=False)
    assert got is not None
    assert got.goal_direction == "medical_review"
    assert got.target_range == "prenatal_guidelines"
    assert "bmi.interpretation.disclaimer.pregnancy" in got.disclaimers
    assert "bmi.interpretation.disclaimer.medical_review" in got.disclaimers
    # Should NOT have athlete disclaimer
    assert "bmi.interpretation.disclaimer.athlete_body_composition" not in got.disclaimers


def test_pregnant_athlete_has_combined_disclaimers() -> None:
    """Test pregnant+athlete special case has combined disclaimers."""
    got = build_interpretation_v1(group="pregnant", bmi=24.0, athlete=True)
    assert got is not None
    assert got.goal_direction == "medical_review"
    assert "bmi.interpretation.disclaimer.pregnancy" in got.disclaimers
    assert "bmi.interpretation.disclaimer.athlete_body_composition" in got.disclaimers
    assert "bmi.interpretation.disclaimer.medical_review" in got.disclaimers
    assert got.target_range == "prenatal_guidelines"


@pytest.mark.parametrize(
    ("group", "bmi", "expected_goal", "expected_target"),
    [
        ("teen", 22.0, "maintain", "age_appropriate_growth"),
        ("teen", 17.0, "medical_review", "age_appropriate_growth"),
        ("teen", 30.0, "medical_review", "age_appropriate_growth"),
        ("child", 22.0, "maintain", "age_appropriate_growth"),
        ("child", 18.4, "medical_review", "age_appropriate_growth"),
        ("child", 30.0, "medical_review", "age_appropriate_growth"),
    ],
)
def test_child_teen_qualitative(
    group: str, bmi: float, expected_goal: str, expected_target: str
) -> None:
    """Test child/teen qualitative targets and medical_review for out-of-range."""
    got = build_interpretation_v1(group=group, bmi=bmi, athlete=False)
    assert got is not None
    assert got.goal_direction == expected_goal
    assert got.target_range == expected_target
    assert "bmi.interpretation.disclaimer.pediatric_growth" in got.disclaimers
    assert "bmi.interpretation.priority.growth_monitoring" in got.priority_notes


@pytest.mark.parametrize(
    ("bmi", "expected_goal"),
    [
        (17.9, "increase"),
        (18.5, "maintain"),
        (24.0, "maintain"),
        (27.0, "maintain"),
        (29.9, "maintain"),
        (30.0, "medical_review"),
        (35.0, "medical_review"),
    ],
)
def test_elderly_rules(bmi: float, expected_goal: str) -> None:
    """Test elderly rules: stability-first, allow increase on low BMI."""
    got = build_interpretation_v1(group="elderly", bmi=bmi, athlete=False)
    assert got is not None
    assert got.goal_direction == expected_goal
    assert "bmi.interpretation.priority.stability_first" in got.priority_notes
    if bmi < 18.5:
        assert got.target_range is not None
        assert isinstance(got.target_range, dict)
        assert got.target_range["min"] == 18.5
    elif bmi >= 30.0:
        assert "bmi.interpretation.risk.extreme_value" in got.risk_flags


@pytest.mark.parametrize(
    ("bmi", "expected_goal", "expect_extreme"),
    [
        (18.4, "medical_review", True),
        (18.5, "maintain", False),
        (26.9, "maintain", False),
        (27.0, "maintain", False),
        (27.1, "maintain", False),
        (29.9, "maintain", False),
        (30.0, "medical_review", True),
        (31.0, "medical_review", True),
    ],
)
def test_athlete_rules(bmi: float, expected_goal: str, expect_extreme: bool) -> None:
    """Test athlete rules: maintain in 18.5-30 range, medical_review at extremes."""
    got = build_interpretation_v1(group="athlete", bmi=bmi, athlete=True)
    assert got is not None
    assert got.goal_direction == expected_goal
    has_extreme = "bmi.interpretation.risk.extreme_value" in got.risk_flags
    assert has_extreme is expect_extreme
    assert "bmi.interpretation.disclaimer.athlete_body_composition" in got.disclaimers


@pytest.mark.parametrize(
    ("bmi", "expected_goal"),
    [
        (18.4, "increase"),
        (18.5, "maintain"),
        (24.9, "maintain"),
        (25.0, "reduce"),
        (29.9, "reduce"),
        (30.0, "medical_review"),
        (32.0, "medical_review"),
    ],
)
def test_general_rules(bmi: float, expected_goal: str) -> None:
    """Test general adult rules: increase/maintain/reduce/medical_review per BMI."""
    got = build_interpretation_v1(group="general", bmi=bmi, athlete=False)
    assert got is not None
    assert got.goal_direction == expected_goal
    if bmi >= 30.0:
        assert "bmi.interpretation.risk.extreme_value" in got.risk_flags
        assert "bmi.interpretation.disclaimer.medical_review" in got.disclaimers
        assert got.target_range is None
    else:
        assert "bmi.interpretation.disclaimer.general" in got.disclaimers
        assert got.target_range is not None
        assert isinstance(got.target_range, dict)


def test_all_interpretations_have_i18n_keys_only() -> None:
    """Guard: all text fields must be i18n keys (not translated strings)."""
    test_cases = [
        ("general", 22.0, False),
        ("athlete", 25.0, True),
        ("elderly", 24.0, False),
        ("teen", 20.0, False),
        ("pregnant", 24.0, True),
    ]

    for group, bmi, athlete in test_cases:
        got = build_interpretation_v1(group=group, bmi=bmi, athlete=athlete)
        if got is None:
            continue

        # All fields must be keys (check format: contains dots or known patterns)
        for key in got.risk_flags:
            assert isinstance(key, str)
            assert "." in key or key in {"age_appropriate_growth", "prenatal_guidelines"}

        for key in got.priority_notes:
            assert isinstance(key, str)
            assert "." in key

        for key in got.disclaimers:
            assert isinstance(key, str)
            assert "." in key


def test_interpretation_does_not_mutate_bmi() -> None:
    """Guard: interpretation building does not affect BMI value (immutability check)."""
    bmi_original = 25.5
    got = build_interpretation_v1(group="general", bmi=bmi_original, athlete=False)
    # This is a sanity check - we can't mutate bmi from here, but we verify
    # that the function is pure (no side effects on inputs)
    assert got is not None
    # If we call again with same inputs, should get same result
    got2 = build_interpretation_v1(group="general", bmi=bmi_original, athlete=False)
    assert got2 is not None
    assert got.goal_direction == got2.goal_direction
    assert got.target_range == got2.target_range
