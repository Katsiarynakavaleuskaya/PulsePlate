"""Regression tests for the opt-in local session bootstrap bridge."""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.orchestration import review_invariant_family_relations as relations

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts/orchestration/local_session_bootstrap.sh"
PREFLIGHT_SUCCESS_MARKER = "OK: preflight passed (analyze)"
L1_FLAG = "--review-invariant-family-relations-input"
L1_ROOT = "artifacts/orchestration/review_invariant_family_relations"


def _disposable_env() -> dict[str, str]:
    """Do not let parent Git hooks redirect a disposable child into the real repo."""

    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


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


def _disposable_repo(tmp_path: Path) -> Path:
    """Copy only bootstrap dependencies into an isolated Git repository."""

    repo = tmp_path / "repo"
    repo.mkdir()
    for directory in ("scripts", "core", "docs", ".cursor", ".agents"):
        shutil.copytree(
            REPO_ROOT / directory,
            repo / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    (repo / "tests").mkdir()
    shutil.copy2(REPO_ROOT / "tests/AGENTS.md", repo / "tests/AGENTS.md")
    for filename in ("AGENTS.md", "RUNBOOK_AGENT.md", ".gitignore"):
        shutil.copy2(REPO_ROOT / filename, repo / filename)
    git = shutil.which("git")
    assert git is not None
    initialized = subprocess.run(
        [git, "init", "-q", str(repo)],
        env=_disposable_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert initialized.returncode == 0, initialized.stderr
    return repo


def _snapshot(*, repeated: bool) -> dict[str, object]:
    return {
        "schema_version": relations.SNAPSHOT_SCHEMA_VERSION,
        "universe_finding_ids": ["finding_a", "finding_b"],
        "families": [
            {
                "family_id": "family_alpha",
                "finding_ids": ["finding_a", "finding_b"] if repeated else ["finding_a"],
            }
        ],
        **{field: False for field in relations.AUTHORITY_FIELDS},
    }


def _run_command(repo: Path, command: str) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    assert bash is not None
    env = dict(_disposable_env(), VENV_PYTHON=sys.executable)
    return subprocess.run(
        [bash, "-c", command],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _printed_command(output: str) -> str:
    return output.split("Generate the selected task packet:\n", 1)[1].split("\n\n", 1)[0]


def test_local_session_bootstrap_help_is_non_mutating() -> None:
    """Help should not run preflight or create bootstrap artifacts."""

    result = run_bootstrap("--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--goal <text>" in result.stdout
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


def test_local_session_bootstrap_short_help_is_non_mutating() -> None:
    result = run_bootstrap("-h")
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ("--goal", "G", "--help"),
        ("--goal", L1_FLAG, "--help"),
    ],
)
def test_input_free_legacy_help_anywhere_remains_available(arguments: tuple[str, ...]) -> None:
    result = run_bootstrap(*arguments)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


def test_l1_missing_value_cannot_escape_through_global_help() -> None:
    result = run_bootstrap(L1_FLAG, "--help")
    assert result.returncode == 2
    assert "requires one non-empty path value" in result.stderr
    assert "Usage:" not in result.stdout
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout
    assert "Generate the selected task packet:" not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ("--help", L1_FLAG, "input.json"),
        (L1_FLAG, "input.json", L1_FLAG, "--help"),
    ],
)
def test_l1_flag_never_uses_legacy_help_escape(arguments: tuple[str, ...]) -> None:
    result = run_bootstrap(*arguments)
    assert result.returncode == 2
    assert "Usage:" not in result.stdout
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
    assert "copy `role_agent_dispatch_contract.dispatch_manifest_command` verbatim" in result.stdout
    assert "substitute the actual packet path and repo Python" in result.stdout
    assert "execute the manifest `dispatch_sequence` in order" in result.stdout
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


@pytest.mark.parametrize("repeated", [True, False])
def test_explicit_l1_printed_command_matches_direct_bootstrap_in_disposable_repo(
    tmp_path: Path, repeated: bool
) -> None:
    """Check helper artifact absence and printed-command parity with canonical bootstrap."""

    repo = _disposable_repo(tmp_path)
    artifact = repo / L1_ROOT / "L1 $(touch injected) 'quoted'.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps(_snapshot(repeated=repeated)), encoding="utf-8")
    relative_artifact = artifact.relative_to(repo).as_posix()
    options = (
        "--goal",
        "Review explicit family membership",
        "--task-class",
        "Orchestration",
        "--pr-phase",
        "post_open_review",
        "--path",
        "scripts/orchestration/local_session_bootstrap.sh",
        L1_FLAG,
        relative_artifact,
    )
    bash = shutil.which("bash")
    assert bash is not None
    helper = subprocess.run(
        [bash, str(repo / "scripts/orchestration/local_session_bootstrap.sh"), *options],
        cwd=repo,
        env=dict(_disposable_env(), VENV_PYTHON=sys.executable),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert helper.returncode == 0, helper.stdout + helper.stderr
    assert "did not create a task packet" in helper.stdout
    assert "did not run authoritative task_bootstrap.py" in helper.stdout
    assert not (repo / "artifacts/orchestration/task_packets").exists()
    assert {entry.name for entry in (repo / "artifacts/orchestration").iterdir()} == {
        artifact.parent.name
    }

    printed = _run_command(repo, _printed_command(helper.stdout))
    assert printed.returncode == 0, printed.stdout + printed.stderr
    printed_ref = json.loads(printed.stdout)["output"]
    printed_packet_path = repo / printed_ref
    printed_packet = json.loads(printed_packet_path.read_text(encoding="utf-8"))
    assert not (repo / "injected").exists()
    assert relative_artifact not in printed_packet["candidate_paths"]
    manifest_command = [
        sys.executable,
        str(repo / "scripts/orchestration/role_dispatch_bridge.py"),
        "--packet",
        printed_ref,
        "--mode",
        "runtime",
        "--pretty",
    ]
    printed_manifest_result = subprocess.run(
        manifest_command,
        cwd=repo,
        env=_disposable_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert printed_manifest_result.returncode == 0, printed_manifest_result.stderr
    printed_manifest = json.loads(printed_manifest_result.stdout)
    # Restore the empty candidate inventory: shadow-reuse telemetry is
    # intentionally sensitive to the previous packet's presence.
    printed_packet_path.unlink()

    direct = subprocess.run(
        [sys.executable, str(repo / "scripts/orchestration/task_bootstrap.py"), *options],
        cwd=repo,
        env=_disposable_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert direct.returncode == 0, direct.stdout + direct.stderr
    direct_ref = json.loads(direct.stdout)["output"]
    direct_packet = json.loads((repo / direct_ref).read_text(encoding="utf-8"))
    direct_manifest_result = subprocess.run(
        manifest_command,
        cwd=repo,
        env=_disposable_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert direct_manifest_result.returncode == 0, direct_manifest_result.stderr
    direct_manifest = json.loads(direct_manifest_result.stdout)
    printed_manifest.pop("generated_at")
    direct_manifest.pop("generated_at")
    assert printed_manifest == direct_manifest
    printed_packet.pop("orchestration_shadow_reuse_telemetry")
    direct_packet.pop("orchestration_shadow_reuse_telemetry")
    assert printed_packet == direct_packet
    assert printed_packet["invariant_review"]["state"] == (
        "required_pending" if repeated else "not_required"
    )
    assert (
        printed_packet["role_agent_dispatch_contract"]
        == direct_packet["role_agent_dispatch_contract"]
    )
    assert printed_packet["role_agent_dispatch_contract"]["packet_creation_executes_roles"] is False


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ((L1_FLAG,), "requires one non-empty path"),
        ((L1_FLAG, ""), "requires one non-empty path"),
        ((L1_FLAG, "  "), "requires one non-empty path"),
        ((L1_FLAG, "--path"), "requires one non-empty path"),
        ((L1_FLAG, "bad\nline.json"), "requires one non-empty path"),
        ((L1_FLAG, "bad\tline.json"), "requires one non-empty path"),
        ((L1_FLAG, f" {L1_ROOT}/leading.json"), "requires one non-empty path"),
        ((L1_FLAG, f"{L1_ROOT}/trailing.json "), "requires one non-empty path"),
        ((L1_FLAG, f"{L1_ROOT}/bad\u0085line.json"), "requires one non-empty path"),
        ((L1_FLAG, f"{L1_ROOT}/bad\u2028line.json"), "requires one non-empty path"),
        ((L1_FLAG, f"{L1_ROOT}/bad\u2029line.json"), "requires one non-empty path"),
        ((L1_FLAG, "one.json", L1_FLAG, "two.json"), "may be supplied only once"),
    ],
)
def test_explicit_l1_rejects_ambiguous_helper_values(
    arguments: tuple[str, ...], message: str
) -> None:
    result = run_bootstrap(
        "--goal",
        "Review families",
        "--task-class",
        "Orchestration",
        "--pr-phase",
        "post_open_review",
        *arguments,
    )
    assert result.returncode == 2
    assert message in result.stderr
    assert PREFLIGHT_SUCCESS_MARKER not in result.stdout


@pytest.mark.parametrize("phase", ["none", "pre_open", "merge_ready"])
def test_explicit_l1_requires_post_open_helper_phase(phase: str) -> None:
    result = run_bootstrap(
        "--goal",
        "Review families",
        "--task-class",
        "Orchestration",
        "--pr-phase",
        phase,
        L1_FLAG,
        f"{L1_ROOT}/input.json",
    )
    assert result.returncode == 2
    assert "requires --pr-phase post_open_review" in result.stderr


def test_explicit_l1_rejects_helper_invariant_class_conflict() -> None:
    result = run_bootstrap(
        "--goal",
        "Review families",
        "--task-class",
        "Orchestration",
        "--pr-phase",
        "post_open_review",
        "--invariant-change-class",
        "guard",
        L1_FLAG,
        f"{L1_ROOT}/input.json",
    )
    assert result.returncode == 2
    assert "incompatible with --invariant-change-class" in result.stderr


def test_explicit_l1_invalid_file_is_rejected_by_canonical_reader(tmp_path: Path) -> None:
    repo = _disposable_repo(tmp_path)
    artifact = repo / L1_ROOT / "invalid.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("not JSON", encoding="utf-8")
    bash = shutil.which("bash")
    assert bash is not None
    helper = subprocess.run(
        [
            bash,
            str(repo / "scripts/orchestration/local_session_bootstrap.sh"),
            "--goal",
            "Review families",
            "--task-class",
            "Orchestration",
            "--pr-phase",
            "post_open_review",
            L1_FLAG,
            artifact.relative_to(repo).as_posix(),
        ],
        cwd=repo,
        env=dict(_disposable_env(), VENV_PYTHON=sys.executable),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert helper.returncode == 0, helper.stdout + helper.stderr
    executed = _run_command(repo, _printed_command(helper.stdout))
    assert executed.returncode == 1
    assert "failed canonical L1 validation" in executed.stdout
