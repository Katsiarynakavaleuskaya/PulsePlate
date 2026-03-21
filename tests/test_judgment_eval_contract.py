"""Tests for deterministic judgment eval contract helpers."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Callable

import pytest

from core.judgment_eval import (
    _contains_marker,
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


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_validate_fitchef_replay_pack_accepts_fixture() -> None:
    """The canonical replay pack must validate without runtime dependencies."""

    pack = validate_fitchef_replay_pack(_load_fixture())

    assert pack["mode"] == "fitchef_judgment_replay"
    assert pack["task_class"] == "judgment_adjudication"
    assert len(pack["cases"]) == 9


def test_validate_fitchef_replay_pack_rejects_missing_scores() -> None:
    """Missing per-axis scores must fail closed."""

    payload = _load_fixture()
    del payload["cases"][0]["minimum_scores"]["actionability"]

    with pytest.raises(ValueError, match="minimum_scores.actionability"):
        validate_fitchef_replay_pack(payload)


def test_judgment_eval_helper_edges_fail_closed() -> None:
    """Private helper edges should stay deterministic and fail closed."""

    assert _score_ratio(3, 4) == 4
    assert _contains_marker("steady dinner routine", "") is False

    with pytest.raises(ValueError, match="fitchef markers must be a list"):
        _normalize_string_list("not-a-list", label="fitchef markers")

    with pytest.raises(ValueError, match="FitChef case must include a non-empty case_id"):
        _require_case_string({}, key="case_id", label="FitChef case")

    with pytest.raises(ValueError, match="FitChef payload must be an object"):
        _require_object([], label="FitChef payload")


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda payload: payload.__setitem__("schema_version", "9.9"),
            "schema_version must equal",
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


def test_evaluate_fitchef_replay_case_emits_claim_records_and_uncertainty() -> None:
    """One replay case should emit normalized claim records and uncertainty labels."""

    pack = validate_fitchef_replay_pack(_load_fixture())
    result = evaluate_fitchef_replay_case(pack["cases"][0])

    assert result["decision"] == "promote"
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
