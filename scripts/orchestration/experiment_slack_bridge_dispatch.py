"""GitHub dispatch and live-approval helpers for the Slack bridge."""

from __future__ import annotations

import http.client
import json
import os

from scripts.orchestration.experiment_slack_bridge_config import (
    _compute_live_approval_digest,
)
from scripts.orchestration.experiment_slack_bridge_constants import (
    BRIDGE_EXECUTE_ENABLED_ENV,
    BRIDGE_EXECUTE_ENABLED_VALUE,
    GITHUB_API_HOST,
)
from scripts.orchestration.experiment_slack_bridge_models import (
    BridgeConfig,
    OperatorCommand,
    SlackSocketConfigError,
    SlackSocketDispatchError,
    _sha256_text,
)


def _require_execute_config(config: BridgeConfig) -> tuple[str, str]:
    if os.environ.get(BRIDGE_EXECUTE_ENABLED_ENV, "").strip() != BRIDGE_EXECUTE_ENABLED_VALUE:
        raise SlackSocketConfigError("Slack execute-mode promotion gate is not enabled.")
    if not config.allowed_teams:
        raise SlackSocketConfigError("Slack Socket Mode allowlist configuration is incomplete.")
    if not config.repo or not config.github_token:
        raise SlackSocketConfigError("GitHub dispatch configuration is incomplete.")
    return config.repo, config.github_token


def _github_dispatch_inputs(command: OperatorCommand, *, config: BridgeConfig) -> dict[str, str]:
    if command.kind != "run-experiment" or command.branch_ref is None or command.hypothesis is None:
        raise SlackSocketDispatchError("Slack operator command is not dispatchable.")
    if config.live_approval_sha256 is not None:
        digest = _compute_live_approval_digest(command.branch_ref, command.hypothesis)
        if digest != config.live_approval_sha256:
            raise SlackSocketDispatchError(
                "Slack live-dispatch approval mismatch. "
                "The requested branch and hypothesis do not match the reviewed approval digest."
            )
        return {
            "branch_ref": command.branch_ref,
            "dry_run": "false",
            "hypothesis_sha256": _sha256_text(command.hypothesis),
            "approval_ref": config.live_approval_sha256,
        }
    return {
        "branch_ref": command.branch_ref,
        "dry_run": "true",
        "hypothesis_sha256": _sha256_text(command.hypothesis),
        "approval_ref": "none",
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
