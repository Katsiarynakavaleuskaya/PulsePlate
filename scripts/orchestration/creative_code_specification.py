"""Validate and synthesize governed creative-code specification bundles.

PR-1 is a local control-plane layer only. It converts a validated PR-0
CreativeCodeCandidatePacket into implementation specifications and a deterministic
human-review bundle. It never emits patches, calls providers, writes the repo, or
claims review/merge authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, cast

from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from scripts.orchestration.creative_code_contract import (
    AUTHORITY_FALSE_KEYS,
    AUTHORITY_TRUE_KEYS,
    CreativeCodeContractError,
    validate_creative_code_candidate_packet,
)
from scripts.orchestration.creative_code_rejection_index import (
    build_creative_code_rejection_index,
    validate_creative_code_rejection_index,
)
from scripts.orchestration.experiment_contract import validate_mutable_candidate_surface

SCHEMA_VERSION = "1.0"
BUNDLE_TYPE = "creative_code_specification_bundle"
POLICY_VERSION = "creative-code-specification-pr1"
SUCCESS_OUTPUT = "PASS: creative-code specification bundle valid"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key)",
    re.IGNORECASE,
)
UNSAFE_LOCAL_ABSOLUTE_PATH_RE = re.compile(
    r"(^|[\s:=,(\[{'\"`<])(?:"
    r"/(?:users|home|etc|workspace|tmp)(?:/|$|[\s:;,.)\]}'\"`>])|"
    r"/(?:private/var|var/folders)(?:/|$|[\s:;,.)\]}'\"`>])|"
    r"~[/\\](?:\.ssh(?:[/\\]|$|[\s:;,.)\]}'\"`>])|[^ \t\r\n]*)?|"
    r"[A-Za-z]:[/\\](?:Users|Documents and Settings|Windows|Temp|tmp)"
    r"(?:[/\\]|$|[\s:;,.)\]}'\"`>])|"
    r"\\\\[^\\/\s]+[/\\][^\\/\s]+"
    r")",
    re.IGNORECASE,
)
UNSAFE_TEXT_RE = re.compile(
    r"(candidate\.patch|diff --git|^\+\+\+ |^--- |@@ |provider[_ -]?payload|"
    r"raw[_ -]?(prompt|response|context)|chain[_ -]?of[_ -]?thought|"
    r"https?://|http request|"
    r"(openai|anthropic|provider) (api|scoring|model)|api\.openai\.com|"
    r"runtime service|product runtime|"
    r"apply (a )?(repository )?patch|repository patch|commit changes|git commit|git push|"
    r"open (a )?(draft )?(pull request|PR)|"
    r"create (a )?(pull request|PR|branch)|"
    r"push (the )?branch|"
    r"write (to )?(the )?repository|write repository|"
    r"write (to )?(the )?(shared )?worktree( files)?|"
    r"resolve review thread|mark ready for review|merge readiness|"
    r"semantic cache serving|use semantic cache|call model|call network|"
    r"guarantee[s]? (weight loss|health outcome|clinical outcome)|"
    r"\bdiagnose\b|\btreat\b|clinical efficacy|crisis support|emergency care)",
    re.IGNORECASE | re.MULTILINE,
)

AUTHORITY_FALSE_KEYS_PR1: tuple[str, ...] = AUTHORITY_FALSE_KEYS
AUTHORITY_TRUE_KEYS_PR1: tuple[str, ...] = AUTHORITY_TRUE_KEYS
AUTHORITY_KEYS = frozenset((*AUTHORITY_TRUE_KEYS_PR1, *AUTHORITY_FALSE_KEYS_PR1))

APPROACH_FAMILIES: tuple[str, ...] = (
    "minimal_surgical_change",
    "seam_extraction",
    "fail_closed_guard",
    "observable_metadata_only",
    "test_first_contract_lock",
)
REQUIRED_SKEPTIC_REVIEWERS: tuple[str, ...] = (
    "architecture-specialist",
    "security-auditor",
    "qa-engineer-agent",
)
REVIEW_DECISIONS = frozenset({"pass", "revise", "reject"})
GENERATION_STATUSES = frozenset({"specifications_generated", "all_rejected", "spec_blocked"})
ORACLE_STATUSES = frozenset(
    {"not_run_specification_only", "skeptic_review_passed", "skeptic_review_blocked"}
)
FAILURE_CLASSES = frozenset(
    {
        None,
        "policy_violation",
        "unsafe_authority",
        "duplicate_spec_fingerprint",
        "review_blocker",
        "invalid_input",
    }
)
HUMAN_DECISIONS = frozenset({"pending", "review_required", "discard", "retry_with_new_evidence"})
RANKING_POLICY = "pass_count_then_fingerprint_then_ordinal"

TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "bundle_type",
        "bundle_id",
        "idempotency_key",
        "policy_version",
        "source_packet_id",
        "source_packet_idempotency_key",
        "source_packet_fingerprint",
        "source_candidate_id",
        "source_creative_research",
        "target_surface",
        "immutable_oracles",
        "fallback",
        "authority",
        "variants",
        "skeptic_reviews",
        "synthesis",
        "rejection_index",
        "generation_status",
        "oracle_status",
        "failure_class",
        "human_decision",
        "cost_metadata_available",
        "telemetry_summary",
    }
)
SOURCE_RESEARCH_KEYS = frozenset(
    {"bundle_id", "candidate_id", "promotion_decision", "fingerprint", "evidence_ref"}
)
VARIANT_KEYS = frozenset(
    {
        "variant_id",
        "source_packet_id",
        "source_candidate_id",
        "variant_fingerprint",
        "approach_family",
        "problem_statement",
        "implementation_steps",
        "target_paths",
        "tests_to_add",
        "negative_controls",
        "rollback_plan",
        "falsifier",
        "risk_notes",
        "wellness_boundary",
        "estimated_changed_files",
    }
)
REVIEW_KEYS = frozenset(
    {
        "review_id",
        "source_packet_id",
        "source_candidate_id",
        "variant_id",
        "reviewer_role",
        "decision",
        "blockers",
        "unsafe_authority_flags",
        "duplicate_reason",
        "required_revision",
        "review_fingerprint",
    }
)
SYNTHESIS_KEYS = frozenset(
    {
        "selected_variant_id",
        "selected_variant_fingerprint",
        "selection_reason",
        "ranking_policy",
        "rejected_variant_fingerprints",
        "unresolved_blockers",
        "fallback",
        "next_authority",
        "synthesis_fingerprint",
    }
)
TELEMETRY_KEYS = frozenset(
    {
        "packet_id",
        "source_candidate_id",
        "variant_count",
        "generation_status",
        "oracle_status",
        "failure_class",
        "human_decision",
        "cost_metadata_available",
    }
)

FORBIDDEN_REFERENCE_PREFIXES: tuple[str, ...] = (
    ".git/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "artifacts/",
    "build/",
    "dist/",
    "node_modules/",
    "worktrees/",
)
FORBIDDEN_REFERENCE_PATHS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "artifacts",
        "build",
        "dist",
        "node_modules",
        "worktrees",
    }
)


class CreativeCodeSpecificationError(ValueError):
    """Raised when a creative-code specification bundle violates PR-1 policy."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeSpecificationError(
                f"creative-code specification bundle has duplicate JSON key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_creative_code_specification_bundle(path: Path) -> dict[str, Any]:
    """Read a specification bundle JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeSpecificationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeSpecificationError(
            "Unable to read creative-code specification bundle JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle must be a JSON object."
        )
    return payload


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual_keys = set(payload)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing:
        raise CreativeCodeSpecificationError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodeSpecificationError(f"{label} has unsupported fields: {', '.join(extra)}")


def _require_const(
    payload: Mapping[str, Any],
    key: str,
    expected: Any,
    *,
    label: str,
) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodeSpecificationError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be a safe token.")
    return normalized


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be a sha256 digest.")
    return value


def _require_text(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise CreativeCodeSpecificationError(f"{label}.{key} must be non-empty.")
    _reject_unsafe_text(normalized, label=f"{label}.{key}")
    return normalized


def _reject_unsafe_text(value: str, *, label: str) -> None:
    if "\x00" in value or any(
        ord(character) < 32 and character not in "\n\r\t" for character in value
    ):
        raise CreativeCodeSpecificationError(f"{label} must not contain control characters.")
    if SECRET_RE.search(value) or UNSAFE_TEXT_RE.search(value):
        raise CreativeCodeSpecificationError(f"{label} contains unsafe creative-code authority.")
    if contains_unsafe_local_absolute_path(value):
        raise CreativeCodeSpecificationError(f"{label} must not contain local absolute paths.")


def contains_unsafe_local_absolute_path(value: str) -> bool:
    """Return whether free text contains a machine-local absolute path."""

    return UNSAFE_LOCAL_ABSOLUTE_PATH_RE.search(value) is not None


def _normalize_repo_relative_path(raw_path: Any, *, label: str) -> str:
    if not isinstance(raw_path, str):
        raise CreativeCodeSpecificationError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeCodeSpecificationError(f"{label} must be non-empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeCodeSpecificationError(f"{label} must not contain control characters.")
    if "\\" in value:
        raise CreativeCodeSpecificationError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or Path(value).is_absolute():
        raise CreativeCodeSpecificationError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeCodeSpecificationError(f"{label} must not be a URL or scheme path.")
    path = PurePosixPath(value)
    if not path.parts or "." in path.parts or ".." in path.parts:
        raise CreativeCodeSpecificationError(f"{label} must not contain traversal segments.")
    normalized = path.as_posix()
    if normalized in FORBIDDEN_REFERENCE_PATHS or any(
        normalized.startswith(prefix) for prefix in FORBIDDEN_REFERENCE_PREFIXES
    ):
        raise CreativeCodeSpecificationError(f"{label} points to a forbidden local surface.")
    return normalized


def _normalize_path_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodeSpecificationError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        path = _normalize_repo_relative_path(item, label=f"{label}.{key}[{index}]")
        if path in seen:
            raise CreativeCodeSpecificationError(f"{label}.{key} must not contain duplicates.")
        seen.add(path)
        normalized.append(path)
    return normalized


def _normalize_test_path_list(payload: Mapping[str, Any], key: str, *, label: str) -> list[str]:
    normalized = _normalize_path_list(payload, key, label=label)
    invalid_paths = [path for path in normalized if not path.startswith("tests/")]
    if invalid_paths:
        joined = ", ".join(invalid_paths)
        raise CreativeCodeSpecificationError(
            f"{label}.{key} must stay under tests/. Invalid paths: {joined}"
        )
    return normalized


def _normalize_token_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodeSpecificationError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeCodeSpecificationError(f"{label}.{key}[{index}] must be a string.")
        token = item.strip()
        if not token or not SAFE_TOKEN_RE.fullmatch(token):
            raise CreativeCodeSpecificationError(f"{label}.{key}[{index}] must be a safe token.")
        if SECRET_RE.search(token):
            raise CreativeCodeSpecificationError(
                f"{label}.{key}[{index}] must not contain secret-shaped values."
            )
        if token in seen:
            raise CreativeCodeSpecificationError(f"{label}.{key} must not contain duplicates.")
        seen.add(token)
        normalized.append(token)
    return normalized


def _normalize_text_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodeSpecificationError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeCodeSpecificationError(f"{label}.{key}[{index}] must be a string.")
        text = item.strip()
        if not text:
            raise CreativeCodeSpecificationError(f"{label}.{key}[{index}] must be non-empty.")
        _reject_unsafe_text(text, label=f"{label}.{key}[{index}]")
        if text in seen:
            raise CreativeCodeSpecificationError(f"{label}.{key} must not contain duplicates.")
        seen.add(text)
        normalized.append(text)
    return normalized


def _is_within_surface(path: str, target_surface: Sequence[str]) -> bool:
    for target in target_surface:
        if path == target:
            return True
        if PurePosixPath(target).suffix:
            continue
        if path.startswith(target.rstrip("/") + "/"):
            return True
    return False


def _paths_overlap(left: str, right: str) -> bool:
    if left == right:
        return True
    left_is_file = bool(PurePosixPath(left).suffix)
    right_is_file = bool(PurePosixPath(right).suffix)
    return (not left_is_file and right.startswith(left.rstrip("/") + "/")) or (
        not right_is_file and left.startswith(right.rstrip("/") + "/")
    )


def _reject_immutable_oracle_overlap(
    *,
    target_surface: Sequence[str],
    immutable_oracles: Sequence[str],
) -> None:
    for target in target_surface:
        for oracle in immutable_oracles:
            if _paths_overlap(target, oracle):
                raise CreativeCodeSpecificationError(
                    "target_surface must not overlap immutable_oracles."
                )


def _variant_fingerprint_payload(variant: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: variant[key] for key in sorted(VARIANT_KEYS - {"variant_id", "variant_fingerprint"})
    }


def _review_fingerprint_payload(review: Mapping[str, Any]) -> dict[str, Any]:
    return {key: review[key] for key in sorted(REVIEW_KEYS - {"review_id", "review_fingerprint"})}


def _synthesis_fingerprint_payload(synthesis: Mapping[str, Any]) -> dict[str, Any]:
    return {key: synthesis[key] for key in sorted(SYNTHESIS_KEYS - {"synthesis_fingerprint"})}


def _validate_source_research(raw_source: Any) -> dict[str, str]:
    if not isinstance(raw_source, dict):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.source_creative_research must be a JSON object."
        )
    _require_exact_keys(
        raw_source,
        SOURCE_RESEARCH_KEYS,
        label="CreativeCodeSpecificationBundle.source_creative_research",
    )
    source = {
        "bundle_id": _require_id(
            raw_source,
            "bundle_id",
            label="CreativeCodeSpecificationBundle.source_creative_research",
        ),
        "candidate_id": _require_id(
            raw_source,
            "candidate_id",
            label="CreativeCodeSpecificationBundle.source_creative_research",
        ),
        "promotion_decision": _require_const(
            raw_source,
            "promotion_decision",
            "promote",
            label="CreativeCodeSpecificationBundle.source_creative_research",
        ),
        "fingerprint": _require_fingerprint(
            raw_source,
            "fingerprint",
            label="CreativeCodeSpecificationBundle.source_creative_research",
        ),
        "evidence_ref": _normalize_repo_relative_path(
            raw_source.get("evidence_ref"),
            label="CreativeCodeSpecificationBundle.source_creative_research.evidence_ref",
        ),
    }
    return source


def _validate_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.authority must be a JSON object."
        )
    _require_exact_keys(
        raw_authority, AUTHORITY_KEYS, label="CreativeCodeSpecificationBundle.authority"
    )
    for key in AUTHORITY_TRUE_KEYS_PR1:
        if raw_authority.get(key) is not True:
            raise CreativeCodeSpecificationError(f"authority.{key} must remain true in PR-1.")
    for key in AUTHORITY_FALSE_KEYS_PR1:
        if raw_authority.get(key) is not False:
            raise CreativeCodeSpecificationError(f"authority.{key} must remain false in PR-1.")
    return {key: bool(raw_authority[key]) for key in AUTHORITY_KEYS}


def _validate_variant(
    raw_variant: Any,
    *,
    index: int,
    source_packet_id: str,
    source_candidate_id: str,
    target_surface: Sequence[str],
) -> dict[str, Any]:
    label = f"CreativeCodeSpecificationBundle.variants[{index}]"
    if not isinstance(raw_variant, dict):
        raise CreativeCodeSpecificationError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_variant, VARIANT_KEYS, label=label)
    variant = {
        "variant_id": _require_id(raw_variant, "variant_id", label=label),
        "source_packet_id": _require_const(
            raw_variant,
            "source_packet_id",
            source_packet_id,
            label=label,
        ),
        "source_candidate_id": _require_const(
            raw_variant,
            "source_candidate_id",
            source_candidate_id,
            label=label,
        ),
        "variant_fingerprint": _require_fingerprint(
            raw_variant,
            "variant_fingerprint",
            label=label,
        ),
        "approach_family": _require_token(raw_variant, "approach_family", label=label),
        "problem_statement": _require_text(raw_variant, "problem_statement", label=label),
        "implementation_steps": _normalize_text_list(
            raw_variant,
            "implementation_steps",
            label=label,
        ),
        "target_paths": _normalize_path_list(raw_variant, "target_paths", label=label),
        "tests_to_add": _normalize_test_path_list(raw_variant, "tests_to_add", label=label),
        "negative_controls": _normalize_token_list(
            raw_variant,
            "negative_controls",
            label=label,
        ),
        "rollback_plan": _require_text(raw_variant, "rollback_plan", label=label),
        "falsifier": _require_text(raw_variant, "falsifier", label=label),
        "risk_notes": _normalize_text_list(raw_variant, "risk_notes", label=label),
        "wellness_boundary": _require_text(raw_variant, "wellness_boundary", label=label),
    }
    estimated_changed_files = raw_variant.get("estimated_changed_files")
    if not isinstance(estimated_changed_files, int) or isinstance(estimated_changed_files, bool):
        raise CreativeCodeSpecificationError(f"{label}.estimated_changed_files must be an integer.")
    if not 1 <= estimated_changed_files <= 5:
        raise CreativeCodeSpecificationError(
            f"{label}.estimated_changed_files must be between 1 and 5."
        )
    variant["estimated_changed_files"] = estimated_changed_files
    if variant["approach_family"] not in APPROACH_FAMILIES:
        raise CreativeCodeSpecificationError(f"{label}.approach_family is not supported.")
    try:
        variant["target_paths"] = validate_mutable_candidate_surface(variant["target_paths"])
    except ValueError as exc:
        raise CreativeCodeSpecificationError(str(exc)) from exc
    for path in variant["target_paths"]:
        if not _is_within_surface(path, target_surface):
            raise CreativeCodeSpecificationError(
                f"{label}.target_paths must stay within source target_surface."
            )
    expected_fingerprint = fingerprint_payload(_variant_fingerprint_payload(variant))
    if variant["variant_fingerprint"] != expected_fingerprint:
        raise CreativeCodeSpecificationError(
            f"{label}.variant_fingerprint does not match variant content."
        )
    return variant


def _validate_review(
    raw_review: Any,
    *,
    index: int,
    source_packet_id: str,
    source_candidate_id: str,
    variant_ids: set[str],
) -> dict[str, Any]:
    label = f"CreativeCodeSpecificationBundle.skeptic_reviews[{index}]"
    if not isinstance(raw_review, dict):
        raise CreativeCodeSpecificationError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_review, REVIEW_KEYS, label=label)
    review = {
        "review_id": _require_id(raw_review, "review_id", label=label),
        "source_packet_id": _require_const(
            raw_review,
            "source_packet_id",
            source_packet_id,
            label=label,
        ),
        "source_candidate_id": _require_const(
            raw_review,
            "source_candidate_id",
            source_candidate_id,
            label=label,
        ),
        "variant_id": _require_id(raw_review, "variant_id", label=label),
        "reviewer_role": _require_token(raw_review, "reviewer_role", label=label),
        "decision": _require_token(raw_review, "decision", label=label),
        "blockers": _normalize_token_list(
            raw_review,
            "blockers",
            label=label,
            allow_empty=True,
        ),
        "unsafe_authority_flags": _normalize_token_list(
            raw_review,
            "unsafe_authority_flags",
            label=label,
            allow_empty=True,
        ),
        "duplicate_reason": _require_text(raw_review, "duplicate_reason", label=label),
        "required_revision": _require_text(raw_review, "required_revision", label=label),
        "review_fingerprint": _require_fingerprint(
            raw_review,
            "review_fingerprint",
            label=label,
        ),
    }
    if review["variant_id"] not in variant_ids:
        raise CreativeCodeSpecificationError(f"{label}.variant_id must reference a variant.")
    if review["reviewer_role"] not in REQUIRED_SKEPTIC_REVIEWERS:
        raise CreativeCodeSpecificationError(f"{label}.reviewer_role is not required for PR-1.")
    if review["decision"] not in REVIEW_DECISIONS:
        raise CreativeCodeSpecificationError(f"{label}.decision is not supported.")
    if review["decision"] == "pass":
        if (
            review["blockers"]
            or review["unsafe_authority_flags"]
            or review["duplicate_reason"] != "none"
            or review["required_revision"] != "none"
        ):
            raise CreativeCodeSpecificationError(f"{label} pass reviews must be clean.")
    if review["decision"] == "reject" and not review["blockers"]:
        raise CreativeCodeSpecificationError(f"{label} reject reviews require blockers.")
    if review["decision"] == "revise" and review["required_revision"] == "none":
        raise CreativeCodeSpecificationError(f"{label} revise reviews require revision notes.")
    expected_fingerprint = fingerprint_payload(_review_fingerprint_payload(review))
    if review["review_fingerprint"] != expected_fingerprint:
        raise CreativeCodeSpecificationError(
            f"{label}.review_fingerprint does not match review content."
        )
    return review


def _reviews_by_variant(reviews: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for review in reviews:
        grouped.setdefault(str(review["variant_id"]), []).append(review)
    return grouped


def _validate_complete_review_coverage(
    *,
    variants: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
) -> None:
    required = set(REQUIRED_SKEPTIC_REVIEWERS)
    review_keys: set[tuple[str, str]] = set()
    for review in reviews:
        key = (str(review["variant_id"]), str(review["reviewer_role"]))
        if key in review_keys:
            raise CreativeCodeSpecificationError(
                "skeptic_reviews must not repeat a reviewer for a variant."
            )
        review_keys.add(key)
    for variant in variants:
        variant_id = str(variant["variant_id"])
        roles = {role for review_variant, role in review_keys if review_variant == variant_id}
        if roles != required:
            raise CreativeCodeSpecificationError(
                "Every variant requires complete skeptic review coverage."
            )


def _is_variant_selectable(
    variant: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
) -> bool:
    variant_reviews = [
        review for review in reviews if review["variant_id"] == variant["variant_id"]
    ]
    return all(review["decision"] == "pass" for review in variant_reviews)


def _rejection_records(
    *,
    variants: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped = _reviews_by_variant(reviews)
    records: list[dict[str, Any]] = []
    for variant in variants:
        variant_reviews = grouped.get(str(variant["variant_id"]), [])
        reason_codes: set[str] = set()
        reviewer_roles: set[str] = set()
        for review in variant_reviews:
            if review["decision"] != "pass":
                reason_codes.add(f"review_{review['decision']}")
                reviewer_roles.add(str(review["reviewer_role"]))
            reason_codes.update(str(reason) for reason in review["blockers"])
            reason_codes.update(str(reason) for reason in review["unsafe_authority_flags"])
            if review["duplicate_reason"] != "none":
                reason_codes.add(str(review["duplicate_reason"]))
        if reason_codes:
            records.append(
                {
                    "variant_id": variant["variant_id"],
                    "variant_fingerprint": variant["variant_fingerprint"],
                    "reason_codes": sorted(reason_codes),
                    "reviewer_roles": sorted(reviewer_roles),
                }
            )
    return records


def _build_synthesis(
    *,
    variants: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    fallback: str,
) -> dict[str, Any]:
    selectable = [variant for variant in variants if _is_variant_selectable(variant, reviews)]
    rejected = _rejection_records(variants=variants, reviews=reviews)
    rejected_fingerprints = sorted(record["variant_fingerprint"] for record in rejected)
    unresolved_blockers = sorted(
        {
            reason
            for record in rejected
            for reason in record["reason_codes"]
            if reason != "review_revise"
        }
    )
    if selectable:
        selected = sorted(
            selectable,
            key=lambda variant: (
                -len([r for r in reviews if r["variant_id"] == variant["variant_id"]]),
                str(variant["variant_fingerprint"]),
                str(variant["variant_id"]),
            ),
        )[0]
        selected_variant_id: str | None = str(selected["variant_id"])
        selected_variant_fingerprint: str | None = str(selected["variant_fingerprint"])
        selection_reason = "Selected the lowest-fingerprint fully passed specification."
    else:
        selected_variant_id = None
        selected_variant_fingerprint = None
        selection_reason = "No specification selected because skeptic review blocked every variant."
    synthesis: dict[str, Any] = {
        "selected_variant_id": selected_variant_id,
        "selected_variant_fingerprint": selected_variant_fingerprint,
        "selection_reason": selection_reason,
        "ranking_policy": RANKING_POLICY,
        "rejected_variant_fingerprints": rejected_fingerprints,
        "unresolved_blockers": unresolved_blockers,
        "fallback": fallback,
        "next_authority": "human_review_required",
        "synthesis_fingerprint": "pending",
    }
    synthesis["synthesis_fingerprint"] = fingerprint_payload(
        _synthesis_fingerprint_payload(synthesis)
    )
    return synthesis


def _normalize_synthesis(
    raw_synthesis: Any,
    *,
    variants: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    fallback: str,
) -> dict[str, Any]:
    label = "CreativeCodeSpecificationBundle.synthesis"
    if not isinstance(raw_synthesis, dict):
        raise CreativeCodeSpecificationError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_synthesis, SYNTHESIS_KEYS, label=label)
    selected_variant_id = raw_synthesis.get("selected_variant_id")
    if selected_variant_id is not None and not isinstance(selected_variant_id, str):
        raise CreativeCodeSpecificationError(f"{label}.selected_variant_id must be null or string.")
    if isinstance(selected_variant_id, str) and not ID_RE.fullmatch(selected_variant_id):
        raise CreativeCodeSpecificationError(f"{label}.selected_variant_id must be safe.")
    selected_variant_fingerprint = raw_synthesis.get("selected_variant_fingerprint")
    if selected_variant_fingerprint is not None and (
        not isinstance(selected_variant_fingerprint, str)
        or not SHA256_RE.fullmatch(selected_variant_fingerprint)
    ):
        raise CreativeCodeSpecificationError(
            f"{label}.selected_variant_fingerprint must be null or sha256 digest."
        )
    synthesis = {
        "selected_variant_id": selected_variant_id,
        "selected_variant_fingerprint": selected_variant_fingerprint,
        "selection_reason": _require_text(raw_synthesis, "selection_reason", label=label),
        "ranking_policy": _require_const(
            raw_synthesis,
            "ranking_policy",
            RANKING_POLICY,
            label=label,
        ),
        "rejected_variant_fingerprints": _normalize_fingerprint_list(
            raw_synthesis,
            "rejected_variant_fingerprints",
            label=label,
            allow_empty=True,
        ),
        "unresolved_blockers": _normalize_token_list(
            raw_synthesis,
            "unresolved_blockers",
            label=label,
            allow_empty=True,
        ),
        "fallback": _require_const(raw_synthesis, "fallback", fallback, label=label),
        "next_authority": _require_const(
            raw_synthesis,
            "next_authority",
            "human_review_required",
            label=label,
        ),
        "synthesis_fingerprint": _require_fingerprint(
            raw_synthesis,
            "synthesis_fingerprint",
            label=label,
        ),
    }
    expected_synthesis = _build_synthesis(variants=variants, reviews=reviews, fallback=fallback)
    if synthesis != expected_synthesis:
        raise CreativeCodeSpecificationError(
            "synthesis does not match deterministic PR-1 synthesis."
        )
    return synthesis


def _normalize_fingerprint_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodeSpecificationError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodeSpecificationError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not SHA256_RE.fullmatch(item):
            raise CreativeCodeSpecificationError(f"{label}.{key}[{index}] must be a sha256 digest.")
        if item in seen:
            raise CreativeCodeSpecificationError(f"{label}.{key} must not contain duplicates.")
        seen.add(item)
        normalized.append(item)
    return normalized


def _normalize_telemetry(
    raw_telemetry: Any,
    *,
    source_packet_id: str,
    source_candidate_id: str,
    variant_count: int,
    generation_status: str,
    oracle_status: str,
    failure_class: str | None,
    human_decision: str,
    cost_metadata_available: bool,
) -> dict[str, Any]:
    if not isinstance(raw_telemetry, dict):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.telemetry_summary must be a JSON object."
        )
    _require_exact_keys(
        raw_telemetry,
        TELEMETRY_KEYS,
        label="CreativeCodeSpecificationBundle.telemetry_summary",
    )
    telemetry = {
        "packet_id": _require_const(
            raw_telemetry,
            "packet_id",
            source_packet_id,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "source_candidate_id": _require_const(
            raw_telemetry,
            "source_candidate_id",
            source_candidate_id,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "variant_count": _require_const(
            raw_telemetry,
            "variant_count",
            variant_count,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "generation_status": _require_const(
            raw_telemetry,
            "generation_status",
            generation_status,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "oracle_status": _require_const(
            raw_telemetry,
            "oracle_status",
            oracle_status,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "failure_class": _require_const(
            raw_telemetry,
            "failure_class",
            failure_class,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "human_decision": _require_const(
            raw_telemetry,
            "human_decision",
            human_decision,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
        "cost_metadata_available": _require_const(
            raw_telemetry,
            "cost_metadata_available",
            cost_metadata_available,
            label="CreativeCodeSpecificationBundle.telemetry_summary",
        ),
    }
    return telemetry


def _bundle_identity_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {key: bundle[key] for key in sorted(TOP_LEVEL_KEYS - {"bundle_id", "idempotency_key"})}


def _build_bundle_identity(bundle: Mapping[str, Any]) -> tuple[str, str]:
    fingerprint = fingerprint_payload(_bundle_identity_payload(bundle))
    upstream_ids = (
        str(bundle["source_packet_id"]),
        str(bundle["source_packet_fingerprint"]),
    )
    bundle_id = build_asset_id(
        asset_type="creative_code_specification_bundle",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type="creative_code_specification_bundle",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return bundle_id, idempotency_key


def _source_packet_fingerprint(packet: Mapping[str, Any]) -> str:
    fingerprint = fingerprint_payload(packet)
    if not isinstance(fingerprint, str):
        raise CreativeCodeSpecificationError("source packet fingerprint must be a string.")
    return fingerprint


def _validate_variant_collection(
    raw_variants: Any,
    *,
    source_packet_id: str,
    source_candidate_id: str,
    target_surface: Sequence[str],
    expected_count: int,
) -> list[dict[str, Any]]:
    if not isinstance(raw_variants, list):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.variants must be an array."
        )
    if len(raw_variants) != expected_count:
        raise CreativeCodeSpecificationError("variants must match source variant_count.")
    variants = [
        _validate_variant(
            variant,
            index=index,
            source_packet_id=source_packet_id,
            source_candidate_id=source_candidate_id,
            target_surface=target_surface,
        )
        for index, variant in enumerate(raw_variants)
    ]
    variant_ids = [variant["variant_id"] for variant in variants]
    approach_families = [variant["approach_family"] for variant in variants]
    fingerprints = [variant["variant_fingerprint"] for variant in variants]
    if len(set(variant_ids)) != len(variant_ids):
        raise CreativeCodeSpecificationError("variants must not repeat variant_id.")
    if len(set(approach_families)) != len(approach_families):
        raise CreativeCodeSpecificationError("variants must not repeat approach_family.")
    if len(set(fingerprints)) != len(fingerprints):
        raise CreativeCodeSpecificationError("variants must not repeat variant_fingerprint.")
    return variants


def _validate_review_collection(
    raw_reviews: Any,
    *,
    source_packet_id: str,
    source_candidate_id: str,
    variants: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(raw_reviews, list):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.skeptic_reviews must be an array."
        )
    variant_ids = {str(variant["variant_id"]) for variant in variants}
    reviews = [
        _validate_review(
            review,
            index=index,
            source_packet_id=source_packet_id,
            source_candidate_id=source_candidate_id,
            variant_ids=variant_ids,
        )
        for index, review in enumerate(raw_reviews)
    ]
    review_ids = [review["review_id"] for review in reviews]
    review_fingerprints = [review["review_fingerprint"] for review in reviews]
    if len(set(review_ids)) != len(review_ids):
        raise CreativeCodeSpecificationError("skeptic_reviews must not repeat review_id.")
    if len(set(review_fingerprints)) != len(review_fingerprints):
        raise CreativeCodeSpecificationError("skeptic_reviews must not repeat review_fingerprint.")
    _validate_complete_review_coverage(variants=variants, reviews=reviews)
    return reviews


def _bundle_status_fields(
    *,
    variants: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
) -> tuple[str, str, str | None, str, bool]:
    selectable = [variant for variant in variants if _is_variant_selectable(variant, reviews)]
    if selectable:
        return ("specifications_generated", "skeptic_review_passed", None, "pending", False)
    return ("all_rejected", "skeptic_review_blocked", "review_blocker", "review_required", False)


def build_default_specification_variants(
    source_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build deterministic specification drafts from a validated PR-0 packet."""

    normalized_packet = validate_source_candidate_packet(source_packet)
    variant_count = int(normalized_packet["variant_count"])
    source_packet_id = str(normalized_packet["candidate_id"])
    source_candidate_id = str(normalized_packet["source_creative_research"]["candidate_id"])
    target_paths = list(normalized_packet["target_surface"])
    evidence_bundle = normalized_packet["evidence_bundle"]
    tests_to_add = list(evidence_bundle["required_tests"])
    negative_controls = list(evidence_bundle["negative_controls"])
    variants: list[dict[str, Any]] = []
    for index, approach_family in enumerate(APPROACH_FAMILIES[:variant_count], start=1):
        variant: dict[str, Any] = {
            "variant_id": f"{source_packet_id}:spec-{index}",
            "source_packet_id": source_packet_id,
            "source_candidate_id": source_candidate_id,
            "variant_fingerprint": "pending",
            "approach_family": approach_family,
            "problem_statement": (
                "Convert the promoted creative research into a bounded implementation "
                f"specification for {', '.join(target_paths)} without patch authority."
            ),
            "implementation_steps": [
                f"Describe the {approach_family} implementation inside target_paths only.",
                "Preserve PR-0 authority flags and require human review before patch work.",
                "Define deterministic acceptance criteria and rollback notes.",
            ],
            "target_paths": list(target_paths),
            "tests_to_add": list(tests_to_add),
            "negative_controls": list(negative_controls),
            "rollback_plan": "Discard the specification bundle; do not mutate repository files.",
            "falsifier": "Reject if target paths, authority flags, or oracle boundaries drift.",
            "risk_notes": [
                "Specification-only artifact; no provider, runtime, repo-write, or PR authority."
            ],
            "wellness_boundary": "Wellness planning only with no health outcome promise.",
            "estimated_changed_files": max(1, min(len(target_paths), 5)),
        }
        variant["variant_fingerprint"] = fingerprint_payload(_variant_fingerprint_payload(variant))
        variants.append(variant)
    return variants


def build_pending_skeptic_reviews(
    *,
    source_packet: Mapping[str, Any],
    variants: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build deterministic default skeptic-review records that block selection."""

    normalized_packet = validate_source_candidate_packet(source_packet)
    source_packet_id = str(normalized_packet["candidate_id"])
    source_candidate_id = str(normalized_packet["source_creative_research"]["candidate_id"])
    reviews: list[dict[str, Any]] = []
    for variant in variants:
        for reviewer in REQUIRED_SKEPTIC_REVIEWERS:
            review: dict[str, Any] = {
                "review_id": f"{variant['variant_id']}:{reviewer}",
                "source_packet_id": source_packet_id,
                "source_candidate_id": source_candidate_id,
                "variant_id": variant["variant_id"],
                "reviewer_role": reviewer,
                "decision": "reject",
                "blockers": ["skeptic_review_required"],
                "unsafe_authority_flags": [],
                "duplicate_reason": "none",
                "required_revision": "none",
                "review_fingerprint": "pending",
            }
            review["review_fingerprint"] = fingerprint_payload(_review_fingerprint_payload(review))
            reviews.append(review)
    return reviews


def validate_source_candidate_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate PR-0 source packet and convert contract errors to PR-1 errors."""

    try:
        return cast(dict[str, Any], validate_creative_code_candidate_packet(dict(payload)))
    except CreativeCodeContractError as exc:
        raise CreativeCodeSpecificationError(str(exc)) from exc


def build_creative_code_specification_bundle(
    *,
    source_packet: Mapping[str, Any],
    variants: Sequence[Mapping[str, Any]],
    skeptic_reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic CreativeCodeSpecificationBundle."""

    normalized_packet = validate_source_candidate_packet(source_packet)
    source_packet_id = str(normalized_packet["candidate_id"])
    source_candidate_id = str(normalized_packet["source_creative_research"]["candidate_id"])
    source_packet_fingerprint = _source_packet_fingerprint(normalized_packet)
    normalized_variants = _validate_variant_collection(
        list(variants),
        source_packet_id=source_packet_id,
        source_candidate_id=source_candidate_id,
        target_surface=normalized_packet["target_surface"],
        expected_count=int(normalized_packet["variant_count"]),
    )
    normalized_reviews = _validate_review_collection(
        list(skeptic_reviews),
        source_packet_id=source_packet_id,
        source_candidate_id=source_candidate_id,
        variants=normalized_variants,
    )
    fallback = str(normalized_packet["fallback"])
    synthesis = _build_synthesis(
        variants=normalized_variants,
        reviews=normalized_reviews,
        fallback=fallback,
    )
    generation_status, oracle_status, failure_class, human_decision, cost_available = (
        _bundle_status_fields(variants=normalized_variants, reviews=normalized_reviews)
    )
    rejection_index = build_creative_code_rejection_index(
        source_packet_id=source_packet_id,
        source_packet_fingerprint=source_packet_fingerprint,
        records=_rejection_records(variants=normalized_variants, reviews=normalized_reviews),
    )
    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "bundle_type": BUNDLE_TYPE,
        "bundle_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "source_packet_id": source_packet_id,
        "source_packet_idempotency_key": normalized_packet["idempotency_key"],
        "source_packet_fingerprint": source_packet_fingerprint,
        "source_candidate_id": source_candidate_id,
        "source_creative_research": normalized_packet["source_creative_research"],
        "target_surface": normalized_packet["target_surface"],
        "immutable_oracles": normalized_packet["immutable_oracles"],
        "fallback": fallback,
        "authority": normalized_packet["authority"],
        "variants": normalized_variants,
        "skeptic_reviews": normalized_reviews,
        "synthesis": synthesis,
        "rejection_index": rejection_index,
        "generation_status": generation_status,
        "oracle_status": oracle_status,
        "failure_class": failure_class,
        "human_decision": human_decision,
        "cost_metadata_available": cost_available,
        "telemetry_summary": {
            "packet_id": source_packet_id,
            "source_candidate_id": source_candidate_id,
            "variant_count": len(normalized_variants),
            "generation_status": generation_status,
            "oracle_status": oracle_status,
            "failure_class": failure_class,
            "human_decision": human_decision,
            "cost_metadata_available": cost_available,
        },
    }
    bundle_id, idempotency_key = _build_bundle_identity(bundle)
    bundle["bundle_id"] = bundle_id
    bundle["idempotency_key"] = idempotency_key
    return bundle


def validate_creative_code_specification_bundle(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a PR-1 creative-code specification bundle."""

    _require_exact_keys(payload, TOP_LEVEL_KEYS, label="CreativeCodeSpecificationBundle")
    normalized: dict[str, Any] = {
        "schema_version": _require_const(
            payload,
            "schema_version",
            SCHEMA_VERSION,
            label="CreativeCodeSpecificationBundle",
        ),
        "bundle_type": _require_const(
            payload,
            "bundle_type",
            BUNDLE_TYPE,
            label="CreativeCodeSpecificationBundle",
        ),
        "bundle_id": _require_id(payload, "bundle_id", label="CreativeCodeSpecificationBundle"),
        "idempotency_key": _require_id(
            payload,
            "idempotency_key",
            label="CreativeCodeSpecificationBundle",
        ),
        "policy_version": _require_const(
            payload,
            "policy_version",
            POLICY_VERSION,
            label="CreativeCodeSpecificationBundle",
        ),
        "source_packet_id": _require_id(
            payload,
            "source_packet_id",
            label="CreativeCodeSpecificationBundle",
        ),
        "source_packet_idempotency_key": _require_id(
            payload,
            "source_packet_idempotency_key",
            label="CreativeCodeSpecificationBundle",
        ),
        "source_packet_fingerprint": _require_fingerprint(
            payload,
            "source_packet_fingerprint",
            label="CreativeCodeSpecificationBundle",
        ),
        "source_candidate_id": _require_id(
            payload,
            "source_candidate_id",
            label="CreativeCodeSpecificationBundle",
        ),
    }
    normalized["source_creative_research"] = _validate_source_research(
        payload["source_creative_research"]
    )
    if normalized["source_candidate_id"] != normalized["source_creative_research"]["candidate_id"]:
        raise CreativeCodeSpecificationError("source_candidate_id must match source research.")
    normalized["target_surface"] = validate_mutable_candidate_surface(
        _normalize_path_list(
            payload,
            "target_surface",
            label="CreativeCodeSpecificationBundle",
        )
    )
    normalized["immutable_oracles"] = _normalize_path_list(
        payload,
        "immutable_oracles",
        label="CreativeCodeSpecificationBundle",
    )
    _reject_immutable_oracle_overlap(
        target_surface=normalized["target_surface"],
        immutable_oracles=normalized["immutable_oracles"],
    )
    normalized["fallback"] = _require_text(
        payload,
        "fallback",
        label="CreativeCodeSpecificationBundle",
    )
    normalized["authority"] = _validate_authority(payload["authority"])
    expected_count = _extract_expected_variant_count(payload["telemetry_summary"])
    normalized["variants"] = _validate_variant_collection(
        payload["variants"],
        source_packet_id=normalized["source_packet_id"],
        source_candidate_id=normalized["source_candidate_id"],
        target_surface=normalized["target_surface"],
        expected_count=expected_count,
    )
    normalized["skeptic_reviews"] = _validate_review_collection(
        payload["skeptic_reviews"],
        source_packet_id=normalized["source_packet_id"],
        source_candidate_id=normalized["source_candidate_id"],
        variants=normalized["variants"],
    )
    expected_generation, expected_oracle, expected_failure, expected_human, expected_cost = (
        _bundle_status_fields(
            variants=normalized["variants"],
            reviews=normalized["skeptic_reviews"],
        )
    )
    normalized["generation_status"] = _validate_enum_field(
        payload,
        "generation_status",
        GENERATION_STATUSES,
        expected=expected_generation,
    )
    normalized["oracle_status"] = _validate_enum_field(
        payload,
        "oracle_status",
        ORACLE_STATUSES,
        expected=expected_oracle,
    )
    normalized["failure_class"] = _validate_optional_enum_field(
        payload,
        "failure_class",
        FAILURE_CLASSES,
        expected=expected_failure,
    )
    normalized["human_decision"] = _validate_enum_field(
        payload,
        "human_decision",
        HUMAN_DECISIONS,
        expected=expected_human,
    )
    if payload.get("cost_metadata_available") is not expected_cost:
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.cost_metadata_available has invalid state."
        )
    normalized["cost_metadata_available"] = expected_cost
    normalized["synthesis"] = _normalize_synthesis(
        payload["synthesis"],
        variants=normalized["variants"],
        reviews=normalized["skeptic_reviews"],
        fallback=normalized["fallback"],
    )
    normalized["rejection_index"] = validate_creative_code_rejection_index(
        payload["rejection_index"]
    )
    expected_rejection_index = build_creative_code_rejection_index(
        source_packet_id=normalized["source_packet_id"],
        source_packet_fingerprint=normalized["source_packet_fingerprint"],
        records=_rejection_records(
            variants=normalized["variants"],
            reviews=normalized["skeptic_reviews"],
        ),
    )
    if normalized["rejection_index"] != expected_rejection_index:
        raise CreativeCodeSpecificationError("rejection_index does not match skeptic reviews.")
    normalized["telemetry_summary"] = _normalize_telemetry(
        payload["telemetry_summary"],
        source_packet_id=normalized["source_packet_id"],
        source_candidate_id=normalized["source_candidate_id"],
        variant_count=len(normalized["variants"]),
        generation_status=normalized["generation_status"],
        oracle_status=normalized["oracle_status"],
        failure_class=normalized["failure_class"],
        human_decision=normalized["human_decision"],
        cost_metadata_available=normalized["cost_metadata_available"],
    )
    expected_bundle_id, expected_idempotency_key = _build_bundle_identity(normalized)
    if normalized["bundle_id"] != expected_bundle_id:
        raise CreativeCodeSpecificationError("bundle_id does not match bundle content.")
    if normalized["idempotency_key"] != expected_idempotency_key:
        raise CreativeCodeSpecificationError("idempotency_key does not match bundle content.")
    return normalized


def _extract_expected_variant_count(raw_telemetry: Any) -> int:
    if not isinstance(raw_telemetry, dict):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.telemetry_summary must be a JSON object."
        )
    value = raw_telemetry.get("variant_count")
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.telemetry_summary.variant_count must be an integer."
        )
    if not 3 <= value <= 5:
        raise CreativeCodeSpecificationError(
            "CreativeCodeSpecificationBundle.telemetry_summary.variant_count must be between 3 and 5."
        )
    return value


def _validate_enum_field(
    payload: Mapping[str, Any],
    key: str,
    allowed: frozenset[str],
    *,
    expected: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value not in allowed:
        raise CreativeCodeSpecificationError(
            f"CreativeCodeSpecificationBundle.{key} has invalid state."
        )
    if value != expected:
        raise CreativeCodeSpecificationError(
            f"CreativeCodeSpecificationBundle.{key} does not match synthesis state."
        )
    return value


def _validate_optional_enum_field(
    payload: Mapping[str, Any],
    key: str,
    allowed: frozenset[str | None],
    *,
    expected: str | None,
) -> str | None:
    value = payload.get(key)
    if value not in allowed:
        raise CreativeCodeSpecificationError(
            f"CreativeCodeSpecificationBundle.{key} has invalid state."
        )
    if value != expected:
        raise CreativeCodeSpecificationError(
            f"CreativeCodeSpecificationBundle.{key} does not match synthesis state."
        )
    return value


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        payload = read_creative_code_specification_bundle(args.validate)
        validate_creative_code_specification_bundle(payload)
    except CreativeCodeSpecificationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
