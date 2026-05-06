"""Regression tests for the repo-level PR lane starter."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = REPO_ROOT / "scripts/orchestration/start_pr_lane.sh"


def run_start(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the PR lane starter with captured output."""

    bash_path = shutil.which("bash")
    if bash_path is None:
        raise RuntimeError("bash executable not found on PATH")

    return subprocess.run(
        [bash_path, str(START_SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


def _required_args() -> tuple[str, ...]:
    return (
        "--goal",
        "Start governed PR lane",
        "--task-class",
        "pr_governance",
        "--branch",
        "codex/example-pr-lane",
        "--worktree",
        "worktrees/example-pr-lane",
    )


def test_start_pr_lane_help_is_non_mutating() -> None:
    """Help should not run git or bootstrap commands."""

    result = run_start("--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--branch <name>" in result.stdout
    assert "PulsePlate PR lane start" not in result.stdout


def test_start_pr_lane_requires_core_lane_fields() -> None:
    """Goal, class, branch, and worktree are all required before mutation."""

    required_error_by_args = {
        "--goal is required": (),
        "--task-class is required": ("--goal", "Start governed PR lane"),
        "--branch is required": (
            "--goal",
            "Start governed PR lane",
            "--task-class",
            "pr_governance",
        ),
        "--worktree is required": (
            "--goal",
            "Start governed PR lane",
            "--task-class",
            "pr_governance",
            "--branch",
            "codex/example-pr-lane",
        ),
    }

    for expected_error, args in required_error_by_args.items():
        result = run_start(*args)

        assert result.returncode == 2
        assert expected_error in result.stderr
        assert "PulsePlate PR lane start" not in result.stdout


def test_start_pr_lane_dry_run_prints_stable_commands_and_plugins() -> None:
    """Dry-run should expose the full start recipe without mutating git state."""

    result = run_start(
        *_required_args(),
        "--path",
        "docs/dev/CODEX_SKILLS.md",
        "--path",
        "scripts/orchestration/start_pr_lane.sh",
        "--requested-agent",
        "qa-engineer-agent",
        "--plugin",
        "GitHub",
        "--plugin",
        "CodeRabbit",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert "DRY RUN: no git worktree, preflight, or bootstrap commands were executed." in (
        result.stdout
    )
    assert "Would run: git worktree add -b codex/example-pr-lane" in result.stdout
    assert "Would run in worktree: python3 scripts/orchestration/check_preflight.py" in (
        result.stdout
    )
    assert "Would run in worktree: python3 scripts/orchestration/task_bootstrap.py" in (
        result.stdout
    )
    assert "--path docs/dev/CODEX_SKILLS.md" in result.stdout
    assert "--path scripts/orchestration/start_pr_lane.sh" in result.stdout
    assert "--requested-agent agent-coordinator" in result.stdout
    assert "--requested-agent qa-engineer-agent" in result.stdout
    assert "Plugin/runtime checklist (operator-confirmed, non-blocking):" in result.stdout
    assert result.stdout.index("  - GitHub") < result.stdout.index("  - CodeRabbit")


def test_start_pr_lane_dry_run_uses_default_plugin_checklist() -> None:
    """The default plugin checklist should be stable and non-blocking."""

    result = run_start(*_required_args(), "--dry-run")

    assert result.returncode == 0, result.stderr
    default_plugins = (
        "Browser Use",
        "Computer Use",
        "GitHub",
        "Hugging Face",
        "Life Science Research",
        "Plugin Eval",
        "CodeRabbit",
    )
    for plugin in default_plugins:
        assert f"  - {plugin}" in result.stdout
    assert result.stdout.index("  - Browser Use") < result.stdout.index("  - CodeRabbit")


def test_start_pr_lane_rejects_local_only_scope_paths() -> None:
    """Task scope must not include local-only artifacts or worktrees."""

    for blocked_path in (
        "artifacts/agent_runs/session.json",
        "artifacts/orchestration/task_packets/demo.json",
        "artifacts/security_lab/report.json",
        ".venv/bin/python",
        "worktrees/other-lane",
    ):
        result = run_start(*_required_args(), "--path", blocked_path, "--dry-run")

        assert result.returncode == 2
        assert "local-only artifact/cache surface" in result.stderr
        assert "PulsePlate PR lane start" not in result.stdout


def test_start_pr_lane_rejects_bad_worktree_paths() -> None:
    """The lane worktree itself must be inside repo worktrees/."""

    result = run_start(
        "--goal",
        "Start governed PR lane",
        "--task-class",
        "pr_governance",
        "--branch",
        "codex/example-pr-lane",
        "--worktree",
        "tmp/example-pr-lane",
        "--dry-run",
    )

    assert result.returncode == 2
    assert "--worktree must be under worktrees/" in result.stderr


def test_start_pr_lane_rejects_branch_ref_like_names() -> None:
    """The branch must be a new local branch name, not a remote or ref expression."""

    result = run_start(
        "--goal",
        "Start governed PR lane",
        "--task-class",
        "pr_governance",
        "--branch",
        "origin/main",
        "--worktree",
        "worktrees/example-pr-lane",
        "--dry-run",
    )

    assert result.returncode == 2
    assert "--branch must be a new local branch name" in result.stderr
