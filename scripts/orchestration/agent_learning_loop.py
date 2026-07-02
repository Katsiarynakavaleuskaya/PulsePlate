"""Repo-governed agent learning-loop proposal helpers.

The learning loop is intentionally proposal-only. It redacts inputs and emits
deterministic recommendations that require normal repo review before promotion.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import PurePosixPath
import re
from typing import Any

from scripts.orchestration.review_pattern_oracles import REVIEW_PATTERN_ORACLE_IDS

LEARNING_LOOP_SCHEMA_VERSION = "agent-learning-loop.v1"
LEARNING_RECORD_SCHEMA_VERSION = "agent_learning_record.v1"
LEARNING_METRICS_SCHEMA_VERSION = "agent_learning_metrics.v1"
AUTHORITY_BOUNDARY = "proposal_only_non_runtime"
VALID_LEARNING_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
VALID_LEARNING_PATTERN_KINDS = frozenset({"failure", "successful_iteration"})
VALID_LEARNING_METRIC_IDS = frozenset(
    {
        "agent_iteration_quality",
        "business_risk_clarity",
        "premortem_code_closure_rate",
        "project_development_signal",
        "repeat_failure_reduction",
        "review_actionable_escape_reduction",
        "successful_pattern_reuse",
        "user_impact_clarity",
    }
)
VALID_LEARNING_MEASUREMENT_WINDOWS = frozenset(
    {
        "current_pr",
        "next_comparable_pr",
        "next_two_comparable_prs",
        "release_train",
    }
)
VALID_REQUIRED_ORACLES = frozenset(REVIEW_PATTERN_ORACLE_IDS)
VALID_REDACTION_STATUSES = frozenset({"clean", "redacted"})
LEARNING_RECORD_REQUIRED_FIELDS = frozenset(
    {
        "lesson_id",
        "source",
        "pattern_kind",
        "pattern",
        "severity",
        "affected_surfaces",
        "root_cause",
        "required_oracle",
        "promotion_target",
        "learning_metrics",
        "dedupe_fingerprint",
        "redaction_status",
        "human_review_required",
    }
)
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:/")
_URI_SCHEME_PATH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_SENSITIVE_RE = re.compile(
    r"(?i)(github_pat_[a-z0-9_]+|ghs_[a-z0-9_.-]+|gh[opsru]_[a-z0-9_]+|"
    r"ghp_[a-z0-9_]+|sk-[a-z0-9_-]+|"
    r"\b(?:token|secret|password|api[_-]?key)\b\s*[:=]\s*[^\s]+)"
)
_LOCAL_PATH_RE = re.compile(
    r"(?i)(file://)?("
    r"/(?:Users|home|workspace|workspaces|private|var|tmp|Volumes|root|etc|opt|usr|mnt)/"
    r"[^\s,;]+|"
    r"~[\\/][^\s,;]+|"
    r"[A-Za-z]:[\\/][^\s,;]+"
    r")"
)
_RAW_MODEL_ARTIFACT_LINE_RE = re.compile(
    r"(?im)^.*\b("
    r"raw[_-]?prompt|raw[_-]?response|provider[_-]?payload|"
    r"chain[_ -]?of[_ -]?thought|candidate\.patch"
    r")\b.*$"
)
_PATCH_TEXT_LINE_RE = re.compile(r"(?im)^.*\bdiff --git\b.*$")


def redact_learning_text(value: str) -> str:
    """Redact common token/secret shapes before proposal generation."""

    redacted = _SENSITIVE_RE.sub("<redacted>", value)
    redacted = _LOCAL_PATH_RE.sub("<redacted-path>", redacted)
    redacted = _RAW_MODEL_ARTIFACT_LINE_RE.sub("<redacted>", redacted)
    return _PATCH_TEXT_LINE_RE.sub("<redacted>", redacted)


def _require_repo_relative_path(value: str, *, field_name: str) -> str:
    item = value.strip()
    if not item:
        raise ValueError(f"{field_name} must be a non-empty repo-relative path.")
    if _URI_SCHEME_PATH_RE.match(item):
        raise ValueError(f"{field_name} must be a repo-relative path.")
    path = PurePosixPath(item.replace("\\", "/"))
    if path.is_absolute() or _WINDOWS_DRIVE_PATH_RE.match(path.as_posix()) or ".." in path.parts:
        raise ValueError(f"{field_name} must be a repo-relative path.")
    if path.parts and path.parts[0] in {"~", "tmp", "var", "Users", "Volumes", "private"}:
        raise ValueError(f"{field_name} must not point at a local machine path.")
    return path.as_posix()


def _normalize_severity(value: str) -> str:
    severity = value.strip().lower()
    if severity not in VALID_LEARNING_SEVERITIES:
        allowed = ", ".join(sorted(VALID_LEARNING_SEVERITIES))
        raise ValueError(f"severity must be one of: {allowed}.")
    return severity


def _normalize_pattern_kind(value: str) -> str:
    pattern_kind = value.strip().lower().replace("-", "_")
    if pattern_kind not in VALID_LEARNING_PATTERN_KINDS:
        allowed = ", ".join(sorted(VALID_LEARNING_PATTERN_KINDS))
        raise ValueError(f"pattern_kind must be one of: {allowed}.")
    return pattern_kind


def _normalize_required_oracle(value: str) -> str:
    oracle = value.strip()
    if oracle not in VALID_REQUIRED_ORACLES:
        allowed = ", ".join(REVIEW_PATTERN_ORACLE_IDS)
        raise ValueError(f"required_oracle must be one of: {allowed}.")
    return oracle


def _default_learning_metrics(pattern_kind: str) -> dict[str, Any]:
    if pattern_kind == "successful_iteration":
        primary_metric = "successful_pattern_reuse"
        secondary_metrics = [
            "agent_iteration_quality",
            "user_impact_clarity",
            "business_risk_clarity",
            "project_development_signal",
        ]
    else:
        primary_metric = "repeat_failure_reduction"
        secondary_metrics = [
            "premortem_code_closure_rate",
            "review_actionable_escape_reduction",
            "user_impact_clarity",
            "business_risk_clarity",
            "project_development_signal",
        ]
    return {
        "schema_version": LEARNING_METRICS_SCHEMA_VERSION,
        "primary_metric": primary_metric,
        "secondary_metrics": secondary_metrics,
        "measurement_window": "next_comparable_pr",
        "authority_boundary": AUTHORITY_BOUNDARY,
        "runtime_telemetry_allowed": False,
        "product_runtime_truth": False,
        "semantic_cache_used": False,
        "graph_truth_updated": False,
    }


def _normalize_learning_metrics(
    raw_metrics: Any,
    *,
    pattern_kind: str,
) -> dict[str, Any]:
    metrics = _default_learning_metrics(pattern_kind) if raw_metrics is None else raw_metrics
    if not isinstance(metrics, dict):
        raise ValueError("learning_metrics must be a JSON object.")
    expected_keys = {
        "schema_version",
        "primary_metric",
        "secondary_metrics",
        "measurement_window",
        "authority_boundary",
        "runtime_telemetry_allowed",
        "product_runtime_truth",
        "semantic_cache_used",
        "graph_truth_updated",
    }
    missing = sorted(expected_keys.difference(metrics))
    extra = sorted(set(metrics).difference(expected_keys))
    if missing:
        raise ValueError(f"learning_metrics missing fields {', '.join(missing)}.")
    if extra:
        raise ValueError(f"learning_metrics unexpected fields {', '.join(extra)}.")
    if metrics["schema_version"] != LEARNING_METRICS_SCHEMA_VERSION:
        raise ValueError(
            f"learning_metrics.schema_version must be {LEARNING_METRICS_SCHEMA_VERSION}."
        )
    if metrics["authority_boundary"] != AUTHORITY_BOUNDARY:
        raise ValueError(f"learning_metrics.authority_boundary must be {AUTHORITY_BOUNDARY}.")
    for field in (
        "runtime_telemetry_allowed",
        "product_runtime_truth",
        "semantic_cache_used",
        "graph_truth_updated",
    ):
        if metrics[field] is not False:
            raise ValueError(f"learning_metrics.{field} must be false.")

    primary_metric = str(metrics["primary_metric"]).strip()
    if primary_metric not in VALID_LEARNING_METRIC_IDS:
        allowed = ", ".join(sorted(VALID_LEARNING_METRIC_IDS))
        raise ValueError(f"learning_metrics.primary_metric must be one of: {allowed}.")

    raw_secondary = metrics["secondary_metrics"]
    if not isinstance(raw_secondary, list) or not all(
        isinstance(item, str) for item in raw_secondary
    ):
        raise ValueError("learning_metrics.secondary_metrics must be an array of strings.")
    secondary_metrics: list[str] = []
    for item in raw_secondary:
        metric = item.strip()
        if metric not in VALID_LEARNING_METRIC_IDS:
            allowed = ", ".join(sorted(VALID_LEARNING_METRIC_IDS))
            raise ValueError(f"learning_metrics.secondary_metrics must contain only: {allowed}.")
        if metric != primary_metric and metric not in secondary_metrics:
            secondary_metrics.append(metric)

    _validate_metric_shape_for_pattern_kind(
        pattern_kind=pattern_kind,
        primary_metric=primary_metric,
        secondary_metrics=secondary_metrics,
    )

    measurement_window = str(metrics["measurement_window"]).strip()
    if measurement_window not in VALID_LEARNING_MEASUREMENT_WINDOWS:
        allowed = ", ".join(sorted(VALID_LEARNING_MEASUREMENT_WINDOWS))
        raise ValueError(f"learning_metrics.measurement_window must be one of: {allowed}.")

    return {
        "schema_version": LEARNING_METRICS_SCHEMA_VERSION,
        "primary_metric": primary_metric,
        "secondary_metrics": secondary_metrics,
        "measurement_window": measurement_window,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "runtime_telemetry_allowed": False,
        "product_runtime_truth": False,
        "semantic_cache_used": False,
        "graph_truth_updated": False,
    }


def _validate_metric_shape_for_pattern_kind(
    *,
    pattern_kind: str,
    primary_metric: str,
    secondary_metrics: list[str],
) -> None:
    if pattern_kind == "successful_iteration":
        if primary_metric != "successful_pattern_reuse":
            raise ValueError(
                "learning_metrics.primary_metric must be successful_pattern_reuse "
                "for successful_iteration patterns."
            )
        if "agent_iteration_quality" not in secondary_metrics:
            raise ValueError(
                "learning_metrics.secondary_metrics must include agent_iteration_quality "
                "for successful_iteration patterns."
            )
        failure_metrics = {
            "premortem_code_closure_rate",
            "repeat_failure_reduction",
            "review_actionable_escape_reduction",
        }
        if any(metric in failure_metrics for metric in secondary_metrics):
            raise ValueError(
                "learning_metrics.secondary_metrics must not use failure metrics "
                "for successful_iteration patterns."
            )
        return

    if primary_metric != "repeat_failure_reduction":
        raise ValueError(
            "learning_metrics.primary_metric must be repeat_failure_reduction "
            "for failure patterns."
        )
    if "successful_pattern_reuse" in secondary_metrics:
        raise ValueError(
            "learning_metrics.secondary_metrics must not use successful_pattern_reuse "
            "for failure patterns."
        )
    if not {
        "premortem_code_closure_rate",
        "review_actionable_escape_reduction",
    }.intersection(secondary_metrics):
        raise ValueError(
            "learning_metrics.secondary_metrics must include premortem_code_closure_rate "
            "or review_actionable_escape_reduction for failure patterns."
        )


def _dedupe_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = redact_learning_text(value.strip())
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _learning_record_fingerprint(
    *,
    source: str,
    pattern_kind: str,
    pattern: str,
    severity: str,
    affected_surfaces: list[str],
    root_cause: str,
    required_oracle: str,
    promotion_target: str,
    learning_metrics: dict[str, Any],
    redaction_status: str,
) -> str:
    normalized = "\n".join(
        [
            source,
            pattern_kind,
            pattern,
            severity,
            *affected_surfaces,
            root_cause,
            required_oracle,
            promotion_target,
            json.dumps(learning_metrics, sort_keys=True, separators=(",", ":")),
            redaction_status,
        ]
    )
    return f"sha256:{sha256(normalized.encode('utf-8')).hexdigest()}"


def _lesson_id_for_fingerprint(fingerprint: str) -> str:
    return f"lesson-{fingerprint.removeprefix('sha256:')[:12]}"


def build_agent_learning_record(
    *,
    source: str,
    pattern: str,
    severity: str,
    affected_surfaces: list[str],
    root_cause: str,
    required_oracle: str,
    promotion_target: str,
    pattern_kind: str = "failure",
    learning_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one redacted proposal-only learning record."""

    redacted_source = redact_learning_text(source.strip())
    normalized_pattern_kind = _normalize_pattern_kind(pattern_kind)
    redacted_pattern = redact_learning_text(pattern.strip())
    redacted_root_cause = redact_learning_text(root_cause.strip())
    redacted_surfaces = _dedupe_ordered(
        [
            _require_repo_relative_path(item, field_name="affected_surfaces")
            for item in affected_surfaces
        ]
    )
    normalized_severity = _normalize_severity(severity)
    normalized_promotion_target = _require_repo_relative_path(
        promotion_target,
        field_name="promotion_target",
    )
    normalized_required_oracle = _normalize_required_oracle(required_oracle)
    normalized_learning_metrics = _normalize_learning_metrics(
        learning_metrics,
        pattern_kind=normalized_pattern_kind,
    )
    redaction_status = (
        "redacted"
        if any(
            original != redacted
            for original, redacted in (
                (source.strip(), redacted_source),
                (pattern.strip(), redacted_pattern),
                (root_cause.strip(), redacted_root_cause),
            )
        )
        else "clean"
    )
    fingerprint = _learning_record_fingerprint(
        source=redacted_source,
        pattern_kind=normalized_pattern_kind,
        pattern=redacted_pattern,
        severity=normalized_severity,
        affected_surfaces=redacted_surfaces,
        root_cause=redacted_root_cause,
        required_oracle=normalized_required_oracle,
        promotion_target=normalized_promotion_target,
        learning_metrics=normalized_learning_metrics,
        redaction_status=redaction_status,
    )
    lesson_id = _lesson_id_for_fingerprint(fingerprint)
    return {
        "lesson_id": lesson_id,
        "source": redacted_source,
        "pattern_kind": normalized_pattern_kind,
        "pattern": redacted_pattern,
        "severity": normalized_severity,
        "affected_surfaces": redacted_surfaces,
        "root_cause": redacted_root_cause,
        "required_oracle": normalized_required_oracle,
        "promotion_target": normalized_promotion_target,
        "learning_metrics": normalized_learning_metrics,
        "dedupe_fingerprint": fingerprint,
        "redaction_status": redaction_status,
        "human_review_required": True,
    }


def validate_agent_learning_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate a stored learning record before emitting promotion proposals."""

    missing = sorted(LEARNING_RECORD_REQUIRED_FIELDS.difference(record))
    if missing:
        raise ValueError(f"missing fields {', '.join(missing)}.")
    extra = sorted(set(record).difference(LEARNING_RECORD_REQUIRED_FIELDS))
    if extra:
        raise ValueError(f"unexpected fields {', '.join(extra)}.")

    def _required_text(field: str) -> str:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")
        return value.strip()

    affected_surfaces_raw = record.get("affected_surfaces")
    if not isinstance(affected_surfaces_raw, list) or not all(
        isinstance(item, str) for item in affected_surfaces_raw
    ):
        raise ValueError("affected_surfaces must be an array of repo-relative paths.")
    severity = _normalize_severity(_required_text("severity"))
    pattern_kind = _normalize_pattern_kind(_required_text("pattern_kind"))
    learning_metrics = _normalize_learning_metrics(
        record.get("learning_metrics"),
        pattern_kind=pattern_kind,
    )
    affected_surfaces = [
        _require_repo_relative_path(item, field_name="affected_surfaces")
        for item in affected_surfaces_raw
    ]
    required_oracle = _normalize_required_oracle(_required_text("required_oracle"))
    promotion_target = _require_repo_relative_path(
        _required_text("promotion_target"),
        field_name="promotion_target",
    )

    source = _required_text("source")
    pattern = _required_text("pattern")
    root_cause = _required_text("root_cause")
    for field_name, value in (
        ("source", source),
        ("pattern", pattern),
        ("root_cause", root_cause),
    ):
        if redact_learning_text(value) != value:
            raise ValueError(f"{field_name} must be redacted before validation.")

    redaction_status = _required_text("redaction_status")
    if redaction_status not in VALID_REDACTION_STATUSES:
        allowed = ", ".join(sorted(VALID_REDACTION_STATUSES))
        raise ValueError(f"redaction_status must be one of: {allowed}.")

    fingerprint = _required_text("dedupe_fingerprint")
    if not _FINGERPRINT_RE.match(fingerprint):
        raise ValueError("dedupe_fingerprint must match sha256:<64 lowercase hex chars>.")
    expected_fingerprint = _learning_record_fingerprint(
        source=source,
        pattern_kind=pattern_kind,
        pattern=pattern,
        severity=severity,
        affected_surfaces=affected_surfaces,
        root_cause=root_cause,
        required_oracle=required_oracle,
        promotion_target=promotion_target,
        learning_metrics=learning_metrics,
        redaction_status=redaction_status,
    )
    if fingerprint != expected_fingerprint:
        raise ValueError("dedupe_fingerprint does not match normalized learning record.")

    lesson_id = _required_text("lesson_id")
    if lesson_id != _lesson_id_for_fingerprint(fingerprint):
        raise ValueError("lesson_id does not match dedupe_fingerprint.")

    if record.get("human_review_required") is not True:
        raise ValueError("human_review_required must be true.")

    return {
        "lesson_id": lesson_id,
        "source": source,
        "pattern_kind": pattern_kind,
        "pattern": pattern,
        "severity": severity,
        "affected_surfaces": affected_surfaces,
        "root_cause": root_cause,
        "required_oracle": required_oracle,
        "promotion_target": promotion_target,
        "learning_metrics": learning_metrics,
        "dedupe_fingerprint": fingerprint,
        "redaction_status": redaction_status,
        "human_review_required": True,
    }


def build_learning_promotion_proposal(record: dict[str, Any]) -> dict[str, Any]:
    """Wrap a learning record as a non-mutating promotion proposal."""

    validated = validate_agent_learning_record(record)
    lesson_id = validated["lesson_id"]
    fingerprint = validated["dedupe_fingerprint"]
    return {
        "schema_version": "agent_learning_promotion_proposal.v1",
        "authority_boundary": AUTHORITY_BOUNDARY,
        "side_effects_allowed": False,
        "runtime_authority": False,
        "canonical_until_promoted_by_repo_diff": False,
        "lesson_id": lesson_id,
        "dedupe_fingerprint": fingerprint,
        "promotion_target": validated["promotion_target"],
        "pattern_kind": validated["pattern_kind"],
        "learning_metrics": validated["learning_metrics"],
        "required_oracle": validated["required_oracle"],
        "human_review_required": True,
        "promotion_requirements": [
            "reviewed repo diff",
            "scoped AGENTS.md or docs/orchestration contract update when behavior changes",
            "focused deterministic tests",
        ],
    }


def build_learning_loop_proposal(
    *,
    source: str,
    lessons: list[str],
    target_paths: list[str],
) -> dict[str, Any]:
    """Build a deterministic proposal artifact without writing or side effects."""

    redacted_source = redact_learning_text(source.strip())
    redacted_lessons = _dedupe_ordered(lessons)
    normalized_targets = sorted(
        dict.fromkeys(
            _require_repo_relative_path(path, field_name="target_paths")
            for path in target_paths
            if path.strip()
        )
    )
    fingerprint_source = "\n".join([redacted_source, *redacted_lessons, *normalized_targets])
    return {
        "schema_version": LEARNING_LOOP_SCHEMA_VERSION,
        "source": redacted_source,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "side_effects_allowed": False,
        "runtime_authority": False,
        "canonical_until_promoted_by_repo_diff": False,
        "proposal_fingerprint": f"sha256:{sha256(fingerprint_source.encode('utf-8')).hexdigest()}",
        "redacted_lessons": redacted_lessons,
        "target_paths": normalized_targets,
        "promotion_requirements": [
            "reviewed repo diff",
            "nearest scoped AGENTS.md or docs/orchestration contract update",
            "focused deterministic tests",
        ],
    }
