#!/usr/bin/env python3
"""Local CLI for adaptive production-adjacent creative pilots."""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import errno
import fcntl
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.creative_pilot_workspace_contract import (
    CreativePilotContractError,
    build_approval_v2,
    add_rebuttal_assignments,
    apply_synthesis_transition,
    build_context_map_v2,
    build_evidence_events,
    build_hypothesis_packet_v2,
    build_role_result,
    build_synthesis,
    build_target_manifest,
    build_adaptive_pr1_resume_binding,
    build_adaptive_pr1_variant_intake,
    derive_adaptive_pr1_resume_identity,
    build_workspace,
    complete_handoff,
    detect_conflicts,
    ingest_role_result,
    load_json_strict,
    terminate_workspace,
    validate_dispatch_phase,
    validate_retained_terminal_handoff,
    validate_adaptive_pr1_resume_binding,
    validate_approval_v2,
    validate_synthesis,
    validate_workspace,
    current_origin_main_sha,
    ADAPTIVE_PR1_PREPARE_FILENAMES,
    ADAPTIVE_PR1_SOURCE_TYPES,
)
from scripts.orchestration.creative_code_spec_pipeline import (
    CreativeCodeSpecPipelineError,
    prepare as prepare_specification,
    prepare_exact as prepare_exact_specification,
    validate_default_prepare_artifact_snapshots,
    validate_exact_prepare_artifacts,
)
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    CreativeHypothesisSpecBridgeError,
    build_creative_pilot_spec_bridge_bundle,
)
from scripts.orchestration.creative_code_contract import CreativeCodeContractError
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
)
from core.evidence.fingerprints import fingerprint_payload

PILOT_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "adaptive_pilots"
SPEC_BRIDGE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "spec_bridge"
RESUME_INTAKE_FILENAME = "creative_adaptive_pr1_variant_intake.json"
RESUME_BINDING_FILENAME = "creative_adaptive_pr1_resume_binding.json"
RESUME_CANDIDATE_FILENAME = "creative_code_candidate_packet.json"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise CreativePilotContractError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


FIXED_FILENAMES = {
    "context": "context_map.v2.json",
    "packet": "hypothesis_packet.v2.json",
    "workspace": "workspace.json",
    "synthesis": "synthesis.json",
    "approval": "approval.v2.json",
    "evidence": "evidence_events.json",
    "bridge": "spec_bridge.v2.json",
    "candidate": "creative_code_candidate.v1.json",
}


def _read(path: Path) -> dict[str, Any]:
    parent_fd = -1
    file_fd = -1
    try:
        parent_fd, filename = _open_pinned_parent(path, create=False)
        flags = os.O_RDONLY | _required_open_flag("O_NOFOLLOW")
        flags |= getattr(os, "O_CLOEXEC", 0)
        file_fd = os.open(filename, flags, dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise CreativePilotContractError("pilot input must be a regular file")
        with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
            file_fd = -1
            payload = load_json_strict(handle.read())
        if not isinstance(payload, dict):
            raise CreativePilotContractError("pilot input must be a JSON object")
        return payload
    except CreativePilotContractError:
        raise
    except (OSError, UnicodeDecodeError, ValueError, NotImplementedError) as exc:
        if isinstance(exc, OSError) and exc.errno == errno.ELOOP:
            raise CreativePilotContractError(
                "pilot artifact path must not traverse symlinks"
            ) from exc
        raise CreativePilotContractError("unable to read safe repo-local pilot JSON") from exc
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error = _close_descriptors(file_fd, parent_fd)
        if active_error is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "unable to close pilot input safely"
            ) from cleanup_error


def _read_array(path: Path) -> list[dict[str, Any]]:
    parent_fd = -1
    file_fd = -1
    try:
        parent_fd, filename = _open_pinned_parent(path, create=False)
        flags = os.O_RDONLY | _required_open_flag("O_NOFOLLOW") | getattr(os, "O_CLOEXEC", 0)
        file_fd = os.open(filename, flags, dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise CreativePilotContractError("variant declarations must be a regular file")
        with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
            file_fd = -1
            payload = json.loads(handle.read(), object_pairs_hook=_reject_duplicate_keys)
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise CreativePilotContractError("variant declarations must be a JSON array of objects")
        return payload
    except CreativePilotContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, NotImplementedError) as exc:
        raise CreativePilotContractError("unable to read safe exact variant declarations") from exc
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error = _close_descriptors(file_fd, parent_fd)
        if active_error is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "unable to close variant declarations safely"
            ) from cleanup_error


def _read_json_value(path: Path) -> Any:
    parent_fd = -1
    file_fd = -1
    try:
        parent_fd, filename = _open_pinned_parent(path, create=False)
        flags = os.O_RDONLY | _required_open_flag("O_NOFOLLOW") | getattr(os, "O_CLOEXEC", 0)
        file_fd = os.open(filename, flags, dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise CreativePilotContractError("pilot input must be a regular file")
        with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
            file_fd = -1
            return json.loads(handle.read(), object_pairs_hook=_reject_duplicate_keys)
    except CreativePilotContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, NotImplementedError) as exc:
        raise CreativePilotContractError("unable to read safe pilot JSON value") from exc
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error = _close_descriptors(file_fd, parent_fd)
        if active_error is None and cleanup_error is not None:
            raise CreativePilotContractError("unable to close pilot JSON safely") from cleanup_error


def _atomic_write(path: Path, payload: Any) -> None:
    parent_fd = -1
    file_fd = -1
    temp_name: str | None = None
    try:
        parent_fd, filename = _open_pinned_parent(path, create=True)
        try:
            existing = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(existing.st_mode):
                raise CreativePilotContractError("pilot artifact target must be a regular file")

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _required_open_flag("O_NOFOLLOW")
        flags |= getattr(os, "O_CLOEXEC", 0)
        for _attempt in range(32):
            candidate_name = f".{filename}.{secrets.token_hex(8)}.tmp"
            try:
                file_fd = os.open(candidate_name, flags, 0o600, dir_fd=parent_fd)
                temp_name = candidate_name
                break
            except FileExistsError:
                continue
        else:
            raise CreativePilotContractError("unable to allocate pilot artifact temp file")

        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            file_fd = -1
            handle.write(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temp_name,
            filename,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temp_name = None
        os.fsync(parent_fd)
    except CreativePilotContractError:
        raise
    except (OSError, NotImplementedError) as exc:
        raise CreativePilotContractError("unable to write safe repo-local pilot JSON") from exc
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error: OSError | NotImplementedError | None = None
        if parent_fd >= 0:
            if temp_name is not None:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
                except (OSError, NotImplementedError) as exc:
                    cleanup_error = exc
        descriptor_error = _close_descriptors(file_fd, parent_fd)
        cleanup_error = cleanup_error or descriptor_error
        if active_error is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "unable to clean up pilot artifact safely"
            ) from cleanup_error


def _close_descriptors(*descriptors: int) -> OSError | None:
    first_error: OSError | None = None
    for descriptor in descriptors:
        if descriptor < 0:
            continue
        try:
            os.close(descriptor)
        except OSError as exc:
            first_error = first_error or exc
    return first_error


def _required_open_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise CreativePilotContractError(f"platform lacks required {name} support")
    return value


def _repo_relative_parts(path: Path) -> tuple[str, ...]:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise CreativePilotContractError("pilot artifact path must stay inside repository") from exc
    parts = relative.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise CreativePilotContractError("pilot artifact path must be a safe repo-relative file")
    return parts


def _open_pinned_parent(path: Path, *, create: bool) -> tuple[int, str]:
    parts = _repo_relative_parts(path)
    directory_flags = os.O_RDONLY | _required_open_flag("O_DIRECTORY")
    directory_flags |= _required_open_flag("O_NOFOLLOW") | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(REPO_ROOT, directory_flags)
    try:
        for component in parts[:-1]:
            try:
                child = os.open(component, directory_flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, directory_flags, dir_fd=descriptor)
            previous = descriptor
            descriptor = child
            close_error = _close_descriptors(previous)
            if close_error is not None:
                _close_descriptors(previous, descriptor)
                descriptor = -1
                raise CreativePilotContractError(
                    "unable to transfer pinned directory ownership"
                ) from close_error
        return descriptor, parts[-1]
    except (CreativePilotContractError, OSError, NotImplementedError):
        _close_descriptors(descriptor)
        raise


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current = current / part
        if (current.exists() or current.is_symlink()) and current.is_symlink():
            raise CreativePilotContractError("pilot artifact path must not traverse symlinks")


def _run_dir(pilot_id: str) -> Path:
    if not pilot_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        for char in pilot_id
    ):
        raise CreativePilotContractError("pilot-id must be a safe token")
    _reject_symlink_components(PILOT_ROOT)
    unresolved = PILOT_ROOT / pilot_id
    _reject_symlink_components(unresolved)
    root = PILOT_ROOT.resolve()
    candidate = unresolved.resolve()
    if candidate.parent != root:
        raise CreativePilotContractError("pilot directory escaped the adaptive-pilot root")
    current = candidate
    while current != root:
        if current.is_symlink():
            raise CreativePilotContractError("pilot directory must not traverse symlinks")
        current = current.parent
    return candidate


def _workspace_path(args: argparse.Namespace) -> Path:
    return _run_dir(args.pilot_id) / FIXED_FILENAMES["workspace"]


def _cmd_prepare(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    manifest = build_target_manifest(
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        paths=args.target,
        symbols=args.symbol,
        immutable_oracles=args.oracle,
    )
    context = build_context_map_v2(target_manifest=manifest, context_refs=args.context_ref)
    hypotheses = _read(Path(args.hypotheses)).get("hypotheses")
    if not isinstance(hypotheses, list):
        raise CreativePilotContractError("hypotheses file must contain a hypotheses array")
    packet = build_hypothesis_packet_v2(context_map=context, hypotheses=hypotheses)
    workspace = build_workspace(
        context_map=context,
        hypothesis_packet=packet,
        selected_hypothesis_id=args.selected_hypothesis,
    )
    _atomic_write(run_dir / FIXED_FILENAMES["context"], context)
    _atomic_write(run_dir / FIXED_FILENAMES["packet"], packet)
    _atomic_write(run_dir / FIXED_FILENAMES["workspace"], workspace)
    print(
        f"PASS phase={workspace['state']['phase']} next=emit-dispatch workspace={run_dir.relative_to(REPO_ROOT)}/{FIXED_FILENAMES['workspace']}"
    )


def _cmd_emit_dispatch(args: argparse.Namespace) -> None:
    workspace = validate_dispatch_phase(_read(_workspace_path(args)), phase=args.phase)
    phase = args.phase
    assignments = [row for row in workspace["assignments"] if row["phase"] == phase]
    if not assignments:
        raise CreativePilotContractError(f"workspace has no {phase} assignments")
    payload = {
        "workspace_id": workspace["workspace_id"],
        "workspace_intent_fingerprint": workspace["intent_fingerprint"],
        "workspace_revision_fingerprint": workspace["revision_fingerprint"],
        "phase": phase,
        "assignments": assignments,
        "authority": {
            "execute_role_passes": True,
            "generate_patch": False,
            "write_repository": False,
        },
    }
    output = _run_dir(args.pilot_id) / f"dispatch.{phase}.json"
    _atomic_write(output, payload)
    print(
        f"PASS phase={workspace['state']['phase']} next=task-bootstrap dispatch={output.relative_to(REPO_ROOT)}"
    )


def _cmd_ingest(args: argparse.Namespace) -> None:
    path = _workspace_path(args)
    workspace = validate_workspace(_read(path))
    updated = ingest_role_result(workspace, _read(Path(args.role_result)))
    _atomic_write(path, updated)
    print(
        f"PASS phase={updated['state']['phase']} next={'detect-conflicts' if updated['state']['phase'] == 'independent_complete' else 'ingest-role-result'}"
    )


def _cmd_record_role_result(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    path = run_dir / FIXED_FILENAMES["workspace"]
    workspace = validate_workspace(_read(path))
    existing = next(
        (row for row in workspace["role_results"] if row["assignment_id"] == args.assignment_id),
        None,
    )
    if existing is not None:
        requested = {
            "stance": args.stance,
            "claim_ids": [value.strip() for value in args.claim_id],
            "evidence_refs": [value.strip() for value in args.evidence_ref],
            "blocker_codes": [value.strip() for value in args.blocker_code],
            "oracle_gap_codes": [value.strip() for value in args.oracle_gap_code],
            "peer_result_refs": [value.strip() for value in args.peer_result_ref],
        }
        if any(existing[key] != value for key, value in requested.items()):
            raise CreativePilotContractError("conflicting role-result replay")
        print(
            f"PASS result_id={existing['result_id']} phase={workspace['state']['phase']} replay=idempotent"
        )
        return
    result = build_role_result(
        workspace=workspace,
        assignment_id=args.assignment_id,
        stance=args.stance,
        claim_ids=args.claim_id,
        evidence_refs=args.evidence_ref,
        blocker_codes=args.blocker_code,
        oracle_gap_codes=args.oracle_gap_code,
        peer_result_refs=args.peer_result_ref,
    )
    result_path = run_dir / "role_results" / f"{result['result_id'].split(':')[-1]}.json"
    if result_path.exists() and _read(result_path) != result:
        raise CreativePilotContractError("divergent role-result overwrite is forbidden")
    _atomic_write(result_path, result)
    updated = ingest_role_result(workspace, result)
    _atomic_write(path, updated)
    print(
        f"PASS result_id={result['result_id']} phase={updated['state']['phase']} "
        f"next={'detect-conflicts' if updated['state']['phase'] in {'independent_complete', 'rebuttal_complete'} else 'record-role-result'}"
    )


def _cmd_detect(args: argparse.Namespace) -> None:
    path = _workspace_path(args)
    updated = detect_conflicts(validate_workspace(_read(path)))
    _atomic_write(path, updated)
    print(
        f"PASS phase={updated['state']['phase']} next={'emit-rebuttal' if updated['state']['phase'] == 'rebuttal_required' else 'synthesize'}"
    )


def _cmd_emit_rebuttal(args: argparse.Namespace) -> None:
    path = _workspace_path(args)
    updated = add_rebuttal_assignments(validate_workspace(_read(path)))
    _atomic_write(path, updated)
    output = _run_dir(args.pilot_id) / "dispatch.rebuttal.json"
    _atomic_write(
        output,
        {
            "workspace_id": updated["workspace_id"],
            "workspace_intent_fingerprint": updated["intent_fingerprint"],
            "workspace_revision_fingerprint": updated["revision_fingerprint"],
            "phase": "rebuttal",
            "assignments": [row for row in updated["assignments"] if row["phase"] == "rebuttal"],
            "authority": {
                "execute_role_passes": True,
                "generate_patch": False,
                "write_repository": False,
            },
        },
    )
    print(
        f"PASS phase={updated['state']['phase']} next=task-bootstrap dispatch={output.relative_to(REPO_ROOT)}"
    )


def _cmd_synthesize(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis = build_synthesis(workspace)
    transitioned = apply_synthesis_transition(workspace, synthesis)
    _atomic_write(run_dir / FIXED_FILENAMES["workspace"], transitioned)
    _atomic_write(run_dir / FIXED_FILENAMES["synthesis"], synthesis)
    events = [
        event.to_dict()
        for event in build_evidence_events(
            workspace=transitioned,
            synthesis=synthesis,
            produced_at=datetime.now(timezone.utc).isoformat(),
        )
    ]
    _atomic_write(run_dir / FIXED_FILENAMES["evidence"], events)
    print(
        f"PASS decision={synthesis['decision']} evidence={synthesis['evidence_sufficiency']} next={synthesis['next_allowed_action']}"
    )


def _cmd_approve(args: argparse.Namespace) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise CreativePilotContractError("approve-handoff requires an interactive TTY")
    run_dir = _run_dir(args.pilot_id)
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis = validate_synthesis(_read(run_dir / FIXED_FILENAMES["synthesis"]))
    expected = f"APPROVE {args.pilot_id} {synthesis['synthesis_id']} {workspace['target_manifest']['head_sha']}"
    print(f"Type exactly: {expected}")
    if input("approval> ") != expected:
        raise CreativePilotContractError("approval phrase did not match")
    approval = build_approval_v2(
        workspace=workspace,
        synthesis=synthesis,
        approved_by=args.approved_by,
    )
    approval_path = run_dir / FIXED_FILENAMES["approval"]
    if approval_path.exists() and _read(approval_path) != approval:
        raise CreativePilotContractError("divergent approval overwrite is forbidden")
    _atomic_write(approval_path, approval)
    print(f"PASS approval_id={approval['approval_id']} next=creative-hypothesis-spec-bridge-v2")


def _cmd_build_handoff(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    context = _read(run_dir / FIXED_FILENAMES["context"])
    packet = _read(run_dir / FIXED_FILENAMES["packet"])
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis = validate_synthesis(_read(run_dir / FIXED_FILENAMES["synthesis"]))
    approval = validate_approval_v2(_read(run_dir / FIXED_FILENAMES["approval"]))
    bundle = build_creative_pilot_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        workspace=workspace,
        synthesis=synthesis,
        approval=approval,
        variant_count=args.variant_count,
    )
    bridge_path = run_dir / FIXED_FILENAMES["bridge"]
    candidate_path = run_dir / FIXED_FILENAMES["candidate"]
    _atomic_write(bridge_path, bundle["bridge"])
    _atomic_write(candidate_path, bundle["candidate"])
    prepare_dir = run_dir / "pr1_prepare"
    prepare_specification(candidate_path, prepare_dir)
    completed = complete_handoff(
        workspace=workspace,
        approval=approval,
        bridge=bundle["bridge"],
        candidate=bundle["candidate"],
    )
    _atomic_write(run_dir / FIXED_FILENAMES["workspace"], completed)
    print(
        "PASS candidate_schema=1.0 patch_generated=false "
        f"phase={completed['state']['phase']} next=agent-skeptic-review "
        f"prepare={prepare_dir.relative_to(REPO_ROOT)}"
    )


def _artifact_ref(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise CreativePilotContractError(
            "adaptive resume artifacts must stay inside repository"
        ) from exc


def _binding_row_from_snapshot(
    path: Path, *, payload: Any, filename: str, artifact_type: str
) -> dict[str, str]:
    observed_type = (
        payload.get("artifact_type") or payload.get("packet_type")
        if isinstance(payload, dict)
        else None
    )
    if artifact_type != "json" and observed_type != artifact_type:
        raise CreativePilotContractError(f"adaptive_source_type_mismatch: {filename}")
    return {
        "filename": filename,
        "artifact_type": artifact_type,
        "ref": _artifact_ref(path),
        "fingerprint": fingerprint_payload(payload),
    }


def _exact_source_bindings(
    run_dir: Path,
    *,
    lineage: dict[str, Any],
    prepare_snapshots: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    source_snapshots = {
        FIXED_FILENAMES["context"]: lineage["context_map"],
        FIXED_FILENAMES["packet"]: lineage["hypothesis_packet"],
        FIXED_FILENAMES["workspace"]: lineage["workspace"],
        FIXED_FILENAMES["synthesis"]: lineage["synthesis"],
        FIXED_FILENAMES["approval"]: lineage["approval"],
        FIXED_FILENAMES["bridge"]: lineage["bridge"],
        FIXED_FILENAMES["candidate"]: lineage["candidate"],
    }
    source_rows = [
        _binding_row_from_snapshot(
            run_dir / filename,
            payload=source_snapshots[filename],
            filename=filename,
            artifact_type=artifact_type,
        )
        for filename, artifact_type in ADAPTIVE_PR1_SOURCE_TYPES.items()
    ]
    prepare_rows = [
        _binding_row_from_snapshot(
            run_dir / "pr1_prepare" / filename,
            payload=prepare_snapshots[filename],
            filename=filename,
            artifact_type="json",
        )
        for filename in ADAPTIVE_PR1_PREPARE_FILENAMES
    ]
    return source_rows, prepare_rows


def _revalidate_exact_source_bindings(
    source_rows: list[dict[str, str]], prepare_rows: list[dict[str, str]]
) -> None:
    try:
        for row in (*source_rows, *prepare_rows):
            payload = _read_json_value(REPO_ROOT / row["ref"])
            observed_type = (
                payload.get("artifact_type") or payload.get("packet_type")
                if isinstance(payload, dict)
                else None
            )
            if row["artifact_type"] == "json":
                observed_type = "json"
            if observed_type != row["artifact_type"]:
                raise CreativePilotContractError(
                    f"adaptive_source_type_mismatch: {row['filename']}"
                )
            if fingerprint_payload(payload) != row["fingerprint"]:
                raise CreativePilotContractError(
                    f"adaptive_source_fingerprint_mismatch: {row['filename']}"
                )
    except CreativePilotContractError as exc:
        if str(exc).startswith("adaptive_source_lineage_mismatch:"):
            raise
        raise CreativePilotContractError(f"adaptive_source_lineage_mismatch: {exc}") from exc


def _expected_resume_entries() -> set[str]:
    return {
        RESUME_INTAKE_FILENAME,
        RESUME_BINDING_FILENAME,
        RESUME_CANDIDATE_FILENAME,
        "spec_prepare",
    }


DirectoryIdentity = tuple[int, int]


def _directory_identity(path: Path) -> DirectoryIdentity:
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise CreativePilotContractError("adaptive artifact must be a directory")
    return (info.st_dev, info.st_ino)


def _open_resume_parent_lock(final_dir: Path) -> int:
    parent_fd = -1
    try:
        parent_fd, final_name = _open_pinned_parent(final_dir, create=True)
        if final_name != final_dir.name:
            raise CreativePilotContractError("adaptive resume canonical name changed")
        try:
            fcntl.flock(parent_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CreativePilotContractError("adaptive_resume_lock_contended") from exc
        result = parent_fd
        parent_fd = -1
        return result
    finally:
        cleanup_error = _close_descriptors(parent_fd)
        if sys.exc_info()[1] is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "adaptive resume parent lock could not be closed"
            ) from cleanup_error


def _retain_owned_staging(
    staging: Path,
    *,
    expected_identity: DirectoryIdentity,
) -> str:
    parent_fd = -1
    try:
        parent_fd, name = _open_pinned_parent(staging, create=False)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(current.st_mode)
            or (current.st_dev, current.st_ino) != expected_identity
        ):
            raise CreativePilotContractError(
                "adaptive_publish_cleanup_failed: staging ownership changed; left untouched"
            )
        retained_name = f".{name}.{secrets.token_hex(8)}.failed"
        _kernel_rename_noreplace(
            parent_fd,
            name,
            retained_name,
            collision_message="adaptive_publish_cleanup_failed: retained staging collision",
        )
        os.fsync(parent_fd)
        return retained_name
    finally:
        cleanup_error = _close_descriptors(parent_fd)
        if sys.exc_info()[1] is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "adaptive_publish_cleanup_failed: unable to close staging parent"
            ) from cleanup_error


def _discard_owned_staging(
    staging: Path,
    *,
    expected_identity: DirectoryIdentity,
) -> None:
    if not staging.exists():
        return
    if _directory_identity(staging) != expected_identity:
        raise CreativePilotContractError(
            "adaptive_publish_cleanup_failed: staging ownership changed; left untouched"
        )
    shutil.rmtree(staging)


def _assert_complete_resume_dir(path: Path, *, allow_reviewed_run: bool = False) -> None:
    _reject_symlink_components(path)
    if path.is_symlink() or not path.is_dir():
        raise CreativePilotContractError("adaptive_source_symlink: resume output")
    for current_root, directory_names, filenames in os.walk(path, followlinks=False):
        current = Path(current_root)
        for name in (*directory_names, *filenames):
            if (current / name).is_symlink():
                raise CreativePilotContractError("adaptive_source_symlink: nested resume child")
    observed = {entry.name for entry in path.iterdir()}
    allowed = _expected_resume_entries()
    if allow_reviewed_run:
        allowed.add("spec_finalize_reviewed")
    if not _expected_resume_entries().issubset(observed) or not observed.issubset(allowed):
        raise CreativePilotContractError(
            "adaptive_partial_output: fixed resume output set required"
        )
    if any(entry.is_symlink() for entry in path.iterdir()):
        raise CreativePilotContractError("adaptive_source_symlink: resume child")
    prepare = path / "spec_prepare"
    if prepare.is_symlink() or not prepare.is_dir():
        raise CreativePilotContractError("adaptive_source_symlink: spec_prepare")
    prepare_entries = list(prepare.iterdir())
    if {entry.name for entry in prepare_entries} != set(ADAPTIVE_PR1_PREPARE_FILENAMES):
        raise CreativePilotContractError("adaptive_partial_output: fixed spec_prepare set required")
    if any(entry.is_symlink() for entry in prepare_entries):
        raise CreativePilotContractError("adaptive_source_symlink: spec_prepare child")
    if any(not entry.is_file() for entry in prepare_entries):
        raise CreativePilotContractError(
            "adaptive_partial_output: spec_prepare children must be regular files"
        )


def _kernel_rename_noreplace(
    parent_fd: int,
    source_name: str,
    destination_name: str,
    *,
    collision_message: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename_noreplace = getattr(libc, "renameatx_np", None)
        flag = 0x00000004  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        rename_noreplace = getattr(libc, "renameat2", None)
        flag = 1  # RENAME_NOREPLACE
    else:
        rename_noreplace = None
        flag = 0
    if rename_noreplace is None:
        raise CreativePilotContractError(
            "adaptive_atomic_publish_unsupported: no kernel no-replace rename"
        )
    rename_noreplace.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename_noreplace.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename_noreplace(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(destination_name),
        flag,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise CreativePilotContractError(collision_message)
        raise CreativePilotContractError(
            f"adaptive_publish_failed: no-replace rename errno={error_number}"
        )


def _atomic_publish_directory_noreplace(staging: Path, final_dir: Path) -> None:
    """Atomically publish one complete directory without replacing a destination."""

    parent_fd = -1
    try:
        if staging.parent != final_dir.parent:
            raise CreativePilotContractError(
                "adaptive_publish_failed: staging and destination must share a parent"
            )
        parent_fd, final_name = _open_pinned_parent(final_dir, create=False)
        _kernel_rename_noreplace(
            parent_fd,
            staging.name,
            final_name,
            collision_message=(
                "adaptive_publish_collision: canonical resume directory already exists"
            ),
        )
        os.fsync(parent_fd)
    except CreativePilotContractError:
        raise
    except (OSError, NotImplementedError) as exc:
        raise CreativePilotContractError(
            "adaptive_publish_failed: unable to publish canonical resume directory"
        ) from exc
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error = _close_descriptors(parent_fd)
        if active_error is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "adaptive_publish_failed: unable to close publish directory"
            ) from cleanup_error


def _fsync_directory(path: Path) -> None:
    descriptor = -1
    try:
        descriptor, _sentinel = _open_pinned_parent(path / ".fsync-sentinel", create=False)
        os.fsync(descriptor)
    finally:
        cleanup_error = _close_descriptors(descriptor)
        if sys.exc_info()[1] is None and cleanup_error is not None:
            raise CreativePilotContractError(
                "adaptive_publish_failed: unable to close staged directory"
            ) from cleanup_error


def _validate_existing_resume(
    final_dir: Path,
    *,
    intake: dict[str, Any],
    candidate: dict[str, Any],
    source_rows: list[dict[str, str]],
    prepare_rows: list[dict[str, str]],
) -> None:
    _assert_complete_resume_dir(final_dir, allow_reviewed_run=True)
    existing_intake = _read(final_dir / RESUME_INTAKE_FILENAME)
    existing_candidate = _read(final_dir / RESUME_CANDIDATE_FILENAME)
    existing_binding = _read(final_dir / RESUME_BINDING_FILENAME)
    if existing_intake != intake or existing_candidate != candidate:
        raise CreativePilotContractError("adaptive_divergent_replay: resume inputs changed")
    validate_exact_prepare_artifacts(
        run_dir=final_dir / "spec_prepare",
        expected_packet=existing_candidate,
        expected_variants=existing_intake["materialized_variants"],
    )
    validate_adaptive_pr1_resume_binding(
        existing_binding,
        intake=existing_intake,
        candidate=existing_candidate,
        revalidate_git=True,
    )
    _revalidate_exact_source_bindings(source_rows, prepare_rows)


def _cmd_resume_pr1(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    try:
        context = _read(run_dir / FIXED_FILENAMES["context"])
        packet = _read(run_dir / FIXED_FILENAMES["packet"])
        workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
        synthesis = _read(run_dir / FIXED_FILENAMES["synthesis"])
        approval = _read(run_dir / FIXED_FILENAMES["approval"])
        bridge = _read(run_dir / FIXED_FILENAMES["bridge"])
        candidate = _read(run_dir / FIXED_FILENAMES["candidate"])
        retained_prepare_snapshots = {
            filename: _read_json_value(run_dir / "pr1_prepare" / filename)
            for filename in ADAPTIVE_PR1_PREPARE_FILENAMES
        }
    except CreativePilotContractError as exc:
        raise CreativePilotContractError(f"adaptive_source_lineage_mismatch: {exc}") from exc
    candidate_path = run_dir / FIXED_FILENAMES["candidate"]
    declarations = _read_array(Path(args.variant_declarations))
    current_base = args.current_base_sha
    if current_base != current_origin_main_sha():
        raise CreativePilotContractError(
            "adaptive_base_drift: current-base-sha must equal origin/main"
        )
    old_manifest = workspace["target_manifest"]
    current_manifest = build_target_manifest(
        base_sha=current_base,
        head_sha=current_base,
        paths=[row["path"] for row in old_manifest["files"]],
        symbols=old_manifest["symbols"],
        immutable_oracles=old_manifest["immutable_oracles"],
    )
    lineage = validate_retained_terminal_handoff(
        context_map=context,
        hypothesis_packet=packet,
        workspace=workspace,
        synthesis=synthesis,
        approval=approval,
        bridge=bridge,
        candidate=candidate,
        current_target_manifest=current_manifest,
    )
    context = lineage["context_map"]
    packet = lineage["hypothesis_packet"]
    workspace = lineage["workspace"]
    synthesis = lineage["synthesis"]
    approval = lineage["approval"]
    candidate = lineage["candidate"]
    prepare_snapshots = validate_default_prepare_artifact_snapshots(
        retained_prepare_snapshots,
        expected_packet=candidate,
    )
    source_rows, prepare_rows = _exact_source_bindings(
        run_dir,
        lineage=lineage,
        prepare_snapshots=prepare_snapshots,
    )
    original_candidate_ref = _artifact_ref(candidate_path)
    intake = build_adaptive_pr1_variant_intake(
        pilot_id=args.pilot_id,
        candidate=candidate,
        candidate_ref=original_candidate_ref,
        declarations=declarations,
    )
    resume_id, _idempotency = derive_adaptive_pr1_resume_identity(
        pilot_id=args.pilot_id,
        intake=intake,
        candidate=candidate,
        source_artifacts=source_rows,
        original_prepare_bindings=prepare_rows,
        current_target_manifest=current_manifest,
    )
    final_dir = SPEC_BRIDGE_ROOT / resume_id
    _revalidate_exact_source_bindings(source_rows, prepare_rows)
    lock_fd = -1
    primary_error: Exception | None = None
    try:
        lock_fd = _open_resume_parent_lock(final_dir)
        if final_dir.exists() or final_dir.is_symlink():
            _validate_existing_resume(
                final_dir,
                intake=intake,
                candidate=candidate,
                source_rows=source_rows,
                prepare_rows=prepare_rows,
            )
            print(f"PASS resume_id={resume_id} replay=idempotent next=agent-skeptic-review")
            return

        staging: Path | None = None
        staging_identity: DirectoryIdentity | None = None
        for _attempt in range(32):
            candidate_staging = SPEC_BRIDGE_ROOT / (f".{resume_id}.{secrets.token_hex(8)}.staging")
            try:
                candidate_staging.mkdir(mode=0o700)
            except FileExistsError:
                continue
            staging = candidate_staging
            staging_identity = _directory_identity(staging)
            break
        if staging is None or staging_identity is None:
            raise CreativePilotContractError("adaptive_partial_output: staging collision")

        try:
            _atomic_write(staging / RESUME_INTAKE_FILENAME, intake)
            _atomic_write(staging / RESUME_CANDIDATE_FILENAME, candidate)
            staged_declarations = staging / ".variant_declarations.json"
            _atomic_write(staged_declarations, intake["declarations"])
            prepare_exact_specification(
                staging / RESUME_CANDIDATE_FILENAME,
                staged_declarations,
                staging / "spec_prepare",
            )
            staged_declarations.unlink()
            validate_exact_prepare_artifacts(
                run_dir=staging / "spec_prepare",
                expected_packet=candidate,
                expected_variants=intake["materialized_variants"],
            )
            final_intake_ref = _artifact_ref(final_dir / RESUME_INTAKE_FILENAME)
            final_candidate_ref = _artifact_ref(final_dir / RESUME_CANDIDATE_FILENAME)
            binding = build_adaptive_pr1_resume_binding(
                pilot_id=args.pilot_id,
                intake=intake,
                intake_ref=final_intake_ref,
                candidate=candidate,
                candidate_ref=final_candidate_ref,
                source_artifacts=source_rows,
                original_prepare_bindings=prepare_rows,
                old_target_manifest=old_manifest,
                current_target_manifest=current_manifest,
                spec_prepare_ref=_artifact_ref(final_dir / "spec_prepare"),
            )
            if binding["resume_id"] != resume_id:
                raise CreativePilotContractError("adaptive resume identity changed during staging")
            _atomic_write(staging / RESUME_BINDING_FILENAME, binding)
            _assert_complete_resume_dir(staging)
            _revalidate_exact_source_bindings(source_rows, prepare_rows)
            _fsync_directory(staging)
            try:
                _atomic_publish_directory_noreplace(staging, final_dir)
            except CreativePilotContractError as exc:
                if not str(exc).startswith("adaptive_publish_collision:"):
                    raise
                _validate_existing_resume(
                    final_dir,
                    intake=intake,
                    candidate=candidate,
                    source_rows=source_rows,
                    prepare_rows=prepare_rows,
                )
                _discard_owned_staging(staging, expected_identity=staging_identity)
                print(f"PASS resume_id={resume_id} replay=idempotent " "next=agent-skeptic-review")
                return
            _validate_existing_resume(
                final_dir,
                intake=intake,
                candidate=candidate,
                source_rows=source_rows,
                prepare_rows=prepare_rows,
            )
        except Exception as exc:
            cleanup_error: Exception | None = None
            if staging.exists():
                try:
                    _retain_owned_staging(staging, expected_identity=staging_identity)
                except Exception as cleanup_exc:
                    cleanup_error = cleanup_exc
            if cleanup_error is not None:
                raise CreativePilotContractError(
                    f"{exc}; cleanup_diagnostic={cleanup_error}"
                ) from exc
            raise
    except Exception as exc:
        primary_error = exc
        raise
    finally:
        close_error = _close_descriptors(lock_fd)
        if close_error is not None and primary_error is not None:
            raise CreativePilotContractError(
                f"{primary_error}; cleanup_diagnostic={close_error}"
            ) from primary_error
        if close_error is not None:
            raise CreativePilotContractError(
                "adaptive resume parent lock could not be closed"
            ) from close_error
    print(f"PASS resume_id={resume_id} replay=new next=agent-skeptic-review")


def _cmd_status(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis_path = run_dir / FIXED_FILENAMES["synthesis"]
    approval_path = run_dir / FIXED_FILENAMES["approval"]
    payload = {
        "pilot_id": args.pilot_id,
        "workspace_id": workspace["workspace_id"],
        "phase": workspace["state"]["phase"],
        "terminal": workspace["state"]["terminal"],
        "role_results": len(workspace["role_results"]),
        "synthesis_exists": synthesis_path.is_file(),
        "approval_exists": approval_path.is_file(),
        "patch_generated": False,
    }
    print(json.dumps(payload, sort_keys=True))


def _cmd_stop(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    workspace_path = run_dir / FIXED_FILENAMES["workspace"]
    workspace, disposition = terminate_workspace(
        validate_workspace(_read(workspace_path)),
        phase=args.phase,
        reason_code=args.reason_code,
    )
    _atomic_write(workspace_path, workspace)
    _atomic_write(run_dir / "disposition.json", disposition)
    print(f"PASS phase={workspace['state']['phase']} terminal=true next=none")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creative_pilot_workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--pilot-id", required=True)
    prepare.add_argument("--base-sha", required=True)
    prepare.add_argument("--head-sha", required=True)
    prepare.add_argument("--target", action="append", required=True)
    prepare.add_argument("--symbol", action="append", required=True)
    prepare.add_argument("--oracle", action="append", required=True)
    prepare.add_argument("--context-ref", action="append", required=True)
    prepare.add_argument("--hypotheses", required=True)
    prepare.add_argument("--selected-hypothesis", required=True)
    prepare.set_defaults(func=_cmd_prepare)
    dispatch = sub.add_parser("emit-dispatch")
    dispatch.add_argument("--pilot-id", required=True)
    dispatch.add_argument("--phase", choices=("independent", "rebuttal"), required=True)
    dispatch.set_defaults(func=_cmd_emit_dispatch)
    ingest = sub.add_parser("ingest-role-result")
    ingest.add_argument("--pilot-id", required=True)
    ingest.add_argument("--role-result", required=True)
    ingest.set_defaults(func=_cmd_ingest)
    record = sub.add_parser("record-role-result")
    record.add_argument("--pilot-id", required=True)
    record.add_argument("--assignment-id", required=True)
    record.add_argument("--stance", choices=("pass", "revise", "reject", "abstain"), required=True)
    record.add_argument("--claim-id", action="append", required=True)
    record.add_argument("--evidence-ref", action="append", required=True)
    record.add_argument("--blocker-code", action="append", default=[])
    record.add_argument("--oracle-gap-code", action="append", default=[])
    record.add_argument("--peer-result-ref", action="append", default=[])
    record.set_defaults(func=_cmd_record_role_result)
    detect = sub.add_parser("detect-conflicts")
    detect.add_argument("--pilot-id", required=True)
    detect.set_defaults(func=_cmd_detect)
    rebuttal = sub.add_parser("emit-rebuttal")
    rebuttal.add_argument("--pilot-id", required=True)
    rebuttal.set_defaults(func=_cmd_emit_rebuttal)
    synthesize = sub.add_parser("synthesize")
    synthesize.add_argument("--pilot-id", required=True)
    synthesize.set_defaults(func=_cmd_synthesize)
    approve = sub.add_parser("approve-handoff")
    approve.add_argument("--pilot-id", required=True)
    approve.add_argument("--approved-by", required=True)
    approve.set_defaults(func=_cmd_approve)
    handoff = sub.add_parser("build-handoff")
    handoff.add_argument("--pilot-id", required=True)
    handoff.add_argument("--variant-count", type=int, default=3, choices=(3, 4, 5))
    handoff.set_defaults(func=_cmd_build_handoff)
    resume = sub.add_parser("resume-pr1")
    resume.add_argument("--pilot-id", required=True)
    resume.add_argument("--variant-declarations", required=True)
    resume.add_argument("--current-base-sha", required=True)
    resume.set_defaults(func=_cmd_resume_pr1)
    status = sub.add_parser("status")
    status.add_argument("--pilot-id", required=True)
    status.set_defaults(func=_cmd_status)
    stop = sub.add_parser("stop")
    stop.add_argument("--pilot-id", required=True)
    stop.add_argument("--phase", choices=("revise", "reject", "blocked"), required=True)
    stop.add_argument("--reason-code", required=True)
    stop.set_defaults(func=_cmd_stop)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        args.func(args)
    except (
        CreativePilotContractError,
        CreativeHypothesisSpecBridgeError,
        CreativeCodeContractError,
        CreativeCodeSpecificationError,
        CreativeCodeSpecPipelineError,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
