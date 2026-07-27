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

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
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
        (
            "phase2-pr-body-gates",
            [
                "--pr-number",
                "1005",
                "--body",
                "## Summary\nmirror",
                "--experiment-runner-evidence-mode",
                "advisory",
            ],
        ),
        (
            "merge-readiness-gate",
            ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"],
        ),
        (
            "current-head-checks",
            ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"],
        ),
        ("review-threads-disposition", ["--pr-number", "1005"]),
    ]


def test_local_mode_uses_artifact_first_phase2_args_when_body_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    assert exit_code == 0
    assert calls[0] == (
        "phase2-pr-body-gates",
        ["--pr-number", "1005", "--experiment-runner-evidence-mode", "advisory"],
    )


def test_required_experiment_runner_evidence_mode_forwards_to_phase2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        [
            "--pr-number",
            "1005",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--experiment-runner-evidence-mode",
            "required",
        ]
    )

    assert exit_code == 0
    assert calls[0] == (
        "phase2-pr-body-gates",
        ["--pr-number", "1005", "--experiment-runner-evidence-mode", "required"],
    )


def test_required_experiment_runner_evidence_mode_can_come_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setenv("PULSEPLATE_EXPERIMENT_RUNNER_EVIDENCE_MODE", "required")
    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    assert exit_code == 0
    assert calls[0] == (
        "phase2-pr-body-gates",
        ["--pr-number", "1005", "--experiment-runner-evidence-mode", "required"],
    )


def test_fetch_pr_body_uses_gh_auth_status_when_env_token_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        run_calls.append(argv)
        if argv[-2:] == ["auth", "status"]:
            return merge_ready.subprocess.CompletedProcess(argv, 0, stdout="logged in", stderr="")
        return merge_ready.subprocess.CompletedProcess(
            argv,
            0,
            stdout="## Discussion Thread Pass\n- [x] Discussion-thread pass completed\n",
            stderr="",
        )

    monkeypatch.setattr(merge_ready, "_github_cli_path", lambda: "/usr/local/bin/gh")
    monkeypatch.setattr(merge_ready.subprocess, "run", fake_run)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    body = merge_ready._fetch_pr_body(1129, "Katsiarynakavaleuskaya/PulsePlate")

    assert body.startswith("## Discussion Thread Pass")
    assert run_calls[0] == ["/usr/local/bin/gh", "auth", "status"]
    assert run_calls[1][:4] == ["/usr/local/bin/gh", "pr", "view", "1129"]


def test_local_mode_does_not_fetch_pr_body_when_body_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)
    monkeypatch.setattr(
        merge_ready,
        "_fetch_pr_body",
        lambda pr_number, repo: (_ for _ in ()).throw(RuntimeError("should not be called")),
    )

    exit_code = merge_ready.main(
        ["--pr-number", "1005", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    assert exit_code == 0
    assert calls[0] == (
        "phase2-pr-body-gates",
        ["--pr-number", "1005", "--experiment-runner-evidence-mode", "advisory"],
    )


def test_event_mode_passes_require_auth_only_to_disposition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 1007}}), encoding="utf-8")

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
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
        (
            "phase2-pr-body-gates",
            [
                "--event-path",
                str(event_path),
                "--experiment-runner-evidence-mode",
                "advisory",
            ],
        ),
        ("merge-readiness-gate", ["--event-path", str(event_path)]),
        ("current-head-checks", ["--event-path", str(event_path)]),
        ("review-threads-disposition", ["--pr-number", "1007", "--require-auth"]),
    ]


def test_event_mode_forwards_required_experiment_runner_evidence_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 1007}}), encoding="utf-8")

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        [
            "--event-path",
            str(event_path),
            "--experiment-runner-evidence-mode",
            "required",
        ]
    )

    assert exit_code == 0
    assert calls[0] == (
        "phase2-pr-body-gates",
        [
            "--event-path",
            str(event_path),
            "--experiment-runner-evidence-mode",
            "required",
        ],
    )


def test_pre_closeout_runs_only_mapping_gate_with_strict_tokens(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_gate(
        name: str, script_path: Path, extra_args: list[str]
    ) -> merge_ready.GateResult:
        calls.append((name, extra_args))
        return _ok_result(name, [str(script_path), *extra_args])

    monkeypatch.setenv("GH_TOKEN", "opaque-gh")
    monkeypatch.setenv("GITHUB_TOKEN", "opaque-github")
    monkeypatch.setattr(merge_ready, "_require_pre_closeout_auth", lambda: None)
    monkeypatch.setattr(merge_ready, "_run_gate", fake_run_gate)

    exit_code = merge_ready.main(
        [
            "--pr-number",
            "1005",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--require-auth",
            "--pre-closeout",
        ]
    )

    assert exit_code == 0
    assert calls == [
        (
            "pre-closeout-review-governance",
            [
                "--pr-number",
                "1005",
                "--repo",
                "Katsiarynakavaleuskaya/PulsePlate",
                "--pre-closeout",
            ],
        )
    ]
    output = capsys.readouterr().out
    assert "not merge-readiness evidence" in output
    assert "Blocking merge-ready bundle:" not in output


def test_pre_closeout_requires_require_auth() -> None:
    with pytest.raises(SystemExit):
        merge_ready.main(
            [
                "--pr-number",
                "1005",
                "--repo",
                "Katsiarynakavaleuskaya/PulsePlate",
                "--pre-closeout",
            ]
        )


@pytest.mark.parametrize("missing_token", ["GH_TOKEN", "GITHUB_TOKEN"])
def test_pre_closeout_requires_both_tokens(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_token: str,
) -> None:
    monkeypatch.setenv("GH_TOKEN", "opaque-gh")
    monkeypatch.setenv("GITHUB_TOKEN", "opaque-github")
    monkeypatch.delenv(missing_token)

    exit_code = merge_ready.main(
        [
            "--pr-number",
            "1005",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--require-auth",
            "--pre-closeout",
        ]
    )

    assert exit_code == 1
    assert "requires both GH_TOKEN and GITHUB_TOKEN" in capsys.readouterr().out


def test_event_pr_number_accepts_numeric_string(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": "1008"}}), encoding="utf-8")

    assert merge_ready._event_pr_number(str(event_path)) == 1008


def test_event_pr_number_returns_none_for_invalid_payload(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": "bad"}}), encoding="utf-8")

    assert merge_ready._event_pr_number(str(event_path)) is None


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
        "current-head-checks": merge_ready.GateResult(
            name="current-head-checks",
            argv=[],
            returncode=0,
            stdout="current head ok",
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
    assert "Blocking merge-ready bundle:" in captured.out
    assert "[FAIL] merge-readiness-gate (hard; lane=review-governance; blocking)" in captured.out
    assert "ERROR: orchestration merge-check failed." in captured.out
    assert "Failing gates: merge-readiness-gate" in captured.out
    assert "ERROR: unresolved review threads" in captured.out


def test_merge_ready_bundle_uses_declared_blocking_policy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        merge_ready,
        "GATE_POLICIES",
        {
            "phase2-pr-body-gates": merge_ready.GatePolicy(
                gate_class="hard", lane="pr-governance", blocking=True
            ),
            "merge-readiness-gate": merge_ready.GatePolicy(
                gate_class="hard", lane="review-governance", blocking=False
            ),
            "current-head-checks": merge_ready.GatePolicy(
                gate_class="hard", lane="required-checks", blocking=True
            ),
            "review-threads-disposition": merge_ready.GatePolicy(
                gate_class="hard", lane="review-proof", blocking=True
            ),
        },
    )
    monkeypatch.setattr(
        merge_ready,
        "BLOCKING_MERGE_READY_GATES",
        (
            "phase2-pr-body-gates",
            "merge-readiness-gate",
            "current-head-checks",
            "review-threads-disposition",
        ),
    )

    merge_ready._print_merge_ready_bundle(experiment_runner_evidence_mode="required")

    captured = capsys.readouterr()
    assert "phase2-pr-body-gates: class=hard, lane=pr-governance, blocking=yes" in captured.out
    assert "Experiment Runner Evidence mode=required" in captured.out
    assert "Lane Start Provenance is diagnostic dry-run" in captured.out
    assert "merge-readiness-gate: class=hard, lane=review-governance, blocking=no" in captured.out


def test_wrapper_fails_when_disposition_gate_skips_in_advisory_mode(
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
            returncode=0,
            stdout="merge ok",
            stderr="",
        ),
        "review-threads-disposition": merge_ready.GateResult(
            name="review-threads-disposition",
            argv=[],
            returncode=0,
            stdout="SKIP: no usable gh auth for advisory local run.",
            stderr="",
        ),
        "current-head-checks": merge_ready.GateResult(
            name="current-head-checks",
            argv=[],
            returncode=0,
            stdout="current head ok",
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
    assert "review-threads-disposition ran in advisory SKIP mode" in captured.out
    assert "Failing gates: review-threads-disposition" in captured.out


def test_disposition_gate_skipped_ignores_failed_skip_output() -> None:
    result = merge_ready.GateResult(
        name="review-threads-disposition",
        argv=[],
        returncode=1,
        stdout="SKIP: auth unavailable",
        stderr="",
    )

    assert merge_ready._disposition_gate_skipped(result) is False


def test_wrapper_requires_complete_local_context() -> None:
    with pytest.raises(SystemExit):
        merge_ready.main(["--pr-number", "1005"])


@pytest.mark.parametrize("guidance_path", ["AGENTS.md", "docs/ENGINEERING_LESSONS.md"])
def test_pre_closeout_guidance_includes_complete_local_context(guidance_path: str) -> None:
    guidance = (Path(__file__).resolve().parents[1] / guidance_path).read_text(encoding="utf-8")
    normalized = " ".join(guidance.split())

    assert (
        "python scripts/orchestration/check_merge_ready.py --pr-number <PR_NUMBER> "
        "--repo Katsiarynakavaleuskaya/PulsePlate --pre-closeout --require-auth" in normalized
    )


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


def test_run_gate_returns_failure_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_timeout: list[int] = []

    def raise_timeout(*args, **kwargs) -> None:
        observed_timeout.append(kwargs["timeout"])
        raise merge_ready.subprocess.TimeoutExpired(
            cmd=["python3", "scripts/orchestration/check_merge_ready.py"],
            timeout=kwargs["timeout"],
            output="partial output",
        )

    monkeypatch.setattr(merge_ready.subprocess, "run", raise_timeout)

    result = merge_ready._run_gate(
        "merge-readiness-gate",
        merge_ready.MERGE_GATE,
        ["--pr-number", "1007", "--repo", "Katsiarynakavaleuskaya/PulsePlate"],
    )

    assert result.returncode == 1
    assert result.stdout == "partial output"
    assert observed_timeout == [merge_ready.MERGE_GATE_TIMEOUT_SEC]
    assert f"Timed out after {merge_ready.MERGE_GATE_TIMEOUT_SEC}s" in result.stderr
    assert merge_ready.MERGE_GATE.name in result.stderr
