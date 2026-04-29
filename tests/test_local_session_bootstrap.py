"""Regression tests for the opt-in local session bootstrap bridge."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts/orchestration/local_session_bootstrap.sh"


def run_bootstrap(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the shell bridge without mutating the repo checkout."""

    return subprocess.run(
        ["bash", str(BOOTSTRAP_SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_local_session_bootstrap_help_is_non_mutating() -> None:
    """Help should not run preflight or create bootstrap artifacts."""

    result = run_bootstrap("--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--goal <text>" in result.stdout
    assert "PASS:" not in result.stdout


def test_local_session_bootstrap_prints_exact_selected_bootstrap_command(
    tmp_path: Path,
) -> None:
    """Supplying a goal/class should print an executable task_bootstrap command."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        "--path",
        "scripts/orchestration/local_session_bootstrap.sh",
        "--pr-phase",
        "pre_open",
        "--requested-agent",
        "qa-engineer-agent",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: preflight passed (analyze)" in result.stdout
    assert "Generate the selected task packet:" in result.stdout
    assert f"python3 {BOOTSTRAP_SCRIPT.parent / 'task_bootstrap.py'} \\" in result.stdout
    assert "--goal B0 \\" in result.stdout
    assert "--task-class Orchestration \\" in result.stdout
    assert "--pr-phase pre_open \\" in result.stdout
    assert "--path scripts/orchestration/local_session_bootstrap.sh \\" in result.stdout
    assert "--requested-agent qa-engineer-agent" in result.stdout
    automation_matrix_line = "Automation matrix: docs/orchestration/AUTOMATION_READINESS_MATRIX.md"
    assert automation_matrix_line in result.stdout


def test_local_session_bootstrap_requires_goal_and_task_class_together() -> None:
    """Any concrete bootstrap option should fail closed without goal/class."""

    result = run_bootstrap("--path", "docs/dev/CODEX_SKILLS.md")

    assert result.returncode == 2
    assert "--goal and --task-class are required" in result.stderr


def test_local_session_bootstrap_rejects_invalid_pr_phase() -> None:
    """The printed bootstrap command must not carry an unknown PR phase."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        "--pr-phase",
        "invalid",
    )

    assert result.returncode == 2
    assert "--pr-phase must be one of" in result.stderr


def test_local_session_bootstrap_rejects_unknown_args() -> None:
    """Unknown flags should fail before running preflight."""

    result = run_bootstrap("--nope")

    assert result.returncode == 2
    assert "unknown arg: --nope" in result.stderr
    assert "PASS:" not in result.stdout


def test_local_session_bootstrap_rejects_local_only_scope_paths() -> None:
    """Local-only artifact and worktree paths must not become task scope."""

    for blocked_path in (
        "artifacts/orchestration",
        "artifacts/orchestration/task_packets/demo.json",
        "worktrees",
    ):
        result = run_bootstrap(
            "--goal",
            "B0",
            "--task-class",
            "Orchestration",
            "--path",
            blocked_path,
        )

        assert result.returncode == 2
        assert "local-only artifact/cache surface" in result.stderr
        assert "PASS:" not in result.stdout


def test_local_session_bootstrap_rejects_paths_outside_repo() -> None:
    """Absolute paths outside the repo must not be printed as bootstrap scope."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        "--path",
        "/tmp/outside-repo.txt",
    )

    assert result.returncode == 2
    assert "must be repo-relative or under repo root" in result.stderr
    assert "PASS:" not in result.stdout
