"""Regression tests for the opt-in local session bootstrap bridge."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts/orchestration/local_session_bootstrap.sh"
PREFLIGHT_SUCCESS_MARKER = "OK: preflight passed (analyze)"


def run_bootstrap(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the shell bridge without mutating the repo checkout."""

    bash_path = shutil.which("bash")
    if bash_path is None:
        raise RuntimeError("bash executable not found on PATH")

    return subprocess.run(
        [bash_path, str(BOOTSTRAP_SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
        env=env,
    )


def test_local_session_bootstrap_help_is_non_mutating() -> None:
    """Help should not run preflight or create bootstrap artifacts."""

    result = run_bootstrap("--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--goal <text>" in result.stdout
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


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
    assert "Repo Python:" in result.stdout
    assert "avoid bare python3 -m pytest when .venv exists" in result.stdout
    assert "Generate the selected task packet:" in result.stdout
    assert f"{BOOTSTRAP_SCRIPT.parent / 'task_bootstrap.py'} \\" in result.stdout
    assert "--goal B0 \\" in result.stdout
    assert "--task-class Orchestration \\" in result.stdout
    assert "--pr-phase pre_open \\" in result.stdout
    assert "--path scripts/orchestration/local_session_bootstrap.sh \\" in result.stdout
    assert "--requested-agent qa-engineer-agent" in result.stdout
    automation_matrix_line = "Automation matrix: docs/orchestration/AUTOMATION_READINESS_MATRIX.md"
    assert automation_matrix_line in result.stdout
    assert "Paste into Codex now:" in result.stdout
    assert "STOP: do not edit or write code/docs" in result.stdout
    assert "Start with agent-coordinator as the mandatory first role." in result.stdout
    assert "only ran analyze preflight" in result.stdout
    assert "did not run authoritative task_bootstrap.py" in result.stdout
    assert "did not create a task packet" in result.stdout
    assert "Path scope: scripts/orchestration/local_session_bootstrap.sh" in result.stdout
    assert "Requested role order seed: agent-coordinator, qa-engineer-agent" in result.stdout
    assert "Skills are passive/discovery-only" in result.stdout
    assert "Premortem closure rule: every premortem finding must be fixed" in result.stdout
    assert "No finding may be ignored as advisory." in result.stdout
    assert "VENV_PYTHON" in result.stdout
    assert "$VENV_PYTHON -m pytest" in result.stdout
    assert "$VENV_PYTHON scripts/orchestration/experiment_runner.py" in result.stdout
    assert "artifact load/write failures are infra blockers" in result.stdout
    assert "automatically start" not in result.stdout.lower()


def test_local_session_bootstrap_legacy_no_arg_prompt_is_explicit(tmp_path: Path) -> None:
    """No-arg helper mode should still print a Codex-ready non-authoritative prompt."""

    result = run_bootstrap(cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Generate a task packet (minimal example):" in result.stdout
    assert "Paste into Codex now:" in result.stdout
    assert "only ran analyze preflight" in result.stdout
    assert "did not run authoritative task_bootstrap.py" in result.stdout
    assert "did not create a task packet" in result.stdout
    assert "Goal: <set --goal>" in result.stdout
    assert "Task class: <set --task-class>" in result.stdout
    assert "Requested role order seed: agent-coordinator" in result.stdout
    assert "VENV_PYTHON" in result.stdout
    assert "$VENV_PYTHON -m pytest" in result.stdout
    assert "$VENV_PYTHON scripts/orchestration/experiment_runner.py" in result.stdout
    assert "artifact load/write failures are infra blockers" in result.stdout
    assert "automatically start" not in result.stdout.lower()
    assert "auto-start" not in result.stdout.lower()


def test_local_session_bootstrap_forwards_repeatable_flags_in_order(
    tmp_path: Path,
) -> None:
    """Repeated path and agent flags should all appear in first-seen order."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        "--path",
        "docs/dev/CODEX_SKILLS.md",
        "--path",
        "scripts/orchestration/local_session_bootstrap.sh",
        "--requested-agent",
        "qa-engineer-agent",
        "--requested-agent",
        "bug-hunter",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    command_block = result.stdout.partition("Generate the selected task packet:")[2]
    assert command_block
    first_path = "--path docs/dev/CODEX_SKILLS.md"
    second_path = "--path scripts/orchestration/local_session_bootstrap.sh"
    first_agent = "--requested-agent qa-engineer-agent"
    second_agent = "--requested-agent bug-hunter"

    assert first_path in command_block
    assert second_path in command_block
    assert command_block.index(first_path) < command_block.index(second_path)
    assert first_agent in command_block
    assert second_agent in command_block
    assert command_block.index(first_agent) < command_block.index(second_agent)
    assert "Requested role order seed: agent-coordinator, qa-engineer-agent, bug-hunter" in (
        command_block
    )


def test_local_session_bootstrap_requires_goal_and_task_class_together() -> None:
    """Any concrete bootstrap option should fail closed without goal/class."""

    result = run_bootstrap("--path", "docs/dev/CODEX_SKILLS.md")

    assert result.returncode == 2
    assert "--goal and --task-class are required" in result.stderr
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


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
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


def test_local_session_bootstrap_rejects_unknown_args() -> None:
    """Unknown flags should fail before running preflight."""

    result = run_bootstrap("--nope")

    assert result.returncode == 2
    assert "unknown arg: --nope" in result.stderr
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


def test_local_session_bootstrap_rejects_local_only_scope_paths() -> None:
    """Local-only artifact and worktree paths must not become task scope."""

    for blocked_path in (
        "artifacts/agent_runs",
        "artifacts/agent_runs/session.json",
        "artifacts/orchestration",
        "artifacts/orchestration/task_packets/demo.json",
        "artifacts/security_lab",
        "artifacts/security_lab/report.json",
        ".venv",
        ".venv/bin/python",
        "worktrees",
        "worktrees/other-lane",
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
        assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


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
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


def test_local_session_bootstrap_rejects_relative_venv_python() -> None:
    """The local bridge must not execute cwd-controlled relative Python paths."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        env={**os.environ, "VENV_PYTHON": ".venv/bin/python"},
    )

    assert result.returncode == 1
    assert "VENV_PYTHON must be an absolute executable path" in result.stderr
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


def test_local_session_bootstrap_accepts_absolute_venv_python() -> None:
    """Absolute VENV_PYTHON is accepted and becomes the printed local test path."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        env={**os.environ, "VENV_PYTHON": sys.executable},
    )

    assert result.returncode == 0, result.stderr
    assert f"Repo Python: {sys.executable}" in result.stdout
    assert "interpreter path printed by the starter/bootstrap scripts" in result.stdout
    assert "$VENV_PYTHON -m pytest" in result.stdout
    assert "$VENV_PYTHON scripts/orchestration/experiment_runner.py" in result.stdout
    assert "$PWD/.venv/bin/python` in isolated worktrees" in result.stdout
    assert "VENV_PYTHON=${VENV_PYTHON:-.venv/bin/python}" not in result.stdout


def test_local_session_bootstrap_rejects_parent_traversal_at_path_end() -> None:
    """Parent traversal must fail even when it appears as the final segment."""

    result = run_bootstrap(
        "--goal",
        "B0",
        "--task-class",
        "Orchestration",
        "--path",
        "docs/..",
    )

    assert result.returncode == 2
    assert "must stay inside the repo without parent traversal" in result.stderr
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout
