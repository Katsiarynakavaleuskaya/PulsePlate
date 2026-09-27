#!/usr/bin/env python3
"""Local Experiment Runner PR creative-context CLI.

The CLI emits sanitized local artifacts only. It does not call providers, read
raw PR/review bodies, dispatch workflows, create branches, open PRs, edit fixed
mapping, resolve threads, or claim merge readiness.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import zipfile
import zlib
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    AGENT_ROUTING_TYPE,
    APPROVAL_TYPE,
    COORDINATOR_DISPATCH_TYPE,
    CONTEXT_MAP_TYPE,
    CONSUMPTION_SUMMARY_TYPE,
    HYPOTHESIS_PACKET_TYPE,
    ORACLE_ATTACHMENT_TYPE,
    OPERATOR_MODEL_INTAKE_TYPE,
    CREATIVE_WORKFLOW_SCHEMA_VERSION,
    SECRET_VALUE_RE,
    contains_local_path_outside_route_context,
    ExperimentRunnerCreativeContextContractError,
    build_agent_consumption_summary,
    build_creative_workflow_stage,
    build_creative_hypothesis_coordinator_dispatch,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_packet,
    build_creative_hypothesis_packet_from_model_intake,
    build_creative_protocol_context_map,
    build_experiment_runner_pr_oracle_attachment,
    read_json_object,
    reject_unsafe_creative_context_value,
    validate_artifact_by_type,
    validate_creative_hypothesis_agent_routing,
    validate_creative_hypothesis_operator_model_intake,
    validate_creative_hypothesis_packet,
    validate_creative_protocol_context_map,
    validate_experiment_runner_pr_oracle_attachment,
    validate_creative_workflow_request,
    validate_creative_workflow_native_result,
    validate_creative_workflow_review,
    validate_creative_workflow_handoff,
    validate_creative_workflow_stage,
    workflow_fingerprint,
)

from scripts.orchestration.evidence_rail_applicability import (
    read_task_packet_snapshot,
    EvidenceRailApplicabilityError,
    build_evidence_rail_applicability,
    RailTreatment,
)
from scripts.orchestration.creative_code_patch_workspace import (
    CreativeCodePatchWorkspaceError,
    run_git,
)
from scripts.orchestration import qoder_dispatch_bridge

ARCHIVE_SECRET_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|xox[abprs]-[A-Za-z0-9-]{12,})\b|"
    r"authorization:\s*bearer[ \t]+\S+|"
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----",
    re.IGNORECASE,
)

CREATIVE_CONTEXT_ROOT = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "creative_context"
)
ALLOWED_OUTPUT_FILENAMES = frozenset(
    {
        "context_map.json",
        "hypothesis_packet.json",
        "model_intake.json",
        "agent_routing.json",
        "agent_consumption_summary.json",
        "coordinator_dispatch.json",
        "oracle_attachment.json",
        "approval.json",
        "creative_context.json",
    }
)
WORKFLOW_STAGE_FILES = {
    "prepared": "workflow.prepared.json",
    "returned": "workflow.returned.json",
    "validated": "workflow.validated.json",
    "reviewed": "workflow.reviewed.json",
    "admitted": "workflow.admitted.json",
}
WORKFLOW_ARCHIVE_FILES = frozenset(
    {
        *WORKFLOW_STAGE_FILES.values(),
        "patch.diff",
        "test_evidence.json",
        "oracle_evidence.json",
        "work_review.md",
    }
)
MAX_WORKFLOW_JSON_BYTES = 262_144
MAX_WORKFLOW_ARCHIVE_BYTES = 1_048_576
MAX_WORKFLOW_MANIFEST_BYTES = 2_000_000
SUCCESS_PREPARE_OUTPUT = "PASS: experiment-runner creative-context artifacts prepared"


class ExperimentRunnerCreativeContextCliError(ValueError):
    """Raised when the CLI cannot safely complete."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
            raise ExperimentRunnerCreativeContextCliError(f"{label} must not traverse symlinks.")


def _ensure_creative_context_root() -> Path:
    _reject_symlink_components(CREATIVE_CONTEXT_ROOT, label="creative context root")
    CREATIVE_CONTEXT_ROOT.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(CREATIVE_CONTEXT_ROOT, label="creative context root")
    root = CREATIVE_CONTEXT_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise ExperimentRunnerCreativeContextCliError("creative context root must be a directory.")
    return root


def _resolve_output_dir(raw_output_dir: Path | None, *, create: bool) -> Path:
    root = _ensure_creative_context_root()
    if raw_output_dir is None:
        return root
    if raw_output_dir.is_absolute():
        candidate = raw_output_dir
    elif raw_output_dir.parts[:4] == (
        "artifacts",
        "orchestration",
        "experiments",
        "creative_context",
    ):
        candidate = REPO_ROOT / raw_output_dir
    else:
        candidate = root / raw_output_dir
    _reject_symlink_components(candidate, label="creative context output directory")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, root):
        raise ExperimentRunnerCreativeContextCliError(
            "output directory must stay under creative context artifacts."
        )
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(candidate, label="creative context output directory")
    resolved = candidate.resolve(strict=True)
    if not _is_relative_to(resolved, root) or not resolved.is_dir():
        raise ExperimentRunnerCreativeContextCliError(
            "output directory must stay under creative context artifacts."
        )
    return resolved


def _resolve_json_output(raw_path: Path) -> Path:
    root = _ensure_creative_context_root()
    if raw_path.name not in ALLOWED_OUTPUT_FILENAMES:
        allowed = ", ".join(sorted(ALLOWED_OUTPUT_FILENAMES))
        raise ExperimentRunnerCreativeContextCliError(f"output filename must be one of: {allowed}.")
    if raw_path.is_absolute():
        candidate = raw_path
    elif raw_path.parts[:4] == ("artifacts", "orchestration", "experiments", "creative_context"):
        candidate = REPO_ROOT / raw_path
    else:
        candidate = root / raw_path
    _reject_symlink_components(candidate.parent, label="creative context output parent")
    parent = candidate.parent.resolve(strict=False)
    if not _is_relative_to(parent, root):
        raise ExperimentRunnerCreativeContextCliError(
            "output path must stay under creative context artifacts."
        )
    candidate.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(candidate.parent, label="creative context output parent")
    resolved_parent = candidate.parent.resolve(strict=True)
    if not _is_relative_to(resolved_parent, root):
        raise ExperimentRunnerCreativeContextCliError(
            "output path must stay under creative context artifacts."
        )
    if candidate.exists() or candidate.is_symlink():
        if candidate.is_symlink():
            raise ExperimentRunnerCreativeContextCliError("output file must not be a symlink.")
        if not candidate.is_file():
            raise ExperimentRunnerCreativeContextCliError("output path must be a regular file.")
    return resolved_parent / candidate.name


def _write_json(path: Path | None, payload: Mapping[str, Any]) -> None:
    reject_unsafe_creative_context_value(dict(payload), label="output")
    if path is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    output = _resolve_json_output(path)
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


def _artifact_subdir(context_map: Mapping[str, Any]) -> Path:
    context_id = str(context_map["context_id"])
    leaf = context_id.rsplit(":", maxsplit=1)[-1]
    return _resolve_output_dir(Path(leaf), create=True)


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _common_context_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "changed_paths": args.changed_path,
        "repository": args.repository,
        "pr_number": args.pr_number,
        "base_ref": args.base_ref,
        "base_sha": args.base_sha,
        "head_sha": args.head_sha,
        "task_packet_id": args.task_packet_id,
        "generated_at_utc": args.generated_at_utc or _utc_now(),
        "nearby_repo_refs": args.nearby_repo_ref,
        "test_refs": args.test_ref,
        "contract_refs": args.contract_ref,
        "backlog_refs": args.backlog_ref,
        "review_source_refs": args.review_source_ref,
        "capability_state_ref": args.capability_state_ref,
        "philosophical_context_refs": args.philosophical_context_ref,
        "cross_domain_candidate_refs": args.cross_domain_candidate_ref,
        "label_enabled": args.label_enabled,
        "marker_enabled": args.marker_enabled,
        "manual_enabled": args.manual_enabled,
        "sealed_codex_security_scan_ref": args.sealed_codex_security_scan_ref,
        "sealed_codex_security_scan_fingerprint": args.sealed_codex_security_scan_fingerprint,
        "security_relevant_diff_changed": args.security_relevant_diff_changed,
    }


def _cmd_collect_context(args: argparse.Namespace) -> int:
    context_map = build_creative_protocol_context_map(**_common_context_kwargs(args))
    _write_json(Path(args.output) if args.output else None, context_map)
    return 0


def _cmd_generate_hypotheses(args: argparse.Namespace) -> int:
    context_map = validate_creative_protocol_context_map(read_json_object(args.context_map))
    packet = build_creative_hypothesis_packet(
        context_map,
        hypothesis_count=args.hypothesis_count,
    )
    _write_json(Path(args.output) if args.output else None, packet)
    return 0


def _cmd_route_agents(args: argparse.Namespace) -> int:
    packet = validate_creative_hypothesis_packet(read_json_object(args.hypothesis_packet))
    routing = build_creative_hypothesis_agent_routing(packet)
    _write_json(Path(args.output) if args.output else None, routing)
    return 0


def _cmd_ingest_model_hypotheses(args: argparse.Namespace) -> int:
    context_map = validate_creative_protocol_context_map(read_json_object(args.context_map))
    model_intake = validate_creative_hypothesis_operator_model_intake(
        read_json_object(args.model_intake),
        context_map=context_map,
    )
    packet = build_creative_hypothesis_packet_from_model_intake(
        context_map,
        model_intake,
    )
    _write_json(Path(args.output) if args.output else None, packet)
    normalized_intake_output = (
        Path(args.normalized_intake_output)
        if args.normalized_intake_output
        else Path(args.output).with_name("model_intake.json") if args.output else None
    )
    if normalized_intake_output is not None:
        _write_json(normalized_intake_output, model_intake)
    return 0


def _cmd_dispatch_coordinator(args: argparse.Namespace) -> int:
    packet = validate_creative_hypothesis_packet(read_json_object(args.hypothesis_packet))
    routing = validate_creative_hypothesis_agent_routing(read_json_object(args.routing))
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
    _write_json(Path(args.output) if args.output else None, dispatch)
    return 0


def _cmd_summarize(args: argparse.Namespace) -> int:
    oracle = None
    if args.oracle:
        oracle = validate_experiment_runner_pr_oracle_attachment(read_json_object(args.oracle))
    packet = validate_creative_hypothesis_packet(read_json_object(args.hypotheses))
    routing = validate_creative_hypothesis_agent_routing(read_json_object(args.routing))
    summary = build_agent_consumption_summary(
        oracle_attachment=oracle,
        hypothesis_packet=packet,
        routing=routing,
    )
    _write_json(Path(args.output) if args.output else None, summary)
    return 0


def _cmd_prepare(args: argparse.Namespace) -> int:
    context_map = (
        validate_creative_protocol_context_map(read_json_object(args.context_map))
        if args.context_map
        else build_creative_protocol_context_map(**_common_context_kwargs(args))
    )
    output_dir = (
        _resolve_output_dir(Path(args.output_dir), create=True)
        if args.output_dir
        else _artifact_subdir(context_map)
    )
    model_intake = None
    if args.model_intake:
        model_intake = validate_creative_hypothesis_operator_model_intake(
            read_json_object(args.model_intake),
            context_map=context_map,
        )
        hypothesis_packet = build_creative_hypothesis_packet_from_model_intake(
            context_map,
            model_intake,
        )
    else:
        hypothesis_packet = build_creative_hypothesis_packet(
            context_map,
            hypothesis_count=args.hypothesis_count,
        )
    agent_routing = build_creative_hypothesis_agent_routing(hypothesis_packet)
    coordinator_dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=hypothesis_packet,
        routing=agent_routing,
    )
    oracle_attachment = build_experiment_runner_pr_oracle_attachment(
        source=context_map["source"],
        oracle_status=args.oracle_status,
        result_ref=args.oracle_result_ref,
        result_fingerprint=args.oracle_result_fingerprint,
        coauthor_required=args.oracle_coauthor_required,
    )
    summary = build_agent_consumption_summary(
        oracle_attachment=oracle_attachment,
        hypothesis_packet=hypothesis_packet,
        routing=agent_routing,
    )
    _write_json(output_dir / "context_map.json", context_map)
    if model_intake is not None:
        _write_json(output_dir / "model_intake.json", model_intake)
    _write_json(output_dir / "hypothesis_packet.json", hypothesis_packet)
    _write_json(output_dir / "agent_routing.json", agent_routing)
    _write_json(output_dir / "coordinator_dispatch.json", coordinator_dispatch)
    _write_json(output_dir / "oracle_attachment.json", oracle_attachment)
    _write_json(output_dir / "agent_consumption_summary.json", summary)
    print(SUCCESS_PREPARE_OUTPUT)
    print(f"Artifact directory: {_display_path(output_dir)}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    context_map = read_json_object(args.context_path) if args.context_path else None
    payload = validate_artifact_by_type(
        args.artifact_type,
        read_json_object(args.path),
        context_map=context_map,
    )
    if args.output:
        _write_json(Path(args.output), payload)
    else:
        print("PASS: experiment-runner creative-context artifact valid")
    return 0


def _add_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--repository", default="Katsiarynakavaleuskaya/PulsePlate")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--task-packet-id")
    parser.add_argument("--generated-at-utc")
    parser.add_argument("--nearby-repo-ref", action="append", default=[])
    parser.add_argument("--test-ref", action="append", default=[])
    parser.add_argument("--contract-ref", action="append", default=[])
    parser.add_argument("--backlog-ref", action="append", default=[])
    parser.add_argument("--review-source-ref", action="append", default=[])
    parser.add_argument("--capability-state-ref")
    parser.add_argument("--philosophical-context-ref", action="append", default=[])
    parser.add_argument("--cross-domain-candidate-ref", action="append", default=[])
    parser.add_argument("--label-enabled", action="store_true")
    parser.add_argument("--marker-enabled", action="store_true")
    parser.add_argument("--manual-enabled", action="store_true")
    parser.add_argument("--sealed-codex-security-scan-ref")
    parser.add_argument("--sealed-codex-security-scan-fingerprint")
    parser.add_argument("--security-relevant-diff-changed", action="store_true")


def _workflow_json_bytes(raw: bytes, *, maximum: int = MAX_WORKFLOW_JSON_BYTES) -> dict[str, Any]:
    if not raw or len(raw) > maximum or raw.startswith(b"\xef\xbb\xbf"):
        raise ExperimentRunnerCreativeContextCliError("workflow JSON is empty or exceeds its bound")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_workflow_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        raise ExperimentRunnerCreativeContextCliError("workflow JSON is malformed") from exc
    if not isinstance(value, dict):
        raise ExperimentRunnerCreativeContextCliError("workflow JSON must be an object")
    return value


def _reject_workflow_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _safe_workflow_file(raw_path: str, *, maximum: int) -> bytes:
    path = REPO_ROOT / raw_path
    if (
        raw_path.startswith("/")
        or "\\" in raw_path
        or any(part in {"", ".", ".."} for part in raw_path.split("/"))
    ):
        raise ExperimentRunnerCreativeContextCliError("workflow source path is unsafe")
    _reject_symlink_components(path, label="workflow source")
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
                raise ExperimentRunnerCreativeContextCliError(
                    "workflow source is not an admitted regular file"
                )
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise ExperimentRunnerCreativeContextCliError("workflow source cannot be read") from exc
    if len(raw) != before.st_size or (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ExperimentRunnerCreativeContextCliError("workflow source changed during read")
    return raw


def _git_identity() -> tuple[str, str, str]:
    """Read local Git identity without invoking a shell or a remote service."""

    def query(*arguments: str) -> str:
        try:
            completed = run_git(["--no-replace-objects", *arguments], cwd=REPO_ROOT, check=False)
        except (CreativeCodePatchWorkspaceError, OSError) as exc:
            raise ExperimentRunnerCreativeContextCliError("Git identity is unavailable") from exc
        output = completed.stdout
        if completed.returncode != 0 or not isinstance(output, str) or len(output) > 512:
            raise ExperimentRunnerCreativeContextCliError("Git identity is unavailable")
        return output.strip()

    remote = query("remote", "get-url", "origin")
    matched = re.fullmatch(
        r"(?:git@github\.com:|https://github\.com/|ssh://git@github\.com/)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?",
        remote,
    )
    if matched is None:
        raise ExperimentRunnerCreativeContextCliError("Git origin repository is unsupported")
    return (
        matched.group(1),
        query("rev-parse", "--verify", "origin/main^{commit}"),
        query("rev-parse", "--verify", "HEAD^{commit}"),
    )


def _workflow_sources(request: Mapping[str, Any], *, require_current_git: bool = True) -> None:
    if require_current_git:
        repository, base_sha, head_sha = _git_identity()
        if (
            request["repository"] != repository
            or request["base_sha"] != base_sha
            or request["head_sha"] != head_sha
        ):
            raise ExperimentRunnerCreativeContextCliError("workflow Git material identity is stale")
    snapshot = read_task_packet_snapshot(
        f"artifacts/orchestration/task_packets/{request['task_packet_id']}.json"
    )
    if snapshot.task_packet_fingerprint != request["task_packet_fingerprint"]:
        raise ExperimentRunnerCreativeContextCliError("workflow task packet changed")
    if snapshot.packet.get("creative_applicability") != "alternatives":
        raise ExperimentRunnerCreativeContextCliError("workflow packet does not admit alternatives")
    treatment = next(
        row[1]
        for row in build_evidence_rail_applicability(snapshot).treatments
        if row[0] == "creative"
    )
    if treatment != RailTreatment.RECOMMEND:
        raise ExperimentRunnerCreativeContextCliError(
            "higher-assurance or disabled treatment blocks Creative"
        )
    packet_scope = snapshot.packet.get("candidate_paths")
    if not isinstance(packet_scope, tuple) or not packet_scope or "." in packet_scope:
        raise ExperimentRunnerCreativeContextCliError("task packet scope is unavailable")
    for allowed in request["allowed_paths"]:
        if allowed not in packet_scope:
            raise ExperimentRunnerCreativeContextCliError(
                "workflow allowed path is outside task packet scope"
            )
        allowed_file = REPO_ROOT / allowed
        _reject_symlink_components(allowed_file, label="workflow allowed file")
        if allowed_file.is_dir():
            raise ExperimentRunnerCreativeContextCliError(
                "workflow allowed path must name an exact file"
            )
    for path_key, hash_key in (
        ("criteria_ref", "criteria_sha256"),
        ("requirements_ref", "requirements_sha256"),
        ("euler.artifact_ref", "euler.artifact_sha256"),
    ):
        container = request["euler"] if path_key.startswith("euler.") else request
        path_name = path_key.rsplit(".", maxsplit=1)[-1]
        hash_name = hash_key.rsplit(".", maxsplit=1)[-1]
        raw = _safe_workflow_file(container[path_name], maximum=MAX_WORKFLOW_ARCHIVE_BYTES)
        if "sha256:" + hashlib.sha256(raw).hexdigest() != container[hash_name]:
            raise ExperimentRunnerCreativeContextCliError("workflow source digest changed")


def _workflow_stage_path(raw_path: str, expected: str) -> Path:
    path = Path(raw_path)
    if path.name != WORKFLOW_STAGE_FILES[expected]:
        raise ExperimentRunnerCreativeContextCliError("wrong workflow stage input")
    output_dir = _resolve_output_dir(path.parent, create=False)
    candidate = output_dir / path.name
    _reject_symlink_components(candidate, label="workflow stage")
    return candidate


class _BoundedManifestCapture(io.StringIO):
    """Keep bridge output finite without changing its canonical parser."""

    def write(self, value: str) -> int:
        if self.tell() + len(value) > MAX_WORKFLOW_MANIFEST_BYTES:
            raise ExperimentRunnerCreativeContextCliError("canonical writer manifest is oversized")
        return super().write(value)


def _canonical_manifest_writer_occurrences(
    request: Mapping[str, Any],
) -> tuple[list[str], list[tuple[int, str]]]:
    """Use the canonical role-dispatch bridge for exact runtime occurrences."""

    snapshot = read_task_packet_snapshot(
        f"artifacts/orchestration/task_packets/{request['task_packet_id']}.json"
    )
    if snapshot.task_packet_fingerprint != request["task_packet_fingerprint"]:
        raise ExperimentRunnerCreativeContextCliError("writer packet changed")
    contract = snapshot.packet.get("role_agent_dispatch_contract")
    if not isinstance(contract, Mapping):
        raise ExperimentRunnerCreativeContextCliError("writer dispatch contract is missing")
    owners = contract.get("runtime_implementation_owners")
    if not isinstance(owners, tuple) or not owners or any(not isinstance(x, str) for x in owners):
        raise ExperimentRunnerCreativeContextCliError("writer owners are missing")
    command = ["--packet", str(REPO_ROOT / snapshot.packet_path), "--mode", "runtime"]
    for owner in owners:
        command.extend(("--implementation-owner", owner))
    captured_stdout = _BoundedManifestCapture()
    captured_stderr = _BoundedManifestCapture()
    try:
        with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
            exit_code = qoder_dispatch_bridge.main(command)
    except (OSError, SystemExit, ValueError) as exc:
        raise ExperimentRunnerCreativeContextCliError(
            "canonical writer manifest unavailable"
        ) from exc
    if exit_code != 0:
        raise ExperimentRunnerCreativeContextCliError("canonical writer manifest unavailable")
    manifest = _workflow_json_bytes(
        captured_stdout.getvalue().encode("utf-8"), maximum=MAX_WORKFLOW_MANIFEST_BYTES
    )
    rows = manifest.get("dispatch_sequence")
    if (
        manifest.get("mode") != "runtime"
        or manifest.get("missing_agents") != []
        or not isinstance(rows, list)
        or not rows
    ):
        raise ExperimentRunnerCreativeContextCliError("canonical writer manifest is incomplete")
    role_order: list[str] = []
    eligible: list[tuple[int, str]] = []
    for position, row in enumerate(rows, start=1):
        if (
            not isinstance(row, dict)
            or row.get("order") != position
            or not isinstance(row.get("role_slug"), str)
        ):
            raise ExperimentRunnerCreativeContextCliError("canonical writer order is invalid")
        role = row["role_slug"]
        role_order.append(role)
        if row.get("implementation_owner_override") is True and row.get("readonly") is False:
            eligible.append((position, role))
    if not eligible or not {role for _position, role in eligible}.issubset(owners):
        raise ExperimentRunnerCreativeContextCliError("canonical writer eligibility is invalid")
    return role_order, eligible


def _require_inherited_workflow_evidence(
    stage: Mapping[str, Any], predecessor: Mapping[str, Any] | None
) -> None:
    if predecessor is None:
        return
    inherited_fields = {
        "returned": ("request", "native_result", "review", "handoff"),
        "validated": ("request", "review", "handoff", "intake_error"),
        "reviewed": ("request", "native_result", "handoff", "intake_error"),
        "admitted": ("request", "native_result", "review", "intake_error"),
    }
    if any(stage[key] != predecessor[key] for key in inherited_fields[stage["stage"]]):
        raise ExperimentRunnerCreativeContextCliError("workflow inherited evidence changed")


def _load_workflow_stage(
    raw_path: str, expected: str, *, require_current_git: bool = True
) -> dict[str, Any]:
    path = _workflow_stage_path(raw_path, expected)
    relative = path.relative_to(REPO_ROOT).as_posix()
    data: dict[str, Any] = validate_creative_workflow_stage(
        _workflow_json_bytes(_safe_workflow_file(relative, maximum=MAX_WORKFLOW_JSON_BYTES))
    )
    if data["stage"] != expected:
        raise ExperimentRunnerCreativeContextCliError("workflow stage content mismatch")
    _workflow_sources(data["request"], require_current_git=require_current_git)
    stage_names = tuple(WORKFLOW_STAGE_FILES)
    stage_position = stage_names.index(expected)
    previous = (
        None
        if stage_position == 0
        else _load_workflow_stage(
            str(path.parent / WORKFLOW_STAGE_FILES[stage_names[stage_position - 1]]),
            stage_names[stage_position - 1],
            require_current_git=require_current_git,
        )
    )
    expected_upstream = (
        workflow_fingerprint(data["request"]) if previous is None else previous["fingerprint"]
    )
    if data["upstream_assets"] != [expected_upstream]:
        raise ExperimentRunnerCreativeContextCliError("workflow stage predecessor changed")
    _require_inherited_workflow_evidence(data, previous)
    if expected == "validated" and previous is not None and previous["intake_error"] is not None:
        raise ExperimentRunnerCreativeContextCliError("invalid returned intake blocks validation")
    if expected == "admitted":
        dispatch_order, eligible = _canonical_manifest_writer_occurrences(data["request"])
        validate_creative_workflow_handoff(
            data["handoff"],
            data["request"],
            data["native_result"],
            data["review"],
            eligible,
            dispatch_order,
        )
    return data


def _write_workflow_stage(output_dir: Path, payload: Mapping[str, Any]) -> Path:
    stage_names = tuple(WORKFLOW_STAGE_FILES)
    stage_position = stage_names.index(payload["stage"])
    upstream = (
        workflow_fingerprint(payload["request"])
        if stage_position == 0
        else _load_workflow_stage(
            str(output_dir / WORKFLOW_STAGE_FILES[stage_names[stage_position - 1]]),
            stage_names[stage_position - 1],
        )["fingerprint"]
    )
    validated = build_creative_workflow_stage(payload, upstream_fingerprint=upstream)
    destination = output_dir / WORKFLOW_STAGE_FILES[validated["stage"]]
    encoded = (json.dumps(validated, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode(
        "ascii"
    )
    if len(encoded) > MAX_WORKFLOW_JSON_BYTES:
        raise ExperimentRunnerCreativeContextCliError("workflow stage exceeds its bound")
    if destination.exists() or destination.is_symlink():
        relative = destination.relative_to(REPO_ROOT).as_posix()
        if _safe_workflow_file(relative, maximum=MAX_WORKFLOW_JSON_BYTES) != encoded:
            raise ExperimentRunnerCreativeContextCliError("divergent workflow stage replay")
        return destination
    descriptor, temp_name = tempfile.mkstemp(prefix=".workflow-", dir=output_dir)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, destination, follow_symlinks=False)
    except FileExistsError as exc:
        raise ExperimentRunnerCreativeContextCliError(
            "workflow stage publication collided"
        ) from exc
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return destination


def _workflow_prepare(args: argparse.Namespace) -> int:
    request = validate_creative_workflow_request(
        _workflow_json_bytes(_safe_workflow_file(args.request, maximum=MAX_WORKFLOW_JSON_BYTES))
    )
    if args.packet != f"artifacts/orchestration/task_packets/{request['task_packet_id']}.json":
        raise ExperimentRunnerCreativeContextCliError("workflow packet path differs from request")
    _workflow_sources(request)
    output_dir = _resolve_output_dir(Path(args.output_dir), create=True)
    stage = {
        "schema_version": CREATIVE_WORKFLOW_SCHEMA_VERSION,
        "stage": "prepared",
        "request": request,
        "native_result": None,
        "review": None,
        "handoff": None,
        "intake_error": None,
    }
    path = _write_workflow_stage(output_dir, stage)
    print(f"PASS: Creative workflow prepared at {_display_path(path)}")
    print(f"Request fingerprint: {workflow_fingerprint(request)}")
    return 0


def _workflow_ingest(args: argparse.Namespace) -> int:
    prepared = _load_workflow_stage(args.workflow, "prepared")
    output_dir = _workflow_stage_path(args.workflow, "prepared").parent
    raw = sys.stdin.buffer.read(MAX_WORKFLOW_JSON_BYTES + 1)
    try:
        native_result = validate_creative_workflow_native_result(
            _workflow_json_bytes(raw), prepared["request"]
        )
    except (ExperimentRunnerCreativeContextCliError, ExperimentRunnerCreativeContextContractError):
        returned = dict(prepared, stage="returned", intake_error="INVALID_NATIVE_RESULT")
        _write_workflow_stage(output_dir, returned)
        raise ExperimentRunnerCreativeContextCliError(
            "native result returned but intake is invalid"
        ) from None
    returned = dict(prepared, stage="returned")
    _write_workflow_stage(output_dir, returned)
    validated = dict(returned, stage="validated", native_result=native_result)
    path = _write_workflow_stage(output_dir, validated)
    print(f"PASS: native intake validated at {_display_path(path)}")
    return 0


def _workflow_review(args: argparse.Namespace) -> int:
    validated = _load_workflow_stage(args.workflow, "validated")
    review = validate_creative_workflow_review(
        _workflow_json_bytes(_safe_workflow_file(args.review, maximum=MAX_WORKFLOW_JSON_BYTES)),
        validated["request"],
        validated["native_result"],
    )
    path = _write_workflow_stage(
        _workflow_stage_path(args.workflow, "validated").parent,
        dict(validated, stage="reviewed", review=review),
    )
    print(f"PASS: Creative selection reviewed at {_display_path(path)}")
    return 0


def _workflow_admit(args: argparse.Namespace) -> int:
    reviewed = _load_workflow_stage(args.workflow, "reviewed")
    dispatch_order, eligible = _canonical_manifest_writer_occurrences(reviewed["request"])
    handoff = validate_creative_workflow_handoff(
        _workflow_json_bytes(_safe_workflow_file(args.handoff, maximum=MAX_WORKFLOW_JSON_BYTES)),
        reviewed["request"],
        reviewed["native_result"],
        reviewed["review"],
        eligible,
        dispatch_order,
    )
    path = _write_workflow_stage(
        _workflow_stage_path(args.workflow, "reviewed").parent,
        dict(reviewed, stage="admitted", handoff=handoff),
    )
    print(f"PASS: exact writer handoff recorded at {_display_path(path)}")
    return 0


def _workflow_archive_inputs(directory: Path, include: list[str]) -> dict[str, bytes]:
    required = {
        *WORKFLOW_STAGE_FILES.values(),
        "patch.diff",
        "test_evidence.json",
        "work_review.md",
    }
    if len(include) != len(set(include)) or not required.issubset(include):
        raise ExperimentRunnerCreativeContextCliError("capsule is missing a required file")
    if set(include) - WORKFLOW_ARCHIVE_FILES:
        raise ExperimentRunnerCreativeContextCliError("capsule contains an unapproved file")
    files: dict[str, bytes] = {}
    total = 0
    for name in sorted(include):
        path = directory / name
        data = _safe_workflow_file(
            path.relative_to(REPO_ROOT).as_posix(), maximum=MAX_WORKFLOW_ARCHIVE_BYTES
        )
        total += len(data)
        if total > MAX_WORKFLOW_ARCHIVE_BYTES:
            raise ExperimentRunnerCreativeContextCliError("capsule exceeds size limit")
        try:
            readable = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExperimentRunnerCreativeContextCliError("capsule file is not UTF-8") from exc
        if (
            ARCHIVE_SECRET_RE.search(readable)
            or SECRET_VALUE_RE.search(readable)
            or contains_local_path_outside_route_context(readable)
            or re.search(
                r"/(?:Users|private/var|var/folders|tmp|etc|root)/|file://|"
                r"(?:https?://[^\s?#]+\?[^\s]+)",
                readable,
                re.IGNORECASE,
            )
        ):
            raise ExperimentRunnerCreativeContextCliError(
                "capsule contains private or signed content"
            )
        files[name] = data
    return files


def _workflow_export(args: argparse.Namespace) -> int:
    admitted = _load_workflow_stage(args.workflow, "admitted", require_current_git=False)
    directory = _workflow_stage_path(args.workflow, "admitted").parent
    stages = {
        name: _load_workflow_stage(str(directory / filename), name, require_current_git=False)
        for name, filename in WORKFLOW_STAGE_FILES.items()
    }
    if (
        any(stage["request"] != admitted["request"] for stage in stages.values())
        or stages["returned"]["intake_error"] is not None
        or stages["validated"]["native_result"] != admitted["native_result"]
        or stages["reviewed"]["review"] != admitted["review"]
    ):
        raise ExperimentRunnerCreativeContextCliError("capsule stage chain is inconsistent")
    files = _workflow_archive_inputs(directory, args.include)
    manifest = {
        "schema_version": "creative_workflow_capsule.v1",
        "files": {
            name: "sha256:" + hashlib.sha256(data).hexdigest() for name, data in files.items()
        },
    }
    destination = directory / "creative_workflow_capsule.zip"
    if destination.exists() or destination.is_symlink():
        raise ExperimentRunnerCreativeContextCliError("capsule already exists")
    descriptor, temp_name = tempfile.mkstemp(prefix=".capsule-", dir=directory)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name)
                info.external_attr = 0o600 << 16
                archive.writestr(info, data)
            info = zipfile.ZipInfo("manifest.json")
            info.external_attr = 0o600 << 16
            archive.writestr(info, json.dumps(manifest, sort_keys=True, separators=(",", ":")))
        os.link(temp_name, destination, follow_symlinks=False)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    print(f"PASS: capsule exported at {_display_path(destination)}")
    print("SHA-256: " + hashlib.sha256(destination.read_bytes()).hexdigest())
    print("Storage state: storage_pending until same-ID Drive readback and downloaded restore")
    return 0


def _workflow_verify_archive(args: argparse.Namespace) -> int:
    archive_path = Path(args.archive)
    if archive_path.name != "creative_workflow_capsule.zip":
        raise ExperimentRunnerCreativeContextCliError("unexpected capsule filename")
    directory = _resolve_output_dir(archive_path.parent, create=False)
    archive_path = directory / archive_path.name
    raw = _safe_workflow_file(
        archive_path.relative_to(REPO_ROOT).as_posix(), maximum=MAX_WORKFLOW_ARCHIVE_BYTES + 100_000
    )
    if hashlib.sha256(raw).hexdigest() != args.sha256:
        raise ExperimentRunnerCreativeContextCliError("downloaded capsule hash mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if (
                len(names) != len(set(names))
                or "manifest.json" not in names
                or (set(names) - {"manifest.json"} - WORKFLOW_ARCHIVE_FILES)
            ):
                raise ExperimentRunnerCreativeContextCliError("capsule member names are unsafe")
            if not {
                *WORKFLOW_STAGE_FILES.values(),
                "patch.diff",
                "test_evidence.json",
                "work_review.md",
            }.issubset(names):
                raise ExperimentRunnerCreativeContextCliError("capsule is incomplete")
            for info in infos:
                if (
                    info.is_dir()
                    or info.file_size > MAX_WORKFLOW_ARCHIVE_BYTES
                    or ((info.external_attr >> 16) & 0o170000) not in {0, stat.S_IFREG}
                ):
                    raise ExperimentRunnerCreativeContextCliError(
                        "capsule member type or size is unsafe"
                    )
            manifest = _workflow_json_bytes(archive.read("manifest.json"))
            if manifest.get("schema_version") != "creative_workflow_capsule.v1" or not isinstance(
                manifest.get("files"), dict
            ):
                raise ExperimentRunnerCreativeContextCliError("capsule manifest is invalid")
            if set(manifest["files"]) != set(names) - {"manifest.json"}:
                raise ExperimentRunnerCreativeContextCliError(
                    "capsule manifest does not cover files"
                )
            extracted = {name: archive.read(name) for name in manifest["files"]}
            if sum(len(item) for item in extracted.values()) > MAX_WORKFLOW_ARCHIVE_BYTES:
                raise ExperimentRunnerCreativeContextCliError("capsule expanded size exceeds bound")
            restored_stages: dict[str, dict[str, Any]] = {}
            for name, data in extracted.items():
                if manifest["files"][name] != "sha256:" + hashlib.sha256(data).hexdigest():
                    raise ExperimentRunnerCreativeContextCliError("capsule member digest mismatch")
                if name in WORKFLOW_STAGE_FILES.values():
                    restored_stages[name] = validate_creative_workflow_stage(
                        _workflow_json_bytes(data)
                    )
            predecessor = None
            for stage_name, filename in WORKFLOW_STAGE_FILES.items():
                stage = restored_stages[filename]
                if stage["stage"] != stage_name:
                    raise ExperimentRunnerCreativeContextCliError("restored stage name mismatch")
                expected = (
                    workflow_fingerprint(stage["request"])
                    if predecessor is None
                    else predecessor["fingerprint"]
                )
                if stage["upstream_assets"] != [expected]:
                    raise ExperimentRunnerCreativeContextCliError("restored stage lineage mismatch")
                _require_inherited_workflow_evidence(stage, predecessor)
                predecessor = stage
            if restored_stages["workflow.returned.json"]["intake_error"] is not None:
                raise ExperimentRunnerCreativeContextCliError("restored intake was invalid")
            admitted_stage = restored_stages["workflow.admitted.json"]
            _workflow_sources(admitted_stage["request"], require_current_git=False)
            dispatch_order, eligible = _canonical_manifest_writer_occurrences(
                admitted_stage["request"]
            )
            validate_creative_workflow_handoff(
                admitted_stage["handoff"],
                admitted_stage["request"],
                admitted_stage["native_result"],
                admitted_stage["review"],
                eligible,
                dispatch_order,
            )
    except (zipfile.BadZipFile, zlib.error, RuntimeError, KeyError) as exc:
        raise ExperimentRunnerCreativeContextCliError("capsule could not be restored") from exc
    requested_restore = Path(args.restore_dir)
    if requested_restore.name in {"", ".", ".."} or ".." in requested_restore.parts:
        raise ExperimentRunnerCreativeContextCliError("restore directory must name a safe leaf")
    parent = _resolve_output_dir(requested_restore.parent, create=True)
    restore_dir = parent / requested_restore.name
    _reject_symlink_components(restore_dir, label="restore directory")
    try:
        restore_dir.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ExperimentRunnerCreativeContextCliError("restore directory already exists") from exc
    except OSError as exc:
        raise ExperimentRunnerCreativeContextCliError(
            "restore directory cannot be created"
        ) from exc
    try:
        for name, data in extracted.items():
            target = restore_dir / name
            with target.open("xb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(data)
    except OSError as exc:
        raise ExperimentRunnerCreativeContextCliError(
            "restored capsule could not be written"
        ) from exc
    print(f"PASS: downloaded capsule hash and restore verified at {_display_path(restore_dir)}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare local Experiment Runner PR creative-context artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect-context")
    _add_context_args(collect_parser)
    collect_parser.add_argument("--output")
    collect_parser.set_defaults(func=_cmd_collect_context)

    hypothesis_parser = subparsers.add_parser("generate-hypotheses")
    hypothesis_parser.add_argument("--context-map", required=True)
    hypothesis_parser.add_argument("--hypothesis-count", type=int, default=4)
    hypothesis_parser.add_argument("--output")
    hypothesis_parser.set_defaults(func=_cmd_generate_hypotheses)

    routing_parser = subparsers.add_parser("route-agents")
    routing_parser.add_argument("--hypothesis-packet", required=True)
    routing_parser.add_argument("--output")
    routing_parser.set_defaults(func=_cmd_route_agents)

    ingest_parser = subparsers.add_parser("ingest-model-hypotheses")
    ingest_parser.add_argument("--context-map", required=True)
    ingest_parser.add_argument("--model-intake", required=True)
    ingest_parser.add_argument("--output")
    ingest_parser.add_argument("--normalized-intake-output")
    ingest_parser.set_defaults(func=_cmd_ingest_model_hypotheses)

    dispatch_parser = subparsers.add_parser("dispatch-coordinator")
    dispatch_parser.add_argument("--hypothesis-packet", required=True)
    dispatch_parser.add_argument("--routing", required=True)
    dispatch_parser.add_argument("--output")
    dispatch_parser.set_defaults(func=_cmd_dispatch_coordinator)

    summary_parser = subparsers.add_parser("summarize")
    summary_parser.add_argument("--oracle")
    summary_parser.add_argument("--hypotheses", required=True)
    summary_parser.add_argument("--routing", required=True)
    summary_parser.add_argument("--output")
    summary_parser.set_defaults(func=_cmd_summarize)

    prepare_parser = subparsers.add_parser("prepare")
    _add_context_args(prepare_parser)
    prepare_parser.add_argument("--context-map")
    prepare_parser.add_argument("--hypothesis-count", type=int, default=4)
    prepare_parser.add_argument("--model-intake")
    prepare_parser.add_argument("--oracle-status", default="skipped")
    prepare_parser.add_argument("--oracle-result-ref")
    prepare_parser.add_argument("--oracle-result-fingerprint")
    prepare_parser.add_argument("--oracle-coauthor-required", action="store_true")
    prepare_parser.add_argument("--output-dir")
    prepare_parser.set_defaults(func=_cmd_prepare)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument(
        "--artifact-type",
        required=True,
        choices=sorted(
            {
                ORACLE_ATTACHMENT_TYPE,
                CONTEXT_MAP_TYPE,
                HYPOTHESIS_PACKET_TYPE,
                AGENT_ROUTING_TYPE,
                OPERATOR_MODEL_INTAKE_TYPE,
                COORDINATOR_DISPATCH_TYPE,
                CONSUMPTION_SUMMARY_TYPE,
                APPROVAL_TYPE,
            }
        ),
    )
    validate_parser.add_argument("--context-path")
    validate_parser.add_argument("--path", required=True)
    validate_parser.add_argument("--output")
    validate_parser.set_defaults(func=_cmd_validate)

    workflow_prepare = subparsers.add_parser("workflow-prepare")
    workflow_prepare.add_argument("--packet", required=True)
    workflow_prepare.add_argument("--request", required=True)
    workflow_prepare.add_argument("--output-dir", required=True)
    workflow_prepare.set_defaults(func=_workflow_prepare)

    workflow_ingest = subparsers.add_parser("workflow-ingest")
    workflow_ingest.add_argument("--workflow", required=True)
    workflow_ingest.add_argument("--native-result-stdin", action="store_true", required=True)
    workflow_ingest.set_defaults(func=_workflow_ingest)

    workflow_review = subparsers.add_parser("workflow-review")
    workflow_review.add_argument("--workflow", required=True)
    workflow_review.add_argument("--review", required=True)
    workflow_review.set_defaults(func=_workflow_review)

    workflow_admit = subparsers.add_parser("workflow-admit")
    workflow_admit.add_argument("--workflow", required=True)
    workflow_admit.add_argument("--handoff", required=True)
    workflow_admit.set_defaults(func=_workflow_admit)

    workflow_export = subparsers.add_parser("workflow-export")
    workflow_export.add_argument("--workflow", required=True)
    workflow_export.add_argument("--include", action="append", required=True)
    workflow_export.set_defaults(func=_workflow_export)

    workflow_verify = subparsers.add_parser("workflow-verify-archive")
    workflow_verify.add_argument("--archive", required=True)
    workflow_verify.add_argument("--sha256", required=True)
    workflow_verify.add_argument("--restore-dir", required=True)
    workflow_verify.set_defaults(func=_workflow_verify_archive)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return int(args.func(args))
    except (
        ExperimentRunnerCreativeContextCliError,
        ExperimentRunnerCreativeContextContractError,
        EvidenceRailApplicabilityError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
