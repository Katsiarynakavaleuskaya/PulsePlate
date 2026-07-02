#!/usr/bin/env python3
"""Validate the governed Experiment Runner non-human identity policy."""

from __future__ import annotations

import argparse
from email.utils import parseaddr
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = (
    REPO_ROOT / "docs" / "orchestration" / "GOVERNED_NON_HUMAN_IDENTITY_POLICY.json"
)
EXPECTED_SCHEMA_VERSION = "1.0"
EXPECTED_IDENTITY_SLUG = "experiment-runner"
EXPECTED_DISPLAY_NAME = "PulsePlate Experiment Runner"
EXPECTED_EMAIL = "pulseplate@pm.me"
EXPECTED_CO_AUTHOR_TRAILER = "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>"
FORBIDDEN_CO_AUTHOR_TRAILER = "Co-authored-by: Experiment Runner <runner@example.com>"
FORBIDDEN_EMAILS = frozenset({"runner@example.com"})
FORBIDDEN_CO_AUTHOR_EMAIL_RE = re.compile(
    r"Co-authored-by:\s*[^\n<]*<\s*runner@example\.com\s*>",
    re.IGNORECASE,
)
GUIDANCE_PATHS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "scripts" / "AGENTS.md",
    REPO_ROOT / "docs" / "orchestration" / "AGENT_EXPERIMENTATION_PROTOCOL.md",
    REPO_ROOT / "docs" / "orchestration" / "GOVERNED_NON_HUMAN_IDENTITY_POLICY.md",
)
ALLOWED_SIGNING_METHODS = frozenset({"ssh", "gpg", "github_app_verified_signature"})
ALLOWED_SLACK_SINKS = [
    "experiment_notify_slack_explicit_sink",
    "experiment_slack_socket_operator_bridge",
]
SENSITIVE_FIELD_RE = re.compile(
    r"(access[\s_-]*key|api[\s_-]*key|private[\s_-]*key|pass[\s_-]*phrase|password|secret|token|credential|signing[\s_-]*key)",
    re.IGNORECASE,
)
SENSITIVE_POLICY_KEY_TOKENS = frozenset(
    {
        "access_key",
        "access_key_id",
        "api_key",
        "credential",
        "pass_phrase",
        "password",
        "private_key",
        "secret",
        "signing_key",
        "token",
    }
)
SENSITIVE_VALUE_RE = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----|sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9._-]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abcprs]-[A-Za-z0-9-]{10,}|xapp-[A-Za-z0-9-]{10,}|https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{10,})",
    re.IGNORECASE,
)
AUTHORITY_FIELD_NAMES = frozenset(
    {
        "merge_rights",
        "can_claim_merge_readiness",
        "can_resolve_review_threads",
        "can_push_without_human_review",
        "allowed_commit_context",
    }
)
AUTHORITY_FIELD_COMPACT_NAMES = frozenset(name.replace("_", "") for name in AUTHORITY_FIELD_NAMES)
CANONICAL_SENSITIVE_BOOLEAN_PATHS = frozenset(
    {
        "$.cryptographic_boundary.commit_signing_required_for_autonomous_production_commits",
        "$.cryptographic_boundary.private_key_material_allowed_in_repo",
        "$.cryptographic_boundary.repo_must_not_generate_private_keys",
        "$.cryptographic_boundary.repo_must_not_store_signing_secrets",
        "$.github_app_dispatch.can_mint_installation_tokens",
        "$.slack_identity.requires_bot_token_secret_boundary",
    }
)
CANONICAL_BOUNDARY_KEYS = frozenset(
    {
        "authority_boundary",
        "contribution_attribution",
        "cryptographic_boundary",
        "git_attribution",
        "github_app_dispatch",
        "notification_boundary",
        "slack_identity",
        "validator_mutation_boundary",
    }
)


class IdentityPolicyError(ValueError):
    """Raised when the Experiment Runner identity policy is unsafe."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise IdentityPolicyError("Experiment Runner identity policy has duplicate JSON keys.")
        seen.add(key)
        payload[key] = value
    return payload


def _read_policy(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityPolicyError("Unable to read Experiment Runner identity policy.") from exc
    if not isinstance(payload, dict):
        raise IdentityPolicyError("Experiment Runner identity policy must be a JSON object.")
    return payload


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise IdentityPolicyError(f"{key} must be a JSON object.")
    return value


def _require_bool(mapping: dict[str, Any], key: str, expected: bool) -> None:
    if mapping.get(key) is not expected:
        raise IdentityPolicyError(f"{key} must be {str(expected).lower()}.")


def _normalized_email(raw_email: Any) -> str:
    if not isinstance(raw_email, str):
        raise IdentityPolicyError("git_attribution.email must be a string.")
    display_name, email = parseaddr(raw_email)
    if display_name or email != raw_email or not email:
        raise IdentityPolicyError("git_attribution.email must be a bare email address.")
    if email.lower() != email:
        raise IdentityPolicyError("git_attribution.email must be lowercase.")
    if email in FORBIDDEN_EMAILS or email.endswith("@example.com"):
        raise IdentityPolicyError("Experiment Runner attribution must not use placeholder email.")
    return email


def _path_for_key(path: str, key: Any) -> str:
    if not isinstance(key, str):
        return f"{path}.<non-string-key>"
    if SENSITIVE_VALUE_RE.search(key) or ("." in key and _is_sensitive_policy_key(key)):
        return f"{path}.<redacted-key>"
    return f"{path}.{key}"


def _normalized_policy_key(key: Any) -> str:
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _compact_policy_key(key: Any) -> str:
    return _normalized_policy_key(key).replace("_", "")


def _is_sensitive_policy_key(key: Any) -> bool:
    normalized = _normalized_policy_key(key)
    normalized_tokens = frozenset(token for token in normalized.split("_") if token)
    has_pk_tokens = "private" in normalized_tokens and "key" in normalized_tokens
    return (
        SENSITIVE_FIELD_RE.search(str(key)) is not None
        or any(token in normalized for token in SENSITIVE_POLICY_KEY_TOKENS)
        or has_pk_tokens
    )


def _diagnostic_path(path: str, key: Any) -> str:
    if not isinstance(key, str):
        return f"{path}.<non-string-key>"
    if SENSITIVE_VALUE_RE.search(key) or _is_sensitive_policy_key(key):
        return f"{path}.<redacted-key>"
    return f"{path}.{key}"


def _redact_diagnostic_path(path: str) -> str:
    parts = path.split(".")
    redacted_parts = [
        (
            "<redacted-key>"
            if SENSITIVE_VALUE_RE.search(part) or _is_sensitive_policy_key(part)
            else part
        )
        for part in parts
    ]
    return ".".join(redacted_parts)


def _reject_private_key_material(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = _path_for_key(path, key)
            if isinstance(key, str) and SENSITIVE_VALUE_RE.search(key):
                raise IdentityPolicyError(
                    f"{_diagnostic_path(path, key)} must not store private key material "
                    "or secrets."
                )
            if _is_sensitive_policy_key(key):
                allowed_marker = isinstance(value, str) and value in {"none", "external"}
                allowed_canonical_bool = (
                    next_path in CANONICAL_SENSITIVE_BOOLEAN_PATHS and isinstance(value, bool)
                )
                if not allowed_canonical_bool and not allowed_marker:
                    raise IdentityPolicyError(
                        f"{_diagnostic_path(path, key)} must not store private key "
                        "material or secrets."
                    )
            _reject_private_key_material(value, path=next_path)
        return
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            _reject_private_key_material(item, path=f"{path}[{index}]")
        return
    if isinstance(payload, str) and SENSITIVE_VALUE_RE.search(payload):
        raise IdentityPolicyError(f"{path} must not store private key material or secrets.")


def _reject_authority_drift(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = _path_for_key(path, key)
            normalized_key = _normalized_policy_key(key)
            compact_key = _compact_policy_key(key)
            is_authority_field = (
                normalized_key in AUTHORITY_FIELD_NAMES
                or compact_key in AUTHORITY_FIELD_COMPACT_NAMES
            )
            if (
                path == "$.authority_boundary"
                and is_authority_field
                and str(key) not in AUTHORITY_FIELD_NAMES
            ):
                raise IdentityPolicyError(
                    f"{_redact_diagnostic_path(next_path)} must not duplicate "
                    "Experiment Runner authority."
                )
            if (
                path != "$.authority_boundary"
                and is_authority_field
                and value is not False
                and value != "none"
            ):
                raise IdentityPolicyError(
                    f"{_redact_diagnostic_path(next_path)} must not grant Experiment "
                    "Runner authority."
                )
            _reject_authority_drift(value, path=next_path)
        return
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            _reject_authority_drift(item, path=f"{path}[{index}]")


def _reject_duplicate_boundary_blocks(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = _path_for_key(path, key)
            compact_key = _compact_policy_key(key)
            duplicate_boundary = next(
                (
                    boundary_key
                    for boundary_key in CANONICAL_BOUNDARY_KEYS
                    if _compact_policy_key(boundary_key) in compact_key
                ),
                None,
            )
            if duplicate_boundary is not None and next_path != f"$.{duplicate_boundary}":
                raise IdentityPolicyError(
                    f"{_redact_diagnostic_path(next_path)} must not duplicate "
                    f"{duplicate_boundary} boundary."
                )
            _reject_duplicate_boundary_blocks(value, path=next_path)
        return
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            _reject_duplicate_boundary_blocks(item, path=f"{path}[{index}]")


def validate_identity_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a validated identity policy or raise IdentityPolicyError."""

    _reject_duplicate_boundary_blocks(payload)
    _reject_authority_drift(payload)
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise IdentityPolicyError("schema_version must be 1.0.")
    if payload.get("identity_slug") != EXPECTED_IDENTITY_SLUG:
        raise IdentityPolicyError("identity_slug must be experiment-runner.")
    if payload.get("display_name") != EXPECTED_DISPLAY_NAME:
        raise IdentityPolicyError("display_name must be PulsePlate Experiment Runner.")

    git_attribution = _require_mapping(payload, "git_attribution")
    if git_attribution.get("name") != EXPECTED_DISPLAY_NAME:
        raise IdentityPolicyError("git_attribution.name must match display_name.")
    if _normalized_email(git_attribution.get("email")) != EXPECTED_EMAIL:
        raise IdentityPolicyError("git_attribution.email must be pulseplate@pm.me.")
    if git_attribution.get("co_author_trailer") != EXPECTED_CO_AUTHOR_TRAILER:
        raise IdentityPolicyError(
            "git_attribution.co_author_trailer must use the governed PulsePlate "
            "Experiment Runner identity."
        )
    if git_attribution.get("purpose") != "public_attribution_only":
        raise IdentityPolicyError("git_attribution.purpose must be public_attribution_only.")
    forbidden = git_attribution.get("forbidden_placeholder_emails")
    if not isinstance(forbidden, list) or not all(isinstance(entry, str) for entry in forbidden):
        raise IdentityPolicyError("forbidden_placeholder_emails must be a list of email strings.")
    if not FORBIDDEN_EMAILS.issubset(set(forbidden)):
        raise IdentityPolicyError("forbidden_placeholder_emails must include runner@example.com.")

    authority_boundary = _require_mapping(payload, "authority_boundary")
    if authority_boundary.get("merge_rights") != "none":
        raise IdentityPolicyError("authority_boundary.merge_rights must be none.")
    _require_bool(authority_boundary, "can_claim_merge_readiness", False)
    _require_bool(authority_boundary, "can_resolve_review_threads", False)
    _require_bool(authority_boundary, "can_push_without_human_review", False)
    if authority_boundary.get("allowed_commit_context") != "repo_local_pr_lane_only":
        raise IdentityPolicyError(
            "authority_boundary.allowed_commit_context must be repo_local_pr_lane_only."
        )

    contribution_attribution = _require_mapping(payload, "contribution_attribution")
    if contribution_attribution.get("basis") != "material_evidence_contribution":
        raise IdentityPolicyError(
            "contribution_attribution.basis must be material_evidence_contribution."
        )
    _require_bool(
        contribution_attribution,
        "oracle_only_artifact_can_require_coauthor",
        True,
    )
    _require_bool(
        contribution_attribution,
        "mutated_paths_do_not_control_attribution",
        True,
    )
    _require_bool(
        contribution_attribution,
        "requires_canonical_trailer_when_coauthor_required",
        True,
    )
    not_required = contribution_attribution.get("coauthor_not_required_when")
    required_not_required = {
        "runner_only_launched",
        "artifact_rejected",
        "artifact_unused",
        "not_applicable_recorded",
    }
    if not isinstance(not_required, list) or not all(
        isinstance(item, str) for item in not_required
    ):
        raise IdentityPolicyError(
            "contribution_attribution.coauthor_not_required_when must be a list of strings."
        )
    actual_not_required = set(not_required)
    if actual_not_required != required_not_required:
        missing = sorted(required_not_required - actual_not_required)
        unexpected = sorted(actual_not_required - required_not_required)
        raise IdentityPolicyError(
            "contribution_attribution.coauthor_not_required_when must exactly match "
            "required cases. "
            f"Missing: {missing or ['none']}; unexpected: {unexpected or ['none']}."
        )

    validator_boundary = _require_mapping(payload, "validator_mutation_boundary")
    if validator_boundary.get("status") != "threat_model_only":
        raise IdentityPolicyError("validator_mutation_boundary.status must be threat_model_only.")
    _require_bool(validator_boundary, "active_mutation_access", False)
    _require_bool(validator_boundary, "requires_later_security_pr", True)
    _require_bool(validator_boundary, "rollback_notes_required", True)
    _require_bool(validator_boundary, "identity_checks_required", True)
    allowlisted = validator_boundary.get("allowlisted_validator_scripts")
    if allowlisted != []:
        raise IdentityPolicyError(
            "validator_mutation_boundary.allowlisted_validator_scripts must be empty."
        )
    forbidden = validator_boundary.get("forbidden_surface_prefixes")
    if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
        raise IdentityPolicyError(
            "validator_mutation_boundary.forbidden_surface_prefixes must be a list of strings."
        )
    required_forbidden = {
        "AGENTS.md",
        ".github/workflows/",
        ".env",
        ".env.",
        "docs/orchestration/",
        "docs/review/",
        "fixtures/",
        "scripts/ci/",
        "scripts/orchestration/check_merge_ready.py",
        "scripts/orchestration/check_review_threads_disposition.py",
        "tests/",
    }
    if not required_forbidden.issubset(set(forbidden)):
        raise IdentityPolicyError(
            "validator_mutation_boundary.forbidden_surface_prefixes is missing required "
            "governance surfaces."
        )

    cryptographic_boundary = _require_mapping(payload, "cryptographic_boundary")
    if cryptographic_boundary.get("status") != "operator_managed_external":
        raise IdentityPolicyError(
            "cryptographic_boundary.status must be operator_managed_external."
        )
    _require_bool(cryptographic_boundary, "verified_account_required", True)
    _require_bool(
        cryptographic_boundary,
        "commit_signing_required_for_autonomous_production_commits",
        True,
    )
    _require_bool(cryptographic_boundary, "private_key_material_allowed_in_repo", False)
    _require_bool(cryptographic_boundary, "repo_must_not_generate_private_keys", True)
    _require_bool(cryptographic_boundary, "repo_must_not_store_signing_secrets", True)
    methods = cryptographic_boundary.get("allowed_signing_methods")
    if not isinstance(methods, list) or not all(isinstance(method, str) for method in methods):
        raise IdentityPolicyError(
            "allowed_signing_methods must be a list of signing method strings."
        )
    if set(methods) != ALLOWED_SIGNING_METHODS:
        raise IdentityPolicyError("allowed_signing_methods must be ssh, gpg, and GitHub App.")

    notification_boundary = _require_mapping(payload, "notification_boundary")
    _require_bool(notification_boundary, "git_email_is_delivery_channel", False)
    if (
        notification_boundary.get("experiment_result_delivery")
        != "experiment_notify_explicit_sink_only"
    ):
        raise IdentityPolicyError(
            "notification_boundary.experiment_result_delivery must be "
            "experiment_notify_explicit_sink_only."
        )
    if notification_boundary.get("default_sink") != "local_artifact":
        raise IdentityPolicyError("notification_boundary.default_sink must be local_artifact.")
    if notification_boundary.get("v1_email_recipient") != EXPECTED_EMAIL:
        raise IdentityPolicyError(
            "notification_boundary.v1_email_recipient must be pulseplate@pm.me."
        )

    github_app_dispatch = _require_mapping(payload, "github_app_dispatch")
    if github_app_dispatch.get("status") != "selected_repo_workflow_dispatch_boundary":
        raise IdentityPolicyError(
            "github_app_dispatch.status must be selected_repo_workflow_dispatch_boundary."
        )
    if github_app_dispatch.get("source") != "externally_minted_installation":
        raise IdentityPolicyError(
            "github_app_dispatch.source must be externally_minted_installation."
        )
    if github_app_dispatch.get("repository_scope") != "runtime_allowlist_selected_repositories":
        raise IdentityPolicyError(
            "github_app_dispatch.repository_scope must be "
            "runtime_allowlist_selected_repositories."
        )
    _require_bool(github_app_dispatch, "requires_repo_allowlist", True)
    _require_bool(github_app_dispatch, "requires_installation_class_for_cross_repo", True)
    _require_bool(github_app_dispatch, "requires_actions_write", True)
    if (
        github_app_dispatch.get("private_pilot_capability_gate")
        != "read_only_report_consumed_by_private_pilot_state"
    ):
        raise IdentityPolicyError(
            "github_app_dispatch.private_pilot_capability_gate must be "
            "read_only_report_consumed_by_private_pilot_state."
        )
    _require_bool(github_app_dispatch, "private_pilot_requires_pull_requests_read", True)
    _require_bool(github_app_dispatch, "private_pilot_requires_checks_read", True)
    _require_bool(github_app_dispatch, "private_pilot_actions_write_required_for_readonly", False)
    if github_app_dispatch.get("private_pilot_workflow_dispatch") != "optional_actions_write_only":
        raise IdentityPolicyError(
            "github_app_dispatch.private_pilot_workflow_dispatch must be "
            "optional_actions_write_only."
        )
    _require_bool(github_app_dispatch, "private_pilot_app_settings_mutation", False)
    if (
        github_app_dispatch.get("private_pilot_activation_evidence_loop")
        != "redacted_manual_smoke_contract_only"
    ):
        raise IdentityPolicyError(
            "github_app_dispatch.private_pilot_activation_evidence_loop must be "
            "redacted_manual_smoke_contract_only."
        )
    if (
        github_app_dispatch.get("private_pilot_manual_smoke_operations")
        != "local_validate_import_report_only"
    ):
        raise IdentityPolicyError(
            "github_app_dispatch.private_pilot_manual_smoke_operations must be "
            "local_validate_import_report_only."
        )
    if (
        github_app_dispatch.get("activation_evidence_artifact_scope")
        != "local_redacted_contract_only"
    ):
        raise IdentityPolicyError(
            "github_app_dispatch.activation_evidence_artifact_scope must be "
            "local_redacted_contract_only."
        )
    if github_app_dispatch.get("workflow_file") != "experiment-runner-dispatch.yml":
        raise IdentityPolicyError(
            "github_app_dispatch.workflow_file must be experiment-runner-dispatch.yml."
        )
    if github_app_dispatch.get("workflow_ref") != "main":
        raise IdentityPolicyError("github_app_dispatch.workflow_ref must be main.")
    _require_bool(github_app_dispatch, "can_dispatch_repository_events", False)
    _require_bool(github_app_dispatch, "can_dispatch_arbitrary_workflow", False)
    _require_bool(github_app_dispatch, "can_mint_installation_tokens", False)
    _require_bool(github_app_dispatch, "can_mutate_pull_requests", False)
    _require_bool(github_app_dispatch, "can_mutate_review_threads", False)
    _require_bool(github_app_dispatch, "can_merge_pull_requests", False)
    _require_bool(github_app_dispatch, "can_write_contents", False)
    _require_bool(github_app_dispatch, "can_write_workflows", False)
    _require_bool(github_app_dispatch, "can_enable_semantic_cache_runtime", False)
    _require_bool(github_app_dispatch, "can_administer", False)
    _require_bool(github_app_dispatch, "can_manage_sensitive_store", False)

    slack_identity = _require_mapping(payload, "slack_identity")
    if slack_identity.get("status") != "operator_notification_boundary_defined":
        raise IdentityPolicyError(
            "slack_identity.status must be operator_notification_boundary_defined."
        )
    if slack_identity.get("purpose") != "ops_notification_and_operator_command_boundary_only":
        raise IdentityPolicyError(
            "slack_identity.purpose must be " "ops_notification_and_operator_command_boundary_only."
        )
    _require_bool(slack_identity, "not_cryptographic_identity", True)
    if slack_identity.get("security_pr_status") != "implemented_in_this_pr":
        raise IdentityPolicyError(
            "slack_identity.security_pr_status must be implemented_in_this_pr."
        )
    _require_bool(slack_identity, "requires_socket_auth_boundary", True)
    _require_bool(slack_identity, "requires_bot_token_secret_boundary", True)
    _require_bool(slack_identity, "requires_channel_allowlist", True)
    _require_bool(slack_identity, "requires_user_allowlist", True)
    _require_bool(slack_identity, "requires_fixed_workflow_dispatch", True)
    _require_bool(slack_identity, "requires_explicit_dispatch_opt_in", True)
    _require_bool(slack_identity, "requires_hash_only_audit", True)
    _require_bool(slack_identity, "requires_audit_artifact", True)
    _require_bool(slack_identity, "requires_runtime_presence_diagnostics", True)
    _require_bool(slack_identity, "requires_audit_retention_policy", True)
    _require_bool(slack_identity, "requires_redacted_messages", True)
    _require_bool(slack_identity, "requires_rate_limit", True)
    _require_bool(slack_identity, "requires_timeout", True)
    _require_bool(slack_identity, "requires_idempotency", True)
    _require_bool(slack_identity, "default_enabled", False)
    if slack_identity.get("delivery_credential_source") != "external":
        raise IdentityPolicyError("slack_identity.delivery_credential_source must be external.")
    if slack_identity.get("channel_allowlist_source") != "runtime_env":
        raise IdentityPolicyError("slack_identity.channel_allowlist_source must be runtime_env.")
    if slack_identity.get("allowed_sinks") != ALLOWED_SLACK_SINKS:
        raise IdentityPolicyError(
            "slack_identity.allowed_sinks must list only governed Slack sinks."
        )
    if slack_identity.get("operator_bridge_sink") != "experiment_slack_socket_operator_bridge":
        raise IdentityPolicyError(
            "slack_identity.operator_bridge_sink must be "
            "experiment_slack_socket_operator_bridge."
        )
    operator_command_boundary = _require_mapping(slack_identity, "operator_command_boundary")
    if operator_command_boundary.get("status") != "socket_mode_dry_run_bridge":
        raise IdentityPolicyError(
            "slack_identity.operator_command_boundary.status must be " "socket_mode_dry_run_bridge."
        )
    if operator_command_boundary.get("default_dispatch_mode") != "dry_run":
        raise IdentityPolicyError(
            "slack_identity.operator_command_boundary.default_dispatch_mode must be dry_run."
        )
    _require_bool(operator_command_boundary, "live_socket_default_enabled", False)
    _require_bool(operator_command_boundary, "requires_github_runtime_auth", True)
    if operator_command_boundary.get("github_runtime_auth_source") != "runtime_env":
        raise IdentityPolicyError(
            "slack_identity.operator_command_boundary.github_runtime_auth_source must be runtime_env."
        )
    _require_bool(operator_command_boundary, "can_dispatch_arbitrary_workflow", False)
    _require_bool(operator_command_boundary, "can_dispatch_without_operator_opt_in", False)
    _require_bool(operator_command_boundary, "can_create_pull_requests", False)
    _require_bool(operator_command_boundary, "can_run_shell_commands", False)
    forbidden_authority = _require_mapping(slack_identity, "forbidden_authority")
    _require_bool(forbidden_authority, "public_git_identity", False)
    if forbidden_authority.get("merge_rights") != "none":
        raise IdentityPolicyError("slack_identity.forbidden_authority.merge_rights must be none.")
    _require_bool(forbidden_authority, "can_claim_merge_readiness", False)
    _require_bool(forbidden_authority, "can_resolve_review_threads", False)
    _require_bool(forbidden_authority, "can_push_without_human_review", False)

    _reject_private_key_material(payload)
    return payload


def validate_co_author_guidance(paths: tuple[Path, ...] = GUIDANCE_PATHS) -> None:
    """Validate agent-facing co-author guidance stays on the governed identity."""

    for path in paths:
        try:
            label = str(path.relative_to(REPO_ROOT))
        except ValueError:
            label = path.name
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise IdentityPolicyError("Unable to read Experiment Runner guidance.") from exc
        if EXPECTED_CO_AUTHOR_TRAILER not in content:
            raise IdentityPolicyError(f"{label} must include the governed co-author trailer.")
        if FORBIDDEN_CO_AUTHOR_TRAILER in content or FORBIDDEN_CO_AUTHOR_EMAIL_RE.search(content):
            raise IdentityPolicyError(f"{label} must not include placeholder co-author guidance.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH), help="Policy JSON path.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable status.")
    args = parser.parse_args(argv)

    try:
        policy = validate_identity_policy(_read_policy(Path(args.policy)))
        validate_co_author_guidance()
    except IdentityPolicyError as exc:
        if args.json:
            print(json.dumps({"status": "fail", "error": str(exc)}, sort_keys=True))
        else:
            print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    result = {
        "status": "pass",
        "identity_slug": policy["identity_slug"],
        "co_author_trailer": policy["git_attribution"]["co_author_trailer"],
        "git_email": policy["git_attribution"]["email"],
        "slack_identity": policy["slack_identity"]["status"],
    }
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "PASS: Experiment Runner identity policy is governed, "
            "attribution-only, and externally signed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
