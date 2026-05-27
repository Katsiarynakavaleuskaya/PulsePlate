#!/usr/bin/env python3
"""Validate and summarize the design token/runtime parity boundary."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "design_token_runtime_parity_boundary.v1"
REGISTRY_PATH = Path("docs/orchestration/contracts/design_component_registry.v1.json")
BRIDGE_INVENTORY_PATH = Path(
    "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json"
)
VISUAL_DECISIONS_PATH = Path(
    "docs/orchestration/contracts/design_visual_regression_decisions.v1.json"
)
ACCESSIBILITY_DECISIONS_PATH = Path(
    "docs/orchestration/contracts/design_accessibility_regression_decisions.v1.json"
)
NEXT_REQUIRED_GATE = "first bounded frontend MVP product slice"

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_of_truth",
    "source_registry",
    "source_bridge_inventory",
    "source_visual_decisions",
    "source_accessibility_decisions",
    "authority",
    "parity_dimensions",
    "records",
    "next_required_gate",
}
REQUIRED_AUTHORITY_FIELDS = {"canonical", "reference_only"}
REQUIRED_CANONICAL = {
    "repo code/docs/tests",
    "tokens/**",
    "frontend/src/styles/tokens.css",
    "frontend/src/styles/tokens.ts",
    "ios/PulsePlate/DesignSystem/DesignTokens.generated.swift",
    "ios/PulsePlate/DesignSystem/DesignTokens.swift",
    str(REGISTRY_PATH),
    str(BRIDGE_INVENTORY_PATH),
    str(VISUAL_DECISIONS_PATH),
    str(ACCESSIBILITY_DECISIONS_PATH),
    "docs/design/ui_component_vocabulary.json",
}
REFERENCE_ONLY = {
    "Figma",
    "Canva",
    "Penpot",
    "Kimi",
    "Storybook",
    "Code Connect",
    "screenshots",
    "generated design exports",
    "prompt outputs",
}
DENIED_CANONICAL = {item.lower() for item in REFERENCE_ONLY} | {
    "google drive",
    "screenshot",
    "generated code",
    "generated bundle",
    "desktop export",
    "external design note",
    "prompt output",
}
PARITY_DIMENSIONS = [
    "token_authoring_status",
    "web_runtime_status",
    "ios_runtime_status",
    "generated_mirror_status",
    "visual_decision_anchor",
    "accessibility_decision_anchor",
    "implementation_readiness",
]
REQUIRED_RECORD_FIELDS = {
    "component_id",
    "canonical_name",
    "repo_vocabulary_anchor",
    "token_dependencies",
    "web_runtime_token_anchor",
    "ios_runtime_token_anchor",
    "web_runtime_component_anchor",
    "ios_runtime_component_anchor",
    "visual_decision_anchor",
    "accessibility_decision_anchor",
    "token_authoring_status",
    "web_runtime_status",
    "ios_runtime_status",
    "generated_mirror_status",
    "implementation_readiness",
    "implementation_blocked_reason",
    "next_required_gate",
    "evidence_anchors",
}
STATUS_VALUES = {"ready", "blocked", "deferred", "missing", "unspecified"}
REFERENCE_TOOLS = {item.lower() for item in REFERENCE_ONLY} | {"google drive", "desktop export"}
RUNTIME_PERMISSION_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"runtime\s+implementation\s+(is\s+)?(allowed|permitted|approved|unblocked)",
        r"permission\s+to\s+implement",
        r"may\s+implement\s+runtime",
        r"can\s+implement\s+runtime",
        r"web/iOS\s+implementation\s+may\s+start",
    )
]


class TokenRuntimeParityBoundaryError(ValueError):
    """Raised when token/runtime parity boundary validation fails."""


def _repo_path(path: str | Path, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise TokenRuntimeParityBoundaryError(f"{label}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise TokenRuntimeParityBoundaryError(f"{label}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise TokenRuntimeParityBoundaryError(f"{label}: cannot read file: {exc}") from exc
    if not isinstance(data, dict):
        raise TokenRuntimeParityBoundaryError(f"{label}: expected JSON object")
    return data


def _load_records(
    repo_root: Path, path: Path, *, label: str, records_key: str = "records"
) -> list[dict[str, Any]]:
    payload = _load_json_object(repo_root / path, label=str(path))
    records = payload.get(records_key)
    if not isinstance(records, list):
        raise TokenRuntimeParityBoundaryError(f"{label}: {records_key} must be a list")
    if not all(isinstance(item, dict) for item in records):
        raise TokenRuntimeParityBoundaryError(f"{label}: each record must be an object")
    return records


def _normalize_authority(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _check_empty_null_or_unknown(value: Any, *, path: str, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{path}: null is forbidden; use 'unspecified'")
        return
    if isinstance(value, str):
        if value == "":
            errors.append(f"{path}: empty string is forbidden; use 'unspecified'")
        if value.lower() in {"unknown", "n/a", "tbd"}:
            errors.append(f"{path}: use exact 'unspecified' for unknown values")
        for pattern in RUNTIME_PERMISSION_PATTERNS:
            if pattern.search(value):
                errors.append(f"{path}: must not grant runtime implementation permission")
                break
        normalized = _normalize_authority(value)
        if re.search(
            r"generated\s+(mirror|mirrors|token\s+mirror|token\s+mirrors)\s+"
            r"(are|is|become|becomes|as)\s+(the\s+)?(authoring|source\s+of\s+truth)",
            normalized,
        ):
            errors.append(f"{path}: generated mirrors must not be treated as authoring truth")
        if "mutate token" in value.lower() or "edit token values" in value.lower():
            errors.append(f"{path}: token/runtime parity must not mutate token values")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_empty_null_or_unknown(item, path=f"{path}[{index}]", errors=errors)
    if isinstance(value, dict):
        for key, item in value.items():
            _check_empty_null_or_unknown(item, path=f"{path}.{key}", errors=errors)


def _validate_authority(authority: Any, errors: list[str]) -> None:
    if not isinstance(authority, dict):
        errors.append("authority: expected object")
        return
    if authority.keys() != REQUIRED_AUTHORITY_FIELDS:
        errors.append("authority: expected fields canonical, reference_only")
        return
    canonical = authority.get("canonical")
    reference_only = authority.get("reference_only")
    if not isinstance(canonical, list) or not all(isinstance(item, str) for item in canonical):
        errors.append("authority.canonical: expected list of strings")
        canonical = []
    if not isinstance(reference_only, list) or not all(
        isinstance(item, str) for item in reference_only
    ):
        errors.append("authority.reference_only: expected list of strings")
        reference_only = []
    canonical_set = set(canonical)
    if canonical_set != REQUIRED_CANONICAL:
        missing = sorted(REQUIRED_CANONICAL - canonical_set)
        unexpected = sorted(canonical_set - REQUIRED_CANONICAL)
        if missing:
            errors.append("authority.canonical: missing " + ", ".join(missing))
        if unexpected:
            errors.append("authority.canonical: unexpected " + ", ".join(unexpected))
    reference_set = set(reference_only)
    if reference_set != REFERENCE_ONLY:
        missing = sorted(REFERENCE_ONLY - reference_set)
        unexpected = sorted(reference_set - REFERENCE_ONLY)
        if missing:
            errors.append("authority.reference_only: missing " + ", ".join(missing))
        if unexpected:
            errors.append("authority.reference_only: unexpected " + ", ".join(unexpected))
    promoted = []
    for entry in canonical:
        normalized = _normalize_authority(entry)
        if any(
            re.search(rf"(?<![a-z0-9]){re.escape(denied)}(?![a-z0-9])", normalized)
            for denied in DENIED_CANONICAL
        ):
            promoted.append(entry)
    if promoted:
        errors.append(
            "authority.canonical: reference artifacts must not be canonical: " + ", ".join(promoted)
        )


def _repo_evidence_file_exists(anchor: str, repo_root: Path) -> bool:
    path_text = anchor.split(":", 1)[0]
    path = repo_root / path_text
    try:
        path.resolve(strict=False).relative_to(repo_root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    if "**" in path_text:
        return bool(list(repo_root.glob(path_text)))
    return path.is_file()


def _validate_evidence_anchors(
    anchors: Any, *, prefix: str, repo_root: Path, errors: list[str]
) -> None:
    if (
        not isinstance(anchors, list)
        or not anchors
        or not all(isinstance(item, str) for item in anchors)
    ):
        errors.append(f"{prefix}.evidence_anchors: expected non-empty list of strings")
        return
    for anchor in anchors:
        normalized = _normalize_authority(anchor)
        if any(tool in normalized for tool in REFERENCE_TOOLS):
            errors.append(
                f"{prefix}.evidence_anchors: reference-tool evidence is not canonical: {anchor!r}"
            )
        if not re.match(r"^(docs|scripts|tests|frontend|ios|tokens)/", anchor):
            errors.append(f"{prefix}.evidence_anchors: expected repo evidence anchor: {anchor!r}")
        elif not _repo_evidence_file_exists(anchor, repo_root):
            errors.append(
                f"{prefix}.evidence_anchors: repo evidence file does not exist: {anchor!r}"
            )


def _validate_status(record: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = record.get(field)
    if not isinstance(value, str) or value not in STATUS_VALUES:
        errors.append(f"{prefix}.{field}: invalid value {value!r}")


def _validate_record(
    record: dict[str, Any],
    *,
    index: int,
    registry_record: dict[str, Any],
    bridge_record: dict[str, Any],
    visual_record: dict[str, Any],
    accessibility_record: dict[str, Any],
    repo_root: Path,
    errors: list[str],
) -> None:
    prefix = f"records[{index}]"
    if record.keys() != REQUIRED_RECORD_FIELDS:
        missing = REQUIRED_RECORD_FIELDS - record.keys()
        unexpected = record.keys() - REQUIRED_RECORD_FIELDS
        if missing:
            errors.append(f"{prefix}: missing required fields: {', '.join(sorted(missing))}")
        if unexpected:
            errors.append(f"{prefix}: unexpected fields: {', '.join(sorted(unexpected))}")
        return
    _check_empty_null_or_unknown(record, path=prefix, errors=errors)
    component_id = record["component_id"]
    expected_id = registry_record.get("component_id")
    if component_id != expected_id:
        errors.append(f"{prefix}.component_id: expected registry id {expected_id!r}")
        return
    if component_id != bridge_record.get("component_id"):
        errors.append(f"{prefix}.component_id: mismatch with bridge inventory")
    if component_id != visual_record.get("component_id"):
        errors.append(f"{prefix}.component_id: mismatch with visual decisions")
    if component_id != accessibility_record.get("component_id"):
        errors.append(f"{prefix}.component_id: mismatch with accessibility decisions")
    if record["canonical_name"] != registry_record.get("canonical_name"):
        errors.append(f"{prefix}.canonical_name: mismatch with registry")
    if record["repo_vocabulary_anchor"] != registry_record.get("repo_vocabulary_anchor"):
        errors.append(f"{prefix}.repo_vocabulary_anchor: mismatch with registry")
    if record["web_runtime_component_anchor"] != registry_record.get("web_runtime_anchor"):
        errors.append(f"{prefix}.web_runtime_component_anchor: mismatch with registry")
    if record["ios_runtime_component_anchor"] != registry_record.get("ios_runtime_anchor"):
        errors.append(f"{prefix}.ios_runtime_component_anchor: mismatch with registry")
    expected_visual = f"{VISUAL_DECISIONS_PATH}:{component_id}"
    expected_accessibility = f"{ACCESSIBILITY_DECISIONS_PATH}:{component_id}"
    if record["visual_decision_anchor"] != expected_visual:
        errors.append(f"{prefix}.visual_decision_anchor: expected {expected_visual!r}")
    if record["accessibility_decision_anchor"] != expected_accessibility:
        errors.append(
            f"{prefix}.accessibility_decision_anchor: expected {expected_accessibility!r}"
        )
    if accessibility_record.get("visual_decision_anchor") != expected_visual:
        errors.append(f"{prefix}.visual_decision_anchor: missing accessibility gate linkage")
    for field in (
        "token_authoring_status",
        "web_runtime_status",
        "ios_runtime_status",
        "generated_mirror_status",
        "implementation_readiness",
    ):
        _validate_status(record, field, prefix, errors)
    if record["web_runtime_token_anchor"] != "frontend/src/styles/tokens.css":
        errors.append(f"{prefix}.web_runtime_token_anchor: expected web token runtime SoT")
    if (
        record["ios_runtime_token_anchor"]
        != "ios/PulsePlate/DesignSystem/DesignTokens.generated.swift"
    ):
        errors.append(f"{prefix}.ios_runtime_token_anchor: expected generated iOS token mirror")
    if (
        record["token_authoring_status"] == "ready"
        and record["token_dependencies"] == "unspecified"
    ):
        errors.append(f"{prefix}.token_authoring_status: ready requires token dependencies")
    if record["generated_mirror_status"] == "ready" and record["token_authoring_status"] != "ready":
        errors.append(f"{prefix}.generated_mirror_status: ready requires token authoring readiness")
    if record["implementation_readiness"] == "ready":
        if visual_record.get("visual_regression_decision") != "ready":
            errors.append(f"{prefix}.implementation_readiness: ready requires visual gate")
        if accessibility_record.get("accessibility_regression_decision") != "ready":
            errors.append(f"{prefix}.implementation_readiness: ready requires accessibility gate")
        for field in (
            "token_authoring_status",
            "web_runtime_status",
            "ios_runtime_status",
            "generated_mirror_status",
        ):
            if record[field] != "ready":
                errors.append(f"{prefix}.implementation_readiness: ready requires {field}=ready")
    if record["next_required_gate"] != NEXT_REQUIRED_GATE:
        errors.append(f"{prefix}.next_required_gate: must be {NEXT_REQUIRED_GATE}")
    reason = record["implementation_blocked_reason"]
    if not isinstance(reason, str):
        errors.append(f"{prefix}.implementation_blocked_reason: expected string")
    else:
        lowered = reason.lower()
        required_terms = ["block", "token", "mirror", "visual", "accessibility", "frontend mvp"]
        if not all(term in lowered for term in required_terms):
            errors.append(
                f"{prefix}.implementation_blocked_reason: must block on token, mirror, visual, accessibility, and frontend MVP gates"
            )
    _validate_evidence_anchors(
        record["evidence_anchors"], prefix=prefix, repo_root=repo_root, errors=errors
    )


def validate_boundary(path: str | Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return validation errors for a token/runtime parity boundary path."""
    boundary_path = _repo_path(path, repo_root)
    errors: list[str] = []
    try:
        boundary = _load_json_object(boundary_path, label=str(boundary_path))
    except TokenRuntimeParityBoundaryError as exc:
        return [str(exc)]
    missing = REQUIRED_TOP_LEVEL_FIELDS - boundary.keys()
    unexpected = boundary.keys() - REQUIRED_TOP_LEVEL_FIELDS
    if missing:
        errors.append("boundary: missing required fields: " + ", ".join(sorted(missing)))
    if unexpected:
        errors.append("boundary: unexpected fields: " + ", ".join(sorted(unexpected)))
    if boundary.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}")
    if boundary.get("source_of_truth") != "repo":
        errors.append("source_of_truth: expected 'repo'")
    expected_paths = {
        "source_registry": REGISTRY_PATH,
        "source_bridge_inventory": BRIDGE_INVENTORY_PATH,
        "source_visual_decisions": VISUAL_DECISIONS_PATH,
        "source_accessibility_decisions": ACCESSIBILITY_DECISIONS_PATH,
    }
    for field, expected_path in expected_paths.items():
        if boundary.get(field) != str(expected_path):
            errors.append(f"{field}: expected {str(expected_path)!r}")
        elif not (repo_root / expected_path).is_file():
            errors.append(f"{field}: file not found at '{expected_path}'")
    if boundary.get("parity_dimensions") != PARITY_DIMENSIONS:
        errors.append("parity_dimensions: unexpected dimensions or order")
    if boundary.get("next_required_gate") != NEXT_REQUIRED_GATE:
        errors.append(f"next_required_gate: must be {NEXT_REQUIRED_GATE}")
    _validate_authority(boundary.get("authority"), errors)
    _check_empty_null_or_unknown(boundary, path="boundary", errors=errors)
    try:
        registry_records = _load_records(
            repo_root, REGISTRY_PATH, label=str(REGISTRY_PATH), records_key="components"
        )
        bridge_records = _load_records(
            repo_root, BRIDGE_INVENTORY_PATH, label=str(BRIDGE_INVENTORY_PATH)
        )
        visual_records = _load_records(
            repo_root, VISUAL_DECISIONS_PATH, label=str(VISUAL_DECISIONS_PATH)
        )
        accessibility_records = _load_records(
            repo_root, ACCESSIBILITY_DECISIONS_PATH, label=str(ACCESSIBILITY_DECISIONS_PATH)
        )
    except TokenRuntimeParityBoundaryError as exc:
        errors.append(str(exc))
        registry_records = []
        bridge_records = []
        visual_records = []
        accessibility_records = []
    records = boundary.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records: expected non-empty list")
        return errors
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"records[{index}]: expected object")
            continue
        component_id = record.get("component_id")
        if isinstance(component_id, str):
            if component_id in seen:
                errors.append(f"records[{index}].component_id: duplicate id {component_id!r}")
            seen.add(component_id)
        if index >= len(registry_records):
            errors.append(f"records[{index}].component_id: component not in registry")
            continue
        if (
            index >= len(bridge_records)
            or index >= len(visual_records)
            or index >= len(accessibility_records)
        ):
            errors.append(f"records[{index}].component_id: missing upstream decision record")
            continue
        _validate_record(
            record,
            index=index,
            registry_record=registry_records[index],
            bridge_record=bridge_records[index],
            visual_record=visual_records[index],
            accessibility_record=accessibility_records[index],
            repo_root=repo_root,
            errors=errors,
        )
    registry_ids = {
        str(record.get("component_id")) for record in registry_records if record.get("component_id")
    }
    missing_ids = sorted(registry_ids - seen)
    if missing_ids:
        errors.append("records: missing registry components: " + ", ".join(missing_ids))
    extra_ids = sorted(seen - registry_ids)
    if extra_ids:
        errors.append("records: components not in registry: " + ", ".join(extra_ids))
    return errors


def summarize_boundary(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return a deterministic summary for a valid token/runtime parity boundary."""
    errors = validate_boundary(path, repo_root=repo_root)
    if errors:
        raise TokenRuntimeParityBoundaryError("; ".join(errors))
    boundary = _load_json_object(_repo_path(path, repo_root), label=str(path))
    records = boundary["records"]
    fields = (
        "token_authoring_status",
        "web_runtime_status",
        "ios_runtime_status",
        "generated_mirror_status",
        "implementation_readiness",
    )
    status_counts = {
        field: dict(sorted(Counter(record[field] for record in records).items()))
        for field in fields
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_count": len(records),
        "status_counts": status_counts,
        "blocked_for_implementation": sum(
            1 for record in records if record["implementation_readiness"] == "blocked"
        ),
        "next_required_gate_counts": dict(
            sorted(Counter(record["next_required_gate"] for record in records).items())
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate token/runtime parity boundary")
    validate.add_argument("path")
    summarize = subparsers.add_parser("summarize", help="print deterministic summary")
    summarize.add_argument("path")
    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        errors = validate_boundary(args.path)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("PASS: design token/runtime parity boundary valid", file=stdout)
        return 0
    if args.command == "summarize":
        try:
            summary = summarize_boundary(args.path)
        except TokenRuntimeParityBoundaryError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, sort_keys=True), file=stdout)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
