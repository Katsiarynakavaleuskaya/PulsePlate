#!/usr/bin/env python3
"""Dry-run-first Slack Socket Mode bridge for Experiment Runner operators."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import logging
from pathlib import Path
import sys
from typing import Any, cast

try:
    from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
except ModuleNotFoundError as exc:  # pragma: no cover - direct script invocation guard.
    if exc.name != "scripts":
        raise
    print(
        "FAIL: run as `python -m scripts.orchestration.experiment_slack_socket_bridge` "
        "from repo root.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc

try:
    from scripts.orchestration import experiment_slack_bridge_audit as _audit
    from scripts.orchestration import experiment_slack_bridge_config as _config
    from scripts.orchestration import experiment_slack_bridge_dispatch as _dispatch
    from scripts.orchestration import experiment_slack_bridge_rendering as _rendering
    from scripts.orchestration import experiment_slack_bridge_transport as _transport
    from scripts.orchestration import experiment_operator_ledger as _operator_ledger
    from scripts.orchestration.experiment_slack_bridge_commands import (
        _read_json_object,
        _require_authorized_event,
        _validate_hypothesis,
        normalize_slack_payload,
        parse_operator_command,
    )
    from scripts.orchestration.experiment_slack_bridge_config import (
        _allowlist_from_env,
        _compute_live_approval_digest,
        _github_token,
        _is_safe_ref,
        _live_approval_sha256,
        _normalize_slack_id,
        _normalized_absolute_path,
        _optional_token,
        _positive_int_from_env,
        _reject_symlinked_existing_path,
        _validate_repo,
        _validate_workflow_file,
        _validate_workflow_ref,
    )
    from scripts.orchestration.experiment_slack_bridge_constants import (
        ALLOWED_COMMANDS,
        ALLOWED_WORKFLOW_REFS,
        ALLOWED_WORKFLOWS,
        BRIDGE_AUDIT_RETENTION_DAYS_ENV,
        BRIDGE_EXECUTE_ENABLED_ENV,
        BRIDGE_EXECUTE_ENABLED_VALUE,
        BRIDGE_MIN_INTERVAL_ENV,
        BRIDGE_TIMEOUT_ENV,
        CONTROL_CHAR_RE,
        DEFAULT_AUDIT_RETENTION_DAYS,
        DEFAULT_OPERATOR_LEDGER_TASK_PACKET_ID,
        DEFAULT_WORKFLOW_FILE,
        DEFAULT_WORKFLOW_REF,
        ENV_ASSIGNMENT_RE,
        GITHUB_API_HOST,
        GITHUB_TOKEN_RE,
        LIVE_APPROVAL_SHA256_ENV,
        LIVE_SECRET_PRESENCE_ENV,
        LIVE_SMOKE_BRANCH_REF_ENV,
        LIVE_SMOKE_HYPOTHESIS_SHA256_ENV,
        MAX_AUDIT_RETENTION_DAYS,
        OPERATOR_LEDGER_TASK_PACKET_ID_ENV,
        RATE_LIMIT_CLAIM_MAX_ATTEMPTS,
        RATE_LIMIT_LOCK_DIR,
        REJECTED_RATE_LIMIT_LOCK_DIR,
        SAFE_BRANCH_RE,
        SAFE_SLACK_ERROR_CODE_RE,
        SAFE_SLACK_ID_RE,
        SECRET_SHAPED_RE,
        SHA256_HEX_RE,
        SHELL_META_RE,
        SLACK_API_HOST,
        SLACK_APP_AUTH_ENV,
        SLACK_APP_TOKEN_RE,
        SLACK_BOT_AUTH_ENV,
        SLACK_BOT_TOKEN_RE,
        SLACK_CHANNEL_ALLOWLIST_ENV,
        SLACK_LIVE_SMOKE_METHODS,
        SLACK_TEAM_ALLOWLIST_ENV,
        SLACK_USER_ALLOWLIST_ENV,
        default_audit_artifact_dir,
    )
    from scripts.orchestration.experiment_slack_bridge_models import (
        BridgeConfig,
        BridgeDecision,
        OperatorCommand,
        OperatorEvent,
        SlackApiTransport,
        SlackSafeMessage,
        SlackSocketAuditError,
        SlackSocketBridgeError,
        SlackSocketCommandError,
        SlackSocketConfigError,
        SlackSocketDispatchError,
        WorkflowDispatchTransport,
        _bounded_text,
        _safe_hash,
        _sha256_text,
        _utcnow,
    )
    from scripts.orchestration.experiment_slack_bridge_rendering import (
        render_dispatch_dry_run_preview,
        render_kpp_status_overview,
        render_operator_help_message,
        render_operator_status_message,
    )
    from scripts.orchestration.experiment_slack_bridge_transport import (
        _require_slack_ok_response,
        _require_socket_mode_url,
        _safe_slack_error_code,
        validate_live_smoke_inputs,
    )
    from scripts.orchestration.mvp_evidence_snapshot import (
        ALLOWED_EVENT_NAMES as _MVP_ALLOWED_EVENT_NAMES,
        read_latest_snapshot_line as _read_latest_snapshot_line,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - direct script invocation guard.
    if exc.name != "scripts":
        raise
    print(
        "FAIL: run as `python -m scripts.orchestration.experiment_slack_socket_bridge` "
        "from repo root.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc

__all__ = (
    "ALLOWED_COMMANDS",
    "ALLOWED_WORKFLOW_REFS",
    "ALLOWED_WORKFLOWS",
    "AUDIT_ARTIFACT_DIR",
    "BRIDGE_AUDIT_RETENTION_DAYS_ENV",
    "BRIDGE_EXECUTE_ENABLED_ENV",
    "BRIDGE_EXECUTE_ENABLED_VALUE",
    "BRIDGE_MIN_INTERVAL_ENV",
    "BRIDGE_TIMEOUT_ENV",
    "BridgeConfig",
    "BridgeDecision",
    "CONTROL_CHAR_RE",
    "DEFAULT_AUDIT_RETENTION_DAYS",
    "DEFAULT_OPERATOR_LEDGER_TASK_PACKET_ID",
    "DEFAULT_WORKFLOW_FILE",
    "DEFAULT_WORKFLOW_REF",
    "ENV_ASSIGNMENT_RE",
    "GITHUB_API_HOST",
    "GITHUB_TOKEN_RE",
    "LIVE_APPROVAL_SHA256_ENV",
    "LIVE_SECRET_PRESENCE_ENV",
    "LIVE_SMOKE_BRANCH_REF_ENV",
    "LIVE_SMOKE_HYPOTHESIS_SHA256_ENV",
    "MAX_AUDIT_RETENTION_DAYS",
    "OPERATOR_LEDGER_TASK_PACKET_ID_ENV",
    "OperatorCommand",
    "OperatorEvent",
    "RATE_LIMIT_CLAIM_MAX_ATTEMPTS",
    "RATE_LIMIT_LOCK_DIR",
    "REJECTED_RATE_LIMIT_LOCK_DIR",
    "SAFE_BRANCH_RE",
    "SAFE_SLACK_ERROR_CODE_RE",
    "SAFE_SLACK_ID_RE",
    "SECRET_SHAPED_RE",
    "SHA256_HEX_RE",
    "SHELL_META_RE",
    "SLACK_API_HOST",
    "SLACK_APP_AUTH_ENV",
    "SLACK_APP_TOKEN_RE",
    "SLACK_BOT_AUTH_ENV",
    "SLACK_BOT_TOKEN_RE",
    "SLACK_CHANNEL_ALLOWLIST_ENV",
    "SLACK_LIVE_SMOKE_METHODS",
    "SLACK_TEAM_ALLOWLIST_ENV",
    "SLACK_USER_ALLOWLIST_ENV",
    "SlackApiTransport",
    "SlackSafeMessage",
    "SlackSocketAuditError",
    "SlackSocketBridgeError",
    "SlackSocketCommandError",
    "SlackSocketConfigError",
    "SlackSocketDispatchError",
    "WorkflowDispatchTransport",
    "_allowlist_from_env",
    "_approval_prefix",
    "_audit_payload",
    "_audit_path",
    "_audit_timestamp",
    "_bounded_text",
    "_check_rate_limit",
    "_claim_event",
    "_claim_rate_limit",
    "_claim_rejected_event_audit_throttle",
    "_cleanup_partial_rate_limit_claim",
    "_compute_live_approval_digest",
    "_format_command_reply",
    "_github_dispatch_inputs",
    "_github_token",
    "_is_safe_ref",
    "_live_approval_sha256",
    "_load_slack_bolt",
    "_preflight_operator_ledger_event",
    "_normalize_slack_id",
    "_normalized_absolute_path",
    "_optional_token",
    "_partial_rate_limit_claim_is_stale",
    "_positive_int_from_env",
    "_read_audit",
    "_read_json_object",
    "_read_latest_snapshot_line",
    "_read_rate_limit_claim",
    "_reject_symlinked_existing_path",
    "_reject_symlinked_output_components",
    "_remove_stale_rate_limit_claim",
    "_require_authorized_event",
    "_require_execute_config",
    "_require_live_smoke_runtime",
    "_require_slack_ok_response",
    "_require_socket_mode_url",
    "_resolve_audit_dir",
    "_safe_hash",
    "_safe_slack_error_code",
    "_send_github_workflow_dispatch",
    "_send_slack_api_request",
    "_sha256_text",
    "_utcnow",
    "_validate_hypothesis",
    "_validate_repo",
    "_validate_workflow_file",
    "_validate_workflow_ref",
    "_write_audit",
    "_write_audit_exclusive",
    "_write_operator_ledger_event",
    "audit_retention_summary",
    "build_config",
    "default_audit_artifact_dir",
    "main",
    "normalize_slack_payload",
    "parse_operator_command",
    "process_operator_event",
    "process_payload",
    "render_dispatch_dry_run_preview",
    "render_kpp_status_overview",
    "render_latest_operator_ledger_summary",
    "render_mvp_evidence_summary",
    "render_operator_help_message",
    "render_operator_status_message",
    "run_socket_listener",
    "validate_live_smoke",
    "validate_live_smoke_inputs",
    "validate_secret_presence",
)

AUDIT_ARTIFACT_DIR = default_audit_artifact_dir(REPO_ROOT)
LOGGER = logging.getLogger(__name__)


def _reject_symlinked_output_components(candidate: Path, *, artifact_dir: Path) -> None:
    _config._reject_symlinked_output_components(
        candidate,
        artifact_dir=artifact_dir,
        repo_root=Path(REPO_ROOT),
    )


def _resolve_audit_dir(raw_audit_dir: str | None) -> Path:
    return cast(
        Path,
        _config._resolve_audit_dir(
            raw_audit_dir,
            repo_root=Path(REPO_ROOT),
            audit_artifact_dir=Path(AUDIT_ARTIFACT_DIR),
        ),
    )


def build_config(
    *,
    dispatch_mode: str,
    audit_dir: str | None = None,
    repo: str | None = None,
    workflow_file: str = DEFAULT_WORKFLOW_FILE,
    workflow_ref: str = DEFAULT_WORKFLOW_REF,
) -> BridgeConfig:
    """Read sanitized bridge config from runtime env."""

    return _config.build_config(
        dispatch_mode=dispatch_mode,
        repo_root=Path(REPO_ROOT),
        audit_artifact_dir=Path(AUDIT_ARTIFACT_DIR),
        audit_dir=audit_dir,
        repo=repo,
        workflow_file=workflow_file,
        workflow_ref=workflow_ref,
    )


def validate_secret_presence(
    required_env: tuple[str, ...] = LIVE_SECRET_PRESENCE_ENV,
) -> dict[str, object]:
    """Return a value-free live-smoke secret/allowlist presence report."""

    return cast(
        dict[str, object],
        _config.validate_secret_presence(
            config_builder=build_config,
            required_env=required_env,
        ),
    )


def render_mvp_evidence_summary() -> SlackSafeMessage:
    """Render MVP evidence summary with facade-level snapshot reader compatibility."""

    return _rendering.render_mvp_evidence_summary(
        snapshot_reader=_read_latest_snapshot_line,
        allowed_event_names=_MVP_ALLOWED_EVENT_NAMES,
    )


def render_latest_operator_ledger_summary(
    *,
    exclude_event_hash: str | None = None,
) -> tuple[str, ...]:
    """Render latest local operator ledger summary using the facade repo root."""

    return cast(
        tuple[str, ...],
        _operator_ledger.latest_operator_ledger_summary(
            repo_root=Path(REPO_ROOT),
            exclude_event_hash=exclude_event_hash,
        ),
    )


def _audit_path(config: BridgeConfig, event: OperatorEvent) -> Path:
    return cast(Path, _audit._audit_path(config, event))


def _read_audit(path: Path) -> dict[str, Any] | None:
    return cast(dict[str, Any] | None, _audit._read_audit(path))


def _audit_timestamp(audit: dict[str, Any]) -> Any:
    return _audit._audit_timestamp(audit)


def audit_retention_summary(config: BridgeConfig, *, cleanup: bool) -> dict[str, Any]:
    """Report or delete expired Slack audit JSON files without exposing paths."""

    return cast(
        dict[str, Any],
        _audit.audit_retention_summary(config, cleanup=cleanup, repo_root=Path(REPO_ROOT)),
    )


def _ensure_event_not_processed(path: Path, *, config: BridgeConfig) -> None:
    _audit._ensure_event_not_processed(path, config=config, repo_root=Path(REPO_ROOT))


def _approval_prefix(config: BridgeConfig, command: OperatorCommand) -> str | None:
    return cast(str | None, _audit._approval_prefix(config, command))


def _audit_payload(
    *,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _audit._audit_payload(
            event=event,
            command=command,
            config=config,
            status=status,
            failure_class=failure_class,
        ),
    )


def _write_audit(
    *,
    path: Path,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None = None,
) -> None:
    _audit._write_audit(
        path=path,
        event=event,
        command=command,
        config=config,
        repo_root=Path(REPO_ROOT),
        status=status,
        failure_class=failure_class,
    )


def _write_audit_exclusive(
    *,
    path: Path,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None = None,
) -> None:
    _audit._write_audit_exclusive(
        path=path,
        event=event,
        command=command,
        config=config,
        repo_root=Path(REPO_ROOT),
        status=status,
        failure_class=failure_class,
    )


def _preflight_operator_ledger_event(config: BridgeConfig) -> None:
    try:
        _operator_ledger.preflight_slack_bridge_operator_ledger_event(
            task_packet_id=config.operator_ledger_task_packet_id,
            repo_root=Path(REPO_ROOT),
        )
    except _operator_ledger.OperatorLedgerError as exc:
        raise SlackSocketAuditError("Experiment operator ledger evidence is unavailable.") from exc


def _write_operator_ledger_event(
    *,
    config: BridgeConfig,
    event: OperatorEvent,
    command: OperatorCommand,
    audit_path: Path,
    status: str,
    failure_class: str | None = None,
) -> str:
    event_hash = _sha256_text(event.event_id)
    approval_prefix = _approval_prefix(config, command)
    if status == "dispatched" and approval_prefix is not None:
        review_outcome = "approved"
    elif status == "rejected":
        review_outcome = "rejected"
    else:
        review_outcome = "pending"
    try:
        ledger_path = _operator_ledger.write_slack_bridge_operator_ledger_event(
            task_packet_id=config.operator_ledger_task_packet_id,
            command_kind=command.kind,
            status=status,
            dispatch_mode=config.dispatch_mode,
            workflow_file=config.workflow_file,
            workflow_ref=config.workflow_ref,
            event_hash=event_hash,
            channel_hash=_sha256_text(event.channel_id),
            user_hash=_sha256_text(event.user_id),
            team_hash=_safe_hash(event.team_id),
            branch_hash=_safe_hash(command.branch_ref),
            hypothesis_hash=_safe_hash(command.hypothesis),
            slack_audit_path=audit_path,
            failure_class=failure_class,
            human_review_outcome=review_outcome,
            retention_days=config.audit_retention_days,
            repo_root=Path(REPO_ROOT),
        )
    except _operator_ledger.OperatorLedgerError as exc:
        raise SlackSocketAuditError("Experiment operator ledger evidence is unavailable.") from exc
    return cast(str, normalize_repo_path(ledger_path))


def _claim_event(
    path: Path, *, event: OperatorEvent, command: OperatorCommand, config: BridgeConfig
) -> None:
    _audit._claim_event(
        path,
        event=event,
        command=command,
        config=config,
        repo_root=Path(REPO_ROOT),
    )


def _rate_limit_claim_dir(
    config: BridgeConfig, *, lock_dir_name: str = RATE_LIMIT_LOCK_DIR
) -> Path:
    return cast(Path, _audit._rate_limit_claim_dir(config, lock_dir_name=lock_dir_name))


def _read_rate_limit_claim(lock_dir: Path) -> Any:
    return _audit._read_rate_limit_claim(lock_dir)


def _remove_stale_rate_limit_claim(lock_dir: Path) -> None:
    _audit._remove_stale_rate_limit_claim(lock_dir)


def _partial_rate_limit_claim_is_stale(lock_dir: Path, *, config: BridgeConfig) -> bool:
    return cast(bool, _audit._partial_rate_limit_claim_is_stale(lock_dir, config=config))


def _cleanup_partial_rate_limit_claim(lock_dir: Path) -> None:
    _audit._cleanup_partial_rate_limit_claim(lock_dir)


def _claim_rate_limit(
    config: BridgeConfig,
    event: OperatorEvent,
    *,
    lock_dir_name: str = RATE_LIMIT_LOCK_DIR,
) -> None:
    _audit._claim_rate_limit(
        config,
        event,
        repo_root=Path(REPO_ROOT),
        lock_dir_name=lock_dir_name,
        remove_stale_rate_limit_claim=_remove_stale_rate_limit_claim,
    )


def _claim_rejected_event_audit_throttle(config: BridgeConfig, event: OperatorEvent) -> None:
    """Bound rejected audit writes without consuming the main operator throttle."""

    _claim_rate_limit(config, event, lock_dir_name=REJECTED_RATE_LIMIT_LOCK_DIR)


def _check_rate_limit(config: BridgeConfig) -> None:
    _audit._check_rate_limit(config)


def _require_execute_config(config: BridgeConfig) -> tuple[str, str]:
    return cast(tuple[str, str], _dispatch._require_execute_config(config))


def _github_dispatch_inputs(command: OperatorCommand, *, config: BridgeConfig) -> dict[str, str]:
    return cast(dict[str, str], _dispatch._github_dispatch_inputs(command, config=config))


def _send_github_workflow_dispatch(
    *,
    repo: str,
    workflow_file: str,
    ref: str,
    inputs: dict[str, str],
    token: str,
    timeout_seconds: int,
) -> None:
    _dispatch._send_github_workflow_dispatch(
        repo=repo,
        workflow_file=workflow_file,
        ref=ref,
        inputs=inputs,
        token=token,
        timeout_seconds=timeout_seconds,
    )


def _send_slack_api_request(
    *,
    method: str,
    token: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _transport._send_slack_api_request(
            method=method,
            token=token,
            timeout_seconds=timeout_seconds,
        ),
    )


def _require_live_smoke_runtime(config: BridgeConfig) -> None:
    _transport._require_live_smoke_runtime(config)


def validate_live_smoke(
    config: BridgeConfig,
    *,
    branch_ref: str | None = None,
    hypothesis_sha256: str | None = None,
    slack_api_transport: SlackApiTransport | None = None,
) -> dict[str, Any]:
    """Run bounded live-smoke checks and return a redacted status payload."""

    return cast(
        dict[str, Any],
        _transport.validate_live_smoke(
            config,
            branch_ref=branch_ref,
            hypothesis_sha256=hypothesis_sha256,
            slack_api_transport=slack_api_transport or _send_slack_api_request,
        ),
    )


def process_operator_event(
    event: OperatorEvent,
    config: BridgeConfig,
    *,
    dispatch_transport: WorkflowDispatchTransport | None = None,
) -> BridgeDecision:
    """Authorize, audit, and optionally dispatch one Slack operator event."""

    audit_path = _audit_path(config, event)
    _ensure_event_not_processed(audit_path, config=config)
    try:
        _require_authorized_event(event, config)
        command = parse_operator_command(event.text, command_hint=event.command_hint)
    except SlackSocketCommandError:
        command = OperatorCommand(kind="rejected")
        _claim_rejected_event_audit_throttle(config, event)
        _write_audit_exclusive(
            path=audit_path,
            event=event,
            command=command,
            config=config,
            status="rejected",
            failure_class="command_rejected",
        )
        _write_operator_ledger_event(
            config=config,
            event=event,
            command=command,
            audit_path=audit_path,
            status="rejected",
            failure_class="command_rejected",
        )
        raise
    dispatchable_command = command.kind == "run-experiment"
    if dispatchable_command:
        _preflight_operator_ledger_event(config)
    _claim_event(audit_path, event=event, command=command, config=config)
    try:
        _check_rate_limit(config)
        _claim_rate_limit(config, event)
    except SlackSocketAuditError:
        _write_audit(
            path=audit_path,
            event=event,
            command=command,
            config=config,
            status="failed",
            failure_class="rate_limited",
        )
        if dispatchable_command:
            _write_operator_ledger_event(
                config=config,
                event=event,
                command=command,
                audit_path=audit_path,
                status="failed",
                failure_class="rate_limited",
            )
        raise
    status = "dry_run"
    failure_class: str | None = None
    try:
        if config.dispatch_mode == "execute" and command.kind == "run-experiment":
            repo, token = _require_execute_config(config)
            transport = dispatch_transport or _send_github_workflow_dispatch
            transport(
                repo=repo,
                workflow_file=config.workflow_file,
                ref=config.workflow_ref,
                inputs=_github_dispatch_inputs(command, config=config),
                token=token,
                timeout_seconds=config.timeout_seconds,
            )
            status = "dispatched"
        elif config.dispatch_mode == "execute":
            status = "dry_run"
    except SlackSocketBridgeError as exc:
        failure_class = "dispatch_failed"
        _write_audit(
            path=audit_path,
            event=event,
            command=command,
            config=config,
            status="failed",
            failure_class=failure_class,
        )
        _write_operator_ledger_event(
            config=config,
            event=event,
            command=command,
            audit_path=audit_path,
            status="failed",
            failure_class=failure_class,
        )
        raise SlackSocketDispatchError("Slack operator dispatch failed.") from exc
    _write_audit(path=audit_path, event=event, command=command, config=config, status=status)
    operator_ledger_ref = (
        _write_operator_ledger_event(
            config=config,
            event=event,
            command=command,
            audit_path=audit_path,
            status=status,
        )
        if dispatchable_command
        else None
    )
    return BridgeDecision(
        status=status,
        command_kind=command.kind,
        dispatch_mode=config.dispatch_mode,
        audit_path=audit_path,
        event_hash=_sha256_text(event.event_id),
        channel_hash=_sha256_text(event.channel_id),
        user_hash=_sha256_text(event.user_id),
        workflow_file=config.workflow_file,
        workflow_ref=config.workflow_ref,
        branch_hash=_safe_hash(command.branch_ref),
        hypothesis_hash=_safe_hash(command.hypothesis),
        approval_hash=_approval_prefix(config, command),
        failure_class=failure_class,
        operator_ledger_ref=operator_ledger_ref,
    )


def process_payload(
    payload: dict[str, Any],
    config: BridgeConfig,
    *,
    dispatch_transport: WorkflowDispatchTransport | None = None,
) -> BridgeDecision:
    """Process one Slack payload and write hash-only audit evidence."""

    event = normalize_slack_payload(payload)
    return process_operator_event(event, config, dispatch_transport=dispatch_transport)


def _require_live_socket_runtime(config: BridgeConfig) -> None:
    if config.slack_app_token is None or config.slack_bot_token is None:
        raise SlackSocketConfigError("Slack Socket Mode configuration is incomplete.")
    if not config.allowed_channels or not config.allowed_users or not config.allowed_teams:
        raise SlackSocketConfigError("Slack Socket Mode allowlist configuration is incomplete.")
    _load_slack_bolt()


def _load_slack_bolt() -> tuple[Any, Any]:
    return cast(tuple[Any, Any], _transport._load_slack_bolt())


def run_socket_listener(config: BridgeConfig) -> int:
    """Run the optional live Socket Mode listener when operator deps exist."""

    _require_live_socket_runtime(config)
    App, SocketModeHandler = _load_slack_bolt()
    app = App(token=config.slack_bot_token)

    def _handle_command(
        ack: Callable[[], None], body: dict[str, Any], respond: Callable[[str], None]
    ) -> None:
        ack()
        try:
            decision = process_payload(body, config)
            event = normalize_slack_payload(body)
            command = parse_operator_command(event.text, command_hint=event.command_hint)
            respond(_format_command_reply(command, config, decision=decision))
        except SlackSocketBridgeError as exc:
            LOGGER.warning(
                "Experiment Runner bridge rejected Slack request: failure_class=%s",
                exc.__class__.__name__,
            )
            respond("Experiment Runner bridge rejected the request. No sensitive details included.")

    app.command("/run-experiment")(_handle_command)
    app.command("/pulseplate-runner")(_handle_command)
    handler = SocketModeHandler(app, config.slack_app_token)
    handler.start()
    return 0


def _format_command_reply(
    command: OperatorCommand,
    config: BridgeConfig,
    *,
    decision: BridgeDecision | None = None,
) -> str:
    """Return the operator-visible reply for one processed command."""

    if command.kind == "help":
        return cast(str, render_operator_help_message().as_text())
    if command.kind == "status":
        excluded_event_hash = (
            decision.event_hash
            if decision is not None and decision.command_kind == "status"
            else None
        )
        return cast(
            str,
            render_operator_status_message(
                config,
                operator_ledger_summary=render_latest_operator_ledger_summary(
                    exclude_event_hash=excluded_event_hash,
                ),
            ).as_text(),
        )
    if command.kind == "kpp-status":
        return cast(str, render_kpp_status_overview().as_text())
    if command.kind == "mvp-evidence":
        return cast(str, render_mvp_evidence_summary().as_text())
    if command.kind == "run-experiment":
        if decision is not None and decision.status == "dispatched":
            dry_run_flag = "true" if decision.approval_hash is None else "false"
            return cast(
                str,
                SlackSafeMessage(
                    message_type="dispatch_result",
                    header="Experiment Runner dispatch result",
                    status_line="dispatched",
                    scope="Fixed workflow dispatch was requested by an allowlisted operator.",
                    evidence_summary=(
                        f"workflow_file={decision.workflow_file}",
                        f"workflow_ref={config.workflow_ref}",
                        f"branch_hash={decision.branch_hash or 'none'}",
                        f"hypothesis_hash={decision.hypothesis_hash or 'none'}",
                        f"workflow_input_dry_run={dry_run_flag}",
                        f"approval_hash={decision.approval_hash or 'none'}",
                        f"operator_ledger_ref={decision.operator_ledger_ref or 'none'}",
                        f"operator_ledger_status={decision.status}",
                        "slack_authority=not_merge_readiness",
                    ),
                    action_required="Inspect GitHub workflow result; Slack does not prove readiness.",
                    artifact_refs=(".github/workflows/experiment-runner-dispatch.yml",),
                ).as_text(),
            )
        return cast(
            str,
            render_dispatch_dry_run_preview(
                command,
                operator_ledger_ref=decision.operator_ledger_ref if decision else None,
            ).as_text(),
        )
    raise SlackSocketCommandError("Slack operator command is invalid.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-json", default=None, help="Slack Socket Mode payload JSON path.")
    parser.add_argument(
        "--dispatch-mode",
        choices=("dry-run", "execute"),
        default="dry-run",
        help="Dry-run by default; execute requires GitHub auth and fixed workflow allowlist.",
    )
    parser.add_argument(
        "--audit-dir", default=None, help="Audit directory under artifacts/orchestration."
    )
    parser.add_argument("--repo", default=None, help="GitHub owner/repo for explicit execute mode.")
    parser.add_argument("--workflow-ref", default=DEFAULT_WORKFLOW_REF, help="Fixed workflow ref.")
    parser.add_argument(
        "--run-socket",
        action="store_true",
        help="Run live Socket Mode listener; requires optional Slack SDK and runtime secrets.",
    )
    parser.add_argument(
        "--validate-runtime",
        action="store_true",
        help="Validate bridge runtime config without connecting to Slack or GitHub.",
    )
    parser.add_argument(
        "--validate-secret-presence",
        action="store_true",
        help="Report live-smoke secret and allowlist presence without printing values.",
    )
    parser.add_argument(
        "--validate-live-smoke",
        action="store_true",
        help="Run bounded live-smoke validation for Socket Mode and bot auth, then exit.",
    )
    parser.add_argument(
        "--validate-smoke-inputs",
        action="store_true",
        help="Validate manual smoke branch/digest inputs without printing values.",
    )
    parser.add_argument(
        "--validate-dispatch-inputs",
        action="store_true",
        dest="validate_smoke_inputs",
        help="Alias for validating bounded dispatch branch/digest inputs.",
    )
    parser.add_argument(
        "--validate-live-approval",
        action="store_true",
        dest="validate_live_approval",
        help="Validate live-dispatch approval digest without printing the raw value.",
    )
    parser.add_argument(
        "--branch-ref",
        default=None,
        help="Manual smoke branch ref; if omitted, read runtime env.",
    )
    parser.add_argument(
        "--hypothesis-sha256",
        default=None,
        help="Manual smoke hypothesis digest; if omitted, read runtime env.",
    )
    parser.add_argument(
        "--audit-retention",
        choices=("none", "report", "cleanup"),
        default="none",
        help="Report or explicitly clean up expired local Slack audit artifacts.",
    )
    parser.add_argument(
        "--reply-format",
        choices=("payload", "text"),
        default="payload",
        help="For --event-json, print public payload JSON or the Slack-safe reply text.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.validate_smoke_inputs:
            print(
                json.dumps(
                    {
                        **validate_live_smoke_inputs(
                            branch_ref=args.branch_ref,
                            hypothesis_sha256=args.hypothesis_sha256,
                        ),
                        "status": "pass",
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.validate_secret_presence:
            return 0 if validate_secret_presence()["status"] == "pass" else 1
        if args.validate_live_approval:
            try:
                approval = _live_approval_sha256()
            except SlackSocketConfigError:
                print("FAIL: Slack live-dispatch approval is missing or invalid.")
                return 1
            if approval is None:
                print("FAIL: Slack live-dispatch approval is missing or invalid.")
                return 1
            print(json.dumps({"approval_status": "valid", "status": "pass"}, sort_keys=True))
            return 0
        config = build_config(
            dispatch_mode=args.dispatch_mode,
            audit_dir=args.audit_dir,
            repo=args.repo,
            workflow_ref=args.workflow_ref,
        )
        if args.audit_retention != "none":
            print(
                json.dumps(
                    audit_retention_summary(config, cleanup=args.audit_retention == "cleanup"),
                    sort_keys=True,
                )
            )
            return 0
        if args.validate_live_smoke:
            print(
                json.dumps(
                    validate_live_smoke(
                        config,
                        branch_ref=args.branch_ref,
                        hypothesis_sha256=args.hypothesis_sha256,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if args.validate_runtime:
            if config.dispatch_mode == "execute":
                _require_execute_config(config)
            if args.run_socket:
                _require_live_socket_runtime(config)
            _preflight_operator_ledger_event(config)
            print(
                json.dumps(
                    {"dispatch_mode": config.dispatch_mode, "status": "pass"}, sort_keys=True
                )
            )
            return 0
        if args.run_socket:
            return run_socket_listener(config)
        if args.event_json is None:
            print(
                json.dumps(
                    {"dispatch_mode": config.dispatch_mode, "status": "idle"}, sort_keys=True
                )
            )
            return 0
        payload = _read_json_object(Path(args.event_json).expanduser())
        decision = process_payload(payload, config)
    except SlackSocketBridgeError as exc:
        print(f"FAIL: {exc}")
        return 1
    if args.reply_format == "text":
        try:
            event = normalize_slack_payload(payload)
            command = parse_operator_command(event.text, command_hint=event.command_hint)
            print(_format_command_reply(command, config, decision=decision))
        except SlackSocketBridgeError as exc:
            print(f"FAIL: {exc}")
            return 1
        return 0
    print(json.dumps(decision.public_payload(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
