#!/usr/bin/env python3
"""Validate and summarize PulsePlate screen evidence pack manifests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
VOCABULARY_PATH = Path("docs/design/ui_component_vocabulary.json")
LOCAL_ARTIFACT_PREFIX = "artifacts/design/screen_evidence/"

try:
    from evidence_utils import _has_meaningful_evidence_value
except ModuleNotFoundError:
    evidence_utils_path = Path(__file__).with_name("evidence_utils.py")
    spec = importlib.util.spec_from_file_location("evidence_utils", evidence_utils_path)
    if spec is None or spec.loader is None:
        raise
    evidence_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evidence_utils)
    _has_meaningful_evidence_value = evidence_utils._has_meaningful_evidence_value

REQUIRED_FIELDS = [
    "evidence_id",
    "generated_by",
    "generated_at_policy",
    "platform",
    "surface_id",
    "surface_name",
    "route_or_screen",
    "source_of_truth_note",
    "capture_mode",
    "artifact_policy",
    "viewport",
    "theme",
    "locale",
    "component_ids",
    "token_mirror_paths_checked",
    "accessibility_evidence",
    "responsive_evidence",
    "motion_evidence",
    "copy_safety_evidence",
    "tabbar_or_navigation_evidence",
    "overflow_evidence",
    "screenshot_artifact_path",
    "dom_artifact_path",
    "a11y_artifact_path",
    "storybook_artifact_path",
    "ios_simulator_artifact_path",
    "warnings",
    "status",
]

STRING_FIELDS = {
    "evidence_id",
    "generated_by",
    "generated_at_policy",
    "platform",
    "surface_id",
    "surface_name",
    "route_or_screen",
    "source_of_truth_note",
    "capture_mode",
    "artifact_policy",
    "viewport",
    "theme",
    "locale",
    "screenshot_artifact_path",
    "dom_artifact_path",
    "a11y_artifact_path",
    "storybook_artifact_path",
    "ios_simulator_artifact_path",
    "status",
}

ARRAY_FIELDS = {
    "component_ids",
    "token_mirror_paths_checked",
    "warnings",
}

OBJECT_FIELDS = {
    "accessibility_evidence",
    "responsive_evidence",
    "motion_evidence",
    "copy_safety_evidence",
    "tabbar_or_navigation_evidence",
    "overflow_evidence",
}

ARTIFACT_PATH_FIELDS = {
    "screenshot_artifact_path",
    "dom_artifact_path",
    "a11y_artifact_path",
    "storybook_artifact_path",
    "ios_simulator_artifact_path",
}

GENERATED_AT_POLICY_VALUES = {"omitted", "local_artifact_only"}
PLATFORM_VALUES = {"web", "ios"}
CAPTURE_MODE_VALUES = {"automated", "manual", "sample"}
ARTIFACT_POLICY_VALUES = {"local_only", "committed_sample_metadata"}
STATUS_VALUES = {"sample", "captured", "validated", "rejected"}

TOKEN_MIRROR_PATHS = {
    "frontend/src/styles/tokens.css",
    "frontend/src/styles/tokens.ts",
    "ios/PulsePlate/DesignSystem/DesignTokens.generated.swift",
}

DISALLOWED_PATH_PARTS = {
    ".venv",
    "DerivedData",
    "node_modules",
    "storybook-static",
    "worktrees",
}

BINARY_ARTIFACT_EXTENSIONS = {
    ".har",
    ".jpeg",
    ".jpg",
    ".mp4",
    ".png",
    ".trace",
    ".webp",
    ".zip",
}

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

SOT_AUTHORITY_PATTERNS = [
    r"\b(is|are|becomes?|serves as|acts as)\b.{0,40}\b(source of truth|source-of-truth|canonical truth|runtime authority|token authority)\b",
    r"\b(source of truth|source-of-truth|canonical truth|runtime authority|token authority)\b.{0,40}\b(overrides?|replaces?|beats|wins over)\b",
    r"\boverrides?\b.{0,40}\b(repo|tokens|runtime|backend|openapi|ui vocabulary)\b",
]


class EvidenceManifestError(ValueError):
    """Raised when a screen evidence manifest fails validation."""


def _repo_path(path: str | Path, repo_root: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except UnicodeDecodeError as exc:
        raise EvidenceManifestError(f"{path}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceManifestError(f"{path}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise EvidenceManifestError(f"{path}: cannot read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise EvidenceManifestError(f"{path}: manifest must be a JSON object")
    return data


def _load_component_ids(repo_root: Path) -> set[str]:
    path = repo_root / VOCABULARY_PATH
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except UnicodeDecodeError as exc:
        raise EvidenceManifestError(f"{VOCABULARY_PATH}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceManifestError(f"{VOCABULARY_PATH}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise EvidenceManifestError(f"{VOCABULARY_PATH}: cannot read vocabulary: {exc}") from exc
    if not isinstance(data, list):
        raise EvidenceManifestError(f"{VOCABULARY_PATH}: expected JSON array")
    component_ids = set()
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise EvidenceManifestError(f"{VOCABULARY_PATH}: every component requires a string id")
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


def _field_text(record: dict[str, Any]) -> str:
    return "\n".join(_stringify(record[key]) for key in sorted(record)).lower()


def _validate_required_fields(record: dict[str, Any], errors: list[str]) -> None:
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")


def _validate_field_types(record: dict[str, Any], errors: list[str]) -> None:
    for field in STRING_FIELDS:
        if field in record and not isinstance(record[field], str):
            errors.append(f"{field} must be a string")
    for field in STRING_FIELDS - ARTIFACT_PATH_FIELDS:
        if field in record and isinstance(record[field], str) and not record[field].strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ARRAY_FIELDS:
        if field in record:
            values = record[field]
            if not isinstance(values, list):
                errors.append(f"{field} must be an array")
            elif any(not isinstance(item, str) or not item.strip() for item in values):
                errors.append(f"{field} must contain only non-empty strings")
    for field in OBJECT_FIELDS:
        if field in record and not isinstance(record[field], dict):
            errors.append(f"{field} must be an object")


def _validate_enums(record: dict[str, Any], errors: list[str]) -> None:
    enum_fields = [
        ("generated_at_policy", GENERATED_AT_POLICY_VALUES),
        ("platform", PLATFORM_VALUES),
        ("capture_mode", CAPTURE_MODE_VALUES),
        ("artifact_policy", ARTIFACT_POLICY_VALUES),
        ("status", STATUS_VALUES),
    ]
    for field, allowed_values in enum_fields:
        value = record.get(field)
        if isinstance(value, str) and value not in allowed_values:
            errors.append(f"{field} must be one of: {', '.join(sorted(allowed_values))}")


def _validate_source_of_truth(record: dict[str, Any], errors: list[str]) -> None:
    note = _stringify(record.get("source_of_truth_note", "")).lower()
    if "review evidence" not in note:
        errors.append("source_of_truth_note must state this is review evidence")
    if "not source of truth" not in note and "non-canonical" not in note:
        errors.append("source_of_truth_note must state evidence is not source of truth")

    text = _field_text(record)
    if re.search(r"\bbut\b.{0,40}\boverrides?\b", text):
        errors.append("screen evidence must not become a source of truth")
        return
    for pattern in SOT_AUTHORITY_PATTERNS:
        for match in re.finditer(pattern, text):
            match_text = match.group(0).lower()
            has_in_match_negation = any(marker in match_text for marker in NEGATION_MARKERS)
            if not has_in_match_negation and not _has_negation_near(text, match.start()):
                errors.append("screen evidence must not become a source of truth")
                return


def _validate_components(record: dict[str, Any], repo_root: Path, errors: list[str]) -> None:
    if not isinstance(record.get("component_ids"), list):
        return
    known_ids = _load_component_ids(repo_root)
    for component_id in record["component_ids"]:
        if not isinstance(component_id, str):
            continue
        if component_id not in known_ids:
            errors.append(f"unknown PulsePlate component id: {component_id}")


def _validate_token_paths(record: dict[str, Any], errors: list[str]) -> None:
    values = record.get("token_mirror_paths_checked")
    if not isinstance(values, list):
        return
    for value in values:
        if value not in TOKEN_MIRROR_PATHS:
            errors.append(f"unknown token mirror path: {value}")


def _validate_artifact_paths(record: dict[str, Any], errors: list[str]) -> None:
    artifact_policy = record.get("artifact_policy")
    for field in sorted(ARTIFACT_PATH_FIELDS):
        value = record.get(field)
        if not isinstance(value, str) or not value:
            continue
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            errors.append(f"{field} must be a repo-relative local artifact path")
        if any(part in candidate.parts or part in value for part in DISALLOWED_PATH_PARTS):
            errors.append(f"{field} contains a disallowed local artifact path segment")
        if artifact_policy == "committed_sample_metadata":
            errors.append(f"{field} must be empty for committed_sample_metadata")
        elif not value.startswith(LOCAL_ARTIFACT_PREFIX):
            errors.append(f"{field} must stay under {LOCAL_ARTIFACT_PREFIX}")
        if candidate.suffix.lower() in BINARY_ARTIFACT_EXTENSIONS:
            if artifact_policy == "committed_sample_metadata":
                errors.append(f"{field} must not reference committed binary artifacts")


def _validate_wellness_copy(record: dict[str, Any], errors: list[str]) -> None:
    text = _stringify(record.get("copy_safety_evidence", "")).lower()
    for term in WELLNESS_CLAIM_TERMS:
        for match in re.finditer(re.escape(term), text):
            if not _has_negation_near(text, match.start()):
                errors.append(
                    "copy_safety_evidence must not promote diagnosis, treatment, "
                    "therapy, emergency, crisis, guaranteed outcome, or medical claims"
                )
                return


def _dict_has_evidence(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(_has_meaningful_evidence_value(item) for item in value.values())


def _validate_status_requirements(record: dict[str, Any], errors: list[str]) -> None:
    status = record.get("status")
    platform = record.get("platform")
    capture_mode = record.get("capture_mode")
    if platform == "web" and not _stringify(record.get("route_or_screen", "")).strip():
        errors.append("platform=web requires route_or_screen")
    if platform == "ios" and capture_mode == "automated":
        if not _stringify(record.get("ios_simulator_artifact_path", "")).strip():
            errors.append("platform=ios automated capture requires ios_simulator_artifact_path")
    if status == "validated":
        for field in sorted(OBJECT_FIELDS):
            if not _dict_has_evidence(record.get(field)):
                errors.append(f"status=validated requires non-empty {field}")
        if not record.get("token_mirror_paths_checked"):
            errors.append("status=validated requires token_mirror_paths_checked")


def validate_record(record: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return deterministic validation errors for one screen evidence manifest."""

    errors: list[str] = []
    _validate_required_fields(record, errors)
    _validate_field_types(record, errors)
    _validate_enums(record, errors)
    _validate_source_of_truth(record, errors)
    _validate_components(record, repo_root, errors)
    _validate_token_paths(record, errors)
    _validate_artifact_paths(record, errors)
    _validate_wellness_copy(record, errors)
    _validate_status_requirements(record, errors)
    return sorted(dict.fromkeys(errors))


def validate_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    manifest_path = _repo_path(path, repo_root)
    record = _load_json(manifest_path)
    return validate_record(record, repo_root=repo_root)


def validate_dir(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, list[str]]:
    manifest_dir = _repo_path(path, repo_root)
    manifests = sorted(manifest_dir.rglob("*.json"))
    if not manifests:
        return {str(manifest_dir): ["no JSON manifests found"]}
    results: dict[str, list[str]] = {}
    for manifest_path in manifests:
        relative = (
            manifest_path.relative_to(repo_root)
            if manifest_path.is_relative_to(repo_root)
            else manifest_path
        )
        results[str(relative)] = validate_path(manifest_path, repo_root=repo_root)
    return results


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    status = _stringify(record.get("status", ""))
    if status == "rejected":
        recommendation = "reject"
    elif status == "validated":
        recommendation = "validated"
    elif status == "captured":
        recommendation = "needs_validation"
    else:
        recommendation = "sample_only"
    return {
        "artifact_policy": record.get("artifact_policy"),
        "capture_mode": record.get("capture_mode"),
        "component_ids": sorted(record.get("component_ids", [])),
        "evidence_id": record.get("evidence_id"),
        "evidence_flags": {
            "accessibility": _dict_has_evidence(record.get("accessibility_evidence")),
            "copy_safety": _dict_has_evidence(record.get("copy_safety_evidence")),
            "motion": _dict_has_evidence(record.get("motion_evidence")),
            "navigation": _dict_has_evidence(record.get("tabbar_or_navigation_evidence")),
            "overflow": _dict_has_evidence(record.get("overflow_evidence")),
            "responsive": _dict_has_evidence(record.get("responsive_evidence")),
        },
        "platform": record.get("platform"),
        "recommendation": recommendation,
        "route_or_screen": record.get("route_or_screen"),
        "status": status,
        "surface_id": record.get("surface_id"),
        "token_mirror_paths_checked": sorted(record.get("token_mirror_paths_checked", [])),
        "warnings": sorted(record.get("warnings", [])),
    }


def summarize_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    manifest_path = _repo_path(path, repo_root)
    record = _load_json(manifest_path)
    errors = validate_record(record, repo_root=repo_root)
    if errors:
        raise EvidenceManifestError(
            f"{manifest_path}: cannot summarize invalid manifest: {'; '.join(errors)}"
        )
    return summarize_record(record)


def _route_slug(route: str) -> str:
    stripped = route.strip("/")
    if not stripped:
        return "root"
    return re.sub(r"[^a-z0-9]+", "-", stripped.lower()).strip("-")


def web_plan(routes: list[str], out_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []
    for route in routes:
        slug = _route_slug(route)
        manifest = {
            "a11y_artifact_path": "",
            "accessibility_evidence": {
                "planned": "Capture contrast, focus, keyboard, and landmark evidence later.",
            },
            "artifact_policy": "local_only",
            "capture_mode": "sample",
            "component_ids": [],
            "copy_safety_evidence": {
                "planned": "Review for wellness-only copy; avoid diagnosis, treatment, crisis, medical, and guaranteed outcome claims.",
            },
            "dom_artifact_path": "",
            "evidence_id": f"web-{slug}-screen-evidence-plan",
            "generated_at_policy": "omitted",
            "generated_by": "scripts/design/screen_evidence_pack.py web-plan",
            "ios_simulator_artifact_path": "",
            "locale": "en-US",
            "motion_evidence": {
                "planned": "Capture reduced-motion behavior later if motion is present.",
            },
            "overflow_evidence": {
                "planned": "Capture horizontal overflow evidence later.",
            },
            "platform": "web",
            "responsive_evidence": {
                "planned": "Capture desktop and mobile viewport metadata later.",
            },
            "route_or_screen": route,
            "screenshot_artifact_path": "",
            "source_of_truth_note": "Screen evidence is review evidence only, non-canonical, and not source of truth; repo tokens, UI vocabulary, backend/OpenAPI contracts, tests, and runtime code win.",
            "status": "sample",
            "storybook_artifact_path": "",
            "surface_id": f"web:{route}",
            "surface_name": f"Web {route} review surface",
            "tabbar_or_navigation_evidence": {
                "planned": "Capture shell navigation and tabbar visibility later.",
            },
            "theme": "repo-default",
            "token_mirror_paths_checked": [
                "frontend/src/styles/tokens.css",
                "frontend/src/styles/tokens.ts",
            ],
            "viewport": "desktop-1440x1100",
            "warnings": [
                "metadata plan only",
                "no screenshots captured",
                "no runtime UI mutation",
            ],
        }
        output_path = output_dir / f"{slug}.screen-evidence.json"
        output_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        generated_files.append(str(output_path))
    return {"generated_files": sorted(generated_files), "routes": sorted(routes)}


def _print_errors(errors: list[str], *, stderr: TextIO) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate one evidence manifest")
    validate_parser.add_argument("path")

    validate_dir_parser = subparsers.add_parser("validate-dir", help="validate evidence manifests")
    validate_dir_parser.add_argument("dir")

    summarize_parser = subparsers.add_parser("summarize", help="summarize one manifest")
    summarize_parser.add_argument("path")

    web_plan_parser = subparsers.add_parser(
        "web-plan", help="write deterministic web evidence plans"
    )
    web_plan_parser.add_argument("--routes", nargs="+", required=True)
    web_plan_parser.add_argument("--out", required=True)

    return parser


def run(
    argv: list[str] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            errors = validate_path(args.path, repo_root=repo_root)
            if errors:
                _print_errors(errors, stderr=stderr)
                return 1
            return 0
        if args.command == "validate-dir":
            results = validate_dir(args.dir, repo_root=repo_root)
            all_errors = [
                f"{path}: {error}" for path, errors in results.items() for error in errors
            ]
            if all_errors:
                _print_errors(sorted(all_errors), stderr=stderr)
                return 1
            return 0
        if args.command == "summarize":
            summary = summarize_path(args.path, repo_root=repo_root)
            print(json.dumps(summary, indent=2, sort_keys=True), file=stdout)
            return 0
        if args.command == "web-plan":
            summary = web_plan(args.routes, args.out)
            print(json.dumps(summary, indent=2, sort_keys=True), file=stdout)
            return 0
    except EvidenceManifestError as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
