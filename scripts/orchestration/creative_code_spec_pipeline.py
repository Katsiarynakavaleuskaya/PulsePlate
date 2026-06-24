"""Local prepare/finalize CLI for PR-1 creative-code specification bundles."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

from scripts.orchestration.context_pack_compression import (
    build_context_pack_compression,
    to_stable_mapping,
)
from scripts.orchestration.creative_code_contract import (
    CreativeCodeContractError,
    read_creative_code_candidate_packet,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
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


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current = path.anchor
    if not current:
        current_path = Path(".")
    else:
        current_path = Path(current)
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodeSpecPipelineError(f"{label} must not traverse symlinks.")


def _ensure_artifact_root() -> Path:
    _reject_symlink_components(ARTIFACT_ROOT, label="artifact root")
    try:
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodeSpecPipelineError("artifact root could not be created.") from exc
    _reject_symlink_components(ARTIFACT_ROOT, label="artifact root")
    root = ARTIFACT_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodeSpecPipelineError("artifact root must be a directory.")
    return root


def _resolve_repo_input_file(raw_path: Path) -> Path:
    path = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(path, label="input path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeSpecPipelineError("input path must be an existing file.") from exc
    repo_root = REPO_ROOT.resolve()
    if not _is_relative_to(resolved, repo_root):
        raise CreativeCodeSpecPipelineError("input path must stay inside the repository.")
    if not resolved.is_file():
        raise CreativeCodeSpecPipelineError("input path must be a file.")
    if resolved.suffix != ".json":
        raise CreativeCodeSpecPipelineError("input path must be a JSON file.")
    return resolved


def _resolve_artifact_dir(raw_path: Path, *, create: bool) -> Path:
    root = _ensure_artifact_root()
    path = raw_path if raw_path.is_absolute() else ARTIFACT_ROOT / raw_path
    if path.is_absolute():
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise CreativeCodeSpecPipelineError(
                "artifact directory must stay under creative-code artifacts."
            ) from exc
    _reject_symlink_components(path, label="artifact directory")
    candidate_resolved = path.resolve(strict=False)
    if not _is_relative_to(candidate_resolved, root):
        raise CreativeCodeSpecPipelineError(
            "artifact directory must stay under creative-code artifacts."
        )
    if create:
        path.mkdir(parents=True, exist_ok=True)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeSpecPipelineError("artifact directory must exist.") from exc
    if not _is_relative_to(resolved, root):
        raise CreativeCodeSpecPipelineError(
            "artifact directory must stay under creative-code artifacts."
        )
    if not resolved.is_dir():
        raise CreativeCodeSpecPipelineError("artifact directory must be a directory.")
    return resolved


def _resolve_artifact_file(raw_path: Path, *, for_write: bool) -> Path:
    root = _ensure_artifact_root()
    path = raw_path if raw_path.is_absolute() else ARTIFACT_ROOT / raw_path
    if path.is_absolute():
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise CreativeCodeSpecPipelineError(
                "artifact file must stay under creative-code artifacts."
            ) from exc
    parent = path.parent
    _reject_symlink_components(parent, label="artifact file parent")
    parent_candidate = parent.resolve(strict=False)
    if not _is_relative_to(parent_candidate, root):
        raise CreativeCodeSpecPipelineError(
            "artifact file must stay under creative-code artifacts."
        )
    if for_write:
        parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(parent, label="artifact file parent")
    try:
        parent_resolved = parent.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeSpecPipelineError("artifact file parent must exist.") from exc
    if not _is_relative_to(parent_resolved, root):
        raise CreativeCodeSpecPipelineError(
            "artifact file must stay under creative-code artifacts."
        )
    if path.exists() or path.is_symlink():
        _reject_symlink_components(path, label="artifact file")
        if path.is_symlink():
            raise CreativeCodeSpecPipelineError("artifact file must not be a symlink.")
    if path.suffix != ".json":
        raise CreativeCodeSpecPipelineError("artifact file must be JSON.")
    return parent_resolved / path.name


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


def _read_json_artifact(path: Path) -> Any:
    artifact = _resolve_artifact_file(path, for_write=False)
    try:
        return json.loads(
            artifact.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeSpecPipelineError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeSpecPipelineError(
            "Unable to read creative-code specification pipeline JSON."
        ) from exc


def _write_json_atomic(path: Path, payload: Any) -> None:
    output = _resolve_artifact_file(path, for_write=True)
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
            json.dump(payload, temp_file, sort_keys=True, indent=2)
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


def prepare(packet_path: Path, run_dir: Path) -> None:
    source_path = _resolve_repo_input_file(packet_path)
    try:
        packet = read_creative_code_candidate_packet(source_path)
        normalized_packet = validate_source_candidate_packet(packet)
    except CreativeCodeContractError as exc:
        raise CreativeCodeSpecPipelineError(str(exc)) from exc
    variants = build_default_specification_variants(normalized_packet)
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
