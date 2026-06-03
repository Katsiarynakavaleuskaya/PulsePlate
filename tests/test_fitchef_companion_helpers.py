"""Focused unit tests for FitChef structured companion helpers."""

from __future__ import annotations

import pytest

from core.insight.fitchef_companion import (
    _build_distortion_reason,
    _extract_json_payload,
    _fallback_balanced_reframe,
    _fallback_next_small_action,
    _infer_distortion_labels,
    _normalize_distortion_labels,
    _normalize_string_list,
    _normalize_structured_string,
    _structured_texts_are_safe,
    build_distortion_simulator_prompt,
    build_identity_loop_mapper_prompt,
    has_high_distress_boundary,
    prepare_distortion_simulator_draft,
    prepare_identity_loop_mapper_draft,
)


def test_build_distortion_simulator_prompt_includes_rag_context() -> None:
    """Structured distortion prompt should embed CBT context when available."""

    prompt = build_distortion_simulator_prompt(
        "I ate dessert after dinner",
        "I ruined the whole day",
        "guilt",
        "steady dinners",
        "CBT context block",
    )

    assert "Relevant CBT context:\nCBT context block" in prompt
    assert "Goal: steady dinners" in prompt


def test_prepare_distortion_simulator_draft_normalizes_aliases_and_defaults() -> None:
    """Missing structured fields should fall back to deterministic safe values."""

    draft = prepare_distortion_simulator_draft(
        """
        {
          "distortion_labels": ["black and white thinking"],
          "why_it_matches": "",
          "evidence_for": [],
          "evidence_against": [],
          "balanced_reframe": "",
          "next_small_action": ""
        }
        """,
        situation="I ate dessert after dinner",
        automatic_thought="I ruined the whole day",
        emotion="guilt",
        goal="steady dinners",
    )

    assert draft.distortion_labels == ["all_or_nothing_thinking"]
    assert "middle ground" in draft.why_it_matches
    assert any("steady dinners" in item for item in draft.evidence_against)
    assert "steady dinners" in draft.balanced_reframe
    assert "steady dinners" in draft.next_small_action
    assert draft.warnings == []


def test_prepare_distortion_simulator_draft_rewrites_unsafe_payload() -> None:
    """Unsafe clinical/provider language must fall back to the safe draft."""

    draft = prepare_distortion_simulator_draft(
        """
        {
          "distortion_labels": ["catastrophizing"],
          "why_it_matches": "This diagnoses your condition.",
          "evidence_for": ["You need therapy now."],
          "evidence_against": ["None."],
          "balanced_reframe": "A therapist should fix this.",
          "next_small_action": "Start treatment immediately."
        }
        """,
        situation="Dinner felt chaotic",
        automatic_thought="Nothing will ever work",
        emotion="panic",
        goal=None,
    )

    assert draft.distortion_labels == ["catastrophizing"]
    assert draft.warnings == ["wellness_language_rewritten"]
    assert draft.next_small_action == (
        "Write one kinder replacement thought and pair it with one concrete next meal or habit step."
    )


def test_build_identity_loop_mapper_prompt_includes_exact_shape_and_context() -> None:
    """Identity-loop prompt should demand the frozen JSON shape and CBT context."""

    prompt = build_identity_loop_mapper_prompt(
        "steady dinners",
        "I stop planning dinner after one hard evening",
        "I am too inconsistent",
        "work runs late",
        "CBT identity-loop context",
    )

    assert '"identity_loop"' in prompt
    assert '"identity_shift_statement"' in prompt
    assert "Relevant CBT context:\nCBT identity-loop context" in prompt
    assert "Trigger context: work runs late" in prompt
    assert "Do not label the user's identity" in prompt


def test_prepare_identity_loop_mapper_draft_normalizes_valid_payload() -> None:
    """Identity-loop draft parser should normalize the structured provider object."""

    draft = prepare_identity_loop_mapper_draft(
        """
        {
          "identity_loop": {
            "belief": "  If dinner slips, the whole routine is broken. ",
            "behavior": "I stop planning after one hard evening.",
            "short_term_reward": "Pressure drops for a moment.",
            "long_term_cost": "The next meal gets less support."
          },
          "identity_shift_statement": "I can practice returning after one hard moment.",
          "replacement_action": "Choose one default dinner today.",
          "repair_if_slip": "Name the slip calmly and restart at the next meal."
        }
        """,
        goal="steady dinners",
        recent_pattern="I stop planning dinner after one hard evening",
        self_talk="I am too inconsistent",
        trigger_context="work runs late",
    )

    assert draft.belief == "If dinner slips, the whole routine is broken."
    assert draft.behavior == "I stop planning after one hard evening."
    assert draft.short_term_reward == "Pressure drops for a moment."
    assert draft.long_term_cost == "The next meal gets less support."
    assert draft.identity_shift_statement.startswith("I can practice returning")
    assert draft.warnings == []


def test_prepare_identity_loop_mapper_draft_falls_back_without_trigger_context() -> None:
    """Malformed identity-loop JSON should return a complete deterministic fallback."""

    draft = prepare_identity_loop_mapper_draft(
        "not json",
        goal="steady dinners",
        recent_pattern="I stop planning dinner after one hard evening",
        self_talk="I am too inconsistent",
        trigger_context=None,
    )

    assert draft.warnings == ["structured_parse_fallback"]
    assert draft.belief
    assert "when planning gets hard" in draft.behavior
    assert "steady dinners" in draft.replacement_action
    assert draft.repair_if_slip.startswith("Name the slip calmly")


def test_prepare_identity_loop_mapper_draft_sanitizes_unsafe_goal_fallback() -> None:
    """Fallback text should not echo unsafe food-morality goal language."""

    draft = prepare_identity_loop_mapper_draft(
        "not json",
        goal="avoid bad foods",
        recent_pattern="I stop planning dinner after one hard evening",
        self_talk="I am too inconsistent",
        trigger_context=None,
    )

    assert "bad foods" not in draft.replacement_action.lower()
    assert "current wellness goal" in draft.replacement_action
    assert _structured_texts_are_safe(draft.replacement_action)


def test_prepare_identity_loop_mapper_draft_rewrites_unsafe_payload() -> None:
    """Clinical/provider language must fall back to the safe identity-loop draft."""

    draft = prepare_identity_loop_mapper_draft(
        """
        {
          "identity_loop": {
            "belief": "This diagnosis means you need treatment.",
            "behavior": "A therapist should decide your meals.",
            "short_term_reward": "Treatment fixes the problem.",
            "long_term_cost": "You will relapse without therapy."
          },
          "identity_shift_statement": "You are a patient now.",
          "replacement_action": "Start treatment immediately.",
          "repair_if_slip": "Call crisis support for dinner planning."
        }
        """,
        goal="steady dinners",
        recent_pattern="I stop planning dinner after one hard evening",
        self_talk="I am too inconsistent",
        trigger_context="work runs late",
    )

    assert draft.warnings == ["wellness_language_rewritten"]
    assert draft.belief.startswith("One difficult planning moment")
    assert "when the same trigger shows up" in draft.behavior
    assert "treatment" not in draft.replacement_action.lower()


def test_identity_loop_mapper_detects_high_distress_boundary() -> None:
    """High-distress text should leave the identity-loop personalization lane."""

    assert has_high_distress_boundary("steady dinners", "I might kill myself tonight")
    assert has_high_distress_boundary("I want to hurt myself")
    assert has_high_distress_boundary("I do not want to live")
    assert not has_high_distress_boundary("I felt disappointed after dinner planning slipped")


def test_extract_json_payload_accepts_fenced_and_embedded_objects() -> None:
    """Structured JSON extraction should support fenced and embedded payloads."""

    fenced = _extract_json_payload("""```json\n{\"candidate\": 1}\n```""")
    embedded = _extract_json_payload('prefix {"candidate": 2} suffix')

    assert fenced == {"candidate": 1}
    assert embedded == {"candidate": 2}


def test_extract_json_payload_rejects_non_object_json() -> None:
    """Structured JSON extraction should fail closed for non-object payloads."""

    with pytest.raises(ValueError, match="did not contain a JSON object"):
        _extract_json_payload("[1, 2, 3]")


def test_extract_json_payload_rejects_non_dict_decoder_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Embedded payload parsing should fail closed when the decoder does not return a dict."""

    monkeypatch.setattr(
        "core.insight.fitchef_companion.json.loads",
        lambda _raw: ["not", "a", "dict"],
    )

    with pytest.raises(ValueError, match="JSON must be an object"):
        _extract_json_payload('prefix {"candidate": 2} suffix')


def test_normalize_structured_string_and_list_fail_closed() -> None:
    """Normalization helpers should degrade cleanly on invalid shapes."""

    assert _normalize_structured_string(123) == ""
    assert _normalize_structured_string("  one   two  ") == "one two"
    assert _normalize_string_list("bad-shape") == []
    assert _normalize_string_list([" one ", "", 3, "two"]) == ["one", "two"]


def test_normalize_distortion_labels_defaults_when_unknown() -> None:
    """Unknown distortion labels must fall back to the stable default."""

    assert _normalize_distortion_labels(["mental filtering"]) == ["mental_filtering"]
    assert _normalize_distortion_labels(["unknown"]) == ["emotional_reasoning"]


def test_normalize_distortion_labels_ignores_non_string_values() -> None:
    """Non-string distortion label candidates must be ignored safely."""

    assert _normalize_distortion_labels([None, "mental filtering", 7]) == ["mental_filtering"]


@pytest.mark.parametrize(
    ("automatic_thought", "expected_label"),
    [
        ("I should be perfect here", "should_statements"),
        ("I feel this means it is true", "emotional_reasoning"),
        ("Nothing good happened, I only failed", "mental_filtering"),
        ("This setback is awful and nothing will work", "catastrophizing"),
        ("Always ruined, completely failed", "all_or_nothing_thinking"),
    ],
)
def test_infer_distortion_labels_covers_core_branches(
    automatic_thought: str,
    expected_label: str,
) -> None:
    """Automatic thought inference should map to canonical distortion labels."""

    assert expected_label in _infer_distortion_labels(automatic_thought)


def test_infer_distortion_labels_defaults_when_no_pattern_matches() -> None:
    """Inference should fall back to the canonical default when no heuristic matches."""

    assert _infer_distortion_labels("A plain observation with no strong cognitive marker.") == [
        "emotional_reasoning"
    ]


@pytest.mark.parametrize(
    ("labels", "automatic_thought", "expected_fragment"),
    [
        (["catastrophizing"], "I ruined everything", "worst-case"),
        (["should_statements"], "I should do better", "rigid rules"),
        (["mental_filtering"], "I only see the bad parts", "negative part"),
        ([], "I feel awful", "feelings are not the whole evidence"),
        ([], "Just one interpretation", "only one interpretation"),
    ],
)
def test_build_distortion_reason_covers_label_branches(
    labels: list[str],
    automatic_thought: str,
    expected_fragment: str,
) -> None:
    """Reason builder should return stable explanations across branch labels."""

    assert expected_fragment in _build_distortion_reason(
        labels=labels,
        automatic_thought=automatic_thought,
    )


def test_safe_helpers_cover_no_goal_and_empty_belief_branches() -> None:
    """Goal-free and empty self-talk fallbacks should remain deterministic."""

    assert "only interpretation" in _fallback_balanced_reframe(
        automatic_thought="I blew it",
        goal=None,
    )
    assert _fallback_next_small_action(goal=None).startswith("Write one kinder replacement")


def test_structured_texts_are_safe_flags_unsafe_language() -> None:
    """Structured wellness validator should reject clinical escalation language."""

    assert _structured_texts_are_safe("Choose one calm next step.")
    assert not _structured_texts_are_safe("This diagnosis needs treatment.")
