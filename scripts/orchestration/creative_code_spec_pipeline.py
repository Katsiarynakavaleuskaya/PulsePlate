"""Local prepare/finalize CLI for PR-1 creative-code specification bundles."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import errno
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import Any

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.context_pack_compression import (
    build_context_pack_compression,
    to_stable_mapping,
)
from scripts.orchestration.creative_code_contract import (
    CreativeCodeContractError,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    build_exact_specification_variants,
    build_creative_code_specification_bundle,
    build_default_specification_variants,
    build_pending_skeptic_reviews,
    validate_source_candidate_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
PREPARE_SUCCESS_OUTPUT = "PASS: creative-code specification prepare complete"
FINALIZE_SUCCESS_OUTPUT = "PASS: creative-code specification finalize complete"

REQUIRED_CONTEXT = (
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
    "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
    "docs/orchestration/contracts/CREATIVE_CODE_CANDIDATE_CONTRACT.md",
    "docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md",
    "scripts/orchestration/creative_code_contract.py",
    "scripts/orchestration/creative_code_specification.py",
    "scripts/orchestration/creative_code_spec_pipeline.py",
    "scripts/orchestration/creative_code_rejection_index.py",
)

_CONTEXT_PACK_KEYS = frozenset(
    {
        "authority_boundary",
        "context_pack_id",
        "estimate",
        "graph_edges",
        "graph_nodes",
        "metadata",
        "omitted_duplicate_refs",
        "policy_version",
        "reason_codes",
        "required_context",
        "selected_context_refs",
    }
)
_CONTEXT_PACK_ESTIMATE_KEYS = frozenset(
    {
        "baseline_context_chars_estimate",
        "baseline_context_tokens_estimate",
        "candidate_context_chars_estimate",
        "candidate_context_tokens_estimate",
        "estimate_id",
        "fanout_tokens_saved_estimate",
        "orchestration_fanout_multiplier",
        "reason_codes",
        "token_estimate_version",
        "tokens_saved_estimate",
    }
)
_CONTEXT_PACK_NODE_KEYS = frozenset(
    {
        "metadata",
        "node_id",
        "node_type",
        "path",
        "path_fingerprint",
        "required",
        "token_estimate",
    }
)
_CONTEXT_PACK_EDGE_KEYS = frozenset({"edge_id", "edge_type", "metadata", "source", "target"})
_CONTEXT_PACK_REF_KEYS = frozenset(
    {"node_id", "path", "path_fingerprint", "reason_code", "status", "token_estimate"}
)
_CONTEXT_PACK_ESTIMATE_TELEMETRY_KEYS = frozenset(
    {
        "baseline_context_chars_estimate",
        "baseline_context_tokens_estimate",
        "candidate_context_chars_estimate",
        "candidate_context_tokens_estimate",
        "estimate_id",
        "fanout_tokens_saved_estimate",
        "tokens_saved_estimate",
    }
)
_CONTEXT_PACK_SECONDARY_AGENTS = (
    "ai-innovation-specialist",
    "security-auditor",
    "qa-engineer-agent",
    "logic-agent",
    "epistemology-discovery-agent",
    "bug-hunter",
    "cursor-specialist-agent",
)
_CONTEXT_PACK_REQUESTED_AGENTS = (
    "agent-coordinator",
    "ai-innovation-specialist",
    "architecture-specialist",
    "security-auditor",
    "qa-engineer-agent",
    "logic-agent",
    "epistemology-discovery-agent",
    "bug-hunter",
    "cursor-specialist-agent",
)


class CreativeCodeSpecPipelineError(ValueError):
    """Raised when the local PR-1 pipeline cannot safely read or write artifacts."""


def _required_open_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise CreativeCodeSpecPipelineError(f"platform lacks required {name} support")
    return value


def _candidate_and_repo_parts(
    raw_path: Path, *, allowed_root: Path, label: str
) -> tuple[Path, tuple[str, ...]]:
    candidate = raw_path if raw_path.is_absolute() else allowed_root / raw_path
    try:
        candidate.relative_to(allowed_root)
        repo_relative = candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise CreativeCodeSpecPipelineError(f"{label} must stay inside its allowed root.") from exc
    parts = repo_relative.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise CreativeCodeSpecPipelineError(f"{label} must be a safe repo-relative path.")
    return candidate, parts


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | _required_open_flag("O_DIRECTORY")
        | _required_open_flag("O_NOFOLLOW")
        | getattr(os, "O_CLOEXEC", 0)
    )


def _walk_pinned_directory(parts: tuple[str, ...], *, create: bool, label: str) -> int:
    descriptor = -1
    try:
        descriptor = os.open(REPO_ROOT, _directory_flags())
        for component in parts:
            try:
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            previous = descriptor
            descriptor = child
            close_error = _close_descriptors(previous)
            if close_error is not None:
                _close_descriptors(previous, descriptor)
                descriptor = -1
                raise CreativeCodeSpecPipelineError(
                    f"{label} could not transfer pinned directory ownership."
                ) from close_error
        return descriptor
    except CreativeCodeSpecPipelineError:
        _close_descriptors(descriptor)
        raise
    except (OSError, NotImplementedError) as exc:
        _close_descriptors(descriptor)
        if isinstance(exc, OSError) and exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise CreativeCodeSpecPipelineError(
                f"{label} must not traverse symlinks or non-directory components."
            ) from exc
        raise CreativeCodeSpecPipelineError(f"{label} could not be opened safely.") from exc


def _open_pinned_parent(
    raw_path: Path, *, allowed_root: Path, create: bool, label: str
) -> tuple[int, str, Path]:
    candidate, parts = _candidate_and_repo_parts(raw_path, allowed_root=allowed_root, label=label)
    parent_fd = _walk_pinned_directory(parts[:-1], create=create, label=label)
    return parent_fd, parts[-1], candidate


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


def _ensure_artifact_root() -> Path:
    _candidate, parts = _candidate_and_repo_parts(
        ARTIFACT_ROOT, allowed_root=ARTIFACT_ROOT, label="artifact root"
    )
    descriptor = _walk_pinned_directory(parts, create=True, label="artifact root")
    close_error = _close_descriptors(descriptor)
    if close_error is not None:
        raise CreativeCodeSpecPipelineError("artifact root could not be closed safely.")
    return ARTIFACT_ROOT


def _resolve_repo_input_file(raw_path: Path) -> Path:
    parent_fd = -1
    try:
        parent_fd, filename, candidate = _open_pinned_parent(
            raw_path, allowed_root=REPO_ROOT, create=False, label="input path"
        )
        info = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise CreativeCodeSpecPipelineError("input path must be a regular file.")
        if candidate.suffix != ".json":
            raise CreativeCodeSpecPipelineError("input path must be a JSON file.")
        return candidate
    except CreativeCodeSpecPipelineError:
        raise
    except (OSError, NotImplementedError) as exc:
        raise CreativeCodeSpecPipelineError("input path must be an existing safe file.") from exc
    finally:
        close_error = _close_descriptors(parent_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeCodeSpecPipelineError("input path could not be closed safely.")


def _resolve_artifact_dir(raw_path: Path, *, create: bool) -> Path:
    _ensure_artifact_root()
    candidate, parts = _candidate_and_repo_parts(
        raw_path, allowed_root=ARTIFACT_ROOT, label="artifact directory"
    )
    descriptor = _walk_pinned_directory(parts, create=create, label="artifact directory")
    close_error = _close_descriptors(descriptor)
    if close_error is not None:
        raise CreativeCodeSpecPipelineError("artifact directory could not be closed safely.")
    return candidate


def _resolve_artifact_file(raw_path: Path, *, for_write: bool) -> Path:
    _ensure_artifact_root()
    parent_fd = -1
    try:
        parent_fd, filename, candidate = _open_pinned_parent(
            raw_path,
            allowed_root=ARTIFACT_ROOT,
            create=for_write,
            label="artifact file",
        )
        if candidate.suffix != ".json":
            raise CreativeCodeSpecPipelineError("artifact file must be JSON.")
        try:
            info = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            if not for_write:
                raise CreativeCodeSpecPipelineError("artifact file must exist.") from None
        else:
            if not stat.S_ISREG(info.st_mode):
                raise CreativeCodeSpecPipelineError("artifact file must be a regular file.")
        return candidate
    except CreativeCodeSpecPipelineError:
        raise
    except (OSError, NotImplementedError) as exc:
        raise CreativeCodeSpecPipelineError("artifact file could not be validated safely.") from exc
    finally:
        close_error = _close_descriptors(parent_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeCodeSpecPipelineError("artifact file could not be closed safely.")


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeSpecPipelineError(
                f"creative-code specification pipeline input has duplicate JSON key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def _read_json_file(path: Path, *, allowed_root: Path, label: str) -> Any:
    parent_fd = -1
    file_fd = -1
    try:
        parent_fd, filename, _candidate = _open_pinned_parent(
            path, allowed_root=allowed_root, create=False, label=label
        )
        flags = os.O_RDONLY | _required_open_flag("O_NOFOLLOW")
        flags |= getattr(os, "O_CLOEXEC", 0)
        file_fd = os.open(filename, flags, dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise CreativeCodeSpecPipelineError(f"{label} must be a regular file.")
        with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
            file_fd = -1
            raw = handle.read()
        return json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeSpecPipelineError:
        raise
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        NotImplementedError,
    ) as exc:
        raise CreativeCodeSpecPipelineError(f"Unable to read safe {label} JSON.") from exc
    finally:
        active_error = sys.exc_info()[1]
        close_error = _close_descriptors(file_fd, parent_fd)
        if active_error is None and close_error is not None:
            raise CreativeCodeSpecPipelineError(f"{label} could not be closed safely.")


def _read_json_artifact(path: Path) -> Any:
    artifact = _resolve_artifact_file(path, for_write=False)
    return _read_json_file(artifact, allowed_root=ARTIFACT_ROOT, label="artifact file")


def _write_json_atomic(path: Path, payload: Any) -> None:
    output = _resolve_artifact_file(path, for_write=True)
    content = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    parent_fd = -1
    file_fd = -1
    temp_name: str | None = None
    try:
        parent_fd, filename, _candidate = _open_pinned_parent(
            output,
            allowed_root=ARTIFACT_ROOT,
            create=True,
            label="artifact file",
        )
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
            raise CreativeCodeSpecPipelineError("unable to allocate artifact temp file")
        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            file_fd = -1
            handle.write(content)
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
    except CreativeCodeSpecPipelineError:
        raise
    except (OSError, NotImplementedError) as exc:
        raise CreativeCodeSpecPipelineError("unable to write artifact safely") from exc
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error: OSError | NotImplementedError | None = None
        if parent_fd >= 0 and temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except (OSError, NotImplementedError) as exc:
                cleanup_error = exc
        close_error = _close_descriptors(file_fd, parent_fd)
        cleanup_error = cleanup_error or close_error
        if active_error is None and cleanup_error is not None:
            raise CreativeCodeSpecPipelineError(
                "unable to clean up artifact safely"
            ) from cleanup_error


def _context_pack_for_packet(packet: dict[str, Any]) -> dict[str, Any]:
    context_pack = build_context_pack_compression(
        candidate_paths=packet["target_surface"],
        required_context=REQUIRED_CONTEXT,
        pr_phase="PR-1",
        domain="orchestration",
        cluster="ops",
        primary_agent="agent-coordinator",
        reviewer="architecture-specialist",
        secondary_agents=_CONTEXT_PACK_SECONDARY_AGENTS,
        requested_agents=_CONTEXT_PACK_REQUESTED_AGENTS,
    )
    return dict(to_stable_mapping(context_pack))


def _require_closed_context_pack_mapping(
    value: Any, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise CreativeCodeSpecPipelineError(
            f"adaptive_source_lineage_mismatch: retained context_pack.json {label} shape changed"
        )
    return value


def _require_historical_non_negative_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json "
            f"{label} must be a non-negative integer"
        )
    return int(value)


def _historical_token_estimate(char_count: int) -> int:
    return 0 if char_count == 0 else max(1, (char_count + 3) // 4)


def _historical_char_bounds(token_estimate: int) -> tuple[int, int]:
    """Return the exact char-count range that can produce one token estimate."""

    if token_estimate == 0:
        return (0, 0)
    return (4 * token_estimate - 3, 4 * token_estimate)


def _canonical_context_pack_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _validate_historical_context_pack(
    value: Any, *, expected_packet: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate one retained context pack without consulting current file sizes."""

    pack = _require_closed_context_pack_mapping(value, keys=_CONTEXT_PACK_KEYS, label="top-level")
    estimate = _require_closed_context_pack_mapping(
        pack["estimate"], keys=_CONTEXT_PACK_ESTIMATE_KEYS, label="estimate"
    )
    graph_nodes = pack["graph_nodes"]
    graph_edges = pack["graph_edges"]
    selected_refs = pack["selected_context_refs"]
    omitted_refs = pack["omitted_duplicate_refs"]
    if not isinstance(graph_nodes, list) or not isinstance(graph_edges, list):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json graph shape changed"
        )
    if not isinstance(selected_refs, list) or not isinstance(omitted_refs, list):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json refs shape changed"
        )

    nodes_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_node in enumerate(graph_nodes):
        node = _require_closed_context_pack_mapping(
            raw_node, keys=_CONTEXT_PACK_NODE_KEYS, label=f"graph_nodes[{index}]"
        )
        token_estimate = _require_historical_non_negative_int(
            node["token_estimate"], label=f"graph_nodes[{index}].token_estimate"
        )
        node_id = node["node_id"]
        if not isinstance(node_id, str) or node_id in nodes_by_id:
            raise CreativeCodeSpecPipelineError(
                "adaptive_source_lineage_mismatch: retained context_pack.json node IDs changed"
            )
        nodes_by_id[node_id] = {**node, "token_estimate": token_estimate}
    for index, raw_edge in enumerate(graph_edges):
        _require_closed_context_pack_mapping(
            raw_edge, keys=_CONTEXT_PACK_EDGE_KEYS, label=f"graph_edges[{index}]"
        )
    selected_chars_minimum = 0
    selected_chars_maximum = 0
    for collection_name, refs in (
        ("selected_context_refs", selected_refs),
        ("omitted_duplicate_refs", omitted_refs),
    ):
        for index, raw_ref in enumerate(refs):
            ref = _require_closed_context_pack_mapping(
                raw_ref,
                keys=_CONTEXT_PACK_REF_KEYS,
                label=f"{collection_name}[{index}]",
            )
            ref_token_estimate = _require_historical_non_negative_int(
                ref["token_estimate"], label=f"{collection_name}[{index}].token_estimate"
            )
            if collection_name == "selected_context_refs":
                lower_bound, upper_bound = _historical_char_bounds(ref_token_estimate)
                selected_chars_minimum += lower_bound
                selected_chars_maximum += upper_bound
            node_id = ref["node_id"]
            if node_id is None:
                continue
            bound_node = nodes_by_id.get(node_id) if isinstance(node_id, str) else None
            if bound_node is None or any(
                ref[key] != bound_node[key]
                for key in ("path", "path_fingerprint", "token_estimate")
            ):
                raise CreativeCodeSpecPipelineError(
                    "adaptive_source_lineage_mismatch: retained context_pack.json "
                    f"{collection_name} node binding changed"
                )

    numeric = {
        key: _require_historical_non_negative_int(estimate[key], label=f"estimate.{key}")
        for key in _CONTEXT_PACK_ESTIMATE_TELEMETRY_KEYS
        if key != "estimate_id"
    }
    fanout = _require_historical_non_negative_int(
        estimate["orchestration_fanout_multiplier"],
        label="estimate.orchestration_fanout_multiplier",
    )
    if fanout < 1:
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json fanout must be positive"
        )
    if numeric["baseline_context_tokens_estimate"] != _historical_token_estimate(
        numeric["baseline_context_chars_estimate"]
    ):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json baseline estimate drifted"
        )
    if not (
        selected_chars_minimum
        <= numeric["baseline_context_chars_estimate"]
        <= selected_chars_maximum
    ):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json "
            "baseline estimate is not bound to selected context refs"
        )
    candidate_metadata_payload = {
        "authority_boundary": pack["authority_boundary"],
        "graph_edges": graph_edges,
        "graph_nodes": graph_nodes,
        "omitted_duplicate_refs": omitted_refs,
        "policy_version": pack["policy_version"],
        "required_context": pack["required_context"],
        "selected_context_refs": selected_refs,
    }
    candidate_chars = len(_canonical_context_pack_json(candidate_metadata_payload))
    if numeric["candidate_context_chars_estimate"] != candidate_chars or numeric[
        "candidate_context_tokens_estimate"
    ] != _historical_token_estimate(candidate_chars):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json candidate estimate drifted"
        )
    saved = max(
        0,
        numeric["baseline_context_tokens_estimate"] - numeric["candidate_context_tokens_estimate"],
    )
    if (
        numeric["tokens_saved_estimate"] != saved
        or numeric["fanout_tokens_saved_estimate"] != saved * fanout
    ):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json estimate arithmetic drifted"
        )
    estimate_identity_payload = {
        key: estimate[key] for key in sorted(_CONTEXT_PACK_ESTIMATE_KEYS - {"estimate_id"})
    }
    expected_estimate_id = f"ctx-estimate:{fingerprint_payload(estimate_identity_payload)[7:31]}"
    if estimate["estimate_id"] != expected_estimate_id:
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json estimate ID drifted"
        )

    normalized_packet = validate_source_candidate_packet(expected_packet)
    pack_identity_payload = {
        "authority_boundary": pack["authority_boundary"],
        "candidate_paths": sorted(set(normalized_packet["target_surface"])),
        "cluster": "ops",
        "domain": "orchestration",
        "estimate": dict(estimate),
        "graph_edges": graph_edges,
        # The builder fingerprints nodes in normalized path order before the
        # dataclass serializes them in node-ID order.
        "graph_nodes": sorted(graph_nodes, key=lambda row: row["path"]),
        "policy_version": pack["policy_version"],
        "pr_phase": "PR-1",
        "primary_agent": "agent-coordinator",
        "reason_codes": pack["reason_codes"],
        "requested_agents": sorted(set(_CONTEXT_PACK_REQUESTED_AGENTS)),
        "required_context": pack["required_context"],
        "reviewer": "architecture-specialist",
        "secondary_agents": sorted(set(_CONTEXT_PACK_SECONDARY_AGENTS)),
    }
    expected_pack_id = f"ctx-pack:{fingerprint_payload(pack_identity_payload)[7:31]}"
    if pack["context_pack_id"] != expected_pack_id:
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained context_pack.json context-pack ID drifted"
        )
    return dict(pack)


def _context_pack_stable_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Remove only repository-size-derived telemetry from a validated context pack."""

    return {
        key: (
            {
                estimate_key: estimate_value
                for estimate_key, estimate_value in value["estimate"].items()
                if estimate_key not in _CONTEXT_PACK_ESTIMATE_TELEMETRY_KEYS
            }
            if key == "estimate"
            else (
                [
                    {
                        row_key: row_value
                        for row_key, row_value in row.items()
                        if row_key != "token_estimate"
                    }
                    for row in value[key]
                ]
                if key in {"graph_nodes", "selected_context_refs", "omitted_duplicate_refs"}
                else item
            )
        )
        for key, item in value.items()
        if key != "context_pack_id"
    }


def build_default_prepare_artifacts(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Build the canonical retained PR-1 prepare snapshot without filesystem reads."""

    normalized_packet = validate_source_candidate_packet(packet)
    variants = build_default_specification_variants(normalized_packet)
    skeptic_reviews = build_pending_skeptic_reviews(
        source_packet=normalized_packet,
        variants=variants,
    )
    return {
        "source_packet.json": normalized_packet,
        "variants.json": variants,
        "skeptic_reviews.json": skeptic_reviews,
        "context_pack.json": _context_pack_for_packet(normalized_packet),
    }


def validate_default_prepare_artifact_snapshots(
    snapshots: Mapping[str, Any], *, expected_packet: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate retained generic PR-1 sidecars against their canonical packet."""

    expected = build_default_prepare_artifacts(expected_packet)
    if list(snapshots) != list(expected):
        raise CreativeCodeSpecPipelineError(
            "adaptive_source_lineage_mismatch: retained prepare artifact set changed"
        )
    for filename, expected_payload in expected.items():
        retained_payload = snapshots[filename]
        if filename == "context_pack.json":
            retained_context_pack = _validate_historical_context_pack(
                retained_payload, expected_packet=expected_packet
            )
            retained_projection = _canonical_context_pack_json(
                _context_pack_stable_projection(retained_context_pack)
            )
            expected_projection = _canonical_context_pack_json(
                _context_pack_stable_projection(expected_payload)
            )
            if retained_projection != expected_projection:
                raise CreativeCodeSpecPipelineError(
                    "adaptive_source_lineage_mismatch: retained context_pack.json "
                    "stable lineage is not canonical"
                )
            continue
        if retained_payload != expected_payload:
            raise CreativeCodeSpecPipelineError(
                f"adaptive_source_lineage_mismatch: retained {filename} is not canonical"
            )
    return {filename: snapshots[filename] for filename in expected}


def prepare(packet_path: Path, run_dir: Path) -> None:
    source_path = _resolve_repo_input_file(packet_path)
    try:
        packet = _read_json_file(source_path, allowed_root=REPO_ROOT, label="input path")
        if not isinstance(packet, dict):
            raise CreativeCodeSpecPipelineError(
                "CreativeCodeCandidatePacket must be a JSON object."
            )
        artifacts = build_default_prepare_artifacts(packet)
    except CreativeCodeContractError as exc:
        raise CreativeCodeSpecPipelineError(str(exc)) from exc
    output_dir = _resolve_artifact_dir(run_dir, create=True)
    for filename, payload in artifacts.items():
        _write_json_atomic(output_dir / filename, payload)


def prepare_exact(packet_path: Path, declarations_path: Path, run_dir: Path) -> None:
    """Prepare PR-1 inputs from complete exact variant declarations."""

    source_path = _resolve_repo_input_file(packet_path)
    declaration_source = _resolve_repo_input_file(declarations_path)
    packet = _read_json_file(source_path, allowed_root=REPO_ROOT, label="input path")
    declarations = _read_json_file(
        declaration_source, allowed_root=REPO_ROOT, label="variant declarations path"
    )
    if not isinstance(packet, dict):
        raise CreativeCodeSpecPipelineError("CreativeCodeCandidatePacket must be a JSON object.")
    if not isinstance(declarations, list):
        raise CreativeCodeSpecPipelineError("exact variant declarations must be a JSON array.")
    normalized_packet = validate_source_candidate_packet(packet)
    variants = build_exact_specification_variants(normalized_packet, declarations)
    skeptic_reviews = build_pending_skeptic_reviews(
        source_packet=normalized_packet,
        variants=variants,
    )
    output_dir = _resolve_artifact_dir(run_dir, create=True)
    _write_json_atomic(output_dir / "source_packet.json", normalized_packet)
    _write_json_atomic(output_dir / "variants.json", variants)
    _write_json_atomic(output_dir / "skeptic_reviews.json", skeptic_reviews)
    _write_json_atomic(
        output_dir / "context_pack.json", _context_pack_for_packet(normalized_packet)
    )


def validate_exact_prepare_artifacts(
    *,
    run_dir: Path,
    expected_packet: Mapping[str, Any],
    expected_variants: Sequence[Mapping[str, Any]],
) -> None:
    """Revalidate all exact PR-1 sidecars for idempotent resume replay."""

    source_dir = _resolve_artifact_dir(run_dir, create=False)
    source_packet = _read_json_artifact(source_dir / "source_packet.json")
    variants = _read_json_artifact(source_dir / "variants.json")
    skeptic_reviews = _read_json_artifact(source_dir / "skeptic_reviews.json")
    context_pack = _read_json_artifact(source_dir / "context_pack.json")
    normalized_packet = validate_source_candidate_packet(expected_packet)
    normalized_variants = [dict(row) for row in expected_variants]
    if source_packet != normalized_packet:
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_source_packet_mismatch: source_packet.json drifted"
        )
    if variants != normalized_variants:
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_variants_mismatch: variants.json drifted"
        )
    expected_reviews = build_pending_skeptic_reviews(
        source_packet=normalized_packet,
        variants=normalized_variants,
    )
    if skeptic_reviews != expected_reviews:
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_reviews_mismatch: skeptic_reviews.json drifted"
        )
    expected_context_pack = _context_pack_for_packet(normalized_packet)
    if context_pack != expected_context_pack:
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_context_mismatch: context_pack.json drifted"
        )


def finalize(run_dir: Path, output: Path) -> None:
    source_dir = _resolve_artifact_dir(run_dir, create=False)
    source_packet = _read_json_artifact(source_dir / "source_packet.json")
    variants = _read_json_artifact(source_dir / "variants.json")
    skeptic_reviews = _read_json_artifact(source_dir / "skeptic_reviews.json")
    if not isinstance(source_packet, dict):
        raise CreativeCodeSpecPipelineError("source_packet.json must be a JSON object.")
    if not isinstance(variants, list):
        raise CreativeCodeSpecPipelineError("variants.json must be a JSON array.")
    if not isinstance(skeptic_reviews, list):
        raise CreativeCodeSpecPipelineError("skeptic_reviews.json must be a JSON array.")
    bundle = build_creative_code_specification_bundle(
        source_packet=source_packet,
        variants=variants,
        skeptic_reviews=skeptic_reviews,
    )
    _write_json_atomic(output, bundle)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--packet", type=Path, required=True)
    prepare_parser.add_argument("--run-dir", type=Path, required=True)

    prepare_exact_parser = subparsers.add_parser("prepare-exact")
    prepare_exact_parser.add_argument("--packet", type=Path, required=True)
    prepare_exact_parser.add_argument("--variant-declarations", type=Path, required=True)
    prepare_exact_parser.add_argument("--run-dir", type=Path, required=True)

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--run-dir", type=Path, required=True)
    finalize_parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args.packet, args.run_dir)
            print(PREPARE_SUCCESS_OUTPUT)
            return 0
        if args.command == "prepare-exact":
            prepare_exact(args.packet, args.variant_declarations, args.run_dir)
            print(PREPARE_SUCCESS_OUTPUT)
            return 0
        if args.command == "finalize":
            finalize(args.run_dir, args.output)
            print(FINALIZE_SUCCESS_OUTPUT)
            return 0
    except (CreativeCodeSpecPipelineError, CreativeCodeSpecificationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
