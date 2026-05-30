"""Slack-safe rendering helpers for Experiment Runner operator messages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scripts.orchestration.experiment_slack_bridge_constants import (
    DEFAULT_WORKFLOW_FILE,
    DEFAULT_WORKFLOW_REF,
)
from scripts.orchestration.experiment_slack_bridge_models import (
    BridgeConfig,
    OperatorCommand,
    SlackSafeMessage,
    _safe_hash,
)
from scripts.orchestration.experiment_slack_redaction import slack_text as _slack_text


def render_mvp_evidence_summary(
    *,
    snapshot_reader: Callable[[], Any],
    allowed_event_names: set[str] | frozenset[str],
) -> SlackSafeMessage:
    """Render MVP evidence summary from latest snapshot, falling back to static contract."""

    try:
        snapshot = snapshot_reader()
    except (ValueError, OSError, TypeError):
        snapshot = None

    if snapshot is not None:
        present_count = sum(1 for v in snapshot.event_aggregates.values() if v > 0)
        route_str = ",".join(snapshot.route_buckets) if snapshot.route_buckets else "none"
        auth_str = ",".join(snapshot.auth_state_buckets) if snapshot.auth_state_buckets else "none"
        coverage_preview = "; ".join(
            flag for flag in snapshot.coverage_flags if flag.endswith("=present")
        )
        if not coverage_preview:
            coverage_preview = "no_events_observed"
        return SlackSafeMessage(
            message_type="mvp_evidence_summary",
            header="MVP evidence snapshot summary",
            status_line="snapshot_backed",
            scope=(
                "Dynamic Guided Planning Preview snapshot; aggregate-only; "
                "no runtime analytics backend."
            ),
            evidence_summary=(
                f"present_event_count={present_count}",
                f"route_buckets={_slack_text(route_str)}",
                f"auth_state_buckets={_slack_text(auth_str)}",
                f"coverage_preview={_slack_text(coverage_preview)}",
                f"policy_version={snapshot.policy_version}",
            ),
            action_required="Human review required for PR/merge decisions; Slack is display-only.",
            artifact_refs=(
                "frontend/src/lib/mvpObservability.ts",
                "scripts/orchestration/mvp_evidence_snapshot.py",
            ),
        )

    return SlackSafeMessage(
        message_type="mvp_evidence_summary",
        header="MVP evidence contract summary",
        status_line="advisory_operator_summary",
        scope=(
            "Static Guided Planning Preview event contract from #1842-#1844; "
            "no runtime analytics backend."
        ),
        evidence_summary=(
            f"safe_event_count={len(allowed_event_names)}",
            "route_path=/app",
            "save_continue_progress_events=present",
            "wellness_boundary_event=present",
            "forbidden_user_data=omitted",
        ),
        action_required="Human review required for PR/merge decisions; Slack is display-only.",
        artifact_refs=("frontend/src/lib/mvpObservability.ts", "frontend/src/pages/Home.tsx"),
    )


def render_dispatch_dry_run_preview(command: OperatorCommand) -> SlackSafeMessage:
    """Render a dry-run-only dispatch preview without raw branch or hypothesis text."""

    return SlackSafeMessage(
        message_type="dispatch_dry_run_preview",
        header="Dispatch dry-run preview",
        status_line="dry_run_only",
        scope="Fixed Experiment Runner dispatch workflow preview; no workflow sent by renderer.",
        evidence_summary=(
            f"workflow_file={DEFAULT_WORKFLOW_FILE}",
            f"workflow_ref={DEFAULT_WORKFLOW_REF}",
            f"branch_hash={_safe_hash(command.branch_ref) or 'none'}",
            f"hypothesis_hash={_safe_hash(command.hypothesis) or 'none'}",
            "dry_run=true",
        ),
        action_required="Human approval and existing execute-mode gate required for dispatch.",
        artifact_refs=(".github/workflows/experiment-runner-dispatch.yml",),
    )


def render_operator_help_message() -> SlackSafeMessage:
    """Render static operator help without authority claims."""

    return SlackSafeMessage(
        message_type="operator_help",
        header="Experiment Runner Slack operator help",
        status_line="display_only_commands",
        scope="Allowlisted operator command boundary; not PR, review, merge, or Git identity authority.",
        evidence_summary=(
            "help: show this bounded command summary",
            "status: show bridge status and authority boundary",
            "kpp-status: show KPP outcome catalog and routing summary",
            "mvp-evidence: show Guided Planning MVP evidence coverage summary",
            "run-experiment <branch> <hypothesis>: dry-run-first fixed workflow preview/dispatch path",
        ),
        action_required="Use repo gates and GitHub review for all merge decisions.",
        artifact_refs=("docs/orchestration/EXPERIMENT_RUNNER_SLACK_SOCKET_OPERATOR_RUNBOOK.md",),
    )


def render_operator_status_message(config: BridgeConfig) -> SlackSafeMessage:
    """Render sanitized bridge status without exposing runtime IDs or tokens."""

    return SlackSafeMessage(
        message_type="operator_status",
        header="Experiment Runner Slack operator status",
        status_line=(
            "configured" if config.allowed_channels and config.allowed_users else "incomplete"
        ),
        scope="Operator bridge status; advisory only and not merge readiness.",
        evidence_summary=(
            f"dispatch_mode={config.dispatch_mode}",
            f"workflow_file={config.workflow_file}",
            f"workflow_ref={config.workflow_ref}",
            f"channel_allowlist_present={str(bool(config.allowed_channels)).lower()}",
            f"user_allowlist_present={str(bool(config.allowed_users)).lower()}",
            f"team_allowlist_present={str(bool(config.allowed_teams)).lower()}",
            f"rate_limit_seconds={config.min_interval_seconds}",
            f"audit_retention_days={config.audit_retention_days}",
        ),
        action_required="Keep dry-run unless a reviewed PR promotes bounded execution.",
        artifact_refs=("artifacts/orchestration/experiments/slack_socket_bridge",),
    )


def render_kpp_status_overview() -> SlackSafeMessage:
    """Render bounded KPP outcome catalog for operator awareness."""

    return SlackSafeMessage(
        message_type="kpp_status_overview",
        header="Experiment Runner KPP outcome catalog",
        status_line="display_only",
        scope="KPP routing outcomes are deterministic and redacted before Slack display.",
        evidence_summary=(
            "PROMOTE: high-signal result ready for promotion review",
            "DEFER: result deferred to backlog or follow-up lane",
            "DISCARD: falsification or no-signal outcome",
            "FAIL: experiment failed; inspect failure_class and artifact reference",
            "ORACLE_VIOLATION: oracle contract violation (security-sensitive)",
            "SURFACE_BREACH: mutation outside allowed surface (security-sensitive)",
        ),
        action_required="Use kpp-status for awareness only; all promotion decisions run through repo gates.",
        artifact_refs=("scripts/orchestration/experiment_slack_kpp_renderer.py",),
    )
