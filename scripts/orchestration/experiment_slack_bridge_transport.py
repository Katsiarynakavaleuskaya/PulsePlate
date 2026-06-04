"""Optional Slack API and Socket Mode transport helpers for the bridge."""

from __future__ import annotations

import http.client
import json
from typing import Any, cast

from scripts.orchestration.experiment_slack_bridge_config import _is_safe_ref
from scripts.orchestration.experiment_slack_bridge_constants import (
    LIVE_SMOKE_BRANCH_REF_ENV,
    LIVE_SMOKE_HYPOTHESIS_SHA256_ENV,
    SAFE_SLACK_ERROR_CODE_RE,
    SHA256_HEX_RE,
    SLACK_API_HOST,
    SLACK_LIVE_SMOKE_METHODS,
)
from scripts.orchestration.experiment_slack_bridge_models import (
    BridgeConfig,
    SlackApiTransport,
    SlackSocketConfigError,
)
import os


def validate_live_smoke_inputs(
    *,
    branch_ref: str | None = None,
    hypothesis_sha256: str | None = None,
) -> dict[str, str]:
    """Validate manual workflow smoke inputs without printing raw values."""

    raw_branch_ref = (
        branch_ref if branch_ref is not None else os.environ.get(LIVE_SMOKE_BRANCH_REF_ENV, "")
    ).strip()
    raw_hypothesis_sha256 = (
        hypothesis_sha256
        if hypothesis_sha256 is not None
        else os.environ.get(LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "")
    )
    if not _is_safe_ref(raw_branch_ref):
        raise SlackSocketConfigError("Slack live smoke input configuration is invalid.")
    if raw_hypothesis_sha256 != raw_hypothesis_sha256.strip():
        raise SlackSocketConfigError("Slack live smoke input configuration is invalid.")
    if SHA256_HEX_RE.fullmatch(raw_hypothesis_sha256) is None:
        raise SlackSocketConfigError("Slack live smoke input configuration is invalid.")
    return {
        "branch_ref_status": "valid",
        "hypothesis_sha256_status": "valid",
    }


def _send_slack_api_request(
    *,
    method: str,
    token: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Call a fixed Slack Web API method for bounded smoke validation."""

    if method not in SLACK_LIVE_SMOKE_METHODS:
        raise SlackSocketConfigError("Slack live smoke method is invalid.")
    connection: http.client.HTTPSConnection | None = None
    try:
        connection = http.client.HTTPSConnection(SLACK_API_HOST, timeout=timeout_seconds)
        connection.request(
            "POST",
            f"/api/{method}",
            body=b"{}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "pulseplate-experiment-runner-slack-bridge",
            },
        )
        response = connection.getresponse()
        response_body = response.read()
    except (OSError, http.client.HTTPException) as exc:
        raise SlackSocketConfigError("Slack live smoke validation failed.") from exc
    finally:
        if connection is not None:
            connection.close()
    if response.status not in {200, 201, 202}:
        raise SlackSocketConfigError("Slack live smoke validation failed.")
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketConfigError("Slack live smoke validation failed.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketConfigError("Slack live smoke validation failed.")
    return payload


def _safe_slack_error_code(payload: dict[str, Any]) -> str:
    raw_error = payload.get("error")
    if not isinstance(raw_error, str):
        return "unknown"
    error = raw_error.strip()
    if SAFE_SLACK_ERROR_CODE_RE.fullmatch(error) is None:
        return "unknown"
    return error


def _require_slack_ok_response(payload: dict[str, Any], *, check_name: str) -> None:
    if payload.get("ok") is not True:
        error_code = _safe_slack_error_code(payload)
        raise SlackSocketConfigError(
            f"Slack live smoke {check_name} validation failed: {error_code}."
        )


def _require_socket_mode_url(payload: dict[str, Any]) -> None:
    socket_url = payload.get("url")
    if not isinstance(socket_url, str) or not socket_url.startswith("wss://"):
        raise SlackSocketConfigError("Slack live smoke Socket Mode validation failed.")


def _require_live_smoke_runtime(config: BridgeConfig) -> None:
    if config.slack_app_token is None or config.slack_bot_token is None:
        raise SlackSocketConfigError("Slack Socket Mode configuration is incomplete.")
    if not config.allowed_channels or not config.allowed_users or not config.allowed_teams:
        raise SlackSocketConfigError("Slack Socket Mode allowlist configuration is incomplete.")


def validate_live_smoke(
    config: BridgeConfig,
    *,
    branch_ref: str | None = None,
    hypothesis_sha256: str | None = None,
    slack_api_transport: SlackApiTransport | None = None,
) -> dict[str, Any]:
    """Run bounded live-smoke checks and return a redacted status payload."""

    _require_live_smoke_runtime(config)
    input_status = validate_live_smoke_inputs(
        branch_ref=branch_ref,
        hypothesis_sha256=hypothesis_sha256,
    )
    transport = slack_api_transport or _send_slack_api_request
    slack_app_token = cast(str, config.slack_app_token)
    slack_bot_token = cast(str, config.slack_bot_token)
    socket_payload = transport(
        method="apps.connections.open",
        token=slack_app_token,
        timeout_seconds=config.timeout_seconds,
    )
    _require_slack_ok_response(socket_payload, check_name="Socket Mode")
    _require_socket_mode_url(socket_payload)
    bot_payload = transport(
        method="auth.test",
        token=slack_bot_token,
        timeout_seconds=config.timeout_seconds,
    )
    _require_slack_ok_response(bot_payload, check_name="bot auth")
    return {
        **input_status,
        "allowlist_status": "present",
        "bot_auth_status": "validated",
        "dispatch_mode": config.dispatch_mode,
        "socket_mode_status": "validated",
        "status": "pass",
    }


def _load_slack_bolt() -> tuple[Any, Any]:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ModuleNotFoundError as exc:
        raise SlackSocketConfigError(
            "Slack Socket Mode SDK is unavailable. Install the optional operator Slack SDK runtime."
        ) from exc
    return App, SocketModeHandler
