"""Tests for the Experiment Runner Slack Socket Mode operator bridge."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import scripts.orchestration.context_pack as context_pack
from scripts.orchestration import experiment_slack_socket_bridge as bridge

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "experiment-runner-slack-socket-smoke.yml"


def _workflow_on(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow.get("on") or workflow[True]


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _configure_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    audit_dir = repo / "artifacts" / "orchestration" / "experiments" / "slack_socket_bridge"
    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(bridge, "REPO_ROOT", repo)
    monkeypatch.setattr(bridge, "AUDIT_ARTIFACT_DIR", audit_dir)
    return audit_dir


def _configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_TIMEOUT_SECONDS", "5")


def _event(
    *,
    event_id: str = "Ev0SLACK01",
    channel: str = "C0ALERTS",
    user: str = "U0OPERATOR",
    command: str = "/run-experiment",
    text: str = "feature/test Improve oracle evidence throughput",
) -> dict[str, object]:
    return {
        "channel_id": channel,
        "command": command,
        "envelope_id": event_id,
        "team_id": "T0TEAM",
        "text": text,
        "user_id": user,
    }


def _config(
    *,
    dispatch_mode: str = "dry-run",
    audit_dir: Path,
    repo: str | None = "Katsiarynakavaleuskaya/PulsePlate",
) -> bridge.BridgeConfig:
    return bridge.build_config(
        dispatch_mode=dispatch_mode,
        audit_dir=str(audit_dir),
        repo=repo,
    )


def test_import_and_dry_run_validation_do_not_require_slack_sdk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "dry-run"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {"dispatch_mode": "dry-run", "status": "pass"}


def test_live_socket_validation_fails_closed_without_runtime_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.delenv("SLACK_APP_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

    assert bridge.main(["--validate-runtime", "--run-socket"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack Socket Mode configuration is incomplete" in stdout
    assert "SLACK_APP_TOKEN" not in stdout
    assert "SLACK_BOT_TOKEN" not in stdout
    assert "xapp-" not in stdout
    assert "xox" not in stdout


def test_live_socket_validation_reports_missing_sdk_without_import_time_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)

    def missing_sdk() -> tuple[Any, Any]:
        raise bridge.SlackSocketConfigError(
            "Slack Socket Mode SDK is unavailable. Install the optional operator Slack SDK runtime."
        )

    monkeypatch.setattr(bridge, "_load_slack_bolt", missing_sdk)

    assert bridge.main(["--validate-runtime", "--run-socket"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack Socket Mode SDK is unavailable" in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout


def test_dry_run_processes_allowlisted_operator_without_dispatch_or_raw_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    calls: list[dict[str, Any]] = []

    decision = bridge.process_payload(
        _event(),
        config,
        dispatch_transport=lambda **kwargs: calls.append(kwargs),
    )

    assert calls == []
    assert decision.status == "dry_run"
    assert decision.command_kind == "run-experiment"
    audit_text = decision.audit_path.read_text(encoding="utf-8")
    audit = json.loads(audit_text)
    assert audit["status"] == "dry_run"
    assert audit["provider_type"] == "slack_socket_mode"
    assert audit["branch_hash"] == bridge._sha256_text("feature/test")
    assert audit["hypothesis_hash"] == bridge._sha256_text("Improve oracle evidence throughput")
    assert "C0ALERTS" not in audit_text
    assert "U0OPERATOR" not in audit_text
    assert "Improve oracle" not in audit_text
    assert "feature/test" not in audit_text


def test_execute_mode_dispatches_only_fixed_workflow_with_typed_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "c" * 24)
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    calls: list[dict[str, Any]] = []

    decision = bridge.process_payload(
        _event(text="release/smoke Validate bounded Slack operator bridge"),
        config,
        dispatch_transport=lambda **kwargs: calls.append(kwargs),
    )

    assert decision.status == "dispatched"
    assert len(calls) == 1
    assert calls[0]["repo"] == "Katsiarynakavaleuskaya/PulsePlate"
    assert calls[0]["workflow_file"] == "experiment-runner-slack-socket-smoke.yml"
    assert calls[0]["ref"] == "main"
    assert calls[0]["inputs"] == {
        "branch_ref": "release/smoke",
        "hypothesis_sha256": bridge._sha256_text("Validate bounded Slack operator bridge"),
        "operator_command": "run-experiment",
        "source": "slack_socket_bridge",
    }


def test_execute_mode_requires_github_auth_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketDispatchError, match="dispatch failed"):
        bridge.process_payload(
            _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
        )

    assert calls == []
    audit = json.loads((audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").read_text())
    assert audit["status"] == "failed"
    assert audit["failure_class"] == "dispatch_failed"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "unknown feature/test Improve oracle evidence throughput",
        "run-experiment ../main Improve oracle evidence throughput",
        "run-experiment feature/test A=1 should not parse",
        "run-experiment feature/test cat /Users/alice/.ssh/id_rsa",
        "run-experiment feature/test Improve; rm -rf repo",
        "run-experiment feature/test xapp-" + "a" * 24,
        "run-experiment feature/test short",
    ],
)
def test_parser_rejects_unsafe_operator_text(text: str) -> None:
    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.parse_operator_command(text)


def test_channel_and_user_allowlists_fail_closed_without_leaking_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(channel="C0SECRET", user="U0DENIED")), encoding="utf-8")

    assert bridge.main(["--event-json", str(event_path), "--audit-dir", str(audit_dir)]) == 1
    stdout = capsys.readouterr().out

    assert "channel is not allowed" in stdout
    assert "C0SECRET" not in stdout
    assert "U0DENIED" not in stdout


def test_duplicate_event_is_blocked_before_second_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "d" * 24)
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    calls: list[dict[str, Any]] = []

    bridge.process_payload(
        _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
    )
    with pytest.raises(bridge.SlackSocketAuditError, match="already processed"):
        bridge.process_payload(
            _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
        )

    assert len(calls) == 1


def test_recent_audit_rate_limit_blocks_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "3600")
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    audit_dir.mkdir(parents=True)
    (audit_dir / "previous.json").write_text(
        json.dumps(
            {
                "event_hash": "a" * 64,
                "status": "dry_run",
                "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketAuditError, match="rate limit"):
        bridge.process_payload(
            _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
        )

    assert calls == []


def test_malformed_existing_audit_blocks_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    audit_dir.mkdir(parents=True)
    (audit_dir / "bad.json").write_text("not-json", encoding="utf-8")
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketAuditError, match="invalid"):
        bridge.process_payload(
            _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
        )

    assert calls == []


def test_workflow_is_manual_only_and_secret_safe() -> None:
    workflow = _load_workflow()
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    triggers = _workflow_on(workflow)

    assert set(triggers) == {"workflow_dispatch"}
    assert "pull_request" not in triggers
    assert "pull_request_target" not in workflow_text
    assert "push" not in triggers
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["slack-socket-bridge-smoke"]
    assert job["timeout-minutes"] == 10
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"dry_run", "branch_ref", "hypothesis_sha256"}
    assert inputs["dry_run"]["default"] == "true"
    assert "${{ secrets.SLACK_APP_TOKEN }}" in workflow_text
    assert "${{ secrets.SLACK_BOT_TOKEN }}" in workflow_text
    assert "SLACK_SIGNING_SECRET" not in workflow_text
    assert "continue-on-error" not in workflow_text
    assert "|| true" not in workflow_text
    assert "pull-requests:" not in workflow_text
    assert "issues:" not in workflow_text
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text
