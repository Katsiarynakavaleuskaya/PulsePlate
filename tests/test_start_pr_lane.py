"""Regression tests for the repo-level PR lane starter."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = REPO_ROOT / "scripts/orchestration/start_pr_lane.sh"


def run_start(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
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
        env=env,
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
    assert "--allow-dirty-launcher" in result.stdout
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
    assert "Would run in worktree:" in result.stdout
    assert "scripts/orchestration/check_preflight.py" in result.stdout
    assert "scripts/orchestration/task_bootstrap.py" in result.stdout
    assert "Repo Python:" in result.stdout
    assert "avoid bare python3 -m pytest when .venv exists" in result.stdout
    assert "--path docs/dev/CODEX_SKILLS.md" in result.stdout
    assert "--path scripts/orchestration/start_pr_lane.sh" in result.stdout
    assert "--requested-agent agent-coordinator" in result.stdout
    assert "--requested-agent qa-engineer-agent" in result.stdout
    assert "Plugin/runtime checklist (operator-confirmed, non-blocking):" in result.stdout
    assert result.stdout.index("  - GitHub") < result.stdout.index("  - CodeRabbit")
    assert "Paste into Codex now:" in result.stdout
    assert "Dry run only: this command did not run preflight" in result.stdout
    assert "only ran analyze preflight" not in result.stdout
    assert "STOP: do not edit or write code/docs" in result.stdout
    assert "Start with agent-coordinator as the mandatory first role." in result.stdout
    assert "Branch: codex/example-pr-lane" in result.stdout
    assert "Worktree: worktrees/example-pr-lane" in result.stdout
    assert "Path scope: docs/dev/CODEX_SKILLS.md, scripts/orchestration/start_pr_lane.sh" in (
        result.stdout
    )
    assert "Skills are passive/discovery-only" in result.stdout
    assert "Premortem closure rule: every premortem finding must be fixed" in result.stdout
    assert "No finding may be ignored as advisory." in result.stdout
    assert "VENV_PYTHON" in result.stdout
    assert "$VENV_PYTHON -m pytest" in result.stdout
    assert "VENV_PYTHON=${VENV_PYTHON:-.venv/bin/python}" not in result.stdout
    assert "Open the PR non-draft by default" in result.stdout
    assert "Lane authority: check_preflight.py -> task_bootstrap.py -> agent-coordinator." in (
        result.stdout
    )
    assert "Host/Codex preflight is not authoritative lane provenance" in result.stdout
    assert "Experiment Runner evidence" in result.stdout
    assert "Experiment Runner: joins after coordinator bootstrap as oracle-only evidence." in (
        result.stdout
    )
    assert "After coordinator bootstrap, create oracle-only Experiment Runner evidence" in (
        result.stdout
    )
    assert "runner joins the lane and must not replace agent-coordinator" in result.stdout
    assert "Lane Start Provenance" in result.stdout
    assert "Starter: scripts/orchestration/start_pr_lane.sh` is supplemental" in result.stdout
    assert "cannot be used alone" in result.stdout
    assert "Not applicable: <reason>" in result.stdout
    assert (
        "Default PR review checklist: agent-coordinator, architecture-specialist, "
        "security-auditor, qa-engineer-agent, bug-hunter, dev-operator"
    ) in result.stdout
    assert "automatically start" not in result.stdout.lower()


def test_start_pr_lane_execute_path_prints_packet_prompt(tmp_path: Path) -> None:
    """The real post-task-bootstrap path should emit the packet-backed Codex prompt."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    packet_path = tmp_path / "packet.json"
    packet_payload = {
        "goal": "Start governed PR lane",
        "task_class": "pr_governance",
        "pr_phase": "pre_open",
        "candidate_paths": ["docs/dev/CODEX_SKILLS.md"],
        "recommended_skills": ["pulseplate-premortem-risk-review"],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "backend-engineer"},
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "secondary": [{"repo_agent_slug": "security-auditor"}],
            "advisory": [{"repo_agent_slug": "agent-coordinator"}],
        },
    }
    packet_path.write_text(json.dumps(packet_payload), encoding="utf-8")
    worktree_rel = f"worktrees/execute-path-test-{tmp_path.name}"

    git_stub = bin_dir / "git"
    git_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  check-ref-format) exit 0 ;;
  show-ref) exit 1 ;;
  status) exit 0 ;;
  fetch) exit 0 ;;
  rev-parse)
    if [[ "${3:-}" == "main^{commit}" ]]; then exit 1; fi
    echo abcdef1234567890
    exit 0
    ;;
  rev-list) printf '0\\t0\\n'; exit 0 ;;
  worktree) mkdir -p "$5"; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    git_stub.chmod(0o755)

    python_stub = bin_dir / "python3"
    real_python = sys.executable
    python_stub.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  *check_preflight.py)
    echo "PASS: stub preflight"
    exit 0
    ;;
  *task_bootstrap.py)
    printf '{{"output": "{packet_path}", "primary_agent": "agent-coordinator", "reviewer": "qa-engineer-agent", "recommended_skills": ["pulseplate-premortem-risk-review"]}}\\n'
    exit 0
    ;;
  *render_codex_start_prompt.py)
    shift
    exec {real_python!r} {str(REPO_ROOT / "scripts/orchestration/render_codex_start_prompt.py")!r} "$@"
    ;;
  *)
    exec {real_python!r} "$@"
    ;;
esac
""",
        encoding="utf-8",
    )
    python_stub.chmod(0o755)

    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env["VENV_PYTHON"] = str(python_stub)
    result = run_start(
        "--goal",
        "Start governed PR lane",
        "--task-class",
        "pr_governance",
        "--branch",
        "codex/execute-path-test",
        "--worktree",
        worktree_rel,
        "--path",
        "docs/dev/CODEX_SKILLS.md",
        "--allow-dirty-launcher",
        env=env,
    )
    shutil.rmtree(REPO_ROOT / worktree_rel, ignore_errors=True)

    assert result.returncode == 0, result.stderr
    assert "Authoritative bootstrap already ran" in result.stdout
    assert f"Task packet: {packet_path}" in result.stdout
    assert "Role order: agent-coordinator, backend-engineer, qa-engineer-agent" in result.stdout
    assert "Passive skills from packet: pulseplate-premortem-risk-review" in result.stdout
    assert "VENV_PYTHON" in result.stdout
    assert "$VENV_PYTHON -m pytest" in result.stdout
    assert "VENV_PYTHON=${VENV_PYTHON:-.venv/bin/python}" not in result.stdout
    assert "Open the PR non-draft by default" in result.stdout
    assert "Experiment Runner evidence" in result.stdout
    assert "Experiment Runner joins after coordinator bootstrap" in result.stdout
    assert "Lane start provenance" in result.stdout
    assert "did not run authoritative task_bootstrap.py" not in result.stdout
    assert "auto-start" not in result.stdout.lower()


def test_start_pr_lane_dry_run_uses_default_plugin_checklist() -> None:
    """The default plugin checklist should be stable and non-blocking."""

    result = run_start(*_required_args(), "--dry-run")

    assert result.returncode == 0, result.stderr
    default_plugins = (
        "GitHub",
        "CodeRabbit",
        "Codex Security",
        "Browser",
        "Chrome",
        "Computer Use",
        "Hugging Face",
        "Life Science Research",
    )
    for plugin in default_plugins:
        assert f"  - {plugin}" in result.stdout
    assert result.stdout.index("  - GitHub") < result.stdout.index("  - CodeRabbit")
    assert "PR open mode: non-draft by default" in result.stdout


def test_start_pr_lane_allows_dirty_launcher_for_synced_origin_main_lane(
    tmp_path: Path,
) -> None:
    """A dirty launcher checkout requires an explicit isolated origin/main exception."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "goal": "Start governed PR lane",
                "task_class": "pr_governance",
                "pr_phase": "pre_open",
                "candidate_paths": ["scripts/orchestration/start_pr_lane.sh"],
                "recommended_skills": [],
                "native_subagent_bridge": {
                    "primary": {"repo_agent_slug": "agent-coordinator"},
                    "reviewer": {"repo_agent_slug": "architecture-specialist"},
                },
            }
        ),
        encoding="utf-8",
    )
    worktree_rel = f"worktrees/dirty-origin-main-test-{tmp_path.name}"

    git_stub = bin_dir / "git"
    git_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  check-ref-format) exit 0 ;;
  show-ref) exit 1 ;;
  fetch) exit 0 ;;
  rev-parse) echo abcdef1234567890; exit 0 ;;
  rev-list) printf '0\\t0\\n'; exit 0 ;;
  status) printf ' M docs/foreign.md\\n'; exit 0 ;;
  worktree) mkdir -p "$5"; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    git_stub.chmod(0o755)

    python_stub = bin_dir / "python3"
    real_python = sys.executable
    python_stub.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  *check_preflight.py)
    echo "PASS: stub preflight"
    exit 0
    ;;
  *task_bootstrap.py)
    printf '{{"output": "{packet_path}", "primary_agent": "agent-coordinator", "reviewer": "architecture-specialist", "recommended_skills": []}}\\n'
    exit 0
    ;;
  *render_codex_start_prompt.py)
    shift
    exec {real_python!r} {str(REPO_ROOT / "scripts/orchestration/render_codex_start_prompt.py")!r} "$@"
    ;;
  *)
    exec {real_python!r} "$@"
    ;;
esac
""",
        encoding="utf-8",
    )
    python_stub.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "VENV_PYTHON": str(python_stub),
    }
    result = run_start(
        "--goal",
        "Start governed PR lane",
        "--task-class",
        "pr_governance",
        "--branch",
        "codex/dirty-origin-main-test",
        "--worktree",
        worktree_rel,
        "--path",
        "scripts/orchestration/start_pr_lane.sh",
        "--allow-dirty-launcher",
        env=env,
    )
    shutil.rmtree(REPO_ROOT / worktree_rel, ignore_errors=True)

    assert result.returncode == 0, result.stderr
    assert "Authoritative bootstrap already ran" in result.stdout


def test_start_pr_lane_rejects_dirty_launcher_without_explicit_exception(
    tmp_path: Path,
) -> None:
    """Dirty launcher state remains fail-closed unless the operator opts in."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_stub = bin_dir / "git"
    git_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  check-ref-format) exit 0 ;;
  show-ref) exit 1 ;;
  fetch) exit 0 ;;
  rev-parse) echo abcdef1234567890; exit 0 ;;
  rev-list) printf '0\\t0\\n'; exit 0 ;;
  status) printf ' M docs/foreign.md\\n'; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    git_stub.chmod(0o755)

    python_stub = bin_dir / "python3"
    python_stub.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    python_stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    result = run_start(*_required_args(), env=env)

    assert result.returncode == 1
    assert "pass --allow-dirty-launcher for an isolated origin/main lane" in result.stderr


def test_start_pr_lane_rejects_dirty_launcher_exception_for_non_origin_main_base(
    tmp_path: Path,
) -> None:
    """The dirty-launcher exception is scoped only to isolated origin/main lanes."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_stub = bin_dir / "git"
    git_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  check-ref-format) exit 0 ;;
  show-ref) exit 1 ;;
  fetch) exit 0 ;;
  rev-parse) echo abcdef1234567890; exit 0 ;;
  status) printf ' M docs/foreign.md\\n'; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    git_stub.chmod(0o755)
    python_stub = bin_dir / "python3"
    python_stub.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    python_stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    result = run_start(
        *_required_args(),
        "--base",
        "origin/release",
        "--allow-dirty-launcher",
        env=env,
    )

    assert result.returncode == 1
    assert "--allow-dirty-launcher is only allowed with --base origin/main" in result.stderr


def test_start_pr_lane_rejects_dirty_launcher_exception_for_non_origin_main_dry_run() -> None:
    """Dry-run must reject dirty-launcher options that real execution rejects."""

    result = run_start(
        *_required_args(),
        "--dry-run",
        "--base",
        "origin/release",
        "--allow-dirty-launcher",
    )

    assert result.returncode == 1
    assert "--allow-dirty-launcher is only allowed with --base origin/main" in result.stderr


def test_start_pr_lane_dirty_launcher_exception_still_requires_synced_main(
    tmp_path: Path,
) -> None:
    """The dirty-launcher flag must not bypass the main...origin/main sync guard."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_stub = bin_dir / "git"
    git_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  check-ref-format) exit 0 ;;
  show-ref) exit 1 ;;
  fetch) exit 0 ;;
  rev-parse) echo abcdef1234567890; exit 0 ;;
  rev-list) printf '0\\t1\\n'; exit 0 ;;
  status) printf ' M docs/foreign.md\\n'; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    git_stub.chmod(0o755)
    python_stub = bin_dir / "python3"
    python_stub.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    python_stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    result = run_start(*_required_args(), "--allow-dirty-launcher", env=env)

    assert result.returncode == 1
    assert "local main must be synced with origin/main" in result.stderr


def test_start_pr_lane_rejects_relative_venv_python() -> None:
    """Governance launcher must not execute cwd-controlled relative Python paths."""

    env = {**os.environ, "VENV_PYTHON": ".venv/bin/python"}

    result = run_start(*_required_args(), "--dry-run", env=env)

    assert result.returncode == 1
    assert "VENV_PYTHON must be an absolute executable path" in result.stderr


def test_start_pr_lane_rejects_local_only_scope_paths() -> None:
    """Task scope must not include local-only artifacts or worktrees."""

    for blocked_path in (
        "artifacts/agent_runs/session.json",
        "artifacts/orchestration/task_packets/demo.json",
        "artifacts/security_lab/report.json",
        ".venv/bin/python",
        "worktrees/other-lane",
        ".DS_Store",
        ".coverage",
        "coverage.xml",
    ):
        result = run_start(*_required_args(), "--path", blocked_path, "--dry-run")

        assert result.returncode == 2
        assert "local-only artifact/cache surface" in result.stderr
        assert "PulsePlate PR lane start" not in result.stdout


def test_start_pr_lane_rejects_parent_traversal_scope_paths() -> None:
    """Task scope paths must stay inside tracked repo surfaces."""

    blocked_path_errors = {
        "../secrets.json": "--path must stay inside the repo without parent traversal",
        "../../outside-repo": "--path must stay inside the repo without parent traversal",
        "/tmp/session.json": "--path must be repo-relative or under repo root",
    }

    for blocked_path, expected_error in blocked_path_errors.items():
        result = run_start(*_required_args(), "--path", blocked_path, "--dry-run")

        assert result.returncode == 2
        assert expected_error in result.stderr
        assert "PulsePlate PR lane start" not in result.stdout


def test_start_pr_lane_rejects_bad_worktree_paths() -> None:
    """The lane worktree itself must be inside repo worktrees/."""

    blocked_worktree_errors = {
        "tmp/example-pr-lane": "--worktree must be under worktrees/",
        "../example-pr-lane": "--worktree must stay inside the repo without parent traversal",
        "../../outside-repo/example-pr-lane": "--worktree must stay inside the repo without parent traversal",
        "/tmp/example-pr-lane": "--worktree must be repo-relative or under repo root",
    }

    for blocked_worktree, expected_error in blocked_worktree_errors.items():
        result = run_start(
            "--goal",
            "Start governed PR lane",
            "--task-class",
            "pr_governance",
            "--branch",
            "codex/example-pr-lane",
            "--worktree",
            blocked_worktree,
            "--dry-run",
        )

        assert result.returncode == 2
        assert expected_error in result.stderr


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


def test_start_pr_lane_rejects_git_invalid_branch_names() -> None:
    """Branch validation should match git refname rules."""

    result = run_start(
        "--goal",
        "Start governed PR lane",
        "--task-class",
        "pr_governance",
        "--branch",
        "bad branch name",
        "--worktree",
        "worktrees/example-pr-lane",
        "--dry-run",
    )

    assert result.returncode == 2
    assert "--branch must be a valid branch name" in result.stderr
