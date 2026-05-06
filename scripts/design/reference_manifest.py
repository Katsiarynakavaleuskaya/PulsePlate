#!/usr/bin/env python3
"""Validate and normalize external UI/UX reference manifests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
VOCABULARY_PATH = Path("docs/design/ui_component_vocabulary.json")

REQUIRED_FIELDS = [
    "reference_id",
    "source_name",
    "source_url",
    "license_status",
    "attribution_required",
    "product_category",
    "platform",
    "surface_type",
    "visual_archetype",
    "palette_archetype",
    "typography_archetype",
    "spacing_density",
    "radius_profile",
    "component_patterns",
    "layout_patterns",
    "motion_notes",
    "accessibility_notes",
    "wellness_safety_notes",
    "monetization_notes",
    "legal_copy_risks",
    "adopt_adapt_reject_decision",
    "normalization_notes",
    "mapped_pulseplate_components",
    "forbidden_copy_elements",
    "icon-silhouette-check",
    "design-guard",
    "status",
]

STRING_FIELDS = {
    "reference_id",
    "source_name",
    "source_url",
    "license_status",
    "product_category",
    "visual_archetype",
    "palette_archetype",
    "typography_archetype",
    "spacing_density",
    "radius_profile",
    "motion_notes",
    "accessibility_notes",
    "wellness_safety_notes",
    "monetization_notes",
    "adopt_adapt_reject_decision",
    "normalization_notes",
    "icon-silhouette-check",
    "design-guard",
    "status",
}

ARRAY_FIELDS = {
    "platform",
    "surface_type",
    "component_patterns",
    "layout_patterns",
    "legal_copy_risks",
    "mapped_pulseplate_components",
    "forbidden_copy_elements",
}

STATUS_VALUES = {"read_only", "normalized", "rejected", "candidate_for_brief"}
DECISION_VALUES = {"adopt", "adapt", "reject"}
LICENSE_VALUES = {"permissive", "restricted", "unknown", "internal_only", "not_applicable"}
SPACING_DENSITY_VALUES = {"compact", "balanced", "comfortable", "editorial", "unknown"}
RADIUS_PROFILE_VALUES = {"sharp", "subtle", "medium", "soft", "pill", "mixed", "unknown"}
EXPORT_GATE_VALUES = {"required", "passed", "not_applicable", "blocked"}

DIRECT_COPY_PATTERNS = [
    r"\bcopy\b.{0,40}\b(screenshot|asset|brand|exact layout|layout|component|marketing text|copy)\b",
    r"\bclone\b.{0,40}\b(screenshot|asset|brand|exact layout|layout|component|marketing text|copy)\b",
    r"\breuse\b.{0,40}\b(screenshot|asset|brand|exact layout|layout|component|marketing text|copy)\b",
    r"\breplicate\b.{0,40}\b(screenshot|asset|brand|exact layout|layout|component|marketing text|copy)\b",
    r"\buse\b.{0,40}\b(external brand|vendor brand|proprietary component|copied marketing text)\b",
]

WELLNESS_CLAIM_TERMS = [
    "diagnos",
    "treat",
    "therapy",
    "therapeutic",
    "emergency",
    "crisis",
    "guaranteed",
    "medical",
    "cure",
]

SOT_DRIFT_PATTERNS = [
    r"\b(source of truth|source-of-truth|canonical truth|runtime authority|token authority)\b",
    r"\boverrides?\b.{0,40}\b(repo|tokens|runtime|backend|openapi|ui vocabulary)\b",
]

NEGATION_MARKERS = (
    "avoid",
    "no ",
    "not ",
    "must not",
    "does not",
    "do not",
    "without",
    "non-",
    "never",
)


class ManifestError(ValueError):
    """Raised when a reference manifest fails deterministic validation."""


def _repo_path(path: str | Path, repo_root: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a JSON object")
    return data


def _load_component_ids(repo_root: Path) -> set[str]:
    path = repo_root / VOCABULARY_PATH
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ManifestError(f"{VOCABULARY_PATH}: expected JSON array")
    component_ids: set[str] = set()
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ManifestError(f"{VOCABULARY_PATH}: every component requires a string id")
        component_ids.add(item["id"])
    return component_ids


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_stringify(item) for item in value.values())
    return str(value)


def _has_negation_near(text: str, index: int) -> bool:
    sentence_start = max(text.rfind(".", 0, index), text.rfind(";", 0, index))
    window_start = max(0, sentence_start + 1, index - 96)
    window = text[window_start:index].lower()
    return any(marker in window for marker in NEGATION_MARKERS)


def _field_text(record: dict[str, Any], *, exclude: set[str] | None = None) -> str:
    excluded = exclude or set()
    parts = []
    for key in sorted(record):
        if key in excluded:
            continue
        parts.append(_stringify(record[key]))
    return "\n".join(parts).lower()


def _validate_required_fields(record: dict[str, Any], errors: list[str]) -> None:
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")


def _validate_field_types(record: dict[str, Any], errors: list[str]) -> None:
    for field in STRING_FIELDS:
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            errors.append(f"{field} must be a non-empty string")
    for field in ARRAY_FIELDS:
        if field in record:
            values = record[field]
            if not isinstance(values, list):
                errors.append(f"{field} must be an array")
            elif any(not isinstance(item, str) or not item.strip() for item in values):
                errors.append(f"{field} must contain only non-empty strings")
    if "attribution_required" in record and not isinstance(record["attribution_required"], bool):
        errors.append("attribution_required must be a boolean")


def _validate_enums(record: dict[str, Any], errors: list[str]) -> None:
    enum_fields = [
        ("status", STATUS_VALUES),
        ("adopt_adapt_reject_decision", DECISION_VALUES),
        ("license_status", LICENSE_VALUES),
        ("spacing_density", SPACING_DENSITY_VALUES),
        ("radius_profile", RADIUS_PROFILE_VALUES),
        ("icon-silhouette-check", EXPORT_GATE_VALUES),
        ("design-guard", EXPORT_GATE_VALUES),
    ]
    for field, allowed in enum_fields:
        if field in record and record[field] not in allowed:
            errors.append(f"{field} must be one of: {', '.join(sorted(allowed))}")


def _validate_status_alignment(record: dict[str, Any], errors: list[str]) -> None:
    status = record.get("status")
    decision = record.get("adopt_adapt_reject_decision")
    license_status = record.get("license_status")
    if decision == "reject" and status != "rejected":
        errors.append("adopt_adapt_reject_decision=reject requires status=rejected")
    if status == "candidate_for_brief":
        if decision not in {"adopt", "adapt"}:
            errors.append("status=candidate_for_brief requires decision adopt or adapt")
        if license_status == "unknown":
            errors.append("license_status=unknown cannot be candidate_for_brief")
        for field in ("normalization_notes", "legal_copy_risks", "mapped_pulseplate_components"):
            value = record.get(field)
            if isinstance(value, str) and not value.strip():
                errors.append(f"candidate_for_brief requires non-empty {field}")
            if isinstance(value, list) and not value:
                errors.append(f"candidate_for_brief requires non-empty {field}")
    if status != "rejected" and not record.get("forbidden_copy_elements"):
        errors.append("non-rejected references require forbidden_copy_elements")


def _validate_component_mapping(record: dict[str, Any], repo_root: Path, errors: list[str]) -> None:
    component_ids = _load_component_ids(repo_root)
    for component_id in record.get("mapped_pulseplate_components", []):
        if component_id not in component_ids:
            errors.append(f"unknown PulsePlate component mapping: {component_id}")


def _validate_copy_risk(record: dict[str, Any], errors: list[str]) -> None:
    text = _field_text(record, exclude={"forbidden_copy_elements", "legal_copy_risks"})
    for pattern in DIRECT_COPY_PATTERNS:
        if re.search(pattern, text):
            errors.append("direct-copy intent is forbidden")
            break


def _validate_wellness_safety(record: dict[str, Any], errors: list[str]) -> None:
    notes = str(record.get("wellness_safety_notes", "")).lower()
    for term in WELLNESS_CLAIM_TERMS:
        for match in re.finditer(re.escape(term), notes):
            if not _has_negation_near(notes, match.start()):
                errors.append(
                    "wellness_safety_notes must not promote medical, treatment, crisis, "
                    "emergency, therapy, diagnosis, cure, or guaranteed-outcome claims"
                )
                return


def _validate_source_of_truth(record: dict[str, Any], errors: list[str]) -> None:
    text = _field_text(record)
    if "read-only" in text or "read only" in text or "non-canonical" in text:
        pass
    else:
        errors.append("manifest must state references are read-only or non-canonical evidence")
    for pattern in SOT_DRIFT_PATTERNS:
        for match in re.finditer(pattern, text):
            if not _has_negation_near(text, match.start()):
                errors.append("external references must not become a source of truth")
                return


def validate_record(record: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    _validate_required_fields(record, errors)
    _validate_field_types(record, errors)
    _validate_enums(record, errors)
    _validate_status_alignment(record, errors)
    if not errors:
        _validate_component_mapping(record, repo_root, errors)
    _validate_copy_risk(record, errors)
    _validate_wellness_safety(record, errors)
    _validate_source_of_truth(record, errors)
    return errors


def validate_path(path: Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    record = _load_json(path)
    return [f"{path}: {error}" for error in validate_record(record, repo_root=repo_root)]


def validate_dir(path: Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    files = sorted(item for item in path.rglob("*.json") if item.is_file())
    if not files:
        return [f"{path}: no JSON manifest files found"]
    errors: list[str] = []
    for file_path in files:
        errors.extend(validate_path(file_path, repo_root=repo_root))
    return errors


def _recommendation(record: dict[str, Any]) -> str:
    if record["status"] == "rejected" or record["adopt_adapt_reject_decision"] == "reject":
        return "reject"
    if record["status"] == "candidate_for_brief":
        return "candidate_for_brief"
    return "read_only"


def normalized_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "copy_risk_summary": sorted(record["forbidden_copy_elements"]),
        "decision": record["adopt_adapt_reject_decision"],
        "license_risk_summary": {
            "attribution_required": record["attribution_required"],
            "legal_copy_risks": sorted(record["legal_copy_risks"]),
            "license_status": record["license_status"],
        },
        "mapped_pulseplate_component_ids": sorted(record["mapped_pulseplate_components"]),
        "platform": sorted(record["platform"]),
        "recommendation": _recommendation(record),
        "reference_id": record["reference_id"],
        "source_name": record["source_name"],
        "status": record["status"],
        "surface_type": sorted(record["surface_type"]),
        "wellness_safety_summary": record["wellness_safety_notes"],
    }


def _print_errors(errors: list[str], stderr: TextIO) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=stderr)


def run(argv: list[str] | None = None, *, repo_root: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("path")

    validate_dir_parser = subparsers.add_parser("validate-dir")
    validate_dir_parser.add_argument("dir")

    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("path")

    args = parser.parse_args(argv)

    if args.command == "validate":
        errors = validate_path(_repo_path(args.path, repo_root), repo_root=repo_root)
        if errors:
            _print_errors(errors, sys.stderr)
            return 1
        print(f"OK: {args.path} is valid.")
        return 0

    if args.command == "validate-dir":
        errors = validate_dir(_repo_path(args.dir, repo_root), repo_root=repo_root)
        if errors:
            _print_errors(errors, sys.stderr)
            return 1
        print(f"OK: {args.dir} manifests are valid.")
        return 0

    if args.command == "normalize":
        path = _repo_path(args.path, repo_root)
        record = _load_json(path)
        errors = validate_record(record, repo_root=repo_root)
        if errors:
            _print_errors([f"{path}: {error}" for error in errors], sys.stderr)
            return 1
        print(json.dumps(normalized_summary(record), indent=2, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
