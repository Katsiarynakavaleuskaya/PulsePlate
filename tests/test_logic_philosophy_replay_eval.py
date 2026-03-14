"""Tests for the governed logic + philosophy offline replay lane."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.orchestration.logic_philosophy_replay_eval as replay_eval
from scripts.orchestration.logic_philosophy_replay_contract import (
    load_json_document,
    validate_negative_controls_document,
    validate_replay_cases_document,
)
from scripts.orchestration.logic_philosophy_replay_eval import (
    _resolve_output_path,
    evaluate_answer,
    evaluate_replay_documents,
    main,
)

FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "orchestration" / "logic_philosophy_replay"
)


def _fixture(path_name: str) -> Path:
    return FIXTURE_DIR / path_name


def test_validate_replay_cases_document_requires_all_arms() -> None:
    """Replay cases must define all four canonical ablation arms."""

    payload = load_json_document(_fixture("replay_cases.json"), label="Replay cases")
    payload["cases"][0]["arm_outputs"].pop("A3_combined")

    with pytest.raises(ValueError, match="missing required arms: A3_combined"):
        validate_replay_cases_document(payload)


def test_validate_replay_cases_document_requires_zero_network_budget() -> None:
    """Wave 1 replay corpus must stay strictly offline."""

    payload = load_json_document(_fixture("replay_cases.json"), label="Replay cases")
    payload["network_budget"] = 1

    with pytest.raises(ValueError, match="must equal 0 for wave 1 offline replay"):
        validate_replay_cases_document(payload)


def test_validate_negative_controls_document_accepts_fixture() -> None:
    """Known-good controls should validate as immutable offline oracles."""

    payload = load_json_document(
        _fixture("replay_negative_controls.json"),
        label="Replay negative controls",
    )

    validated = validate_negative_controls_document(payload)

    assert validated["network_budget"] == 0
    assert len(validated["known_good_controls"]) == 3


def test_evaluate_answer_flags_unsupported_claims_and_contradictions() -> None:
    """Per-answer scoring should capture unsupported and contradictory claims."""

    result = evaluate_answer(
        answer="A 700 to 800 calorie deficit is always best. This plan is balanced. This plan is not balanced.",
        required_facts=["small calorie deficit"],
        supported_claims=["small calorie deficit"],
        usefulness_markers=["small calorie deficit"],
        contradiction_checker=replay_eval.NonContradictionChecker(),
    )

    assert result["correctness_pass"] is False
    assert result["unsupported_claim_rate"] > 0
    assert result["contradiction_count"] > 0
    assert result["first_pass_ready"] is False


def test_evaluate_replay_documents_picks_combined_arm() -> None:
    """The provided offline corpus should rank the combined arm highest."""

    replay_cases = load_json_document(_fixture("replay_cases.json"), label="Replay cases")
    negative_controls = load_json_document(
        _fixture("replay_negative_controls.json"),
        label="Replay negative controls",
    )

    summary = evaluate_replay_documents(
        replay_cases=replay_cases,
        negative_controls=negative_controls,
    )

    assert summary["mode"] == "offline_replay_ablation"
    assert summary["network_budget"] == 0
    assert summary["winner_arm"] == "A3_combined"
    assert summary["promotion_ready"] is True
    assert summary["guardrails"]["known_good_false_positive_rate"] == 0.0
    assert summary["arms"]["A3_combined"]["correctness_pass_rate"] == 1.0
    assert summary["arms"]["A3_combined"]["first_pass_readiness_proxy"] == 1.0
    assert summary["arms"]["A0_control"]["unsupported_claim_rate"] > 0.0
    assert summary["arms"]["A0_control"]["contradiction_rate"] > 0.0


def test_resolve_output_path_rejects_paths_outside_results_dir(tmp_path: Path) -> None:
    """Result artifacts must stay under the local experiment results directory."""

    outside = tmp_path / "logic-philosophy-result.json"

    with pytest.raises(
        ValueError,
        match="--output must stay within artifacts/orchestration/experiments/results",
    ):
        _resolve_output_path(str(outside))


def test_main_writes_result_artifact(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """CLI should write replay summaries only inside the local results directory."""

    repo_root = tmp_path.resolve()
    results_dir = (repo_root / "artifacts" / "orchestration" / "experiments" / "results").resolve()
    monkeypatch.setattr(replay_eval, "REPO_ROOT", repo_root)
    monkeypatch.setattr(replay_eval, "RESULTS_DIR", results_dir)

    exit_code = main(
        [
            "--cases",
            str(_fixture("replay_cases.json")),
            "--negative-controls",
            str(_fixture("replay_negative_controls.json")),
            "--output",
            "logic-philosophy/result.json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    output_path = repo_root / payload["output"]
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["winner_arm"] == "A3_combined"
    assert written["promotion_ready"] is True
    assert written["guardrails"]["known_good_false_positive_rate"] == 0.0
