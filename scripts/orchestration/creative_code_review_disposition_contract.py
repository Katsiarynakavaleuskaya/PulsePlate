"""Strict PR-5 creative-code review-disposition contracts.

PR-5 consumes sanitized local review context and optional read-only GitHub
fixtures. It can classify feedback and prepare a PR-1 specification launch
packet, but it never resolves review threads, edits fixed mapping, writes a
branch, opens a PR, merges, calls providers, or touches product runtime.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-code-review-disposition-pr5"

FEEDBACK_RECORD_TYPE = "creative_code_review_feedback_record"
FEEDBACK_COLLECTION_TYPE = "creative_code_review_feedback_collection"
DISPOSITION_PACKET_TYPE = "creative_code_review_disposition_packet"
REPAIR_LAUNCH_PACKET_TYPE = "creative_code_repair_launch_packet"

SUCCESS_OUTPUT = "PASS: creative-code review-disposition contract valid"
MAX_EXCERPT_CHARS = 240

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/"
    r"(?:pull|issues)/[0-9]+(?:[#/][A-Za-z0-9_./:-]+)?$"
)
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|candidate_patch|"
    r"raw[_ -]?(body|prompt|response|context|patch)|review[_ -]?thread[_ -]?body|"
    r"pull[_ -]?request[_ -]?body|chain[_ -]?of[_ -]?thought|"
    r"provider[_ -]?payload|oracle[_ -]?(stdout|stderr)|file://|/Users/|"
    r"/private/var/|/var/folders/|/tmp/|~[/\\]|[A-Za-z]:[\\/]|\.venv/|"
    r"\.git/|worktrees([:/._-]|$)|github_pat_|gh[psoru]_|xox[abprs]-|"
    r"sk-[A-Za-z0-9_-]{12,}|GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE | re.MULTILINE,
)
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

SOURCE_KINDS = frozenset(
    {
        "local_context",
        "github_fixture",
        "github_read_only",
        "pr_review_context",
        "pr_review_report",
        "artifact_read_error",
    }
)
FEEDBACK_KINDS = frozenset(
    {
        "review_thread",
        "bot_comment",
        "check_annotation",
        "security_finding",
        "context_warning",
        "review_source_status",
        "unknown",
    }
)
SEVERITIES = frozenset({"note", "low", "medium", "high", "critical"})
DISPOSITION_CANDIDATES = frozenset(
    {
        "simple_fix",
        "creative_repair_candidate",
        "not_a_bug_candidate",
        "defer_candidate",
        "out_of_scope",
        "security_blocker",
    }
)
REASON_CODES = frozenset(
    {
        "already_addressed",
        "documentation",
        "fixed_mapping_governance",
        "head_sha_drift",
        "security_sensitive",
        "source_degraded",
        "test_failure",
        "unknown",
        "unsafe_authority",
    }
)

RECORD_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "policy_version",
        "record_id",
        "idempotency_key",
        "source",
        "review_surface",
        "feedback_kind",
        "severity",
        "classification",
        "sanitized_excerpt",
        "fingerprints",
        "authority",
        "sanitized",
    }
)
SOURCE_KEYS = frozenset(
    {
        "source_kind",
        "source_id",
        "source_url",
        "repository",
        "pr_number",
        "head_sha",
        "observed_at_utc",
    }
)
REVIEW_SURFACE_KEYS = frozenset({"path", "line", "side"})
CLASSIFICATION_KEYS = frozenset(
    {
        "candidate_disposition",
        "reason_code",
        "requires_human_decision",
        "requires_repair",
        "repair_priority",
    }
)
EXCERPT_KEYS = frozenset({"text", "char_count", "truncated", "body_fingerprint"})
FINGERPRINT_KEYS = frozenset({"source_fingerprint", "record_fingerprint"})
REVIEW_AUTHORITY_KEYS = frozenset(
    {
        "post_github_comment",
        "resolve_threads",
        "edit_fixed_mapping",
        "create_branch",
        "write_branch",
        "push",
        "open_pr",
        "merge",
        "claim_merge_readiness",
        "write_runtime",
        "call_provider",
        "call_product_runtime",
        "use_semantic_cache",
        "modify_workflows",
        "modify_slack",
        "modify_github_app",
    }
)

PACKET_KEYS = frozenset(
    {
        "schema_version",
        "packet_type",
        "policy_version",
        "packet_id",
        "idempotency_key",
        "source_context",
        "expected_head_sha",
        "actual_head_sha",
        "head_sha_drift",
        "feedback_records",
        "summary",
        "authority",
        "sanitized",
    }
)
COLLECTION_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "source_context",
        "feedback_records",
        "sanitized",
    }
)
SOURCE_CONTEXT_KEYS = frozenset(
    {"source_kind", "source_id", "source_fingerprint", "context_path", "repository", "pr_number"}
)
SUMMARY_KEYS = frozenset(
    {
        "records_total",
        "repair_candidates",
        "not_actionable",
        "deferred_candidates",
        "blocked_by_head_drift",
        "highest_repair_priority",
    }
)

REPAIR_LAUNCH_KEYS = frozenset(
    {
        "schema_version",
        "packet_type",
        "policy_version",
        "launch_id",
        "idempotency_key",
        "source_disposition_packet_id",
        "source_disposition_packet_fingerprint",
        "target_pr1_specification",
        "repair_candidates",
        "authority",
        "sanitized",
    }
)
TARGET_PR1_KEYS = frozenset({"allowed", "reason", "source_packet_id"})
REPAIR_CANDIDATE_KEYS = frozenset(
    {"record_id", "reason_code", "repair_priority", "sanitized_excerpt", "source_fingerprint"}
)
REPAIR_AUTHORITY_KEYS = frozenset(
    {
        "create_pr1_specification",
        "generate_patch",
        "write_branch",
        "push",
        "open_pr",
        "resolve_threads",
        "edit_fixed_mapping",
        "merge",
    }
)


class CreativeCodeReviewDispositionContractError(ValueError):
    """Raised when PR-5 review-disposition artifacts violate local authority."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeReviewDispositionContractError(
                f"creative-code review-disposition JSON has duplicate key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_json_object(path: str | Path) -> dict[str, Any]:
    """Read a JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeReviewDispositionContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeReviewDispositionContractError(
            "Unable to read creative-code review-disposition JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodeReviewDispositionContractError(
            "Creative-code review-disposition artifact must be a JSON object."
        )
    return payload


def reject_unsafe_review_value(value: Any, *, label: str) -> None:
    """Reject strings that could leak raw review bodies, secrets, or local paths."""

    if isinstance(value, str):
        if GITHUB_URL_RE.fullmatch(value):
            return
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise CreativeCodeReviewDispositionContractError(
                f"{label} contains unsafe review-disposition text."
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_unsafe_review_value(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            reject_unsafe_review_value(item, label=f"{label}.{key}")


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected_keys - actual)
    extra = sorted(actual - expected_keys)
    if missing:
        raise CreativeCodeReviewDispositionContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodeReviewDispositionContractError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodeReviewDispositionContractError(
            f"{label}.{key} must be a safe identifier."
        )
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be a safe token.")
    return normalized


def _require_sha256(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be a sha256 digest.")
    return value


def _require_optional_sha(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodeReviewDispositionContractError(f"{label} must be null or a 40-char SHA.")
    return value


def _require_optional_repository(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
        raise CreativeCodeReviewDispositionContractError(
            f"{label} must be null or an owner/repo slug."
        )
    return value


def _require_optional_url(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not GITHUB_URL_RE.fullmatch(value):
        raise CreativeCodeReviewDispositionContractError(
            f"{label} must be null or a GitHub web URL."
        )
    reject_unsafe_review_value(value, label=label)
    return value


def _require_optional_timestamp(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise CreativeCodeReviewDispositionContractError(
            f"{label} must be null or an UTC timestamp."
        )
    return value


def _require_optional_int(
    value: Any,
    *,
    min_value: int,
    max_value: int,
    label: str,
) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeCodeReviewDispositionContractError(f"{label} must be null or integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodeReviewDispositionContractError(
            f"{label} must be between {min_value} and {max_value}."
        )
    return value


def _require_int(
    payload: Mapping[str, Any],
    key: str,
    *,
    min_value: int,
    max_value: int,
    label: str,
) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodeReviewDispositionContractError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, expected: bool, label: str) -> bool:
    value = payload.get(key)
    if value is not expected:
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be {expected}.")
    return expected


def _require_any_bool(payload: Mapping[str, Any], key: str, *, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CreativeCodeReviewDispositionContractError(f"{label}.{key} must be a boolean.")
    return value


def _normalize_repo_relative_path(raw_path: Any, *, label: str) -> str | None:
    if raw_path is None:
        return None
    if not isinstance(raw_path, str):
        raise CreativeCodeReviewDispositionContractError(f"{label} must be null or string.")
    value = raw_path.strip()
    if not value:
        raise CreativeCodeReviewDispositionContractError(f"{label} must not be empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeCodeReviewDispositionContractError(
            f"{label} must not contain control characters."
        )
    if "\\" in value:
        raise CreativeCodeReviewDispositionContractError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or Path(value).is_absolute():
        raise CreativeCodeReviewDispositionContractError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeCodeReviewDispositionContractError(f"{label} must not be a URL.")

    path = PurePosixPath(value)
    parts = path.parts
    if not parts or "." in parts or ".." in parts:
        raise CreativeCodeReviewDispositionContractError(
            f"{label} must not contain traversal segments."
        )
    normalized = path.as_posix()
    if normalized in {".git", ".venv", "artifacts", "worktrees"} or any(
        normalized.startswith(prefix) for prefix in (".git/", ".venv/", "artifacts/", "worktrees/")
    ):
        raise CreativeCodeReviewDispositionContractError(
            f"{label} points to a forbidden local surface."
        )
    reject_unsafe_review_value(normalized, label=label)
    return normalized


def _default_review_authority() -> dict[str, bool]:
    return {key: False for key in sorted(REVIEW_AUTHORITY_KEYS)}


def default_repair_launch_authority() -> dict[str, bool]:
    """Return the only authority PR-5 can prepare for later human review."""

    return {
        "create_pr1_specification": True,
        "edit_fixed_mapping": False,
        "generate_patch": False,
        "merge": False,
        "open_pr": False,
        "push": False,
        "resolve_threads": False,
        "write_branch": False,
    }


def _normalize_review_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodeReviewDispositionContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, REVIEW_AUTHORITY_KEYS, label="authority")
    return {
        key: _require_bool(raw_authority, key, expected=False, label="authority")
        for key in sorted(REVIEW_AUTHORITY_KEYS)
    }


def _normalize_repair_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodeReviewDispositionContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, REPAIR_AUTHORITY_KEYS, label="authority")
    normalized: dict[str, bool] = {}
    for key in sorted(REPAIR_AUTHORITY_KEYS):
        normalized[key] = _require_bool(
            raw_authority,
            key,
            expected=(key == "create_pr1_specification"),
            label="authority",
        )
    return normalized


def sanitize_review_excerpt(raw_text: str, *, max_chars: int = MAX_EXCERPT_CHARS) -> dict[str, Any]:
    """Return bounded sanitized excerpt metadata without preserving raw body."""

    if not isinstance(raw_text, str):
        raise CreativeCodeReviewDispositionContractError("review excerpt source must be a string.")
    normalized = re.sub(r"\s+", " ", raw_text).strip()
    if not normalized:
        raise CreativeCodeReviewDispositionContractError("review excerpt must not be empty.")
    reject_unsafe_review_value(normalized, label="sanitized_excerpt")
    truncated = len(normalized) > max_chars
    text = normalized[: max_chars - 3].rstrip() + "..." if truncated else normalized
    excerpt = {
        "text": text,
        "char_count": len(text),
        "truncated": truncated,
        "body_fingerprint": fingerprint_payload({"sanitized_excerpt": text}),
    }
    return _normalize_sanitized_excerpt(excerpt)


def _normalize_source(raw_source: Any) -> dict[str, Any]:
    if not isinstance(raw_source, dict):
        raise CreativeCodeReviewDispositionContractError("source must be a JSON object.")
    _require_exact_keys(raw_source, SOURCE_KEYS, label="source")
    source_kind = _require_token(raw_source, "source_kind", label="source")
    if source_kind not in SOURCE_KINDS:
        raise CreativeCodeReviewDispositionContractError("source.source_kind is unsupported.")
    normalized = {
        "source_kind": source_kind,
        "source_id": _require_id(raw_source, "source_id", label="source"),
        "source_url": _require_optional_url(raw_source["source_url"], label="source.source_url"),
        "repository": _require_optional_repository(
            raw_source["repository"], label="source.repository"
        ),
        "pr_number": _require_optional_int(
            raw_source["pr_number"], min_value=1, max_value=1_000_000, label="source.pr_number"
        ),
        "head_sha": _require_optional_sha(raw_source["head_sha"], label="source.head_sha"),
        "observed_at_utc": _require_optional_timestamp(
            raw_source["observed_at_utc"], label="source.observed_at_utc"
        ),
    }
    reject_unsafe_review_value(normalized, label="source")
    return normalized


def _normalize_review_surface(raw_surface: Any) -> dict[str, Any]:
    if not isinstance(raw_surface, dict):
        raise CreativeCodeReviewDispositionContractError("review_surface must be a JSON object.")
    _require_exact_keys(raw_surface, REVIEW_SURFACE_KEYS, label="review_surface")
    side = raw_surface["side"]
    if side not in {"left", "right", "unknown"}:
        raise CreativeCodeReviewDispositionContractError("review_surface.side is unsupported.")
    return {
        "path": _normalize_repo_relative_path(raw_surface["path"], label="review_surface.path"),
        "line": _require_optional_int(
            raw_surface["line"], min_value=1, max_value=10_000_000, label="review_surface.line"
        ),
        "side": side,
    }


def _normalize_classification(raw_classification: Any) -> dict[str, Any]:
    if not isinstance(raw_classification, dict):
        raise CreativeCodeReviewDispositionContractError("classification must be a JSON object.")
    _require_exact_keys(raw_classification, CLASSIFICATION_KEYS, label="classification")
    candidate_disposition = _require_token(
        raw_classification, "candidate_disposition", label="classification"
    )
    reason_code = _require_token(raw_classification, "reason_code", label="classification")
    if candidate_disposition not in DISPOSITION_CANDIDATES:
        raise CreativeCodeReviewDispositionContractError(
            "classification.candidate_disposition is unsupported."
        )
    if reason_code not in REASON_CODES:
        raise CreativeCodeReviewDispositionContractError(
            "classification.reason_code is unsupported."
        )
    requires_human_decision = _require_bool(
        raw_classification, "requires_human_decision", expected=True, label="classification"
    )
    requires_repair = _require_any_bool(
        raw_classification, "requires_repair", label="classification"
    )
    repair_priority = _require_int(
        raw_classification,
        "repair_priority",
        min_value=0,
        max_value=3,
        label="classification",
    )
    if requires_repair != (
        candidate_disposition in {"creative_repair_candidate", "security_blocker"}
    ):
        raise CreativeCodeReviewDispositionContractError(
            "classification.requires_repair must match repair-capable disposition."
        )
    if not requires_repair and repair_priority != 0:
        raise CreativeCodeReviewDispositionContractError(
            "classification.repair_priority must be 0 unless repair is required."
        )
    if requires_repair and repair_priority == 0:
        raise CreativeCodeReviewDispositionContractError(
            "classification.repair_priority must be positive when repair is required."
        )
    return {
        "candidate_disposition": candidate_disposition,
        "reason_code": reason_code,
        "requires_human_decision": requires_human_decision,
        "requires_repair": requires_repair,
        "repair_priority": repair_priority,
    }


def _normalize_sanitized_excerpt(raw_excerpt: Any) -> dict[str, Any]:
    if not isinstance(raw_excerpt, dict):
        raise CreativeCodeReviewDispositionContractError("sanitized_excerpt must be a JSON object.")
    _require_exact_keys(raw_excerpt, EXCERPT_KEYS, label="sanitized_excerpt")
    text = raw_excerpt.get("text")
    if not isinstance(text, str) or not text.strip():
        raise CreativeCodeReviewDispositionContractError("sanitized_excerpt.text must be string.")
    if len(text) > MAX_EXCERPT_CHARS:
        raise CreativeCodeReviewDispositionContractError("sanitized_excerpt.text is too long.")
    reject_unsafe_review_value(text, label="sanitized_excerpt.text")
    char_count = _require_int(
        raw_excerpt,
        "char_count",
        min_value=1,
        max_value=MAX_EXCERPT_CHARS,
        label="sanitized_excerpt",
    )
    if char_count != len(text):
        raise CreativeCodeReviewDispositionContractError(
            "sanitized_excerpt.char_count must match text length."
        )
    truncated = _require_any_bool(raw_excerpt, "truncated", label="sanitized_excerpt")
    body_fingerprint = _require_sha256(raw_excerpt, "body_fingerprint", label="sanitized_excerpt")
    expected = fingerprint_payload({"sanitized_excerpt": text})
    if body_fingerprint != expected:
        raise CreativeCodeReviewDispositionContractError(
            "sanitized_excerpt.body_fingerprint does not match excerpt."
        )
    return {
        "text": text,
        "char_count": char_count,
        "truncated": truncated,
        "body_fingerprint": body_fingerprint,
    }


def _record_identity_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in sorted(RECORD_KEYS - {"record_id", "idempotency_key", "fingerprints"})
    }


def _record_identity(record: Mapping[str, Any]) -> tuple[str, str, str]:
    record_fingerprint = fingerprint_payload(cast(Any, _record_identity_payload(record)))
    source = cast(Mapping[str, Any], record["source"])
    excerpt = cast(Mapping[str, Any], record["sanitized_excerpt"])
    upstream_ids = (str(source["source_id"]), str(excerpt["body_fingerprint"]))
    record_id = build_asset_id(
        asset_type=FEEDBACK_RECORD_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=record_fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=FEEDBACK_RECORD_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=record_fingerprint,
        upstream_ids=upstream_ids,
    )
    return record_id, idempotency_key, record_fingerprint


def build_creative_code_review_feedback_record(
    *,
    source_kind: str,
    source_id: str,
    source_fingerprint: str,
    excerpt: str,
    feedback_kind: str,
    severity: str = "note",
    source_url: str | None = None,
    repository: str | None = None,
    pr_number: int | None = None,
    head_sha: str | None = None,
    observed_at_utc: str | None = None,
    path: str | None = None,
    line: int | None = None,
    side: str = "unknown",
    classification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a sanitized local feedback record with deterministic identity."""

    if classification is None:
        classification = {
            "candidate_disposition": "out_of_scope",
            "reason_code": "unknown",
            "requires_human_decision": True,
            "requires_repair": False,
            "repair_priority": 0,
        }
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": FEEDBACK_RECORD_TYPE,
        "policy_version": POLICY_VERSION,
        "record_id": "pending",
        "idempotency_key": "pending",
        "source": {
            "source_kind": source_kind,
            "source_id": source_id,
            "source_url": source_url,
            "repository": repository,
            "pr_number": pr_number,
            "head_sha": head_sha,
            "observed_at_utc": observed_at_utc,
        },
        "review_surface": {"path": path, "line": line, "side": side},
        "feedback_kind": feedback_kind,
        "severity": severity,
        "classification": dict(classification),
        "sanitized_excerpt": sanitize_review_excerpt(excerpt),
        "fingerprints": {
            "source_fingerprint": source_fingerprint,
            "record_fingerprint": "pending",
        },
        "authority": _default_review_authority(),
        "sanitized": True,
    }
    source = _normalize_source(record["source"])
    if feedback_kind not in FEEDBACK_KINDS:
        raise CreativeCodeReviewDispositionContractError("feedback_kind is unsupported.")
    if severity not in SEVERITIES:
        raise CreativeCodeReviewDispositionContractError("severity is unsupported.")
    record["source"] = source
    record["review_surface"] = _normalize_review_surface(record["review_surface"])
    record["classification"] = _normalize_classification(record["classification"])
    record["fingerprints"]["source_fingerprint"] = _require_sha256(
        record["fingerprints"], "source_fingerprint", label="fingerprints"
    )
    record_id, idempotency_key, record_fingerprint = _record_identity(record)
    record["record_id"] = record_id
    record["idempotency_key"] = idempotency_key
    record["fingerprints"]["record_fingerprint"] = record_fingerprint
    return validate_creative_code_review_feedback_record(record)


def validate_creative_code_review_feedback_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeCodeReviewFeedbackRecord"
    _require_exact_keys(payload, RECORD_KEYS, label=label)
    feedback_kind = _require_token(payload, "feedback_kind", label=label)
    severity = _require_token(payload, "severity", label=label)
    if feedback_kind not in FEEDBACK_KINDS:
        raise CreativeCodeReviewDispositionContractError(f"{label}.feedback_kind is unsupported.")
    if severity not in SEVERITIES:
        raise CreativeCodeReviewDispositionContractError(f"{label}.severity is unsupported.")
    fingerprints = payload["fingerprints"]
    if not isinstance(fingerprints, dict):
        raise CreativeCodeReviewDispositionContractError("fingerprints must be a JSON object.")
    _require_exact_keys(fingerprints, FINGERPRINT_KEYS, label="fingerprints")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "record_type": _require_const(payload, "record_type", FEEDBACK_RECORD_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "record_id": _require_id(payload, "record_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_source(payload["source"]),
        "review_surface": _normalize_review_surface(payload["review_surface"]),
        "feedback_kind": feedback_kind,
        "severity": severity,
        "classification": _normalize_classification(payload["classification"]),
        "sanitized_excerpt": _normalize_sanitized_excerpt(payload["sanitized_excerpt"]),
        "fingerprints": {
            "source_fingerprint": _require_sha256(
                fingerprints, "source_fingerprint", label="fingerprints"
            ),
            "record_fingerprint": _require_sha256(
                fingerprints, "record_fingerprint", label="fingerprints"
            ),
        },
        "authority": _normalize_review_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    record_id, idempotency_key, record_fingerprint = _record_identity(normalized)
    if normalized["record_id"] != record_id:
        raise CreativeCodeReviewDispositionContractError("record_id does not match record content.")
    if normalized["idempotency_key"] != idempotency_key:
        raise CreativeCodeReviewDispositionContractError(
            "idempotency_key does not match record content."
        )
    if normalized["fingerprints"]["record_fingerprint"] != record_fingerprint:
        raise CreativeCodeReviewDispositionContractError(
            "record_fingerprint does not match record content."
        )
    reject_unsafe_review_value(normalized, label=label)
    return normalized


def classify_feedback_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic classification for one validated feedback record."""

    normalized = validate_creative_code_review_feedback_record(record)
    text = normalized["sanitized_excerpt"]["text"].lower()
    severity = normalized["severity"]
    feedback_kind = normalized["feedback_kind"]
    reason_code = "unknown"
    disposition = "out_of_scope"
    priority = 0

    if any(
        marker in text
        for marker in (
            "resolve review thread",
            "resolve thread",
            "fixed mapping",
            "merge readiness",
            "open pr",
            "push branch",
            "unsafe authority",
        )
    ):
        reason_code = "unsafe_authority"
        disposition = "security_blocker"
        priority = 3
    elif any(marker in text for marker in ("secret", "token", "credential", "vulnerability")):
        reason_code = "security_sensitive"
        disposition = "security_blocker"
        priority = 3
    elif any(marker in text for marker in ("test fail", "lint fail", "coverage", "guard fail")):
        reason_code = "test_failure"
        disposition = "creative_repair_candidate"
        priority = 2
    elif feedback_kind in {"context_warning", "review_source_status"}:
        reason_code = "source_degraded"
        disposition = "out_of_scope"
    elif severity in {"high", "critical"}:
        reason_code = "security_sensitive"
        disposition = "security_blocker" if severity == "critical" else "creative_repair_candidate"
        priority = 2 if severity == "high" else 3
    elif "not a bug" in text or "works as intended" in text:
        reason_code = "already_addressed"
        disposition = "not_a_bug_candidate"
    elif "defer" in text or "backlog" in text:
        reason_code = "fixed_mapping_governance"
        disposition = "defer_candidate"
    elif "docs" in text or "documentation" in text:
        reason_code = "documentation"
        disposition = "simple_fix"
        priority = 0

    classified = dict(normalized)
    classified["classification"] = {
        "candidate_disposition": disposition,
        "reason_code": reason_code,
        "requires_human_decision": True,
        "requires_repair": disposition in {"creative_repair_candidate", "security_blocker"},
        "repair_priority": priority,
    }
    classified["record_id"] = "pending"
    classified["idempotency_key"] = "pending"
    classified["fingerprints"] = {
        "source_fingerprint": normalized["fingerprints"]["source_fingerprint"],
        "record_fingerprint": "pending",
    }
    record_id, idempotency_key, record_fingerprint = _record_identity(classified)
    classified["record_id"] = record_id
    classified["idempotency_key"] = idempotency_key
    classified["fingerprints"]["record_fingerprint"] = record_fingerprint
    return validate_creative_code_review_feedback_record(classified)


def _normalize_source_context(raw_context: Any) -> dict[str, Any]:
    if not isinstance(raw_context, dict):
        raise CreativeCodeReviewDispositionContractError("source_context must be a JSON object.")
    _require_exact_keys(raw_context, SOURCE_CONTEXT_KEYS, label="source_context")
    source_kind = _require_token(raw_context, "source_kind", label="source_context")
    if source_kind not in SOURCE_KINDS:
        raise CreativeCodeReviewDispositionContractError(
            "source_context.source_kind is unsupported."
        )
    context_path = _normalize_repo_relative_path(
        raw_context["context_path"], label="source_context.context_path"
    )
    normalized = {
        "source_kind": source_kind,
        "source_id": _require_id(raw_context, "source_id", label="source_context"),
        "source_fingerprint": _require_sha256(
            raw_context, "source_fingerprint", label="source_context"
        ),
        "context_path": context_path,
        "repository": _require_optional_repository(
            raw_context["repository"], label="source_context.repository"
        ),
        "pr_number": _require_optional_int(
            raw_context["pr_number"],
            min_value=1,
            max_value=1_000_000,
            label="source_context.pr_number",
        ),
    }
    reject_unsafe_review_value(normalized, label="source_context")
    return normalized


def _summary_for_records(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    normalized = [validate_creative_code_review_feedback_record(record) for record in records]
    repair_candidates = sum(
        1 for record in normalized if record["classification"]["requires_repair"]
    )
    not_actionable = sum(
        1
        for record in normalized
        if record["classification"]["candidate_disposition"] == "not_a_bug_candidate"
    )
    deferred = sum(
        1
        for record in normalized
        if record["classification"]["candidate_disposition"] == "defer_candidate"
    )
    drift = sum(
        1 for record in normalized if record["classification"]["reason_code"] == "head_sha_drift"
    )
    highest = max(
        (int(record["classification"]["repair_priority"]) for record in normalized),
        default=0,
    )
    return {
        "blocked_by_head_drift": drift,
        "deferred_candidates": deferred,
        "highest_repair_priority": highest,
        "not_actionable": not_actionable,
        "records_total": len(normalized),
        "repair_candidates": repair_candidates,
    }


def _packet_identity_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {key: packet[key] for key in sorted(PACKET_KEYS - {"packet_id", "idempotency_key"})}


def _packet_identity(packet: Mapping[str, Any]) -> tuple[str, str, str]:
    packet_fingerprint = fingerprint_payload(cast(Any, _packet_identity_payload(packet)))
    source_context = cast(Mapping[str, Any], packet["source_context"])
    upstream_ids = (str(source_context["source_id"]), str(packet["actual_head_sha"] or "no-head"))
    packet_id = build_asset_id(
        asset_type=DISPOSITION_PACKET_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=packet_fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=DISPOSITION_PACKET_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=packet_fingerprint,
        upstream_ids=upstream_ids,
    )
    return packet_id, idempotency_key, packet_fingerprint


def build_creative_code_review_disposition_packet(
    *,
    feedback_records: Sequence[Mapping[str, Any]],
    source_context: Mapping[str, Any],
    expected_head_sha: str | None = None,
    actual_head_sha: str | None = None,
    classify: bool = True,
) -> dict[str, Any]:
    """Build a sanitized advisory disposition packet from local feedback."""

    records = [
        (
            classify_feedback_record(record)
            if classify
            else validate_creative_code_review_feedback_record(record)
        )
        for record in feedback_records
    ]
    expected_head = _require_optional_sha(expected_head_sha, label="expected_head_sha")
    actual_head = _require_optional_sha(actual_head_sha, label="actual_head_sha")
    drift = bool(expected_head and actual_head and expected_head != actual_head)
    if drift:
        drifted: list[dict[str, Any]] = []
        for record in records:
            updated = dict(record)
            updated["classification"] = {
                "candidate_disposition": "out_of_scope",
                "reason_code": "head_sha_drift",
                "requires_human_decision": True,
                "requires_repair": False,
                "repair_priority": 0,
            }
            updated["record_id"] = "pending"
            updated["idempotency_key"] = "pending"
            updated["fingerprints"] = {
                "source_fingerprint": record["fingerprints"]["source_fingerprint"],
                "record_fingerprint": "pending",
            }
            record_id, idempotency_key, record_fingerprint = _record_identity(updated)
            updated["record_id"] = record_id
            updated["idempotency_key"] = idempotency_key
            updated["fingerprints"]["record_fingerprint"] = record_fingerprint
            drifted.append(validate_creative_code_review_feedback_record(updated))
        records = drifted

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "packet_type": DISPOSITION_PACKET_TYPE,
        "policy_version": POLICY_VERSION,
        "packet_id": "pending",
        "idempotency_key": "pending",
        "source_context": dict(source_context),
        "expected_head_sha": expected_head,
        "actual_head_sha": actual_head,
        "head_sha_drift": drift,
        "feedback_records": records,
        "summary": _summary_for_records(records),
        "authority": _default_review_authority(),
        "sanitized": True,
    }
    packet["source_context"] = _normalize_source_context(packet["source_context"])
    packet_id, idempotency_key, _packet_fingerprint = _packet_identity(packet)
    packet["packet_id"] = packet_id
    packet["idempotency_key"] = idempotency_key
    return validate_creative_code_review_disposition_packet(packet)


def validate_creative_code_review_disposition_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeCodeReviewDispositionPacket"
    _require_exact_keys(payload, PACKET_KEYS, label=label)
    expected_head = _require_optional_sha(payload["expected_head_sha"], label="expected_head_sha")
    actual_head = _require_optional_sha(payload["actual_head_sha"], label="actual_head_sha")
    head_sha_drift = _require_any_bool(payload, "head_sha_drift", label=label)
    if head_sha_drift != bool(expected_head and actual_head and expected_head != actual_head):
        raise CreativeCodeReviewDispositionContractError(
            "head_sha_drift must match expected_head_sha/actual_head_sha."
        )
    raw_records = payload["feedback_records"]
    if not isinstance(raw_records, list):
        raise CreativeCodeReviewDispositionContractError("feedback_records must be an array.")
    records = [validate_creative_code_review_feedback_record(record) for record in raw_records]
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise CreativeCodeReviewDispositionContractError("summary must be a JSON object.")
    _require_exact_keys(summary, SUMMARY_KEYS, label="summary")
    normalized_summary = {
        "records_total": _require_int(
            summary, "records_total", min_value=0, max_value=10_000, label="summary"
        ),
        "repair_candidates": _require_int(
            summary, "repair_candidates", min_value=0, max_value=10_000, label="summary"
        ),
        "not_actionable": _require_int(
            summary, "not_actionable", min_value=0, max_value=10_000, label="summary"
        ),
        "deferred_candidates": _require_int(
            summary, "deferred_candidates", min_value=0, max_value=10_000, label="summary"
        ),
        "blocked_by_head_drift": _require_int(
            summary, "blocked_by_head_drift", min_value=0, max_value=10_000, label="summary"
        ),
        "highest_repair_priority": _require_int(
            summary, "highest_repair_priority", min_value=0, max_value=3, label="summary"
        ),
    }
    expected_summary = _summary_for_records(records)
    if normalized_summary != expected_summary:
        raise CreativeCodeReviewDispositionContractError("summary does not match feedback_records.")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "packet_type": _require_const(payload, "packet_type", DISPOSITION_PACKET_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "packet_id": _require_id(payload, "packet_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_context": _normalize_source_context(payload["source_context"]),
        "expected_head_sha": expected_head,
        "actual_head_sha": actual_head,
        "head_sha_drift": head_sha_drift,
        "feedback_records": records,
        "summary": normalized_summary,
        "authority": _normalize_review_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    packet_id, idempotency_key, _packet_fingerprint = _packet_identity(normalized)
    if normalized["packet_id"] != packet_id:
        raise CreativeCodeReviewDispositionContractError("packet_id does not match packet content.")
    if normalized["idempotency_key"] != idempotency_key:
        raise CreativeCodeReviewDispositionContractError(
            "idempotency_key does not match packet content."
        )
    reject_unsafe_review_value(normalized, label=label)
    return normalized


def disposition_packet_fingerprint(packet: Mapping[str, Any]) -> str:
    normalized = validate_creative_code_review_disposition_packet(packet)
    return cast(str, fingerprint_payload(cast(Any, _packet_identity_payload(normalized))))


def validate_creative_code_review_feedback_collection(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    label = "CreativeCodeReviewFeedbackCollection"
    _require_exact_keys(payload, COLLECTION_KEYS, label=label)
    raw_records = payload["feedback_records"]
    if not isinstance(raw_records, list):
        raise CreativeCodeReviewDispositionContractError("feedback_records must be an array.")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload, "artifact_type", FEEDBACK_COLLECTION_TYPE, label=label
        ),
        "source_context": _normalize_source_context(payload["source_context"]),
        "feedback_records": [
            validate_creative_code_review_feedback_record(record) for record in raw_records
        ],
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    reject_unsafe_review_value(normalized, label=label)
    return normalized


def _launch_identity_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: packet[key] for key in sorted(REPAIR_LAUNCH_KEYS - {"launch_id", "idempotency_key"})
    }


def _launch_identity(packet: Mapping[str, Any]) -> tuple[str, str]:
    launch_fingerprint = fingerprint_payload(cast(Any, _launch_identity_payload(packet)))
    upstream_ids = (
        str(packet["source_disposition_packet_id"]),
        str(packet["source_disposition_packet_fingerprint"]),
    )
    launch_id = build_asset_id(
        asset_type=REPAIR_LAUNCH_PACKET_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=launch_fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=REPAIR_LAUNCH_PACKET_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=launch_fingerprint,
        upstream_ids=upstream_ids,
    )
    return launch_id, idempotency_key


def build_creative_code_repair_launch_packet(
    disposition_packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Prepare a specification-only repair launch packet from a current packet."""

    packet = validate_creative_code_review_disposition_packet(disposition_packet)
    if packet["head_sha_drift"]:
        raise CreativeCodeReviewDispositionContractError(
            "Cannot prepare repair launch while review disposition head SHA drift is present."
        )
    candidates: list[dict[str, Any]] = []
    for record in packet["feedback_records"]:
        classification = record["classification"]
        if not classification["requires_repair"]:
            continue
        candidates.append(
            {
                "record_id": record["record_id"],
                "reason_code": classification["reason_code"],
                "repair_priority": classification["repair_priority"],
                "sanitized_excerpt": record["sanitized_excerpt"]["text"],
                "source_fingerprint": record["fingerprints"]["source_fingerprint"],
            }
        )
    candidates = sorted(
        candidates,
        key=lambda row: (-int(row["repair_priority"]), str(row["record_id"])),
    )
    launch: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "packet_type": REPAIR_LAUNCH_PACKET_TYPE,
        "policy_version": POLICY_VERSION,
        "launch_id": "pending",
        "idempotency_key": "pending",
        "source_disposition_packet_id": packet["packet_id"],
        "source_disposition_packet_fingerprint": disposition_packet_fingerprint(packet),
        "target_pr1_specification": {
            "allowed": bool(candidates),
            "reason": (
                "repair candidates may be converted into a PR-1 specification packet"
                if candidates
                else "no repair candidates present"
            ),
            "source_packet_id": packet["packet_id"],
        },
        "repair_candidates": candidates,
        "authority": default_repair_launch_authority(),
        "sanitized": True,
    }
    launch_id, idempotency_key = _launch_identity(launch)
    launch["launch_id"] = launch_id
    launch["idempotency_key"] = idempotency_key
    return validate_creative_code_repair_launch_packet(launch)


def _normalize_target_pr1(raw_target: Any) -> dict[str, Any]:
    if not isinstance(raw_target, dict):
        raise CreativeCodeReviewDispositionContractError(
            "target_pr1_specification must be a JSON object."
        )
    _require_exact_keys(raw_target, TARGET_PR1_KEYS, label="target_pr1_specification")
    reason = raw_target["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise CreativeCodeReviewDispositionContractError(
            "target_pr1_specification.reason must be a string."
        )
    if len(reason) > MAX_EXCERPT_CHARS:
        raise CreativeCodeReviewDispositionContractError(
            "target_pr1_specification.reason is too long."
        )
    reject_unsafe_review_value(reason, label="target_pr1_specification.reason")
    return {
        "allowed": _require_any_bool(raw_target, "allowed", label="target_pr1_specification"),
        "reason": reason,
        "source_packet_id": _require_id(
            raw_target, "source_packet_id", label="target_pr1_specification"
        ),
    }


def _normalize_repair_candidate(raw_candidate: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(raw_candidate, dict):
        raise CreativeCodeReviewDispositionContractError(
            f"repair_candidates[{index}] must be a JSON object."
        )
    _require_exact_keys(raw_candidate, REPAIR_CANDIDATE_KEYS, label=f"repair_candidates[{index}]")
    reason_code = _require_token(raw_candidate, "reason_code", label=f"repair_candidates[{index}]")
    if reason_code not in REASON_CODES:
        raise CreativeCodeReviewDispositionContractError(
            f"repair_candidates[{index}].reason_code is unsupported."
        )
    excerpt = raw_candidate["sanitized_excerpt"]
    if not isinstance(excerpt, str) or not excerpt.strip():
        raise CreativeCodeReviewDispositionContractError(
            f"repair_candidates[{index}].sanitized_excerpt must be a string."
        )
    if len(excerpt) > MAX_EXCERPT_CHARS:
        raise CreativeCodeReviewDispositionContractError(
            f"repair_candidates[{index}].sanitized_excerpt is too long."
        )
    reject_unsafe_review_value(excerpt, label=f"repair_candidates[{index}].sanitized_excerpt")
    return {
        "record_id": _require_id(raw_candidate, "record_id", label=f"repair_candidates[{index}]"),
        "reason_code": reason_code,
        "repair_priority": _require_int(
            raw_candidate,
            "repair_priority",
            min_value=1,
            max_value=3,
            label=f"repair_candidates[{index}]",
        ),
        "sanitized_excerpt": excerpt,
        "source_fingerprint": _require_sha256(
            raw_candidate, "source_fingerprint", label=f"repair_candidates[{index}]"
        ),
    }


def validate_creative_code_repair_launch_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeCodeRepairLaunchPacket"
    _require_exact_keys(payload, REPAIR_LAUNCH_KEYS, label=label)
    raw_candidates = payload["repair_candidates"]
    if not isinstance(raw_candidates, list):
        raise CreativeCodeReviewDispositionContractError("repair_candidates must be an array.")
    candidates = [
        _normalize_repair_candidate(candidate, index=index)
        for index, candidate in enumerate(raw_candidates)
    ]
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "packet_type": _require_const(
            payload, "packet_type", REPAIR_LAUNCH_PACKET_TYPE, label=label
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "launch_id": _require_id(payload, "launch_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_disposition_packet_id": _require_id(
            payload, "source_disposition_packet_id", label=label
        ),
        "source_disposition_packet_fingerprint": _require_sha256(
            payload, "source_disposition_packet_fingerprint", label=label
        ),
        "target_pr1_specification": _normalize_target_pr1(payload["target_pr1_specification"]),
        "repair_candidates": sorted(
            candidates,
            key=lambda row: (-int(row["repair_priority"]), str(row["record_id"])),
        ),
        "authority": _normalize_repair_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["target_pr1_specification"]["allowed"] != bool(candidates):
        raise CreativeCodeReviewDispositionContractError(
            "target_pr1_specification.allowed must match repair candidate presence."
        )
    launch_id, idempotency_key = _launch_identity(normalized)
    if normalized["launch_id"] != launch_id:
        raise CreativeCodeReviewDispositionContractError("launch_id does not match launch content.")
    if normalized["idempotency_key"] != idempotency_key:
        raise CreativeCodeReviewDispositionContractError(
            "idempotency_key does not match launch content."
        )
    reject_unsafe_review_value(normalized, label=label)
    return normalized


def _read_artifact_by_type(path: str | Path) -> dict[str, Any]:
    payload = read_json_object(path)
    artifact_type = (
        payload.get("record_type") or payload.get("artifact_type") or payload.get("packet_type")
    )
    if artifact_type == FEEDBACK_RECORD_TYPE:
        return validate_creative_code_review_feedback_record(payload)
    if artifact_type == FEEDBACK_COLLECTION_TYPE:
        return validate_creative_code_review_feedback_collection(payload)
    if artifact_type == DISPOSITION_PACKET_TYPE:
        return validate_creative_code_review_disposition_packet(payload)
    if artifact_type == REPAIR_LAUNCH_PACKET_TYPE:
        return validate_creative_code_repair_launch_packet(payload)
    raise CreativeCodeReviewDispositionContractError("Unsupported review-disposition artifact.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate PR-5 creative-code review-disposition artifacts."
    )
    parser.add_argument("paths", nargs="+", help="Artifact JSON path(s) to validate")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        for path in args.paths:
            _read_artifact_by_type(path)
    except CreativeCodeReviewDispositionContractError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
