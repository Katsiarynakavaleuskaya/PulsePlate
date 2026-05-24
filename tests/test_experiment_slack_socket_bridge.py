"""Tests for the Experiment Runner Slack Socket Mode operator bridge."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
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
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "60")
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


def _config_without_rate_limit(
    *,
    monkeypatch: pytest.MonkeyPatch,
    audit_dir: Path,
    dispatch_mode: str = "dry-run",
    repo: str | None = "Katsiarynakavaleuskaya/PulsePlate",
) -> bridge.BridgeConfig:
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "1")
    config = _config(dispatch_mode=dispatch_mode, audit_dir=audit_dir, repo=repo)
    return bridge.BridgeConfig(
        dispatch_mode=config.dispatch_mode,
        allowed_channels=config.allowed_channels,
        allowed_users=config.allowed_users,
        allowed_teams=config.allowed_teams,
        audit_dir=config.audit_dir,
        repo=config.repo,
        workflow_file=config.workflow_file,
        workflow_ref=config.workflow_ref,
        timeout_seconds=config.timeout_seconds,
        min_interval_seconds=0,
        slack_app_token=config.slack_app_token,
        slack_bot_token=config.slack_bot_token,
        github_token=config.github_token,
    )


def test_import_and_dry_run_validation_do_not_require_slack_sdk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)

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


def test_execute_runtime_validation_requires_github_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "execute"]) == 1
    stdout = capsys.readouterr().out

    assert "GitHub dispatch configuration is incomplete" in stdout
    assert "GH_TOKEN" not in stdout
    assert "GITHUB_TOKEN" not in stdout


def test_live_socket_validation_requires_channel_and_user_allowlists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", raising=False)
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", raising=False)

    assert bridge.main(["--validate-runtime", "--run-socket"]) == 1
    stdout = capsys.readouterr().out

    assert "allowlist configuration is incomplete" in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout


def test_config_rejects_zero_rate_limit_without_test_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "0")

    with pytest.raises(bridge.SlackSocketConfigError):
        _config(audit_dir=audit_dir)


def test_config_rejects_non_main_workflow_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)

    with pytest.raises(bridge.SlackSocketConfigError):
        bridge.build_config(
            dispatch_mode="dry-run",
            audit_dir=str(audit_dir),
            repo="Katsiarynakavaleuskaya/PulsePlate",
            workflow_ref="feature/unreviewed",
        )


def test_config_rejects_parent_traversal_audit_dir_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    escaped = audit_dir / ".." / ".." / ".." / "outside"

    with pytest.raises(bridge.SlackSocketAuditError, match="artifacts/orchestration"):
        bridge.build_config(
            dispatch_mode="dry-run",
            audit_dir=str(escaped),
            repo="Katsiarynakavaleuskaya/PulsePlate",
        )


def test_dry_run_processes_allowlisted_operator_without_dispatch_or_raw_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
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


def test_socket_mode_envelope_uses_outer_envelope_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    payload = {
        "accepts_response_payload": True,
        "envelope_id": "Ev0OUTER1",
        "payload": {
            "channel_id": "C0ALERTS",
            "command": "/run-experiment",
            "team_id": "T0TEAM",
            "text": "feature/socket Validate Slack envelope parsing",
            "trigger_id": "123.456.abcdef",
            "user_id": "U0OPERATOR",
        },
        "type": "slash_commands",
    }

    decision = bridge.process_payload(payload, config)

    assert decision.status == "dry_run"
    assert decision.event_hash == bridge._sha256_text("Ev0OUTER1")


def test_bolt_command_body_uses_trigger_id_as_fallback_event_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    payload = {
        "channel_id": "C0ALERTS",
        "command": "/run-experiment",
        "team_id": "T0TEAM",
        "text": "feature/bolt Validate Bolt command body parsing",
        "trigger_id": "37053613634.26768298162.440952c06ef4de2653466a48fe495f93",
        "user_id": "U0OPERATOR",
    }
    fallback_event_id = f"trigger-{bridge._sha256_text(str(payload['trigger_id']))[:32]}"

    decision = bridge.process_payload(payload, config)

    assert decision.status == "dry_run"
    assert decision.event_hash == bridge._sha256_text(fallback_event_id)


def test_execute_mode_dispatches_only_fixed_workflow_with_typed_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "c" * 24)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
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
        "dry_run": "true",
        "hypothesis_sha256": bridge._sha256_text("Validate bounded Slack operator bridge"),
    }


def test_dispatch_inputs_match_manual_workflow_contract() -> None:
    workflow = _load_workflow()
    triggers = _workflow_on(workflow)
    workflow_inputs = set(triggers["workflow_dispatch"]["inputs"])
    command = bridge.OperatorCommand(
        kind="run-experiment",
        branch_ref="release/smoke",
        hypothesis="Validate bounded Slack operator bridge",
    )

    assert set(bridge._github_dispatch_inputs(command)) <= workflow_inputs


def test_execute_mode_requires_github_auth_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
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
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
    calls: list[dict[str, Any]] = []

    bridge.process_payload(
        _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
    )
    with pytest.raises(bridge.SlackSocketAuditError, match="already processed"):
        bridge.process_payload(
            _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
        )

    assert len(calls) == 1


def test_rejected_duplicate_event_cannot_overwrite_successful_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    decision = bridge.process_payload(_event(), config)
    original_audit = decision.audit_path.read_text(encoding="utf-8")

    with pytest.raises(bridge.SlackSocketAuditError, match="already processed"):
        bridge.process_payload(_event(text="run-experiment feature/test bad; rm -rf repo"), config)

    assert decision.audit_path.read_text(encoding="utf-8") == original_audit


def test_duplicate_rejected_event_is_blocked_without_overwriting_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    rejected = _event(text="run-experiment feature/test bad; rm -rf repo")

    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.process_payload(rejected, config)
    audit_path = audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json"
    original_audit = audit_path.read_text(encoding="utf-8")

    with pytest.raises(bridge.SlackSocketAuditError, match="already processed"):
        bridge.process_payload(rejected, config)

    assert audit_path.read_text(encoding="utf-8") == original_audit


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


def test_atomic_rate_limit_claim_blocks_concurrent_unique_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "e" * 24)
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    calls: list[dict[str, Any]] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def slow_dispatch(**kwargs: Any) -> None:
        calls.append(kwargs)
        barrier.wait(timeout=5)

    def worker(event_id: str) -> None:
        try:
            bridge.process_payload(
                _event(
                    event_id=event_id,
                    text=f"feature/{event_id.lower()} Validate atomic rate limit claim",
                ),
                config,
                dispatch_transport=slow_dispatch,
            )
        except BaseException as exc:  # noqa: BLE001 - tests collect thread exceptions.
            errors.append(exc)
            try:
                barrier.abort()
            except threading.BrokenBarrierError:
                pass

    thread_one = threading.Thread(target=worker, args=("Ev0RATE01",))
    thread_two = threading.Thread(target=worker, args=("Ev0RATE02",))
    thread_one.start()
    thread_two.start()
    thread_one.join(timeout=5)
    thread_two.join(timeout=5)

    assert not thread_one.is_alive()
    assert not thread_two.is_alive()
    assert len(calls) == 1
    assert any(isinstance(error, bridge.SlackSocketAuditError) for error in errors)


def test_rate_limit_claim_rejects_symlinked_artifact_ancestor_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    outside = tmp_path / "outside"
    experiments = repo / "artifacts" / "orchestration" / "experiments"
    experiments.parent.mkdir(parents=True)
    outside.mkdir()
    experiments.symlink_to(outside, target_is_directory=True)
    config = _config(audit_dir=experiments / "slack_socket_bridge")

    with pytest.raises(bridge.SlackSocketAuditError, match="symlink"):
        bridge.process_payload(_event(event_id="Ev0SYMLINKRATE"), config)

    assert not (outside / "slack_socket_bridge" / bridge.RATE_LIMIT_LOCK_DIR).exists()


def test_rate_limit_claim_retry_loop_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "1")
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    lock_dir = audit_dir / bridge.RATE_LIMIT_LOCK_DIR
    lock_dir.mkdir(parents=True)
    (lock_dir / "claim.json").write_text(
        json.dumps(
            {
                "event_hash": "b" * 64,
                "provider_type": "slack_socket_mode",
                "status": "claimed",
                "timestamp": datetime.fromtimestamp(0, tz=timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    attempts = 0

    def no_op_stale_cleanup(_lock_dir: Path) -> None:
        nonlocal attempts
        attempts += 1

    monkeypatch.setattr(bridge, "_remove_stale_rate_limit_claim", no_op_stale_cleanup)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to acquire"):
        bridge.process_payload(_event(event_id="Ev0BOUNDED"), config)

    assert attempts == bridge.RATE_LIMIT_CLAIM_MAX_ATTEMPTS


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
    assert set(inputs) == {
        "branch_ref",
        "channel_allowlist",
        "dry_run",
        "hypothesis_sha256",
        "user_allowlist",
    }
    assert inputs["dry_run"]["default"] == "true"
    assert "${{ secrets.SLACK_APP_TOKEN }}" in workflow_text
    assert "${{ secrets.SLACK_BOT_TOKEN }}" in workflow_text
    assert "slack-bolt==1.28.0" in workflow_text
    assert "SLACK_SIGNING_SECRET" not in workflow_text
    assert "continue-on-error" not in workflow_text
    assert "|| true" not in workflow_text
    assert "pull-requests:" not in workflow_text
    assert "issues:" not in workflow_text
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text


def test_audit_dir_rejects_symlinked_artifact_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    experiments = repo / "artifacts" / "orchestration" / "experiments"
    experiments.parent.mkdir(parents=True)
    outside.mkdir()
    experiments.symlink_to(outside, target_is_directory=True)

    with pytest.raises(bridge.SlackSocketAuditError, match="symlink"):
        bridge._write_audit_exclusive(
            path=experiments / "slack_socket_bridge" / "audit.json",
            event=bridge.OperatorEvent(
                event_id="Ev0SYMLINK",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=_config_without_rate_limit(
                monkeypatch=monkeypatch,
                audit_dir=experiments / "slack_socket_bridge",
            ),
            status="dry_run",
        )


def test_audit_write_rejects_symlinked_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    audit_dir.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    output = audit_dir / "audit.json"
    output.symlink_to(outside)

    with pytest.raises(bridge.SlackSocketAuditError, match="symlink"):
        bridge._write_audit(
            path=output,
            event=bridge.OperatorEvent(
                event_id="Ev0SYMLINK",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=_config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir),
            status="dry_run",
        )


def test_audit_write_rejects_parent_traversal_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    escaped = audit_dir / ".." / "outside.json"

    with pytest.raises(bridge.SlackSocketAuditError, match="artifacts/orchestration"):
        bridge._write_audit(
            path=escaped,
            event=bridge.OperatorEvent(
                event_id="Ev0TRAVERSAL",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=config,
            status="dry_run",
        )

    assert not (audit_dir.parent / "outside.json").exists()
