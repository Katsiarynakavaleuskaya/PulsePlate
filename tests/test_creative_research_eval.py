"""Tests for the creative research offline eval runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.orchestration.creative_research_eval as creative_research_eval
from scripts.orchestration.creative_research_eval_contract import evaluate_bundle

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "orchestration" / "creative_research"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_evaluate_bundle_triggers_negative_controls() -> None:
    """Duplicate, unsafe, and incomplete hypotheses must fail closed."""

    result = evaluate_bundle(_load_fixture("bundle_negative_controls.json"))
    by_id = {candidate["candidate_id"]: candidate for candidate in result["candidates"]}

    assert "duplicate_candidate" in by_id["dup-a"]["negative_controls_triggered"]
    assert by_id["dup-a"]["promotion_decision"] == "discard"
    assert "unsafe_wellness_language" in by_id["unsafe-cure"]["negative_controls_triggered"]
    assert by_id["unsafe-cure"]["scorecard"]["wellness_safety"] == 0
    assert by_id["missing-fields"]["output_class"] == "creative_ideation"
    assert by_id["missing-fields"]["promotion_decision"] == "discard"
    assert result["summary"]["discard"] == 4


def test_main_writes_result_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should write results only under the gitignored artifact tree."""

    artifact_dir = tmp_path / "artifacts" / "orchestration" / "creative_research" / "evals"
    input_path = tmp_path / "bundle.json"
    input_path.write_text(
        json.dumps(_load_fixture("bundle_valid.json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(creative_research_eval, "RESULT_ARTIFACT_DIR", artifact_dir)

    exit_code = creative_research_eval.main(["--input", str(input_path)])

    assert exit_code == 0
    stdout = capsys.readouterr().out.strip()
    output_path = Path(stdout)
    assert output_path.exists()
    assert output_path.parent == artifact_dir
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["bundle_id"] == "creative-research-valid"
    assert payload["summary"]["promote"] >= 1


def test_main_rejects_output_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Output paths must remain inside the dedicated artifacts subtree."""

    artifact_dir = tmp_path / "artifacts" / "orchestration" / "creative_research" / "evals"
    input_path = tmp_path / "bundle.json"
    input_path.write_text(
        json.dumps(_load_fixture("bundle_valid.json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(creative_research_eval, "RESULT_ARTIFACT_DIR", artifact_dir)

    exit_code = creative_research_eval.main(
        ["--input", str(input_path), "--output", "../escape.json"]
    )

    assert exit_code == 1
    assert "must stay within" in capsys.readouterr().err
