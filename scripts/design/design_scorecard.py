#!/usr/bin/env python3
"""Score PulsePlate screen evidence packs with deterministic governance checks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, TextIO

try:
    import screen_evidence_pack
except ModuleNotFoundError:
    screen_evidence_pack_path = Path(__file__).with_name("screen_evidence_pack.py")
    spec = importlib.util.spec_from_file_location("screen_evidence_pack", screen_evidence_pack_path)
    if spec is None or spec.loader is None:
        raise
    screen_evidence_pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(screen_evidence_pack)

REPO_ROOT = Path(__file__).resolve().parents[2]

SCORECARD_STATUSES = {"pass", "warn", "fail"}
RECOMMENDATIONS = {"usable_for_pr5_pr6_brief", "needs_evidence", "rejected"}
GENERATED_BY = "scripts/design/design_scorecard.py"
SOURCE_OF_TRUTH_NOTE = (
    "Design scorecards are deterministic review evidence only, non-canonical, "
    "and not source of truth; repo tokens, UI vocabulary, backend/OpenAPI "
    "contracts, tests, and runtime code win."
)

DIMENSION_IDS = [
    "source_truth_compliance",
    "artifact_hygiene",
    "component_vocabulary_integrity",
    "token_evidence",
    "accessibility_evidence",
    "responsive_evidence",
    "copy_safety",
    "navigation_evidence",
    "overflow_evidence",
    "motion_evidence",
    "platform_metadata",
]

SUBJECTIVE_FIELD_TERMS = {
    "beautiful",
    "beauty",
    "luxury",
    "luxury_score",
    "market_appeal",
    "premium_score",
    "taste",
    "taste_score",
    "visual_ready",
    "visually_ready",
}


class DesignScorecardError(ValueError):
    """Raised when scorecard generation or validation fails."""


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
        raise DesignScorecardError(f"{path}: invalid UTF-8: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise DesignScorecardError(f"{path}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise DesignScorecardError(f"{path}: cannot read JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DesignScorecardError(f"{path}: expected JSON object")
    return data


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_stringify(item) for item in value.values())
    return str(value)


def _dict_has_evidence(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(bool(_stringify(item).strip()) for item in value.values())


def _dimension(
    dimension_id: str,
    *,
    score: int,
    status: str,
    summary: str,
    max_score: int = 10,
) -> dict[str, Any]:
    return {
        "id": dimension_id,
        "max_score": max_score,
        "score": score,
        "status": status,
        "summary": summary,
    }


def _score_presence_dimension(
    record: dict[str, Any],
    field: str,
    dimension_id: str,
    present_summary: str,
    missing_summary: str,
) -> tuple[dict[str, Any], list[str]]:
    if _dict_has_evidence(record.get(field)):
        return (
            _dimension(
                dimension_id,
                score=10,
                status="pass",
                summary=present_summary,
            ),
            [],
        )
    return (
        _dimension(
            dimension_id,
            score=0,
            status="warn",
            summary=missing_summary,
        ),
        [missing_summary],
    )


def _token_evidence_dimension(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    platform = record.get("platform")
    token_paths = set(record.get("token_mirror_paths_checked", []))
    if platform == "web":
        expected = {
            "frontend/src/styles/tokens.css",
            "frontend/src/styles/tokens.ts",
        }
    elif platform == "ios":
        expected = {
            "ios/PulsePlate/DesignSystem/DesignTokens.generated.swift",
        }
    else:
        expected = set()
    if expected and expected.issubset(token_paths):
        return (
            _dimension(
                "token_evidence",
                score=10,
                status="pass",
                summary="Platform token mirror evidence is present.",
            ),
            [],
        )
    if token_paths:
        summary = "Token evidence is partial for this platform."
        return (
            _dimension("token_evidence", score=6, status="warn", summary=summary),
            [summary],
        )
    summary = "Token evidence is missing."
    return (
        _dimension("token_evidence", score=0, status="warn", summary=summary),
        [summary],
    )


def _component_dimension(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    component_ids = record.get("component_ids", [])
    if component_ids:
        return (
            _dimension(
                "component_vocabulary_integrity",
                score=10,
                status="pass",
                summary="Mapped component ids passed PR-3 vocabulary validation.",
            ),
            [],
        )
    summary = "No component ids are mapped yet."
    return (
        _dimension(
            "component_vocabulary_integrity",
            score=6,
            status="warn",
            summary=summary,
        ),
        [summary],
    )


def _platform_dimension(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    platform = record.get("platform")
    route_or_screen = _stringify(record.get("route_or_screen", "")).strip()
    viewport = _stringify(record.get("viewport", "")).strip()
    if platform == "web" and route_or_screen and viewport:
        return (
            _dimension(
                "platform_metadata",
                score=10,
                status="pass",
                summary="Web route and viewport metadata are present.",
            ),
            [],
        )
    if platform == "ios" and route_or_screen and viewport:
        return (
            _dimension(
                "platform_metadata",
                score=10,
                status="pass",
                summary="iOS screen and device metadata are present.",
            ),
            [],
        )
    summary = "Platform route/screen or viewport metadata is incomplete."
    return (
        _dimension("platform_metadata", score=0, status="warn", summary=summary),
        [summary],
    )


def _status_and_recommendation(
    *,
    total_score: int,
    max_score: int,
    blocking_failures: list[str],
) -> tuple[str, str, float]:
    normalized_score = round(total_score / max_score, 4) if max_score else 0.0
    if blocking_failures:
        status = "fail"
    elif normalized_score >= 0.85:
        status = "pass"
    elif normalized_score >= 0.60:
        status = "warn"
    else:
        status = "fail"

    if blocking_failures or status == "fail":
        recommendation = "rejected"
    elif status == "pass":
        recommendation = "usable_for_pr5_pr6_brief"
    else:
        recommendation = "needs_evidence"
    return status, recommendation, normalized_score


def _score_record(record: dict[str, Any]) -> dict[str, Any]:
    dimensions: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking_failures: list[str] = []

    if record.get("status") == "rejected":
        blocking_failures.append("evidence status is rejected")

    dimensions.append(
        _dimension(
            "source_truth_compliance",
            score=10,
            status="pass",
            summary="Evidence source-of-truth note passed PR-3 validation.",
        )
    )
    dimensions.append(
        _dimension(
            "artifact_hygiene",
            score=10,
            status="pass",
            summary="Artifact path policy passed PR-3 validation.",
        )
    )

    dimension, dimension_warnings = _component_dimension(record)
    dimensions.append(dimension)
    warnings.extend(dimension_warnings)

    dimension, dimension_warnings = _token_evidence_dimension(record)
    dimensions.append(dimension)
    warnings.extend(dimension_warnings)

    for field, dimension_id, present_summary, missing_summary in [
        (
            "accessibility_evidence",
            "accessibility_evidence",
            "Accessibility evidence metadata is present; this does not claim WCAG pass.",
            "Accessibility evidence metadata is missing.",
        ),
        (
            "responsive_evidence",
            "responsive_evidence",
            "Responsive evidence metadata is present.",
            "Responsive evidence metadata is missing.",
        ),
        (
            "copy_safety_evidence",
            "copy_safety",
            "Copy-safety evidence passed PR-3 wellness validation.",
            "Copy-safety evidence metadata is missing.",
        ),
        (
            "tabbar_or_navigation_evidence",
            "navigation_evidence",
            "Navigation or tabbar evidence metadata is present.",
            "Navigation or tabbar evidence metadata is missing.",
        ),
        (
            "overflow_evidence",
            "overflow_evidence",
            "Overflow evidence metadata is present.",
            "Overflow evidence metadata is missing.",
        ),
        (
            "motion_evidence",
            "motion_evidence",
            "Motion or reduced-motion evidence metadata is present.",
            "Motion or reduced-motion evidence metadata is missing.",
        ),
    ]:
        dimension, dimension_warnings = _score_presence_dimension(
            record,
            field,
            dimension_id,
            present_summary,
            missing_summary,
        )
        dimensions.append(dimension)
        warnings.extend(dimension_warnings)

    dimension, dimension_warnings = _platform_dimension(record)
    dimensions.append(dimension)
    warnings.extend(dimension_warnings)

    ordered_dimensions = [
        next(item for item in dimensions if item["id"] == item_id) for item_id in DIMENSION_IDS
    ]
    total_score = sum(int(item["score"]) for item in ordered_dimensions)
    max_score = sum(int(item["max_score"]) for item in ordered_dimensions)
    status, recommendation, normalized_score = _status_and_recommendation(
        total_score=total_score,
        max_score=max_score,
        blocking_failures=blocking_failures,
    )

    evidence_id = _stringify(record.get("evidence_id", "")).strip()
    return {
        "blocking_failures": sorted(blocking_failures),
        "dimensions": ordered_dimensions,
        "generated_by": GENERATED_BY,
        "max_score": max_score,
        "normalized_score": normalized_score,
        "platform": record.get("platform"),
        "recommendation": recommendation,
        "route_or_screen": record.get("route_or_screen"),
        "scorecard_id": f"design-scorecard::{evidence_id}",
        "source_evidence_id": evidence_id,
        "source_of_truth_note": SOURCE_OF_TRUTH_NOTE,
        "status": status,
        "surface_id": record.get("surface_id"),
        "total_score": total_score,
        "warnings": sorted(dict.fromkeys(warnings)),
    }


def score_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    evidence_path = _repo_path(path, repo_root)
    try:
        record = screen_evidence_pack._load_json(evidence_path)
        errors = screen_evidence_pack.validate_record(record, repo_root=repo_root)
    except screen_evidence_pack.EvidenceManifestError as exc:
        raise DesignScorecardError(f"{evidence_path}: cannot score screen evidence: {exc}") from exc
    if errors:
        raise DesignScorecardError(
            f"{evidence_path}: cannot score invalid screen evidence: {'; '.join(errors)}"
        )
    return _score_record(record)


def score_dir(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    evidence_dir = _repo_path(path, repo_root)
    manifests = sorted(evidence_dir.rglob("*.json"))
    if not manifests:
        raise DesignScorecardError(f"{evidence_dir}: no JSON evidence manifests found")
    scorecards = []
    for manifest_path in manifests:
        relative = (
            manifest_path.relative_to(repo_root)
            if manifest_path.is_relative_to(repo_root)
            else manifest_path
        )
        scorecards.append(
            {
                "path": str(relative),
                "scorecard": score_path(manifest_path, repo_root=repo_root),
            }
        )
    return {"scorecards": scorecards}


def _find_subjective_keys(value: Any, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in SUBJECTIVE_FIELD_TERMS:
                findings.append(path)
            findings.extend(_find_subjective_keys(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_find_subjective_keys(item, f"{prefix}[{index}]"))
    return findings


def validate_scorecard_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "blocking_failures",
        "dimensions",
        "generated_by",
        "max_score",
        "normalized_score",
        "platform",
        "recommendation",
        "route_or_screen",
        "scorecard_id",
        "source_evidence_id",
        "source_of_truth_note",
        "status",
        "surface_id",
        "total_score",
        "warnings",
    }
    for field in sorted(required_fields):
        if field not in record:
            errors.append(f"missing required field: {field}")
    if errors:
        return errors

    if record.get("status") not in SCORECARD_STATUSES:
        errors.append("status must be one of: fail, pass, warn")
    if record.get("recommendation") not in RECOMMENDATIONS:
        errors.append(
            "recommendation must be one of: needs_evidence, rejected, usable_for_pr5_pr6_brief"
        )
    if record.get("generated_by") != GENERATED_BY:
        errors.append(f"generated_by must be {GENERATED_BY}")
    if not isinstance(record.get("source_evidence_id"), str) or not record["source_evidence_id"]:
        errors.append("source_evidence_id must be a non-empty string")
    expected_scorecard_id = f"design-scorecard::{record.get('source_evidence_id')}"
    if record.get("scorecard_id") != expected_scorecard_id:
        errors.append(f"scorecard_id must be {expected_scorecard_id}")
    if "not source of truth" not in _stringify(record.get("source_of_truth_note", "")).lower():
        errors.append("source_of_truth_note must state scorecards are not source of truth")

    dimensions = record.get("dimensions")
    if not isinstance(dimensions, list):
        errors.append("dimensions must be an array")
    else:
        dimension_ids = []
        for dimension in dimensions:
            if not isinstance(dimension, dict):
                errors.append("dimensions must contain objects")
                continue
            dimension_ids.append(dimension.get("id"))
            for field in ["id", "max_score", "score", "status", "summary"]:
                if field not in dimension:
                    errors.append(f"dimension missing required field: {field}")
            if dimension.get("status") not in SCORECARD_STATUSES:
                errors.append("dimension status must be one of: fail, pass, warn")
            score = dimension.get("score")
            max_score = dimension.get("max_score")
            if not isinstance(score, int) or not isinstance(max_score, int):
                errors.append("dimension score and max_score must be integers")
            elif score < 0 or max_score <= 0 or score > max_score:
                errors.append("dimension score must be between 0 and max_score")
        if dimension_ids != DIMENSION_IDS:
            errors.append("dimensions must use the canonical deterministic dimension order")

    for field in ["blocking_failures", "warnings"]:
        values = record.get(field)
        if not isinstance(values, list):
            errors.append(f"{field} must be an array")
        elif any(not isinstance(item, str) for item in values):
            errors.append(f"{field} must contain strings")
        elif values != sorted(values):
            errors.append(f"{field} must be sorted")

    total_score = record.get("total_score")
    max_score = record.get("max_score")
    normalized_score = record.get("normalized_score")
    if not isinstance(total_score, int) or not isinstance(max_score, int):
        errors.append("total_score and max_score must be integers")
    elif total_score < 0 or max_score <= 0 or total_score > max_score:
        errors.append("total_score must be between 0 and max_score")
    if not isinstance(normalized_score, (float, int)):
        errors.append("normalized_score must be numeric")
    elif normalized_score < 0 or normalized_score > 1:
        errors.append("normalized_score must be between 0 and 1")

    if isinstance(dimensions, list) and all(isinstance(item, dict) for item in dimensions):
        if all(isinstance(item.get("score"), int) for item in dimensions) and all(
            isinstance(item.get("max_score"), int) for item in dimensions
        ):
            expected_total = sum(int(item["score"]) for item in dimensions)
            expected_max = sum(int(item["max_score"]) for item in dimensions)
            blocking_failures = record.get("blocking_failures")
            if isinstance(blocking_failures, list) and all(
                isinstance(item, str) for item in blocking_failures
            ):
                (
                    expected_status,
                    expected_recommendation,
                    expected_normalized,
                ) = _status_and_recommendation(
                    total_score=expected_total,
                    max_score=expected_max,
                    blocking_failures=blocking_failures,
                )
                if record.get("total_score") != expected_total:
                    errors.append("total_score must equal the sum of dimension scores")
                if record.get("max_score") != expected_max:
                    errors.append("max_score must equal the sum of dimension max_score values")
                if record.get("normalized_score") != expected_normalized:
                    errors.append("normalized_score must match total_score / max_score")
                if record.get("status") != expected_status:
                    errors.append("status must match score thresholds and blocking failures")
                if record.get("recommendation") != expected_recommendation:
                    errors.append(
                        "recommendation must match score thresholds and blocking failures"
                    )

    subjective_keys = _find_subjective_keys(record)
    for key in subjective_keys:
        errors.append(f"subjective scorecard field is forbidden: {key}")

    return sorted(dict.fromkeys(errors))


def validate_score_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    scorecard_path = _repo_path(path, repo_root)
    record = _load_json(scorecard_path)
    return validate_scorecard_record(record)


def summarize_scorecard(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate_scorecard_record(record)
    if errors:
        raise DesignScorecardError(f"cannot summarize invalid scorecard: {'; '.join(errors)}")
    return {
        "blocking_failures": sorted(record["blocking_failures"]),
        "normalized_score": record["normalized_score"],
        "recommendation": record["recommendation"],
        "scorecard_id": record["scorecard_id"],
        "source_evidence_id": record["source_evidence_id"],
        "status": record["status"],
        "surface_id": record["surface_id"],
        "warnings": sorted(record["warnings"]),
    }


def summarize_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    scorecard_path = _repo_path(path, repo_root)
    return summarize_scorecard(_load_json(scorecard_path))


def _print_errors(errors: list[str], *, stderr: TextIO) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=stderr)


def _print_json(payload: dict[str, Any], *, stdout: TextIO) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True), file=stdout)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    score_parser = subparsers.add_parser("score", help="score one screen evidence manifest")
    score_parser.add_argument("path")

    score_dir_parser = subparsers.add_parser(
        "score-dir", help="score every screen evidence manifest in a directory"
    )
    score_dir_parser.add_argument("path")

    validate_score_parser = subparsers.add_parser(
        "validate-score", help="validate one generated scorecard"
    )
    validate_score_parser.add_argument("path")

    summarize_parser = subparsers.add_parser("summarize", help="summarize one scorecard")
    summarize_parser.add_argument("path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "score":
            _print_json(score_path(args.path), stdout=sys.stdout)
            return 0
        if args.command == "score-dir":
            _print_json(score_dir(args.path), stdout=sys.stdout)
            return 0
        if args.command == "validate-score":
            errors = validate_score_path(args.path)
            if errors:
                _print_errors(errors, stderr=sys.stderr)
                return 1
            print(f"OK: {args.path}")
            return 0
        if args.command == "summarize":
            _print_json(summarize_path(args.path), stdout=sys.stdout)
            return 0
    except DesignScorecardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
