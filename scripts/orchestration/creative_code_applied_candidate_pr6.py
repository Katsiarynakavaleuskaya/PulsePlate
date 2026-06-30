"""PR-6 local run-plan wrapper for the first applied creative-code candidate.

This CLI validates a PR-5 repair launch packet and emits a deterministic local
checklist for the existing PR-1 -> PR-2 -> PR-3 -> PR-4 tools. It does not run
patch generation, create branches, open PRs, call providers, edit review
mapping, resolve threads, or claim merge readiness.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence, cast

from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from scripts.orchestration.creative_code_review_disposition_contract import (
    CreativeCodeReviewDispositionContractError,
    read_json_object,
    reject_unsafe_review_value,
    validate_creative_code_repair_launch_packet,
)
from scripts.orchestration.experiment_contract import validate_mutable_candidate_surface

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
APPLIED_CANDIDATES_ROOT = CREATIVE_CODE_ROOT / "applied_candidates"

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "creative_code_applied_candidate_run_plan"
POLICY_VERSION = "creative-code-applied-candidate-pr6"
DEFAULT_TARGET_SURFACE = "docs/prompts/cv/program.md"
DEFAULT_CANDIDATE_ID = "cv-program-offline-eval-001"
RUN_PLAN_FILE = "run_plan.json"

SUCCESS_VALIDATE_OUTPUT = "PASS: creative-code applied candidate launch valid"
SUCCESS_PLAN_OUTPUT = "PASS: creative-code applied candidate run plan complete"
SUCCESS_SUMMARY_OUTPUT = "PASS: creative-code applied candidate summary complete"

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
RUN_PLAN_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "run_plan_id",
        "idempotency_key",
        "policy_version",
        "candidate_id",
        "source_launch_packet_id",
        "source_launch_packet_fingerprint",
        "source_disposition_packet_id",
        "target_surface",
        "target_surface_policy",
        "candidate_limits",
        "allowed_next_steps",
        "expected_artifacts",
        "commands",
        "authority",
        "lifecycle_checkpoints",
        "sanitized",
    }
)

WRAPPER_TRUE_AUTHORITY_KEYS = frozenset(
    {
        "validate_launch_packet",
        "emit_run_plan",
        "launch_pr1_specification",
    }
)
WRAPPER_FALSE_AUTHORITY_KEYS = frozenset(
    {
        "generate_patch",
        "write_branch",
        "push",
        "open_pr",
        "resolve_threads",
        "edit_fixed_mapping",
        "claim_merge_readiness",
        "merge",
        "call_provider",
        "call_product_runtime",
        "read_secrets",
        "modify_github_app",
        "modify_slack",
        "modify_workflows",
        "use_semantic_cache",
    }
)


class CreativeCodeAppliedCandidatePR6Error(ValueError):
    """Raised when the PR-6 local run-plan wrapper fails closed."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodeAppliedCandidatePR6Error(f"{label} must not traverse symlinks.")


def _ensure_applied_candidates_root() -> Path:
    _reject_symlink_components(APPLIED_CANDIDATES_ROOT, label="applied candidate root")
    try:
        APPLIED_CANDIDATES_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodeAppliedCandidatePR6Error(
            "applied candidate root could not be created."
        ) from exc
    _reject_symlink_components(APPLIED_CANDIDATES_ROOT, label="applied candidate root")
    root = APPLIED_CANDIDATES_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodeAppliedCandidatePR6Error("applied candidate root must be a directory.")
    return root


def _normalize_candidate_id(raw_candidate_id: str) -> str:
    candidate_id = raw_candidate_id.strip()
    if not candidate_id or not SAFE_ID_RE.fullmatch(candidate_id):
        raise CreativeCodeAppliedCandidatePR6Error("candidate_id must be a safe identifier.")
    return candidate_id


def _normalize_target_surface(raw_target: str) -> str:
    target = raw_target.strip()
    if target != DEFAULT_TARGET_SURFACE:
        raise CreativeCodeAppliedCandidatePR6Error(
            f"target surface must be exactly {DEFAULT_TARGET_SURFACE}."
        )
    try:
        normalized = cast(list[str], validate_mutable_candidate_surface([target]))
    except ValueError as exc:
        raise CreativeCodeAppliedCandidatePR6Error(str(exc)) from exc
    if normalized != [DEFAULT_TARGET_SURFACE]:
        raise CreativeCodeAppliedCandidatePR6Error(
            f"target surface must normalize to {DEFAULT_TARGET_SURFACE}."
        )
    return normalized[0]


def _artifact_path_for_output_dir(raw_output_dir: Path, *, create: bool) -> Path:
    root = _ensure_applied_candidates_root()
    if raw_output_dir.is_absolute():
        candidate = raw_output_dir
    elif raw_output_dir.parts[:4] == (
        "artifacts",
        "orchestration",
        "creative_code",
        "applied_candidates",
    ):
        candidate = REPO_ROOT / raw_output_dir
    else:
        candidate = APPLIED_CANDIDATES_ROOT / raw_output_dir
    _reject_symlink_components(candidate, label="applied candidate directory")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, root):
        raise CreativeCodeAppliedCandidatePR6Error(
            "output directory must stay under applied candidate artifacts."
        )
    if create:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CreativeCodeAppliedCandidatePR6Error(
                "output directory could not be created."
            ) from exc
        _reject_symlink_components(candidate, label="applied candidate directory")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeAppliedCandidatePR6Error("output directory must exist.") from exc
    if not _is_relative_to(resolved, root) or not resolved.is_dir():
        raise CreativeCodeAppliedCandidatePR6Error(
            "output directory must stay under applied candidate artifacts."
        )
    return resolved


def _resolve_run_plan_file(raw_path: Path) -> Path:
    root = _ensure_applied_candidates_root()
    path = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(path.parent, label="run plan parent")
    parent = path.parent.resolve(strict=False)
    if not _is_relative_to(parent, root):
        raise CreativeCodeAppliedCandidatePR6Error(
            "run plan path must stay under applied candidate artifacts."
        )
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeAppliedCandidatePR6Error("run plan parent must exist.") from exc
    if path.name != RUN_PLAN_FILE:
        raise CreativeCodeAppliedCandidatePR6Error(f"run plan filename must be {RUN_PLAN_FILE}.")
    if path.exists() or path.is_symlink():
        if path.is_symlink():
            raise CreativeCodeAppliedCandidatePR6Error("run plan file must not be a symlink.")
        if not path.is_file():
            raise CreativeCodeAppliedCandidatePR6Error("run plan path must be a file.")
    return resolved_parent / path.name


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    reject_unsafe_review_value(dict(payload), label="run_plan")
    output = _resolve_run_plan_file(path)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _validate_launch_authority(launch_packet: Mapping[str, Any]) -> None:
    authority = launch_packet.get("authority")
    if not isinstance(authority, Mapping):
        raise CreativeCodeAppliedCandidatePR6Error("launch authority must be an object.")
    if authority.get("create_pr1_specification") is not True:
        raise CreativeCodeAppliedCandidatePR6Error(
            "launch packet must set create_pr1_specification=true."
        )
    for key, value in sorted(authority.items()):
        if key == "create_pr1_specification":
            continue
        if value is not False:
            raise CreativeCodeAppliedCandidatePR6Error(f"launch authority {key} must remain false.")


def _validate_launch_packet(launch_packet: Mapping[str, Any]) -> dict[str, Any]:
    try:
        normalized = cast(
            dict[str, Any],
            validate_creative_code_repair_launch_packet(launch_packet),
        )
    except CreativeCodeReviewDispositionContractError as exc:
        raise CreativeCodeAppliedCandidatePR6Error(str(exc)) from exc
    _validate_launch_authority(normalized)
    target_pr1 = normalized["target_pr1_specification"]
    if target_pr1["allowed"] is not True:
        raise CreativeCodeAppliedCandidatePR6Error(
            "launch packet must allow a PR-1 specification target."
        )
    if not normalized["repair_candidates"]:
        raise CreativeCodeAppliedCandidatePR6Error(
            "launch packet must include at least one repair candidate."
        )
    reject_unsafe_review_value(normalized, label="launch_packet")
    return normalized


def load_and_validate_launch_packet(path: Path, *, target: str) -> dict[str, Any]:
    """Read and validate a PR-5 launch packet for the PR-6 target surface."""

    try:
        launch_packet = read_json_object(path)
    except CreativeCodeReviewDispositionContractError as exc:
        raise CreativeCodeAppliedCandidatePR6Error(str(exc)) from exc
    _normalize_target_surface(target)
    return _validate_launch_packet(launch_packet)


def _command(label: str, command: str) -> dict[str, Any]:
    reject_unsafe_review_value(command, label=f"command.{label}")
    return {
        "label": label,
        "command": command,
        "checklist_only": True,
        "executes_in_wrapper": False,
    }


def _module_command(module: str, args: Sequence[str]) -> str:
    joined_args = " ".join(args)
    return f"<repo-python> -m {module} {joined_args}".strip()


def _commands(candidate_id: str) -> dict[str, list[dict[str, Any]]]:
    spec_run_dir = f"spec_runs/{candidate_id}"
    patch_run_id = f"{candidate_id}-patch"
    promotion_id = f"{candidate_id}-promotion"
    return {
        "pr1_specification": [
            _command(
                "prepare_specification",
                _module_command(
                    "scripts.orchestration.creative_code_spec_pipeline",
                    [
                        "prepare",
                        "--packet",
                        f"artifacts/orchestration/creative_code/applied_candidates/{candidate_id}/candidate_packet.json",
                        "--run-dir",
                        spec_run_dir,
                    ],
                ),
            ),
            _command(
                "record_skeptic_review_decisions",
                (
                    "manual: record complete PR-1 skeptic review decisions in "
                    f"artifacts/orchestration/creative_code/spec_runs/{candidate_id}/"
                    "skeptic_reviews.json before finalize"
                ),
            ),
            _command(
                "finalize_specification",
                _module_command(
                    "scripts.orchestration.creative_code_spec_pipeline",
                    [
                        "finalize",
                        "--run-dir",
                        spec_run_dir,
                        "--output",
                        f"spec_runs/{candidate_id}/bundle.json",
                    ],
                ),
            ),
        ],
        "pr2_patch_builder": [
            _command(
                "prepare_patch_request",
                _module_command(
                    "scripts.orchestration.creative_code_patch_builder",
                    [
                        "prepare",
                        "--spec-bundle",
                        f"artifacts/orchestration/creative_code/spec_runs/{candidate_id}/bundle.json",
                        "--request",
                        f"artifacts/orchestration/creative_code/applied_candidates/{candidate_id}/patch_request.json",
                        "--run-dir",
                        patch_run_id,
                    ],
                ),
            ),
            _command(
                "generate_patch_candidate",
                _module_command(
                    "scripts.orchestration.creative_code_patch_builder",
                    ["generate", "--run-dir", patch_run_id],
                ),
            ),
            _command(
                "evaluate_patch_candidate",
                _module_command(
                    "scripts.orchestration.creative_code_patch_builder",
                    ["evaluate", "--run-dir", patch_run_id],
                ),
            ),
        ],
        "pr3_promotion": [
            _command(
                "plan_promotion",
                _module_command(
                    "scripts.orchestration.creative_code_pr_promotion",
                    ["plan", "--patch-run", patch_run_id, "--promotion-id", promotion_id],
                ),
            ),
            _command(
                "validate_promotion",
                _module_command(
                    "scripts.orchestration.creative_code_pr_promotion",
                    ["validate", "--promotion-id", promotion_id],
                ),
            ),
            _command(
                "approve_promotion",
                _module_command(
                    "scripts.orchestration.creative_code_pr_promotion",
                    [
                        "approve",
                        "--promotion-id",
                        promotion_id,
                        "--approved-by-login",
                        "Katsiarynakavaleuskaya",
                    ],
                ),
            ),
            _command(
                "promote_non_draft_pr",
                _module_command(
                    "scripts.orchestration.creative_code_pr_promotion",
                    ["promote", "--promotion-id", promotion_id],
                ),
            ),
        ],
        "pr4_telemetry": [
            _command(
                "collect_telemetry",
                _module_command(
                    "scripts.orchestration.creative_code_telemetry",
                    [
                        "--spec-runs-dir",
                        f"artifacts/orchestration/creative_code/spec_runs/{candidate_id}",
                        "--patch-runs-dir",
                        f"artifacts/orchestration/creative_code/patch_runs/{patch_run_id}",
                        "--promotions-dir",
                        f"artifacts/orchestration/creative_code/promotions/{promotion_id}",
                        "--output-dir",
                        "artifacts/orchestration/creative_code/telemetry",
                        "--strict",
                    ],
                ),
            ),
        ],
    }


def _expected_artifacts(candidate_id: str) -> dict[str, str]:
    patch_run_id = f"{candidate_id}-patch"
    promotion_id = f"{candidate_id}-promotion"
    return {
        "pr1_source_candidate_packet": (
            f"artifacts/orchestration/creative_code/applied_candidates/{candidate_id}/"
            "candidate_packet.json"
        ),
        "pr1_specification_bundle": (
            f"artifacts/orchestration/creative_code/spec_runs/{candidate_id}/bundle.json"
        ),
        "pr2_patch_request": (
            f"artifacts/orchestration/creative_code/applied_candidates/{candidate_id}/"
            "patch_request.json"
        ),
        "pr2_patch_result": (
            f"artifacts/orchestration/creative_code/patch_runs/{patch_run_id}/result.json"
        ),
        "pr3_promotion_receipt": (
            "artifacts/orchestration/creative_code/promotions/"
            f"{promotion_id}/promotion_receipt.json"
        ),
        "pr4_telemetry_rollup": (
            "artifacts/orchestration/creative_code/telemetry/creative_code_telemetry_rollup.json"
        ),
    }


def _run_plan_identity(plan: Mapping[str, Any]) -> tuple[str, str]:
    payload = {key: plan[key] for key in sorted(RUN_PLAN_KEYS - {"run_plan_id", "idempotency_key"})}
    fingerprint = fingerprint_payload(payload)
    upstream_ids = (
        str(plan["candidate_id"]),
        str(plan["source_launch_packet_id"]),
        str(plan["source_launch_packet_fingerprint"]),
    )
    run_plan_id = build_asset_id(
        asset_type=ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return run_plan_id, idempotency_key


def build_run_plan(
    *,
    launch_packet: Mapping[str, Any],
    target: str,
    candidate_id: str = DEFAULT_CANDIDATE_ID,
) -> dict[str, Any]:
    """Build a sanitized local PR-6 run plan without executing any commands."""

    normalized_launch = _validate_launch_packet(launch_packet)
    normalized_target = _normalize_target_surface(target)
    normalized_candidate_id = _normalize_candidate_id(candidate_id)
    launch_fingerprint = fingerprint_payload(normalized_launch)
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "run_plan_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "candidate_id": normalized_candidate_id,
        "source_launch_packet_id": normalized_launch["launch_id"],
        "source_launch_packet_fingerprint": launch_fingerprint,
        "source_disposition_packet_id": normalized_launch["source_disposition_packet_id"],
        "target_surface": [normalized_target],
        "target_surface_policy": {
            "required_exact_target": DEFAULT_TARGET_SURFACE,
            "validated_by": "validate_mutable_candidate_surface",
            "generated_candidate_may_modify_scripts_orchestration": False,
            "generated_candidate_may_modify_tests": False,
            "generated_candidate_may_modify_governance_docs": False,
        },
        "candidate_limits": {
            "allowed_existing_paths": [normalized_target],
            "allowed_new_paths": [],
            "generation_attempts": 1,
            "max_changed_files": 1,
            "max_diff_lines": 120,
            "max_patch_bytes": 65536,
            "network_budget": 0,
            "negative_controls_minimum": 2,
            "primary_metric_required": True,
        },
        "allowed_next_steps": {
            "run_pr1_specification": True,
            "prepare_pr2_patch_request": True,
            "run_pr2_patch_builder": True,
            "run_pr3_promotion": True,
            "run_pr4_telemetry": True,
        },
        "expected_artifacts": _expected_artifacts(normalized_candidate_id),
        "commands": _commands(normalized_candidate_id),
        "authority": {
            **{key: True for key in sorted(WRAPPER_TRUE_AUTHORITY_KEYS)},
            **{key: False for key in sorted(WRAPPER_FALSE_AUTHORITY_KEYS)},
        },
        "lifecycle_checkpoints": [
            "wrapper_bootstrap",
            "pr1_specification_bundle",
            "pr2_accepted_patch_result",
            "pr3_non_draft_experiment_pr",
            "normal_pr_governance",
            "telemetry_closeout",
        ],
        "sanitized": True,
    }
    run_plan_id, idempotency_key = _run_plan_identity(plan)
    plan["run_plan_id"] = run_plan_id
    plan["idempotency_key"] = idempotency_key
    return validate_run_plan(plan)


def validate_run_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a PR-6 run plan produced by this wrapper."""

    actual_keys = set(payload)
    missing = sorted(RUN_PLAN_KEYS - actual_keys)
    extra = sorted(actual_keys - RUN_PLAN_KEYS)
    if missing:
        raise CreativeCodeAppliedCandidatePR6Error(
            f"run plan is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodeAppliedCandidatePR6Error(
            f"run plan has unsupported fields: {', '.join(extra)}"
        )
    schema_version = payload["schema_version"]
    artifact_type = payload["artifact_type"]
    policy_version = payload["policy_version"]
    if schema_version != SCHEMA_VERSION:
        raise CreativeCodeAppliedCandidatePR6Error("run plan schema_version is unsupported.")
    if artifact_type != ARTIFACT_TYPE:
        raise CreativeCodeAppliedCandidatePR6Error("run plan artifact_type is unsupported.")
    if policy_version != POLICY_VERSION:
        raise CreativeCodeAppliedCandidatePR6Error("run plan policy_version is unsupported.")
    candidate_id = _normalize_candidate_id(cast(str, payload["candidate_id"]))
    target_surface = payload["target_surface"]
    if target_surface != [DEFAULT_TARGET_SURFACE]:
        raise CreativeCodeAppliedCandidatePR6Error(
            f"run plan target_surface must be [{DEFAULT_TARGET_SURFACE!r}]."
        )
    authority = payload["authority"]
    if not isinstance(authority, Mapping):
        raise CreativeCodeAppliedCandidatePR6Error("run plan authority must be an object.")
    for key in WRAPPER_TRUE_AUTHORITY_KEYS:
        if authority.get(key) is not True:
            raise CreativeCodeAppliedCandidatePR6Error(f"run plan authority {key} must be true.")
    for key in WRAPPER_FALSE_AUTHORITY_KEYS:
        if authority.get(key) is not False:
            raise CreativeCodeAppliedCandidatePR6Error(f"run plan authority {key} must be false.")
    commands = payload["commands"]
    if not isinstance(commands, Mapping):
        raise CreativeCodeAppliedCandidatePR6Error("run plan commands must be an object.")
    for phase, rows in commands.items():
        if not isinstance(phase, str) or not isinstance(rows, list) or not rows:
            raise CreativeCodeAppliedCandidatePR6Error("run plan command phases are invalid.")
        for row in rows:
            if not isinstance(row, Mapping):
                raise CreativeCodeAppliedCandidatePR6Error("run plan command rows are invalid.")
            if row.get("checklist_only") is not True or row.get("executes_in_wrapper") is not False:
                raise CreativeCodeAppliedCandidatePR6Error(
                    "run plan commands must be checklist-only."
                )
    if payload["sanitized"] is not True:
        raise CreativeCodeAppliedCandidatePR6Error("run plan sanitized must be true.")
    reject_unsafe_review_value(cast(dict[str, Any], dict(payload)), label="run_plan")
    expected_id, expected_idempotency_key = _run_plan_identity(payload)
    if payload["run_plan_id"] != expected_id:
        raise CreativeCodeAppliedCandidatePR6Error("run_plan_id does not match run plan content.")
    if payload["idempotency_key"] != expected_idempotency_key:
        raise CreativeCodeAppliedCandidatePR6Error(
            "idempotency_key does not match run plan content."
        )
    normalized = dict(payload)
    normalized["candidate_id"] = candidate_id
    return normalized


def write_run_plan(
    *,
    run_plan: Mapping[str, Any],
    output_dir: Path,
) -> Path:
    """Write the run plan under the local applied-candidate artifact root."""

    resolved_dir = _artifact_path_for_output_dir(output_dir, create=True)
    output = resolved_dir / RUN_PLAN_FILE
    _write_json_atomic(output, validate_run_plan(run_plan))
    return output


def read_run_plan(path: Path) -> dict[str, Any]:
    """Read and validate a previously emitted run plan."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeAppliedCandidatePR6Error("Unable to read run plan JSON.") from exc
    if not isinstance(payload, dict):
        raise CreativeCodeAppliedCandidatePR6Error("run plan must be a JSON object.")
    return validate_run_plan(payload)


def summarize_run_plan(run_plan: Mapping[str, Any]) -> str:
    """Return a concise safe summary for operator handoff."""

    normalized = validate_run_plan(run_plan)
    lines = [
        f"candidate_id: {normalized['candidate_id']}",
        f"target_surface: {', '.join(normalized['target_surface'])}",
        "wrapper_authority: validate launch packet and emit run plan only",
        "candidate_limits: one existing file, no new files, no network budget",
        "next_steps: PR-1 specification, PR-2 patch builder, PR-3 promotion, PR-4 telemetry",
        "merge_readiness: not claimed",
    ]
    summary = "\n".join(lines)
    reject_unsafe_review_value(summary, label="run_plan_summary")
    return summary


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and plan the first PR-6 applied creative-code candidate."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-launch")
    validate_parser.add_argument("--launch-packet", type=Path, required=True)
    validate_parser.add_argument("--target", default=DEFAULT_TARGET_SURFACE)

    plan_parser = subparsers.add_parser("plan-run")
    plan_parser.add_argument("--launch-packet", type=Path, required=True)
    plan_parser.add_argument("--target", default=DEFAULT_TARGET_SURFACE)
    plan_parser.add_argument("--candidate-id", default=DEFAULT_CANDIDATE_ID)
    plan_parser.add_argument("--output-dir", type=Path, default=None)

    summarize_parser = subparsers.add_parser("summarize")
    summarize_parser.add_argument("--run-plan", type=Path, required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "validate-launch":
            load_and_validate_launch_packet(args.launch_packet, target=args.target)
            print(SUCCESS_VALIDATE_OUTPUT)
            return 0
        if args.command == "plan-run":
            launch_packet = load_and_validate_launch_packet(args.launch_packet, target=args.target)
            run_plan = build_run_plan(
                launch_packet=launch_packet,
                target=args.target,
                candidate_id=args.candidate_id,
            )
            output_dir = args.output_dir or Path(args.candidate_id)
            output = write_run_plan(run_plan=run_plan, output_dir=output_dir)
            print(f"{SUCCESS_PLAN_OUTPUT}: {output.relative_to(REPO_ROOT).as_posix()}")
            return 0
        if args.command == "summarize":
            print(summarize_run_plan(read_run_plan(args.run_plan)))
            print(SUCCESS_SUMMARY_OUTPUT)
            return 0
        raise CreativeCodeAppliedCandidatePR6Error("unsupported command.")
    except CreativeCodeAppliedCandidatePR6Error as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
