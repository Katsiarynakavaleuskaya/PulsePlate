"""Regression tests for the repo-level PR lane starter."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

import scripts.orchestration.task_bootstrap as task_bootstrap

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


def run_start_with_system_bash(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the starter with macOS system Bash 3.2, not PATH discovery."""

    return subprocess.run(
        ["/bin/bash", str(START_SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
        env=os.environ.copy(),
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
    assert "Would run in worktree after bootstrap:" in result.stdout
    assert "scripts/orchestration/evidence_rail_applicability.py build" in result.stdout
    assert "scripts/orchestration/pr_evidence_sidecar.py prepare" in result.stdout
    assert "applicability: pending validated bootstrap packet" in result.stdout
    assert "<validated-mask-rails>" in result.stdout
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
    assert "$VENV_PYTHON scripts/orchestration/experiment_runner.py" in result.stdout
    assert "artifact load/write failures are infra blockers" in result.stdout
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
    assert "copy `role_agent_dispatch_contract.dispatch_manifest_command` verbatim" in (
        result.stdout
    )
    assert "substitute the actual packet path and repo Python" in result.stdout
    assert "execute the manifest `dispatch_sequence` in order" in result.stdout
    assert "Role-agent dispatch is a required post-bootstrap step" in result.stdout
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


def test_system_bash_dry_run_handles_empty_additive_rail_array() -> None:
    result = run_start_with_system_bash(*_required_args(), "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "Requested additive evidence rails: <none>" in result.stdout
    assert "--additive-rail" not in next(
        line
        for line in result.stdout.splitlines()
        if "evidence_rail_applicability.py build" in line
    )


def test_system_bash_dry_run_accepts_first_additive_rail() -> None:
    result = run_start_with_system_bash(
        *_required_args(),
        "--evidence-sidecar-rail",
        "teleology",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    build_line = next(
        line
        for line in result.stdout.splitlines()
        if "evidence_rail_applicability.py build" in line
    )
    assert build_line.count("--additive-rail teleology") == 1
    assert "Requested additive evidence rails: teleology" in result.stdout


def _valid_sidecar_prepare_payload() -> dict[str, object]:
    sidecar_id = "sha256:" + ("d" * 64)
    return {
        "schema_version": "pr_evidence_sidecar.start.v1",
        "command": "prepare",
        "sidecar_id": sidecar_id,
        "sidecar_path": (
            f"artifacts/orchestration/pr_evidence_sidecars/{sidecar_id[7:]}/start.json"
        ),
        "created": True,
    }


def _make_packet_artifact(tmp_path: Path, *, candidate_path: str) -> tuple[str, Path]:
    packet = task_bootstrap.build_task_packet(
        goal=f"Start governed PR lane {tmp_path.name}",
        task_class="Orchestration",
        candidate_paths=[candidate_path],
        telemetry_path=tmp_path / "missing-telemetry.json",
    )
    packet_rel = "artifacts/orchestration/task_packets/" + str(packet["task_packet_id"]) + ".json"
    packet_path = REPO_ROOT / packet_rel
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return packet_rel, packet_path


def _run_execute_path_with_sidecar_payload(
    tmp_path: Path,
    sidecar_payload: dict[str, object],
    *,
    candidate_path: str = "scripts/orchestration/start_pr_lane.sh",
    applicability_mode: str = "valid",
    applicability_helper_present: bool = True,
    extra_start_args: tuple[str, ...] = (),
    assert_projection_not_exported: bool = False,
    preexported_projection_sentinel: bool = False,
    worktree_check: Callable[[Path], None] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    packet_rel, packet_path = _make_packet_artifact(tmp_path, candidate_path=candidate_path)
    worktree_rel = f"worktrees/execute-path-test-{tmp_path.name}"
    worktree_path = REPO_ROOT / worktree_rel

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
  worktree)
    if [[ -n "${WORKTREE_MARKER_PATH:-}" ]]; then
      printf 'created\n' > "${WORKTREE_MARKER_PATH}"
    fi
    mkdir -p "$5/scripts/orchestration"
    touch "$5/scripts/orchestration/pr_evidence_sidecar.py"
    if [[ "${CREATE_APPLICABILITY_HELPER:-1}" == "1" ]]; then
      touch "$5/scripts/orchestration/evidence_rail_applicability.py"
    fi
    exit 0
    ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    git_stub.chmod(0o755)

    python_stub = bin_dir / "python3"
    real_python = sys.executable
    sidecar_output = shlex.quote(json.dumps(sidecar_payload, separators=(",", ":"), sort_keys=True))
    python_stub.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
assert_projection_not_exported() {{
  if [[ "${{ASSERT_PROJECTION_NOT_EXPORTED:-0}}" == "1" && "${{APPLICABILITY_JSON+x}}" == "x" ]]; then
    echo "APPLICABILITY_JSON leaked into child environment" >&2
    exit 91
  fi
}}
case "$1" in
  *check_preflight.py)
    echo "PASS: stub preflight"
    exit 0
    ;;
  *task_bootstrap.py)
    printf '%s\\0' "$@" > {str(tmp_path / "task-bootstrap-args.bin")!r}
    printf '{{"output": "{packet_rel}", "primary_agent": "agent-coordinator", "reviewer": "qa-engineer-agent", "recommended_skills": ["pulseplate-premortem-risk-review"]}}\\n'
    exit 0
    ;;
  *evidence_rail_applicability.py)
    assert_projection_not_exported
    if [[ "${{ASSERT_PROJECTION_NOT_EXPORTED:-0}}" == "1" && "${{2:-}}" == "validate" ]]; then
      printf 'validator-env\\n' >> {str(tmp_path / "applicability-transport-checks.txt")!r}
    fi
    if [[ "${{2:-}}" == "build" ]]; then
      case "${{APPLICABILITY_MODE:-valid}}" in
        failure)
          echo INVALID_INPUT >&2
          exit 1
          ;;
        empty)
          exit 0
          ;;
        noncanonical)
          printf '{{}}\n'
          exit 0
          ;;
        oversized)
          {real_python!r} -c 'print("x" * 9000)'
          exit 0
          ;;
      esac
    fi
    shift
    exec {real_python!r} {str(REPO_ROOT / "scripts/orchestration/evidence_rail_applicability.py")!r} "$@"
    ;;
  *pr_evidence_sidecar.py)
    assert_projection_not_exported
    if [[ "${{ASSERT_PROJECTION_NOT_EXPORTED:-0}}" == "1" ]]; then
      printf 'sidecar-env\\n' >> {str(tmp_path / "applicability-transport-checks.txt")!r}
    fi
    printf '%s\\n' "$*" > {str(tmp_path / "sidecar-args.txt")!r}
    printf '%s\\n' {sidecar_output}
    exit 0
    ;;
  *render_codex_start_prompt.py)
    assert_projection_not_exported
    if [[ "${{ASSERT_PROJECTION_NOT_EXPORTED:-0}}" == "1" ]]; then
      printf 'renderer-env\\n' >> {str(tmp_path / "applicability-transport-checks.txt")!r}
    fi
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
    env["APPLICABILITY_MODE"] = applicability_mode
    env["CREATE_APPLICABILITY_HELPER"] = "1" if applicability_helper_present else "0"
    env["WORKTREE_MARKER_PATH"] = str(tmp_path / "worktree-created.txt")
    if assert_projection_not_exported:
        if preexported_projection_sentinel:
            env["APPLICABILITY_JSON"] = "sentinel-preexported-projection"
        else:
            env.pop("APPLICABILITY_JSON", None)
        env["SHELLOPTS"] = "allexport"
        env["ASSERT_PROJECTION_NOT_EXPORTED"] = "1"
    try:
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
            *extra_start_args,
            "--allow-dirty-launcher",
            env=env,
        )
        if worktree_check is not None:
            worktree_check(worktree_path)
    finally:
        if worktree_path.exists():
            shutil.rmtree(worktree_path)
        packet_path.unlink(missing_ok=True)
    return result, packet_path


def test_start_pr_lane_execute_path_prints_packet_prompt(tmp_path: Path) -> None:
    """The real post-task-bootstrap path should emit the packet-backed Codex prompt."""

    result, packet_path = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
    )

    assert result.returncode == 0, result.stderr
    assert "Authoritative bootstrap already ran" in result.stdout
    assert "PR evidence sidecar v1: state=prepared" in result.stdout
    assert f"sha256:{'d' * 64}" in result.stdout
    assert "Structural local receipt only; no review, CI, merge" in result.stdout
    assert "Rail truth table: false -> not_applicable + null" in result.stdout
    packet_rel = packet_path.relative_to(REPO_ROOT).as_posix()
    assert f"Task packet: {packet_rel}" in result.stdout
    assert "packet_creation_executes_roles=false" in result.stdout
    assert "role_agent_dispatch_required=true" in result.stdout
    assert "role_dispatch_bridge.py --packet" in result.stdout
    assert shlex.quote(packet_rel) in result.stdout
    assert "--mode runtime --implementation-owner" in result.stdout
    assert "Run the dispatch_sequence roles in order before implementation." in result.stdout
    assert "Role order: agent-coordinator" in result.stdout
    assert "Passive skills from packet: pulseplate-workflow" in result.stdout
    assert "Evidence rail applicability: validated packet-bound selection." in result.stdout
    assert "Applicable PR evidence sidecar rails: euler, experiment_runner, teleology" in (
        result.stdout
    )
    assert "VENV_PYTHON" in result.stdout
    assert "$VENV_PYTHON -m pytest" in result.stdout
    assert "$VENV_PYTHON scripts/orchestration/experiment_runner.py" in result.stdout
    assert "artifact load/write failures are infra blockers" in result.stdout
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


def test_start_pr_lane_dry_run_deduplicates_sidecar_rails_without_writing() -> None:
    """Dry-run prints the post-bootstrap plan once per applicability rail."""

    result = run_start(
        *_required_args(),
        "--evidence-sidecar-rail",
        "teleology",
        "--evidence-sidecar-rail",
        "experiment_runner",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    planned = next(
        line
        for line in result.stdout.splitlines()
        if "evidence_rail_applicability.py build" in line
    )
    assert planned.count("--additive-rail experiment_runner") == 1
    assert planned.count("--additive-rail teleology") == 1
    assert "--applicable-rail" not in planned
    assert "pr_evidence_sidecars/" not in result.stdout


def test_start_pr_lane_dry_run_forwards_all_typed_design_arguments() -> None:
    result = run_start(
        *_required_args(),
        "--design-source",
        "figma_design",
        "--source-url",
        "https://www.figma.com/design/example",
        "--file-key-or-workspace",
        "file-key",
        "--node-id-or-frame-id",
        "1:2",
        "--target-surface",
        "web-home",
        "--task-mode",
        "verify",
        "--figma-lane-tool",
        "figma_native",
        "--design-blocker",
        "stale",
        "--code-native-design-brief-path",
        "docs/design/example.md",
        "--explicit-creation-mode",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    bootstrap_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("Would run in worktree:") and "task_bootstrap.py" in line
    )
    for expected in (
        "--design-source figma_design",
        "--source-url https://www.figma.com/design/example",
        "--file-key-or-workspace file-key",
        "--node-id-or-frame-id 1:2",
        "--target-surface web-home",
        "--task-mode verify",
        "--figma-lane-tool figma_native",
        "--design-blocker stale",
        "--code-native-design-brief-path docs/design/example.md",
        "--explicit-creation-mode",
    ):
        assert expected in bootstrap_line
        assert expected in result.stdout.split("Paste into Codex now:", maxsplit=1)[1]
    assert "pending validated bootstrap packet" in result.stdout
    assert "Applicable PR evidence sidecar rails:" not in result.stdout


def test_start_pr_lane_execute_path_forwards_all_design_arguments_unchanged(
    tmp_path: Path,
) -> None:
    design_args = (
        "--design-source",
        "figma_design",
        "--source-url",
        "https://www.figma.com/design/example?node-id=42-7",
        "--file-key-or-workspace",
        "file key",
        "--node-id-or-frame-id",
        "42:7",
        "--target-surface",
        "web.home",
        "--task-mode",
        "sync",
        "--figma-lane-tool",
        "figma_native",
        "--design-blocker",
        "stale",
        "--design-blocker",
        "blocked_by_plan",
        "--code-native-design-brief-path",
        "docs/design/hero brief.md",
        "--explicit-creation-mode",
    )
    result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
        extra_start_args=design_args,
    )

    assert result.returncode == 0, result.stderr
    raw_args = (tmp_path / "task-bootstrap-args.bin").read_bytes().split(b"\0")
    assert raw_args[-1] == b""
    observed = [item.decode("utf-8") for item in raw_args[:-1]]
    design_start = observed.index("--design-source")
    assert observed[design_start:] == list(design_args)


def test_start_pr_lane_uses_exact_three_and_two_rail_masks(tmp_path: Path) -> None:
    high_result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path / "high",
        _valid_sidecar_prepare_payload(),
    )
    assert high_result.returncode == 0, high_result.stderr
    high_args = (tmp_path / "high/sidecar-args.txt").read_text(encoding="utf-8")
    assert high_args.count("--applicable-rail euler") == 1
    assert high_args.count("--applicable-rail experiment_runner") == 1
    assert high_args.count("--applicable-rail teleology") == 1

    docs_result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path / "docs",
        _valid_sidecar_prepare_payload(),
        candidate_path="README.md",
    )
    assert docs_result.returncode == 0, docs_result.stderr
    docs_args = (tmp_path / "docs/sidecar-args.txt").read_text(encoding="utf-8")
    assert "--applicable-rail euler" not in docs_args
    assert docs_args.count("--applicable-rail experiment_runner") == 1
    assert docs_args.count("--applicable-rail teleology") == 1


def test_applicability_failure_blocks_sidecar_and_prompt(tmp_path: Path) -> None:
    result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
        applicability_mode="failure",
    )

    assert result.returncode == 1
    assert "INVALID_INPUT" in result.stderr
    assert "evidence rail applicability build failed" in result.stderr
    assert not (tmp_path / "sidecar-args.txt").exists()
    assert "Paste into Codex now:" not in result.stdout


@pytest.mark.parametrize(
    ("mode", "expected_error"),
    (
        ("empty", "evidence rail applicability build returned empty output"),
        ("noncanonical", "evidence rail applicability validation failed"),
        ("oversized", "evidence rail applicability validation failed"),
    ),
)
def test_invalid_applicability_output_blocks_sidecar_and_prompt(
    tmp_path: Path,
    mode: str,
    expected_error: str,
) -> None:
    result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
        applicability_mode=mode,
    )

    assert result.returncode == 1
    assert expected_error in result.stderr
    assert not (tmp_path / "sidecar-args.txt").exists()
    assert "Paste into Codex now:" not in result.stdout


def test_missing_applicability_helper_retains_diagnostic_worktree_before_blocking(
    tmp_path: Path,
) -> None:
    retained_worktrees: list[Path] = []

    def check_retained_worktree(worktree_path: Path) -> None:
        assert worktree_path.is_dir()
        retained_worktrees.append(worktree_path)

    result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
        applicability_helper_present=False,
        worktree_check=check_retained_worktree,
    )

    assert result.returncode == 1
    assert "evidence rail applicability helper is unavailable after bootstrap" in result.stderr
    assert (tmp_path / "worktree-created.txt").read_text(encoding="utf-8") == "created\n"
    assert len(retained_worktrees) == 1
    assert not retained_worktrees[0].exists()
    assert not (tmp_path / "sidecar-args.txt").exists()
    assert "Paste into Codex now:" not in result.stdout


def test_inherited_allexport_does_not_export_captured_projection(
    tmp_path: Path,
) -> None:
    result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
        assert_projection_not_exported=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Evidence rail applicability: validated packet-bound selection." in result.stdout
    assert "Applicable PR evidence sidecar rails:" in result.stdout
    assert (tmp_path / "applicability-transport-checks.txt").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "validator-env",
        "sidecar-env",
        "renderer-env",
    ]


def test_preexported_projection_is_unset_before_packet_capture(
    tmp_path: Path,
) -> None:
    result, _ = _run_execute_path_with_sidecar_payload(
        tmp_path,
        _valid_sidecar_prepare_payload(),
        assert_projection_not_exported=True,
        preexported_projection_sentinel=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Evidence rail applicability: validated packet-bound selection." in result.stdout
    assert "Applicable PR evidence sidecar rails:" in result.stdout
    assert "sentinel-preexported-projection" not in result.stdout
    assert "sentinel-preexported-projection" not in result.stderr
    assert (tmp_path / "applicability-transport-checks.txt").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "validator-env",
        "sidecar-env",
        "renderer-env",
    ]


def test_start_script_keeps_captured_projection_on_stdin_and_bash_32_surface() -> None:
    source = START_SCRIPT.read_text(encoding="utf-8")

    assert "--evidence-rail-applicability-stdin" in source
    assert "printf '%s\\n' \"${APPLICABILITY_JSON}\" |" in source
    assert "--evidence-rail-applicability-json" not in source
    assert "declare -A" not in source
    assert "${!" not in source
    assert "mapfile" not in source
    assert "readarray" not in source

    bash_path = shutil.which("bash")
    assert bash_path is not None
    syntax = subprocess.run(
        [bash_path, "-n", str(START_SCRIPT)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr


def test_start_pr_lane_handshake_contract_rejects_schema_and_hex_drift(
    tmp_path: Path,
) -> None:
    """Execute-path handshake validation rejects schema, lowercase-id, and key drift."""

    valid = _valid_sidecar_prepare_payload()
    uppercase_id = "sha256:" + ("D" * 64)
    cases = {
        "wrong-schema": {**valid, "schema_version": "pr_evidence_sidecar.start.v2"},
        "uppercase-id": {
            **valid,
            "sidecar_id": uppercase_id,
            "sidecar_path": (
                "artifacts/orchestration/pr_evidence_sidecars/" f"{uppercase_id[7:]}/start.json"
            ),
        },
        "extra-key": {**valid, "unexpected": True},
    }

    for case_name, payload in cases.items():
        case_path = tmp_path / f"{tmp_path.name}-{case_name}"
        result, _packet_path = _run_execute_path_with_sidecar_payload(case_path, payload)

        assert result.returncode == 0, result.stderr
        assert "PR evidence sidecar v1: state=invalid; id=<none>." in result.stdout
        assert "PR evidence sidecar v1: state=prepared" not in result.stdout
        assert (
            "WARNING: evidence sidecar invalid; structural receipt only, no authority granted."
            in result.stderr
        )


def test_start_pr_lane_allows_dirty_launcher_for_synced_origin_main_lane(
    tmp_path: Path,
) -> None:
    """A dirty launcher checkout requires an explicit isolated origin/main exception."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    packet_rel, packet_path = _make_packet_artifact(
        tmp_path, candidate_path="scripts/orchestration/start_pr_lane.sh"
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
  worktree)
    mkdir -p "$5/scripts/orchestration"
    touch "$5/scripts/orchestration/evidence_rail_applicability.py"
    exit 0
    ;;
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
    printf '{{"output": "{packet_rel}", "primary_agent": "agent-coordinator", "reviewer": "architecture-specialist", "recommended_skills": []}}\\n'
    exit 0
    ;;
  *evidence_rail_applicability.py)
    shift
    exec {real_python!r} {str(REPO_ROOT / "scripts/orchestration/evidence_rail_applicability.py")!r} "$@"
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
    packet_path.unlink(missing_ok=True)

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
