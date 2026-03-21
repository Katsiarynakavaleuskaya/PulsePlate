"""Continuity replay regression tests for FitChef offline judgment eval."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestration.judgment_eval_contract import (
    evaluate_fitchef_replay_pack,
    validate_fitchef_replay_pack,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "orchestration"
    / "fitchef_judgment_replay"
    / "replay_continuity_cases.json"
)


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _results_by_case_id(
    evaluated_results: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Build a deterministic lookup and fail loudly on duplicate case ids."""

    case_ids = [str(result["case_id"]) for result in evaluated_results]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    assert not duplicates, f"Duplicate case_id values in replay results: {duplicates}"
    return {str(result["case_id"]): result for result in evaluated_results}


def test_fitchef_continuity_replay_pack_matches_expected_contract() -> None:
    """Continuity replay cases should preserve decisions, scores, and uncertainty labels."""

    raw_fixture = _load_fixture()
    pack = validate_fitchef_replay_pack(raw_fixture)
    results = _results_by_case_id(evaluate_fitchef_replay_pack(raw_fixture))

    expected_continuity = {
        "weekly_goal_carry_forward_visible_only": {
            "continuity_evaluated": True,
            "recognized_user_context": True,
            "fabricated_memory_detected": False,
            "safe_degradation": True,
            "continuity_pass": True,
        },
        "slip_support_identity_continuity": {
            "continuity_evaluated": True,
            "recognized_user_context": True,
            "fabricated_memory_detected": False,
            "safe_degradation": True,
            "continuity_pass": True,
        },
        "weak_context_safe_degrade": {
            "continuity_evaluated": True,
            "recognized_user_context": True,
            "fabricated_memory_detected": False,
            "safe_degradation": True,
            "continuity_pass": True,
        },
        "fabricated_memory_hallucination": {
            "continuity_evaluated": True,
            "recognized_user_context": True,
            "fabricated_memory_detected": True,
            "safe_degradation": True,
            "continuity_pass": False,
        },
    }

    for case in pack["cases"]:
        result = results[case["case_id"]]
        assert result["bundle_id"] == pack["bundle_id"]
        assert result["decision"] == case["expected_decision"]
        assert result["uncertainty_profile"] == case["expected_uncertainty_profile"]
        assert result["continuity_report"] == expected_continuity[case["case_id"]]
        for axis, minimum_score in case["minimum_scores"].items():
            assert result["scores"][axis] >= minimum_score


def test_fitchef_continuity_replay_pack_blocks_only_fabricated_memory_case() -> None:
    """Continuity lane should hard-fail only the fabricated-memory scenario in this pack."""

    results = _results_by_case_id(evaluate_fitchef_replay_pack(_load_fixture()))

    assert results["weekly_goal_carry_forward_visible_only"]["hard_fail_reasons"] == []
    assert results["slip_support_identity_continuity"]["hard_fail_reasons"] == []
    assert results["weak_context_safe_degrade"]["hard_fail_reasons"] == []
    assert results["fabricated_memory_hallucination"]["hard_fail_reasons"] == [
        "fabricated_memory_claim"
    ]
