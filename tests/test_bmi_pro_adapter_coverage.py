"""
Tests for BMI Pro adapter edge cases to improve coverage.

Covers:
- Empty recommendation handling
- risk_factors='0' handling
- whr_risk='unknown' vs normal cases
"""

import pytest
from app.routers.bmi_pro import _adapt_pro_stage_to_response


def test_adapt_pro_stage_to_response_empty_recommendation():
    """Test adapter handles empty recommendation correctly."""
    # Stage dict with empty recommendation
    stage_dict = {
        "stage": "low_risk",
        "recommendation": "",  # Empty - should not be added to notes
        "risk_factors": "0",
        "wht_risk": "low",
        "whr_risk": "low",
    }

    risk_level, notes = _adapt_pro_stage_to_response(stage_dict, "en")

    # Empty recommendation should not be added to notes
    assert risk_level == "low"
    # Notes should be empty or not contain empty strings
    assert "" not in notes
    assert all(n.strip() for n in notes if n)


def test_adapt_pro_stage_to_response_risk_factors_zero():
    """Test adapter doesn't add 'Risk factors: 0' to notes."""
    # Stage dict with risk_factors="0"
    stage_dict = {
        "stage": "low_risk",
        "recommendation": "Maintain healthy habits",
        "risk_factors": "0",  # Should not add to notes
        "wht_risk": "low",
        "whr_risk": "low",
    }

    risk_level, notes = _adapt_pro_stage_to_response(stage_dict, "en")

    # risk_factors="0" should not appear in notes
    assert risk_level == "low"
    notes_text = " ".join(notes)
    assert "Risk factors: 0" not in notes_text
    # Should contain recommendation
    assert "Maintain healthy habits" in notes_text


def test_adapt_pro_stage_to_response_risk_factors_non_zero():
    """Test adapter adds 'Risk factors: N' when risk_factors > 0."""
    # Stage dict with risk_factors="2"
    stage_dict = {
        "stage": "high_risk",
        "recommendation": "Consider consulting",
        "risk_factors": "2",  # Should add to notes
        "wht_risk": "moderate",
        "whr_risk": "high",
    }

    risk_level, notes = _adapt_pro_stage_to_response(stage_dict, "en")

    # risk_factors="2" should appear in notes
    assert risk_level == "high"
    notes_text = " ".join(notes)
    assert "Risk factors: 2" in notes_text


def test_adapt_pro_stage_to_response_whr_risk_unknown():
    """Test adapter adds missing hip note when whr_risk='unknown'."""
    # Stage dict with whr_risk="unknown"
    stage_dict = {
        "stage": "moderate_risk",
        "recommendation": "Monitor health",
        "risk_factors": "1",
        "wht_risk": "moderate",
        "whr_risk": "unknown",  # Should trigger missing hip note
    }

    risk_level, notes = _adapt_pro_stage_to_response(stage_dict, "en")

    # Should contain missing hip explanation
    assert risk_level == "moderate"
    notes_text = " ".join(notes).lower()
    assert "whr not computed" in notes_text or "missing hip_cm" in notes_text


def test_adapt_pro_stage_to_response_whr_risk_low():
    """Test adapter doesn't add missing hip note when whr_risk is not 'unknown'."""
    # Stage dict with whr_risk="low"
    stage_dict = {
        "stage": "low_risk",
        "recommendation": "Maintain habits",
        "risk_factors": "0",
        "wht_risk": "low",
        "whr_risk": "low",  # Not "unknown" - should not add missing hip note
    }

    risk_level, notes = _adapt_pro_stage_to_response(stage_dict, "en")

    # Should NOT contain missing hip explanation
    assert risk_level == "low"
    notes_text = " ".join(notes)
    assert "WHR not computed" not in notes_text
    assert "missing hip_cm" not in notes_text.lower()


def test_adapt_pro_stage_to_response_wht_risk_moderate():
    """Test adapter adds WHtR risk when wht_risk != 'low'."""
    # Stage dict with wht_risk="moderate"
    stage_dict = {
        "stage": "moderate_risk",
        "recommendation": "Monitor health",
        "risk_factors": "1",
        "wht_risk": "moderate",  # Should add to notes
        "whr_risk": "low",
    }

    risk_level, notes = _adapt_pro_stage_to_response(stage_dict, "en")

    # Should contain WHtR risk
    assert risk_level == "moderate"
    notes_text = " ".join(notes)
    assert "WHtR risk: moderate" in notes_text


def test_adapt_pro_stage_to_response_stage_mapping():
    """Test adapter correctly maps stage to risk_level."""
    test_cases = [
        ("high_risk", "high"),
        ("moderate_risk", "moderate"),
        ("low_risk", "low"),
        ("unknown_stage", "low"),  # Default fallback
    ]

    for stage, expected_risk in test_cases:
        stage_dict = {
            "stage": stage,
            "recommendation": "Test",
            "risk_factors": "0",
            "wht_risk": "low",
            "whr_risk": "low",
        }

        risk_level, _ = _adapt_pro_stage_to_response(stage_dict, "en")
        assert risk_level == expected_risk, f"Stage {stage} should map to {expected_risk}"
