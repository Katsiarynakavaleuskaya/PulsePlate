"""Replay-pack regression tests for FitChef offline judgment eval."""

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
    / "replay_cases.json"
)


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fitchef_replay_pack_matches_expected_decisions_and_scores() -> None:
    """Every replay case should satisfy its deterministic decision and score floor."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    results = {result["case_id"]: result for result in evaluate_fitchef_replay_pack(pack)}

    for case in pack["cases"]:
        result = results[case["case_id"]]
        assert result["decision"] == case["expected_decision"]
        assert result["uncertainty_profile"] == case["expected_uncertainty_profile"]
        for axis, minimum_score in case["minimum_scores"].items():
            assert result["scores"][axis] >= minimum_score


def test_fitchef_replay_pack_hard_fails_unsafe_cases_only() -> None:
    """Unsafe scenarios should discard; safe scenarios should stay free of hard-fail reasons."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    results = {result["case_id"]: result for result in evaluate_fitchef_replay_pack(pack)}

    assert results["self_punishment_request"]["hard_fail_reasons"]
    assert results["diagnosis_bait"]["hard_fail_reasons"]
    assert not results["cravings_afternoon"]["hard_fail_reasons"]
    assert not results["guilt_after_dessert"]["hard_fail_reasons"]
