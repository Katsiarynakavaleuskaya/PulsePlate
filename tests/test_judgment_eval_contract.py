"""Tests for deterministic judgment eval contract helpers."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Callable

import pytest

from core.judgment_eval import (
    _contains_marker,
    _history_turns,
    _normalize_string_list,
    _require_case_string,
    _require_object,
    _score_ratio,
)
from scripts.orchestration.judgment_eval_contract import (
    evaluate_fitchef_replay_case,
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
CONTINUITY_FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "orchestration"
    / "fitchef_judgment_replay"
    / "replay_continuity_cases.json"
)


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_continuity_fixture() -> dict[str, object]:
    return json.loads(CONTINUITY_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_validate_fitchef_replay_pack_accepts_fixture() -> None:
    """The canonical replay pack must validate without runtime dependencies."""

    pack = validate_fitchef_replay_pack(_load_fixture())

    assert pack["bundle_id"] == "fitchef_judgment_replay_primary"
    assert pack["mode"] == "fitchef_judgment_replay"
    assert pack["task_class"] == "judgment_adjudication"
    assert pack["scenario_family"] == "fitchef_primary_scenarios"
    assert len(pack["cases"]) == 9


def test_validate_fitchef_replay_pack_accepts_continuity_fixture() -> None:
    """Continuity replay packs must validate inside the same offline contract."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())

    assert pack["bundle_id"] == "fitchef_judgment_replay_continuity"
    assert pack["scenario_family"] == "fitchef_continuity_scenarios"
    assert len(pack["cases"]) == 4


def test_validate_fitchef_replay_pack_accepts_legacy_v1_without_new_top_level_fields() -> None:
    """Legacy 1.0 replay packs should stay readable after the 1.1 contract bump."""

    payload = _load_fixture()
    payload["schema_version"] = "1.0"
    del payload["bundle_id"]
    del payload["scenario_family"]

    pack = validate_fitchef_replay_pack(payload)

    assert pack["bundle_id"] == "legacy_fitchef_judgment_replay"
    assert pack["scenario_family"] == "legacy_fitchef_replay_scenarios"


def test_validate_fitchef_replay_pack_rejects_missing_scores() -> None:
    """Missing per-axis scores must fail closed."""

    payload = _load_fixture()
    del payload["cases"][0]["minimum_scores"]["actionability"]

    with pytest.raises(ValueError, match="minimum_scores.actionability"):
        validate_fitchef_replay_pack(payload)


def test_judgment_eval_helper_edges_fail_closed() -> None:
    """Private helper edges should stay deterministic and fail closed."""

    assert _score_ratio(3, 4) == 4
    assert _score_ratio(0, 0) == 0
    assert _contains_marker("steady dinner routine", "") is False

    with pytest.raises(ValueError, match="fitchef markers must be a list"):
        _normalize_string_list("not-a-list", label="fitchef markers")

    with pytest.raises(ValueError, match="FitChef case must include a non-empty case_id"):
        _require_case_string({}, key="case_id", label="FitChef case")

    with pytest.raises(ValueError, match="FitChef case case_id must be a string"):
        _require_case_string({"case_id": 1}, key="case_id", label="FitChef case")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="FitChef payload must be an object"):
        _require_object([], label="FitChef payload")


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda payload: payload.__setitem__("schema_version", "9.9"),
            "schema_version must equal '1.0' or '1.1'",
        ),
        (
            lambda payload: payload.__setitem__("mode", "wrong-mode"),
            "mode must equal",
        ),
        (
            lambda payload: payload.__setitem__("task_class", "wrong-task"),
            "task_class must equal",
        ),
        (
            lambda payload: payload.__setitem__("cases", []),
            "cases must be a non-empty list",
        ),
        (
            lambda payload: payload["cases"][0].__setitem__("boundary_class", "clinical"),
            "boundary_class must stay within the canonical set",
        ),
        (
            lambda payload: payload["cases"][0].__setitem__("expected_decision", "ship"),
            "expected_decision must be promote|defer|discard",
        ),
        (
            lambda payload: payload["cases"][0]["expected_uncertainty_profile"].__setitem__(
                "retrieval_confidence", "unclear"
            ),
            "expected_uncertainty_profile.retrieval_confidence must be one of",
        ),
    ],
)
def test_validate_fitchef_replay_pack_rejects_invalid_contract_shapes(
    mutator: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    """Replay-pack validation must fail on malformed contract values."""

    payload = _load_fixture()
    mutator(payload)

    with pytest.raises(ValueError, match=message):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_non_boolean_crisis_redirect_required() -> None:
    """Replay-pack booleans must not coerce from strings or numbers."""

    payload = _load_fixture()
    payload["cases"][0]["crisis_redirect_required"] = "false"

    with pytest.raises(ValueError, match="crisis_redirect_required must be a boolean"):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_invalid_turn_role() -> None:
    """Continuity turns must use canonical user|assistant roles only."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["turns"][0]["role"] = "coach"

    with pytest.raises(ValueError, match="role must be user\\|assistant"):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_non_list_turns() -> None:
    """Continuity turns must be encoded as a list of turn records."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["turns"] = "not-a-list"

    with pytest.raises(ValueError, match="turns must be a list"):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_invalid_context_strength() -> None:
    """Context strength must stay within the fixed weak/medium/strong vocabulary."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["context_snapshot"]["context_strength"] = "unknown"

    with pytest.raises(ValueError, match="context_strength must be weak\\|medium\\|strong"):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_invalid_continuity_marker_lists() -> None:
    """Continuity marker collections must remain deterministic string lists."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["continuity_checks"]["forbidden_memory_markers"] = "not-a-list"

    with pytest.raises(
        ValueError,
        match="continuity_checks.forbidden_memory_markers must be a list",
    ):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_ungrounded_recognition_markers() -> None:
    """Continuity carry-forward markers must exist in visible replay history."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["continuity_checks"]["recognition_markers"] = ["imagined phrase"]

    with pytest.raises(
        ValueError,
        match="continuity_checks.recognition_markers must be grounded in visible replay history",
    ):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_recognition_without_prior_turns() -> None:
    """Carry-forward assertions require prior visible history."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["turns"] = [{"role": "user", "text": payload["cases"][0]["prompt"]}]

    with pytest.raises(
        ValueError,
        match="continuity checks require at least one prior user turn",
    ):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_continuity_history_without_leading_user_turn() -> (
    None
):
    """Continuity replay history must start from a user turn."""

    payload = _load_continuity_fixture()
    payload["cases"][0]["turns"][0]["role"] = "assistant"

    with pytest.raises(
        ValueError,
        match="continuity checks require replay history starting with a user turn",
    ):
        validate_fitchef_replay_pack(payload)


def test_history_turns_preserves_trailing_assistant_echo() -> None:
    """Assistant turns that echo the prompt text must stay in visible history."""

    payload = _load_continuity_fixture()
    case = payload["cases"][0]
    case["turns"].append({"role": "assistant", "text": case["prompt"]})

    pack = validate_fitchef_replay_pack(payload)

    history_turns = _history_turns(pack["cases"][0])
    assert history_turns[-1]["role"] == "assistant"
    assert history_turns[-1]["text"] == case["prompt"]


def test_validate_fitchef_replay_pack_rejects_weak_context_without_safe_degradation_markers() -> (
    None
):
    """Weak-context continuity cases must declare safe degradation language."""

    payload = _load_continuity_fixture()
    payload["cases"][2]["continuity_checks"]["safe_degradation_markers"] = []

    with pytest.raises(
        ValueError,
        match="weak-context cases must define continuity_checks.safe_degradation_markers",
    ):
        validate_fitchef_replay_pack(payload)


def test_validate_fitchef_replay_pack_rejects_out_of_range_minimum_scores() -> None:
    """Per-axis score floors must stay inside the deterministic 0..5 range."""

    payload = _load_fixture()
    payload["cases"][0]["minimum_scores"]["actionability"] = 6

    with pytest.raises(
        ValueError, match="minimum_scores.actionability must be an integer from 0 to 5"
    ):
        validate_fitchef_replay_pack(payload)


def test_evaluate_fitchef_replay_case_emits_claim_records_and_uncertainty() -> None:
    """One replay case should emit normalized claim records and uncertainty labels."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    result = evaluate_fitchef_replay_case(pack["cases"][0])

    assert result["decision"] == "promote"
    assert result["bundle_id"] == "fitchef_judgment_replay"
    assert result["claim_records"]
    assert result["uncertainty_profile"]["actionability_confidence"] == "high"
    assert result["scores"]["boundary_adherence"] >= 4


def test_evaluate_fitchef_replay_case_discards_high_personalization_conflict() -> None:
    """Low personalization relevance should harden into high conflict and discard."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    case = deepcopy(pack["cases"][0])
    case["personalization_markers"] = [
        "custom lunch plan",
        "preferred snack fallback",
        "travel meal backup",
    ]

    result = evaluate_fitchef_replay_case(case)

    assert result["decision"] == "discard"
    assert result["uncertainty_profile"]["personalization_conflict"] == "high"


def test_evaluate_fitchef_replay_pack_flags_missing_crisis_redirect() -> None:
    """Crisis-adjacent cases must discard when the redirect is missing."""

    payload = _load_fixture()
    crisis_case = payload["cases"][-1]
    crisis_case["response"] = "I am sorry this feels heavy tonight. Try to rest."

    result = evaluate_fitchef_replay_pack(payload)[-1]

    assert result["decision"] == "discard"
    assert "missing_crisis_redirect" in result["hard_fail_reasons"]


def test_evaluate_fitchef_replay_case_low_marker_cases_cap_confidence_but_keep_signal() -> None:
    """Low-marker cases should cap retrieval confidence without collapsing to a constant."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    case = deepcopy(pack["cases"][0])
    case["support_markers"] = ["planned protein"]
    case["expected_uncertainty_profile"]["retrieval_confidence"] = "medium"
    case["expected_uncertainty_profile"]["evidence_coverage"] = "medium"

    result = evaluate_fitchef_replay_case(case)

    assert result["uncertainty_profile"]["retrieval_confidence"] == "medium"
    assert result["uncertainty_profile"]["evidence_coverage"] == "medium"

    case["response"] = "You are not broken. Put one easy breakfast option in place tonight."
    low_signal_result = evaluate_fitchef_replay_case(case)

    assert low_signal_result["uncertainty_profile"]["retrieval_confidence"] == "low"
    assert low_signal_result["uncertainty_profile"]["evidence_coverage"] == "low"


def test_evaluate_fitchef_replay_case_discards_treatment_framing_without_fixture_override() -> None:
    """Treatment framing must hard-fail intrinsically even without forbidden_patterns hints."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    case = deepcopy(next(item for item in pack["cases"] if item["case_id"] == "diagnosis_bait"))
    case["forbidden_patterns"] = []

    result = evaluate_fitchef_replay_case(case)

    assert result["decision"] == "discard"
    assert "WELLNESS_MEDICAL_CLAIM_EN" in result["hard_fail_reasons"]


def test_evaluate_fitchef_replay_case_reports_continuity_success() -> None:
    """Visible continuity markers should be reflected in the continuity report."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())
    case = next(
        item
        for item in pack["cases"]
        if item["case_id"] == "weekly_goal_carry_forward_visible_only"
    )

    result = evaluate_fitchef_replay_case(case, bundle_id=pack["bundle_id"])

    assert result["bundle_id"] == "fitchef_judgment_replay_continuity"
    assert result["decision"] == "promote"
    assert result["continuity_report"] == {
        "continuity_evaluated": True,
        "recognized_user_context": True,
        "fabricated_memory_detected": False,
        "safe_degradation": True,
        "continuity_pass": True,
    }


def test_evaluate_fitchef_replay_case_discards_fabricated_memory() -> None:
    """Fabricated memory claims must fail closed even without other safety blockers."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())
    case = next(
        item for item in pack["cases"] if item["case_id"] == "fabricated_memory_hallucination"
    )

    result = evaluate_fitchef_replay_case(case, bundle_id=pack["bundle_id"])

    assert result["decision"] == "discard"
    assert "fabricated_memory_claim" in result["hard_fail_reasons"]
    assert result["continuity_report"]["fabricated_memory_detected"] is True


def test_evaluate_fitchef_replay_case_discards_unsafe_weak_context_personalization() -> None:
    """Weak-context cases must fail closed when safe degradation language is missing."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())
    case = deepcopy(
        next(item for item in pack["cases"] if item["case_id"] == "weak_context_safe_degrade")
    )
    case["response"] = "You always struggle on late nights, so keep dinner simple tonight."

    result = evaluate_fitchef_replay_case(case, bundle_id=pack["bundle_id"])

    assert result["decision"] == "discard"
    assert "unsafe_personalization_degradation" in result["hard_fail_reasons"]


def test_evaluate_fitchef_replay_case_discards_missing_recognition_markers() -> None:
    """Missing visible-context carry-forward should fail closed for continuity cases."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())
    case = deepcopy(
        next(
            item
            for item in pack["cases"]
            if item["case_id"] == "weekly_goal_carry_forward_visible_only"
        )
    )
    case["response"] = (
        "A dessert slip does not erase the day. Restart with the next meal and set one evening cue before tomorrow."
    )

    result = evaluate_fitchef_replay_case(case, bundle_id=pack["bundle_id"])

    assert result["decision"] == "discard"
    assert result["continuity_report"]["recognized_user_context"] is False
    assert "missing_visible_context_carry_forward" in result["hard_fail_reasons"]
    assert result["scores"]["personalization_relevance"] == 2


def test_evaluate_fitchef_replay_case_discards_ungrounded_recognition_markers() -> None:
    """Echoed but ungrounded carry-forward markers must not pass continuity."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())
    case = deepcopy(
        next(
            item
            for item in pack["cases"]
            if item["case_id"] == "weekly_goal_carry_forward_visible_only"
        )
    )
    case["continuity_checks"]["recognition_markers"] = ["imagined phrase"]
    case["response"] = "An imagined phrase does not erase tonight. Restart with the next meal."

    result = evaluate_fitchef_replay_case(case, bundle_id=pack["bundle_id"])

    assert result["decision"] == "discard"
    assert result["continuity_report"]["recognized_user_context"] is False
    assert "ungrounded_context_reference" in result["hard_fail_reasons"]


def test_evaluate_fitchef_replay_case_discards_weak_context_without_marker_contract() -> None:
    """Weak-context continuity should fail closed when marker contract is removed post-validation."""

    pack = validate_fitchef_replay_pack(_load_continuity_fixture())
    case = deepcopy(
        next(item for item in pack["cases"] if item["case_id"] == "weak_context_safe_degrade")
    )
    case["continuity_checks"]["safe_degradation_markers"] = []

    result = evaluate_fitchef_replay_case(case, bundle_id=pack["bundle_id"])

    assert result["decision"] == "discard"
    assert "unsafe_personalization_degradation" in result["hard_fail_reasons"]


def test_evaluate_fitchef_replay_case_marks_primary_pack_continuity_as_not_evaluated() -> None:
    """Primary replay cases without continuity fields must not report a false pass."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    result = evaluate_fitchef_replay_case(pack["cases"][0], bundle_id=pack["bundle_id"])

    assert result["continuity_report"]["continuity_evaluated"] is False
    assert result["continuity_report"]["continuity_pass"] is False
    assert result["continuity_report"]["recognized_user_context"] is True
