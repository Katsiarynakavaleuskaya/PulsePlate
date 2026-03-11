"""Tests for creative research offline eval contract helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration.creative_research_eval_contract import (
    _count_hints,
    classify_output,
    evaluate_bundle,
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
