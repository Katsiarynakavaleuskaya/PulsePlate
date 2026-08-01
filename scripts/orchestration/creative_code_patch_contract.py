"""Validate PR-2 sandboxed creative-code candidate patch contracts.

PR-2 opens local candidate-patch generation only. The contract binds a human
admission request to an exact PR-1 specification bundle and records sanitized
result metadata after isolated generation/evaluation. It never grants shared
repository-write, PR, review-thread, promotion, runtime, Slack, or GitHub
authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from pathlib import PurePosixPath
import re
import sys
from typing import Any, Literal

from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    read_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.experiment_contract import (
    validate_capability_zero_attempt_observations,
    validate_failure_retry_observations,
    validate_immutable_oracles,
    validate_metrics,
    validate_mutable_candidate_surface,
)
from scripts.orchestration.creative_code_patch_workspace import (
    REPO_ROOT,
    CreativeCodePatchWorkspaceError,
    run_git,
)

SCHEMA_VERSION = "1.0"
REQUEST_TYPE = "creative_code_patch_build_request"
RESULT_TYPE = "creative_code_patch_result"
POLICY_VERSION = "creative-code-patch-builder-pr2"
SUCCESS_OUTPUT = "PASS: creative-code patch contract valid"

DEFAULT_MAX_CHANGED_FILES = 3
HARD_MAX_CHANGED_FILES = 5
HARD_MAX_DIFF_LINES = 800
HARD_MAX_CHANGED_LINES = 800
HARD_MAX_PATCH_BYTES = 524288
HARD_TIMEOUT_SECONDS = 600
GENERATION_ATTEMPTS = 1
CHANGED_LINE_METRIC = "numstat_added_plus_deleted_v1"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key)",
    re.IGNORECASE,
)
FAILURE_CLASSES = frozenset(
    {
        "timeout",
        "oom",
        "metric_regression",
        "guard_failure",
        "policy_violation",
        "unchanged_result",
        "capability_mismatch",
        "infra_flake",
    }
)
FailureClassCoherenceViolation = Literal[
    "accepted_with_failure_class",
    "rejected_without_failure_class",
]
TerminalOutcomeCoherenceViolation = Literal[
    "accepted_with_failure_class",
    "rejected_without_failure_class",
    "accepted_with_nonaccepted_runner",
    "accepted_without_runner_proof",
    "accepted_without_workspace_proof",
    "rejected_pre_oracle_without_runner_proof",
    "rejected_failure_mismatch",
]
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |raw[_ -]?(prompt|response|context)|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|oracle stdout|oracle stderr|"
    r"/Users/|/private/var/|/var/folders/|/tmp/|github_pat_|gh[psoru]_|"
    r"xox[abprs]-|sk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE | re.MULTILINE,
)


def classify_failure_class_coherence(
    *,
    status: str,
    failure_class: str | None,
) -> FailureClassCoherenceViolation | None:
    """Return the closed coherence violation for one terminal status pair."""

    if status == "accepted" and failure_class is not None:
        return "accepted_with_failure_class"
    if status == "rejected" and failure_class is None:
        return "rejected_without_failure_class"
    return None


def classify_terminal_outcome_coherence(
    *,
    status: str,
    failure_class: str | None,
    runner_status: str,
    runner_failure_class: str | None,
    runner_oracle_commands_configured: int,
    runner_oracle_commands_executed: int,
    runner_shared_tree_untouched: bool,
    workspace_summary: Mapping[str, Any],
) -> TerminalOutcomeCoherenceViolation | None:
    """Apply shared result/receipt coherence rules in canonical precedence."""

    failure_violation = classify_failure_class_coherence(
        status=status,
        failure_class=failure_class,
    )
    if failure_violation is not None:
        return failure_violation
    if status == "accepted" and runner_status != "accepted":
        return "accepted_with_nonaccepted_runner"
    if status == "accepted" and (
        runner_oracle_commands_configured < 1
        or runner_oracle_commands_executed != runner_oracle_commands_configured
        or not runner_shared_tree_untouched
    ):
        return "accepted_without_runner_proof"
    if status == "accepted" and not (
        workspace_summary["origin_removed"]
        and workspace_summary["checkout_destroyed"]
        and workspace_summary["shared_tree_untouched"]
    ):
        return "accepted_without_workspace_proof"
    if (
        status == "rejected"
        and failure_class in {"capability_mismatch", "policy_violation"}
        and runner_status != "rejected"
    ):
        return "rejected_pre_oracle_without_runner_proof"
    if (
        status == "rejected"
        and runner_status == "rejected"
        and failure_class != runner_failure_class
    ):
        return "rejected_failure_mismatch"
    return None


REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "request_type",
        "request_id",
        "idempotency_key",
        "policy_version",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "source_packet_id",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
        "human_admission",
        "authority",
        "executor",
        "allowed_existing_paths",
        "allowed_new_paths",
        "oracle_commands",
        "metrics",
        "budgets",
    }
)
HUMAN_ADMISSION_KEYS = frozenset({"decision", "approval_ref"})
AUTHORITY_KEYS = frozenset(
    {
        "generate_candidate_patch",
        "write_isolated_workspace",
        "evaluate_candidate_patch",
        "call_local_codex_exec",
        "write_repository",
        "write_shared_worktree",
        "create_branch",
        "push_branch",
        "open_pull_request",
        "open_draft_pr",
        "mark_ready_for_review",
        "resolve_review_threads",
        "merge",
        "release",
        "call_product_runtime_models",
        "call_arbitrary_network",
        "read_secrets",
        "modify_openapi_or_clients",
        "use_semantic_cache",
        "public_multi_tenant_use",
        "slack_github_authority_expansion",
    }
)
AUTHORITY_TRUE_KEYS = frozenset(
    {
        "generate_candidate_patch",
        "write_isolated_workspace",
        "evaluate_candidate_patch",
        "call_local_codex_exec",
    }
)
EXECUTOR_KEYS = frozenset(
    {
        "kind",
        "command_profile",
        "approval_policy",
        "sandbox",
        "command_network_access",
        "web_search",
        "apps_enabled",
        "ignore_user_config",
        "ephemeral",
        "json_events",
    }
)
LEGACY_BUDGET_KEYS = frozenset(
    {
        "generation_attempts",
        "generation_timeout_seconds",
        "evaluation_timeout_seconds",
        "max_changed_files",
        "max_diff_lines",
        "max_patch_bytes",
    }
)
CURRENT_BUDGET_KEYS = frozenset(
    {
        "generation_attempts",
        "generation_timeout_seconds",
        "evaluation_timeout_seconds",
        "max_changed_files",
        "max_changed_lines",
        "max_patch_bytes",
        "line_metric",
    }
)
RESULT_KEYS = frozenset(
    {
        "schema_version",
        "result_type",
        "result_id",
        "idempotency_key",
        "policy_version",
        "request_id",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
        "status",
        "failure_class",
        "changed_paths",
        "patch_summary",
        "workspace_summary",
        "runner_summary",
        "authority",
        "promotion_ready",
        "sanitized",
    }
)
LEGACY_PATCH_SUMMARY_KEYS = frozenset({"patch_fingerprint", "patch_bytes", "diff_lines"})
CURRENT_PATCH_SUMMARY_KEYS = frozenset(
    {
        "patch_fingerprint",
        "patch_bytes",
        "changed_lines",
        "serialized_patch_lines",
        "line_metric",
    }
)
LEGACY_PATCH_METADATA_KEYS = frozenset(
    {"changed_paths", "changed_path_statuses", "patch_fingerprint", "patch_bytes", "diff_lines"}
)
CURRENT_PATCH_METADATA_KEYS = frozenset(
    {
        "changed_paths",
        "changed_path_statuses",
        "patch_fingerprint",
        "patch_bytes",
        "changed_lines",
        "serialized_patch_lines",
        "line_metric",
    }
)
WORKSPACE_SUMMARY_KEYS = frozenset(
    {
        "detached_base_sha",
        "origin_removed",
        "checkout_destroyed",
        "shared_tree_untouched",
    }
)
RUNNER_SUMMARY_KEYS = frozenset(
    {
        "experiment_id",
        "status",
        "failure_class",
        "mutated_path_count",
        "oracle_commands_configured",
        "oracle_commands_executed",
        "attempts",
        "retries_consumed",
        "shared_tree_untouched",
        "runner_result_fingerprint",
        "runner_error_present",
        "runner_error_fingerprint",
    }
)
RESULT_AUTHORITY_KEYS = frozenset(
    {
        "candidate_patch_generated",
        "candidate_patch_evaluated",
        "write_repository",
        "open_pull_request",
        "resolve_review_threads",
        "merge",
        "promotion",
    }
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
    "docs/orchestration/",
    "docs/review/",
    "ios/",
    "frontend/",
    "node_modules/",
    "scripts/ci/",
    "tests/",
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
        "docs/orchestration",
        "docs/review",
        "frontend",
        "ios",
        "node_modules",
        "worktrees",
    }
)


class CreativeCodePatchContractError(ValueError):
    """Raised when a PR-2 patch-builder artifact violates local authority."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodePatchContractError(
                "creative-code patch contract has duplicate JSON key."
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_json_object(path: str) -> dict[str, Any]:
    """Read a JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodePatchContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodePatchContractError("Unable to read creative-code patch JSON.") from exc
    if not isinstance(payload, dict):
        raise CreativeCodePatchContractError("Creative-code patch artifact must be a JSON object.")
    return payload


def read_creative_code_patch_build_request(path: str) -> dict[str, Any]:
    """Read a PR-2 build request JSON object."""

    return read_json_object(path)


def read_creative_code_patch_result(path: str) -> dict[str, Any]:
    """Read a PR-2 sanitized result JSON object."""

    return read_json_object(path)


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
        raise CreativeCodePatchContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodePatchContractError(f"{label} has unsupported fields.")


def _exact_shape_family(
    payload: Mapping[str, Any],
    *,
    legacy_keys: frozenset[str],
    current_keys: frozenset[str],
    label: str,
) -> Literal["legacy", "current"]:
    keys = set(payload)
    if keys == legacy_keys:
        return "legacy"
    if keys == current_keys:
        return "current"
    raise CreativeCodePatchContractError(
        f"{label} must use one exact legacy or changed-line shape."
    )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodePatchContractError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a safe token.")
    return normalized


def _require_sha(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a 40-char git SHA.")
    return value


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a sha256 digest.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, expected: bool, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool) or value != expected:
        raise CreativeCodePatchContractError(f"{label}.{key} must be {expected}.")
    return value


def _require_any_bool(payload: Mapping[str, Any], key: str, *, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CreativeCodePatchContractError(f"{label}.{key} must be a boolean.")
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
        raise CreativeCodePatchContractError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodePatchContractError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _normalize_patch_path(raw_path: Any, *, label: str) -> str:
    if not isinstance(raw_path, str):
        raise CreativeCodePatchContractError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeCodePatchContractError(f"{label} must be non-empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeCodePatchContractError(f"{label} must not contain control characters.")
    if "\\" in value:
        raise CreativeCodePatchContractError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")):
        raise CreativeCodePatchContractError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeCodePatchContractError(f"{label} must not be a URL or scheme path.")
    path = PurePosixPath(value)
    if not path.parts or "." in path.parts or ".." in path.parts:
        raise CreativeCodePatchContractError(f"{label} must not contain traversal segments.")
    normalized = path.as_posix()
    if normalized in FORBIDDEN_PATCH_PATHS or any(
        normalized.startswith(prefix) for prefix in FORBIDDEN_PATCH_PREFIXES
    ):
        raise CreativeCodePatchContractError(f"{label} points to a forbidden patch surface.")
    return normalized


def parse_creative_code_numstat(
    output: str,
    *,
    expected_paths: Sequence[str],
) -> dict[str, Any]:
    """Parse one strict text-only Git numstat and bind it to exact paths."""

    if not isinstance(output, str) or not output:
        raise CreativeCodePatchContractError("git numstat output must be non-empty text.")
    normalized_expected: list[str] = []
    expected_seen: set[str] = set()
    for index, raw_path in enumerate(expected_paths):
        path = _normalize_patch_path(raw_path, label=f"expected_paths[{index}]")
        if path in expected_seen:
            raise CreativeCodePatchContractError("expected numstat paths must not duplicate.")
        expected_seen.add(path)
        normalized_expected.append(path)

    additions = 0
    deletions = 0
    parsed_paths: list[str] = []
    seen_paths: set[str] = set()
    for index, row in enumerate(output.splitlines()):
        if not row:
            raise CreativeCodePatchContractError("git numstat output contains a blank row.")
        fields = row.split("\t")
        if len(fields) != 3:
            raise CreativeCodePatchContractError(
                "git numstat rows must contain exactly three tab-separated fields."
            )
        added_text, deleted_text, raw_path = fields
        if added_text == "-" or deleted_text == "-":
            raise CreativeCodePatchContractError("candidate patch must not contain binary numstat.")
        if (
            re.fullmatch(r"[0-9]+", added_text, flags=re.ASCII) is None
            or re.fullmatch(r"[0-9]+", deleted_text, flags=re.ASCII) is None
        ):
            raise CreativeCodePatchContractError(
                "git numstat counts must be nonnegative ASCII decimal integers."
            )
        path = _normalize_patch_path(raw_path, label=f"numstat[{index}].path")
        if path in seen_paths:
            raise CreativeCodePatchContractError("git numstat output contains duplicate paths.")
        seen_paths.add(path)
        parsed_paths.append(path)
        additions += int(added_text)
        deletions += int(deleted_text)

    if set(parsed_paths) != set(normalized_expected) or len(parsed_paths) != len(
        normalized_expected
    ):
        raise CreativeCodePatchContractError(
            "git numstat paths must exactly match git name-status paths."
        )
    return {
        "additions": additions,
        "deletions": deletions,
        "changed_lines": additions + deletions,
        "changed_paths": sorted(parsed_paths),
    }


def measure_persisted_creative_code_patch(
    patch_text: str,
    *,
    expected_paths: Sequence[str],
) -> dict[str, Any]:
    """Measure one persisted patch without applying or mutating it."""

    try:
        numstat = run_git(
            ["apply", "--numstat"],
            cwd=REPO_ROOT,
            input_text=patch_text,
        ).stdout
    except CreativeCodePatchWorkspaceError as exc:
        raise CreativeCodePatchContractError(
            "candidate.patch could not be measured with git apply --numstat."
        ) from exc
    return parse_creative_code_numstat(numstat, expected_paths=expected_paths)


def _normalize_path_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodePatchContractError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodePatchContractError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        path = _normalize_patch_path(item, label=f"{label}.{key}[{index}]")
        if path in seen:
            raise CreativeCodePatchContractError(f"{label}.{key} must not contain duplicates.")
        seen.add(path)
        normalized.append(path)
    return normalized


def _path_matches_surface(path: str, surface: str) -> bool:
    return path == surface or path.startswith(f"{surface.rstrip('/')}/")


def _is_within_any(path: str, surfaces: Sequence[str]) -> bool:
    return any(_path_matches_surface(path, surface) for surface in surfaces)


def _paths_overlap(left: str, right: str) -> bool:
    return _path_matches_surface(left, right) or _path_matches_surface(right, left)


def _normalize_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodePatchContractError("CreativeCodePatchBuildRequest.authority is invalid.")
    _require_exact_keys(
        raw_authority, AUTHORITY_KEYS, label="CreativeCodePatchBuildRequest.authority"
    )
    normalized: dict[str, bool] = {}
    for key in AUTHORITY_KEYS:
        expected = key in AUTHORITY_TRUE_KEYS
        normalized[key] = _require_bool(
            raw_authority,
            key,
            expected=expected,
            label="CreativeCodePatchBuildRequest.authority",
        )
    return normalized


def _normalize_executor(raw_executor: Any) -> dict[str, Any]:
    if not isinstance(raw_executor, dict):
        raise CreativeCodePatchContractError("CreativeCodePatchBuildRequest.executor is invalid.")
    label = "CreativeCodePatchBuildRequest.executor"
    _require_exact_keys(raw_executor, EXECUTOR_KEYS, label=label)
    return {
        "kind": _require_const(raw_executor, "kind", "codex_exec", label=label),
        "command_profile": _require_const(
            raw_executor,
            "command_profile",
            "codex-cli-0.141.0-fixed-argv",
            label=label,
        ),
        "approval_policy": _require_const(raw_executor, "approval_policy", "never", label=label),
        "sandbox": _require_const(raw_executor, "sandbox", "workspace-write", label=label),
        "command_network_access": _require_bool(
            raw_executor,
            "command_network_access",
            expected=False,
            label=label,
        ),
        "web_search": _require_const(raw_executor, "web_search", "disabled", label=label),
        "apps_enabled": _require_bool(raw_executor, "apps_enabled", expected=False, label=label),
        "ignore_user_config": _require_bool(
            raw_executor,
            "ignore_user_config",
            expected=True,
            label=label,
        ),
        "ephemeral": _require_bool(raw_executor, "ephemeral", expected=True, label=label),
        "json_events": _require_bool(raw_executor, "json_events", expected=True, label=label),
    }


def _normalize_human_admission(raw_admission: Any) -> dict[str, str]:
    if not isinstance(raw_admission, dict):
        raise CreativeCodePatchContractError(
            "CreativeCodePatchBuildRequest.human_admission is invalid."
        )
    label = "CreativeCodePatchBuildRequest.human_admission"
    _require_exact_keys(raw_admission, HUMAN_ADMISSION_KEYS, label=label)
    return {
        "decision": _require_const(
            raw_admission,
            "decision",
            "approved_for_sandbox_generation",
            label=label,
        ),
        "approval_ref": _require_id(raw_admission, "approval_ref", label=label),
    }


def creative_code_budget_line_family(
    budgets: Mapping[str, Any],
) -> Literal["legacy", "current"]:
    """Return the exact line-measurement family without rewriting the payload."""

    return _exact_shape_family(
        budgets,
        legacy_keys=LEGACY_BUDGET_KEYS,
        current_keys=CURRENT_BUDGET_KEYS,
        label="CreativeCodePatchBuildRequest.budgets",
    )


def _normalize_budgets(raw_budgets: Any) -> dict[str, int | str]:
    if not isinstance(raw_budgets, dict):
        raise CreativeCodePatchContractError("CreativeCodePatchBuildRequest.budgets is invalid.")
    label = "CreativeCodePatchBuildRequest.budgets"
    family = creative_code_budget_line_family(raw_budgets)
    budgets: dict[str, int | str] = {
        "generation_attempts": _require_int(
            raw_budgets,
            "generation_attempts",
            min_value=GENERATION_ATTEMPTS,
            max_value=GENERATION_ATTEMPTS,
            label=label,
        ),
        "generation_timeout_seconds": _require_int(
            raw_budgets,
            "generation_timeout_seconds",
            min_value=1,
            max_value=HARD_TIMEOUT_SECONDS,
            label=label,
        ),
        "evaluation_timeout_seconds": _require_int(
            raw_budgets,
            "evaluation_timeout_seconds",
            min_value=1,
            max_value=HARD_TIMEOUT_SECONDS,
            label=label,
        ),
        "max_changed_files": _require_int(
            raw_budgets,
            "max_changed_files",
            min_value=1,
            max_value=HARD_MAX_CHANGED_FILES,
            label=label,
        ),
        "max_patch_bytes": _require_int(
            raw_budgets,
            "max_patch_bytes",
            min_value=1,
            max_value=HARD_MAX_PATCH_BYTES,
            label=label,
        ),
    }
    if family == "legacy":
        budgets["max_diff_lines"] = _require_int(
            raw_budgets,
            "max_diff_lines",
            min_value=1,
            max_value=HARD_MAX_DIFF_LINES,
            label=label,
        )
    else:
        budgets["max_changed_lines"] = _require_int(
            raw_budgets,
            "max_changed_lines",
            min_value=1,
            max_value=HARD_MAX_CHANGED_LINES,
            label=label,
        )
        budgets["line_metric"] = _require_const(
            raw_budgets,
            "line_metric",
            CHANGED_LINE_METRIC,
            label=label,
        )
    ordered = {key: budgets[key] for key in raw_budgets}
    if int(budgets["max_changed_files"]) > DEFAULT_MAX_CHANGED_FILES:
        # PR-2 permits hard-max expansion only when the request records it explicitly.
        # The budget field itself is the auditable expansion; no hidden defaults.
        return ordered
    return ordered


def _normalize_string_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodePatchContractError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodePatchContractError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeCodePatchContractError(f"{label}.{key}[{index}] must be a string.")
        text = item.strip()
        if not text:
            raise CreativeCodePatchContractError(f"{label}.{key}[{index}] must be non-empty.")
        if SECRET_RE.search(text) or LEAK_TEXT_RE.search(text):
            raise CreativeCodePatchContractError(f"{label}.{key}[{index}] contains unsafe text.")
        if text in seen:
            raise CreativeCodePatchContractError(f"{label}.{key} must not contain duplicates.")
        seen.add(text)
        normalized.append(text)
    return normalized


def _selected_variant(bundle: Mapping[str, Any]) -> dict[str, Any]:
    synthesis = bundle["synthesis"]
    if not isinstance(synthesis, dict):
        raise CreativeCodePatchContractError("source bundle synthesis is invalid.")
    selected_id = synthesis.get("selected_variant_id")
    selected_fingerprint = synthesis.get("selected_variant_fingerprint")
    if not selected_id or not selected_fingerprint:
        raise CreativeCodePatchContractError(
            "PR-2 requires a selected fully passed specification variant."
        )
    variants = bundle["variants"]
    if not isinstance(variants, list):
        raise CreativeCodePatchContractError("source bundle variants are invalid.")
    matches = [
        variant
        for variant in variants
        if isinstance(variant, dict)
        and variant.get("variant_id") == selected_id
        and variant.get("variant_fingerprint") == selected_fingerprint
    ]
    if len(matches) != 1:
        raise CreativeCodePatchContractError("selected variant binding is invalid.")
    reviews = bundle["skeptic_reviews"]
    if not isinstance(reviews, list):
        raise CreativeCodePatchContractError("source bundle skeptic reviews are invalid.")
    selected_reviews = [
        review
        for review in reviews
        if isinstance(review, dict) and review.get("variant_id") == selected_id
    ]
    if not selected_reviews or any(review.get("decision") != "pass" for review in selected_reviews):
        raise CreativeCodePatchContractError("selected variant must have only passing reviews.")
    return dict(matches[0])


def source_bundle_fingerprint(bundle: Mapping[str, Any]) -> str:
    """Return the PR-2 full-source-bundle fingerprint binding."""

    fingerprint = fingerprint_payload(bundle)
    if not isinstance(fingerprint, str):
        raise CreativeCodePatchContractError("source bundle fingerprint must be a string.")
    return fingerprint


def validate_creative_code_patch_build_request(
    payload: dict[str, Any],
    *,
    source_bundle: dict[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a PR-2 patch-builder request."""

    try:
        bundle = validate_creative_code_specification_bundle(source_bundle)
    except CreativeCodeSpecificationError as exc:
        raise CreativeCodePatchContractError(str(exc)) from exc
    _require_exact_keys(payload, REQUEST_KEYS, label="CreativeCodePatchBuildRequest")
    variant = _selected_variant(bundle)
    label = "CreativeCodePatchBuildRequest"
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "request_type": _require_const(payload, "request_type", REQUEST_TYPE, label=label),
        "request_id": _require_id(payload, "request_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "source_bundle_id": _require_const(
            payload,
            "source_bundle_id",
            bundle["bundle_id"],
            label=label,
        ),
        "source_bundle_fingerprint": _require_fingerprint(
            payload,
            "source_bundle_fingerprint",
            label=label,
        ),
        "source_packet_id": _require_const(
            payload,
            "source_packet_id",
            bundle["source_packet_id"],
            label=label,
        ),
        "selected_variant_id": _require_const(
            payload,
            "selected_variant_id",
            variant["variant_id"],
            label=label,
        ),
        "selected_variant_fingerprint": _require_const(
            payload,
            "selected_variant_fingerprint",
            variant["variant_fingerprint"],
            label=label,
        ),
        "base_commit_sha": _require_sha(payload, "base_commit_sha", label=label),
        "human_admission": _normalize_human_admission(payload["human_admission"]),
        "authority": _normalize_authority(payload["authority"]),
        "executor": _normalize_executor(payload["executor"]),
        "allowed_existing_paths": _normalize_path_list(
            payload,
            "allowed_existing_paths",
            label=label,
            allow_empty=True,
        ),
        "allowed_new_paths": _normalize_path_list(
            payload,
            "allowed_new_paths",
            label=label,
            allow_empty=True,
        ),
        "oracle_commands": _normalize_string_list(payload, "oracle_commands", label=label),
        "metrics": _normalize_string_list(payload, "metrics", label=label),
        "budgets": _normalize_budgets(payload["budgets"]),
    }
    actual_bundle_fingerprint = source_bundle_fingerprint(bundle)
    if normalized["source_bundle_fingerprint"] != actual_bundle_fingerprint:
        raise CreativeCodePatchContractError("source_bundle_fingerprint does not match bundle.")
    try:
        validate_immutable_oracles(normalized["oracle_commands"])
        validate_metrics(
            normalized["metrics"],
            baseline_reference="current-main",
            acceptance_threshold="strict_improvement",
        )
    except ValueError as exc:
        raise CreativeCodePatchContractError(str(exc)) from exc
    allowed_paths = sorted(
        set(normalized["allowed_existing_paths"]) | set(normalized["allowed_new_paths"])
    )
    if not allowed_paths:
        raise CreativeCodePatchContractError("At least one allowed patch path is required.")
    try:
        validate_mutable_candidate_surface(allowed_paths)
    except ValueError as exc:
        raise CreativeCodePatchContractError(str(exc)) from exc
    target_paths = variant["target_paths"]
    if not isinstance(target_paths, list):
        raise CreativeCodePatchContractError("selected variant target_paths are invalid.")
    invalid_allowed = [path for path in allowed_paths if not _is_within_any(path, target_paths)]
    if invalid_allowed:
        raise CreativeCodePatchContractError(
            "allowed patch paths must stay within selected variant target paths: "
            + ", ".join(invalid_allowed)
        )
    if len(allowed_paths) > normalized["budgets"]["max_changed_files"]:
        raise CreativeCodePatchContractError("allowed patch paths exceed max_changed_files budget.")
    for path in allowed_paths:
        for oracle_path in bundle["immutable_oracles"]:
            if isinstance(oracle_path, str) and _paths_overlap(path, oracle_path):
                raise CreativeCodePatchContractError(
                    "allowed patch paths must not overlap immutable oracle paths."
                )
    expected_id, expected_key = _build_request_identity(normalized)
    if normalized["request_id"] != expected_id:
        raise CreativeCodePatchContractError("request_id does not match request content.")
    if normalized["idempotency_key"] != expected_key:
        raise CreativeCodePatchContractError("idempotency_key does not match request content.")
    return normalized


def _request_identity_payload(request: Mapping[str, Any]) -> dict[str, Any]:
    return {key: request[key] for key in sorted(REQUEST_KEYS - {"request_id", "idempotency_key"})}


def _build_request_identity(request: Mapping[str, Any]) -> tuple[str, str]:
    fingerprint = fingerprint_payload(_request_identity_payload(request))
    upstream_ids = (
        str(request["source_bundle_id"]),
        str(request["source_bundle_fingerprint"]),
        str(request["selected_variant_fingerprint"]),
        str(request["base_commit_sha"]),
    )
    request_id = build_asset_id(
        asset_type="creative_code_patch_build_request",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type="creative_code_patch_build_request",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return request_id, idempotency_key


def build_creative_code_patch_build_request(
    *,
    source_bundle: dict[str, Any],
    base_commit_sha: str,
    approval_ref: str,
    allowed_existing_paths: list[str],
    allowed_new_paths: list[str] | None = None,
    oracle_commands: list[str],
    metrics: list[str],
    budgets: dict[str, int | str],
) -> dict[str, Any]:
    """Build a deterministic PR-2 request from a validated PR-1 bundle."""

    bundle = validate_creative_code_specification_bundle(source_bundle)
    variant = _selected_variant(bundle)
    normalized_budgets = _normalize_budgets(budgets)
    if creative_code_budget_line_family(normalized_budgets) != "current":
        raise CreativeCodePatchContractError(
            "new patch requests must use the changed-line budget shape."
        )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "request_type": REQUEST_TYPE,
        "request_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "source_bundle_id": bundle["bundle_id"],
        "source_bundle_fingerprint": source_bundle_fingerprint(bundle),
        "source_packet_id": bundle["source_packet_id"],
        "selected_variant_id": variant["variant_id"],
        "selected_variant_fingerprint": variant["variant_fingerprint"],
        "base_commit_sha": base_commit_sha,
        "human_admission": {
            "decision": "approved_for_sandbox_generation",
            "approval_ref": approval_ref,
        },
        "authority": {key: key in AUTHORITY_TRUE_KEYS for key in sorted(AUTHORITY_KEYS)},
        "executor": {
            "kind": "codex_exec",
            "command_profile": "codex-cli-0.141.0-fixed-argv",
            "approval_policy": "never",
            "sandbox": "workspace-write",
            "command_network_access": False,
            "web_search": "disabled",
            "apps_enabled": False,
            "ignore_user_config": True,
            "ephemeral": True,
            "json_events": True,
        },
        "allowed_existing_paths": allowed_existing_paths,
        "allowed_new_paths": allowed_new_paths or [],
        "oracle_commands": oracle_commands,
        "metrics": metrics,
        "budgets": normalized_budgets,
    }
    request_id, idempotency_key = _build_request_identity(payload)
    payload["request_id"] = request_id
    payload["idempotency_key"] = idempotency_key
    normalized = validate_creative_code_patch_build_request(payload, source_bundle=bundle)
    return normalized


def _safe_runner_summary(runner_result: Mapping[str, Any]) -> dict[str, Any]:
    budget_observations = runner_result.get("budget_observations", {})
    if not isinstance(budget_observations, dict):
        raise CreativeCodePatchContractError(
            "runner_result.budget_observations must be a JSON object."
        )
    oracle_results = runner_result.get("oracle_results", [])
    if not isinstance(oracle_results, list):
        raise CreativeCodePatchContractError("runner_result.oracle_results must be an array.")
    mutated_paths = runner_result.get("mutated_paths", [])
    if not isinstance(mutated_paths, list) or not all(
        isinstance(path, str) for path in mutated_paths
    ):
        raise CreativeCodePatchContractError("runner_result.mutated_paths must be a string array.")
    experiment_id = runner_result.get("experiment_id")
    if not isinstance(experiment_id, str):
        raise CreativeCodePatchContractError("runner_result.experiment_id must be a string.")
    status = runner_result.get("status", "rejected")
    if not isinstance(status, str):
        raise CreativeCodePatchContractError("runner_result.status must be a string.")
    failure_class = runner_result.get("failure_class")
    if failure_class is not None and not isinstance(failure_class, str):
        raise CreativeCodePatchContractError("runner_result.failure_class must be null or string.")
    shared_tree_untouched = runner_result.get("shared_tree_untouched")
    if not isinstance(shared_tree_untouched, bool):
        raise CreativeCodePatchContractError(
            "runner_result.shared_tree_untouched must be a boolean."
        )
    oracle_commands_configured = budget_observations.get("oracle_commands_configured", 0)
    attempts = budget_observations.get("attempts", 0)
    retries_consumed = budget_observations.get("retries_consumed", 0)
    for key, value in (
        ("oracle_commands_configured", oracle_commands_configured),
        ("attempts", attempts),
        ("retries_consumed", retries_consumed),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CreativeCodePatchContractError(
                f"runner_result.budget_observations.{key} must be an integer."
            )
    runner_error = budget_observations.get("runner_error")
    if runner_error is not None and not isinstance(runner_error, str):
        raise CreativeCodePatchContractError(
            "runner_result.budget_observations.runner_error must be null or string."
        )
    runner_error_text = runner_error or ""
    return {
        "experiment_id": experiment_id,
        "status": status,
        "failure_class": failure_class,
        "mutated_path_count": len(mutated_paths),
        "oracle_commands_configured": oracle_commands_configured,
        "oracle_commands_executed": len(oracle_results),
        "attempts": attempts,
        "retries_consumed": retries_consumed,
        "shared_tree_untouched": shared_tree_untouched,
        "runner_result_fingerprint": fingerprint_payload(runner_result),
        "runner_error_present": bool(runner_error_text),
        "runner_error_fingerprint": (
            fingerprint_payload({"runner_error": runner_error_text}) if runner_error_text else None
        ),
    }


def build_creative_code_patch_result(
    *,
    request: Mapping[str, Any],
    changed_paths: list[str],
    patch_fingerprint: str,
    patch_bytes: int,
    runner_result: Mapping[str, Any],
    checkout_destroyed: bool,
    origin_removed: bool,
    shared_tree_untouched: bool,
    failure_class: str | None = None,
    diff_lines: int | None = None,
    changed_lines: int | None = None,
    serialized_patch_lines: int | None = None,
    line_metric: str | None = None,
) -> dict[str, Any]:
    """Build a sanitized PR-2 patch result from local metadata and runner output."""

    runner_summary = _safe_runner_summary(runner_result)
    status = (
        "accepted"
        if runner_summary["status"] == "accepted" and failure_class is None
        else "rejected"
    )
    result_failure = failure_class or runner_summary["failure_class"]
    if not checkout_destroyed or not origin_removed or not shared_tree_untouched:
        status = "rejected"
        result_failure = result_failure or "infra_flake"
    line_family = creative_code_budget_line_family(request["budgets"])
    if line_family == "legacy":
        raise CreativeCodePatchContractError(
            "legacy patch requests are read-only and cannot author new results."
        )
    if (
        diff_lines is not None
        or not isinstance(changed_lines, int)
        or isinstance(changed_lines, bool)
        or not isinstance(serialized_patch_lines, int)
        or isinstance(serialized_patch_lines, bool)
        or line_metric != CHANGED_LINE_METRIC
    ):
        raise CreativeCodePatchContractError(
            "current results require changed_lines, serialized_patch_lines, and line_metric."
        )
    patch_summary = {
        "patch_fingerprint": patch_fingerprint,
        "patch_bytes": patch_bytes,
        "changed_lines": changed_lines,
        "serialized_patch_lines": serialized_patch_lines,
        "line_metric": line_metric,
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_type": RESULT_TYPE,
        "result_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "source_bundle_fingerprint": request["source_bundle_fingerprint"],
        "selected_variant_id": request["selected_variant_id"],
        "selected_variant_fingerprint": request["selected_variant_fingerprint"],
        "base_commit_sha": request["base_commit_sha"],
        "status": status,
        "failure_class": result_failure,
        "changed_paths": sorted(changed_paths),
        "patch_summary": patch_summary,
        "workspace_summary": {
            "detached_base_sha": request["base_commit_sha"],
            "origin_removed": origin_removed,
            "checkout_destroyed": checkout_destroyed,
            "shared_tree_untouched": shared_tree_untouched,
        },
        "runner_summary": runner_summary,
        "authority": {
            "candidate_patch_generated": True,
            "candidate_patch_evaluated": True,
            "write_repository": False,
            "open_pull_request": False,
            "resolve_review_threads": False,
            "merge": False,
            "promotion": False,
        },
        "promotion_ready": False,
        "sanitized": True,
    }
    result_id, idempotency_key = _build_result_identity(result)
    result["result_id"] = result_id
    result["idempotency_key"] = idempotency_key
    return validate_creative_code_patch_result(result)


def _result_identity_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in sorted(RESULT_KEYS - {"result_id", "idempotency_key"})}


def _build_result_identity(result: Mapping[str, Any]) -> tuple[str, str]:
    fingerprint = fingerprint_payload(_result_identity_payload(result))
    upstream_ids = (
        str(result["request_id"]),
        str(result["source_bundle_fingerprint"]),
        str(result["selected_variant_fingerprint"]),
        str(result["base_commit_sha"]),
    )
    result_id = build_asset_id(
        asset_type="creative_code_patch_result",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type="creative_code_patch_result",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return result_id, idempotency_key


def _reject_result_leaks(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise CreativeCodePatchContractError(f"{label} contains unsafe result text.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_result_leaks(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_result_leaks(item, label=f"{label}.{key}")


def validate_creative_code_patch_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate sanitized PR-2 result metadata."""

    label = "CreativeCodePatchResult"
    _require_exact_keys(payload, RESULT_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "result_type": _require_const(payload, "result_type", RESULT_TYPE, label=label),
        "result_id": _require_id(payload, "result_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "request_id": _require_id(payload, "request_id", label=label),
        "source_bundle_id": _require_id(payload, "source_bundle_id", label=label),
        "source_bundle_fingerprint": _require_fingerprint(
            payload,
            "source_bundle_fingerprint",
            label=label,
        ),
        "selected_variant_id": _require_id(payload, "selected_variant_id", label=label),
        "selected_variant_fingerprint": _require_fingerprint(
            payload,
            "selected_variant_fingerprint",
            label=label,
        ),
        "base_commit_sha": _require_sha(payload, "base_commit_sha", label=label),
        "status": _require_token(payload, "status", label=label),
        "failure_class": payload.get("failure_class"),
        "changed_paths": _normalize_path_list(payload, "changed_paths", label=label),
        "patch_summary": payload["patch_summary"],
        "workspace_summary": payload["workspace_summary"],
        "runner_summary": payload["runner_summary"],
        "authority": payload["authority"],
        "promotion_ready": _require_bool(
            payload,
            "promotion_ready",
            expected=False,
            label=label,
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["status"] not in {"accepted", "rejected"}:
        raise CreativeCodePatchContractError("CreativeCodePatchResult.status is unsupported.")
    if normalized["failure_class"] is not None and not isinstance(normalized["failure_class"], str):
        raise CreativeCodePatchContractError(
            "CreativeCodePatchResult.failure_class must be null or string."
        )
    if (
        normalized["failure_class"] is not None
        and normalized["failure_class"] not in FAILURE_CLASSES
    ):
        raise CreativeCodePatchContractError(
            "CreativeCodePatchResult.failure_class is unsupported."
        )
    normalized["patch_summary"] = _validate_patch_summary(normalized["patch_summary"])
    workspace_summary = _validate_workspace_summary(normalized["workspace_summary"])
    runner_summary = _validate_runner_summary(normalized["runner_summary"])
    _validate_result_authority(normalized["authority"])
    if workspace_summary["detached_base_sha"] != normalized["base_commit_sha"]:
        raise CreativeCodePatchContractError(
            "workspace_summary.detached_base_sha must match base_commit_sha."
        )
    coherence_violation = classify_terminal_outcome_coherence(
        status=normalized["status"],
        failure_class=normalized["failure_class"],
        runner_status=runner_summary["status"],
        runner_failure_class=runner_summary["failure_class"],
        runner_oracle_commands_configured=runner_summary["oracle_commands_configured"],
        runner_oracle_commands_executed=runner_summary["oracle_commands_executed"],
        runner_shared_tree_untouched=runner_summary["shared_tree_untouched"],
        workspace_summary=workspace_summary,
    )
    if coherence_violation == "accepted_with_failure_class":
        raise CreativeCodePatchContractError("accepted results must not have failure_class.")
    if coherence_violation == "rejected_without_failure_class":
        raise CreativeCodePatchContractError("rejected results require failure_class.")
    if coherence_violation == "accepted_with_nonaccepted_runner":
        raise CreativeCodePatchContractError("accepted results require an accepted runner summary.")
    if coherence_violation == "accepted_without_runner_proof":
        raise CreativeCodePatchContractError(
            "accepted results require complete runner oracle and shared-tree proof."
        )
    if coherence_violation == "accepted_without_workspace_proof":
        raise CreativeCodePatchContractError("accepted results require full workspace proof.")
    if coherence_violation == "rejected_pre_oracle_without_runner_proof":
        raise CreativeCodePatchContractError(
            "terminal pre-oracle rejected results require a rejected runner summary."
        )
    if coherence_violation == "rejected_failure_mismatch":
        raise CreativeCodePatchContractError(
            "rejected result and runner summary failure_class values must match."
        )
    for observed_failure, failure_label in (
        (normalized["failure_class"], "CreativeCodePatchResult.runner_summary"),
        (runner_summary["failure_class"], "runner_summary"),
    ):
        try:
            validate_failure_retry_observations(
                failure_class=observed_failure,
                attempts=runner_summary["attempts"],
                retries_consumed=runner_summary["retries_consumed"],
                runner_error_present=runner_summary["runner_error_present"],
                label=failure_label,
            )
        except ValueError as exc:
            raise CreativeCodePatchContractError(str(exc)) from exc
    try:
        validate_capability_zero_attempt_observations(
            failure_class=runner_summary["failure_class"],
            attempts=runner_summary["attempts"],
            mutated_path_count=runner_summary["mutated_path_count"],
            oracle_commands_executed=runner_summary["oracle_commands_executed"],
            label="runner_summary",
        )
    except ValueError as exc:
        raise CreativeCodePatchContractError(str(exc)) from exc
    _reject_result_leaks(normalized, label=label)
    expected_id, expected_key = _build_result_identity(normalized)
    if normalized["result_id"] != expected_id:
        raise CreativeCodePatchContractError("result_id does not match result content.")
    if normalized["idempotency_key"] != expected_key:
        raise CreativeCodePatchContractError("idempotency_key does not match result content.")
    return normalized


def _patch_changed_path_statuses(patch_text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    current_path: str | None = None
    current_status = "M"

    def flush_current_path() -> None:
        nonlocal current_path, current_status
        if current_path is None:
            return
        statuses[current_path] = current_status
        current_path = None
        current_status = "M"

    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            flush_current_path()
            parts = line.split()
            if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                raise CreativeCodePatchContractError(
                    "candidate.patch contains unsupported diff header."
                )
            old_path = parts[2][2:]
            new_path = parts[3][2:]
            if old_path != new_path:
                raise CreativeCodePatchContractError("candidate.patch renames are not supported.")
            path = Path(new_path)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in new_path
                or new_path in {"", "."}
            ):
                raise CreativeCodePatchContractError(
                    "candidate.patch contains unsafe changed path."
                )
            current_path = new_path
            current_status = "M"
            continue

        if current_path is None:
            continue
        if line.startswith("new file mode "):
            current_status = "A"
        elif (
            line.startswith("deleted file mode ")
            or line.startswith("rename ")
            or line.startswith("copy ")
        ):
            raise CreativeCodePatchContractError(
                "candidate.patch contains unsupported diff status."
            )

    flush_current_path()
    if not statuses:
        raise CreativeCodePatchContractError(
            "candidate.patch must contain at least one diff header."
        )
    return dict(sorted(statuses.items()))


def _patch_changed_paths(patch_text: str) -> list[str]:
    return sorted(_patch_changed_path_statuses(patch_text))


def creative_code_patch_changed_path_statuses(patch_text: str) -> dict[str, str]:
    """Return the existing strict path/status projection for persisted patch rechecks."""

    return _patch_changed_path_statuses(patch_text)


def validate_creative_code_patch_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate PR-2 patch metadata sidecars with an exact sanitized shape."""

    label = "patch_metadata"
    family = _exact_shape_family(
        payload,
        legacy_keys=LEGACY_PATCH_METADATA_KEYS,
        current_keys=CURRENT_PATCH_METADATA_KEYS,
        label=label,
    )
    changed_paths = _normalize_path_list(payload, "changed_paths", label=label)
    statuses = payload["changed_path_statuses"]
    if not isinstance(statuses, dict):
        raise CreativeCodePatchContractError("patch_metadata.changed_path_statuses is invalid.")
    if set(statuses) != set(changed_paths):
        raise CreativeCodePatchContractError(
            "patch_metadata.changed_path_statuses must match changed_paths."
        )
    normalized_statuses: dict[str, str] = {}
    for path in changed_paths:
        status = statuses[path]
        if status not in {"A", "M"}:
            raise CreativeCodePatchContractError(
                "patch_metadata.changed_path_statuses values must be A or M."
            )
        normalized_statuses[path] = status
    normalized: dict[str, Any] = {
        "changed_paths": changed_paths,
        "changed_path_statuses": normalized_statuses,
        "patch_fingerprint": _require_fingerprint(payload, "patch_fingerprint", label=label),
        "patch_bytes": _require_int(
            payload,
            "patch_bytes",
            min_value=1,
            max_value=HARD_MAX_PATCH_BYTES,
            label=label,
        ),
    }
    if family == "legacy":
        normalized["diff_lines"] = _require_int(
            payload,
            "diff_lines",
            min_value=1,
            max_value=HARD_MAX_DIFF_LINES,
            label=label,
        )
    else:
        normalized["changed_lines"] = _require_int(
            payload,
            "changed_lines",
            min_value=1,
            max_value=HARD_MAX_CHANGED_LINES,
            label=label,
        )
        normalized["serialized_patch_lines"] = _require_int(
            payload,
            "serialized_patch_lines",
            min_value=1,
            max_value=HARD_MAX_PATCH_BYTES,
            label=label,
        )
        normalized["line_metric"] = _require_const(
            payload,
            "line_metric",
            CHANGED_LINE_METRIC,
            label=label,
        )
    _reject_result_leaks(normalized, label=label)
    return normalized


def _validate_patch_paths_against_request_authority(
    patch_changed_path_statuses: Mapping[str, str],
    *,
    request: Mapping[str, Any],
) -> None:
    allowed_existing = set(request["allowed_existing_paths"])
    allowed_new = set(request["allowed_new_paths"])
    allowed_paths = allowed_existing | allowed_new
    changed_paths = sorted(patch_changed_path_statuses)
    if len(changed_paths) > request["budgets"]["max_changed_files"]:
        raise CreativeCodePatchContractError(
            "candidate.patch exceeds request max_changed_files budget."
        )
    for path, status in patch_changed_path_statuses.items():
        if path not in allowed_paths:
            raise CreativeCodePatchContractError(
                "candidate.patch touches path outside PR-2 request allowlist."
            )
        if status == "A" and path not in allowed_new:
            raise CreativeCodePatchContractError(
                "candidate.patch adds path outside PR-2 request new-path allowlist."
            )
        if status == "M" and path not in allowed_existing:
            raise CreativeCodePatchContractError(
                "candidate.patch modifies path outside PR-2 request existing-path allowlist."
            )


def validate_creative_code_patch_run_sidecars(
    *,
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    patch_text: str,
    selected_variant: Mapping[str, Any],
    patch_metadata: Mapping[str, Any],
    require_accepted: bool,
) -> dict[str, Any]:
    """Validate canonical PR-2 sidecars without granting promotion authority."""

    if require_accepted:
        if result["status"] != "accepted":
            raise CreativeCodePatchContractError("PR-2 result must be accepted.")
        if result["failure_class"] is not None:
            raise CreativeCodePatchContractError(
                "accepted PR-2 result must not have failure_class."
            )
        runner_summary = result["runner_summary"]
        if runner_summary["status"] != "accepted" or runner_summary["failure_class"] is not None:
            raise CreativeCodePatchContractError("PR-2 runner summary must be accepted.")
        if runner_summary["oracle_commands_configured"] < 1:
            raise CreativeCodePatchContractError("PR-2 runner must configure at least one oracle.")
        if (
            runner_summary["oracle_commands_executed"]
            != runner_summary["oracle_commands_configured"]
        ):
            raise CreativeCodePatchContractError(
                "PR-2 runner must execute every configured oracle."
            )
        if not runner_summary["shared_tree_untouched"]:
            raise CreativeCodePatchContractError("PR-2 runner must leave shared tree untouched.")
    workspace_summary = result["workspace_summary"]
    if require_accepted and not (
        workspace_summary["origin_removed"]
        and workspace_summary["checkout_destroyed"]
        and workspace_summary["shared_tree_untouched"]
    ):
        raise CreativeCodePatchContractError("PR-2 result requires full checkout cleanup proof.")
    if result["promotion_ready"] is not False:
        raise CreativeCodePatchContractError("PR-2 result must preserve promotion_ready=false.")
    if not result["sanitized"]:
        raise CreativeCodePatchContractError("PR-2 result must be sanitized.")
    for key in (
        "request_id",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
    ):
        if result[key] != request[key]:
            raise CreativeCodePatchContractError(f"PR-2 lineage mismatch for {key}.")
    if selected_variant.get("variant_id") != request["selected_variant_id"]:
        raise CreativeCodePatchContractError("selected_variant_id does not match PR-2 request.")
    if selected_variant.get("variant_fingerprint") != request["selected_variant_fingerprint"]:
        raise CreativeCodePatchContractError(
            "selected_variant_fingerprint does not match PR-2 request."
        )
    patch_fingerprint = fingerprint_payload({"candidate_patch": patch_text})
    patch_bytes = len(patch_text.encode("utf-8"))
    serialized_patch_lines = len(patch_text.splitlines())
    patch_summary = result["patch_summary"]
    if patch_summary["patch_fingerprint"] != patch_fingerprint:
        raise CreativeCodePatchContractError("candidate.patch fingerprint mismatch.")
    if patch_summary["patch_bytes"] != patch_bytes:
        raise CreativeCodePatchContractError("candidate.patch byte count mismatch.")
    if not result["changed_paths"]:
        raise CreativeCodePatchContractError("PR-2 result must include changed paths.")
    patch_changed_path_statuses = _patch_changed_path_statuses(patch_text)
    patch_changed_paths = sorted(patch_changed_path_statuses)
    if patch_changed_paths != sorted(result["changed_paths"]):
        raise CreativeCodePatchContractError("candidate.patch changed paths mismatch.")
    _validate_patch_paths_against_request_authority(
        patch_changed_path_statuses,
        request=request,
    )
    metadata = validate_creative_code_patch_metadata(patch_metadata)
    if metadata["changed_paths"] != result["changed_paths"]:
        raise CreativeCodePatchContractError("patch_metadata changed paths mismatch.")
    if metadata["changed_path_statuses"] != patch_changed_path_statuses:
        raise CreativeCodePatchContractError("patch_metadata changed_path_statuses mismatch.")
    request_family = creative_code_budget_line_family(request["budgets"])
    summary_family = _exact_shape_family(
        patch_summary,
        legacy_keys=LEGACY_PATCH_SUMMARY_KEYS,
        current_keys=CURRENT_PATCH_SUMMARY_KEYS,
        label="patch_summary",
    )
    metadata_family = _exact_shape_family(
        metadata,
        legacy_keys=LEGACY_PATCH_METADATA_KEYS,
        current_keys=CURRENT_PATCH_METADATA_KEYS,
        label="patch_metadata",
    )
    if len({request_family, summary_family, metadata_family}) != 1:
        raise CreativeCodePatchContractError(
            "request, result, and patch metadata line-measurement families must match."
        )
    expected_measurements: dict[str, Any]
    if request_family == "legacy":
        if patch_summary["diff_lines"] != serialized_patch_lines:
            raise CreativeCodePatchContractError("candidate.patch diff line count mismatch.")
        if serialized_patch_lines > request["budgets"]["max_diff_lines"]:
            raise CreativeCodePatchContractError(
                "candidate.patch exceeds request max_diff_lines budget."
            )
        expected_measurements = {"diff_lines": serialized_patch_lines}
    else:
        measured = measure_persisted_creative_code_patch(
            patch_text,
            expected_paths=patch_changed_paths,
        )
        changed_lines = measured["changed_lines"]
        if changed_lines > request["budgets"]["max_changed_lines"]:
            raise CreativeCodePatchContractError(
                "candidate.patch exceeds request max_changed_lines budget."
            )
        expected_measurements = {
            "changed_lines": changed_lines,
            "serialized_patch_lines": serialized_patch_lines,
            "line_metric": CHANGED_LINE_METRIC,
        }
        for key, expected in expected_measurements.items():
            if patch_summary[key] != expected:
                raise CreativeCodePatchContractError(f"candidate.patch {key} measurement mismatch.")
    if patch_bytes > request["budgets"]["max_patch_bytes"]:
        raise CreativeCodePatchContractError("candidate.patch exceeds request max_patch_bytes.")
    expected_metadata = {
        "patch_fingerprint": patch_fingerprint,
        "patch_bytes": patch_bytes,
        **expected_measurements,
    }
    for key, expected in expected_metadata.items():
        if metadata[key] != expected:
            raise CreativeCodePatchContractError(f"patch_metadata {key} mismatch.")
    return {
        "patch_fingerprint": patch_fingerprint,
        "patch_bytes": patch_bytes,
        **expected_measurements,
    }


def _validate_patch_summary(raw_summary: Any) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeCodePatchContractError("patch_summary must be a JSON object.")
    family = _exact_shape_family(
        raw_summary,
        legacy_keys=LEGACY_PATCH_SUMMARY_KEYS,
        current_keys=CURRENT_PATCH_SUMMARY_KEYS,
        label="patch_summary",
    )
    normalized: dict[str, Any] = {
        "patch_fingerprint": _require_fingerprint(
            raw_summary,
            "patch_fingerprint",
            label="patch_summary",
        ),
        "patch_bytes": _require_int(
            raw_summary,
            "patch_bytes",
            min_value=1,
            max_value=HARD_MAX_PATCH_BYTES,
            label="patch_summary",
        ),
    }
    if family == "legacy":
        normalized["diff_lines"] = _require_int(
            raw_summary,
            "diff_lines",
            min_value=1,
            max_value=HARD_MAX_DIFF_LINES,
            label="patch_summary",
        )
    else:
        normalized["changed_lines"] = _require_int(
            raw_summary,
            "changed_lines",
            min_value=1,
            max_value=HARD_MAX_CHANGED_LINES,
            label="patch_summary",
        )
        normalized["serialized_patch_lines"] = _require_int(
            raw_summary,
            "serialized_patch_lines",
            min_value=1,
            max_value=HARD_MAX_PATCH_BYTES,
            label="patch_summary",
        )
        normalized["line_metric"] = _require_const(
            raw_summary,
            "line_metric",
            CHANGED_LINE_METRIC,
            label="patch_summary",
        )
    return normalized


def _validate_workspace_summary(raw_summary: Any) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeCodePatchContractError("workspace_summary must be a JSON object.")
    _require_exact_keys(raw_summary, WORKSPACE_SUMMARY_KEYS, label="workspace_summary")
    return {
        "detached_base_sha": _require_sha(
            raw_summary,
            "detached_base_sha",
            label="workspace_summary",
        ),
        "origin_removed": _require_any_bool(
            raw_summary,
            "origin_removed",
            label="workspace_summary",
        ),
        "checkout_destroyed": _require_any_bool(
            raw_summary,
            "checkout_destroyed",
            label="workspace_summary",
        ),
        "shared_tree_untouched": _require_any_bool(
            raw_summary,
            "shared_tree_untouched",
            label="workspace_summary",
        ),
    }


def _validate_runner_summary(raw_summary: Any) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeCodePatchContractError("runner_summary must be a JSON object.")
    _require_exact_keys(raw_summary, RUNNER_SUMMARY_KEYS, label="runner_summary")
    status = _require_token(raw_summary, "status", label="runner_summary")
    if status not in {"accepted", "rejected"}:
        raise CreativeCodePatchContractError("runner_summary.status is unsupported.")
    failure_class = raw_summary["failure_class"]
    if failure_class is not None and not isinstance(failure_class, str):
        raise CreativeCodePatchContractError("runner_summary.failure_class must be null or string.")
    if failure_class is not None and failure_class not in FAILURE_CLASSES:
        raise CreativeCodePatchContractError("runner_summary.failure_class is unsupported.")
    coherence_violation = classify_failure_class_coherence(
        status=status,
        failure_class=failure_class,
    )
    if coherence_violation == "accepted_with_failure_class":
        raise CreativeCodePatchContractError(
            "accepted runner summaries must not have failure_class."
        )
    if coherence_violation == "rejected_without_failure_class":
        raise CreativeCodePatchContractError("rejected runner summaries require failure_class.")
    runner_error_fingerprint = raw_summary["runner_error_fingerprint"]
    runner_error_present = _require_any_bool(
        raw_summary,
        "runner_error_present",
        label="runner_summary",
    )
    if runner_error_present:
        if not isinstance(runner_error_fingerprint, str) or not SHA256_RE.fullmatch(
            runner_error_fingerprint
        ):
            raise CreativeCodePatchContractError(
                "runner_summary.runner_error_fingerprint must be a sha256 digest."
            )
    elif runner_error_fingerprint is not None:
        raise CreativeCodePatchContractError(
            "runner_summary.runner_error_fingerprint must be null when no runner error is present."
        )
    attempts = _require_int(
        raw_summary,
        "attempts",
        min_value=0,
        max_value=3,
        label="runner_summary",
    )
    retries_consumed = _require_int(
        raw_summary,
        "retries_consumed",
        min_value=0,
        max_value=2,
        label="runner_summary",
    )
    return {
        "experiment_id": _require_id(raw_summary, "experiment_id", label="runner_summary"),
        "status": status,
        "failure_class": failure_class,
        "mutated_path_count": _require_int(
            raw_summary,
            "mutated_path_count",
            min_value=0,
            max_value=HARD_MAX_CHANGED_FILES,
            label="runner_summary",
        ),
        "oracle_commands_configured": _require_int(
            raw_summary,
            "oracle_commands_configured",
            min_value=0,
            max_value=20,
            label="runner_summary",
        ),
        "oracle_commands_executed": _require_int(
            raw_summary,
            "oracle_commands_executed",
            min_value=0,
            max_value=20,
            label="runner_summary",
        ),
        "attempts": attempts,
        "retries_consumed": retries_consumed,
        "shared_tree_untouched": _require_any_bool(
            raw_summary,
            "shared_tree_untouched",
            label="runner_summary",
        ),
        "runner_result_fingerprint": _require_fingerprint(
            raw_summary,
            "runner_result_fingerprint",
            label="runner_summary",
        ),
        "runner_error_present": runner_error_present,
        "runner_error_fingerprint": runner_error_fingerprint,
    }


def _validate_result_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodePatchContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, RESULT_AUTHORITY_KEYS, label="authority")
    return {
        "candidate_patch_generated": _require_bool(
            raw_authority,
            "candidate_patch_generated",
            expected=True,
            label="authority",
        ),
        "candidate_patch_evaluated": _require_bool(
            raw_authority,
            "candidate_patch_evaluated",
            expected=True,
            label="authority",
        ),
        "write_repository": _require_bool(
            raw_authority,
            "write_repository",
            expected=False,
            label="authority",
        ),
        "open_pull_request": _require_bool(
            raw_authority,
            "open_pull_request",
            expected=False,
            label="authority",
        ),
        "resolve_review_threads": _require_bool(
            raw_authority,
            "resolve_review_threads",
            expected=False,
            label="authority",
        ),
        "merge": _require_bool(raw_authority, "merge", expected=False, label="authority"),
        "promotion": _require_bool(raw_authority, "promotion", expected=False, label="authority"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PR-2 creative-code patch artifacts.")
    parser.add_argument("--validate-request", help="Path to CreativeCodePatchBuildRequest JSON.")
    parser.add_argument(
        "--source-bundle", help="Path to PR-1 CreativeCodeSpecificationBundle JSON."
    )
    parser.add_argument("--validate-result", help="Path to CreativeCodePatchResult JSON.")
    args = parser.parse_args(argv)

    try:
        if args.validate_request:
            if not args.source_bundle:
                raise CreativeCodePatchContractError("--source-bundle is required.")
            request = read_creative_code_patch_build_request(args.validate_request)
            bundle = read_creative_code_specification_bundle(Path(args.source_bundle))
            validate_creative_code_patch_build_request(request, source_bundle=bundle)
        elif args.validate_result:
            result = read_creative_code_patch_result(args.validate_result)
            validate_creative_code_patch_result(result)
        else:
            parser.error("--validate-request or --validate-result is required")
    except CreativeCodePatchContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
