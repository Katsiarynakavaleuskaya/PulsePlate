#!/usr/bin/env python3
"""Validate and summarize the design bridge coverage inventory."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "design_bridge_coverage_inventory.v1"
REGISTRY_PATH = Path("docs/orchestration/contracts/design_component_registry.v1.json")
VOCABULARY_PATH = Path("docs/design/ui_component_vocabulary.json")

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_of_truth",
    "source_registry",
    "source_vocabulary",
    "authority",
    "coverage_dimensions",
    "records",
}
REQUIRED_AUTHORITY_FIELDS = {"canonical", "reference_only"}
REQUIRED_CANONICAL = {
    "repo code/docs/tests",
    "docs/orchestration/contracts/design_component_registry.v1.json",
    "docs/design/ui_component_vocabulary.json",
}
REFERENCE_ONLY = {"Kimi", "Figma", "Canva", "Penpot", "Storybook", "Code Connect"}
DENIED_CANONICAL = {item.lower() for item in REFERENCE_ONLY} | {
    "google drive",
    "google drive prototype folder",
    "drive folder",
    "prototype folder",
    "screenshot",
    "screenshots",
    "generated code",
    "generated code bundle",
    "generated code bundles",
    "generated brief",
    "generated briefs",
    "external design note",
    "external design notes",
    "desktop export",
    "desktop exports",
}
COVERAGE_DIMENSIONS = [
    "repo_vocabulary",
    "web_runtime",
    "ios_runtime",
    "storybook_review",
    "figma_reference",
    "penpot_reference",
    "code_connect",
    "visual_regression",
    "accessibility_regression",
]
REQUIRED_RECORD_FIELDS = {
    "component_id",
    "canonical_name",
    "registry_status",
    "repo_vocabulary_coverage",
    "web_runtime_coverage",
    "ios_runtime_coverage",
    "storybook_review_coverage",
    "figma_reference_coverage",
    "penpot_reference_coverage",
    "code_connect_coverage",
    "visual_regression_decision",
    "accessibility_regression_decision",
    "implementation_blocked_reason",
    "next_required_gate",
    "evidence_anchors",
}
COVERAGE_STATUSES = {"covered", "partial", "missing", "unspecified"}
STATUS_FIELDS = {
    "repo_vocabulary_coverage",
    "web_runtime_coverage",
    "ios_runtime_coverage",
    "storybook_review_coverage",
    "figma_reference_coverage",
    "penpot_reference_coverage",
    "code_connect_coverage",
    "visual_regression_decision",
    "accessibility_regression_decision",
}
REFERENCE_TOOLS = {"kimi", "figma", "canva", "penpot", "storybook", "code connect"}


class InventoryError(ValueError):
    """Raised when bridge coverage inventory validation fails."""


def _repo_path(path: str | Path, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{label}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise InventoryError(f"{label}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise InventoryError(f"{label}: cannot read file: {exc}") from exc
    if not isinstance(data, dict):
        raise InventoryError(f"{label}: expected JSON object")
    return data


def _load_json_array(path: Path, *, label: str) -> list[Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{label}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise InventoryError(f"{label}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise InventoryError(f"{label}: cannot read file: {exc}") from exc
    if not isinstance(data, list):
        raise InventoryError(f"{label}: expected JSON array")
    return data


def _normalize_authority(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _check_empty_or_null(value: Any, *, path: str, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{path}: null is forbidden; use 'unspecified'")
        return
    if isinstance(value, str):
        if value == "":
            errors.append(f"{path}: empty string is forbidden; use 'unspecified'")
        if value.lower() in {"unknown", "n/a", "tbd"}:
            errors.append(f"{path}: use exact 'unspecified' for unknown values")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_empty_or_null(item, path=f"{path}[{index}]", errors=errors)
    if isinstance(value, dict):
        for key, item in value.items():
            _check_empty_or_null(item, path=f"{path}.{key}", errors=errors)


def _load_registry(repo_root: Path) -> list[dict[str, Any]]:
    registry = _load_json_object(repo_root / REGISTRY_PATH, label=str(REGISTRY_PATH))
    components = registry.get("components")
    if not isinstance(components, list):
        raise InventoryError(f"{REGISTRY_PATH}: components must be a list")
    if not all(isinstance(item, dict) for item in components):
        raise InventoryError(f"{REGISTRY_PATH}: each component must be an object")
    for index, component in enumerate(components):
        component_id = component.get("component_id")
        if not isinstance(component_id, str):
            raise InventoryError(
                f"{REGISTRY_PATH}: components[{index}].component_id must be a string"
            )
    return components


def _load_vocabulary(repo_root: Path) -> dict[str, dict[str, Any]]:
    raw = _load_json_array(repo_root / VOCABULARY_PATH, label=str(VOCABULARY_PATH))
    vocabulary: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise InventoryError(f"{VOCABULARY_PATH}: item {index} requires string id")
        item_id = item["id"]
        if item_id in vocabulary:
            raise InventoryError(f"{VOCABULARY_PATH}: duplicate id {item_id!r} at item {index}")
        vocabulary[item_id] = item
    return vocabulary


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
    if not REQUIRED_CANONICAL.issubset(canonical_set):
        errors.append("authority.canonical: missing required repo source-of-truth entries")
    reference_set = set(reference_only)
    if not REFERENCE_ONLY.issubset(reference_set):
        errors.append("authority.reference_only: missing required reference-only tools")
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
            "authority.canonical: reference tools must not be canonical: " + ", ".join(promoted)
        )


def _expected_web_coverage(component: dict[str, Any], *, prefix: str, errors: list[str]) -> str:
    web_anchor = component.get("web_runtime_anchor")
    if not isinstance(web_anchor, str) or not web_anchor:
        errors.append(f"{prefix}.registry.web_runtime_anchor: expected non-empty string")
        return "missing"
    return "partial" if web_anchor != "unspecified" else "missing"


def _repo_evidence_file_exists(anchor: str, repo_root: Path) -> bool:
    path_text = anchor.split(":", 1)[0]
    path = repo_root / path_text
    try:
        path.resolve(strict=False).relative_to(repo_root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return path.is_file()


def _validate_record(
    record: dict[str, Any],
    *,
    index: int,
    component: dict[str, Any],
    vocabulary: dict[str, dict[str, Any]],
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
    _check_empty_or_null(record, path=prefix, errors=errors)
    component_id = record["component_id"]
    if component_id != component.get("component_id"):
        errors.append(
            f"{prefix}.component_id: expected registry order id {component.get('component_id')!r}"
        )
        return
    if component_id not in vocabulary:
        errors.append(f"{prefix}.component_id: unknown vocabulary id {component_id!r}")
    if record["canonical_name"] != component.get("canonical_name"):
        errors.append(f"{prefix}.canonical_name: mismatch with registry")
    registry_status = component.get("status")
    if registry_status not in COVERAGE_STATUSES:
        errors.append(f"{prefix}.registry_status: registry has invalid status {registry_status!r}")
    if record["registry_status"] != registry_status:
        errors.append(f"{prefix}.registry_status: mismatch with registry")
    for field in STATUS_FIELDS:
        if not isinstance(record[field], str) or record[field] not in COVERAGE_STATUSES:
            errors.append(f"{prefix}.{field}: invalid coverage status {record[field]!r}")
    if record["repo_vocabulary_coverage"] != "covered":
        errors.append(f"{prefix}.repo_vocabulary_coverage: expected 'covered'")
    if record["web_runtime_coverage"] != _expected_web_coverage(
        component, prefix=prefix, errors=errors
    ):
        errors.append(f"{prefix}.web_runtime_coverage: mismatch with registry web anchor")
    for field in (
        "ios_runtime_coverage",
        "storybook_review_coverage",
        "figma_reference_coverage",
        "penpot_reference_coverage",
        "code_connect_coverage",
    ):
        if record[field] != "unspecified":
            errors.append(
                f"{prefix}.{field}: expected 'unspecified' without repo-confirmed evidence"
            )
    if record["visual_regression_decision"] not in {"missing", "unspecified"}:
        errors.append(
            f"{prefix}.visual_regression_decision: expected fail-closed missing/unspecified"
        )
    if record["accessibility_regression_decision"] not in {"missing", "unspecified"}:
        errors.append(
            f"{prefix}.accessibility_regression_decision: expected fail-closed missing/unspecified"
        )
    if not isinstance(record["implementation_blocked_reason"], str):
        errors.append(f"{prefix}.implementation_blocked_reason: expected string")
        reason = ""
    else:
        reason = record["implementation_blocked_reason"].lower()
    if "block" not in reason or "visual" not in reason or "accessibility" not in reason:
        errors.append(
            f"{prefix}.implementation_blocked_reason: must block implementation on visual/accessibility gates"
        )
    next_gate = record["next_required_gate"]
    if next_gate != "visual regression decision gate":
        errors.append(f"{prefix}.next_required_gate: must be visual regression decision gate")
    anchors = record["evidence_anchors"]
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


def validate_inventory(path: str | Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return validation errors for a bridge coverage inventory path."""
    inventory_path = _repo_path(path, repo_root)
    errors: list[str] = []
    try:
        inventory = _load_json_object(inventory_path, label=str(inventory_path))
    except InventoryError as exc:
        return [str(exc)]
    missing = REQUIRED_TOP_LEVEL_FIELDS - inventory.keys()
    unexpected = inventory.keys() - REQUIRED_TOP_LEVEL_FIELDS
    if missing:
        errors.append("inventory: missing required fields: " + ", ".join(sorted(missing)))
    if unexpected:
        errors.append("inventory: unexpected fields: " + ", ".join(sorted(unexpected)))
    if inventory.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}")
    if inventory.get("source_of_truth") != "repo":
        errors.append("source_of_truth: expected 'repo'")
    if inventory.get("source_registry") != str(REGISTRY_PATH):
        errors.append(f"source_registry: expected {str(REGISTRY_PATH)!r}")
    if inventory.get("source_vocabulary") != str(VOCABULARY_PATH):
        errors.append(f"source_vocabulary: expected {str(VOCABULARY_PATH)!r}")
    if inventory.get("coverage_dimensions") != COVERAGE_DIMENSIONS:
        errors.append("coverage_dimensions: unexpected dimensions or order")
    _validate_authority(inventory.get("authority"), errors)
    _check_empty_or_null(inventory, path="inventory", errors=errors)
    try:
        registry_components = _load_registry(repo_root)
        vocabulary = _load_vocabulary(repo_root)
        dependency_load_failed = False
    except InventoryError as exc:
        errors.append(str(exc))
        registry_components = []
        vocabulary = {}
        dependency_load_failed = True
    records = inventory.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records: expected non-empty list")
        return errors
    if dependency_load_failed:
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
        if index >= len(registry_components):
            errors.append(f"records[{index}].component_id: inventory component not in registry")
            continue
        _validate_record(
            record,
            index=index,
            component=registry_components[index],
            vocabulary=vocabulary,
            repo_root=repo_root,
            errors=errors,
        )
    registry_ids = {component.get("component_id") for component in registry_components}
    missing_registry_ids = sorted(str(item) for item in registry_ids - seen if item)
    if missing_registry_ids:
        errors.append("records: missing registry components: " + ", ".join(missing_registry_ids))
    extra_ids = sorted(seen - {str(item) for item in registry_ids if item})
    if extra_ids:
        errors.append("records: inventory components not in registry: " + ", ".join(extra_ids))
    vocabulary_ids = set(vocabulary)
    registry_id_strings = {str(item) for item in registry_ids if item}
    extra_vocabulary_ids = sorted(vocabulary_ids - registry_id_strings)
    if extra_vocabulary_ids:
        errors.append(
            "records: vocabulary ids missing from registry: " + ", ".join(extra_vocabulary_ids)
        )
    return errors


def summarize_inventory(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return deterministic summary for a valid bridge coverage inventory."""
    errors = validate_inventory(path, repo_root=repo_root)
    if errors:
        raise InventoryError("; ".join(errors))
    inventory = _load_json_object(_repo_path(path, repo_root), label=str(path))
    records = inventory["records"]
    coverage_counts: dict[str, dict[str, int]] = {}
    for field in sorted(field for field in STATUS_FIELDS if field.endswith("_coverage")):
        coverage_counts[field] = dict(sorted(Counter(record[field] for record in records).items()))
    blocked = sum(
        1 for record in records if "block" in record["implementation_blocked_reason"].lower()
    )
    next_gate_counts = dict(
        sorted(Counter(record["next_required_gate"] for record in records).items())
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_count": len(records),
        "coverage_counts": coverage_counts,
        "blocked_for_implementation": blocked,
        "next_required_gate_counts": next_gate_counts,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate a bridge coverage inventory")
    validate.add_argument("path")
    summarize = subparsers.add_parser("summarize", help="print deterministic summary")
    summarize.add_argument("path")
    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        errors = validate_inventory(args.path)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("PASS: design bridge coverage inventory valid", file=stdout)
        return 0
    if args.command == "summarize":
        try:
            summary = summarize_inventory(args.path)
        except InventoryError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, sort_keys=True), file=stdout)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
