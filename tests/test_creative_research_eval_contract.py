"""Tests for creative research offline eval contract helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.creative_research import _max_similarity
from scripts.orchestration.creative_research_eval_contract import (
    _count_hints,
    build_scorecard,
    classify_output,
    evaluate_bundle,
    normalize_creative_research_text,
    select_promotion_decision,
    validate_bundle,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "orchestration" / "creative_research"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_validate_bundle_accepts_creative_research_fixture() -> None:
    """The canonical PR-B fixture should normalize successfully."""

    bundle = validate_bundle(_load_fixture("bundle_valid.json"))

    assert bundle["task_class"] == "creative_research"
    assert bundle["phase"] == "verification"
    assert len(bundle["candidates"]) == 3
    assert bundle["candidates"][0]["candidate_id"] == "hyp-batch"


def test_validate_bundle_rejects_non_creative_task_class() -> None:
    """The PR-B harness must stay pinned to creative_research only."""

    bundle = _load_fixture("bundle_valid.json")
    bundle["task_class"] = "Experimentation"

    with pytest.raises(ValueError, match="task_class"):
        validate_bundle(bundle)


def test_validate_bundle_rejects_unknown_confidence_level() -> None:
    """Confidence must stay within the deterministic offline enum."""

    bundle = _load_fixture("bundle_valid.json")
    bundle["candidates"][0]["confidence"] = "certain"

    with pytest.raises(ValueError, match="confidence must be one of"):
        validate_bundle(bundle)


def test_evaluate_bundle_classifies_valid_output_types() -> None:
    """Valid PR-B fixture candidates should map to the three governed output classes."""

    result = evaluate_bundle(_load_fixture("bundle_valid.json"))
    by_id = {candidate["candidate_id"]: candidate for candidate in result["candidates"]}

    assert by_id["hyp-batch"]["output_class"] == "mechanistic_hypothesis"
    assert by_id["hyp-template"]["output_class"] == "experimental_proposal"
    assert by_id["hyp-weekend"]["output_class"] == "anomaly_explanation_candidate"
    assert by_id["hyp-batch"]["promotion_decision"] == "promote"
    assert result["summary"]["candidate_count"] == 3


def test_count_hints_matches_token_boundaries_for_short_markers() -> None:
    """Short hints like `ab` and `if` must not match inside unrelated words."""

    assert _count_hints("Habit loops improve adherence over time.", ("ab",)) == 0
    assert _count_hints("Specific friction cues shape adherence.", ("if",)) == 0
    assert _count_hints("Run an AB cohort compare over two weeks.", ("ab", "compare")) == 2
    assert _count_hints("If adherence stays flat, the mechanism is wrong.", ("if", "wrong")) == 2


def test_classify_output_does_not_promote_substring_false_positives() -> None:
    """Substring collisions must not turn ideation into proposal or anomaly classes."""

    candidate = {
        "candidate_id": "substring-guard",
        "claim": "Specific habit loops improve consistency.",
        "mechanism": "Habit scaffolds reduce switching friction and decision fatigue.",
        "evidence_needed": "Collect diary notes from a small user group.",
        "falsifier": "Track adherence outcomes across the observation window.",
        "confidence": "medium",
        "known_risks": ["self-report bias"],
        "wellness_boundary": "Wellness-only framing, not diagnosis or treatment.",
    }

    output_class, controls = classify_output(candidate)

    assert output_class == "mechanistic_hypothesis"
    assert controls == []


def test_normalize_text_and_similarity_cover_empty_inputs() -> None:
    """Normalization and similarity helpers must stay deterministic on edge inputs."""

    assert normalize_creative_research_text("A/B-test:_cohort", " compare(measure).") == (
        "a b test cohort compare measure"
    )
    assert _count_hints("Measure cohort outcomes.", (".", "cohort")) == 1
    assert _max_similarity(set(), [set(), {"signal"}]) == 0.0
    assert _max_similarity({"signal"}, [set()]) == 0.0


@pytest.mark.parametrize(
    ("bundle_mutator", "message"),
    [
        (lambda bundle: bundle.update({"phase": "chaos"}), "phase must be one of"),
        (
            lambda bundle: bundle.update({"reference_corpus": "not-a-list"}),
            "reference_corpus must be a list",
        ),
        (
            lambda bundle: bundle.update({"candidates": []}),
            "candidates must be a non-empty list",
        ),
        (
            lambda bundle: bundle["candidates"].__setitem__(0, "bad-candidate"),
            "candidate #1 must be an object",
        ),
        (
            lambda bundle: bundle["candidates"][0].update({"candidate_id": ""}),
            "candidate_id",
        ),
    ],
)
def test_validate_bundle_rejects_additional_invalid_shapes(
    bundle_mutator: object,
    message: str,
) -> None:
    """Validation must fail closed on malformed bundles and candidates."""

    bundle = _load_fixture("bundle_valid.json")
    bundle_mutator(bundle)

    with pytest.raises(ValueError, match=message):
        validate_bundle(bundle)


def test_validate_bundle_rejects_non_object_payload() -> None:
    """Top-level payload must stay a JSON object."""

    with pytest.raises(ValueError, match="must be a JSON object"):
        validate_bundle(["not", "a", "dict"])


def test_build_scorecard_covers_controls_and_midrange_branches() -> None:
    """Scorecard logic must cover duplicate, overlap, weak falsifier, and boundary branches."""

    candidate = {
        "candidate_id": "dup-mid",
        "claim": "Weekend depletion may shape adherence.",
        "mechanism": "Friction cues shape adherence under shifting routines.",
        "evidence_needed": "Collect weekly meal logs with cohort notes.",
        "falsifier": "Track weekly logs carefully.",
        "confidence": "medium",
        "known_risks": [],
        "wellness_boundary": "Wellness support only.",
    }

    scorecard, controls = build_scorecard(
        candidate,
        output_class="mechanistic_hypothesis",
        reference_overlap=0.8,
        peer_overlap=0.85,
        duplicate_candidate=True,
    )

    assert "duplicate_candidate" in controls
    assert "corpus_overlap_high" in controls
    assert "weak_falsifier" in controls
    assert scorecard["flexibility"] == 0
    assert scorecard["mechanism_specificity"] == 2
    assert scorecard["groundedness"] == 3
    assert scorecard["falsifiability"] == 1
    assert scorecard["wellness_safety"] == 4


def test_build_scorecard_covers_high_specificity_and_non_wellness_boundary() -> None:
    """High-information candidates should hit the strong scoring branches deterministically."""

    candidate = {
        "candidate_id": "strong-signal",
        "claim": "A structured fallback meal may improve adherence under time scarcity.",
        "mechanism": (
            "Because a predefined fallback sequence reduces switching friction, preserves planning "
            "momentum, sustains a feedback loop, clarifies the next action, anchors an observable "
            "cue, and reduces overload during evening decisions."
        ),
        "evidence_needed": "Observe meal completion after repeated fallback prompts.",
        "falsifier": "Compare repeated null results despite cohort replication.",
        "confidence": "low",
        "known_risks": ["confounding"],
        "wellness_boundary": "General lifestyle support.",
    }

    scorecard, controls = build_scorecard(
        candidate,
        output_class="mechanistic_hypothesis",
        reference_overlap=0.15,
        peer_overlap=0.22,
        duplicate_candidate=False,
    )

    assert controls == []
    assert scorecard["mechanism_specificity"] == 5
    assert scorecard["groundedness"] == 3
    assert scorecard["falsifiability"] == 4
    assert scorecard["wellness_safety"] == 3


def test_select_promotion_decision_returns_defer_for_safe_but_non_promotable_scores() -> None:
    """Safe candidates that miss promotion thresholds must degrade to defer."""

    decision, label = select_promotion_decision(
        output_class="mechanistic_hypothesis",
        scorecard={
            "originality": 3,
            "flexibility": 2,
            "mechanism_specificity": 3,
            "groundedness": 3,
            "falsifiability": 3,
            "wellness_safety": 5,
            "hallucination_risk": 2,
        },
        negative_controls=[],
    )

    assert decision == "defer"
    assert label == "interesting but unverified hypothesis"
