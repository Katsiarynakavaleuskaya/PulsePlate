"""Tests for the FitChef judgment offline eval runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.orchestration.judgment_eval as judgment_eval

FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "orchestration" / "fitchef_judgment_replay"
)


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_main_writes_result_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should write results only under the dedicated judgment artifact tree."""

    artifact_dir = tmp_path / "artifacts" / "orchestration" / "judgment" / "evals"
    input_path = tmp_path / "bundle.json"
    input_path.write_text(
        json.dumps(_load_fixture("replay_cases.json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(judgment_eval, "RESULT_ARTIFACT_DIR", artifact_dir)

    exit_code = judgment_eval.main(["--input", str(input_path)])

    assert exit_code == 0
    output_path = Path(capsys.readouterr().out.strip())
    assert output_path.exists()
    assert output_path.parent == artifact_dir
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["bundle_id"] == "fitchef_judgment_replay_primary"
    assert payload["scenario_family"] == "fitchef_primary_scenarios"
    assert payload["summary"]["promote"] >= 1


def test_main_rejects_output_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Output paths must remain inside the judgment artifact subtree."""

    artifact_dir = tmp_path / "artifacts" / "orchestration" / "judgment" / "evals"
    input_path = tmp_path / "bundle.json"
    input_path.write_text(
        json.dumps(_load_fixture("replay_cases.json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(judgment_eval, "RESULT_ARTIFACT_DIR", artifact_dir)

    exit_code = judgment_eval.main(["--input", str(input_path), "--output", "../escape.json"])

    assert exit_code == 1
    assert "must stay within" in capsys.readouterr().err
