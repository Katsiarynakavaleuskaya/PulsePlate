"""Repo-governed agent learning-loop proposal helpers.

The learning loop is intentionally proposal-only. It redacts inputs and emits
deterministic recommendations that require normal repo review before promotion.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import PurePosixPath
import re
from typing import Any

LEARNING_LOOP_SCHEMA_VERSION = "agent-learning-loop.v1"
LEARNING_RECORD_SCHEMA_VERSION = "agent_learning_record.v1"
AUTHORITY_BOUNDARY = "proposal_only_non_runtime"
VALID_LEARNING_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
_SENSITIVE_RE = re.compile(
    r"(?i)(ghp_[a-z0-9_]+|ghs_[a-z0-9_.-]+|sk-[a-z0-9_-]+|"
    r"\b(?:token|secret|password|api[_-]?key)\b\s*[:=]\s*[^\s]+)"
)


def redact_learning_text(value: str) -> str:
    """Redact common token/secret shapes before proposal generation."""

    return _SENSITIVE_RE.sub("<redacted>", value)


def _require_repo_relative_path(value: str, *, field_name: str) -> str:
    item = value.strip()
    if not item:
        raise ValueError(f"{field_name} must be a non-empty repo-relative path.")
    path = PurePosixPath(item.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
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


def build_agent_learning_record(
    *,
    source: str,
    pattern: str,
    severity: str,
    affected_surfaces: list[str],
    root_cause: str,
    required_oracle: str,
    promotion_target: str,
) -> dict[str, Any]:
    """Build one redacted proposal-only learning record."""

    redacted_source = redact_learning_text(source.strip())
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
    normalized = "\n".join(
        [
            redacted_source,
            redacted_pattern,
            normalized_severity,
            *redacted_surfaces,
            redacted_root_cause,
            required_oracle.strip(),
            normalized_promotion_target,
        ]
    )
    fingerprint = f"sha256:{sha256(normalized.encode('utf-8')).hexdigest()}"
    lesson_id = f"lesson-{fingerprint.removeprefix('sha256:')[:12]}"
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
    return {
        "lesson_id": lesson_id,
        "source": redacted_source,
        "pattern": redacted_pattern,
        "severity": normalized_severity,
        "affected_surfaces": redacted_surfaces,
        "root_cause": redacted_root_cause,
        "required_oracle": required_oracle.strip(),
        "promotion_target": normalized_promotion_target,
        "dedupe_fingerprint": fingerprint,
        "redaction_status": redaction_status,
        "human_review_required": True,
    }


def build_learning_promotion_proposal(record: dict[str, Any]) -> dict[str, Any]:
    """Wrap a learning record as a non-mutating promotion proposal."""

    lesson_id = str(record.get("lesson_id") or "")
    fingerprint = str(record.get("dedupe_fingerprint") or "")
    return {
        "schema_version": "agent_learning_promotion_proposal.v1",
        "authority_boundary": AUTHORITY_BOUNDARY,
        "side_effects_allowed": False,
        "runtime_authority": False,
        "canonical_until_promoted_by_repo_diff": False,
        "lesson_id": lesson_id,
        "dedupe_fingerprint": fingerprint,
        "promotion_target": str(record.get("promotion_target") or ""),
        "required_oracle": str(record.get("required_oracle") or ""),
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
