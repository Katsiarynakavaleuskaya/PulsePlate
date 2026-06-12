"""Typed models and safe rendering primitives for the Slack bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Literal, Protocol

from scripts.orchestration.context_pack import normalize_repo_path
from scripts.orchestration.experiment_slack_redaction import slack_text as _slack_text


class SlackSocketBridgeError(RuntimeError):
    """Bridge failures with sanitized diagnostics."""


class SlackSocketConfigError(SlackSocketBridgeError):
    """Runtime configuration is missing or invalid."""


class SlackSocketCommandError(SlackSocketBridgeError):
    """Operator command payload is malformed or unauthorized."""


class SlackSocketAuditError(SlackSocketBridgeError):
    """Local audit state blocks safe execution."""


class SlackSocketDispatchError(SlackSocketBridgeError):
    """GitHub workflow dispatch failed without exposing provider details."""


class WorkflowDispatchTransport(Protocol):
    """Fakeable GitHub workflow dispatch transport."""

    def __call__(
        self,
        *,
        repo: str,
        workflow_file: str,
        ref: str,
        inputs: dict[str, str],
        token: str,
        timeout_seconds: int,
    ) -> None:
        """Dispatch a fixed workflow with sanitized typed inputs."""


class SlackApiTransport(Protocol):
    """Fakeable Slack Web API transport for bounded live-smoke checks."""

    def __call__(
        self,
        *,
        method: str,
        token: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """Call one fixed Slack Web API method and return parsed JSON."""


GitHubDispatchAuthClass = Literal["installation", "runtime"]


@dataclass(frozen=True)
class GitHubDispatchAuth:
    """Opaque runtime GitHub credential classification for fixed workflow dispatch."""

    token: str = field(repr=False)
    source_env: str
    auth_class: GitHubDispatchAuthClass

    @property
    def is_installation_token(self) -> bool:
        """Return whether the opaque token is a GitHub App installation token class."""

        return self.auth_class == "installation"


@dataclass(frozen=True)
class GitHubDispatchTarget:
    """Validated fixed GitHub workflow dispatch target."""

    repo: str = field(repr=False)
    workflow_file: str
    workflow_ref: str
    current_repo: str | None = field(default=None, repr=False)
    repo_allowlist: frozenset[str] = field(default_factory=frozenset, repr=False)

    @property
    def is_cross_repo(self) -> bool:
        """Return whether the known ambient repository differs from the target."""

        return self.current_repo is not None and self.repo != self.current_repo

    @property
    def is_allowlisted(self) -> bool:
        """Return whether this target is exactly present in the runtime allowlist."""

        return self.repo in self.repo_allowlist


@dataclass(frozen=True)
class GitHubDispatchConfig:
    """Typed GitHub workflow dispatch adapter config."""

    auth: GitHubDispatchAuth | None
    target: GitHubDispatchTarget | None


@dataclass(frozen=True)
class BridgeConfig:
    """Runtime configuration for one bridge event or validation pass."""

    dispatch_mode: str
    allowed_channels: frozenset[str]
    allowed_users: frozenset[str]
    allowed_teams: frozenset[str]
    audit_dir: Path
    repo: str | None
    workflow_file: str
    workflow_ref: str
    timeout_seconds: int
    min_interval_seconds: int
    audit_retention_days: int
    slack_app_token: str | None = field(repr=False)
    slack_bot_token: str | None = field(repr=False)
    github_token: str | None = field(repr=False)
    live_approval_sha256: str | None
    workflow_dispatch_secret: str | None = field(repr=False)
    operator_ledger_task_packet_id: str
    github_dispatch: GitHubDispatchConfig | None = None


@dataclass(frozen=True)
class OperatorEvent:
    """Normalized Slack operator event with raw fields kept out of audits."""

    event_id: str
    channel_id: str
    user_id: str
    team_id: str | None
    text: str
    command_hint: str | None = None


@dataclass(frozen=True)
class OperatorCommand:
    """Typed, validated bridge command."""

    kind: str
    branch_ref: str | None = None
    hypothesis: str | None = None


@dataclass(frozen=True)
class SlackSafeMessage:
    """Deterministic operator message payload safe for Slack display."""

    message_type: str
    header: str
    status_line: str
    scope: str
    evidence_summary: tuple[str, ...]
    action_required: str
    artifact_refs: tuple[str, ...] = ()
    redaction_notice: str = (
        "No sensitive user data, raw Slack identifiers, raw hypotheses, tokens, local paths, "
        "oracle output, or patch text included."
    )

    def as_text(self) -> str:
        """Render stable Slack mrkdwn text without untrusted formatting."""

        artifact_lines = self.artifact_refs or ("none",)
        evidence_lines = self.evidence_summary or ("none",)
        sections = [
            f"*{_slack_text(self.header)}*",
            f"Status: `{_slack_text(self.status_line)}`",
            f"Scope: {_slack_text(self.scope)}",
            "Evidence summary:",
            *(f"- {_slack_text(line)}" for line in evidence_lines),
            "Artifact/reference:",
            *(f"- `{_slack_text(line)}`" for line in artifact_lines),
            f"Action required: {_slack_text(self.action_required)}",
            f"Redaction: {_slack_text(self.redaction_notice)}",
        ]
        return _bounded_text("\n".join(sections))


@dataclass(frozen=True)
class BridgeDecision:
    """Bridge outcome safe to print as JSON."""

    status: str
    command_kind: str
    dispatch_mode: str
    audit_path: Path
    event_hash: str
    channel_hash: str
    user_hash: str
    workflow_file: str
    workflow_ref: str
    branch_hash: str | None = None
    hypothesis_hash: str | None = None
    approval_hash: str | None = None
    failure_class: str | None = None
    operator_ledger_ref: str | None = None
    operator_ledger_status: str | None = None

    def public_payload(self) -> dict[str, Any]:
        """Return a sanitized payload for stdout or tests."""

        return {
            "approval_hash": self.approval_hash or "none",
            "audit": normalize_repo_path(self.audit_path),
            "branch_hash": self.branch_hash,
            "channel_hash": self.channel_hash,
            "command_kind": self.command_kind,
            "dispatch_mode": self.dispatch_mode,
            "event_hash": self.event_hash,
            "failure_class": self.failure_class or "none",
            "hypothesis_hash": self.hypothesis_hash,
            "operator_ledger_ref": self.operator_ledger_ref or "none",
            "operator_ledger_status": self.operator_ledger_status or "none",
            "status": self.status,
            "user_hash": self.user_hash,
            "workflow_file": self.workflow_file,
            "workflow_ref": self.workflow_ref,
        }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_hash(value: str | None) -> str | None:
    if value is None:
        return None
    return _sha256_text(value)


def _bounded_text(value: str, *, limit: int = 2800) -> str:
    """Bound Slack-visible text and make truncation explicit."""

    if len(value) <= limit:
        return value
    return value[: limit - 20].rstrip() + "\n[truncated=true]"
