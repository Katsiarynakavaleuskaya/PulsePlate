#!/usr/bin/env python3
"""Bounded experiment runner for governed candidate evaluation.

RU: Применяет candidate patch только в изолированном checkout, запускает
неизменяемые oracle-команды в sandbox и пишет локальный result artifact.
EN: Applies a candidate patch only in an isolated checkout, runs immutable
oracle commands in the sandbox, and writes a local result artifact.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess  # nosec B404: git subprocesses are required for isolated temp checkouts (remove-by: 2026-07-31, ref: PR-1082)
import sys
import tempfile
import time
from typing import Any, Iterator

RUNNER_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(RUNNER_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNNER_REPO_ROOT))

from app.security import agent_control_plane as cp
from app.security import execution_sandbox as sandbox
from app.security.execution_sandbox import SandboxRequest
from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
from scripts.orchestration.creative_code_patch_workspace import (
    git_env_without_parent_state as _sanitized_git_env_without_parent_state,
    safe_git_config_args as _safe_git_config_args,
)
from scripts.orchestration.experiment_contract import (
    CONTRIBUTION_KINDS,
    DEFAULT_STOP_CONDITION,
    DEFAULT_RUNNER_MODE,
    ORACLE_BINARY_ALLOWLIST,
    ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
    SCHEMA_VERSION,
    validate_contribution_attribution,
    validate_experiment_id,
    validate_runner_mode,
    validate_experiment_packet,
)

RESULT_SCHEMA_VERSION = SCHEMA_VERSION
RESULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "results"
OOM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bout of memory\b", re.IGNORECASE),
    re.compile(r"\boom\b", re.IGNORECASE),
    re.compile(r"\bcannot allocate memory\b", re.IGNORECASE),
)
PYTHON_ORACLE_BINARIES = {"python", "python3"}


class ExperimentRunnerError(RuntimeError):
    """Base error for internal runner failures."""


class PolicyViolationError(ExperimentRunnerError):
    """Candidate patch or oracle command violates the governed contract."""


class InfraFlakeError(ExperimentRunnerError):
    """Patch/apply/oracle execution failed for runner reasons, not code signal."""


class CapabilityMismatchError(ExperimentRunnerError):
    """Required execution isolation disappeared or is unsupported."""


def _result_payload(
    *,
    experiment_id: str,
    runner_mode: str = DEFAULT_RUNNER_MODE,
    candidate_patch: str,
    status: str,
    failure_class: str | None,
    mutated_paths: list[str],
    oracle_results: list[dict[str, Any]],
    budget_observations: dict[str, Any],
    shared_tree_untouched: bool,
    contribution_kind: str = "none",
    coauthor_required: bool = False,
    coauthor_reason: str = "",
) -> dict[str, Any]:
    """Build the stable result payload returned by the runner."""

    if status != "accepted":
        contribution_kind = "none"
        coauthor_required = False
        coauthor_reason = ""

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "runner_mode": runner_mode,
        "candidate_patch": candidate_patch,
        "status": status,
        "failure_class": failure_class,
        "mutated_paths": mutated_paths,
        "oracle_results": oracle_results,
        "budget_observations": budget_observations,
        "shared_tree_untouched": shared_tree_untouched,
        "promotion_ready": False,
        "contribution_kind": contribution_kind,
        "coauthor_required": coauthor_required,
        "coauthor_reason": coauthor_reason,
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load experiment packet JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Experiment packet must be a JSON object.")
    return payload


def _read_patch_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InfraFlakeError(f"Unable to read candidate patch: {exc}") from exc


def _normalize_patch_target(raw_path: str) -> str:
    """Normalize a patch target and reject path-escape tricks."""

    stripped = raw_path.strip()
    if stripped in {"", "/dev/null"}:
        return ""
    if stripped.startswith(("a/", "b/")):
        stripped = stripped[2:]
    pure_path = PurePosixPath(stripped)
    if pure_path.is_absolute():
        raise PolicyViolationError(f"Patch path must be repo-relative, got: {raw_path}")
    if any(part == ".." for part in pure_path.parts):
        raise PolicyViolationError(f"Patch path escapes mutable surface: {raw_path}")
    normalized_parts = [part for part in pure_path.parts if part not in {"", "."}]
    if not normalized_parts:
        raise PolicyViolationError(f"Patch path must not be empty: {raw_path}")
    return PurePosixPath(*normalized_parts).as_posix()


def _extract_mutated_paths(patch_text: str) -> list[str]:
    """Extract deterministic touched paths from a unified diff patch."""

    if patch_text.strip() == "":
        return []

    mutated_paths: set[str] = set()
    saw_diff_marker = False
    for raw_line in patch_text.splitlines():
        if raw_line.startswith("diff --git "):
            saw_diff_marker = True
            parts = raw_line.split()
            if len(parts) >= 4:
                target = _normalize_patch_target(parts[3])
                if target:
                    mutated_paths.add(target)
            continue
        if raw_line.startswith(("rename to ", "copy to ")):
            saw_diff_marker = True
            target = _normalize_patch_target(raw_line.split(" ", 2)[2])
            if target:
                mutated_paths.add(target)
            continue
        if raw_line.startswith("rename from "):
            saw_diff_marker = True
            source = _normalize_patch_target(raw_line.split(" ", 2)[2])
            if source:
                mutated_paths.add(source)
            continue
        if raw_line.startswith("+++ "):
            saw_diff_marker = True
            target = _normalize_patch_target(raw_line[4:])
            if target:
                mutated_paths.add(target)

    if not mutated_paths and saw_diff_marker:
        return []
    if not mutated_paths:
        raise InfraFlakeError("Candidate patch is not a valid unified diff.")
    return sorted(mutated_paths)


def _path_matches_surface(path: str, surface: str) -> bool:
    return path == surface or path.startswith(f"{surface}/")


def _validate_patch_targets(packet: dict[str, Any], mutated_paths: list[str]) -> None:
    """Reject patches that exceed mutable surfaces or changed-file budget."""

    if not mutated_paths:
        return

    changed_file_budget = int(packet["budgets"]["max_changed_files"])
    if len(mutated_paths) > changed_file_budget:
        raise PolicyViolationError(
            "Candidate patch exceeds max_changed_files budget: "
            f"{len(mutated_paths)} > {changed_file_budget}"
        )

    mutable_surface = packet["mutable_candidate_surface"]
    invalid_paths = [
        path
        for path in mutated_paths
        if not any(_path_matches_surface(path, surface) for surface in mutable_surface)
    ]
    if invalid_paths:
        joined = ", ".join(invalid_paths)
        raise PolicyViolationError(
            "Candidate patch touches paths outside mutable_candidate_surface: " f"{joined}"
        )


def _resolve_git_binary() -> str:
    git_binary = shutil.which("git")
    if not git_binary:
        raise InfraFlakeError("git binary is required for experiment_runner.")
    resolved = Path(git_binary).expanduser().resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise InfraFlakeError("git binary must resolve to an executable file.")
    return str(resolved)


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git with an absolute binary and stable text capture."""

    process = subprocess.run(  # nosec B603: absolute git binary with bounded argv is required for isolated checkouts (remove-by: 2026-07-31, ref: PR-1082)
        [_resolve_git_binary(), *_safe_git_config_args(), *args],
        cwd=str(cwd),
        env=_sanitized_git_env_without_parent_state(),
        capture_output=True,
        text=True,
        check=False,
        input=input_text,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown git failure"
        raise InfraFlakeError(f"git {' '.join(args)} failed: {stderr}")
    return process


def _absolute_path_env(raw_path: str | None) -> str:
    """Return PATH entries as absolute paths for subprocess cwd isolation."""

    if not raw_path:
        return ""
    absolute_entries: list[str] = []
    for entry in raw_path.split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry).expanduser()
        if not candidate.is_absolute():
            candidate = candidate.resolve()
        absolute_entries.append(str(candidate))
    return os.pathsep.join(absolute_entries)


def _repo_python_from_env(env_name: str) -> Path | None:
    """Return a validated repo-approved Python executable from an env override."""

    raw_value = os.environ.get(env_name)
    if raw_value is None or raw_value.strip() == "":
        return None
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        raise InfraFlakeError(f"{env_name} must be an absolute executable path.")
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise InfraFlakeError(f"{env_name} is set but is not executable: {candidate}")
    return candidate


def _select_repo_python() -> Path | None:
    """Select the repo-approved Python interpreter for Python oracle commands."""

    for env_name in ("VENV_PYTHON", "DEV_PYTHON"):
        selected = _repo_python_from_env(env_name)
        if selected is not None:
            return selected

    candidates = [
        Path(REPO_ROOT) / ".venv" / "bin" / "python",
        Path(REPO_ROOT) / ".venv" / "Scripts" / "python.exe",
    ]
    parent_dir = Path(REPO_ROOT).resolve().parent
    if parent_dir.name == "worktrees":
        shared_root = parent_dir.parent
        try:
            git_common_dir = Path(
                _run_git(
                    ["rev-parse", "--path-format=absolute", "--git-common-dir"],
                    cwd=Path(REPO_ROOT),
                ).stdout.strip()
            ).resolve()
            git_common_dir.relative_to(shared_root / ".git")
        except (InfraFlakeError, OSError, ValueError):
            pass
        else:
            candidates.extend(
                [
                    shared_root / ".venv" / "bin" / "python",
                    shared_root / ".venv" / "Scripts" / "python.exe",
                ]
            )

    for repo_python in candidates:
        if repo_python.is_file() and os.access(repo_python, os.X_OK):
            return repo_python
    return None


def _python_oracle_path_prefix(requests: list[SandboxRequest]) -> str | None:
    """Return PATH prefix required for Python oracles, or fail closed."""

    python_binaries = sorted(
        {request.binary for request in requests if request.binary in PYTHON_ORACLE_BINARIES}
    )
    if not python_binaries:
        return None

    selected_python = _select_repo_python()
    if selected_python is None:
        binaries = ", ".join(python_binaries)
        raise InfraFlakeError(
            "Python oracle command requires repo-approved Python, but no executable "
            f"VENV_PYTHON, DEV_PYTHON, or repo .venv/bin/python was found for: {binaries}"
        )

    python_bin_dir = selected_python.parent
    for binary in python_binaries:
        resolved_binary = shutil.which(binary, path=str(python_bin_dir))
        if resolved_binary is None:
            raise InfraFlakeError(
                f"Python oracle binary {binary!r} was not found in repo-approved "
                f"Python bin dir: {python_bin_dir}"
            )
        if Path(resolved_binary).parent != python_bin_dir:
            raise InfraFlakeError(
                f"Python oracle binary {binary!r} did not resolve through "
                f"repo-approved Python bin dir: {python_bin_dir}"
            )
    return str(python_bin_dir)


def _shared_tree_status(root: Path) -> str:
    """Capture tracked/untracked status to prove the shared tree stayed untouched."""

    return _run_git(["status", "--short"], cwd=root).stdout


def _working_tree_diff_against_head(root: Path) -> str:
    """Capture tracked working-tree changes for oracle-only reviewer evidence."""

    return _run_git(
        ["diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD"],
        cwd=root,
    ).stdout


def _safe_result_experiment_id(packet: Any) -> str:
    if not isinstance(packet, dict):
        return "invalid-experiment"
    raw_experiment_id = str(packet.get("experiment_id", "")).strip()
    if not raw_experiment_id:
        return "invalid-experiment"
    try:
        return str(validate_experiment_id(raw_experiment_id, label="Experiment result"))
    except ValueError:
        return "invalid-experiment"


def _safe_result_runner_mode(packet: Any) -> str:
    if not isinstance(packet, dict):
        return str(DEFAULT_RUNNER_MODE)
    try:
        return str(validate_runner_mode(packet.get("runner_mode", DEFAULT_RUNNER_MODE)))
    except ValueError:
        return str(DEFAULT_RUNNER_MODE)


def _candidate_patch_ref_for_runner_mode(runner_mode: str, candidate_patch_ref: str) -> str:
    if runner_mode == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
        return str(ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE)
    return candidate_patch_ref


def _invalid_packet_result(
    *,
    packet: Any,
    candidate_patch_ref: str,
    error: str,
) -> dict[str, Any]:
    runner_mode = _safe_result_runner_mode(packet)
    return _result_payload(
        experiment_id=_safe_result_experiment_id(packet),
        runner_mode=runner_mode,
        candidate_patch=_candidate_patch_ref_for_runner_mode(runner_mode, candidate_patch_ref),
        status="rejected",
        failure_class="policy_violation",
        mutated_paths=[],
        oracle_results=[],
        budget_observations={"runner_error": error},
        shared_tree_untouched=False,
    )


@contextmanager
def _temporary_sandbox_env(
    *,
    sandbox_root: Path,
    allowed_binaries: tuple[str, ...],
    timeout_seconds: int,
    path_prefix: str | None = None,
) -> Iterator[None]:
    """Temporarily configure sandbox env without leaking state across runs."""

    normalized_path = _absolute_path_env(os.environ.get("PATH") or os.defpath)
    if path_prefix:
        normalized_path = os.pathsep.join([path_prefix, normalized_path])
    overrides = {
        sandbox.SANDBOX_ENABLED_ENV: "true",
        sandbox.SANDBOX_ROOT_ENV: str(sandbox_root),
        sandbox.SANDBOX_TIMEOUT_ENV: str(timeout_seconds),
        sandbox.SANDBOX_ALLOWED_BINARIES_ENV: ",".join(allowed_binaries),
        cp.EXECUTION_MODE_ENV: cp.EXECUTION_MODE_AUTO_SAFE,
        "PATH": normalized_path,
    }
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        os.environ.update(overrides)
        yield
    finally:
        for key, original in previous.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


def _create_temp_checkout(root: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    """Clone the current repo into a detached temporary checkout."""

    temp_dir = tempfile.TemporaryDirectory(prefix="experiment-runner-")
    checkout_root = Path(temp_dir.name) / "checkout"
    _run_git(["clone", "--quiet", "--no-hardlinks", str(root), str(checkout_root)], cwd=root)
    head_sha = _run_git(["rev-parse", "HEAD"], cwd=root).stdout.strip()
    _run_git(["checkout", "--quiet", "--detach", head_sha], cwd=checkout_root)
    return temp_dir, checkout_root


def _apply_candidate_patch(checkout_root: Path, patch_text: str) -> None:
    """Verify patch applicability before applying it inside the isolated checkout."""

    _run_git(["apply", "--check"], cwd=checkout_root, input_text=patch_text)
    _run_git(["apply"], cwd=checkout_root, input_text=patch_text)


def _has_effective_diff(checkout_root: Path) -> bool:
    """Return whether the temp checkout changed after patch apply."""

    process = _run_git(["status", "--short"], cwd=checkout_root, check=False)
    if process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown git failure"
        raise InfraFlakeError(f"git status failed after patch apply: {stderr}")
    return bool(process.stdout.strip())


def _command_to_request(command: str, *, disable_network: bool = False) -> SandboxRequest:
    """Convert a packet oracle command string into a sandbox request."""

    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise InfraFlakeError(f"Unable to parse oracle command: {command}") from exc
    if not argv:
        raise InfraFlakeError("Oracle command must not be empty.")
    binary = argv[0]
    if binary not in ORACLE_BINARY_ALLOWLIST:
        allowed = ", ".join(ORACLE_BINARY_ALLOWLIST)
        raise PolicyViolationError(
            f"Oracle binary {binary!r} is not allowlisted for experiment runner. "
            f"Allowed: {allowed}"
        )
    request_env = {sandbox.SANDBOX_DISABLE_NETWORK_ENV: "1"} if disable_network else None
    return SandboxRequest(binary=binary, args=tuple(argv[1:]), cwd=".", env=request_env)


def _classify_oracle_failure(result: sandbox.SandboxResult) -> str:
    """Map a non-zero oracle result to the canonical PR3 failure classes."""

    if result.timed_out:
        return "timeout"
    combined_output = f"{result.stdout}\n{result.stderr}"
    if "unshare:" in combined_output and any(
        marker in combined_output.lower()
        for marker in (
            "operation not permitted",
            "permission denied",
            "failed to execute",
            "invalid option",
            "not found",
        )
    ):
        return "capability_mismatch"
    if any(pattern.search(combined_output) for pattern in OOM_PATTERNS):
        return "oom"
    return "guard_failure"


def _run_oracles(
    packet: dict[str, Any], checkout_root: Path
) -> tuple[list[dict[str, Any]], str | None]:
    """Execute immutable oracle commands in the isolated sandbox root."""

    oracle_results: list[dict[str, Any]] = []
    failure_class: str | None = None
    disable_network = int(packet["budgets"]["network_budget"]) == 0
    requests = [
        _command_to_request(oracle["command"], disable_network=disable_network)
        for oracle in packet["immutable_oracles"]
    ]
    allowed_binaries = tuple(sorted({request.binary for request in requests}))
    path_prefix = _python_oracle_path_prefix(requests)
    total_wall_clock_seconds = int(packet["budgets"]["wall_clock_seconds"])
    started_at = time.monotonic()

    for oracle, request in zip(packet["immutable_oracles"], requests, strict=True):
        remaining_seconds = total_wall_clock_seconds - (time.monotonic() - started_at)
        if remaining_seconds <= 0:
            oracle_results.append(
                {
                    "command": oracle["command"],
                    "returncode": 124,
                    "timed_out": True,
                    "truncated": False,
                    "stdout": "",
                    "stderr": "Experiment wall_clock_seconds budget exhausted before oracle start.",
                    "cwd": str(checkout_root),
                }
            )
            failure_class = "timeout"
            break

        timeout_seconds = max(1, math.floor(remaining_seconds))
        with _temporary_sandbox_env(
            sandbox_root=checkout_root,
            allowed_binaries=allowed_binaries,
            timeout_seconds=timeout_seconds,
            path_prefix=path_prefix,
        ):
            try:
                result = sandbox.run_local_sandbox(
                    request,
                    allowlist={("sandbox.exec", "local://sandbox")},
                )
            except Exception as exc:
                message = str(exc).lower()
                if disable_network and (
                    "unshare" in message or "network-disabled sandbox" in message
                ):
                    raise CapabilityMismatchError(
                        f"Unable to enforce zero-network oracle isolation for "
                        f"{oracle['command']!r}: {exc}"
                    ) from exc
                raise InfraFlakeError(
                    f"Unable to execute oracle {oracle['command']!r}: {exc}"
                ) from exc

        oracle_results.append(
            {
                "command": oracle["command"],
                "returncode": result.returncode,
                "timed_out": result.timed_out,
                "truncated": result.truncated,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cwd": result.cwd,
            }
        )
        if result.returncode != 0 and failure_class is None:
            failure_class = _classify_oracle_failure(result)
            break

    return oracle_results, failure_class


def _resolve_output_path(raw_output: str | None, experiment_id: str) -> Path:
    """Resolve result output path under the experiment result artifact directory."""

    if raw_output:
        candidate = Path(raw_output)
        if not candidate.is_absolute():
            candidate = RESULT_ARTIFACT_DIR / candidate
    else:
        candidate = RESULT_ARTIFACT_DIR / f"{experiment_id}.json"
    candidate = candidate.resolve()

    try:
        candidate.relative_to(RESULT_ARTIFACT_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/experiments/results"
        ) from exc
    return candidate


def _evaluate_attempt(
    *,
    packet: dict[str, Any],
    patch_text: str,
    mutated_paths: list[str],
    budget_observations: dict[str, Any],
    candidate_patch_ref: str,
) -> dict[str, Any]:
    """Run one isolated evaluation attempt and fail closed on cleanup errors."""

    temp_dir, checkout_root = _create_temp_checkout(REPO_ROOT)
    try:
        _apply_candidate_patch(checkout_root, patch_text)
        if not _has_effective_diff(checkout_root):
            return _result_payload(
                experiment_id=packet["experiment_id"],
                runner_mode=packet.get("runner_mode", DEFAULT_RUNNER_MODE),
                candidate_patch=candidate_patch_ref,
                status="rejected",
                failure_class="unchanged_result",
                mutated_paths=mutated_paths,
                oracle_results=[],
                budget_observations=budget_observations,
                shared_tree_untouched=True,
            )

        oracle_results, failure_class = _run_oracles(packet, checkout_root)
        budget_observations["oracle_commands_executed"] = len(oracle_results)
        status = "accepted" if failure_class is None else "rejected"
        return _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=packet.get("runner_mode", DEFAULT_RUNNER_MODE),
            candidate_patch=candidate_patch_ref,
            status=status,
            failure_class=failure_class,
            mutated_paths=mutated_paths,
            oracle_results=oracle_results,
            budget_observations=budget_observations,
            shared_tree_untouched=True,
        )
    finally:
        try:
            temp_dir.cleanup()
        except Exception as exc:
            raise InfraFlakeError(f"Unable to clean temp checkout: {exc}") from exc


def evaluate_candidate(packet: dict[str, Any], candidate_patch_path: Path) -> dict[str, Any]:
    """Evaluate a candidate patch against a validated experiment packet."""

    candidate_patch_ref = str(candidate_patch_path)
    try:
        packet = validate_experiment_packet(packet)
    except ValueError as exc:
        return _invalid_packet_result(
            packet=packet,
            candidate_patch_ref=candidate_patch_ref,
            error=str(exc),
        )
    budget_observations = {
        "configured_budgets": dict(packet["budgets"]),
        "stop_condition": packet["budgets"].get("stop_condition", DEFAULT_STOP_CONDITION),
        "oracle_commands_configured": len(packet["immutable_oracles"]),
        "oracle_commands_executed": 0,
        "candidate_changed_files": 0,
        "attempts": 0,
        "retries_consumed": 0,
    }
    shared_status_before: str | None = None

    try:
        candidate_patch_ref = normalize_repo_path(candidate_patch_path)
        shared_status_before = _shared_tree_status(REPO_ROOT)
        if packet.get("runner_mode") == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
            raise PolicyViolationError(
                "oracle_only_governance_reviewer mode must not evaluate candidate patches"
            )
        patch_text = _read_patch_text(candidate_patch_path)
        mutated_paths = _extract_mutated_paths(patch_text)
        budget_observations["candidate_changed_files"] = len(mutated_paths)
        if not mutated_paths:
            result = _result_payload(
                experiment_id=packet["experiment_id"],
                runner_mode=packet.get("runner_mode", DEFAULT_RUNNER_MODE),
                candidate_patch=candidate_patch_ref,
                status="rejected",
                failure_class="unchanged_result",
                mutated_paths=[],
                oracle_results=[],
                budget_observations=budget_observations,
                shared_tree_untouched=True,
            )
            return result

        _validate_patch_targets(packet, mutated_paths)

        max_attempts = int(packet["budgets"]["retry_budget"]) + 1
        last_infra_error: str | None = None
        for attempt_number in range(1, max_attempts + 1):
            budget_observations["attempts"] = attempt_number
            budget_observations["retries_consumed"] = attempt_number - 1
            budget_observations["oracle_commands_executed"] = 0

            try:
                result = _evaluate_attempt(
                    packet=packet,
                    patch_text=patch_text,
                    mutated_paths=mutated_paths,
                    budget_observations=budget_observations,
                    candidate_patch_ref=candidate_patch_ref,
                )
                break
            except InfraFlakeError as exc:
                last_infra_error = str(exc)
                if attempt_number == max_attempts:
                    raise
        else:
            raise InfraFlakeError(last_infra_error or "Unknown infra_flake during experiment run.")
    except PolicyViolationError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=packet.get("runner_mode", DEFAULT_RUNNER_MODE),
            candidate_patch=_candidate_patch_ref_for_runner_mode(
                packet.get("runner_mode", DEFAULT_RUNNER_MODE),
                candidate_patch_ref,
            ),
            status="rejected",
            failure_class="policy_violation",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=shared_status_before is not None,
        )
    except CapabilityMismatchError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=packet.get("runner_mode", DEFAULT_RUNNER_MODE),
            candidate_patch=candidate_patch_ref,
            status="rejected",
            failure_class="capability_mismatch",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=shared_status_before is not None,
        )
    except InfraFlakeError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=packet.get("runner_mode", DEFAULT_RUNNER_MODE),
            candidate_patch=candidate_patch_ref,
            status="rejected",
            failure_class="infra_flake",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=shared_status_before is not None,
        )

    if shared_status_before is None:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"].setdefault(
            "runner_error",
            "Unable to capture shared working tree status before run.",
        )
        return result

    try:
        shared_status_after = _shared_tree_status(REPO_ROOT)
    except InfraFlakeError as exc:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"]["runner_error"] = str(exc)
        return result
    if shared_status_before != shared_status_after:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"]["runner_error"] = "Shared working tree changed during run."
    return result


def evaluate_oracle_only_governance_reviewer(
    packet: dict[str, Any],
    *,
    contribution_kind: str = "none",
    coauthor_required: bool = False,
    coauthor_reason: str = "",
) -> dict[str, Any]:
    """Run immutable governance oracles without applying any candidate patch."""

    try:
        contribution_kind, coauthor_required, coauthor_reason = validate_contribution_attribution(
            contribution_kind=contribution_kind,
            coauthor_required=coauthor_required,
            coauthor_reason=coauthor_reason,
        )
    except ValueError as exc:
        raise PolicyViolationError(str(exc)) from exc

    try:
        packet = validate_experiment_packet(packet)
    except ValueError as exc:
        return _invalid_packet_result(
            packet=packet,
            candidate_patch_ref=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            error=str(exc),
        )
    if packet.get("runner_mode") != ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
        raise PolicyViolationError(
            "evaluate_oracle_only_governance_reviewer requires oracle-only runner_mode"
        )

    budget_observations = {
        "configured_budgets": dict(packet["budgets"]),
        "stop_condition": packet["budgets"].get("stop_condition", DEFAULT_STOP_CONDITION),
        "oracle_commands_configured": len(packet["immutable_oracles"]),
        "oracle_commands_executed": 0,
        "candidate_changed_files": 0,
        "attempts": 1,
        "retries_consumed": 0,
        "runner_mode": ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
        "source_diff_applied": False,
        "source_diff_paths": [],
    }
    shared_status_before: str | None = None

    try:
        shared_status_before = _shared_tree_status(REPO_ROOT)
        source_diff = _working_tree_diff_against_head(REPO_ROOT)
        source_diff_paths = _extract_mutated_paths(source_diff) if source_diff else []
        budget_observations["source_diff_paths"] = source_diff_paths
        context_surface = packet["mutable_candidate_surface"]
        outside_context = [
            path
            for path in source_diff_paths
            if not any(_path_matches_surface(path, surface) for surface in context_surface)
        ]
        if outside_context:
            joined = ", ".join(outside_context)
            raise PolicyViolationError(
                "Oracle-only source diff must stay within packet context surface: " f"{joined}"
            )
        temp_dir, checkout_root = _create_temp_checkout(REPO_ROOT)
        try:
            if source_diff:
                _apply_candidate_patch(checkout_root, source_diff)
                budget_observations["source_diff_applied"] = True
            oracle_results, failure_class = _run_oracles(packet, checkout_root)
            budget_observations["oracle_commands_executed"] = len(oracle_results)
            status = "accepted" if failure_class is None else "rejected"
            result = _result_payload(
                experiment_id=packet["experiment_id"],
                runner_mode=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
                candidate_patch=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
                status=status,
                failure_class=failure_class,
                mutated_paths=[],
                oracle_results=oracle_results,
                budget_observations=budget_observations,
                shared_tree_untouched=True,
                contribution_kind=contribution_kind,
                coauthor_required=coauthor_required,
                coauthor_reason=coauthor_reason.strip(),
            )
        finally:
            try:
                temp_dir.cleanup()
            except Exception as exc:
                raise InfraFlakeError(f"Unable to clean temp checkout: {exc}") from exc
    except PolicyViolationError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            candidate_patch=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            status="rejected",
            failure_class="policy_violation",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=shared_status_before is not None,
        )
    except CapabilityMismatchError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            candidate_patch=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            status="rejected",
            failure_class="capability_mismatch",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=shared_status_before is not None,
        )
    except InfraFlakeError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            runner_mode=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            candidate_patch=ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
            status="rejected",
            failure_class="infra_flake",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=shared_status_before is not None,
        )

    if shared_status_before is None:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"].setdefault(
            "runner_error",
            "Unable to capture shared working tree status before run.",
        )
        return result

    try:
        shared_status_after = _shared_tree_status(REPO_ROOT)
    except InfraFlakeError as exc:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"]["runner_error"] = str(exc)
        return result
    if shared_status_before != shared_status_after:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"]["runner_error"] = "Shared working tree changed during run."
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="experiment_runner",
        description="Evaluate a governed candidate patch or oracle-only reviewer packet.",
    )
    parser.add_argument("--packet", required=True, help="Experiment packet JSON path.")
    parser.add_argument("--candidate-patch", default=None, help="Unified diff patch path.")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional result JSON path under artifacts/orchestration/experiments/results/. "
            "Defaults to artifacts/orchestration/experiments/results/<id>.json"
        ),
    )
    parser.add_argument(
        "--contribution-kind",
        default="none",
        choices=CONTRIBUTION_KINDS,
        help=(
            "Material Experiment Runner contribution kind for advisory attribution. "
            "Use with --coauthor-required only when the oracle result will shape the PR."
        ),
    )
    parser.add_argument(
        "--coauthor-required",
        action="store_true",
        help="Mark the result artifact as requiring the canonical Experiment Runner trailer.",
    )
    parser.add_argument(
        "--coauthor-reason",
        default="",
        help="Human-readable reason when --coauthor-required is set.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    packet_path = Path(args.packet).expanduser().resolve()

    try:
        packet = validate_experiment_packet(_read_json_object(packet_path))
        output_path = _resolve_output_path(args.output, packet["experiment_id"])
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

    runner_mode = packet.get("runner_mode", DEFAULT_RUNNER_MODE)
    if runner_mode == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
        if args.candidate_patch:
            print("FAIL: oracle-only governance reviewer mode does not accept --candidate-patch")
            return 1
        try:
            result = evaluate_oracle_only_governance_reviewer(
                packet,
                contribution_kind=args.contribution_kind,
                coauthor_required=bool(args.coauthor_required),
                coauthor_reason=args.coauthor_reason,
            )
        except PolicyViolationError as exc:
            print(f"FAIL: {exc}")
            return 1
    else:
        if args.coauthor_required or args.contribution_kind != "none" or args.coauthor_reason:
            print("FAIL: contribution attribution flags are supported only in oracle-only mode")
            return 1
        if not args.candidate_patch:
            print("FAIL: --candidate-patch is required for candidate_patch runner mode")
            return 1
        candidate_patch_path = Path(args.candidate_patch).expanduser().resolve()
        result = evaluate_candidate(packet, candidate_patch_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"FAIL: unable to write experiment result: {exc}")
        return 1

    print(
        json.dumps(
            {
                "result_artifact_written": True,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
