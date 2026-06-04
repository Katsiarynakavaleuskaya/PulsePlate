"""Redacted activation-readiness reporting for the Slack operator bridge."""

from __future__ import annotations

from collections.abc import Mapping
import os
from typing import Any

from scripts.orchestration.experiment_slack_bridge_config import _is_safe_ref
from scripts.orchestration.experiment_slack_bridge_constants import (
    BRIDGE_AUDIT_RETENTION_DAYS_ENV,
    CONTROL_CHAR_RE,
    DEFAULT_AUDIT_RETENTION_DAYS,
    LIVE_SMOKE_BRANCH_REF_ENV,
    LIVE_SMOKE_HYPOTHESIS_SHA256_ENV,
    MAX_AUDIT_RETENTION_DAYS,
    SAFE_SLACK_ID_RE,
    SHA256_HEX_RE,
    SLACK_APP_AUTH_ENV,
    SLACK_APP_TOKEN_RE,
    SLACK_BOT_AUTH_ENV,
    SLACK_BOT_TOKEN_RE,
    SLACK_CHANNEL_ALLOWLIST_ENV,
    SLACK_TEAM_ALLOWLIST_ENV,
    SLACK_USER_ALLOWLIST_ENV,
)

_TOKEN_LABELS = {
    SLACK_APP_AUTH_ENV: "slack_app_token_status",
    SLACK_BOT_AUTH_ENV: "slack_bot_token_status",
}
_ALLOWLIST_LABELS = {
    SLACK_CHANNEL_ALLOWLIST_ENV: "channel_allowlist_status",
    SLACK_USER_ALLOWLIST_ENV: "user_allowlist_status",
    SLACK_TEAM_ALLOWLIST_ENV: "team_allowlist_status",
}


def activation_readiness_authority_boundary() -> dict[str, bool]:
    """Return the fixed authority boundary for activation-readiness reports."""

    return {
        "backend_contract_changed": False,
        "claimed_merge_readiness": False,
        "created_pr": False,
        "deterministic_ci_requires_live_slack": False,
        "opened_http_ingress": False,
        "product_runtime_changed": False,
        "resolved_review_threads": False,
        "semantic_cache_enabled": False,
    }


def manual_only_activation_readiness_report() -> dict[str, Any]:
    """Return a static report for local observability without reading runtime env."""

    return {
        "activation_state": "manual_only",
        "audit_retention_status": "not_checked",
        "authority_boundary": activation_readiness_authority_boundary(),
        "dispatch_surface": "socket_mode_only",
        "manual_live_smoke": "operator_evidence_only",
        "redaction": "labels_only",
        "slack_app_token_status": "not_checked",
        "slack_bot_token_status": "not_checked",
        "channel_allowlist_status": "not_checked",
        "user_allowlist_status": "not_checked",
        "team_allowlist_status": "not_checked",
        "branch_ref_status": "not_checked",
        "hypothesis_sha256_status": "not_checked",
        "status": "pass",
    }


def _value(env: Mapping[str, str], name: str) -> str:
    return env.get(name, "").strip()


def _token_status(env: Mapping[str, str], name: str) -> str:
    raw = _value(env, name)
    if not raw:
        return "missing"
    pattern = {
        SLACK_APP_AUTH_ENV: SLACK_APP_TOKEN_RE,
        SLACK_BOT_AUTH_ENV: SLACK_BOT_TOKEN_RE,
    }[name]
    if CONTROL_CHAR_RE.search(raw) or "`" in raw or pattern.fullmatch(raw) is None:
        return "invalid"
    return "valid"


def _allowlist_status(env: Mapping[str, str], name: str) -> str:
    raw = _value(env, name)
    if not raw:
        return "missing"
    for candidate in raw.split(","):
        candidate = candidate.strip()
        if (
            not candidate
            or CONTROL_CHAR_RE.search(candidate)
            or SAFE_SLACK_ID_RE.fullmatch(candidate) is None
        ):
            return "invalid"
    return "present"


def _branch_ref_status(raw_value: str | None, env: Mapping[str, str]) -> str:
    raw = (raw_value if raw_value is not None else env.get(LIVE_SMOKE_BRANCH_REF_ENV, "")).strip()
    if not raw:
        return "not_checked"
    return "valid" if _is_safe_ref(raw) else "invalid"


def _hypothesis_digest_status(raw_value: str | None, env: Mapping[str, str]) -> str:
    raw = raw_value if raw_value is not None else env.get(LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "")
    if not raw:
        return "not_checked"
    return "valid" if SHA256_HEX_RE.fullmatch(raw) is not None else "invalid"


def _audit_retention_status(env: Mapping[str, str]) -> str:
    raw = env.get(BRIDGE_AUDIT_RETENTION_DAYS_ENV, str(DEFAULT_AUDIT_RETENTION_DAYS)).strip()
    try:
        value = int(raw)
    except ValueError:
        return "invalid"
    return "valid" if 0 < value <= MAX_AUDIT_RETENTION_DAYS else "invalid"


def _activation_state(
    *,
    token_statuses: Mapping[str, str],
    allowlist_statuses: Mapping[str, str],
    branch_ref_status: str,
    hypothesis_sha256_status: str,
    audit_retention_status: str,
    require_smoke_inputs: bool,
) -> str:
    invalid_values = {
        *token_statuses.values(),
        *allowlist_statuses.values(),
        branch_ref_status,
        hypothesis_sha256_status,
        audit_retention_status,
    }
    if "invalid" in invalid_values:
        return "blocked_by_invalid_config"
    if all(status == "missing" for status in token_statuses.values()) and all(
        status == "missing" for status in allowlist_statuses.values()
    ):
        return "manual_only"
    if any(status == "missing" for status in token_statuses.values()):
        return "blocked_by_missing_secret"
    if any(status == "missing" for status in allowlist_statuses.values()):
        return "blocked_by_allowlist"
    if require_smoke_inputs and (
        branch_ref_status != "valid" or hypothesis_sha256_status != "valid"
    ):
        return "blocked_by_smoke_input"
    return "ready_for_manual_live_smoke" if require_smoke_inputs else "manual_only"


def build_activation_readiness_report(
    *,
    env: Mapping[str, str] | None = None,
    branch_ref: str | None = None,
    hypothesis_sha256: str | None = None,
    require_smoke_inputs: bool = True,
) -> dict[str, Any]:
    """Build a value-free Socket Mode activation-readiness report."""

    effective_env = env if env is not None else os.environ
    token_statuses = {
        label: _token_status(effective_env, env_name) for env_name, label in _TOKEN_LABELS.items()
    }
    allowlist_statuses = {
        label: _allowlist_status(effective_env, env_name)
        for env_name, label in _ALLOWLIST_LABELS.items()
    }
    branch_status = _branch_ref_status(branch_ref, effective_env)
    hypothesis_status = _hypothesis_digest_status(hypothesis_sha256, effective_env)
    audit_status = _audit_retention_status(effective_env)
    activation_state = _activation_state(
        token_statuses=token_statuses,
        allowlist_statuses=allowlist_statuses,
        branch_ref_status=branch_status,
        hypothesis_sha256_status=hypothesis_status,
        audit_retention_status=audit_status,
        require_smoke_inputs=require_smoke_inputs,
    )
    report: dict[str, Any] = {
        "activation_state": activation_state,
        "audit_retention_status": audit_status,
        "authority_boundary": activation_readiness_authority_boundary(),
        "branch_ref_status": branch_status,
        "dispatch_surface": "socket_mode_only",
        "hypothesis_sha256_status": hypothesis_status,
        "manual_live_smoke": "operator_evidence_only",
        "redaction": "labels_only",
        "smoke_input_requirement": "required" if require_smoke_inputs else "not_required",
        "status": (
            "fail"
            if activation_state
            in {
                "blocked_by_allowlist",
                "blocked_by_invalid_config",
                "blocked_by_missing_secret",
                "blocked_by_smoke_input",
            }
            else "pass"
        ),
    }
    report.update(token_statuses)
    report.update(allowlist_statuses)
    return report


def render_activation_readiness_summary(report: Mapping[str, Any]) -> tuple[str, ...]:
    """Render a Slack-safe and report-safe readiness summary tuple."""

    authority_boundary = report.get("authority_boundary", {})
    boundary = authority_boundary if isinstance(authority_boundary, Mapping) else {}
    return (
        f"socket_mode_activation_state={report.get('activation_state', 'manual_only')}",
        f"socket_mode_readiness_status={report.get('status', 'pass')}",
        f"slack_app_token_status={report.get('slack_app_token_status', 'not_checked')}",
        f"slack_bot_token_status={report.get('slack_bot_token_status', 'not_checked')}",
        f"channel_allowlist_status={report.get('channel_allowlist_status', 'not_checked')}",
        f"user_allowlist_status={report.get('user_allowlist_status', 'not_checked')}",
        f"team_allowlist_status={report.get('team_allowlist_status', 'not_checked')}",
        f"branch_ref_status={report.get('branch_ref_status', 'not_checked')}",
        f"hypothesis_sha256_status={report.get('hypothesis_sha256_status', 'not_checked')}",
        f"audit_retention_status={report.get('audit_retention_status', 'not_checked')}",
        f"manual_live_smoke={report.get('manual_live_smoke', 'operator_evidence_only')}",
        f"deterministic_ci_requires_live_slack={str(boundary.get('deterministic_ci_requires_live_slack', False)).lower()}",
        f"opened_http_ingress={str(boundary.get('opened_http_ingress', False)).lower()}",
        f"semantic_cache_enabled={str(boundary.get('semantic_cache_enabled', False)).lower()}",
        f"product_runtime_changed={str(boundary.get('product_runtime_changed', False)).lower()}",
        f"claimed_merge_readiness={str(boundary.get('claimed_merge_readiness', False)).lower()}",
        "activation_authority=display_only",
    )
