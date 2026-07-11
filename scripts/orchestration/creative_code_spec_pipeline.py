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


class CreativeCodeSpecPipelineError(ValueError):
    """Raised when the local PR-1 pipeline cannot safely read or write artifacts."""


def _json_payloads_equal(observed: Any, expected: Any) -> bool:
    try:
        return fingerprint_payload(observed) == fingerprint_payload(expected)
    except (TypeError, ValueError):
        return False


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
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, NotImplementedError) as exc:
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
        secondary_agents=(
            "ai-innovation-specialist",
            "security-auditor",
            "qa-engineer-agent",
            "logic-agent",
            "epistemology-discovery-agent",
            "bug-hunter",
            "cursor-specialist-agent",
        ),
        requested_agents=(
            "agent-coordinator",
            "ai-innovation-specialist",
            "architecture-specialist",
            "security-auditor",
            "qa-engineer-agent",
            "logic-agent",
            "epistemology-discovery-agent",
            "bug-hunter",
            "cursor-specialist-agent",
        ),
    )
    return dict(to_stable_mapping(context_pack))


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
        if not _json_payloads_equal(snapshots[filename], expected_payload):
            raise CreativeCodeSpecPipelineError(
                f"adaptive_source_lineage_mismatch: retained {filename} is not canonical"
            )
    return expected


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
    snapshots = {
        "source_packet.json": _read_json_artifact(source_dir / "source_packet.json"),
        "variants.json": _read_json_artifact(source_dir / "variants.json"),
        "skeptic_reviews.json": _read_json_artifact(source_dir / "skeptic_reviews.json"),
        "context_pack.json": _read_json_artifact(source_dir / "context_pack.json"),
    }
    validate_exact_prepare_artifact_snapshots(
        snapshots=snapshots,
        expected_packet=expected_packet,
        expected_variants=expected_variants,
    )


def validate_exact_prepare_artifact_snapshots(
    *,
    snapshots: Mapping[str, Any],
    expected_packet: Mapping[str, Any],
    expected_variants: Sequence[Mapping[str, Any]],
) -> None:
    """Recompute exact PR-1 sidecars from descriptor-bound JSON snapshots."""

    expected_names = (
        "source_packet.json",
        "variants.json",
        "skeptic_reviews.json",
        "context_pack.json",
    )
    if set(snapshots) != set(expected_names):
        raise CreativeCodeSpecPipelineError(
            "adaptive_partial_output: fixed exact prepare artifact set required"
        )
    source_packet = snapshots["source_packet.json"]
    variants = snapshots["variants.json"]
    skeptic_reviews = snapshots["skeptic_reviews.json"]
    context_pack = snapshots["context_pack.json"]
    normalized_packet = validate_source_candidate_packet(expected_packet)
    normalized_variants = [dict(row) for row in expected_variants]
    if not _json_payloads_equal(source_packet, normalized_packet):
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_source_packet_mismatch: source_packet.json drifted"
        )
    if not _json_payloads_equal(variants, normalized_variants):
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_variants_mismatch: variants.json drifted"
        )
    expected_reviews = build_pending_skeptic_reviews(
        source_packet=normalized_packet,
        variants=normalized_variants,
    )
    if not _json_payloads_equal(skeptic_reviews, expected_reviews):
        raise CreativeCodeSpecPipelineError(
            "adaptive_prepare_reviews_mismatch: skeptic_reviews.json drifted"
        )
    expected_context_pack = _context_pack_for_packet(normalized_packet)
    if not _json_payloads_equal(context_pack, expected_context_pack):
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
