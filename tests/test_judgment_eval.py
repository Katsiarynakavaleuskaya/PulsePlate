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


@pytest.mark.parametrize(
    ("payload", "expected_stderr_fragment"),
    [
        ("{ this is not valid json", "Unable to load FitChef judgment replay JSON"),
        ('["valid-json-but-not-object"]', "must be a JSON object"),
        ('"primitive-json-string"', "must be a JSON object"),
    ],
)
def test_main_rejects_invalid_or_non_object_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    payload: str,
    expected_stderr_fragment: str,
) -> None:
    """CLI should fail closed for malformed or non-object replay inputs."""

    input_path = tmp_path / "bundle.json"
    input_path.write_text(payload, encoding="utf-8")

    exit_code = judgment_eval.main(["--input", str(input_path)])

    assert exit_code == 1
    assert expected_stderr_fragment in capsys.readouterr().err


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


def test_main_rejects_unknown_summary_decision() -> None:
    """Summary builder must fail fast on contract drift."""

    with pytest.raises(ValueError, match="Unexpected decision"):
        judgment_eval._build_summary([{"decision": "ship", "hard_fail_reasons": []}])


def test_main_returns_clean_error_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Filesystem write failures should return exit code 1 without a traceback."""

    artifact_dir = tmp_path / "artifacts" / "orchestration" / "judgment" / "evals"
    input_path = tmp_path / "bundle.json"
    input_path.write_text(
        json.dumps(_load_fixture("replay_cases.json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(judgment_eval, "RESULT_ARTIFACT_DIR", artifact_dir)

    def _raise_write_failure(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _raise_write_failure)

    exit_code = judgment_eval.main(["--input", str(input_path)])

    assert exit_code == 1
    assert "disk full" in capsys.readouterr().err
