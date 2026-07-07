"""Strict contracts for PR-3 human-approved creative-code PR promotion.

PR-3 consumes accepted PR-2 candidate patch artifacts and can open a normal
non-draft `experiment/*` pull request only after isolated validation and explicit
TTY approval. The artifacts here are metadata contracts; they do not grant
review-thread, merge-readiness, merge, release, Slack, or GitHub App authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import PurePosixPath
import re
import sys
from pathlib import Path
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-code-pr-promotion-pr3"

PLAN_TYPE = "creative_code_pr_promotion_plan"
VALIDATION_TYPE = "creative_code_pr_promotion_validation"
APPROVAL_TYPE = "creative_code_pr_promotion_approval"
RECEIPT_TYPE = "creative_code_pr_promotion_receipt"

TARGET_REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
TARGET_BASE_BRANCH = "main"
PULL_REQUEST_MODE = "non_draft"
APPROVAL_DECISION = "approve_non_draft_pr_creation"
RUNNER_COAUTHOR = "PulsePlate Experiment Runner <pulseplate@pm.me>"

SUCCESS_OUTPUT = "PASS: creative-code PR promotion contract valid"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PROMOTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SAFE_TITLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/()#,+-]{0,119}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
BRANCH_RE = re.compile(r"^experiment/[a-z0-9][a-z0-9._-]{0,68}$")
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
URL_RE = re.compile(r"^https://github\.com/Katsiarynakavaleuskaya/PulsePlate/pull/[0-9]+$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |raw[_ -]?(prompt|response|context|patch)|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|oracle stdout|oracle stderr|"
    r"/Users/|/private/var/|/var/folders/|/tmp/|github_pat_|gh[psoru]_|"
    r"xox[abprs]-|sk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE | re.MULTILINE,
)

FORBIDDEN_PATCH_PREFIXES: tuple[str, ...] = (
    ".git/",
    ".github/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "artifacts/",
    "build/",
    "dist/",
    "docs/review/",
    "frontend/",
    "ios/",
    "node_modules/",
    "scripts/ci/",
    "worktrees/",
)
FORBIDDEN_PATCH_PATHS = frozenset(
    {
        ".git",
        ".github",
        ".gitmodules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "artifacts",
        "build",
        "dist",
        "docs/review",
        "frontend",
        "ios",
        "node_modules",
        "worktrees",
    }
)

PLAN_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "promotion_id",
        "idempotency_key",
        "source_result_id",
        "source_request_id",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "patch_fingerprint",
        "base_commit_sha",
        "changed_paths",
        "target_repository",
        "target_base_branch",
        "target_head_branch",
        "pull_request_mode",
        "pull_request_title",
        "pull_request_body_fingerprint",
        "authority",
    }
)
PLAN_AUTHORITY_KEYS = frozenset(
    {
        "create_new_branch",
        "push_new_branch",
        "open_non_draft_pull_request",
        "open_draft_pull_request",
        "modify_existing_branch",
        "force_push",
        "write_default_branch",
        "request_review",
        "submit_review",
        "resolve_review_threads",
        "claim_merge_readiness",
        "merge",
        "release",
        "modify_github_app_settings",
        "modify_slack_settings",
    }
)
PLAN_AUTHORITY_TRUE_KEYS = frozenset(
    {"create_new_branch", "push_new_branch", "open_non_draft_pull_request"}
)

VALIDATION_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "promotion_id",
        "plan_fingerprint",
        "patch_fingerprint",
        "base_commit_sha",
        "fresh_oracle",
        "preopen_gates",
        "validation_checkout",
        "validation_fingerprint",
    }
)
FRESH_ORACLE_KEYS = frozenset(
    {
        "status",
        "changed_paths_match",
        "shared_tree_untouched",
        "oracle_commands_configured",
        "oracle_commands_executed",
    }
)
PREOPEN_GATES_KEYS = frozenset({"pre_commit", "validate_changed", "patch_unchanged_after_gates"})
VALIDATION_CHECKOUT_KEYS = frozenset({"created", "destroyed", "used_throwaway_commit"})

APPROVAL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "promotion_id",
        "approval_id",
        "plan_fingerprint",
        "validation_fingerprint",
        "decision",
        "approved_by_login",
        "confirmed_patch_fingerprint",
        "confirmed_base_commit_sha",
        "confirmed_target_branch",
        "confirmation_mode",
        "unattended_approval",
    }
)

RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "promotion_id",
        "receipt_id",
        "plan_fingerprint",
        "validation_fingerprint",
        "approval_id",
        "source_result_id",
        "patch_fingerprint",
        "repository",
        "base_branch",
        "head_branch",
        "commit_sha",
        "pull_request_number",
        "pull_request_url",
        "pull_request_state",
        "pull_request_draft",
        "review_cycle_started",
        "approved_by_login",
        "human_commit_author",
        "runner_commit_author",
        "runner_coauthor_trailer_present",
        "ready_for_review_operation_used",
        "merge_ready",
        "sanitized",
        "partial_failure",
    }
)


class CreativeCodePRPromotionContractError(ValueError):
    """Raised when a PR-3 promotion artifact violates authority or schema."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodePRPromotionContractError(
                f"creative-code PR promotion artifact has duplicate JSON key: {key}"
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
    except CreativeCodePRPromotionContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodePRPromotionContractError(
            "Unable to read creative-code PR promotion JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodePRPromotionContractError(
            "Creative-code PR promotion artifact must be a JSON object."
        )
    return payload


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
        raise CreativeCodePRPromotionContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodePRPromotionContractError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_promotion_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not PROMOTION_ID_RE.fullmatch(normalized):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_sha(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a 40-char git SHA.")
    return value


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a sha256 digest.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, expected: bool, label: str) -> bool:
    value = payload.get(key)
    if value is not expected:
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be {expected}.")
    return True if expected else False


def _require_any_bool(payload: Mapping[str, Any], key: str, *, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a boolean.")
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
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodePRPromotionContractError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _reject_leaks(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise CreativeCodePRPromotionContractError(f"{label} contains unsafe text.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_leaks(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_leaks(item, label=f"{label}.{key}")


def reject_unsafe_public_text(text: str, *, label: str) -> None:
    """Reject text that must not be written to PR bodies or receipts."""

    _reject_leaks(text, label=label)


def _normalize_patch_path(raw_path: Any, *, label: str) -> str:
    if not isinstance(raw_path, str):
        raise CreativeCodePRPromotionContractError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeCodePRPromotionContractError(f"{label} must be non-empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeCodePRPromotionContractError(f"{label} must not contain control characters.")
    if "\\" in value:
        raise CreativeCodePRPromotionContractError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")):
        raise CreativeCodePRPromotionContractError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeCodePRPromotionContractError(f"{label} must not be a URL or scheme path.")
    path = PurePosixPath(value)
    if not path.parts or "." in path.parts or ".." in path.parts:
        raise CreativeCodePRPromotionContractError(f"{label} must not contain traversal segments.")
    normalized = path.as_posix()
    if normalized in FORBIDDEN_PATCH_PATHS or any(
        normalized.startswith(prefix) for prefix in FORBIDDEN_PATCH_PREFIXES
    ):
        raise CreativeCodePRPromotionContractError(f"{label} points to a forbidden surface.")
    return normalized


def _normalize_path_list(payload: Mapping[str, Any], key: str, *, label: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be an array.")
    if not value:
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        path = _normalize_patch_path(item, label=f"{label}.{key}[{index}]")
        if path in seen:
            raise CreativeCodePRPromotionContractError(
                f"{label}.{key} must not contain duplicates."
            )
        seen.add(path)
        normalized.append(path)
    return normalized


def require_safe_branch(branch: Any, *, label: str = "target_head_branch") -> str:
    """Validate the derived `experiment/*` promotion branch name."""

    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        raise CreativeCodePRPromotionContractError(
            f"{label} must be a derived lowercase experiment/* branch."
        )
    if "//" in branch or ".." in branch or branch.endswith((".", ".lock", "/")):
        raise CreativeCodePRPromotionContractError(f"{label} is not a safe git ref name.")
    return branch


def _normalize_title(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SAFE_TITLE_RE.fullmatch(value):
        raise CreativeCodePRPromotionContractError(f"{label}.{key} must be a safe title.")
    _reject_leaks(value, label=f"{label}.{key}")
    return value.strip()


def _normalize_plan_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodePRPromotionContractError("CreativeCodePRPromotionPlan.authority invalid.")
    label = "CreativeCodePRPromotionPlan.authority"
    _require_exact_keys(raw_authority, PLAN_AUTHORITY_KEYS, label=label)
    normalized: dict[str, bool] = {}
    for key in PLAN_AUTHORITY_KEYS:
        normalized[key] = _require_bool(
            raw_authority,
            key,
            expected=key in PLAN_AUTHORITY_TRUE_KEYS,
            label=label,
        )
    return {key: normalized[key] for key in sorted(normalized)}


def _plan_identity_payload(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {key: plan[key] for key in sorted(PLAN_KEYS - {"idempotency_key"})}


def promotion_plan_fingerprint(plan: Mapping[str, Any]) -> str:
    """Return the immutable fingerprint a human approves for PR creation."""

    return cast(str, fingerprint_payload(_plan_identity_payload(plan)))


def _build_plan_idempotency_key(plan: Mapping[str, Any]) -> str:
    fingerprint = promotion_plan_fingerprint(plan)
    upstream_ids = (
        str(plan["source_result_id"]),
        str(plan["patch_fingerprint"]),
        str(plan["base_commit_sha"]),
        str(plan["target_head_branch"]),
    )
    return cast(
        str,
        build_idempotency_key(
            asset_type=PLAN_TYPE,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=upstream_ids,
        ),
    )


def build_creative_code_pr_promotion_plan(
    *,
    promotion_id: str,
    source_result_id: str,
    source_request_id: str,
    source_bundle_id: str,
    source_bundle_fingerprint: str,
    selected_variant_id: str,
    selected_variant_fingerprint: str,
    patch_fingerprint: str,
    base_commit_sha: str,
    changed_paths: list[str],
    target_head_branch: str,
    pull_request_title: str,
    pull_request_body_fingerprint: str,
) -> dict[str, Any]:
    """Build a deterministic PR-3 promotion plan."""

    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PLAN_TYPE,
        "policy_version": POLICY_VERSION,
        "promotion_id": promotion_id,
        "idempotency_key": "pending",
        "source_result_id": source_result_id,
        "source_request_id": source_request_id,
        "source_bundle_id": source_bundle_id,
        "source_bundle_fingerprint": source_bundle_fingerprint,
        "selected_variant_id": selected_variant_id,
        "selected_variant_fingerprint": selected_variant_fingerprint,
        "patch_fingerprint": patch_fingerprint,
        "base_commit_sha": base_commit_sha,
        "changed_paths": changed_paths,
        "target_repository": TARGET_REPOSITORY,
        "target_base_branch": TARGET_BASE_BRANCH,
        "target_head_branch": target_head_branch,
        "pull_request_mode": PULL_REQUEST_MODE,
        "pull_request_title": pull_request_title,
        "pull_request_body_fingerprint": pull_request_body_fingerprint,
        "authority": {key: key in PLAN_AUTHORITY_TRUE_KEYS for key in sorted(PLAN_AUTHORITY_KEYS)},
    }
    plan["idempotency_key"] = _build_plan_idempotency_key(plan)
    return validate_creative_code_pr_promotion_plan(plan)


def validate_creative_code_pr_promotion_plan(payload: dict[str, Any]) -> dict[str, Any]:
    label = "CreativeCodePRPromotionPlan"
    _require_exact_keys(payload, PLAN_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", PLAN_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "promotion_id": _require_promotion_id(payload, "promotion_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_result_id": _require_id(payload, "source_result_id", label=label),
        "source_request_id": _require_id(payload, "source_request_id", label=label),
        "source_bundle_id": _require_id(payload, "source_bundle_id", label=label),
        "source_bundle_fingerprint": _require_fingerprint(
            payload, "source_bundle_fingerprint", label=label
        ),
        "selected_variant_id": _require_id(payload, "selected_variant_id", label=label),
        "selected_variant_fingerprint": _require_fingerprint(
            payload, "selected_variant_fingerprint", label=label
        ),
        "patch_fingerprint": _require_fingerprint(payload, "patch_fingerprint", label=label),
        "base_commit_sha": _require_sha(payload, "base_commit_sha", label=label),
        "changed_paths": _normalize_path_list(payload, "changed_paths", label=label),
        "target_repository": _require_const(
            payload, "target_repository", TARGET_REPOSITORY, label=label
        ),
        "target_base_branch": _require_const(
            payload, "target_base_branch", TARGET_BASE_BRANCH, label=label
        ),
        "target_head_branch": require_safe_branch(
            payload.get("target_head_branch"), label=f"{label}.target_head_branch"
        ),
        "pull_request_mode": _require_const(
            payload, "pull_request_mode", PULL_REQUEST_MODE, label=label
        ),
        "pull_request_title": _normalize_title(payload, "pull_request_title", label=label),
        "pull_request_body_fingerprint": _require_fingerprint(
            payload, "pull_request_body_fingerprint", label=label
        ),
        "authority": _normalize_plan_authority(payload["authority"]),
    }
    expected_key = _build_plan_idempotency_key(normalized)
    if normalized["idempotency_key"] != expected_key:
        raise CreativeCodePRPromotionContractError(
            "idempotency_key does not match promotion plan content."
        )
    _reject_leaks(normalized, label=label)
    return normalized


def _normalize_fresh_oracle(raw_oracle: Any) -> dict[str, Any]:
    if not isinstance(raw_oracle, dict):
        raise CreativeCodePRPromotionContractError("fresh_oracle must be a JSON object.")
    label = "fresh_oracle"
    _require_exact_keys(raw_oracle, FRESH_ORACLE_KEYS, label=label)
    return {
        "status": _require_const(raw_oracle, "status", "accepted", label=label),
        "changed_paths_match": _require_bool(
            raw_oracle, "changed_paths_match", expected=True, label=label
        ),
        "shared_tree_untouched": _require_bool(
            raw_oracle, "shared_tree_untouched", expected=True, label=label
        ),
        "oracle_commands_configured": _require_int(
            raw_oracle,
            "oracle_commands_configured",
            min_value=1,
            max_value=20,
            label=label,
        ),
        "oracle_commands_executed": _require_int(
            raw_oracle,
            "oracle_commands_executed",
            min_value=1,
            max_value=20,
            label=label,
        ),
    }


def _normalize_preopen_gates(raw_gates: Any) -> dict[str, Any]:
    if not isinstance(raw_gates, dict):
        raise CreativeCodePRPromotionContractError("preopen_gates must be a JSON object.")
    label = "preopen_gates"
    _require_exact_keys(raw_gates, PREOPEN_GATES_KEYS, label=label)
    return {
        "pre_commit": _require_const(raw_gates, "pre_commit", "passed", label=label),
        "validate_changed": _require_const(raw_gates, "validate_changed", "passed", label=label),
        "patch_unchanged_after_gates": _require_bool(
            raw_gates,
            "patch_unchanged_after_gates",
            expected=True,
            label=label,
        ),
    }


def _normalize_validation_checkout(raw_checkout: Any) -> dict[str, bool]:
    if not isinstance(raw_checkout, dict):
        raise CreativeCodePRPromotionContractError("validation_checkout must be a JSON object.")
    label = "validation_checkout"
    _require_exact_keys(raw_checkout, VALIDATION_CHECKOUT_KEYS, label=label)
    return {
        "created": _require_bool(raw_checkout, "created", expected=True, label=label),
        "destroyed": _require_bool(raw_checkout, "destroyed", expected=True, label=label),
        "used_throwaway_commit": _require_bool(
            raw_checkout, "used_throwaway_commit", expected=True, label=label
        ),
    }


def _validation_identity_payload(validation: Mapping[str, Any]) -> dict[str, Any]:
    return {key: validation[key] for key in sorted(VALIDATION_KEYS - {"validation_fingerprint"})}


def build_creative_code_pr_promotion_validation(
    *,
    promotion_id: str,
    plan_fingerprint: str,
    patch_fingerprint: str,
    base_commit_sha: str,
    oracle_commands_configured: int,
    oracle_commands_executed: int,
) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": VALIDATION_TYPE,
        "policy_version": POLICY_VERSION,
        "promotion_id": promotion_id,
        "plan_fingerprint": plan_fingerprint,
        "patch_fingerprint": patch_fingerprint,
        "base_commit_sha": base_commit_sha,
        "fresh_oracle": {
            "status": "accepted",
            "changed_paths_match": True,
            "shared_tree_untouched": True,
            "oracle_commands_configured": oracle_commands_configured,
            "oracle_commands_executed": oracle_commands_executed,
        },
        "preopen_gates": {
            "pre_commit": "passed",
            "validate_changed": "passed",
            "patch_unchanged_after_gates": True,
        },
        "validation_checkout": {
            "created": True,
            "destroyed": True,
            "used_throwaway_commit": True,
        },
        "validation_fingerprint": "pending",
    }
    validation["validation_fingerprint"] = fingerprint_payload(
        _validation_identity_payload(validation)
    )
    return validate_creative_code_pr_promotion_validation(validation)


def validate_creative_code_pr_promotion_validation(payload: dict[str, Any]) -> dict[str, Any]:
    label = "CreativeCodePRPromotionValidation"
    _require_exact_keys(payload, VALIDATION_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", VALIDATION_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "promotion_id": _require_promotion_id(payload, "promotion_id", label=label),
        "plan_fingerprint": _require_fingerprint(payload, "plan_fingerprint", label=label),
        "patch_fingerprint": _require_fingerprint(payload, "patch_fingerprint", label=label),
        "base_commit_sha": _require_sha(payload, "base_commit_sha", label=label),
        "fresh_oracle": _normalize_fresh_oracle(payload["fresh_oracle"]),
        "preopen_gates": _normalize_preopen_gates(payload["preopen_gates"]),
        "validation_checkout": _normalize_validation_checkout(payload["validation_checkout"]),
        "validation_fingerprint": _require_fingerprint(
            payload, "validation_fingerprint", label=label
        ),
    }
    if (
        normalized["fresh_oracle"]["oracle_commands_executed"]
        != normalized["fresh_oracle"]["oracle_commands_configured"]
    ):
        raise CreativeCodePRPromotionContractError(
            "fresh_oracle must execute every configured oracle command."
        )
    expected = fingerprint_payload(_validation_identity_payload(normalized))
    if normalized["validation_fingerprint"] != expected:
        raise CreativeCodePRPromotionContractError(
            "validation_fingerprint does not match validation content."
        )
    _reject_leaks(normalized, label=label)
    return normalized


def _approval_identity_payload(approval: Mapping[str, Any]) -> dict[str, Any]:
    return {key: approval[key] for key in sorted(APPROVAL_KEYS - {"approval_id"})}


def build_creative_code_pr_promotion_approval(
    *,
    promotion_id: str,
    plan_fingerprint: str,
    validation_fingerprint: str,
    approved_by_login: str,
    confirmed_patch_fingerprint: str,
    confirmed_base_commit_sha: str,
    confirmed_target_branch: str,
) -> dict[str, Any]:
    approval: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": APPROVAL_TYPE,
        "policy_version": POLICY_VERSION,
        "promotion_id": promotion_id,
        "approval_id": "pending",
        "plan_fingerprint": plan_fingerprint,
        "validation_fingerprint": validation_fingerprint,
        "decision": APPROVAL_DECISION,
        "approved_by_login": approved_by_login,
        "confirmed_patch_fingerprint": confirmed_patch_fingerprint,
        "confirmed_base_commit_sha": confirmed_base_commit_sha,
        "confirmed_target_branch": confirmed_target_branch,
        "confirmation_mode": "interactive_tty",
        "unattended_approval": False,
    }
    approval["approval_id"] = build_asset_id(
        asset_type=APPROVAL_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint_payload(_approval_identity_payload(approval)),
        upstream_ids=(promotion_id, plan_fingerprint, validation_fingerprint),
    )
    return validate_creative_code_pr_promotion_approval(approval)


def validate_creative_code_pr_promotion_approval(payload: dict[str, Any]) -> dict[str, Any]:
    label = "CreativeCodePRPromotionApproval"
    _require_exact_keys(payload, APPROVAL_KEYS, label=label)
    approved_by = payload.get("approved_by_login")
    if not isinstance(approved_by, str) or not LOGIN_RE.fullmatch(approved_by):
        raise CreativeCodePRPromotionContractError(
            "CreativeCodePRPromotionApproval.approved_by_login must be a GitHub login."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", APPROVAL_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "promotion_id": _require_promotion_id(payload, "promotion_id", label=label),
        "approval_id": _require_id(payload, "approval_id", label=label),
        "plan_fingerprint": _require_fingerprint(payload, "plan_fingerprint", label=label),
        "validation_fingerprint": _require_fingerprint(
            payload, "validation_fingerprint", label=label
        ),
        "decision": _require_const(payload, "decision", APPROVAL_DECISION, label=label),
        "approved_by_login": approved_by,
        "confirmed_patch_fingerprint": _require_fingerprint(
            payload, "confirmed_patch_fingerprint", label=label
        ),
        "confirmed_base_commit_sha": _require_sha(
            payload, "confirmed_base_commit_sha", label=label
        ),
        "confirmed_target_branch": require_safe_branch(
            payload.get("confirmed_target_branch"),
            label=f"{label}.confirmed_target_branch",
        ),
        "confirmation_mode": _require_const(
            payload, "confirmation_mode", "interactive_tty", label=label
        ),
        "unattended_approval": _require_bool(
            payload, "unattended_approval", expected=False, label=label
        ),
    }
    expected = build_asset_id(
        asset_type=APPROVAL_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint_payload(_approval_identity_payload(normalized)),
        upstream_ids=(
            normalized["promotion_id"],
            normalized["plan_fingerprint"],
            normalized["validation_fingerprint"],
        ),
    )
    if normalized["approval_id"] != expected:
        raise CreativeCodePRPromotionContractError("approval_id does not match approval content.")
    _reject_leaks(normalized, label=label)
    return normalized


def _receipt_identity_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: receipt[key] for key in sorted(RECEIPT_KEYS - {"receipt_id"})}


def build_creative_code_pr_promotion_receipt(
    *,
    promotion_id: str,
    plan_fingerprint: str,
    validation_fingerprint: str,
    approval_id: str,
    source_result_id: str,
    patch_fingerprint: str,
    head_branch: str,
    commit_sha: str,
    pull_request_number: int,
    pull_request_url: str,
    approved_by_login: str,
    partial_failure: str | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": RECEIPT_TYPE,
        "policy_version": POLICY_VERSION,
        "promotion_id": promotion_id,
        "receipt_id": "pending",
        "plan_fingerprint": plan_fingerprint,
        "validation_fingerprint": validation_fingerprint,
        "approval_id": approval_id,
        "source_result_id": source_result_id,
        "patch_fingerprint": patch_fingerprint,
        "repository": TARGET_REPOSITORY,
        "base_branch": TARGET_BASE_BRANCH,
        "head_branch": head_branch,
        "commit_sha": commit_sha,
        "pull_request_number": pull_request_number,
        "pull_request_url": pull_request_url,
        "pull_request_state": "open" if partial_failure is None else "partial_failure",
        "pull_request_draft": False,
        "review_cycle_started": partial_failure is None,
        "approved_by_login": approved_by_login,
        "human_commit_author": True,
        "runner_commit_author": False,
        "runner_coauthor_trailer_present": True,
        "ready_for_review_operation_used": False,
        "merge_ready": False,
        "sanitized": True,
        "partial_failure": partial_failure,
    }
    receipt["receipt_id"] = build_asset_id(
        asset_type=RECEIPT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint_payload(_receipt_identity_payload(receipt)),
        upstream_ids=(promotion_id, approval_id, patch_fingerprint),
    )
    return validate_creative_code_pr_promotion_receipt(receipt)


def validate_creative_code_pr_promotion_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    label = "CreativeCodePRPromotionReceipt"
    _require_exact_keys(payload, RECEIPT_KEYS, label=label)
    pr_url = payload.get("pull_request_url")
    if pr_url != "" and (not isinstance(pr_url, str) or not URL_RE.fullmatch(pr_url)):
        raise CreativeCodePRPromotionContractError(
            "CreativeCodePRPromotionReceipt.pull_request_url must be a PulsePlate PR URL."
        )
    approved_by = payload.get("approved_by_login")
    if not isinstance(approved_by, str) or not LOGIN_RE.fullmatch(approved_by):
        raise CreativeCodePRPromotionContractError(
            "CreativeCodePRPromotionReceipt.approved_by_login must be a GitHub login."
        )
    partial_failure = payload.get("partial_failure")
    if partial_failure is not None and not isinstance(partial_failure, str):
        raise CreativeCodePRPromotionContractError("partial_failure must be null or string.")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", RECEIPT_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "promotion_id": _require_promotion_id(payload, "promotion_id", label=label),
        "receipt_id": _require_id(payload, "receipt_id", label=label),
        "plan_fingerprint": _require_fingerprint(payload, "plan_fingerprint", label=label),
        "validation_fingerprint": _require_fingerprint(
            payload, "validation_fingerprint", label=label
        ),
        "approval_id": _require_id(payload, "approval_id", label=label),
        "source_result_id": _require_id(payload, "source_result_id", label=label),
        "patch_fingerprint": _require_fingerprint(payload, "patch_fingerprint", label=label),
        "repository": _require_const(payload, "repository", TARGET_REPOSITORY, label=label),
        "base_branch": _require_const(payload, "base_branch", TARGET_BASE_BRANCH, label=label),
        "head_branch": require_safe_branch(
            payload.get("head_branch"), label=f"{label}.head_branch"
        ),
        "commit_sha": _require_sha(payload, "commit_sha", label=label),
        "pull_request_number": _require_int(
            payload, "pull_request_number", min_value=0, max_value=999999, label=label
        ),
        "pull_request_url": pr_url,
        "pull_request_state": payload.get("pull_request_state"),
        "pull_request_draft": _require_bool(
            payload, "pull_request_draft", expected=False, label=label
        ),
        "review_cycle_started": _require_any_bool(payload, "review_cycle_started", label=label),
        "approved_by_login": approved_by,
        "human_commit_author": _require_bool(
            payload, "human_commit_author", expected=True, label=label
        ),
        "runner_commit_author": _require_bool(
            payload, "runner_commit_author", expected=False, label=label
        ),
        "runner_coauthor_trailer_present": _require_bool(
            payload, "runner_coauthor_trailer_present", expected=True, label=label
        ),
        "ready_for_review_operation_used": _require_bool(
            payload, "ready_for_review_operation_used", expected=False, label=label
        ),
        "merge_ready": _require_bool(payload, "merge_ready", expected=False, label=label),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
        "partial_failure": partial_failure,
    }
    state = normalized["pull_request_state"]
    if state not in {"open", "partial_failure"}:
        raise CreativeCodePRPromotionContractError(
            "CreativeCodePRPromotionReceipt.pull_request_state is unsupported."
        )
    if state == "open":
        if partial_failure is not None:
            raise CreativeCodePRPromotionContractError(
                "open receipts must not record partial_failure."
            )
        if normalized["pull_request_number"] < 1 or normalized["pull_request_url"] == "":
            raise CreativeCodePRPromotionContractError(
                "open receipts require pull_request_number and pull_request_url."
            )
        if normalized["review_cycle_started"] is not True:
            raise CreativeCodePRPromotionContractError(
                "open receipts require review_cycle_started=true."
            )
    if state == "partial_failure" and not partial_failure:
        raise CreativeCodePRPromotionContractError(
            "partial failure receipts require partial_failure."
        )
    expected = build_asset_id(
        asset_type=RECEIPT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint_payload(_receipt_identity_payload(normalized)),
        upstream_ids=(
            normalized["promotion_id"],
            normalized["approval_id"],
            normalized["patch_fingerprint"],
        ),
    )
    if normalized["receipt_id"] != expected:
        raise CreativeCodePRPromotionContractError("receipt_id does not match receipt content.")
    _reject_leaks(normalized, label=label)
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate PR-3 creative-code PR promotion artifacts."
    )
    parser.add_argument("--validate-plan", help="Path to promotion plan JSON.")
    parser.add_argument("--validate-validation", help="Path to pre-open validation JSON.")
    parser.add_argument("--validate-approval", help="Path to approval JSON.")
    parser.add_argument("--validate-receipt", help="Path to promotion receipt JSON.")
    args = parser.parse_args(argv)

    validators = [
        (args.validate_plan, validate_creative_code_pr_promotion_plan),
        (args.validate_validation, validate_creative_code_pr_promotion_validation),
        (args.validate_approval, validate_creative_code_pr_promotion_approval),
        (args.validate_receipt, validate_creative_code_pr_promotion_receipt),
    ]
    selected = [(path, validator) for path, validator in validators if path]
    if len(selected) != 1:
        parser.error(
            "exactly one of --validate-plan, --validate-validation, "
            "--validate-approval, or --validate-receipt is required"
        )

    try:
        path, validator = selected[0]
        validator(read_json_object(path))
    except CreativeCodePRPromotionContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
