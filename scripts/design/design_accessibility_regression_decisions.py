#!/usr/bin/env python3
"""Validate and summarize design accessibility regression decisions."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
try:
    from scripts.design import design_visual_regression_decisions as _visual_decisions_package
except ModuleNotFoundError:
    import design_visual_regression_decisions as _visual_decisions_script

    design_visual_regression_decisions = _visual_decisions_script
else:
    design_visual_regression_decisions = _visual_decisions_package
SCHEMA_VERSION = "design_accessibility_regression_decisions.v1"
BRIDGE_INVENTORY_PATH = Path(
    "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json"
)
REGISTRY_PATH = Path("docs/orchestration/contracts/design_component_registry.v1.json")
VISUAL_DECISIONS_PATH = Path(
    "docs/orchestration/contracts/design_visual_regression_decisions.v1.json"
)

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_of_truth",
    "source_bridge_inventory",
    "source_registry",
    "source_visual_decisions",
    "authority",
    "decision_dimensions",
    "records",
}
REQUIRED_AUTHORITY_FIELDS = {"canonical", "reference_only"}
REQUIRED_CANONICAL = {
    "repo code/docs/tests",
    "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json",
    "docs/orchestration/contracts/design_component_registry.v1.json",
    "docs/orchestration/contracts/design_visual_regression_decisions.v1.json",
    "docs/design/ui_component_vocabulary.json",
}
REFERENCE_ONLY = {
    "Kimi",
    "Figma",
    "Canva",
    "Penpot",
    "Storybook",
    "Code Connect",
    "screenshots",
    "generated design exports",
    "prompt outputs",
}
DENIED_CANONICAL = {item.lower() for item in REFERENCE_ONLY} | {
    "google drive",
    "google drive prototype folder",
    "drive folder",
    "prototype folder",
    "screenshot",
    "generated code",
    "generated code bundle",
    "generated code bundles",
    "generated brief",
    "generated briefs",
    "external design note",
    "external design notes",
    "desktop export",
    "desktop exports",
    "binary asset",
    "binary assets",
    "prompt output",
}
DECISION_DIMENSIONS = [
    "accessibility_regression_decision",
    "keyboard_focus_policy",
    "semantic_role_name_value_policy",
    "aria_status_live_region_policy",
    "reduced_motion_policy",
    "non_color_only_semantics_policy",
    "touch_target_policy",
    "state_accessibility_policy",
    "ios_voiceover_dynamic_type_policy",
    "web_screen_reader_policy",
    "implementation_readiness",
]
REQUIRED_RECORD_FIELDS = {
    "component_id",
    "canonical_name",
    "bridge_inventory_anchor",
    "visual_decision_anchor",
    "accessibility_regression_decision",
    "keyboard_focus_policy",
    "semantic_role_name_value_policy",
    "aria_status_live_region_policy",
    "reduced_motion_policy",
    "non_color_only_semantics_policy",
    "touch_target_policy",
    "state_accessibility_policy",
    "ios_voiceover_dynamic_type_policy",
    "web_screen_reader_policy",
    "implementation_readiness",
    "implementation_blocked_reason",
    "next_required_gate",
    "evidence_anchors",
}
ACCESSIBILITY_DECISIONS = {"blocked", "deferred", "ready", "unspecified"}
IMPLEMENTATION_READINESS = {"blocked", "deferred", "ready", "unspecified"}
POLICY_VALUES = {
    "repo_evidence_required_before_runtime",
    "existing_repo_evidence",
    "not_applicable",
    "unspecified",
}
ACCESSIBILITY_POLICY_FIELDS = {
    "keyboard_focus_policy",
    "semantic_role_name_value_policy",
    "aria_status_live_region_policy",
    "reduced_motion_policy",
    "non_color_only_semantics_policy",
    "touch_target_policy",
    "state_accessibility_policy",
    "ios_voiceover_dynamic_type_policy",
    "web_screen_reader_policy",
}
NEXT_REQUIRED_GATE = "token/runtime parity boundary"
REFERENCE_TOOLS = {
    "kimi",
    "figma",
    "canva",
    "penpot",
    "storybook",
    "code connect",
    "google drive",
    "screenshot",
    "screenshots",
    "generated design export",
    "generated design exports",
    "prompt output",
    "prompt outputs",
    "desktop export",
    "desktop exports",
}
RUNTIME_PERMISSION_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"ready\s+for\s+runtime\s+implementation",
        r"runtime\s+implementation\s+(is\s+)?(allowed|permitted|approved|unblocked)",
        r"permission\s+to\s+implement",
        r"may\s+implement\s+runtime",
        r"can\s+implement\s+runtime",
        r"implementation\s+(can|may)\s+start",
        r"start\s+(runtime\s+)?implementation",
        r"implementation\s+is\s+unblocked",
        r"web/iOS\s+implementation\s+may\s+start",
    )
]
VISUAL_APPROVAL_RE = re.compile(
    r"visual[^.\n]*(approval|approved|ready|passed|complete|satisfied)", flags=re.IGNORECASE
)


class AccessibilityDecisionError(ValueError):
    """Raised when accessibility regression decision validation fails."""


def _repo_path(path: str | Path, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise AccessibilityDecisionError(f"{label}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise AccessibilityDecisionError(f"{label}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise AccessibilityDecisionError(f"{label}: cannot read file: {exc}") from exc
    if not isinstance(data, dict):
        raise AccessibilityDecisionError(f"{label}: expected JSON object")
    return data


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
        if VISUAL_APPROVAL_RE.search(value):
            errors.append(f"{path}: visual decision must not substitute for accessibility approval")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_empty_null_or_unknown(item, path=f"{path}[{index}]", errors=errors)
    if isinstance(value, dict):
        for key, item in value.items():
            _check_empty_null_or_unknown(item, path=f"{path}.{key}", errors=errors)


def _load_records(repo_root: Path, path: Path, *, label: str) -> list[dict[str, Any]]:
    payload = _load_json_object(repo_root / path, label=str(path))
    records = payload.get("records")
    if not isinstance(records, list):
        raise AccessibilityDecisionError(f"{label}: records must be a list")
    if not all(isinstance(item, dict) for item in records):
        raise AccessibilityDecisionError(f"{label}: each record must be an object")
    return records


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
    missing_canonical = sorted(REQUIRED_CANONICAL - canonical_set)
    unexpected_canonical = sorted(canonical_set - REQUIRED_CANONICAL)
    if missing_canonical or unexpected_canonical:
        details = []
        if missing_canonical:
            details.append("missing " + ", ".join(missing_canonical))
        if unexpected_canonical:
            details.append("unexpected " + ", ".join(unexpected_canonical))
        errors.append("authority.canonical: " + "; ".join(details))
    reference_only_set = set(reference_only)
    missing_reference = sorted(REFERENCE_ONLY - reference_only_set)
    unexpected_reference = sorted(reference_only_set - REFERENCE_ONLY)
    if missing_reference or unexpected_reference:
        details = []
        if missing_reference:
            details.append("missing " + ", ".join(missing_reference))
        if unexpected_reference:
            details.append("unexpected " + ", ".join(unexpected_reference))
        errors.append("authority.reference_only: " + "; ".join(details))
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


def _repo_evidence_error(anchor: str, repo_root: Path) -> str | None:
    path_text, _, fragment = anchor.partition(":")
    if ".." in Path(path_text).parts:
        return "repo evidence file does not exist"
    path = repo_root / path_text
    try:
        resolved_relative = path.resolve(strict=False).relative_to(repo_root.resolve(strict=True))
    except (OSError, ValueError):
        return "repo evidence file does not exist"
    allowed_roots = ("docs/", "scripts/", "tests/", "frontend/", "ios/", "tokens/")
    if not str(resolved_relative).startswith(allowed_roots):
        return "repo evidence file does not exist"
    if not path.is_file():
        return "repo evidence file does not exist"
    if not fragment:
        return None
    if path.suffix != ".json":
        return "invalid evidence fragment"
    try:
        payload = _load_json_object(path, label=str(path))
    except AccessibilityDecisionError:
        return "invalid evidence fragment"
    records = payload.get("records")
    fragment_exists = isinstance(records, list) and any(
        isinstance(record, dict) and record.get("component_id") == fragment for record in records
    )
    return None if fragment_exists else "invalid evidence fragment"


def _validate_enum(
    record: dict[str, Any], *, field: str, allowed: set[str], prefix: str, errors: list[str]
) -> None:
    value = record.get(field)
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{prefix}.{field}: invalid value {value!r}")


def _validate_evidence_anchors(
    anchors: Any, *, prefix: str, component_id: str, repo_root: Path, errors: list[str]
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
        else:
            evidence_error = _repo_evidence_error(anchor, repo_root)
            if evidence_error:
                errors.append(f"{prefix}.evidence_anchors: {evidence_error}: {anchor!r}")
    expected_bridge_anchor = f"{BRIDGE_INVENTORY_PATH}:{component_id}"
    if expected_bridge_anchor not in anchors:
        errors.append(f"{prefix}.evidence_anchors: missing bridge evidence anchor")
    expected_visual_anchor = f"{VISUAL_DECISIONS_PATH}:{component_id}"
    if expected_visual_anchor not in anchors:
        errors.append(f"{prefix}.evidence_anchors: missing visual evidence anchor")


def _validate_record(
    record: dict[str, Any],
    *,
    index: int,
    bridge_record: dict[str, Any],
    visual_record: dict[str, Any],
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
    bridge_component_id = bridge_record.get("component_id")
    if component_id != bridge_component_id:
        errors.append(
            f"{prefix}.component_id: expected bridge inventory id {bridge_component_id!r}"
        )
        return
    if component_id != visual_record.get("component_id"):
        errors.append(f"{prefix}.component_id: mismatch with visual decision order")
    if record["canonical_name"] != bridge_record.get("canonical_name"):
        errors.append(f"{prefix}.canonical_name: mismatch with bridge inventory")
    expected_bridge_anchor = f"{BRIDGE_INVENTORY_PATH}:{component_id}"
    if record["bridge_inventory_anchor"] != expected_bridge_anchor:
        errors.append(f"{prefix}.bridge_inventory_anchor: expected {expected_bridge_anchor!r}")
    expected_visual_anchor = f"{VISUAL_DECISIONS_PATH}:{component_id}"
    if record["visual_decision_anchor"] != expected_visual_anchor:
        errors.append(f"{prefix}.visual_decision_anchor: expected {expected_visual_anchor!r}")
    _validate_enum(
        record,
        field="accessibility_regression_decision",
        allowed=ACCESSIBILITY_DECISIONS,
        prefix=prefix,
        errors=errors,
    )
    for field in ACCESSIBILITY_POLICY_FIELDS:
        _validate_enum(record, field=field, allowed=POLICY_VALUES, prefix=prefix, errors=errors)
    _validate_enum(
        record,
        field="implementation_readiness",
        allowed=IMPLEMENTATION_READINESS,
        prefix=prefix,
        errors=errors,
    )
    if record["accessibility_regression_decision"] == "ready":
        missing_fields = sorted(
            field
            for field in ACCESSIBILITY_POLICY_FIELDS
            if record[field] != "existing_repo_evidence"
        )
        if missing_fields:
            errors.append(
                f"{prefix}.accessibility_regression_decision: ready requires repo evidence for "
                + ", ".join(missing_fields)
            )
        if visual_record.get("visual_regression_decision") != "ready":
            errors.append(
                f"{prefix}.accessibility_regression_decision: ready requires ready visual decision"
            )
    if record["implementation_readiness"] == "ready":
        errors.append(
            f"{prefix}.implementation_readiness: ready requires accessibility and token/runtime parity gates"
        )
    if record["next_required_gate"] != NEXT_REQUIRED_GATE:
        errors.append(f"{prefix}.next_required_gate: must be {NEXT_REQUIRED_GATE}")
        if (
            isinstance(record["next_required_gate"], str)
            and "runtime" in record["next_required_gate"].lower()
            and "token/runtime parity boundary" not in record["next_required_gate"].lower()
        ):
            errors.append(
                f"{prefix}.next_required_gate: must not skip token/runtime parity boundary"
            )
    reason = record["implementation_blocked_reason"]
    if not isinstance(reason, str):
        errors.append(f"{prefix}.implementation_blocked_reason: expected string")
    else:
        lowered = reason.lower()
        required_terms = [
            "block",
            "accessibility",
            "keyboard",
            "semantic",
            "motion",
            "token/runtime",
        ]
        if not all(term in lowered for term in required_terms):
            errors.append(
                f"{prefix}.implementation_blocked_reason: must block implementation on "
                "accessibility dimensions and token/runtime parity"
            )
    _validate_evidence_anchors(
        record["evidence_anchors"],
        prefix=prefix,
        component_id=component_id,
        repo_root=repo_root,
        errors=errors,
    )


def validate_decisions(path: str | Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return validation errors for an accessibility regression decisions path."""
    decisions_path = _repo_path(path, repo_root)
    errors: list[str] = []
    try:
        decisions = _load_json_object(decisions_path, label=str(decisions_path))
    except AccessibilityDecisionError as exc:
        return [str(exc)]
    missing = REQUIRED_TOP_LEVEL_FIELDS - decisions.keys()
    unexpected = decisions.keys() - REQUIRED_TOP_LEVEL_FIELDS
    if missing:
        errors.append("decisions: missing required fields: " + ", ".join(sorted(missing)))
    if unexpected:
        errors.append("decisions: unexpected fields: " + ", ".join(sorted(unexpected)))
    if decisions.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}")
    if decisions.get("source_of_truth") != "repo":
        errors.append("source_of_truth: expected 'repo'")
    if decisions.get("source_bridge_inventory") != str(BRIDGE_INVENTORY_PATH):
        errors.append(f"source_bridge_inventory: expected {str(BRIDGE_INVENTORY_PATH)!r}")
    if decisions.get("source_registry") != str(REGISTRY_PATH):
        errors.append(f"source_registry: expected {str(REGISTRY_PATH)!r}")
    elif not (repo_root / REGISTRY_PATH).is_file():
        errors.append(f"source_registry: file not found at '{REGISTRY_PATH}'")
    if decisions.get("source_visual_decisions") != str(VISUAL_DECISIONS_PATH):
        errors.append(f"source_visual_decisions: expected {str(VISUAL_DECISIONS_PATH)!r}")
    elif not (repo_root / VISUAL_DECISIONS_PATH).is_file():
        errors.append(f"source_visual_decisions: file not found at '{VISUAL_DECISIONS_PATH}'")
    if decisions.get("decision_dimensions") != DECISION_DIMENSIONS:
        errors.append("decision_dimensions: unexpected dimensions or order")
    _validate_authority(decisions.get("authority"), errors)
    _check_empty_null_or_unknown(decisions, path="decisions", errors=errors)
    try:
        bridge_records = _load_records(
            repo_root, BRIDGE_INVENTORY_PATH, label=str(BRIDGE_INVENTORY_PATH)
        )
        visual_errors = design_visual_regression_decisions.validate_decisions(
            repo_root / VISUAL_DECISIONS_PATH, repo_root=repo_root
        )
        if visual_errors:
            errors.extend(f"source_visual_decisions: {error}" for error in visual_errors)
        visual_records = _load_records(
            repo_root, VISUAL_DECISIONS_PATH, label=str(VISUAL_DECISIONS_PATH)
        )
    except AccessibilityDecisionError as exc:
        errors.append(str(exc))
        bridge_records = []
        visual_records = []
    records = decisions.get("records")
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
        if index >= len(bridge_records):
            errors.append(f"records[{index}].component_id: component not in bridge inventory")
            continue
        if index >= len(visual_records):
            errors.append(f"records[{index}].component_id: component not in visual decisions")
            continue
        _validate_record(
            record,
            index=index,
            bridge_record=bridge_records[index],
            visual_record=visual_records[index],
            repo_root=repo_root,
            errors=errors,
        )
    bridge_ids = {
        str(record.get("component_id")) for record in bridge_records if record.get("component_id")
    }
    missing_bridge_ids = sorted(bridge_ids - seen)
    if missing_bridge_ids:
        errors.append(
            "records: missing bridge inventory components: " + ", ".join(missing_bridge_ids)
        )
    extra_ids = sorted(seen - bridge_ids)
    if extra_ids:
        errors.append("records: components not in bridge inventory: " + ", ".join(extra_ids))
    return errors


def summarize_decisions(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return a deterministic summary for valid accessibility regression decisions."""
    errors = validate_decisions(path, repo_root=repo_root)
    if errors:
        raise AccessibilityDecisionError("; ".join(errors))
    decisions = _load_json_object(_repo_path(path, repo_root), label=str(path))
    records = decisions["records"]
    fields = (
        "accessibility_regression_decision",
        *sorted(ACCESSIBILITY_POLICY_FIELDS),
        "implementation_readiness",
    )
    decision_counts = {
        field: dict(sorted(Counter(record[field] for record in records).items()))
        for field in fields
    }
    blocked = sum(1 for record in records if record["implementation_readiness"] == "blocked")
    next_required_gate_counts = dict(
        sorted(Counter(record["next_required_gate"] for record in records).items())
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_count": len(records),
        "decision_counts": decision_counts,
        "blocked_for_implementation": blocked,
        "next_required_gate_counts": next_required_gate_counts,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate accessibility decisions")
    validate.add_argument("path")
    summarize = subparsers.add_parser("summarize", help="print deterministic summary")
    summarize.add_argument("path")
    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        errors = validate_decisions(args.path)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("PASS: design accessibility regression decisions valid", file=stdout)
        return 0
    if args.command == "summarize":
        try:
            summary = summarize_decisions(args.path)
        except AccessibilityDecisionError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, sort_keys=True), file=stdout)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
