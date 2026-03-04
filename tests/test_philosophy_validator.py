"""Unit tests for core.insight.philosophy_validator (deterministic LLM output validation)."""

from __future__ import annotations

import pytest

from core.insight.philosophy_validator import Report, validate_llm_output


def test_validate_llm_output_ok_empty() -> None:
    """Empty text passes."""
    r = validate_llm_output("")
    assert r.ok is True
    assert r.blockers == []


def test_validate_llm_output_ok_safe_text() -> None:
    """Safe wellness text passes."""
    r = validate_llm_output("Eat more vegetables. Consider fiber intake.")
    assert r.ok is True
    assert r.blockers == []


def test_validate_llm_output_blocks_ru_medical_claim() -> None:
    """RU medical claim (лечит/диагноз) blocks."""
    r = validate_llm_output("Мы вылечим тревожность за 2 недели.")
    assert r.ok is False
    assert len(r.blockers) >= 1
    codes = [b.code for b in r.blockers]
    assert "WELLNESS_MEDICAL_CLAIM_RU" in codes


def test_validate_llm_output_blocks_ru_diagnosis() -> None:
    """RU diagnosis claim blocks."""
    r = validate_llm_output("FFMI лечит недостаток мышц.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_RU" for b in r.blockers)


def test_validate_llm_output_blocks_en_medical_claim() -> None:
    """EN medical claim (we cure / will diagnose) blocks."""
    r = validate_llm_output("We cure anxiety quickly.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_EN" for b in r.blockers)


def test_validate_llm_output_blocks_en_will_diagnose() -> None:
    """EN will diagnose blocks."""
    r = validate_llm_output("This will diagnose your condition.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_EN" for b in r.blockers)


def test_validate_llm_output_blocks_guarantee() -> None:
    """WELLNESS_GUARANTEE blocks."""
    r = validate_llm_output("Guaranteed to cure in 30 days.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_GUARANTEE" for b in r.blockers)


def test_validate_llm_output_blocks_contradiction_marker() -> None:
    """POTENTIAL_CONTRADICTION blocks."""
    r = validate_llm_output("However, we cure everyone.")
    assert r.ok is False
    assert any(b.code == "POTENTIAL_CONTRADICTION" for b in r.blockers)


def test_validate_llm_output_deterministic_split() -> None:
    """Same input yields same output (determinism)."""
    text = "We cure anxiety. Consider fiber."
    r1 = validate_llm_output(text)
    r2 = validate_llm_output(text)
    assert r1.ok == r2.ok
    assert len(r1.blockers) == len(r2.blockers)
    for b1, b2 in zip(r1.blockers, r2.blockers):
        assert b1.code == b2.code
        assert b1.matched == b2.matched


def test_validate_llm_output_domain_passthrough() -> None:
    """domain parameter is stored in report."""
    r = validate_llm_output("Safe text.", domain="nutrition")
    assert r.domain == "nutrition"


def test_validate_llm_output_treat_as_not_blocked() -> None:
    """'treat as' / 'treatment' (excluded per precision>recall) does not block."""
    r = validate_llm_output("Treat this as a suggestion, not medical advice.")
    assert r.ok is True
