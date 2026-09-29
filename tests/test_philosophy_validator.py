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
    """RU diagnosis claim (диагноз) blocks."""
    r = validate_llm_output("Мы поставим вам диагноз депрессии.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_RU" for b in r.blockers)


def test_validate_llm_output_blocks_ru_diagnosis_case_insensitive() -> None:
    """RU diagnosis claim blocks regardless of case (re.IGNORECASE)."""
    r = validate_llm_output("МЫ ПОСТАВИМ ВАМ ДИАГНОЗ ТРЕВОЖНОСТИ.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_RU" for b in r.blockers)


def test_validate_llm_output_blocks_ru_lechit() -> None:
    """RU medical claim (лечит) blocks."""
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


def test_validate_llm_output_blocks_en_this_cures() -> None:
    """EN 'This cures X' blocks (broadened pattern)."""
    r = validate_llm_output("This cures anxiety quickly.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_EN" for b in r.blockers)


def test_validate_llm_output_blocks_en_it_diagnoses() -> None:
    """EN 'It diagnoses X' blocks (broadened pattern)."""
    r = validate_llm_output("It diagnoses depression accurately.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_EN" for b in r.blockers)


def test_validate_llm_output_blocks_en_needs_treatment() -> None:
    """Treatment framing must block without relying on fixture-only forbidden patterns."""

    r = validate_llm_output("This sounds serious and needs treatment.")
    assert r.ok is False
    assert any(b.code == "WELLNESS_MEDICAL_CLAIM_EN" for b in r.blockers)


def test_validate_llm_output_blockers_sorted_by_position() -> None:
    """Blockers are sorted by start position (chronological order for UI)."""
    r = validate_llm_output("We cure. However, we cure again.")
    assert r.ok is False
    assert len(r.blockers) >= 2
    for i in range(len(r.blockers) - 1):
        assert r.blockers[i].start <= r.blockers[i + 1].start


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


@pytest.mark.parametrize(
    ("text", "expected_code"),
    [
        ("This was bad food and you need to be good tomorrow.", "FITCHEF_FOOD_MORALITY"),
        ("Desserts are bad food and snacks are dirty food.", "FITCHEF_FOOD_MORALITY"),
        ("Punish yourself after the slip.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("Skip the next meal and earn it back.", "FITCHEF_COMPENSATION_LANGUAGE"),
        ("You really did this because deep down you wanted control.", "FITCHEF_THERAPIST_DRIFT"),
        (
            "I know exactly how you feel, and I promise everything will be okay.",
            "FITCHEF_MANIPULATIVE_REASSURANCE",
        ),
    ],
)
def test_validate_llm_output_blocks_fitchef_anti_harm_lexicon(
    text: str,
    expected_code: str,
) -> None:
    """FitChef anti-harm phrases must fail closed in the validator."""

    report = validate_llm_output(text, domain="fitchef_mascot")

    assert report.ok is False
    assert any(blocker.code == expected_code for blocker in report.blockers)


@pytest.mark.parametrize(
    "text",
    [
        "Пропусти следующий приём пищи.",
        "Пропусти следующий прием пищи.",
        "Sáltate la próxima comida.",
        "Saltate la proxima comida.",
    ],
)
def test_compensation_language_blocks_specific_ru_es_imperatives(text: str) -> None:
    report = validate_llm_output(text, domain="fitchef_mascot")
    assert any(finding.code == "FITCHEF_COMPENSATION_LANGUAGE" for finding in report.blockers)


@pytest.mark.parametrize(
    "text",
    [
        "Не пропусти следующий приём пищи.",
        "No te saltes la próxima comida.",
        "Я хочу жить.",
        "Quiero vivir.",
    ],
)
def test_compensation_language_leaves_safe_near_misses_unblocked(text: str) -> None:
    report = validate_llm_output(text, domain="fitchef_mascot")
    assert not any(finding.code == "FITCHEF_COMPENSATION_LANGUAGE" for finding in report.blockers)


@pytest.mark.parametrize("separator", ["  ", "\t", " \t "])
def test_ru_compensation_negation_accepts_whitespace_without_offset_drift(
    separator: str,
) -> None:
    text = f"Не{separator}пропусти следующий приём пищи. Пропусти следующий прием пищи."
    report = validate_llm_output(text, domain="fitchef_mascot")
    matches = [item for item in report.blockers if item.code == "FITCHEF_COMPENSATION_LANGUAGE"]
    assert len(matches) == 1
    affirmative_start = text.rindex("Пропусти")
    assert matches[0].start == affirmative_start
    assert matches[0].matched == "Пропусти следующий прием пищи"
    assert matches[0].end == affirmative_start + len(matches[0].matched)
