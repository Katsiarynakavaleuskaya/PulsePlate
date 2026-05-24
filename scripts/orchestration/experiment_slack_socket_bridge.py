#!/usr/bin/env python3
"""Dry-run-first Slack Socket Mode bridge for Experiment Runner operators."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Protocol

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


AUDIT_ARTIFACT_DIR = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "slack_socket_bridge"
)
SLACK_APP_AUTH_ENV = "SLACK_APP_" + "".join(("TO", "KEN"))
SLACK_BOT_AUTH_ENV = "SLACK_BOT_" + "".join(("TO", "KEN"))
SLACK_CHANNEL_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST"
SLACK_USER_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST"
SLACK_TEAM_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST"
BRIDGE_MIN_INTERVAL_ENV = "EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS"
BRIDGE_TIMEOUT_ENV = "EXPERIMENT_SLACK_SOCKET_TIMEOUT_SECONDS"
GITHUB_API_HOST = "api.github.com"
DEFAULT_WORKFLOW_FILE = "experiment-runner-slack-socket-smoke.yml"
DEFAULT_WORKFLOW_REF = "main"
ALLOWED_WORKFLOW_REFS = {DEFAULT_WORKFLOW_REF}
SAFE_SLACK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,79}$")
SAFE_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
SHELL_META_RE = re.compile(r"[;&|`$<>\\\\]")
LOCAL_PATH_RE = re.compile(r"(^|\s)(/Users/|/private/|/tmp/|\.{1,2}/|[A-Za-z]:\\|\\\\)")
ENV_ASSIGNMENT_RE = re.compile(r"(^|\s)[A-Za-z_][A-Za-z0-9_]*=")
SECRET_SHAPED_RE = re.compile(
    r"(xapp-[A-Za-z0-9-]{10,}|xox[abcprs]-[A-Za-z0-9-]{10,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{10,}|sk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE,
)
SLACK_APP_TOKEN_RE = re.compile(r"^xapp-[A-Za-z0-9-]{10,}$")
SLACK_BOT_TOKEN_RE = re.compile(r"^xoxb-[A-Za-z0-9-]{10,}$")
GITHUB_TOKEN_RE = re.compile(r"^(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})$")
ALLOWED_COMMANDS = {"help", "status", "run-experiment"}
ALLOWED_WORKFLOWS = {DEFAULT_WORKFLOW_FILE}
RATE_LIMIT_LOCK_DIR = "rate_limit_claim"
RATE_LIMIT_CLAIM_MAX_ATTEMPTS = 10


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
    slack_app_token: str | None
    slack_bot_token: str | None
    github_token: str | None


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
    branch_hash: str | None = None
    hypothesis_hash: str | None = None
    failure_class: str | None = None

    def public_payload(self) -> dict[str, Any]:
        """Return a sanitized payload for stdout or tests."""

        return {
            "audit": normalize_repo_path(self.audit_path),
            "branch_hash": self.branch_hash,
            "channel_hash": self.channel_hash,
            "command_kind": self.command_kind,
            "dispatch_mode": self.dispatch_mode,
            "event_hash": self.event_hash,
            "failure_class": self.failure_class or "none",
            "hypothesis_hash": self.hypothesis_hash,
            "status": self.status,
            "user_hash": self.user_hash,
            "workflow_file": self.workflow_file,
        }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_hash(value: str | None) -> str | None:
    if value is None:
        return None
    return _sha256_text(value)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketCommandError("Slack operator event payload is invalid.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketCommandError("Slack operator event payload is invalid.")
    return payload


def _normalize_slack_id(raw_value: str, *, label: str) -> str:
    value = raw_value.strip()
    if not value or CONTROL_CHAR_RE.search(value) or not SAFE_SLACK_ID_RE.fullmatch(value):
        raise SlackSocketConfigError(f"{label} allowlist is invalid.")
    return value


def _allowlist_from_env(env_name: str, *, label: str) -> frozenset[str]:
    raw = os.environ.get(env_name, "")
    values: set[str] = set()
    for candidate in raw.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        values.add(_normalize_slack_id(candidate, label=label))
    return frozenset(values)


def _optional_token(env_name: str) -> str | None:
    token = os.environ.get(env_name, "").strip()
    if not token:
        return None
    token_pattern = {
        SLACK_APP_AUTH_ENV: SLACK_APP_TOKEN_RE,
        SLACK_BOT_AUTH_ENV: SLACK_BOT_TOKEN_RE,
    }.get(env_name)
    if token_pattern is None:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    if CONTROL_CHAR_RE.search(token) or "`" in token or token_pattern.fullmatch(token) is None:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    return token


def _github_token() -> str | None:
    token = os.environ.get("GH_TOKEN", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return None
    if CONTROL_CHAR_RE.search(token) or "`" in token or GITHUB_TOKEN_RE.fullmatch(token) is None:
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return token


def _positive_int_from_env(env_name: str, default: int, *, maximum: int) -> int:
    raw = os.environ.get(env_name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.") from exc
    if value <= 0 or value > maximum:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    return value


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlinked_existing_path(root: Path, candidate: Path, *, message: str) -> None:
    current = root
    if current.is_symlink():
        raise SlackSocketAuditError(message)
    for part in candidate.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise SlackSocketAuditError(message)


def _reject_symlinked_output_components(candidate: Path, *, artifact_dir: Path) -> None:
    repo_root = _normalized_absolute_path(Path(REPO_ROOT))
    artifact_root = _normalized_absolute_path(repo_root / "artifacts" / "orchestration")
    artifact_dir = _normalized_absolute_path(artifact_dir)
    candidate = _normalized_absolute_path(candidate)
    try:
        artifact_root.relative_to(repo_root)
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator audit directory must stay under artifacts/orchestration."
        ) from exc
    _reject_symlinked_existing_path(
        repo_root,
        artifact_root,
        message="Slack operator audit ancestors must not be symlinks.",
    )
    try:
        artifact_dir.relative_to(artifact_root)
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator audit directory must stay under artifacts/orchestration."
        ) from exc
    _reject_symlinked_existing_path(
        artifact_root,
        artifact_dir,
        message="Slack operator audit ancestors must not be symlinks.",
    )
    try:
        candidate.relative_to(artifact_dir)
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator audit directory must stay under artifacts/orchestration."
        ) from exc
    _reject_symlinked_existing_path(
        artifact_dir,
        candidate,
        message="Slack operator audit path must not traverse a symlink.",
    )


def _resolve_audit_dir(raw_audit_dir: str | None) -> Path:
    base_dir = _normalized_absolute_path(Path(AUDIT_ARTIFACT_DIR))
    candidate: Path = Path(raw_audit_dir).expanduser() if raw_audit_dir else base_dir
    if not candidate.is_absolute():
        candidate = _normalized_absolute_path(REPO_ROOT / candidate)
    else:
        candidate = _normalized_absolute_path(candidate)
    try:
        candidate.relative_to(_normalized_absolute_path(REPO_ROOT / "artifacts" / "orchestration"))
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator bridge audit directory must stay under artifacts/orchestration."
        ) from exc
    return candidate


def _validate_workflow_ref(ref: str) -> str:
    if ref not in ALLOWED_WORKFLOW_REFS or not _is_safe_ref(ref):
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return ref


def _validate_workflow_file(workflow_file: str) -> str:
    if workflow_file not in ALLOWED_WORKFLOWS:
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return workflow_file


def _validate_repo(raw_repo: str | None) -> str | None:
    if raw_repo is None or not raw_repo.strip():
        return None
    repo = raw_repo.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return repo


def build_config(
    *,
    dispatch_mode: str,
    audit_dir: str | None = None,
    repo: str | None = None,
    workflow_file: str = DEFAULT_WORKFLOW_FILE,
    workflow_ref: str = DEFAULT_WORKFLOW_REF,
) -> BridgeConfig:
    """Read sanitized bridge config from runtime env."""

    if dispatch_mode not in {"dry-run", "execute"}:
        raise SlackSocketConfigError("Slack operator bridge dispatch mode is invalid.")
    return BridgeConfig(
        dispatch_mode=dispatch_mode,
        allowed_channels=_allowlist_from_env(SLACK_CHANNEL_ALLOWLIST_ENV, label="channel"),
        allowed_users=_allowlist_from_env(SLACK_USER_ALLOWLIST_ENV, label="user"),
        allowed_teams=_allowlist_from_env(SLACK_TEAM_ALLOWLIST_ENV, label="team"),
        audit_dir=_resolve_audit_dir(audit_dir),
        repo=_validate_repo(repo or os.environ.get("GITHUB_REPOSITORY")),
        workflow_file=_validate_workflow_file(workflow_file),
        workflow_ref=_validate_workflow_ref(workflow_ref),
        timeout_seconds=_positive_int_from_env(BRIDGE_TIMEOUT_ENV, 10, maximum=30),
        min_interval_seconds=_positive_int_from_env(
            BRIDGE_MIN_INTERVAL_ENV,
            60,
            maximum=3600,
        ),
        slack_app_token=_optional_token(SLACK_APP_AUTH_ENV),
        slack_bot_token=_optional_token(SLACK_BOT_AUTH_ENV),
        github_token=_github_token(),
    )


def _is_safe_ref(value: str) -> bool:
    if (
        not value
        or CONTROL_CHAR_RE.search(value)
        or SHELL_META_RE.search(value)
        or not SAFE_BRANCH_RE.fullmatch(value)
        or value.startswith(("-", "/", "."))
        or value.endswith(("/", "."))
        or ".." in value
        or "//" in value
        or "@{" in value
    ):
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def _validate_hypothesis(value: str) -> str:
    hypothesis = value.strip()
    if (
        len(hypothesis) < 8
        or len(hypothesis) > 280
        or CONTROL_CHAR_RE.search(hypothesis)
        or SHELL_META_RE.search(hypothesis)
        or '"' in hypothesis
        or "'" in hypothesis
        or LOCAL_PATH_RE.search(hypothesis)
        or ENV_ASSIGNMENT_RE.search(hypothesis)
        or SECRET_SHAPED_RE.search(hypothesis)
    ):
        raise SlackSocketCommandError("Slack operator command is invalid.")
    return hypothesis


def parse_operator_command(text: str, *, command_hint: str | None = None) -> OperatorCommand:
    """Parse one bounded Slack operator command."""

    normalized = CONTROL_CHAR_RE.sub(" ", text).strip()
    normalized = re.sub(r"^(<@[A-Za-z0-9_-]+>\s*)+", "", normalized).strip()
    if command_hint == "/run-experiment":
        normalized = f"run-experiment {normalized}".strip()
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if not normalized:
        raise SlackSocketCommandError("Slack operator command is invalid.")
    verb, _separator, remainder = normalized.partition(" ")
    if verb not in ALLOWED_COMMANDS:
        raise SlackSocketCommandError("Slack operator command is invalid.")
    if verb in {"help", "status"}:
        if remainder.strip():
            raise SlackSocketCommandError("Slack operator command is invalid.")
        return OperatorCommand(kind=verb)
    branch, separator, hypothesis = remainder.strip().partition(" ")
    if not separator or not _is_safe_ref(branch):
        raise SlackSocketCommandError("Slack operator command is invalid.")
    return OperatorCommand(
        kind="run-experiment",
        branch_ref=branch,
        hypothesis=_validate_hypothesis(hypothesis),
    )


def normalize_slack_payload(payload: dict[str, Any]) -> OperatorEvent:
    """Normalize slash-command or app-mention payloads into one event shape."""

    raw_body = payload.get("payload")
    body: dict[str, Any] = raw_body if isinstance(raw_body, dict) else payload
    raw_event = body.get("event")
    event: dict[str, Any] = raw_event if isinstance(raw_event, dict) else {}
    raw_event_id = (
        payload.get("envelope_id")
        or body.get("envelope_id")
        or body.get("event_id")
        or event.get("client_msg_id")
    )
    if raw_event_id is None and body.get("trigger_id"):
        raw_event_id = f"trigger-{_sha256_text(str(body['trigger_id']))[:32]}"
    event_id = str(raw_event_id or "").strip()
    channel = str(body.get("channel_id") or event.get("channel") or "").strip()
    user = str(body.get("user_id") or event.get("user") or "").strip()
    team = str(body.get("team_id") or event.get("team") or "").strip() or None
    text = str(body.get("text") or event.get("text") or "").strip()
    command_hint = str(body.get("command") or "").strip() or None
    if not event_id or not channel or not user:
        raise SlackSocketCommandError("Slack operator event payload is invalid.")
    _normalize_slack_id(event_id, label="event")
    _normalize_slack_id(channel, label="channel")
    _normalize_slack_id(user, label="user")
    if team is not None:
        _normalize_slack_id(team, label="team")
    return OperatorEvent(
        event_id=event_id,
        channel_id=channel,
        user_id=user,
        team_id=team,
        text=text,
        command_hint=command_hint,
    )


def _require_authorized_event(event: OperatorEvent, config: BridgeConfig) -> None:
    if not config.allowed_channels or event.channel_id not in config.allowed_channels:
        raise SlackSocketCommandError("Slack operator channel is not allowed.")
    if not config.allowed_users or event.user_id not in config.allowed_users:
        raise SlackSocketCommandError("Slack operator user is not allowed.")
    if config.allowed_teams and event.team_id not in config.allowed_teams:
        raise SlackSocketCommandError("Slack operator workspace is not allowed.")


def _audit_path(config: BridgeConfig, event: OperatorEvent) -> Path:
    return config.audit_dir / f"{_sha256_text(event.event_id)}.json"


def _read_audit(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
    return payload


def _ensure_event_not_processed(path: Path, *, config: BridgeConfig) -> None:
    _reject_symlinked_output_components(
        path.absolute(), artifact_dir=Path(config.audit_dir).absolute()
    )
    existing = _read_audit(path)
    if existing is None:
        return
    if existing.get("status") in {"claimed", "dry_run", "dispatched", "failed", "rejected"}:
        raise SlackSocketAuditError("Slack operator event was already processed.")
    raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")


def _audit_payload(
    *,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None,
) -> dict[str, Any]:
    return {
        "branch_hash": _safe_hash(command.branch_ref),
        "channel_hash": _sha256_text(event.channel_id),
        "command_kind": command.kind,
        "dispatch_mode": config.dispatch_mode,
        "event_hash": _sha256_text(event.event_id),
        "failure_class": failure_class or "none",
        "hypothesis_hash": _safe_hash(command.hypothesis),
        "provider_type": "slack_socket_mode",
        "status": status,
        "team_hash": _safe_hash(event.team_id),
        "timestamp": _utcnow().isoformat(),
        "user_hash": _sha256_text(event.user_id),
        "workflow_file": config.workflow_file,
    }


def _write_audit(
    *,
    path: Path,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None = None,
) -> None:
    _reject_symlinked_output_components(
        path.absolute(), artifact_dir=Path(config.audit_dir).absolute()
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                _audit_payload(
                    event=event,
                    command=command,
                    config=config,
                    status=status,
                    failure_class=failure_class,
                ),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SlackSocketAuditError("Unable to write Slack operator audit artifact.") from exc


def _write_audit_exclusive(
    *,
    path: Path,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None = None,
) -> None:
    _reject_symlinked_output_components(
        path.absolute(), artifact_dir=Path(config.audit_dir).absolute()
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to prepare Slack operator audit artifact path."
        ) from exc
    payload = _audit_payload(
        event=event,
        command=command,
        config=config,
        status=status,
        failure_class=failure_class,
    )
    try:
        with path.open("x", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    except FileExistsError:
        existing = _read_audit(path)
        if existing is None:
            raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
        raise SlackSocketAuditError("Slack operator event was already processed.")
    except OSError as exc:
        raise SlackSocketAuditError("Unable to write Slack operator audit artifact.") from exc


def _claim_event(
    path: Path, *, event: OperatorEvent, command: OperatorCommand, config: BridgeConfig
) -> None:
    _reject_symlinked_output_components(
        path.absolute(), artifact_dir=Path(config.audit_dir).absolute()
    )
    payload = _audit_payload(
        event=event,
        command=command,
        config=config,
        status="claimed",
        failure_class=None,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to prepare Slack operator audit artifact path."
        ) from exc
    try:
        with path.open("x", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return
    except FileExistsError:
        existing = _read_audit(path)
    except OSError as exc:
        raise SlackSocketAuditError("Unable to claim Slack operator event audit artifact.") from exc
    if existing is None or existing.get("status") not in {
        "claimed",
        "dry_run",
        "dispatched",
        "failed",
        "rejected",
    }:
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
    raise SlackSocketAuditError("Slack operator event was already processed.")


def _rate_limit_claim_dir(config: BridgeConfig) -> Path:
    return config.audit_dir / RATE_LIMIT_LOCK_DIR


def _read_rate_limit_claim(lock_dir: Path) -> datetime:
    claim_path = lock_dir / "claim.json"
    try:
        payload = json.loads(claim_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.")
    timestamp_raw = payload.get("timestamp")
    if not isinstance(timestamp_raw, str):
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.")
    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except ValueError as exc:
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.") from exc
    if timestamp.tzinfo is None:
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.")
    return timestamp.astimezone(timezone.utc)


def _remove_stale_rate_limit_claim(lock_dir: Path) -> None:
    try:
        (lock_dir / "claim.json").unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clear stale Slack operator rate-limit claim."
        ) from exc
    try:
        lock_dir.rmdir()
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clear stale Slack operator rate-limit claim."
        ) from exc


def _cleanup_partial_rate_limit_claim(lock_dir: Path) -> None:
    claim_path = lock_dir / "claim.json"
    try:
        claim_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clean up partial Slack operator rate-limit claim."
        ) from exc
    try:
        lock_dir.rmdir()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clean up partial Slack operator rate-limit claim."
        ) from exc


def _claim_rate_limit(config: BridgeConfig, event: OperatorEvent) -> None:
    if config.min_interval_seconds <= 0:
        return
    lock_dir = _rate_limit_claim_dir(config)
    _reject_symlinked_output_components(
        (lock_dir / "claim.json").absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
    )
    try:
        config.audit_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to prepare Slack operator rate-limit claim path."
        ) from exc
    for _ in range(RATE_LIMIT_CLAIM_MAX_ATTEMPTS):
        try:
            lock_dir.mkdir()
        except FileExistsError:
            _reject_symlinked_output_components(
                (lock_dir / "claim.json").absolute(),
                artifact_dir=Path(config.audit_dir).absolute(),
            )
            if not (lock_dir / "claim.json").exists():
                _remove_stale_rate_limit_claim(lock_dir)
                continue
            timestamp = _read_rate_limit_claim(lock_dir)
            age_seconds = (_utcnow() - timestamp).total_seconds()
            if 0 <= age_seconds < config.min_interval_seconds:
                raise SlackSocketAuditError("Slack operator bridge rate limit is active.")
            _remove_stale_rate_limit_claim(lock_dir)
            continue
        except OSError as exc:
            raise SlackSocketAuditError(
                "Unable to create Slack operator rate-limit claim."
            ) from exc
        claim = {
            "event_hash": _sha256_text(event.event_id),
            "provider_type": "slack_socket_mode",
            "status": "claimed",
            "timestamp": _utcnow().isoformat(),
        }
        try:
            (lock_dir / "claim.json").write_text(
                json.dumps(claim, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            _cleanup_partial_rate_limit_claim(lock_dir)
            raise SlackSocketAuditError(
                "Unable to record Slack operator rate-limit claim."
            ) from exc
        return
    raise SlackSocketAuditError("Unable to acquire Slack operator rate-limit claim.")


def _check_rate_limit(config: BridgeConfig) -> None:
    if not config.audit_dir.exists():
        return
    now = _utcnow()
    try:
        audit_paths = sorted(config.audit_dir.glob("*.json"))
    except OSError as exc:
        raise SlackSocketAuditError("Unable to inspect Slack operator audit artifacts.") from exc
    for audit_path in audit_paths:
        audit = _read_audit(audit_path)
        if audit is None or audit.get("status") not in {"dry_run", "dispatched"}:
            continue
        if config.min_interval_seconds <= 0:
            continue
        timestamp_raw = audit.get("timestamp")
        if not isinstance(timestamp_raw, str):
            raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
        try:
            timestamp = datetime.fromisoformat(timestamp_raw)
        except ValueError as exc:
            raise SlackSocketAuditError(
                "Existing Slack operator audit artifact is invalid."
            ) from exc
        if timestamp.tzinfo is None:
            raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
        age_seconds = (now - timestamp.astimezone(timezone.utc)).total_seconds()
        if 0 <= age_seconds < config.min_interval_seconds:
            raise SlackSocketAuditError("Slack operator bridge rate limit is active.")


def _require_execute_config(config: BridgeConfig) -> tuple[str, str]:
    if not config.repo or not config.github_token:
        raise SlackSocketConfigError("GitHub dispatch configuration is incomplete.")
    return config.repo, config.github_token


def _github_dispatch_inputs(command: OperatorCommand) -> dict[str, str]:
    if command.kind != "run-experiment" or command.branch_ref is None or command.hypothesis is None:
        raise SlackSocketDispatchError("Slack operator command is not dispatchable.")
    return {
        "branch_ref": command.branch_ref,
        "dry_run": "true",
        "hypothesis_sha256": _sha256_text(command.hypothesis),
    }


def _send_github_workflow_dispatch(
    *,
    repo: str,
    workflow_file: str,
    ref: str,
    inputs: dict[str, str],
    token: str,
    timeout_seconds: int,
) -> None:
    payload = json.dumps({"ref": ref, "inputs": inputs}).encode("utf-8")
    connection: http.client.HTTPSConnection | None = None
    try:
        connection = http.client.HTTPSConnection(GITHUB_API_HOST, timeout=timeout_seconds)
        connection.request(
            "POST",
            f"/repos/{repo}/actions/workflows/{workflow_file}/dispatches",
            body=payload,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "pulseplate-experiment-runner-slack-bridge",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response = connection.getresponse()
        response.read()
    except (OSError, http.client.HTTPException) as exc:
        raise SlackSocketDispatchError("GitHub workflow dispatch failed.") from exc
    finally:
        if connection is not None:
            connection.close()
    if response.status not in {200, 201, 202, 204}:
        raise SlackSocketDispatchError("GitHub workflow dispatch failed.")


def process_operator_event(
    event: OperatorEvent,
    config: BridgeConfig,
    *,
    dispatch_transport: WorkflowDispatchTransport | None = None,
) -> BridgeDecision:
    """Authorize, audit, and optionally dispatch one Slack operator event."""

    audit_path = _audit_path(config, event)
    try:
        _require_authorized_event(event, config)
        _ensure_event_not_processed(audit_path, config=config)
        command = parse_operator_command(event.text, command_hint=event.command_hint)
    except SlackSocketCommandError:
        command = OperatorCommand(kind="rejected")
        _write_audit_exclusive(
            path=audit_path,
            event=event,
            command=command,
            config=config,
            status="rejected",
            failure_class="command_rejected",
        )
        raise
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
                inputs=_github_dispatch_inputs(command),
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
        raise SlackSocketDispatchError("Slack operator dispatch failed.") from exc
    _write_audit(path=audit_path, event=event, command=command, config=config, status=status)
    return BridgeDecision(
        status=status,
        command_kind=command.kind,
        dispatch_mode=config.dispatch_mode,
        audit_path=audit_path,
        event_hash=_sha256_text(event.event_id),
        channel_hash=_sha256_text(event.channel_id),
        user_hash=_sha256_text(event.user_id),
        workflow_file=config.workflow_file,
        branch_hash=_safe_hash(command.branch_ref),
        hypothesis_hash=_safe_hash(command.hypothesis),
        failure_class=failure_class,
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
    if not config.allowed_channels or not config.allowed_users:
        raise SlackSocketConfigError("Slack Socket Mode allowlist configuration is incomplete.")
    _load_slack_bolt()


def _load_slack_bolt() -> tuple[Any, Any]:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ModuleNotFoundError as exc:
        raise SlackSocketConfigError(
            "Slack Socket Mode SDK is unavailable. Install the optional operator Slack SDK runtime."
        ) from exc
    return App, SocketModeHandler


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
            respond(_format_operator_reply(decision))
        except SlackSocketBridgeError as exc:
            respond(f"Experiment Runner bridge rejected the request: {exc}")

    app.command("/run-experiment")(_handle_command)
    handler = SocketModeHandler(app, config.slack_app_token)
    handler.start()
    return 0


def _format_operator_reply(decision: BridgeDecision) -> str:
    return (
        "Experiment Runner bridge "
        f"{decision.status}; command={decision.command_kind}; "
        f"dispatch_mode={decision.dispatch_mode}; event={decision.event_hash[:12]}"
    )


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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        config = build_config(
            dispatch_mode=args.dispatch_mode,
            audit_dir=args.audit_dir,
            repo=args.repo,
            workflow_ref=args.workflow_ref,
        )
        if args.validate_runtime:
            if config.dispatch_mode == "execute":
                _require_execute_config(config)
            if args.run_socket:
                _require_live_socket_runtime(config)
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
    print(json.dumps(decision.public_payload(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
