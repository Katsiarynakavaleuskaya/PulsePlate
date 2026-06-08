"""Parsing, normalization, and authorization helpers for the Slack bridge."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from scripts.orchestration.experiment_slack_bridge_config import (
    _is_safe_ref,
    _normalize_slack_id,
)
from scripts.orchestration.experiment_slack_bridge_constants import (
    ALLOWED_COMMANDS,
    CONTROL_CHAR_RE,
    ENV_ASSIGNMENT_RE,
    SECRET_SHAPED_RE,
    SHELL_META_RE,
)
from scripts.orchestration.experiment_slack_bridge_models import (
    BridgeConfig,
    OperatorCommand,
    OperatorEvent,
    SlackSocketCommandError,
    SlackSocketConfigError,
    _sha256_text,
)
from scripts.orchestration.experiment_slack_redaction import LOCAL_PATH_RE

DISPLAY_ONLY_COMMANDS = {"help", "kpp-status", "mvp-evidence", "status"}
DISPATCH_COMMAND = "run-experiment"
SLASH_COMMAND_SCOPES = {
    "/pulseplate-runner": DISPLAY_ONLY_COMMANDS,
    "/run-experiment": {DISPATCH_COMMAND},
}


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketCommandError("Slack operator event payload is invalid.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketCommandError("Slack operator event payload is invalid.")
    return payload


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
    scoped_commands = SLASH_COMMAND_SCOPES.get(command_hint or "")
    if scoped_commands is not None and verb not in scoped_commands:
        raise SlackSocketCommandError("Slack operator command is invalid.")
    if verb in DISPLAY_ONLY_COMMANDS:
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
    try:
        _normalize_slack_id(event_id, label="event")
        _normalize_slack_id(channel, label="channel")
        _normalize_slack_id(user, label="user")
        if team is not None:
            _normalize_slack_id(team, label="team")
    except SlackSocketConfigError as exc:
        raise SlackSocketCommandError("Slack operator event payload is invalid.") from exc
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
