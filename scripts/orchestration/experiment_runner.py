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
from scripts.orchestration.experiment_contract import (
    DEFAULT_STOP_CONDITION,
    ORACLE_BINARY_ALLOWLIST,
    SCHEMA_VERSION,
    validate_experiment_packet,
)

RESULT_SCHEMA_VERSION = SCHEMA_VERSION
RESULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "results"
OOM_MARKERS: tuple[str, ...] = (
    "out of memory",
    "oom",
    "cannot allocate memory",
)


class ExperimentRunnerError(RuntimeError):
    """Base error for internal runner failures."""


class PolicyViolationError(ExperimentRunnerError):
    """Candidate patch or oracle command violates the governed contract."""


class InfraFlakeError(ExperimentRunnerError):
    """Patch/apply/oracle execution failed for runner reasons, not code signal."""


def _result_payload(
    *,
    experiment_id: str,
    candidate_patch: str,
    status: str,
    failure_class: str | None,
    mutated_paths: list[str],
    oracle_results: list[dict[str, Any]],
    budget_observations: dict[str, Any],
    shared_tree_untouched: bool,
) -> dict[str, Any]:
    """Build the stable result payload returned by the runner."""

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "candidate_patch": candidate_patch,
        "status": status,
        "failure_class": failure_class,
        "mutated_paths": mutated_paths,
        "oracle_results": oracle_results,
        "budget_observations": budget_observations,
        "shared_tree_untouched": shared_tree_untouched,
        "promotion_ready": False,
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
        if raw_line.startswith(("rename from ", "copy from ")):
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
    return git_binary


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run git with an absolute binary and stable text capture."""

    process = subprocess.run(  # nosec B603: absolute git binary with bounded argv is required for isolated checkouts (remove-by: 2026-07-31, ref: PR-1082)
        [_resolve_git_binary(), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown git failure"
        raise InfraFlakeError(f"git {' '.join(args)} failed: {stderr}")
    return process


def _shared_tree_status(root: Path) -> str:
    """Capture tracked/untracked status to prove the shared tree stayed untouched."""

    return _run_git(["status", "--short"], cwd=root).stdout


@contextmanager
def _temporary_sandbox_env(
    *,
    sandbox_root: Path,
    allowed_binaries: tuple[str, ...],
    timeout_seconds: int,
) -> Iterator[None]:
    """Temporarily configure sandbox env without leaking state across runs."""

    overrides = {
        sandbox.SANDBOX_ENABLED_ENV: "true",
        sandbox.SANDBOX_ROOT_ENV: str(sandbox_root),
        sandbox.SANDBOX_TIMEOUT_ENV: str(timeout_seconds),
        sandbox.SANDBOX_ALLOWED_BINARIES_ENV: ",".join(allowed_binaries),
        cp.EXECUTION_MODE_ENV: cp.EXECUTION_MODE_AUTO_SAFE,
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


def _apply_candidate_patch(checkout_root: Path, patch_path: Path) -> None:
    """Verify patch applicability before applying it inside the isolated checkout."""

    _run_git(["apply", "--check", str(patch_path)], cwd=checkout_root)
    _run_git(["apply", str(patch_path)], cwd=checkout_root)


def _has_effective_diff(checkout_root: Path) -> bool:
    """Return whether the temp checkout changed after patch apply."""

    process = _run_git(["status", "--short"], cwd=checkout_root, check=False)
    if process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown git failure"
        raise InfraFlakeError(f"git status failed after patch apply: {stderr}")
    return bool(process.stdout.strip())


def _command_to_request(command: str) -> SandboxRequest:
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
    return SandboxRequest(binary=binary, args=tuple(argv[1:]), cwd=".")


def _classify_oracle_failure(result: sandbox.SandboxResult) -> str:
    """Map a non-zero oracle result to the canonical PR3 failure classes."""

    if result.timed_out:
        return "timeout"
    combined_output = f"{result.stdout}\n{result.stderr}".lower()
    if any(marker in combined_output for marker in OOM_MARKERS):
        return "oom"
    return "guard_failure"


def _run_oracles(
    packet: dict[str, Any], checkout_root: Path
) -> tuple[list[dict[str, Any]], str | None]:
    """Execute immutable oracle commands in the isolated sandbox root."""

    oracle_results: list[dict[str, Any]] = []
    failure_class: str | None = None
    requests = [_command_to_request(oracle["command"]) for oracle in packet["immutable_oracles"]]
    allowed_binaries = tuple(sorted({request.binary for request in requests}))
    total_wall_clock_seconds = int(packet["budgets"]["wall_clock_seconds"])
    started_at = time.monotonic()

    for oracle, request in zip(packet["immutable_oracles"], requests, strict=True):
        remaining_seconds = total_wall_clock_seconds - (time.monotonic() - started_at)
        if remaining_seconds < 1:
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
        ):
            try:
                result = sandbox.run_local_sandbox(
                    request,
                    allowlist={("sandbox.exec", "local://sandbox")},
                )
            except Exception as exc:
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

    if not raw_output:
        return (RESULT_ARTIFACT_DIR / f"{experiment_id}.json").resolve()

    candidate = Path(raw_output)
    if not candidate.is_absolute():
        candidate = (RESULT_ARTIFACT_DIR / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(RESULT_ARTIFACT_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/experiments/results"
        ) from exc
    return candidate


def evaluate_candidate(packet: dict[str, Any], candidate_patch_path: Path) -> dict[str, Any]:
    """Evaluate a candidate patch against a validated experiment packet."""

    candidate_patch_ref = normalize_repo_path(candidate_patch_path.resolve())
    shared_status_before = _shared_tree_status(REPO_ROOT)
    patch_text = _read_patch_text(candidate_patch_path)
    budget_observations = {
        "configured_budgets": dict(packet["budgets"]),
        "stop_condition": packet["budgets"].get("stop_condition", DEFAULT_STOP_CONDITION),
        "oracle_commands_configured": len(packet["immutable_oracles"]),
        "oracle_commands_executed": 0,
        "candidate_changed_files": 0,
    }

    try:
        mutated_paths = _extract_mutated_paths(patch_text)
        budget_observations["candidate_changed_files"] = len(mutated_paths)
        if not mutated_paths:
            result = _result_payload(
                experiment_id=packet["experiment_id"],
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

        temp_dir, checkout_root = _create_temp_checkout(REPO_ROOT)
        try:
            _apply_candidate_patch(checkout_root, candidate_patch_path)
            if not _has_effective_diff(checkout_root):
                result = _result_payload(
                    experiment_id=packet["experiment_id"],
                    candidate_patch=candidate_patch_ref,
                    status="rejected",
                    failure_class="unchanged_result",
                    mutated_paths=mutated_paths,
                    oracle_results=[],
                    budget_observations=budget_observations,
                    shared_tree_untouched=True,
                )
                return result

            oracle_results, failure_class = _run_oracles(packet, checkout_root)
            budget_observations["oracle_commands_executed"] = len(oracle_results)
            status = "accepted" if failure_class is None else "rejected"
            result = _result_payload(
                experiment_id=packet["experiment_id"],
                candidate_patch=candidate_patch_ref,
                status=status,
                failure_class=failure_class,
                mutated_paths=mutated_paths,
                oracle_results=oracle_results,
                budget_observations=budget_observations,
                shared_tree_untouched=True,
            )
        finally:
            temp_dir.cleanup()
    except PolicyViolationError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            candidate_patch=candidate_patch_ref,
            status="rejected",
            failure_class="policy_violation",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=True,
        )
    except InfraFlakeError as exc:
        budget_observations["runner_error"] = str(exc)
        result = _result_payload(
            experiment_id=packet["experiment_id"],
            candidate_patch=candidate_patch_ref,
            status="rejected",
            failure_class="infra_flake",
            mutated_paths=[],
            oracle_results=[],
            budget_observations=budget_observations,
            shared_tree_untouched=True,
        )

    shared_status_after = _shared_tree_status(REPO_ROOT)
    if shared_status_before != shared_status_after:
        result["shared_tree_untouched"] = False
        result["status"] = "rejected"
        result["failure_class"] = "infra_flake"
        result["budget_observations"]["runner_error"] = "Shared working tree changed during run."
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="experiment_runner",
        description="Evaluate a candidate patch inside the governed experimentation lane.",
    )
    parser.add_argument("--packet", required=True, help="Experiment packet JSON path.")
    parser.add_argument("--candidate-patch", required=True, help="Unified diff patch path.")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional result JSON path under artifacts/orchestration/experiments/results/. "
            "Defaults to artifacts/orchestration/experiments/results/<id>.json"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    packet_path = Path(args.packet).expanduser().resolve()
    candidate_patch_path = Path(args.candidate_patch).expanduser().resolve()

    try:
        packet = validate_experiment_packet(_read_json_object(packet_path))
        output_path = _resolve_output_path(args.output, packet["experiment_id"])
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

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

    try:
        output_ref = str(output_path.relative_to(REPO_ROOT))
    except ValueError:
        output_ref = str(output_path)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "failure_class": result["failure_class"],
                "output": output_ref,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
