"""Contracts for the local creative-code private-pilot loop operator.

The operator reads sanitized PR/check/review state and emits local lifecycle
artifacts only. It does not generate candidates, mutate GitHub, edit fixed
mapping, resolve threads, call providers, or claim readiness.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
import re
import argparse
import sys
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.github_app_private_pilot_capability import (
    GithubAppPrivatePilotCapabilityError,
    default_github_app_capability_state,
    normalize_github_app_capability_state,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-code-private-pilot-loop-operator"
STATE_ARTIFACT_TYPE = "creative_code_private_pilot_state"
CANDIDATE_PLAN_ARTIFACT_TYPE = "creative_code_private_pilot_candidate_plan"
DEFAULT_TARGET_SURFACE = "docs/prompts/cv/program.md"

DECISIONS = frozenset(
    {
        "wait_for_hotfix_main",
        "wait_for_review",
        "wait_for_ci",
        "fix_current_pr",
        "prepare_next_candidate_plan",
        "hold_for_governance",
        "hold_for_security",
    }
)
CHECK_STATES = frozenset({"passed", "pending", "failed", "cancelled", "stale", "neutral"})
CHECK_OVERALL_STATES = frozenset({"success", "pending", "failing", "missing", "unknown"})
REVIEW_SOURCE_STATUSES = frozenset(
    {
        "available",
        "degraded",
        "unavailable",
        "rate_limited",
        "usage_limit_reached",
        "auth_missing",
        "partial",
        "fallback_finding",
        "failed_required_check",
        "unresolved_threads",
        "actionable_bot_comments",
    }
)
REVIEW_FRICTION = frozenset({"none", "low", "medium", "high", "blocked"})
ARTIFACT_REF_TYPES = frozenset(
    {
        "creative_code_telemetry_rollup",
        "creative_code_telemetry_event",
        "creative_code_review_disposition_packet",
        "creative_code_repair_launch_packet",
        "creative_code_applied_candidate_run_plan",
        "creative_code_private_pilot_state",
    }
)
ALLOWED_ARTIFACT_REF_PREFIXES = (
    "artifacts/orchestration/creative_code/telemetry/",
    "artifacts/orchestration/creative_code/review_disposition/",
    "artifacts/orchestration/creative_code/applied_candidates/",
    "artifacts/orchestration/creative_code/private_pilot/",
)

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SAFE_GIT_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/\S+$")
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|candidate_patch|"
    r"raw[_ -]?(body|prompt|response|context|patch|review|pr)|"
    r"review[_ -]?thread[_ -]?body|pull[_ -]?request[_ -]?body|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|"
    r"oracle[_ -]?(stdout|stderr|output)|file://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|merge[-_ ]?ready|ready to merge|mergeable)",
    re.IGNORECASE | re.MULTILINE,
)
UNSAFE_KEY_RE = re.compile(
    r"(?i)(^raw|raw_|_raw|body$|_body$|body_text|body_html|patch_text|raw_patch|"
    r"prompt_text|raw_prompt|provider_payload|oracle_stdout|oracle_stderr|"
    r"secret_value|token_value|access_token|api_key)"
)
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

STATE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "state_id",
        "idempotency_key",
        "generated_at_utc",
        "source_pr",
        "current_head_checks",
        "review_capacity",
        "blockers",
        "governance_refs",
        "github_app_capability",
        "external_dependencies",
        "decision",
        "authority",
        "sanitized",
    }
)
SOURCE_PR_KEYS = frozenset(
    {
        "repository",
        "pr_number",
        "url",
        "state",
        "draft",
        "base_ref",
        "base_sha",
        "head_sha",
    }
)
CHECKS_KEYS = frozenset(
    {
        "pr_head_sha",
        "overall",
        "required_metadata_available",
        "current",
        "stale_diagnostics",
        "summary",
        "degraded_reasons",
    }
)
CHECK_ENTRY_KEYS = frozenset(
    {
        "name",
        "workflow",
        "state",
        "conclusion",
        "head_sha",
        "required",
        "details_url",
        "observed_at_utc",
    }
)
STALE_KEYS = frozenset(
    {
        "total",
        "failed",
        "cancelled",
        "superseded",
        "wrong_head_sha",
        "missing_head_sha",
    }
)
CHECK_SUMMARY_KEYS = frozenset(
    {
        "current_total",
        "current_success",
        "current_pending",
        "current_failing",
        "required_total",
        "required_pending",
        "required_failing",
        "required_missing",
    }
)
REVIEW_CAPACITY_KEYS = frozenset({"friction", "sources"})
REVIEW_SOURCE_KEYS = frozenset({"source", "status", "source_degraded", "blocking"})
BLOCKERS_KEYS = frozenset(
    {
        "actionable_review_count",
        "security_blocker_count",
        "governance_blocker_count",
        "fixed_mapping_required",
        "fixed_mapping_present",
    }
)
GOVERNANCE_KEYS = frozenset(
    {
        "target_surface",
        "fixed_mapping",
        "pr4_telemetry_refs",
        "pr5_disposition_refs",
        "pr6_run_plan_refs",
    }
)
FIXED_MAPPING_KEYS = frozenset({"required", "present", "repo_path", "entry_count", "no_actionable"})
ARTIFACT_REF_KEYS = frozenset({"artifact_type", "repo_path", "exists", "fingerprint"})
EXTERNAL_DEPENDENCY_KEYS = frozenset({"hotfix_main_required", "hotfix_main_merged", "reference"})
AUTHORITY_TRUE_KEYS = frozenset(
    {"read_github_metadata", "read_sanitized_artifacts", "emit_pilot_state", "emit_candidate_plan"}
)
AUTHORITY_FALSE_KEYS = frozenset(
    {
        "create_branch",
        "write_branch",
        "push",
        "open_pr",
        "open_draft_pr",
        "mark_pr_ready",
        "post_github_comment",
        "resolve_threads",
        "edit_fixed_mapping",
        "generate_candidate",
        "execute_pr1_specification",
        "execute_pr2_patch_builder",
        "execute_pr3_promotion",
        "merge",
        "release",
        "claim_merge_readiness",
        "call_provider",
        "call_product_runtime",
        "read_secrets",
        "modify_github_app",
        "modify_slack",
        "modify_workflows",
        "use_semantic_cache",
        "change_openapi",
        "change_client_runtime",
    }
)
AUTHORITY_KEYS = AUTHORITY_TRUE_KEYS | AUTHORITY_FALSE_KEYS
CANDIDATE_PLAN_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "plan_id",
        "idempotency_key",
        "source_state_id",
        "source_state_fingerprint",
        "decision",
        "target_surface",
        "checklist",
        "blocked_authority",
        "authority",
        "sanitized",
    }
)
CHECKLIST_ITEM_KEYS = frozenset(
    {
        "label",
        "description",
        "checklist_only",
        "executes_in_operator",
        "requires_human_gate",
    }
)


class CreativeCodePrivatePilotContractError(ValueError):
    """Raised when private-pilot loop artifacts violate the local contract."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodePrivatePilotContractError(
                f"private-pilot JSON has duplicate key: {key}"
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
    except CreativeCodePrivatePilotContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodePrivatePilotContractError(
            "Unable to read creative-code private-pilot JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodePrivatePilotContractError(
            "Creative-code private-pilot artifact must be a JSON object."
        )
    return payload


def reject_unsafe_private_pilot_value(value: Any, *, label: str) -> None:
    """Reject strings that could persist raw bodies, patches, secrets, or local paths."""

    if isinstance(value, str):
        if SECRET_RE.search(value):
            raise CreativeCodePrivatePilotContractError(
                f"{label} contains unsafe private-pilot text."
            )
        if GITHUB_URL_RE.fullmatch(value):
            return
        if LEAK_TEXT_RE.search(value):
            raise CreativeCodePrivatePilotContractError(
                f"{label} contains unsafe private-pilot text."
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_unsafe_private_pilot_value(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if UNSAFE_KEY_RE.search(key):
                raise CreativeCodePrivatePilotContractError(
                    f"{label}.{key} is an unsupported raw/private field."
                )
            reject_unsafe_private_pilot_value(item, label=f"{label}.{key}")


def default_private_pilot_authority() -> dict[str, bool]:
    """Return the only authority this local operator may claim."""

    authority = {key: False for key in sorted(AUTHORITY_FALSE_KEYS)}
    authority.update({key: True for key in sorted(AUTHORITY_TRUE_KEYS)})
    return dict(sorted(authority.items()))


def _require_exact_keys(
    payload: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise CreativeCodePrivatePilotContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodePrivatePilotContractError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_bool(
    payload: Mapping[str, Any], key: str, *, expected: bool | None, label: str
) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a boolean.")
    if expected is not None and value is not expected:
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be {expected}.")
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
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodePrivatePilotContractError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a safe identifier.")
    reject_unsafe_private_pilot_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a safe token.")
    reject_unsafe_private_pilot_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_git_ref(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if (
        not normalized
        or not SAFE_GIT_REF_RE.fullmatch(normalized)
        or normalized.startswith(("/", "."))
        or normalized.endswith(("/", ".lock"))
        or ".." in normalized
        or "//" in normalized
        or "@{" in normalized
        or "\\" in normalized
    ):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a safe git ref.")
    reject_unsafe_private_pilot_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_safe_text(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    max_chars: int = 160,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a string.")
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) > max_chars:
        raise CreativeCodePrivatePilotContractError(
            f"{label}.{key} must be at most {max_chars} characters."
        )
    reject_unsafe_private_pilot_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_sha(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label}.{key} must be a 40-char SHA.")
    return value


def _require_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a sha256 digest.")
    return value


def _require_optional_sha(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must be null or a 40-char SHA.")
    return value


def _require_optional_url(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not GITHUB_URL_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must be null or a GitHub web URL.")
    reject_unsafe_private_pilot_value(value, label=label)
    return value


def _safe_github_url_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or not GITHUB_URL_RE.fullmatch(normalized):
        return None
    reject_unsafe_private_pilot_value(normalized, label="details_url")
    return normalized


def _require_optional_timestamp(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must be null or UTC timestamp.")
    return value


def _require_timestamp(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a UTC timestamp.")
    return value


def _require_repository(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must be an owner/repo slug.")
    reject_unsafe_private_pilot_value(value, label=label)
    return value


def _normalize_repo_relative_path(raw_path: Any, *, label: str, artifact_ref: bool = False) -> str:
    if not isinstance(raw_path, str):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeCodePrivatePilotContractError(f"{label} must not be empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeCodePrivatePilotContractError(f"{label} must not contain control chars.")
    if "\\" in value:
        raise CreativeCodePrivatePilotContractError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or Path(value).is_absolute():
        raise CreativeCodePrivatePilotContractError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeCodePrivatePilotContractError(f"{label} must not be a URL.")
    path = PurePosixPath(value)
    if "." in path.parts or ".." in path.parts:
        raise CreativeCodePrivatePilotContractError(f"{label} must not contain traversal segments.")
    normalized = path.as_posix()
    if artifact_ref:
        if not normalized.startswith(ALLOWED_ARTIFACT_REF_PREFIXES):
            raise CreativeCodePrivatePilotContractError(
                f"{label} must reference a creative-code local artifact path."
            )
    elif normalized == "artifacts" or normalized.startswith("artifacts/"):
        raise CreativeCodePrivatePilotContractError(f"{label} points to a local artifact path.")
    if normalized in {".git", ".venv", "worktrees"} or normalized.startswith(
        (".git/", ".venv/", "worktrees/")
    ):
        raise CreativeCodePrivatePilotContractError(f"{label} points to a forbidden surface.")
    reject_unsafe_private_pilot_value(normalized, label=label)
    return normalized


def _normalize_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, Mapping):
        raise CreativeCodePrivatePilotContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, AUTHORITY_KEYS, label="authority")
    normalized: dict[str, bool] = {}
    for key in sorted(AUTHORITY_KEYS):
        expected = key in AUTHORITY_TRUE_KEYS
        normalized[key] = _require_bool(raw_authority, key, expected=expected, label="authority")
    return normalized


def _normalize_source_pr(raw_source_pr: Any) -> dict[str, Any]:
    if not isinstance(raw_source_pr, Mapping):
        raise CreativeCodePrivatePilotContractError("source_pr must be a JSON object.")
    _require_exact_keys(raw_source_pr, SOURCE_PR_KEYS, label="source_pr")
    return {
        "repository": _require_repository(
            raw_source_pr["repository"], label="source_pr.repository"
        ),
        "pr_number": _require_int(
            raw_source_pr, "pr_number", min_value=1, max_value=1_000_000, label="source_pr"
        ),
        "url": _require_optional_url(raw_source_pr["url"], label="source_pr.url"),
        "state": _require_token(raw_source_pr, "state", label="source_pr"),
        "draft": _require_bool(raw_source_pr, "draft", expected=None, label="source_pr"),
        "base_ref": _require_git_ref(raw_source_pr, "base_ref", label="source_pr"),
        "base_sha": _require_optional_sha(raw_source_pr["base_sha"], label="source_pr.base_sha"),
        "head_sha": _require_sha(raw_source_pr, "head_sha", label="source_pr"),
    }


def _normalize_check_entry(raw_entry: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_entry, Mapping):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_entry, CHECK_ENTRY_KEYS, label=label)
    state = _require_token(raw_entry, "state", label=label)
    if state not in CHECK_STATES:
        raise CreativeCodePrivatePilotContractError(f"{label}.state is unsupported.")
    return {
        "name": _require_safe_text(raw_entry, "name", label=label),
        "workflow": _require_safe_text(raw_entry, "workflow", label=label),
        "state": state,
        "conclusion": _require_safe_text(raw_entry, "conclusion", label=label, max_chars=64),
        "head_sha": _require_sha(raw_entry, "head_sha", label=label),
        "required": _require_bool(raw_entry, "required", expected=None, label=label),
        "details_url": _require_optional_url(
            raw_entry["details_url"], label=f"{label}.details_url"
        ),
        "observed_at_utc": _require_optional_timestamp(
            raw_entry["observed_at_utc"], label=f"{label}.observed_at_utc"
        ),
    }


def _normalize_stale_diagnostics(raw_stale: Any) -> dict[str, int]:
    if not isinstance(raw_stale, Mapping):
        raise CreativeCodePrivatePilotContractError("stale_diagnostics must be a JSON object.")
    _require_exact_keys(raw_stale, STALE_KEYS, label="stale_diagnostics")
    return {
        key: _require_int(
            raw_stale,
            key,
            min_value=0,
            max_value=1_000_000,
            label="stale_diagnostics",
        )
        for key in sorted(STALE_KEYS)
    }


def _normalize_check_summary_counts(raw_summary: Any) -> dict[str, int]:
    if not isinstance(raw_summary, Mapping):
        raise CreativeCodePrivatePilotContractError("check summary must be a JSON object.")
    _require_exact_keys(raw_summary, CHECK_SUMMARY_KEYS, label="current_head_checks.summary")
    return {
        key: _require_int(
            raw_summary,
            key,
            min_value=0,
            max_value=1_000_000,
            label="current_head_checks.summary",
        )
        for key in sorted(CHECK_SUMMARY_KEYS)
    }


def _is_failing_check_state(state: str) -> bool:
    return state in {"failed", "cancelled", "stale"}


def _check_state_risk_rank(state: str) -> int:
    if _is_failing_check_state(state):
        return 3
    if state == "pending":
        return 2
    if state == "neutral":
        return 1
    return 0


def _check_summary_from_current(
    current: Sequence[Mapping[str, Any]],
    *,
    required_missing: int,
) -> dict[str, int]:
    required_current = [entry for entry in current if bool(entry["required"])]
    return {
        "current_total": len(current),
        "current_success": sum(1 for entry in current if entry["state"] in {"passed", "neutral"}),
        "current_pending": sum(1 for entry in current if entry["state"] == "pending"),
        "current_failing": sum(1 for entry in current if _is_failing_check_state(entry["state"])),
        "required_total": len(required_current) + required_missing,
        "required_pending": sum(1 for entry in required_current if entry["state"] == "pending"),
        "required_failing": sum(
            1 for entry in required_current if _is_failing_check_state(entry["state"])
        ),
        "required_missing": required_missing,
    }


def _overall_from_check_summary(
    *,
    summary: Mapping[str, int],
    required_metadata_available: bool,
) -> str:
    if summary["required_failing"] or (
        not required_metadata_available and summary["current_failing"]
    ):
        return "failing"
    if (
        summary["required_pending"]
        or summary["required_missing"]
        or (not required_metadata_available and summary["current_pending"])
    ):
        return "missing" if summary["required_missing"] else "pending"
    if not required_metadata_available:
        return "unknown"
    if not summary["current_total"] and not summary["required_total"]:
        return "unknown"
    return "success"


def _normalize_current_head_checks(raw_checks: Any, *, source_head_sha: str) -> dict[str, Any]:
    if not isinstance(raw_checks, Mapping):
        raise CreativeCodePrivatePilotContractError("current_head_checks must be a JSON object.")
    _require_exact_keys(raw_checks, CHECKS_KEYS, label="current_head_checks")
    pr_head_sha = _require_sha(raw_checks, "pr_head_sha", label="current_head_checks")
    if pr_head_sha != source_head_sha:
        raise CreativeCodePrivatePilotContractError("current_head_checks.pr_head_sha drift.")
    overall = _require_token(raw_checks, "overall", label="current_head_checks")
    if overall not in CHECK_OVERALL_STATES:
        raise CreativeCodePrivatePilotContractError("current_head_checks.overall is unsupported.")
    current_raw = raw_checks["current"]
    if not isinstance(current_raw, list):
        raise CreativeCodePrivatePilotContractError("current_head_checks.current must be a list.")
    current = [
        _normalize_check_entry(entry, label=f"current_head_checks.current[{index}]")
        for index, entry in enumerate(current_raw)
    ]
    for entry in current:
        if entry["head_sha"] != pr_head_sha:
            raise CreativeCodePrivatePilotContractError(
                "current check entry must match source PR head SHA."
            )
    degraded_raw = raw_checks["degraded_reasons"]
    if not isinstance(degraded_raw, list):
        raise CreativeCodePrivatePilotContractError(
            "current_head_checks.degraded_reasons must be a list."
        )
    degraded = [
        _require_safe_text({"reason": reason}, "reason", label="current_head_checks.degraded")
        for reason in degraded_raw
    ]
    required_metadata_available = _require_bool(
        raw_checks,
        "required_metadata_available",
        expected=None,
        label="current_head_checks",
    )
    summary = _normalize_check_summary_counts(raw_checks["summary"])
    expected_summary = _check_summary_from_current(
        current,
        required_missing=summary["required_missing"],
    )
    if summary != expected_summary:
        raise CreativeCodePrivatePilotContractError(
            "current_head_checks.summary does not match current checks."
        )
    expected_overall = _overall_from_check_summary(
        summary=summary,
        required_metadata_available=required_metadata_available,
    )
    if overall != expected_overall:
        raise CreativeCodePrivatePilotContractError(
            "current_head_checks.overall does not match current checks."
        )
    return {
        "pr_head_sha": pr_head_sha,
        "overall": overall,
        "required_metadata_available": required_metadata_available,
        "current": current,
        "stale_diagnostics": _normalize_stale_diagnostics(raw_checks["stale_diagnostics"]),
        "summary": summary,
        "degraded_reasons": degraded,
    }


def _normalize_review_source(raw_source: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_source, Mapping):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_source, REVIEW_SOURCE_KEYS, label=label)
    status = _require_token(raw_source, "status", label=label)
    if status not in REVIEW_SOURCE_STATUSES:
        raise CreativeCodePrivatePilotContractError(f"{label}.status is unsupported.")
    return {
        "source": _require_token(raw_source, "source", label=label),
        "status": status,
        "source_degraded": _require_bool(raw_source, "source_degraded", expected=None, label=label),
        "blocking": _require_bool(raw_source, "blocking", expected=None, label=label),
    }


def _normalize_review_capacity(raw_review: Any) -> dict[str, Any]:
    if not isinstance(raw_review, Mapping):
        raise CreativeCodePrivatePilotContractError("review_capacity must be a JSON object.")
    _require_exact_keys(raw_review, REVIEW_CAPACITY_KEYS, label="review_capacity")
    friction = _require_token(raw_review, "friction", label="review_capacity")
    if friction not in REVIEW_FRICTION:
        raise CreativeCodePrivatePilotContractError("review_capacity.friction is unsupported.")
    sources_raw = raw_review["sources"]
    if not isinstance(sources_raw, list):
        raise CreativeCodePrivatePilotContractError("review_capacity.sources must be a list.")
    return {
        "friction": friction,
        "sources": [
            _normalize_review_source(source, label=f"review_capacity.sources[{index}]")
            for index, source in enumerate(sources_raw)
        ],
    }


def _normalize_blockers(raw_blockers: Any) -> dict[str, Any]:
    if not isinstance(raw_blockers, Mapping):
        raise CreativeCodePrivatePilotContractError("blockers must be a JSON object.")
    _require_exact_keys(raw_blockers, BLOCKERS_KEYS, label="blockers")
    return {
        "actionable_review_count": _require_int(
            raw_blockers,
            "actionable_review_count",
            min_value=0,
            max_value=100_000,
            label="blockers",
        ),
        "security_blocker_count": _require_int(
            raw_blockers, "security_blocker_count", min_value=0, max_value=100_000, label="blockers"
        ),
        "governance_blocker_count": _require_int(
            raw_blockers,
            "governance_blocker_count",
            min_value=0,
            max_value=100_000,
            label="blockers",
        ),
        "fixed_mapping_required": _require_bool(
            raw_blockers, "fixed_mapping_required", expected=None, label="blockers"
        ),
        "fixed_mapping_present": _require_bool(
            raw_blockers, "fixed_mapping_present", expected=None, label="blockers"
        ),
    }


def _normalize_fixed_mapping(raw_mapping: Any) -> dict[str, Any]:
    if not isinstance(raw_mapping, Mapping):
        raise CreativeCodePrivatePilotContractError("fixed_mapping must be a JSON object.")
    _require_exact_keys(raw_mapping, FIXED_MAPPING_KEYS, label="fixed_mapping")
    return {
        "required": _require_bool(raw_mapping, "required", expected=None, label="fixed_mapping"),
        "present": _require_bool(raw_mapping, "present", expected=None, label="fixed_mapping"),
        "repo_path": _normalize_repo_relative_path(
            raw_mapping["repo_path"], label="fixed_mapping.repo_path"
        ),
        "entry_count": _require_int(
            raw_mapping, "entry_count", min_value=0, max_value=100_000, label="fixed_mapping"
        ),
        "no_actionable": _require_bool(
            raw_mapping, "no_actionable", expected=None, label="fixed_mapping"
        ),
    }


def _normalize_artifact_ref(raw_ref: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_ref, Mapping):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_ref, ARTIFACT_REF_KEYS, label=label)
    artifact_type = _require_token(raw_ref, "artifact_type", label=label)
    if artifact_type not in ARTIFACT_REF_TYPES:
        raise CreativeCodePrivatePilotContractError(f"{label}.artifact_type is unsupported.")
    fingerprint = raw_ref["fingerprint"]
    return {
        "artifact_type": artifact_type,
        "repo_path": _normalize_repo_relative_path(
            raw_ref["repo_path"], label=f"{label}.repo_path", artifact_ref=True
        ),
        "exists": _require_bool(raw_ref, "exists", expected=None, label=label),
        "fingerprint": (
            None
            if fingerprint is None
            else _require_sha256(fingerprint, label=f"{label}.fingerprint")
        ),
    }


def _normalize_ref_list(raw_refs: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_refs, list):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a list.")
    return [
        _normalize_artifact_ref(ref, label=f"{label}[{index}]")
        for index, ref in enumerate(raw_refs)
    ]


def _normalize_governance_refs(raw_refs: Any) -> dict[str, Any]:
    if not isinstance(raw_refs, Mapping):
        raise CreativeCodePrivatePilotContractError("governance_refs must be a JSON object.")
    _require_exact_keys(raw_refs, GOVERNANCE_KEYS, label="governance_refs")
    target_surface = raw_refs["target_surface"]
    if target_surface != [DEFAULT_TARGET_SURFACE]:
        raise CreativeCodePrivatePilotContractError(
            f"governance_refs.target_surface must be exactly [{DEFAULT_TARGET_SURFACE!r}]."
        )
    return {
        "target_surface": [DEFAULT_TARGET_SURFACE],
        "fixed_mapping": _normalize_fixed_mapping(raw_refs["fixed_mapping"]),
        "pr4_telemetry_refs": _normalize_ref_list(
            raw_refs["pr4_telemetry_refs"], label="governance_refs.pr4_telemetry_refs"
        ),
        "pr5_disposition_refs": _normalize_ref_list(
            raw_refs["pr5_disposition_refs"], label="governance_refs.pr5_disposition_refs"
        ),
        "pr6_run_plan_refs": _normalize_ref_list(
            raw_refs["pr6_run_plan_refs"], label="governance_refs.pr6_run_plan_refs"
        ),
    }


def _validate_fixed_mapping_consistency(normalized: Mapping[str, Any]) -> None:
    blockers = normalized["blockers"]
    fixed_mapping = normalized["governance_refs"]["fixed_mapping"]
    if blockers["fixed_mapping_required"] != fixed_mapping["required"]:
        raise CreativeCodePrivatePilotContractError(
            "blockers.fixed_mapping_required must match governance_refs.fixed_mapping.required."
        )
    if blockers["fixed_mapping_present"] != fixed_mapping["present"]:
        raise CreativeCodePrivatePilotContractError(
            "blockers.fixed_mapping_present must match governance_refs.fixed_mapping.present."
        )
    if fixed_mapping["present"] and not (
        fixed_mapping["entry_count"] > 0 or fixed_mapping["no_actionable"]
    ):
        raise CreativeCodePrivatePilotContractError(
            "governance_refs.fixed_mapping present requires mapping entries or no-actionable proof."
        )


def _normalize_external_dependencies(raw_deps: Any) -> dict[str, Any]:
    if not isinstance(raw_deps, Mapping):
        raise CreativeCodePrivatePilotContractError("external_dependencies must be a JSON object.")
    _require_exact_keys(raw_deps, EXTERNAL_DEPENDENCY_KEYS, label="external_dependencies")
    reference = raw_deps["reference"]
    if reference is not None:
        reference = _require_safe_text(
            {"reference": reference}, "reference", label="external_dependencies"
        )
    return {
        "hotfix_main_required": _require_bool(
            raw_deps, "hotfix_main_required", expected=None, label="external_dependencies"
        ),
        "hotfix_main_merged": _require_bool(
            raw_deps, "hotfix_main_merged", expected=None, label="external_dependencies"
        ),
        "reference": reference,
    }


def _normalize_github_app_capability(raw_capability: Any) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], normalize_github_app_capability_state(raw_capability))
    except GithubAppPrivatePilotCapabilityError as exc:
        raise CreativeCodePrivatePilotContractError(str(exc)) from exc


def decide_next_action(state: Mapping[str, Any]) -> str:
    """Return the next lifecycle action from a validated state-like mapping."""

    normalized = validate_private_pilot_state(
        state,
        refresh_decision=False,
        validate_identity=False,
    )
    blockers = normalized["blockers"]
    checks = normalized["current_head_checks"]
    summary = checks["summary"]
    deps = normalized["external_dependencies"]
    source_state = str(normalized["source_pr"]["state"]).lower()

    if deps["hotfix_main_required"] and not deps["hotfix_main_merged"]:
        return "wait_for_hotfix_main"
    if source_state not in {"open", "merged"}:
        return "hold_for_governance"
    if blockers["security_blocker_count"] > 0:
        return "hold_for_security"
    if blockers["governance_blocker_count"] > 0:
        return "hold_for_governance"
    if blockers["fixed_mapping_required"] and not blockers["fixed_mapping_present"]:
        return "hold_for_governance"
    if blockers["actionable_review_count"] > 0:
        return "fix_current_pr"
    if summary["required_failing"] > 0 or (
        not checks["required_metadata_available"] and summary["current_failing"] > 0
    ):
        return "fix_current_pr"
    if (
        summary["required_pending"] > 0
        or summary["required_missing"] > 0
        or (not checks["required_metadata_available"] and summary["current_pending"] > 0)
        or checks["overall"] in {"pending", "missing", "unknown"}
    ):
        return "wait_for_ci"
    if normalized["source_pr"]["draft"]:
        return "wait_for_review"
    if normalized["review_capacity"]["friction"] in {"high", "blocked"}:
        return "wait_for_review"
    if normalized["github_app_capability"]["missing_permissions"]:
        return "hold_for_governance"
    return "prepare_next_candidate_plan"


def _state_identity_payload(
    state: Mapping[str, Any], *, legacy_without_github_app_capability: bool = False
) -> dict[str, Any]:
    payload = {
        "source_pr": state["source_pr"],
        "current_head_checks": state["current_head_checks"],
        "review_capacity": state["review_capacity"],
        "blockers": state["blockers"],
        "governance_refs": state["governance_refs"],
        "external_dependencies": state["external_dependencies"],
        "decision": state["decision"],
        "authority": state["authority"],
        "sanitized": True,
    }
    if not legacy_without_github_app_capability:
        payload["github_app_capability"] = state["github_app_capability"]
    return payload


def _private_pilot_identity(
    state: Mapping[str, Any], *, legacy_without_github_app_capability: bool = False
) -> tuple[str, str]:
    fingerprint = fingerprint_payload(
        _state_identity_payload(
            state,
            legacy_without_github_app_capability=legacy_without_github_app_capability,
        )
    )
    state_id = build_asset_id(
        asset_type=STATE_ARTIFACT_TYPE,
        rail="creative_code_private_pilot",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=(
            f"pr:{state['source_pr']['repository']}:{state['source_pr']['pr_number']}",
            state["source_pr"]["head_sha"],
        ),
    )
    idempotency_key = build_idempotency_key(
        asset_type=STATE_ARTIFACT_TYPE,
        rail="creative_code_private_pilot",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=(state_id,),
    )
    return state_id, idempotency_key


def validate_private_pilot_state(
    payload: Mapping[str, Any],
    *,
    refresh_decision: bool = True,
    validate_identity: bool = True,
) -> dict[str, Any]:
    """Validate and normalize a CreativeCodePrivatePilotState payload."""

    legacy_without_github_app_capability = "github_app_capability" not in payload
    raw_payload: Mapping[str, Any]
    if legacy_without_github_app_capability:
        allowed_legacy_keys = STATE_KEYS - {"github_app_capability"}
        _require_exact_keys(payload, allowed_legacy_keys, label="state")
        raw_payload = {
            **payload,
            "github_app_capability": default_github_app_capability_state(),
        }
    else:
        _require_exact_keys(payload, STATE_KEYS, label="state")
        raw_payload = payload
    _require_const(raw_payload, "schema_version", SCHEMA_VERSION, label="state")
    _require_const(raw_payload, "artifact_type", STATE_ARTIFACT_TYPE, label="state")
    _require_const(raw_payload, "policy_version", POLICY_VERSION, label="state")
    source_pr = _normalize_source_pr(raw_payload["source_pr"])
    normalized: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": STATE_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "state_id": _require_id(raw_payload, "state_id", label="state"),
        "idempotency_key": _require_id(raw_payload, "idempotency_key", label="state"),
        "generated_at_utc": _require_timestamp(
            raw_payload["generated_at_utc"], label="state.generated_at_utc"
        ),
        "source_pr": source_pr,
        "current_head_checks": _normalize_current_head_checks(
            raw_payload["current_head_checks"], source_head_sha=source_pr["head_sha"]
        ),
        "review_capacity": _normalize_review_capacity(raw_payload["review_capacity"]),
        "blockers": _normalize_blockers(raw_payload["blockers"]),
        "governance_refs": _normalize_governance_refs(raw_payload["governance_refs"]),
        "github_app_capability": _normalize_github_app_capability(
            raw_payload["github_app_capability"]
        ),
        "external_dependencies": _normalize_external_dependencies(
            raw_payload["external_dependencies"]
        ),
        "decision": _require_token(raw_payload, "decision", label="state"),
        "authority": _normalize_authority(raw_payload["authority"]),
        "sanitized": _require_bool(raw_payload, "sanitized", expected=True, label="state"),
    }
    _validate_fixed_mapping_consistency(normalized)
    if normalized["decision"] not in DECISIONS:
        raise CreativeCodePrivatePilotContractError("state.decision is unsupported.")
    expected_decision = (
        decide_next_action(normalized) if refresh_decision else normalized["decision"]
    )
    if normalized["decision"] != expected_decision:
        raise CreativeCodePrivatePilotContractError(
            f"state.decision must equal computed next action {expected_decision!r}."
        )
    if validate_identity:
        expected_state_id, expected_idempotency_key = _private_pilot_identity(
            normalized,
            legacy_without_github_app_capability=legacy_without_github_app_capability,
        )
        if normalized["state_id"] != expected_state_id:
            raise CreativeCodePrivatePilotContractError("state.state_id does not match payload.")
        if normalized["idempotency_key"] != expected_idempotency_key:
            raise CreativeCodePrivatePilotContractError(
                "state.idempotency_key does not match payload."
            )
    reject_unsafe_private_pilot_value(normalized, label="state")
    return normalized


def build_current_head_check_summary(
    *,
    pr_head_sha: str,
    raw_checks: Sequence[Mapping[str, Any]],
    required_check_names: Sequence[str] = (),
    required_metadata_available: bool = False,
) -> dict[str, Any]:
    """Normalize check/run rows and keep only latest rows for the PR head SHA."""

    if not SHA_RE.fullmatch(pr_head_sha):
        raise CreativeCodePrivatePilotContractError("pr_head_sha must be a 40-char SHA.")
    required_specs = {
        _normalize_required_check_spec(name) for name in required_check_names if name.strip()
    }
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    latest_required_keys: dict[tuple[str, str], set[str]] = {}
    latest_ts: dict[tuple[str, str], str] = {}
    stale = {
        "total": 0,
        "failed": 0,
        "cancelled": 0,
        "superseded": 0,
        "wrong_head_sha": 0,
        "missing_head_sha": 0,
    }
    degraded: list[str] = []

    for index, raw in enumerate(raw_checks):
        label = f"raw_checks[{index}]"
        name = _require_safe_text(raw, "name", label=label)
        workflow = _require_safe_text(
            {"workflow": raw.get("workflow") or raw.get("workflow_name") or ""},
            "workflow",
            label=label,
        )
        head_sha = raw.get("head_sha")
        conclusion_raw = str(raw.get("conclusion") or raw.get("status") or "unknown").lower()
        state = _check_state_from_raw(raw)
        timestamp = _timestamp_from_raw(raw)
        required_match_keys = _required_check_match_keys(
            name=name,
            workflow=workflow,
            app_id=raw.get("app_id") or raw.get("appId"),
        )
        if not isinstance(head_sha, str) or not SHA_RE.fullmatch(head_sha):
            stale["total"] += 1
            stale["missing_head_sha"] += 1
            degraded.append(f"missing-head-sha:{name}")
            continue
        if head_sha != pr_head_sha:
            stale["total"] += 1
            stale["wrong_head_sha"] += 1
            if _is_failing_check_state(state):
                stale["failed"] += 1
            if state == "cancelled":
                stale["cancelled"] += 1
            continue
        entry = {
            "name": name,
            "workflow": workflow,
            "state": state,
            "conclusion": conclusion_raw[:64],
            "head_sha": head_sha,
            "required": bool(raw.get("required")) or bool(required_match_keys & required_specs),
            "details_url": _safe_github_url_or_none(raw.get("details_url") or raw.get("url")),
            "observed_at_utc": timestamp or None,
        }
        key = (name, workflow)
        has_previous = key in latest
        previous_ts = latest_ts.get(key)
        if has_previous and (not timestamp or not previous_ts):
            degraded.append(f"missing-check-timestamp:{name}")
            previous = latest[key]
            if _check_state_risk_rank(state) > _check_state_risk_rank(str(previous["state"])):
                if _is_failing_check_state(str(previous["state"])):
                    stale["failed"] += 1
                if previous["state"] == "cancelled":
                    stale["cancelled"] += 1
                latest[key] = entry
                latest_required_keys[key] = required_match_keys
                latest_ts[key] = timestamp
            else:
                if _is_failing_check_state(state):
                    stale["failed"] += 1
                if state == "cancelled":
                    stale["cancelled"] += 1
            stale["total"] += 1
            stale["superseded"] += 1
            continue
        if not has_previous or (timestamp, str(entry["details_url"] or "")) >= (
            previous_ts or "",
            str((latest.get(key) or {}).get("details_url") or ""),
        ):
            if previous_ts is not None:
                stale["total"] += 1
                stale["superseded"] += 1
                previous = latest[key]
                if _is_failing_check_state(previous["state"]):
                    stale["failed"] += 1
                if previous["state"] == "cancelled":
                    stale["cancelled"] += 1
            latest[key] = entry
            latest_required_keys[key] = required_match_keys
            latest_ts[key] = timestamp
        else:
            stale["total"] += 1
            stale["superseded"] += 1
            if _is_failing_check_state(state):
                stale["failed"] += 1
            if state == "cancelled":
                stale["cancelled"] += 1

    observed_required_specs = set().union(
        *(keys & required_specs for keys in latest_required_keys.values())
    )
    missing_required = sorted(required_specs - observed_required_specs)
    current_workflows_by_name: dict[str, set[str]] = {}
    for entry in latest.values():
        current_workflows_by_name.setdefault(str(entry["name"]), set()).add(str(entry["workflow"]))
    identity_conflicts = sorted(
        display_name
        for spec in required_specs
        if _required_check_spec_is_name_only(spec)
        for display_name in [_required_check_display_name(spec)]
        if len(current_workflows_by_name.get(display_name, set())) > 1
    )
    for name in identity_conflicts:
        degraded.append(f"required-check-identity-conflict:{name}")
    current = [latest[key] for key in sorted(latest)]
    summary = _check_summary_from_current(
        current,
        required_missing=len(missing_required) + len(identity_conflicts),
    )
    overall = _overall_from_check_summary(
        summary=summary,
        required_metadata_available=required_metadata_available,
    )
    return {
        "pr_head_sha": pr_head_sha,
        "overall": overall,
        "required_metadata_available": bool(required_metadata_available),
        "current": current,
        "stale_diagnostics": stale,
        "summary": summary,
        "degraded_reasons": sorted(set(degraded)),
    }


def _normalize_required_check_spec(raw_name: str) -> str:
    value = raw_name.strip()
    if value.startswith(("app_id:", "check_run:", "status_context:", "name:")):
        return value
    return f"name:{value}"


def _required_check_spec_is_name_only(spec: str) -> bool:
    return spec.startswith("name:")


def _required_check_display_name(spec: str) -> str:
    if spec.startswith("name:"):
        return spec.removeprefix("name:")
    if spec.startswith("status_context:"):
        return spec.removeprefix("status_context:")
    if spec.startswith("check_run:"):
        return spec.removeprefix("check_run:")
    if spec.startswith("app_id:"):
        return spec.rsplit(":", 1)[-1]
    return spec


def _required_check_match_keys(*, name: str, workflow: str, app_id: Any) -> set[str]:
    keys = {f"name:{name}"}
    if workflow == "status_context":
        keys.add(f"status_context:{name}")
    else:
        keys.add(f"check_run:{name}")
    app_id_text = str(app_id or "").strip()
    if app_id_text:
        keys.add(f"app_id:{app_id_text}:{name}")
    return keys


def _timestamp_from_raw(raw: Mapping[str, Any]) -> str:
    for key in (
        "completed_at",
        "completedAt",
        "started_at",
        "startedAt",
        "created_at",
        "createdAt",
    ):
        value = raw.get(key)
        if isinstance(value, str) and TIMESTAMP_RE.fullmatch(value):
            return value
    return ""


def _check_state_from_raw(raw: Mapping[str, Any]) -> str:
    status = str(raw.get("status") or "").strip().lower()
    conclusion = str(raw.get("conclusion") or "").strip().lower()
    if status in {"queued", "in_progress", "pending", "requested", "waiting", "expected"}:
        return "pending"
    if conclusion == "success" or status == "success":
        return "passed"
    if conclusion == "neutral":
        return "neutral"
    if conclusion == "skipped":
        return "failed"
    if conclusion == "cancelled":
        return "cancelled"
    if conclusion == "stale":
        return "stale"
    if conclusion in {"failure", "timed_out", "action_required", "startup_failure", "error"}:
        return "failed"
    if status in {"failure", "failed", "error", "timed_out", "action_required"}:
        return "failed"
    if status in {"cancelled", "canceled"}:
        return "cancelled"
    if status in {"completed"} and not conclusion:
        return "pending"
    return "pending" if status else "failed"


def classify_review_capacity(raw_sources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Classify review-source friction without preserving raw reasons."""

    sources = []
    for index, source in enumerate(raw_sources):
        source_name = _require_token(source, "source", label=f"review_sources[{index}]")
        status = _require_token(source, "status", label=f"review_sources[{index}]")
        if status not in REVIEW_SOURCE_STATUSES:
            status = "degraded"
        degraded = bool(source.get("source_degraded")) or status in {
            "degraded",
            "unavailable",
            "rate_limited",
            "usage_limit_reached",
            "auth_missing",
            "partial",
        }
        blocking = bool(source.get("blocking")) or status in {
            "fallback_finding",
            "failed_required_check",
            "unresolved_threads",
            "actionable_bot_comments",
        }
        sources.append(
            {
                "source": source_name,
                "status": status,
                "source_degraded": degraded,
                "blocking": blocking,
            }
        )
    if any(source["blocking"] for source in sources):
        friction = "blocked"
    elif sum(1 for source in sources if source["source_degraded"]) >= 2:
        friction = "high"
    elif any(source["source_degraded"] for source in sources):
        friction = "medium"
    elif not sources:
        friction = "low"
    else:
        friction = "none"
    return {"friction": friction, "sources": sources}


def build_private_pilot_state(
    *,
    generated_at_utc: str,
    source_pr: Mapping[str, Any],
    current_head_checks: Mapping[str, Any],
    review_capacity: Mapping[str, Any],
    blockers: Mapping[str, Any],
    governance_refs: Mapping[str, Any],
    github_app_capability: Mapping[str, Any] | None = None,
    external_dependencies: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and validate a CreativeCodePrivatePilotState."""

    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": STATE_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "state_id": "pending-state",
        "idempotency_key": "pending-idempotency",
        "generated_at_utc": generated_at_utc,
        "source_pr": dict(source_pr),
        "current_head_checks": dict(current_head_checks),
        "review_capacity": dict(review_capacity),
        "blockers": dict(blockers),
        "governance_refs": dict(governance_refs),
        "github_app_capability": dict(
            github_app_capability or default_github_app_capability_state()
        ),
        "external_dependencies": dict(
            external_dependencies
            or {
                "hotfix_main_required": False,
                "hotfix_main_merged": False,
                "reference": None,
            }
        ),
        "decision": "wait_for_ci",
        "authority": default_private_pilot_authority(),
        "sanitized": True,
    }
    state["decision"] = decide_next_action(state)
    state_id, idempotency_key = _private_pilot_identity(state)
    state["state_id"] = state_id
    state["idempotency_key"] = idempotency_key
    return validate_private_pilot_state(state)


def _candidate_plan_identity(plan: Mapping[str, Any]) -> tuple[str, str]:
    fingerprint = fingerprint_payload(
        {
            "source_state_id": plan["source_state_id"],
            "source_state_fingerprint": plan["source_state_fingerprint"],
            "target_surface": plan["target_surface"],
            "checklist": plan["checklist"],
            "authority": plan["authority"],
            "sanitized": True,
        }
    )
    plan_id = build_asset_id(
        asset_type=CANDIDATE_PLAN_ARTIFACT_TYPE,
        rail="creative_code_private_pilot",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=(plan["source_state_id"], plan["source_state_fingerprint"]),
    )
    idempotency_key = build_idempotency_key(
        asset_type=CANDIDATE_PLAN_ARTIFACT_TYPE,
        rail="creative_code_private_pilot",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=(plan_id,),
    )
    return plan_id, idempotency_key


def build_candidate_plan(state: Mapping[str, Any]) -> dict[str, Any]:
    """Build a checklist-only candidate plan from an eligible pilot state."""

    normalized_state = validate_private_pilot_state(state)
    if normalized_state["decision"] != "prepare_next_candidate_plan":
        raise CreativeCodePrivatePilotContractError(
            "candidate plan requires prepare_next_candidate_plan decision."
        )
    source_fingerprint = fingerprint_payload(normalized_state)
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": CANDIDATE_PLAN_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "plan_id": "pending-plan",
        "idempotency_key": "pending-idempotency",
        "source_state_id": normalized_state["state_id"],
        "source_state_fingerprint": source_fingerprint,
        "decision": "prepare_next_candidate_plan",
        "target_surface": [DEFAULT_TARGET_SURFACE],
        "checklist": [
            {
                "label": "confirm_current_head_snapshot",
                "description": "Confirm state head SHA, required checks, and review-source status are current.",
                "checklist_only": True,
                "executes_in_operator": False,
                "requires_human_gate": True,
            },
            {
                "label": "prepare_pr1_specification_packet",
                "description": "Prepare a future PR-1 specification packet for the prompt program target only.",
                "checklist_only": True,
                "executes_in_operator": False,
                "requires_human_gate": True,
            },
            {
                "label": "run_existing_creative_code_train_manually",
                "description": "Use existing PR-1, PR-2, PR-3, and PR-4 tools only after separate human approval.",
                "checklist_only": True,
                "executes_in_operator": False,
                "requires_human_gate": True,
            },
        ],
        "blocked_authority": sorted(AUTHORITY_FALSE_KEYS),
        "authority": default_private_pilot_authority(),
        "sanitized": True,
    }
    plan_id, idempotency_key = _candidate_plan_identity(plan)
    plan["plan_id"] = plan_id
    plan["idempotency_key"] = idempotency_key
    return validate_candidate_plan(plan)


def validate_candidate_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a checklist-only candidate plan."""

    _require_exact_keys(payload, CANDIDATE_PLAN_KEYS, label="candidate_plan")
    _require_const(payload, "schema_version", SCHEMA_VERSION, label="candidate_plan")
    _require_const(payload, "artifact_type", CANDIDATE_PLAN_ARTIFACT_TYPE, label="candidate_plan")
    _require_const(payload, "policy_version", POLICY_VERSION, label="candidate_plan")
    target_surface = payload["target_surface"]
    if target_surface != [DEFAULT_TARGET_SURFACE]:
        raise CreativeCodePrivatePilotContractError(
            f"candidate_plan.target_surface must be exactly [{DEFAULT_TARGET_SURFACE!r}]."
        )
    checklist_raw = payload["checklist"]
    if not isinstance(checklist_raw, list) or not checklist_raw:
        raise CreativeCodePrivatePilotContractError("candidate_plan.checklist must be non-empty.")
    checklist = [
        _normalize_checklist_item(item, label=f"candidate_plan.checklist[{index}]")
        for index, item in enumerate(checklist_raw)
    ]
    blocked_authority = payload["blocked_authority"]
    expected_blocked_authority = sorted(AUTHORITY_FALSE_KEYS)
    if not isinstance(blocked_authority, list) or blocked_authority != expected_blocked_authority:
        raise CreativeCodePrivatePilotContractError(
            "candidate_plan.blocked_authority must list all forbidden authority flags "
            "in canonical sorted order."
        )
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": CANDIDATE_PLAN_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "plan_id": _require_id(payload, "plan_id", label="candidate_plan"),
        "idempotency_key": _require_id(payload, "idempotency_key", label="candidate_plan"),
        "source_state_id": _require_id(payload, "source_state_id", label="candidate_plan"),
        "source_state_fingerprint": _require_sha256(
            payload["source_state_fingerprint"], label="candidate_plan.source_state_fingerprint"
        ),
        "decision": _require_const(
            payload, "decision", "prepare_next_candidate_plan", label="candidate_plan"
        ),
        "target_surface": [DEFAULT_TARGET_SURFACE],
        "checklist": checklist,
        "blocked_authority": sorted(AUTHORITY_FALSE_KEYS),
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label="candidate_plan"),
    }
    expected_plan_id, expected_idempotency_key = _candidate_plan_identity(normalized)
    if normalized["plan_id"] != expected_plan_id:
        raise CreativeCodePrivatePilotContractError(
            "candidate_plan.plan_id does not match payload."
        )
    if normalized["idempotency_key"] != expected_idempotency_key:
        raise CreativeCodePrivatePilotContractError(
            "candidate_plan.idempotency_key does not match payload."
        )
    reject_unsafe_private_pilot_value(normalized, label="candidate_plan")
    return normalized


def _normalize_checklist_item(raw_item: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_item, Mapping):
        raise CreativeCodePrivatePilotContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_item, CHECKLIST_ITEM_KEYS, label=label)
    return {
        "label": _require_token(raw_item, "label", label=label),
        "description": _require_safe_text(raw_item, "description", label=label, max_chars=220),
        "checklist_only": _require_bool(raw_item, "checklist_only", expected=True, label=label),
        "executes_in_operator": _require_bool(
            raw_item, "executes_in_operator", expected=False, label=label
        ),
        "requires_human_gate": _require_bool(
            raw_item, "requires_human_gate", expected=True, label=label
        ),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate creative-code private-pilot loop contracts."
    )
    parser.add_argument("--validate-state", help="Path to pilot_state.json.")
    parser.add_argument("--validate-candidate-plan", help="Path to candidate_plan.json.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        did_validate = False
        if args.validate_state:
            validate_private_pilot_state(read_json_object(args.validate_state))
            did_validate = True
        if args.validate_candidate_plan:
            validate_candidate_plan(read_json_object(args.validate_candidate_plan))
            did_validate = True
    except CreativeCodePrivatePilotContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not did_validate:
        print("PASS: creative-code private-pilot contract import valid")
    else:
        print("PASS: creative-code private-pilot contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
