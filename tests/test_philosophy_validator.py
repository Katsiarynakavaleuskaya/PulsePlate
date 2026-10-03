"""Unit tests for core.insight.philosophy_validator (deterministic LLM output validation)."""

from __future__ import annotations

import json

import pytest

from core.i18n import Language
from core.insight.fitchef_companion import prepare_distortion_simulator_draft
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
    """Block the reviewed Russian and Spanish compensatory imperatives."""

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
    """Keep the reviewed safe compensation near misses unblocked."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    assert not any(finding.code == "FITCHEF_COMPENSATION_LANGUAGE" for finding in report.blockers)


@pytest.mark.parametrize("separator", ["  ", "\t", " \t "])
def test_ru_compensation_negation_accepts_whitespace_without_offset_drift(
    separator: str,
) -> None:
    """Preserve immediate Russian negation and original text offsets across whitespace."""

    text = f"Не{separator}пропусти следующий приём пищи. Пропусти следующий прием пищи."
    report = validate_llm_output(text, domain="fitchef_mascot")
    matches = [item for item in report.blockers if item.code == "FITCHEF_COMPENSATION_LANGUAGE"]
    assert len(matches) == 1
    affirmative_start = text.rindex("Пропусти")
    assert matches[0].start == affirmative_start
    assert matches[0].matched == "Пропусти следующий прием пищи"
    assert matches[0].end == affirmative_start + len(matches[0].matched)


@pytest.mark.parametrize(
    ("text", "expected_code", "expected_match"),
    [
        ("Накажи себя за срыв.", "FITCHEF_PUNITIVE_RECOVERY", "Накажи себя"),
        ("Castígate por el desliz.", "FITCHEF_PUNITIVE_RECOVERY", "Castígate"),
        ("Esto cura tu ansiedad.", "WELLNESS_MEDICAL_CLAIM_ES", "Esto cura"),
        (
            "Te diagnostico con ansiedad.",
            "WELLNESS_MEDICAL_CLAIM_ES",
            "Te diagnostico con",
        ),
        ("This cures your anxiety.", "WELLNESS_MEDICAL_CLAIM_EN", "This cures"),
    ],
)
def test_locale_safety_reviewer_witnesses_block_with_original_span(
    text: str, expected_code: str, expected_match: str
) -> None:
    """Bind each reviewed locale blocker to its original matched span."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    matches = [finding for finding in report.blockers if finding.code == expected_code]
    assert report.ok is False
    assert len(matches) == 1
    assert matches[0].matched == expected_match
    assert matches[0].start == text.index(expected_match)
    assert matches[0].end == matches[0].start + len(expected_match)
    assert report.domain == "fitchef_mascot"


_LOCALE_FITCHEF_CASES = [
    (
        "ru",
        "FITCHEF_FOOD_MORALITY",
        "Это плохая еда.",
        "плохая еда",
        "Еда не делает вас плохим.",
    ),
    (
        "es",
        "FITCHEF_FOOD_MORALITY",
        "Es comida mala.",
        "comida mala",
        "La comida no te hace malo.",
    ),
    (
        "ru",
        "FITCHEF_PUNITIVE_RECOVERY",
        "Накажи себя за срыв.",
        "Накажи себя",
        "Не наказывай себя за срыв.",
    ),
    (
        "es",
        "FITCHEF_PUNITIVE_RECOVERY",
        "Castígate por el desliz.",
        "Castígate",
        "No te castigues por el desliz.",
    ),
    (
        "ru",
        "FITCHEF_COMPENSATION_LANGUAGE",
        "Пропусти следующий приём пищи.",
        "Пропусти следующий приём пищи",
        "Не пропусти следующий приём пищи.",
    ),
    (
        "es",
        "FITCHEF_COMPENSATION_LANGUAGE",
        "Sáltate la próxima comida.",
        "Sáltate la próxima comida",
        "No te saltes la próxima comida.",
    ),
    (
        "ru",
        "FITCHEF_THERAPIST_DRIFT",
        "Ты на самом деле сделал это потому, что хотел контроля.",
        "Ты на самом деле сделал это потому, что",
        "Я не знаю, почему это произошло.",
    ),
    (
        "es",
        "FITCHEF_THERAPIST_DRIFT",
        "En el fondo hiciste esto porque querías controlarlo todo.",
        "En el fondo hiciste esto porque",
        "No sabemos por qué ocurrió.",
    ),
    (
        "ru",
        "FITCHEF_MANIPULATIVE_REASSURANCE",
        "Я точно знаю, что ты чувствуешь.",
        "Я точно знаю, что ты чувствуешь",
        "Я не могу знать, что ты чувствуешь.",
    ),
    (
        "es",
        "FITCHEF_MANIPULATIVE_REASSURANCE",
        "Sé exactamente cómo te sientes.",
        "Sé exactamente cómo te sientes",
        "No puedo saber cómo te sientes.",
    ),
]


@pytest.mark.parametrize(
    ("code", "positive", "matched", "safe"),
    [(code, positive, matched, safe) for _, code, positive, matched, safe in _LOCALE_FITCHEF_CASES],
)
def test_reviewed_fitchef_locale_phrases_and_safe_controls(
    code: str, positive: str, matched: str, safe: str
) -> None:
    """Distinguish the reviewed unsafe locale phrases from their safe controls."""

    report = validate_llm_output(positive, domain="fitchef_mascot")
    findings = [finding for finding in report.blockers if finding.code == code]
    assert len(findings) == 1
    assert findings[0].matched == matched
    assert (findings[0].start, findings[0].end) == (
        positive.index(matched),
        positive.index(matched) + len(matched),
    )
    assert report.ok is False

    safe_report = validate_llm_output(safe, domain="fitchef_mascot")
    assert not any(finding.code == code for finding in safe_report.blockers)


@pytest.mark.parametrize(
    "text",
    [
        "Esto no cura la ansiedad; puede apoyar la planificación.",
        "No puedo darte un diagnóstico; podemos hablar de hábitos.",
        "La palabra cura aparece en el texto.",
        "La palabra diagnóstico aparece en el texto.",
    ],
)
def test_es_medical_safe_controls_do_not_claim_cure_or_diagnosis(text: str) -> None:
    """Keep the reviewed Spanish informational controls outside the prohibited claims."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    assert not any(finding.code == "WELLNESS_MEDICAL_CLAIM_ES" for finding in report.blockers)


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("We diagnose anxiety.", "WELLNESS_MEDICAL_CLAIM_EN"),
        ("Это лечит тревожность.", "WELLNESS_MEDICAL_CLAIM_RU"),
        ("Мы поставим вам диагноз тревожности.", "WELLNESS_MEDICAL_CLAIM_RU"),
    ],
)
def test_medical_locale_controls_keep_existing_codes(text: str, code: str) -> None:
    """Preserve canonical warning codes for the reviewed locale controls."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    assert report.ok is False
    assert any(finding.code == code for finding in report.blockers)


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("НАкажи   себя за срыв.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("CASTIGATE por el desliz.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("Esto CURA  tu ansiedad.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("TE DIAGNOSTICO con ansiedad.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("En el fondo hiciste esto porque querias controlarlo todo.", "FITCHEF_THERAPIST_DRIFT"),
        ("Se exactamente como te sientes.", "FITCHEF_MANIPULATIVE_REASSURANCE"),
    ],
)
def test_reviewed_locale_case_spacing_and_accent_variants(text: str, code: str) -> None:
    """Recognize the reviewed variants without changing the canonical warning code."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    assert any(finding.code == code for finding in report.blockers)


@pytest.mark.parametrize(
    "text",
    [
        "preCastígate por el desliz.",
        "Esto curamente tu ansiedad.",
        "Te diagnosticoterapia con ansiedad.",
    ],
)
def test_reviewed_locale_patterns_observe_word_boundaries(text: str) -> None:
    """Avoid matches embedded inside unrelated words."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    assert report.ok is True


@pytest.mark.parametrize(
    ("lang", "phrase"),
    [(lang, positive) for lang, _, positive, _, _ in _LOCALE_FITCHEF_CASES]
    + [
        ("es", "Esto cura tu ansiedad."),
        ("es", "Te diagnostico con ansiedad."),
        ("ru", "Накажи себя за еду."),
        ("es", "Castígate por comer."),
        ("es", "Esto cura tu depresión."),
        ("es", "Te diagnostico con depresión."),
        ("ru", "Ты на самом деле сделал это потому, что хотел успокоиться."),
        ("es", "En el fondo hiciste esto porque buscabas calma."),
    ],
)
@pytest.mark.parametrize(
    "field_name",
    ["why_it_matches", "evidence_for", "evidence_against", "balanced_reframe", "next_small_action"],
)
def test_reviewed_unsafe_provider_field_uses_localized_deterministic_fallback(
    lang: Language, phrase: str, field_name: str
) -> None:
    """Rewrite each reviewed unsafe provider field through the localized fallback."""

    payload: dict[str, str | list[str]] = {
        "distortion_labels": ["catastrophizing"],
        "why_it_matches": "A small setback can feel larger than it is.",
        "evidence_for": ["One plan did not work."],
        "evidence_against": ["One plan can be revised."],
        "balanced_reframe": "One setback does not settle the whole plan.",
        "next_small_action": "Choose one small planning step today.",
    }
    payload[field_name] = [phrase] if field_name.startswith("evidence_") else phrase
    draft = prepare_distortion_simulator_draft(
        json.dumps(payload),
        situation="A meal plan changed.",
        automatic_thought="One setback means the whole plan is lost.",
        emotion="frustrated",
        goal="plan the next meal",
        lang=lang,
    )
    fallback = prepare_distortion_simulator_draft(
        "not-json",
        situation="A meal plan changed.",
        automatic_thought="One setback means the whole plan is lost.",
        emotion="frustrated",
        goal="plan the next meal",
        lang=lang,
    )
    assert draft.warnings == ["wellness_language_rewritten"]
    assert draft.distortion_labels == fallback.distortion_labels
    localized_actions: dict[Language, str] = {
        "ru": "Запишите одну более добрую мысль и выберите один небольшой шаг для следующего приёма пищи или привычки.",
        "es": "Escribe un pensamiento alternativo más amable y elige un paso concreto para la próxima comida o hábito.",
        "en": "Write one kinder replacement thought and pair it with one concrete next meal or habit step.",
    }
    assert draft.next_small_action == localized_actions[lang]
    for field in (
        "why_it_matches",
        "evidence_for",
        "evidence_against",
        "balanced_reframe",
        "next_small_action",
    ):
        assert getattr(draft, field) == getattr(fallback, field)
    assert phrase not in str(draft)


@pytest.mark.parametrize(
    ("lang", "phrase"),
    [
        ("ru", "Накажи себя за срыв"),
        ("es", "Castígate por el desliz"),
        ("es", "Esto cura tu ansiedad"),
    ],
)
@pytest.mark.parametrize("field_name", ["next_small_action", "balanced_reframe"])
def test_quoted_unsafe_provider_phrase_still_uses_existing_fallback(
    lang: Language, phrase: str, field_name: str
) -> None:
    """Keep a quoted unsafe provider phrase subject to the existing fallback."""

    payload = {
        "distortion_labels": ["catastrophizing"],
        "why_it_matches": "One change can feel large.",
        "evidence_for": ["A plan changed."],
        "evidence_against": ["A next step remains."],
        "balanced_reframe": "A change need not settle the whole plan.",
        "next_small_action": "Choose a small step.",
    }
    payload[field_name] = f'Provider says "{phrase}".'
    draft = prepare_distortion_simulator_draft(
        json.dumps(payload),
        situation="A plan changed.",
        automatic_thought="Every plan will fail.",
        emotion="frustrated",
        goal=None,
        lang=lang,
    )
    assert draft.warnings == ["wellness_language_rewritten"]
    assert phrase not in str(draft)


@pytest.mark.parametrize(
    ("text", "code", "construction"),
    [
        ("Накажи себя за еду.", "FITCHEF_PUNITIVE_RECOVERY", "Накажи себя"),
        ("Castígate por comer.", "FITCHEF_PUNITIVE_RECOVERY", "Castígate"),
        ("Esto cura tu depresión.", "WELLNESS_MEDICAL_CLAIM_ES", "Esto cura"),
        ("Te diagnostico con depresión.", "WELLNESS_MEDICAL_CLAIM_ES", "Te diagnostico con"),
        (
            "Ты на самом деле сделал это потому, что хотел успокоиться.",
            "FITCHEF_THERAPIST_DRIFT",
            "Ты на самом деле сделал это потому, что",
        ),
        (
            "En el fondo hiciste esto porque buscabas calma.",
            "FITCHEF_THERAPIST_DRIFT",
            "En el fondo hiciste esto porque",
        ),
    ],
)
@pytest.mark.parametrize("prefix", ["", "Context: "])
def test_locale_safety_alternate_tail_construction_blocks_with_exact_span(
    text: str, code: str, construction: str, prefix: str
) -> None:
    """Block the reviewed alternate construction with its exact original span."""

    source = f"{prefix}{text}"
    report = validate_llm_output(source, domain="fitchef_mascot")
    matches = [finding for finding in report.blockers if finding.code == code]
    assert report.ok is False
    assert len(matches) == 1
    assert matches[0].matched == construction
    assert matches[0].start == source.index(construction)
    assert matches[0].end == matches[0].start + len(construction)


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Не наказывай себя за еду.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("Накажи.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("No te castigues por comer.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("Castiga.", "FITCHEF_PUNITIVE_RECOVERY"),
        ("Esto no cura la ansiedad.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("La palabra cura aparece en el texto.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("No puedo diagnosticarte.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("No puedo darte un diagnóstico.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("La palabra diagnostico aparece en el texto.", "WELLNESS_MEDICAL_CLAIM_ES"),
        ("Я не знаю, почему ты это сделал.", "FITCHEF_THERAPIST_DRIFT"),
        ("No sé por qué lo hiciste.", "FITCHEF_THERAPIST_DRIFT"),
        ("Puedes explorar por qué pasó sin asumir motivos.", "FITCHEF_THERAPIST_DRIFT"),
    ],
)
def test_reviewed_construction_near_misses_do_not_match(text: str, code: str) -> None:
    """Leave the reviewed near misses outside the bounded construction matches."""

    report = validate_llm_output(text, domain="fitchef_mascot")
    assert not any(finding.code == code for finding in report.blockers)
