"""Tests for canonical orchestration merge-check wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration import check_merge_ready as merge_ready


def _ok_result(name: str, argv: list[str]) -> merge_ready.GateResult:
    return merge_ready.GateResult(
        name=name,
        argv=argv,
        returncode=0,
        stdout=f"{name}: ok",
        stderr="",
    )


def test_local_mode_runs_all_gates_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_gate(name: str, script_path, extra_args: list[str]) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        [
            "--pr-number",
            "1005",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--body",
            "## Summary\nmirror",
        ]
    )

    assert exit_code == 0
    assert calls == [
        ("phase2-pr-body-gates", ["--pr-number", "1005", "--body", "## Summary\nmirror"]),
        (
            "merge-readiness-gate",
            ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"],
        ),
        ("review-threads-disposition", ["--pr-number", "1005"]),
    ]


def test_event_mode_passes_require_auth_only_to_disposition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 1007}}), encoding="utf-8")

    def fake_run_gate(name: str, script_path, extra_args: list[str]) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        [
            "--event-path",
            str(event_path),
            "--require-auth",
        ]
    )

    assert exit_code == 0
    assert calls == [
        ("phase2-pr-body-gates", ["--event-path", str(event_path)]),
        ("merge-readiness-gate", ["--event-path", str(event_path)]),
        ("review-threads-disposition", ["--pr-number", "1007", "--require-auth"]),
    ]


def test_wrapper_surfaces_failing_gate_names(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    results = {
        "phase2-pr-body-gates": merge_ready.GateResult(
            name="phase2-pr-body-gates",
            argv=[],
            returncode=0,
            stdout="phase2 ok",
            stderr="",
        ),
        "merge-readiness-gate": merge_ready.GateResult(
            name="merge-readiness-gate",
            argv=[],
            returncode=1,
            stdout="ERROR: unresolved review threads",
            stderr="",
        ),
        "review-threads-disposition": merge_ready.GateResult(
            name="review-threads-disposition",
            argv=[],
            returncode=0,
            stdout="disposition ok",
            stderr="",
        ),
    }

    monkeypatch.setattr(
        merge_ready,
        "_run_gate",
        lambda name, script_path, extra_args: results[name],
    )

    exit_code = merge_ready.main(
        ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: orchestration merge-check failed." in captured.out
    assert "Failing gates: merge-readiness-gate" in captured.out
    assert "ERROR: unresolved review threads" in captured.out


def test_wrapper_requires_complete_local_context() -> None:
    with pytest.raises(SystemExit):
        merge_ready.main(["--pr-number", "1005"])


def test_wrapper_rejects_mixed_event_and_local_modes() -> None:
    with pytest.raises(SystemExit):
        merge_ready.main(
            [
                "--event-path",
                "/tmp/github-event.json",
                "--pr-number",
                "1005",
                "--repo",
                "Katsiarynakavaleuskaya/PulsePlate",
            ]
        )
