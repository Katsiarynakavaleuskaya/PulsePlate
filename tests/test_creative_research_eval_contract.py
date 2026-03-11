"""Tests for creative research offline eval contract helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration.creative_research_eval_contract import evaluate_bundle, validate_bundle

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
