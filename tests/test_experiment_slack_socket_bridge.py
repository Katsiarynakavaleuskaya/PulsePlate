"""Tests for the Experiment Runner Slack Socket Mode operator bridge."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
from typing import Any, cast

import pytest
import yaml

import scripts.orchestration.context_pack as context_pack
from scripts.orchestration import experiment_operator_ledger
from scripts.orchestration import experiment_private_pilot_activation
from scripts.orchestration import experiment_slack_socket_bridge as bridge
from scripts.orchestration.experiment_slack_socket_bridge import LIVE_APPROVAL_SHA256_ENV
from scripts.orchestration.experiment_slack_redaction import SLACK_IDENTIFIER_RE

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "experiment-runner-slack-socket-smoke.yml"
)
DISPATCH_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "experiment-runner-dispatch.yml"
SLACK_MANIFEST_PATH = (
    REPO_ROOT / "docs" / "orchestration" / "EXPERIMENT_RUNNER_SLACK_APP_MANIFEST.yml"
)


def _workflow_on(workflow: dict[Any, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], workflow.get("on") or workflow[True])


def _load_workflow(path: Path = SMOKE_WORKFLOW_PATH) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def _configure_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    audit_dir = repo / "artifacts" / "orchestration" / "experiments" / "slack_socket_bridge"
    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(bridge, "REPO_ROOT", repo)
    monkeypatch.setattr(bridge, "AUDIT_ARTIFACT_DIR", audit_dir)
    for env_name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GITHUB_REPOSITORY",
        bridge.BRIDGE_EXECUTE_ENABLED_ENV,
        bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV,
        bridge.LIVE_APPROVAL_SHA256_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)
    return audit_dir


def _configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("EXPERIMENT_OPERATOR_LEDGER_TASK_PACKET_ID", "packet-pr2")
    monkeypatch.setenv("GITHUB_REPOSITORY", "Katsiarynakavaleuskaya/PulsePlate")


def _clear_readiness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in (
        bridge.SLACK_APP_AUTH_ENV,
        bridge.SLACK_BOT_AUTH_ENV,
        bridge.SLACK_CHANNEL_ALLOWLIST_ENV,
        bridge.SLACK_USER_ALLOWLIST_ENV,
        bridge.SLACK_TEAM_ALLOWLIST_ENV,
        bridge.BRIDGE_AUDIT_RETENTION_DAYS_ENV,
        bridge.LIVE_SMOKE_BRANCH_REF_ENV,
        bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)


def _event(
    *,
    event_id: str = "Ev0SLACK01",
    channel: str = "C0ALERTS",
    user: str = "U0OPERATOR",
    team_id: str = "T0TEAM",
    command: str = "/run-experiment",
    text: str = "feature/test Improve oracle evidence throughput",
) -> dict[str, object]:
    return {
        "channel_id": channel,
        "command": command,
        "envelope_id": event_id,
        "team_id": team_id,
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
        audit_retention_days=config.audit_retention_days,
        slack_app_token=config.slack_app_token,
        slack_bot_token=config.slack_bot_token,
        github_token=config.github_token,
        live_approval_sha256=config.live_approval_sha256,
        operator_ledger_task_packet_id=config.operator_ledger_task_packet_id,
        github_dispatch=config.github_dispatch,
    )


def _repo_root_from_audit_dir(audit_dir: Path) -> Path:
    return audit_dir.parents[3]


def _ledger_records(audit_dir: Path) -> list[experiment_operator_ledger.OperatorLedgerRecord]:
    return experiment_operator_ledger.load_operator_ledger_events(
        repo_root=_repo_root_from_audit_dir(audit_dir)
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


def test_validate_runtime_preflights_operator_ledger_writeability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    repo_root = _repo_root_from_audit_dir(audit_dir)
    event_dir = experiment_operator_ledger.default_ledger_dir(repo_root) / "events"
    event_dir.parent.mkdir(parents=True)
    event_dir.write_text("not a directory", encoding="utf-8")

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "dry-run"]) == 1

    stdout = capsys.readouterr().out
    assert "Experiment operator ledger evidence is unavailable" in stdout
    assert "not a directory" not in stdout
    assert str(event_dir) not in stdout


def test_validate_runtime_rejects_malformed_existing_operator_ledger_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    repo_root = _repo_root_from_audit_dir(audit_dir)
    event_dir = experiment_operator_ledger.default_ledger_dir(repo_root) / "events"
    event_dir.mkdir(parents=True)
    (event_dir / "bad.json").write_text("not-json", encoding="utf-8")

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "dry-run"]) == 1

    stdout = capsys.readouterr().out
    assert "Experiment operator ledger evidence is unavailable" in stdout
    assert "not-json" not in stdout
    assert str(event_dir) not in stdout


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


def test_secret_presence_validation_reports_missing_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)

    assert bridge.main(["--validate-secret-presence"]) == 1
    stdout = capsys.readouterr().out

    assert stdout == ""
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout


def test_secret_presence_validation_passes_without_leaking_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")

    assert bridge.main(["--validate-secret-presence"]) == 0
    stdout = capsys.readouterr().out

    assert stdout == ""
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert "T0TEAM" not in stdout


def test_secret_presence_validation_requires_team_allowlist_without_leaking_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", raising=False)

    assert bridge.main(["--validate-secret-presence"]) == 1
    stdout = capsys.readouterr().out

    assert stdout == ""
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout


def test_secret_presence_validation_rejects_malformed_runtime_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("SLACK_APP_TOKEN", "present-but-not-an-app-token")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")

    assert bridge.main(["--validate-secret-presence"]) == 1
    stdout = capsys.readouterr().out

    assert stdout == ""
    assert "SLACK_APP_TOKEN token class is invalid" not in stdout
    assert "present-but-not-an-app-token" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout


def test_secret_presence_validation_rejects_malformed_allowlist_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "/tmp/channel")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")

    assert bridge.main(["--validate-secret-presence"]) == 1
    stdout = capsys.readouterr().out

    assert stdout == ""
    assert "channel allowlist is invalid" not in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "/tmp/channel" not in stdout
    assert "U0OPERATOR" not in stdout


def test_activation_readiness_report_manual_only_without_runtime_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _clear_readiness_env(monkeypatch)

    assert bridge.main(["--activation-readiness-report"]) == 0
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["activation_state"] == "manual_only"
    assert report["slack_app_token_status"] == "missing"
    assert report["slack_bot_token_status"] == "missing"
    assert report["channel_allowlist_status"] == "missing"
    assert report["user_allowlist_status"] == "missing"
    assert report["team_allowlist_status"] == "missing"
    assert report["branch_ref_status"] == "not_checked"
    assert report["hypothesis_sha256_status"] == "not_checked"
    assert report["audit_retention_status"] == "valid"
    assert report["manual_live_smoke"] == "operator_evidence_only"
    assert report["dispatch_surface"] == "socket_mode_only"
    assert report["authority_boundary"] == {
        "backend_contract_changed": False,
        "claimed_merge_readiness": False,
        "created_pr": False,
        "deterministic_ci_requires_live_slack": False,
        "opened_http_ingress": False,
        "product_runtime_changed": False,
        "resolved_review_threads": False,
        "semantic_cache_enabled": False,
        "workflow_authority_changed": False,
    }
    assert report["evidence_graph_admission_status"] == "contract_only_not_runtime"
    assert report["github_dispatch_readiness_state"] == "manual_only"
    assert report["github_dispatch_auth_status"] == "missing"
    assert report["github_dispatch_auth_class"] == "none"
    assert report["github_dispatch_target_status"] == "not_configured"
    assert report["github_dispatch_repo_allowlist_status"] == "not_required"
    assert report["github_dispatch_workflow_status"] == "fixed"
    assert report["github_dispatch_execute_gate_status"] == "not_required"
    assert report["github_dispatch_live_approval_status"] == "dry_run_default"
    assert report["github_dispatch_authority"] == "display_only"
    assert "SLACK_APP_TOKEN" not in stdout
    assert "SLACK_BOT_TOKEN" not in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_ready_for_manual_live_smoke_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.BRIDGE_AUDIT_RETENTION_DAYS_ENV, "14")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "main")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "a" * 64)

    assert bridge.main(["--activation-readiness-report"]) == 0
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["activation_state"] == "ready_for_manual_live_smoke"
    assert report["slack_app_token_status"] == "valid"
    assert report["slack_bot_token_status"] == "valid"
    assert report["channel_allowlist_status"] == "present"
    assert report["user_allowlist_status"] == "present"
    assert report["team_allowlist_status"] == "present"
    assert report["branch_ref_status"] == "valid"
    assert report["hypothesis_sha256_status"] == "valid"
    assert report["github_dispatch_readiness_state"] == "manual_only"
    assert report["github_dispatch_authority"] == "display_only"
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert "T0TEAM" not in stdout
    assert "main" not in stdout
    assert "a" * 64 not in stdout


def test_activation_readiness_report_projects_cross_repo_private_pilot_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _clear_readiness_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "c" * 64)
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)

    assert (
        bridge.main(
            [
                "--activation-readiness-report",
                "--dispatch-mode",
                "execute",
                "--repo",
                target_repo,
            ]
        )
        == 0
    )
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["github_dispatch_readiness_state"] == "eligible_for_private_pilot_dispatch"
    assert report["github_dispatch_auth_status"] == "present"
    assert report["github_dispatch_auth_class"] == "installation"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert report["github_dispatch_workflow_status"] == "fixed"
    assert report["github_dispatch_execute_gate_status"] == "enabled"
    assert report["github_dispatch_live_approval_status"] == "dry_run_default"
    assert report["github_dispatch_authority"] == "display_only"
    assert report["evidence_graph_admission_status"] == "contract_only_not_runtime"
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert token not in stdout
    assert "ghs_" not in stdout
    assert "release/private-pilot" not in stdout
    assert "c" * 64 not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_labels_cross_repo_dry_run_without_dispatch_eligibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "c" * 64)
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)

    assert bridge.main(["--activation-readiness-report", "--repo", target_repo]) == 0
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["github_dispatch_readiness_state"] == "cross_repo_dry_run_available"
    assert report["github_dispatch_auth_status"] == "present"
    assert report["github_dispatch_auth_class"] == "installation"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert report["github_dispatch_execute_gate_status"] == "not_required"
    assert report["github_dispatch_live_approval_status"] == "dry_run_default"
    assert "eligible_for_private_pilot_dispatch" not in stdout
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert token not in stdout
    assert "ghs_" not in stdout
    assert "release/private-pilot" not in stdout
    assert "c" * 64 not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_allows_cross_repo_dry_run_without_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "c" * 64)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)

    assert bridge.main(["--activation-readiness-report", "--repo", target_repo]) == 0
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["github_dispatch_readiness_state"] == "cross_repo_dry_run_available"
    assert report["github_dispatch_auth_status"] == "missing"
    assert report["github_dispatch_auth_class"] == "none"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert report["github_dispatch_execute_gate_status"] == "not_required"
    assert "blocked_by_missing_auth" not in stdout
    assert "eligible_for_private_pilot_dispatch" not in stdout
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert "release/private-pilot" not in stdout
    assert "c" * 64 not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_allows_cross_repo_dry_run_with_runtime_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    runtime_token = "ghp_" + "b" * 24
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "d" * 64)
    monkeypatch.setenv("GH_TOKEN", runtime_token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)

    assert bridge.main(["--activation-readiness-report", "--repo", target_repo]) == 0
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["github_dispatch_readiness_state"] == "cross_repo_dry_run_available"
    assert report["github_dispatch_auth_status"] == "present"
    assert report["github_dispatch_auth_class"] == "runtime"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert report["github_dispatch_execute_gate_status"] == "not_required"
    assert "blocked_by_auth_class" not in stdout
    assert "eligible_for_private_pilot_dispatch" not in stdout
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert runtime_token not in stdout
    assert "ghp_" not in stdout
    assert "release/private-pilot" not in stdout
    assert "d" * 64 not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_cross_repo_non_installation_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    gh_token = "ghp_" + "b" * 24
    github_token = "ghs_" + "c" * 24
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "d" * 64)
    monkeypatch.setenv("GH_TOKEN", gh_token)
    monkeypatch.setenv("GITHUB_TOKEN", github_token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)

    assert (
        bridge.main(
            [
                "--activation-readiness-report",
                "--dispatch-mode",
                "execute",
                "--repo",
                target_repo,
            ]
        )
        == 1
    )
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["github_dispatch_readiness_state"] == "blocked_by_auth_class"
    assert report["github_dispatch_auth_status"] == "present"
    assert report["github_dispatch_auth_class"] == "runtime"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert "ghp_" not in stdout
    assert "ghs_" not in stdout
    assert gh_token not in stdout
    assert github_token not in stdout
    assert "release/private-pilot" not in stdout
    assert "d" * 64 not in stdout


def test_activation_readiness_report_blocks_malformed_github_dispatch_config_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    malformed_allowlist = "PilotOrg/PrivatePilot,"
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, malformed_allowlist)
    monkeypatch.setenv("GH_TOKEN", "ghs_" + "a" * 24)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)

    assert (
        bridge.main(
            [
                "--activation-readiness-report",
                "--dispatch-mode",
                "execute",
                "--repo",
                target_repo,
            ]
        )
        == 1
    )
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["github_dispatch_readiness_state"] == "blocked_by_invalid_config"
    assert report["github_dispatch_auth_status"] == "invalid"
    assert report["github_dispatch_auth_class"] == "invalid"
    assert report["github_dispatch_target_status"] == "invalid"
    assert report["github_dispatch_repo_allowlist_status"] == "invalid"
    assert report["github_dispatch_workflow_status"] == "invalid"
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert malformed_allowlist not in stdout
    assert "ghs_" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_execute_without_dispatch_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "e" * 64)
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)

    assert bridge.main(["--activation-readiness-report", "--dispatch-mode", "execute"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["github_dispatch_readiness_state"] == "blocked_by_missing_target"
    assert report["github_dispatch_target_status"] == "not_configured"
    assert report["github_dispatch_auth_status"] == "present"
    assert report["github_dispatch_execute_gate_status"] == "enabled"
    assert token not in stdout
    assert "ghs_" not in stdout
    assert "release/private-pilot" not in stdout
    assert "e" * 64 not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_cross_repo_execute_without_slack_allowlists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)

    assert (
        bridge.main(
            [
                "--activation-readiness-report",
                "--dispatch-mode",
                "execute",
                "--repo",
                target_repo,
            ]
        )
        == 1
    )
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["activation_state"] == "manual_only"
    assert report["github_dispatch_readiness_state"] == "blocked_by_slack_allowlist"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert report["github_dispatch_auth_status"] == "present"
    assert report["github_dispatch_auth_class"] == "installation"
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert token not in stdout
    assert "ghs_" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_unverified_live_approval_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    stale_approval = "f" * 64
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "f" * 64)
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)
    monkeypatch.setenv(bridge.LIVE_APPROVAL_SHA256_ENV, stale_approval)

    assert (
        bridge.main(
            [
                "--activation-readiness-report",
                "--dispatch-mode",
                "execute",
                "--repo",
                target_repo,
            ]
        )
        == 1
    )
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["github_dispatch_readiness_state"] == "blocked_by_live_approval_verification"
    assert report["github_dispatch_live_approval_status"] == "present_unverified"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert token not in stdout
    assert "ghs_" not in stdout
    assert stale_approval not in stdout
    assert "release/private-pilot" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_allows_cross_repo_dry_run_with_live_approval_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    stale_approval = "f" * 64
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "release/private-pilot")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "f" * 64)
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv(bridge.LIVE_APPROVAL_SHA256_ENV, stale_approval)

    assert bridge.main(["--activation-readiness-report", "--repo", target_repo]) == 0
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "pass"
    assert report["github_dispatch_readiness_state"] == "cross_repo_dry_run_available"
    assert report["github_dispatch_live_approval_status"] == "present_unverified"
    assert report["github_dispatch_target_status"] == "cross_repo"
    assert report["github_dispatch_repo_allowlist_status"] == "matched"
    assert "blocked_by_live_approval_verification" not in stdout
    assert "eligible_for_private_pilot_dispatch" not in stdout
    assert "PilotOrg" not in stdout
    assert "PrivatePilot" not in stdout
    assert target_repo not in stdout
    assert token not in stdout
    assert "ghs_" not in stdout
    assert stale_approval not in stdout
    assert "release/private-pilot" not in stdout
    assert "f" * 64 not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_missing_secret_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _clear_readiness_env(monkeypatch)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")

    assert bridge.main(["--activation-readiness-report"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["activation_state"] == "blocked_by_missing_secret"
    assert report["slack_app_token_status"] == "missing"
    assert report["slack_bot_token_status"] == "valid"
    assert report["channel_allowlist_status"] == "present"
    assert report["user_allowlist_status"] == "present"
    assert report["team_allowlist_status"] == "present"
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert "T0TEAM" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_allowlist_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _clear_readiness_env(monkeypatch)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")

    assert bridge.main(["--activation-readiness-report"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["activation_state"] == "blocked_by_allowlist"
    assert report["slack_app_token_status"] == "valid"
    assert report["slack_bot_token_status"] == "valid"
    assert report["channel_allowlist_status"] == "present"
    assert report["user_allowlist_status"] == "present"
    assert report["team_allowlist_status"] == "missing"
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_blocks_unchecked_smoke_inputs_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _clear_readiness_env(monkeypatch)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")

    assert bridge.main(["--activation-readiness-report"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["activation_state"] == "blocked_by_smoke_input"
    assert report["branch_ref_status"] == "not_checked"
    assert report["hypothesis_sha256_status"] == "not_checked"
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert "T0TEAM" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_rejects_malformed_shape_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "present-but-not-an-app-token")
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "/tmp/channel")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.BRIDGE_AUDIT_RETENTION_DAYS_ENV, "9999")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "feature/unsafe;branch")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, "raw hypothesis")

    assert bridge.main(["--activation-readiness-report"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["activation_state"] == "blocked_by_invalid_config"
    assert report["slack_app_token_status"] == "invalid"
    assert report["slack_bot_token_status"] == "valid"
    assert report["channel_allowlist_status"] == "invalid"
    assert report["branch_ref_status"] == "invalid"
    assert report["hypothesis_sha256_status"] == "invalid"
    assert report["audit_retention_status"] == "invalid"
    assert "present-but-not-an-app-token" not in stdout
    assert "xoxb-" not in stdout
    assert "/tmp/channel" not in stdout
    assert "feature/unsafe;branch" not in stdout
    assert "raw hypothesis" not in stdout
    assert "U0OPERATOR" not in stdout
    assert str(tmp_path) not in stdout


def test_activation_readiness_report_rejects_padded_hypothesis_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.setenv(bridge.SLACK_CHANNEL_ALLOWLIST_ENV, "C0ALERTS")
    monkeypatch.setenv(bridge.SLACK_USER_ALLOWLIST_ENV, "U0OPERATOR")
    monkeypatch.setenv(bridge.SLACK_TEAM_ALLOWLIST_ENV, "T0TEAM")
    monkeypatch.setenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, "main")
    monkeypatch.setenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, " " + "a" * 64)

    assert bridge.main(["--activation-readiness-report"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)

    assert report["status"] == "fail"
    assert report["activation_state"] == "blocked_by_invalid_config"
    assert report["hypothesis_sha256_status"] == "invalid"
    assert "a" * 64 not in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout


def test_smoke_input_validation_accepts_digest_without_echoing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "a" * 64)

    assert bridge.main(["--validate-smoke-inputs"]) == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)

    assert payload == {
        "branch_ref_status": "valid",
        "hypothesis_sha256_status": "valid",
        "status": "pass",
    }
    assert "main" not in stdout
    assert "a" * 64 not in stdout


def test_smoke_input_validation_rejects_padded_digest_without_echoing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", " " + "a" * 64)

    assert bridge.main(["--validate-smoke-inputs"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack live smoke input configuration is invalid" in stdout
    assert "a" * 64 not in stdout
    assert "main" not in stdout


def test_dispatch_input_validation_alias_accepts_digest_without_echoing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "b" * 64)

    assert bridge.main(["--validate-dispatch-inputs"]) == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)

    assert payload == {
        "branch_ref_status": "valid",
        "hypothesis_sha256_status": "valid",
        "status": "pass",
    }
    assert "main" not in stdout
    assert "b" * 64 not in stdout


def test_operator_help_status_and_mvp_evidence_renderers_are_slack_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    outputs = [
        bridge._format_command_reply(bridge.OperatorCommand(kind="help"), config),
        bridge._format_command_reply(bridge.OperatorCommand(kind="status"), config),
        bridge._format_command_reply(bridge.OperatorCommand(kind="mvp-evidence"), config),
    ]
    combined = "\n".join(outputs)

    assert "MVP evidence contract summary" in combined
    assert "Guided Planning Preview event contract" in combined
    assert "display_only_commands" in combined
    assert "advisory only" in combined
    assert "private_pilot_activation_state=manual_only" in combined
    assert "private_pilot_last_smoke=none" in combined
    assert "private_pilot_next_operator_action=run_manual_live_smoke" in combined
    assert "private_pilot_evidence_status=absent" in combined
    assert "private_pilot_evidence_age_class=absent" in combined
    assert "private_pilot_blocker_trend=none" in combined
    assert "private_pilot_import_status=absent" in combined
    assert "C0ALERTS" not in combined
    assert "U0OPERATOR" not in combined
    assert "xox" not in combined
    assert "xapp-" not in combined
    assert "ghp_" not in combined
    assert "/Users/" not in combined
    assert "/tmp/" not in combined
    assert "mergeable" not in combined.lower()
    assert "review resolved" not in combined.lower()


def test_operator_status_includes_private_pilot_readiness_without_target_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv(bridge.BRIDGE_EXECUTE_ENABLED_ENV, bridge.BRIDGE_EXECUTE_ENABLED_VALUE)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        audit_dir=audit_dir,
        dispatch_mode="execute",
        repo=target_repo,
    )

    output = bridge._format_command_reply(bridge.OperatorCommand(kind="status"), config)

    assert "github_dispatch_readiness_state=eligible_for_private_pilot_dispatch" in output
    assert "github_dispatch_auth_status=present" in output
    assert "github_dispatch_auth_class=installation" in output
    assert "github_dispatch_target_status=cross_repo" in output
    assert "github_dispatch_repo_allowlist_status=matched" in output
    assert "github_dispatch_workflow_status=fixed" in output
    assert "github_dispatch_execute_gate_status=enabled" in output
    assert "github_dispatch_live_approval_status=dry_run_default" in output
    assert "github_dispatch_authority=display_only" in output
    assert "evidence_graph_admission_status=contract_only_not_runtime" in output
    assert "private_pilot_activation_state=manual_only" in output
    assert "private_pilot_last_smoke=none" in output
    assert "private_pilot_next_operator_action=run_manual_live_smoke" in output
    assert "private_pilot_evidence_status=absent" in output
    assert "private_pilot_evidence_age_class=absent" in output
    assert "private_pilot_blocker_trend=none" in output
    assert "private_pilot_import_status=absent" in output
    assert "workflow_authority_changed=false" in output
    assert "semantic_cache_enabled=false" in output
    assert "PilotOrg" not in output
    assert "PrivatePilot" not in output
    assert target_repo not in output
    assert token not in output
    assert "ghs_" not in output
    assert "C0ALERTS" not in output
    assert "U0OPERATOR" not in output
    assert str(tmp_path) not in output


def test_operator_status_projects_latest_private_pilot_activation_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    repo_root = _repo_root_from_audit_dir(audit_dir)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    evidence = experiment_private_pilot_activation.build_private_pilot_activation_evidence(
        {
            "activation_state": "ready_for_manual_live_smoke",
            "audit_retention_status": "valid",
            "branch_ref_status": "valid",
            "channel_allowlist_status": "present",
            "github_dispatch_auth_class": "installation",
            "github_dispatch_auth_status": "present",
            "github_dispatch_authority": "display_only",
            "github_dispatch_execute_gate_status": "enabled",
            "github_dispatch_live_approval_status": "dry_run_default",
            "github_dispatch_readiness_state": "eligible_for_private_pilot_dispatch",
            "github_dispatch_repo_allowlist_status": "matched",
            "github_dispatch_target_status": "cross_repo",
            "github_dispatch_workflow_status": "fixed",
            "hypothesis_sha256_status": "valid",
            "manual_live_smoke": "operator_evidence_only",
            "raw_branch": "refs/heads/feature/private-pilot",
            "raw_digest": "a" * 64,
            "raw_patch": "diff --git a/secret b/secret",
            "raw_path": "/Users/alice/PulsePlate",
            "raw_repo": "PilotOrg/PrivatePilot",
            "raw_slack": "C0SECRETID",
            "raw_token": "ghs_header.payload.signaturesecretsecretsecret",
            "slack_app_token_status": "valid",
            "slack_bot_token_status": "valid",
            "smoke_input_requirement": "required",
            "team_allowlist_status": "present",
            "user_allowlist_status": "present",
        },
        dispatch_outcome_class="smoke_recorded",
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
    experiment_operator_ledger.write_private_pilot_activation_evidence(
        evidence,
        repo_root=repo_root,
    )

    output = bridge._format_command_reply(bridge.OperatorCommand(kind="status"), config)

    assert "private_pilot_activation_state=smoke_recorded" in output
    assert "private_pilot_last_smoke=smoke_recorded" in output
    assert "private_pilot_next_operator_action=review_activation_report" in output
    assert "private_pilot_dispatch_outcome_class=smoke_recorded" in output
    assert "private_pilot_evidence_status=valid" in output
    assert "private_pilot_evidence_age_class=fresh" in output
    assert "private_pilot_blocker_trend=recorded_smoke" in output
    assert "private_pilot_import_status=valid" in output
    assert "private_pilot_authority=display_only" in output
    assert "PilotOrg" not in output
    assert "PrivatePilot" not in output
    assert "refs/heads" not in output
    assert "C0SECRETID" not in output
    assert "ghs_" not in output
    assert "diff --git" not in output
    assert str(tmp_path) not in output


def test_operator_status_requires_team_allowlist_for_configured_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR")
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", raising=False)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    output = bridge._format_command_reply(bridge.OperatorCommand(kind="status"), config)

    assert "Status: `incomplete`" in output
    assert "team_allowlist_present=false" in output


def _operator_ledger_event(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "branch_hash": bridge._sha256_text("feature/operator-plane"),
        "channel_hash": bridge._sha256_text("C0SECRET"),
        "claimed_merge_readiness": False,
        "coauthor_decision": "not_required",
        "coauthor_required": False,
        "command_kind": "status",
        "created_pr": False,
        "dispatch_mode": "dry-run",
        "event_hash": bridge._sha256_text("Ev0SECRET"),
        "failure_class": "none",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "human_review_outcome": "pending",
        "hypothesis_hash": bridge._sha256_text("raw hypothesis must not render"),
        "oracle_result_hash": bridge._sha256_text("oracle result"),
        "oracle_result_ref": ("artifacts/orchestration/experiments/results/operator-plane.json"),
        "policy_version": experiment_operator_ledger.POLICY_VERSION,
        "product_runtime_changed": False,
        "provider_type": experiment_operator_ledger.PROVIDER_TYPE,
        "redaction_version": experiment_operator_ledger.REDACTION_VERSION,
        "resolved_review_threads": False,
        "retention_days": experiment_operator_ledger.DEFAULT_RETENTION_DAYS,
        "schema_version": experiment_operator_ledger.SCHEMA_VERSION,
        "slack_audit_hash": bridge._sha256_text("slack audit"),
        "slack_audit_ref": ("artifacts/orchestration/experiments/slack_socket_bridge/audit.json"),
        "status": "dry_run",
        "task_packet_id": "792c1fdf2e55",
        "team_hash": bridge._sha256_text("T0SECRET"),
        "user_hash": bridge._sha256_text("U0DENIED"),
        "workflow_file": "experiment-runner-dispatch.yml",
        "workflow_ref": "main",
    }
    payload.update(overrides)
    return payload


def test_operator_status_includes_redacted_local_operator_ledger_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    repo_root = audit_dir.parents[3]
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    experiment_operator_ledger.write_operator_ledger_event(
        _operator_ledger_event(),
        repo_root=repo_root,
    )

    output = bridge._format_command_reply(bridge.OperatorCommand(kind="status"), config)

    assert "operator_ledger_status=dry_run" in output
    assert "operator_ledger_scope=local_only" in output
    assert "operator_ledger_authority=display_only" in output
    assert bridge._sha256_text("feature/operator-plane")[:16] in output
    assert "C0SECRET" not in output
    assert "U0DENIED" not in output
    assert "T0SECRET" not in output
    assert "feature/operator-plane" not in output
    assert "raw hypothesis" not in output
    assert "/Users/" not in output
    assert "mergeable" not in output.lower()


def test_mvp_evidence_event_contract_matches_frontend_source() -> None:
    frontend_source = (REPO_ROOT / "frontend" / "src" / "lib" / "mvpObservability.ts").read_text(
        encoding="utf-8"
    )
    event_type_block = frontend_source.split("export type GuidedPlanningEventName =", 1)[1].split(
        ";", 1
    )[0]
    frontend_events = set(re.findall(r"\| '([^']+)'", event_type_block))
    from scripts.orchestration.mvp_evidence_snapshot import ALLOWED_EVENT_NAMES

    snapshot_events = set(ALLOWED_EVENT_NAMES)

    assert frontend_events
    assert snapshot_events
    assert snapshot_events == frontend_events
    assert "email" not in snapshot_events
    assert "weight" not in snapshot_events
    assert "bmi" not in snapshot_events


def test_dispatch_preview_hashes_branch_and_hypothesis_without_dispatching(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    command = bridge.OperatorCommand(
        kind="run-experiment",
        branch_ref="feature/safe-branch",
        hypothesis="Validate bounded operator evidence preview",
    )

    output = bridge._format_command_reply(command, config)

    assert "Dispatch dry-run preview" in output
    assert "dry_run=true" in output
    assert bridge._sha256_text("feature/safe-branch") in output
    assert bridge._sha256_text("Validate bounded operator evidence preview") in output
    assert "feature/safe-branch" not in output
    assert "Validate bounded operator evidence preview" not in output


def test_slack_text_renderer_redacts_secret_mentions_and_paths() -> None:
    message = bridge.SlackSafeMessage(
        message_type="failure_class_alert",
        header="@channel <@U0SECRET> `alert`",
        status_line="guard_failure",
        scope="Path /Users/alice/.ssh/id_rsa and token xoxb-secretsecretsecret",
        evidence_summary=(
            "webhook https://hooks.slack.com/services/AAA/BBB/CCCCCCCCCCCC",
            "raw patch diff --git a/secret b/secret",
        ),
        action_required="Do not ping @here or <#C0SECRET>",
    ).as_text()

    assert "@[redacted-mention]" in message
    assert "[redacted-slack-id]" in message
    assert "[redacted-path]" in message
    assert "[redacted-secret]" in message
    assert "xoxb" not in message
    assert "hooks.slack.com" not in message
    assert "/Users/alice" not in message
    assert "`alert`" not in message
    assert "U0SECRET" not in message
    assert "C0SECRET" not in message
    assert "diff --git" not in message
    assert "raw patch" not in message


def test_mvp_evidence_command_uses_existing_auth_audit_and_no_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(_event(command="/pulseplate-runner", text="mvp-evidence")),
        encoding="utf-8",
    )

    assert (
        bridge.main(
            [
                "--event-json",
                str(event_path),
                "--audit-dir",
                str(audit_dir),
                "--reply-format",
                "text",
            ]
        )
        == 0
    )
    stdout = capsys.readouterr().out

    assert "MVP evidence contract summary" in stdout
    assert "guided_planning_viewed" not in stdout
    assert "C0ALERTS" not in stdout
    audit_path = audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json"
    audit_text = audit_path.read_text(encoding="utf-8")
    audit = json.loads(audit_text)
    assert audit["command_kind"] == "mvp-evidence"
    assert audit["status"] == "dry_run"
    assert "C0ALERTS" not in audit_text
    assert "U0OPERATOR" not in audit_text


def test_execute_mode_text_reply_reports_dispatch_not_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "e" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "1")
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(_event(text="feature/test Validate bounded execution reply")),
        encoding="utf-8",
    )
    calls: list[dict[str, Any]] = []

    config = bridge.build_config(
        dispatch_mode="execute",
        audit_dir=str(audit_dir),
        repo="Katsiarynakavaleuskaya/PulsePlate",
    )
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    decision = bridge.process_payload(
        payload, config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
    )
    event = bridge.normalize_slack_payload(payload)
    command = bridge.parse_operator_command(event.text, command_hint=event.command_hint)
    reply = bridge._format_command_reply(command, config, decision=decision)

    assert len(calls) == 1
    assert len(_ledger_records(audit_dir)) == 1
    assert "Experiment Runner dispatch result" in reply
    assert "Status: `dispatched`" in reply
    assert "workflow_input_dry_run=true" in reply
    assert "dry_run_only" not in reply
    assert "feature/test" not in reply
    assert "Validate bounded execution reply" not in reply
    capsys.readouterr()


def test_run_socket_listener_registers_runner_and_experiment_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    registered: list[str] = []

    class FakeApp:
        def __init__(self, token: str) -> None:
            assert token.startswith("xoxb-")

        def command(self, command_name: str) -> Any:
            registered.append(command_name)

            def decorator(handler: object) -> object:
                return handler

            return decorator

    class FakeSocketModeHandler:
        def __init__(self, app: FakeApp, token: str) -> None:
            assert token.startswith("xapp-")

        def start(self) -> None:
            return None

    monkeypatch.setattr(bridge, "_load_slack_bolt", lambda: (FakeApp, FakeSocketModeHandler))

    assert (
        bridge.run_socket_listener(
            _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
        )
        == 0
    )
    assert registered == ["/run-experiment", "/pulseplate-runner"]


def test_run_socket_listener_rejection_reply_is_redacted_and_logs_failure_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    responses: list[str] = []

    class FakeApp:
        handler: Any = None

        def __init__(self, token: str) -> None:
            assert token.startswith("xoxb-")

        def command(self, _command_name: str) -> Any:
            def decorator(handler: object) -> object:
                FakeApp.handler = handler
                return handler

            return decorator

    class FakeSocketModeHandler:
        def __init__(self, app: FakeApp, token: str) -> None:
            assert token.startswith("xapp-")

        def start(self) -> None:
            assert FakeApp.handler is not None
            FakeApp.handler(
                lambda: None,
                _event(text="run-experiment feature/test xoxb-secretsecretsecret"),
                responses.append,
            )

    monkeypatch.setattr(bridge, "_load_slack_bolt", lambda: (FakeApp, FakeSocketModeHandler))

    with caplog.at_level("WARNING", logger=bridge.__name__):
        assert bridge.run_socket_listener(_config(audit_dir=audit_dir)) == 0

    assert responses == [
        "Experiment Runner bridge rejected the request. No sensitive details included."
    ]
    assert "SlackSocketCommandError" in caplog.text
    assert "xoxb-" not in caplog.text
    assert "feature/test" not in caplog.text


@pytest.mark.parametrize(
    ("branch_ref", "hypothesis_sha256"),
    [
        ("../main", "a" * 64),
        ("main", "raw hypothesis text"),
    ],
)
def test_smoke_input_validation_rejects_unsafe_values_without_echoing_them(
    branch_ref: str,
    hypothesis_sha256: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", branch_ref)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", hypothesis_sha256)

    assert bridge.main(["--validate-smoke-inputs"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack live smoke input configuration is invalid" in stdout
    assert branch_ref not in stdout
    assert hypothesis_sha256 not in stdout


def test_bounded_live_smoke_validates_slack_without_sdk_or_raw_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "c" * 64)
    calls: list[dict[str, Any]] = []

    def fake_slack_api(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        if kwargs["method"] == "apps.connections.open":
            return {
                "ok": True,
                "url": "wss://wss.example.invalid/link/?ticket=secret",
            }
        return {
            "bot_id": "B0SECRET",
            "ok": True,
            "team_id": "T0SECRET",
            "user_id": "U0SECRET",
        }

    def fail_if_sdk_loads() -> tuple[Any, Any]:
        raise AssertionError("bounded live smoke must not load Slack SDK")

    monkeypatch.setattr(bridge, "_send_slack_api_request", fake_slack_api)
    monkeypatch.setattr(bridge, "_load_slack_bolt", fail_if_sdk_loads)

    assert bridge.main(["--validate-live-smoke"]) == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)

    assert payload == {
        "allowlist_status": "present",
        "bot_auth_status": "validated",
        "branch_ref_status": "valid",
        "dispatch_mode": "dry-run",
        "hypothesis_sha256_status": "valid",
        "socket_mode_status": "validated",
        "status": "pass",
    }
    assert [call["method"] for call in calls] == ["apps.connections.open", "auth.test"]
    assert calls[0]["token"].startswith("xapp-")
    assert calls[1]["token"].startswith("xoxb-")
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "wss://" not in stdout
    assert "T0SECRET" not in stdout
    assert "U0SECRET" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout
    assert "c" * 64 not in stdout


def test_bounded_live_smoke_failure_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "d" * 64)

    def fake_slack_api(**_kwargs: Any) -> dict[str, Any]:
        return {
            "error": "invalid_auth",
            "ok": False,
            "url": "wss://wss.example.invalid/link/?ticket=secret",
        }

    monkeypatch.setattr(bridge, "_send_slack_api_request", fake_slack_api)

    assert bridge.main(["--validate-live-smoke"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack live smoke Socket Mode validation failed: invalid_auth." in stdout
    assert "wss://" not in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout
    assert "C0ALERTS" not in stdout
    assert "U0OPERATOR" not in stdout


def test_bounded_live_smoke_failure_suppresses_unsafe_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "e" * 64)

    def fake_slack_api(**_kwargs: Any) -> dict[str, Any]:
        return {
            "error": "invalid_auth xapp-secret",
            "ok": False,
        }

    monkeypatch.setattr(bridge, "_send_slack_api_request", fake_slack_api)

    assert bridge.main(["--validate-live-smoke"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack live smoke Socket Mode validation failed: unknown." in stdout
    assert "invalid_auth xapp-secret" not in stdout
    assert "xapp-" not in stdout


@pytest.mark.parametrize(
    "payload",
    [
        {"ok": True},
        {"ok": True, "url": "https://wss.example.invalid/link/?ticket=secret"},
    ],
)
def test_bounded_live_smoke_requires_socket_mode_wss_url_without_echoing_it(
    payload: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", "main")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "f" * 64)
    monkeypatch.setattr(bridge, "_send_slack_api_request", lambda **_kwargs: payload)

    assert bridge.main(["--validate-live-smoke"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack live smoke Socket Mode validation failed" in stdout
    assert "wss.example.invalid" not in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout


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


@pytest.mark.parametrize(
    ("env_name", "token"),
    [
        ("SLACK_APP_TOKEN", "xoxb-" + "a" * 24),
        ("SLACK_BOT_TOKEN", "xapp-" + "b" * 24),
    ],
)
def test_slack_runtime_tokens_must_match_expected_token_class(
    env_name: str,
    token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.setenv(env_name, token)

    assert bridge.main(["--validate-runtime", "--run-socket", "--audit-dir", str(audit_dir)]) == 1
    stdout = capsys.readouterr().out

    assert f"{env_name} token class is invalid" in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout


def test_execute_runtime_validation_requires_github_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "execute"]) == 1
    stdout = capsys.readouterr().out

    assert "GitHub dispatch configuration is incomplete" in stdout
    assert "GH_TOKEN" not in stdout
    assert "GITHUB_TOKEN" not in stdout


def test_execute_runtime_validation_requires_channel_user_and_team_allowlists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM")
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", raising=False)
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "g" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "execute"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack Socket Mode allowlist configuration is incomplete" in stdout
    assert "T0TEAM" not in stdout
    assert "ghp_" not in stdout


def test_execute_runtime_validation_requires_reviewed_promotion_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "g" * 24)

    assert (
        bridge.main(
            ["--validate-runtime", "--dispatch-mode", "execute", "--audit-dir", str(audit_dir)]
        )
        == 1
    )
    stdout = capsys.readouterr().out

    assert "Slack execute-mode promotion gate is not enabled" in stdout
    assert "reviewed-dry-run-dispatch" not in stdout
    assert "ghp_" not in stdout


@pytest.mark.parametrize(
    "token",
    [
        "ghp_" + "a" * 24,
        "gho_" + "b" * 24,
        "ghu_" + "c" * 24,
        "ghr_" + "d" * 24,
        "ghs_" + "e" * 24,
        "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15,
        "ghs_header-payload.signature-with-hyphen.stateless-token-fixture" + "a" * 24,
        "github_pat_" + "f" * 24,
    ],
)
def test_execute_runtime_accepts_github_token_classes_without_leaking_token(
    token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GITHUB_REPOSITORY", "Katsiarynakavaleuskaya/PulsePlate")
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")

    assert (
        bridge.main(
            ["--validate-runtime", "--dispatch-mode", "execute", "--audit-dir", str(audit_dir)]
        )
        == 0
    )
    stdout = capsys.readouterr().out

    assert token not in stdout
    assert "ghs_" not in stdout
    assert "github_pat_" not in stdout


def test_github_token_env_precedence_accepts_stateless_installation_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    gh_token = "ghs_header.payload.signature" + "_A" * 260
    github_token = "ghp_" + "b" * 24
    monkeypatch.setenv("GH_TOKEN", gh_token)
    monkeypatch.setenv("GITHUB_TOKEN", github_token)

    config = bridge.build_config(
        dispatch_mode="execute",
        audit_dir=str(audit_dir),
        repo="Katsiarynakavaleuskaya/PulsePlate",
    )

    assert config.github_token == gh_token
    assert config.github_dispatch is not None
    assert config.github_dispatch.auth is not None
    assert config.github_dispatch.auth.token == gh_token
    assert config.github_dispatch.auth.is_installation_token


def test_github_dispatch_auth_repr_redacts_installation_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    token = "ghs_header.payload.signature" + "_A" * 260
    monkeypatch.setenv("GH_TOKEN", token)

    config = bridge.build_config(
        dispatch_mode="execute",
        audit_dir=str(audit_dir),
        repo="Katsiarynakavaleuskaya/PulsePlate",
    )

    assert config.github_dispatch is not None
    assert config.github_dispatch.auth is not None
    assert token not in repr(config.github_dispatch.auth)
    assert token not in repr(config.github_dispatch)
    assert token not in repr(config)
    assert "ghs_" not in repr(config)


def test_cross_repo_execute_accepts_allowlisted_installation_token_without_leakage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    token = "ghs_header.payload.signature" + "_statelessinstallationtokenfixture" * 15
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo=target_repo,
    )
    calls: list[dict[str, Any]] = []

    decision = bridge.process_payload(
        _event(text="release/private-pilot Validate bounded private pilot dispatch"),
        config,
        dispatch_transport=lambda **kwargs: calls.append(kwargs),
    )

    assert decision.status == "dispatched"
    assert calls == [
        {
            "inputs": {
                "approval_ref": "none",
                "branch_ref": "release/private-pilot",
                "dry_run": "true",
                "hypothesis_sha256": bridge._sha256_text("Validate bounded private pilot dispatch"),
            },
            "ref": "main",
            "repo": target_repo,
            "timeout_seconds": 5,
            "token": token,
            "workflow_file": "experiment-runner-dispatch.yml",
        }
    ]
    audit_payload = json.loads(
        (audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").read_text()
    )
    records = _ledger_records(audit_dir)
    serialized_governance = json.dumps(
        {"audit": audit_payload, "ledger": [record.payload for record in records]},
        sort_keys=True,
    )
    assert "PilotOrg" not in serialized_governance
    assert "PrivatePilot" not in serialized_governance
    assert token not in serialized_governance
    assert "ghs_" not in serialized_governance
    assert records[0].payload["created_pr"] is False
    assert records[0].payload["resolved_review_threads"] is False
    assert records[0].payload["claimed_merge_readiness"] is False


@pytest.mark.parametrize("allowlist", ["", "OtherOrg/OtherRepo"])
def test_cross_repo_execute_rejects_missing_or_nonmatching_allowlist_before_dispatch(
    allowlist: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    monkeypatch.setenv("GH_TOKEN", "ghs_" + "a" * 24)
    if allowlist:
        monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, allowlist)
    else:
        monkeypatch.delenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, raising=False)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo=target_repo,
    )
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketDispatchError):
        bridge.process_payload(
            _event(),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []
    audit_payload = json.loads(
        (audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").read_text()
    )
    serialized_audit = json.dumps(audit_payload, sort_keys=True)
    assert "PilotOrg" not in serialized_audit
    assert "PrivatePilot" not in serialized_audit
    assert "ghs_" not in serialized_audit


def test_cross_repo_execute_rejects_non_installation_token_even_when_allowlisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "b" * 24)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo=target_repo,
    )
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketDispatchError):
        bridge.process_payload(
            _event(),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


def test_cross_repo_execute_preserves_gh_token_precedence_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    gh_token = "ghp_" + "c" * 24
    github_token = "ghs_" + "d" * 24
    monkeypatch.setenv("GH_TOKEN", gh_token)
    monkeypatch.setenv("GITHUB_TOKEN", github_token)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, target_repo)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo=target_repo,
    )
    calls: list[dict[str, Any]] = []

    assert config.github_dispatch is not None
    assert config.github_dispatch.auth is not None
    assert config.github_dispatch.auth.token == gh_token
    with pytest.raises(bridge.SlackSocketDispatchError):
        bridge.process_payload(
            _event(),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


@pytest.mark.parametrize(
    "allowlist",
    [
        "PilotOrg/PrivatePilot,",
        " PilotOrg/PrivatePilot",
        "PilotOrg/PrivatePilot ",
        "PilotOrg/PrivatePilot,,OtherOrg/Repo",
        "PilotOrg/..",
        "../PrivatePilot",
        "PilotOrg/%2e%2e",
        "PilotOrg/Private/Pilot",
        "*/PrivatePilot",
    ],
)
def test_github_dispatch_repo_allowlist_rejects_malformed_entries(
    allowlist: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv(bridge.GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, allowlist)

    with pytest.raises(bridge.SlackSocketConfigError, match="GitHub dispatch configuration"):
        bridge.build_config(
            dispatch_mode="execute",
            audit_dir=str(audit_dir),
            repo="PilotOrg/PrivatePilot",
        )


@pytest.mark.parametrize("token", ["xapp-" + "a" * 24, "sk-" + "b" * 24])
def test_execute_runtime_rejects_non_github_token_classes(
    token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv("GH_TOKEN", token)

    assert (
        bridge.main(
            ["--validate-runtime", "--dispatch-mode", "execute", "--audit-dir", str(audit_dir)]
        )
        == 1
    )
    stdout = capsys.readouterr().out

    assert "GitHub dispatch configuration is invalid" in stdout
    assert "xapp-" not in stdout
    assert "sk-" not in stdout


@pytest.mark.parametrize(
    ("token", "sensitive_fragment"),
    [
        ("ghs_valid.segment\nnext", "ghs_valid"),
        ("ghs_valid.segment\rnext", "ghs_valid"),
        ("ghs_valid.segment`next", "ghs_valid"),
        ("ghs_valid segment", "ghs_valid"),
        ("ghs_valid/segment", "ghs_valid"),
        ("ghs_valid;segment", "ghs_valid"),
        ("ghs_valid|segment", "ghs_valid"),
        ("ghs_valid$segment", "ghs_valid"),
        ("header.payload.signature", "header.payload.signature"),
        ("xoxb-" + "c" * 24, "xoxb-"),
    ],
)
def test_execute_runtime_rejects_unsafe_or_non_github_token_shapes(
    token: str,
    sensitive_fragment: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv("GH_TOKEN", token)

    assert (
        bridge.main(
            ["--validate-runtime", "--dispatch-mode", "execute", "--audit-dir", str(audit_dir)]
        )
        == 1
    )
    stdout = capsys.readouterr().out

    assert "GitHub dispatch configuration is invalid" in stdout
    assert token not in stdout
    assert sensitive_fragment not in stdout


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
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", raising=False)

    assert bridge.main(["--validate-runtime", "--run-socket"]) == 1
    stdout = capsys.readouterr().out

    assert "allowlist configuration is incomplete" in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout


def test_live_socket_validation_requires_team_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-" + "a" * 24)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-" + "b" * 24)
    monkeypatch.delenv("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", raising=False)

    assert bridge.main(["--validate-runtime", "--run-socket"]) == 1
    stdout = capsys.readouterr().out

    assert "allowlist configuration is incomplete" in stdout
    assert "T0TEAM" not in stdout
    assert "xapp-" not in stdout
    assert "xoxb-" not in stdout


@pytest.mark.parametrize(
    ("env_name", "value"),
    [
        ("EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST", "C0ALERTS, ,C0OPS"),
        ("EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST", "U0OPERATOR, ,U0REVIEWER"),
        ("EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST", "T0TEAM, ,T0ALT"),
    ],
)
def test_allowlists_reject_empty_comma_segments(
    env_name: str,
    value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv(env_name, value)

    with pytest.raises(bridge.SlackSocketConfigError, match="allowlist is invalid"):
        _config(audit_dir=audit_dir)


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


def test_config_rejects_arbitrary_workflow_file(
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
            workflow_file="experiment-runner-slack-socket-smoke.yml",
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


def test_operator_ledger_task_packet_id_defaults_to_safe_static_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    monkeypatch.delenv("EXPERIMENT_OPERATOR_LEDGER_TASK_PACKET_ID", raising=False)

    config = bridge.build_config(dispatch_mode="dry-run", audit_dir=str(audit_dir))

    assert config.operator_ledger_task_packet_id == bridge.DEFAULT_OPERATOR_LEDGER_TASK_PACKET_ID


@pytest.mark.parametrize("packet_id", ["C12345678", "   "])
def test_malformed_operator_ledger_task_packet_id_blocks_before_dispatch(
    packet_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_OPERATOR_LEDGER_TASK_PACKET_ID", packet_id)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "z" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    calls: list[dict[str, Any]] = []

    assert bridge.main(["--validate-runtime", "--dispatch-mode", "dry-run"]) == 1
    stdout = capsys.readouterr().out
    with pytest.raises(bridge.SlackSocketConfigError):
        _config_without_rate_limit(
            monkeypatch=monkeypatch,
            dispatch_mode="execute",
            audit_dir=audit_dir,
        )

    assert calls == []
    assert "Slack operator bridge configuration is invalid" in stdout
    if packet_id.strip():
        assert packet_id not in stdout
    assert not (audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").exists()
    assert not experiment_operator_ledger.default_ledger_dir(
        _repo_root_from_audit_dir(audit_dir)
    ).exists()


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
    assert decision.public_payload()["workflow_ref"] == "main"
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
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    ledger_payload = records[0].payload
    assert ledger_payload["status"] == "dry_run"
    assert ledger_payload["command_kind"] == "run-experiment"
    assert ledger_payload["dispatch_mode"] == "dry-run"
    assert ledger_payload["task_packet_id"] == "packet-pr2"
    assert ledger_payload["workflow_file"] == "experiment-runner-dispatch.yml"
    assert ledger_payload["workflow_ref"] == "main"
    assert ledger_payload["branch_hash"] == bridge._sha256_text("feature/test")
    assert ledger_payload["hypothesis_hash"] == bridge._sha256_text(
        "Improve oracle evidence throughput"
    )
    assert ledger_payload["claimed_merge_readiness"] is False
    assert ledger_payload["resolved_review_threads"] is False
    assert decision.operator_ledger_ref == (
        "artifacts/orchestration/experiments/operator_ledger/events/"
        f"{ledger_payload['idempotency_key']}.json"
    )
    assert "C0ALERTS" not in json.dumps(ledger_payload, sort_keys=True)
    assert "U0OPERATOR" not in json.dumps(ledger_payload, sort_keys=True)
    assert "Improve oracle" not in json.dumps(ledger_payload, sort_keys=True)
    assert "feature/test" not in json.dumps(ledger_payload, sort_keys=True)


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


def test_status_command_reflects_latest_operator_ledger_event_after_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    decision = bridge.process_payload(
        _event(text="feature/status-ledger Validate status ledger summary"),
        config,
    )
    status_decision = bridge.process_payload(
        _event(
            event_id="Ev0STATUSLEDGER",
            command="/pulseplate-runner",
            text="status",
        ),
        config,
    )
    status_reply = bridge._format_command_reply(
        bridge.OperatorCommand(kind="status"),
        config,
        decision=status_decision,
    )

    assert decision.status == "dry_run"
    assert status_decision.status == "dry_run"
    assert status_decision.command_kind == "status"
    assert len(_ledger_records(audit_dir)) == 1
    assert "operator_ledger_status=dry_run" in status_reply
    assert "operator_ledger_command_kind=run-experiment" in status_reply
    assert "operator_ledger_command_kind=status" not in status_reply
    assert "operator_ledger_workflow_file=experiment-runner-dispatch.yml" in status_reply
    assert "operator_ledger_workflow_file=none" not in status_reply
    assert bridge._sha256_text("feature/status-ledger")[:16] in status_reply
    assert "feature/status-ledger" not in status_reply
    assert "Validate status ledger summary" not in status_reply
    assert "socket_mode_activation_state=blocked_by_missing_secret" in status_reply
    assert "socket_mode_readiness_status=fail" in status_reply
    assert "manual_live_smoke=operator_evidence_only" in status_reply
    assert "deterministic_ci_requires_live_slack=false" in status_reply
    assert "opened_http_ingress=false" in status_reply
    assert "semantic_cache_enabled=false" in status_reply
    assert "claimed_merge_readiness=false" in status_reply
    assert "activation_authority=display_only" in status_reply
    assert "display_only" in status_reply


def test_status_command_does_not_fail_on_absent_manual_smoke_inputs_for_live_listener(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv(bridge.SLACK_APP_AUTH_ENV, "xapp-" + "a" * 24)
    monkeypatch.setenv(bridge.SLACK_BOT_AUTH_ENV, "xoxb-" + "b" * 24)
    monkeypatch.delenv(bridge.LIVE_SMOKE_BRANCH_REF_ENV, raising=False)
    monkeypatch.delenv(bridge.LIVE_SMOKE_HYPOTHESIS_SHA256_ENV, raising=False)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    status_reply = bridge._format_command_reply(bridge.OperatorCommand(kind="status"), config)

    assert "socket_mode_readiness_status=pass" in status_reply
    assert "socket_mode_activation_state=manual_only" in status_reply
    assert "branch_ref_status=not_checked" in status_reply
    assert "hypothesis_sha256_status=not_checked" in status_reply
    assert "blocked_by_smoke_input" not in status_reply
    assert "xapp-" not in status_reply
    assert "xoxb-" not in status_reply
    assert "C0ALERTS" not in status_reply
    assert "U0OPERATOR" not in status_reply
    assert str(tmp_path) not in status_reply


def test_repeated_status_commands_keep_dispatch_ledger_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    bridge.process_payload(
        _event(text="feature/status-repeat Validate repeated status summary"),
        config,
    )
    first_status = bridge.process_payload(
        _event(
            event_id="Ev0STATUSONE",
            command="/pulseplate-runner",
            text="status",
        ),
        config,
    )
    second_status = bridge.process_payload(
        _event(
            event_id="Ev0STATUSTWO",
            command="/pulseplate-runner",
            text="status",
        ),
        config,
    )
    status_reply = bridge._format_command_reply(
        bridge.OperatorCommand(kind="status"),
        config,
        decision=second_status,
    )

    assert first_status.operator_ledger_ref is None
    assert second_status.operator_ledger_ref is None
    assert len(_ledger_records(audit_dir)) == 1
    assert "operator_ledger_command_kind=run-experiment" in status_reply
    assert "operator_ledger_command_kind=status" not in status_reply
    assert bridge._sha256_text("feature/status-repeat")[:16] in status_reply
    assert "feature/status-repeat" not in status_reply


def test_status_command_bypasses_dispatch_rate_limit_for_latest_ledger_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    dispatch_config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    bridge.process_payload(
        _event(text="feature/status-throttle Validate status after dispatch throttle"),
        dispatch_config,
    )
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "3600")
    status_config = _config(dispatch_mode="dry-run", audit_dir=audit_dir)

    decision = bridge.process_payload(
        _event(
            event_id="Ev0STATUSBYPASS",
            command="/pulseplate-runner",
            text="status",
        ),
        status_config,
    )
    status_reply = bridge._format_command_reply(
        bridge.OperatorCommand(kind="status"),
        status_config,
        decision=decision,
    )

    assert decision.status == "dry_run"
    assert decision.operator_ledger_ref is None
    assert len(_ledger_records(audit_dir)) == 1
    assert "operator_ledger_command_kind=run-experiment" in status_reply
    assert bridge._sha256_text("feature/status-throttle")[:16] in status_reply
    assert "rate limit" not in status_reply.lower()


def test_status_command_reports_invalid_ledger_without_requiring_write_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    ledger_dir = (
        _repo_root_from_audit_dir(audit_dir) / "artifacts" / "orchestration" / "experiments"
    )
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "operator_ledger").write_text("not a directory", encoding="utf-8")
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    decision = bridge.process_payload(
        _event(
            event_id="Ev0STATUSINVALIDLEDGER",
            command="/pulseplate-runner",
            text="status",
        ),
        config,
    )
    reply = bridge._format_command_reply(
        bridge.OperatorCommand(kind="status"),
        config,
        decision=decision,
    )

    assert decision.status == "dry_run"
    assert decision.operator_ledger_ref is None
    assert "operator_ledger_status=invalid_local_artifact" in reply
    assert "operator_ledger_authority=display_only" in reply


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


def test_malformed_payload_ids_are_command_errors_not_config_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    with pytest.raises(bridge.SlackSocketCommandError, match="payload is invalid"):
        bridge.process_payload(_event(event_id="/tmp/not-a-slack-id"), config)


def test_execute_mode_dispatches_only_fixed_workflow_with_typed_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "c" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
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
    assert calls[0]["workflow_file"] == "experiment-runner-dispatch.yml"
    assert calls[0]["ref"] == "main"
    assert calls[0]["inputs"] == {
        "approval_ref": "none",
        "branch_ref": "release/smoke",
        "dry_run": "true",
        "hypothesis_sha256": bridge._sha256_text("Validate bounded Slack operator bridge"),
    }
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    assert records[0].payload["status"] == "dispatched"
    assert records[0].payload["dispatch_mode"] == "execute"
    assert records[0].payload["human_review_outcome"] == "pending"
    assert records[0].payload["branch_hash"] == bridge._sha256_text("release/smoke")
    assert bridge.DEFAULT_WORKFLOW_FILE == "experiment-runner-dispatch.yml"
    assert bridge.ALLOWED_WORKFLOWS == {"experiment-runner-dispatch.yml"}


def test_same_repo_execute_allows_runtime_token_without_github_repository_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "s" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo="Katsiarynakavaleuskaya/PulsePlate",
    )
    calls: list[dict[str, Any]] = []

    decision = bridge.process_payload(
        _event(text="release/smoke Validate bounded same-repo dispatch"),
        config,
        dispatch_transport=lambda **kwargs: calls.append(kwargs),
    )

    assert decision.status == "dispatched"
    assert len(calls) == 1
    assert calls[0]["repo"] == "Katsiarynakavaleuskaya/PulsePlate"
    assert calls[0]["workflow_file"] == "experiment-runner-dispatch.yml"
    assert calls[0]["ref"] == "main"


def test_unknown_ambient_repo_does_not_bypass_cross_repo_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "u" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo="PilotOrg/PrivatePilot",
    )
    calls: list[dict[str, Any]] = []

    assert config.github_dispatch is not None
    assert config.github_dispatch.target is not None
    assert config.github_dispatch.target.is_cross_repo is True
    with pytest.raises(bridge.SlackSocketDispatchError):
        bridge.process_payload(
            _event(text="release/private-pilot Validate bounded private pilot dispatch"),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


def test_spoofed_github_repository_does_not_bypass_cross_repo_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    target_repo = "PilotOrg/PrivatePilot"
    monkeypatch.setenv("GITHUB_REPOSITORY", target_repo)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "v" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
        repo=target_repo,
    )
    calls: list[dict[str, Any]] = []

    assert config.github_dispatch is not None
    assert config.github_dispatch.target is not None
    assert config.github_dispatch.target.is_cross_repo is True
    with pytest.raises(bridge.SlackSocketDispatchError):
        bridge.process_payload(
            _event(text="release/private-pilot Validate bounded private pilot dispatch"),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


def test_execute_mode_keeps_dispatched_outcome_when_post_dispatch_ledger_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "m" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
    calls: list[dict[str, Any]] = []

    def fail_ledger_write(**_: Any) -> str:
        raise bridge.SlackSocketAuditError("Experiment operator ledger evidence is unavailable.")

    monkeypatch.setattr(bridge, "_write_operator_ledger_event", fail_ledger_write)

    decision = bridge.process_payload(
        _event(text="release/smoke Validate dispatch despite ledger write race"),
        config,
        dispatch_transport=lambda **kwargs: calls.append(kwargs),
    )
    reply = bridge._format_command_reply(
        bridge.OperatorCommand(
            kind="run-experiment",
            branch_ref="release/smoke",
            hypothesis="Validate dispatch despite ledger write race",
        ),
        config,
        decision=decision,
    )

    assert len(calls) == 1
    assert decision.status == "dispatched"
    assert decision.failure_class is None
    assert decision.operator_ledger_ref is None
    assert decision.operator_ledger_status == "write_failed_after_dispatch"
    assert "Status: `dispatched`" in reply
    assert "operator_ledger_ref=none" in reply
    assert "operator_ledger_status=write_failed_after_dispatch" in reply
    audit = json.loads((audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").read_text())
    assert audit["status"] == "dispatched"
    assert _ledger_records(audit_dir) == []


def test_dispatch_inputs_match_manual_workflow_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    # Ensure this contract test always exercises the dry-run branch and does not
    # depend on ambient LIVE_APPROVAL_SHA256 env state.
    monkeypatch.delenv(LIVE_APPROVAL_SHA256_ENV, raising=False)
    workflow = _load_workflow(DISPATCH_WORKFLOW_PATH)
    triggers = _workflow_on(workflow)
    workflow_inputs = set(triggers["workflow_dispatch"]["inputs"])
    command = bridge.OperatorCommand(
        kind="run-experiment",
        branch_ref="release/smoke",
        hypothesis="Validate bounded Slack operator bridge",
    )
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    dispatch_inputs = bridge._github_dispatch_inputs(command, config=config)
    assert set(dispatch_inputs) <= workflow_inputs
    assert dispatch_inputs["approval_ref"] == "none"


def test_execute_mode_requires_github_auth_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
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
        "run-experiment feature/test cat /home/alice/.ssh/id_rsa",
        "run-experiment feature/test cat /var/log/pulseplate/runner.log",
        "run-experiment feature/test Improve; rm -rf repo",
        "run-experiment feature/test xapp-" + "a" * 24,
        "run-experiment feature/test ghs_header.payload.signature" + "a" * 24,
        "run-experiment feature/test short",
    ],
)
def test_parser_rejects_unsafe_operator_text(text: str) -> None:
    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.parse_operator_command(text)


@pytest.mark.parametrize(
    "branch_ref",
    [
        "refs/pull/1/head",
        "feature/.hidden",
        "feature/trailing.",
        "feature//double",
        "main@{1}",
        "-bad",
        "/bad",
        "feature\\bad",
        "feature%0Abad",
        "feature\nbad",
    ],
)
def test_branch_ref_validation_rejects_unsafe_refs_without_echoing_values(
    branch_ref: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    assert bridge._is_safe_ref(branch_ref) is False
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_BRANCH_REF", branch_ref)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256", "a" * 64)

    assert bridge.main(["--validate-dispatch-inputs"]) == 1
    stdout = capsys.readouterr().out

    assert "Slack live smoke input configuration is invalid" in stdout
    assert branch_ref not in stdout


def test_team_allowlist_rejects_mismatched_workspace_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "g" * 24)
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketCommandError, match="workspace is not allowed"):
        bridge.process_payload(
            _event(team_id="T0DENIED"),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


def test_parser_accepts_bounded_pulseplate_runner_commands() -> None:
    assert bridge.parse_operator_command("help").kind == "help"
    assert bridge.parse_operator_command("status").kind == "status"
    assert bridge.parse_operator_command("mvp-evidence").kind == "mvp-evidence"


@pytest.mark.parametrize("text", ["status now", "mvp-evidence raw", "help please"])
def test_parser_rejects_extra_args_for_read_only_commands(text: str) -> None:
    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.parse_operator_command(text)


def test_parser_rejects_dispatch_through_pulseplate_runner_hint() -> None:
    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.parse_operator_command(
            "run-experiment feature/test Validate runner bypass from display command",
            command_hint="/pulseplate-runner",
        )


@pytest.mark.parametrize(
    ("text", "command_hint"),
    [
        ("help", "/unknown-command"),
        ("run-experiment feature/test Validate unknown hint bypass", "/unknown-command"),
    ],
)
def test_parser_rejects_unknown_non_empty_command_hint(text: str, command_hint: str) -> None:
    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.parse_operator_command(text, command_hint=command_hint)


def test_parser_preserves_direct_no_hint_compatibility() -> None:
    assert bridge.parse_operator_command("help", command_hint=None).kind == "help"
    assert bridge.parse_operator_command("status", command_hint="").kind == "status"


def test_pulseplate_runner_cannot_dispatch_in_execute_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "m" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", "a" * 64)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.process_payload(
            _event(
                command="/pulseplate-runner",
                text="run-experiment feature/test Validate runner bypass from display command",
            ),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


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
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
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


def test_duplicate_event_is_checked_before_global_rate_limit_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)

    bridge.process_payload(_event(), config)

    with pytest.raises(bridge.SlackSocketAuditError, match="already processed"):
        bridge.process_payload(_event(), config)
    assert len(_ledger_records(audit_dir)) == 1


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


def test_invalid_command_does_not_acquire_global_rate_limit_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    rejected = _event(text="run-experiment feature/test bad; rm -rf repo")

    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.process_payload(rejected, config)

    audit_path = audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["status"] == "rejected"
    assert not (audit_dir / bridge.RATE_LIMIT_LOCK_DIR).exists()
    assert (audit_dir / bridge.REJECTED_RATE_LIMIT_LOCK_DIR).exists()
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    ledger_payload = records[0].payload
    assert ledger_payload["status"] == "rejected"
    assert ledger_payload["command_kind"] == "rejected"
    assert ledger_payload["failure_class"] == "command_rejected"
    assert ledger_payload["workflow_file"] == "none"
    assert ledger_payload["workflow_ref"] == "none"
    assert ledger_payload["branch_hash"] == "none"
    assert ledger_payload["hypothesis_hash"] == "none"
    assert ledger_payload["created_pr"] is False
    assert ledger_payload["resolved_review_threads"] is False
    assert ledger_payload["claimed_merge_readiness"] is False
    ledger_text = json.dumps(ledger_payload, sort_keys=True)
    assert "bad; rm" not in ledger_text
    assert "feature/test" not in ledger_text
    assert "C0ALERTS" not in ledger_text
    assert "U0OPERATOR" not in ledger_text


def test_unauthorized_event_does_not_block_later_authorized_operator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)

    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.process_payload(_event(channel="C0DENIED"), config)

    assert not (audit_dir / bridge.RATE_LIMIT_LOCK_DIR).exists()
    assert (audit_dir / bridge.REJECTED_RATE_LIMIT_LOCK_DIR).exists()
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    assert records[0].payload["status"] == "rejected"
    assert records[0].payload["failure_class"] == "command_rejected"
    assert records[0].payload["created_pr"] is False
    assert records[0].payload["resolved_review_threads"] is False

    decision = bridge.process_payload(_event(event_id="Ev0AUTHORIZED2"), config)

    assert decision.status == "dry_run"
    assert (audit_dir / bridge.RATE_LIMIT_LOCK_DIR).exists()
    assert len(_ledger_records(audit_dir)) == 2


def test_rejected_event_flood_is_bounded_by_separate_audit_throttle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)

    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.process_payload(
            _event(event_id="Ev0REJECTED1", text="run-experiment feature/test bad; rm -rf repo"),
            config,
        )
    with pytest.raises(bridge.SlackSocketAuditError, match="rate limit"):
        bridge.process_payload(
            _event(event_id="Ev0REJECTED2", text="run-experiment feature/test bad; rm -rf repo"),
            config,
        )

    first_audit = audit_dir / f"{bridge._sha256_text('Ev0REJECTED1')}.json"
    second_audit = audit_dir / f"{bridge._sha256_text('Ev0REJECTED2')}.json"
    assert json.loads(first_audit.read_text(encoding="utf-8"))["status"] == "rejected"
    assert not second_audit.exists()
    assert not (audit_dir / bridge.RATE_LIMIT_LOCK_DIR).exists()
    assert (audit_dir / bridge.REJECTED_RATE_LIMIT_LOCK_DIR).exists()


def test_recent_audit_rate_limit_blocks_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
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
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    assert records[0].payload["status"] == "failed"
    assert records[0].payload["failure_class"] == "rate_limited"
    assert records[0].payload["dispatch_mode"] == "execute"


def test_atomic_rate_limit_claim_blocks_concurrent_unique_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "e" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
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


def test_duplicate_event_during_rate_limit_does_not_drop_winning_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(dispatch_mode="dry-run", audit_dir=audit_dir)
    event = _event(event_id="Ev0RACE01")
    pause = threading.Event()
    resume = threading.Event()
    observed: dict[str, str] = {}
    errors: dict[str, BaseException] = {}
    original_claim_rate_limit = bridge._claim_rate_limit

    def pause_first_claim(
        claim_config: bridge.BridgeConfig,
        claim_event: bridge.OperatorEvent,
    ) -> None:
        original_claim_rate_limit(claim_config, claim_event)
        if not pause.is_set():
            pause.set()
            assert resume.wait(timeout=5)

    monkeypatch.setattr(bridge, "_claim_rate_limit", pause_first_claim)

    def first_worker() -> None:
        try:
            decision = bridge.process_payload(event, config)
            observed["first"] = decision.status
        except BaseException as exc:  # noqa: BLE001 - collect thread exceptions.
            errors["first"] = exc
            resume.set()

    first_thread = threading.Thread(target=first_worker)
    first_thread.start()
    assert pause.wait(timeout=5)
    with pytest.raises(bridge.SlackSocketAuditError, match="already processed"):
        bridge.process_payload(event, config)
    resume.set()
    first_thread.join(timeout=5)

    assert not first_thread.is_alive()
    assert errors == {}
    assert observed["first"] == "dry_run"
    audit_path = audit_dir / f"{bridge._sha256_text(str(event['envelope_id']))}.json"
    assert json.loads(audit_path.read_text(encoding="utf-8"))["status"] == "dry_run"


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
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
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


def test_rate_limit_claim_recovers_empty_stale_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    lock_dir = audit_dir / bridge.RATE_LIMIT_LOCK_DIR
    lock_dir.mkdir(parents=True)
    temp_path = lock_dir / ".claim.json.leftover.tmp"
    temp_path.write_text("partial", encoding="utf-8")
    old_timestamp = datetime.fromtimestamp(0, tz=timezone.utc).timestamp()
    os.utime(lock_dir, (old_timestamp, old_timestamp))

    bridge._claim_rate_limit(
        config,
        bridge.OperatorEvent(
            event_id="Ev0STALELOCK",
            channel_id="C0ALERTS",
            user_id="U0OPERATOR",
            team_id="T0TEAM",
            text="status",
        ),
    )

    claim = json.loads((lock_dir / "claim.json").read_text(encoding="utf-8"))
    assert claim["event_hash"] == bridge._sha256_text("Ev0STALELOCK")
    assert not temp_path.exists()


def test_rate_limit_claim_keeps_fresh_partial_lock_instead_of_stealing_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    lock_dir = audit_dir / bridge.RATE_LIMIT_LOCK_DIR
    lock_dir.mkdir(parents=True)
    sleeps: list[float] = []
    monkeypatch.setattr(bridge._audit.time, "sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to acquire"):
        bridge._claim_rate_limit(
            config,
            bridge.OperatorEvent(
                event_id="Ev0FRESHPARTIAL",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
        )

    assert lock_dir.exists()
    assert not (lock_dir / "claim.json").exists()
    assert (
        sleeps
        == [bridge._audit.PARTIAL_CLAIM_RETRY_BACKOFF_SECONDS]
        * bridge.RATE_LIMIT_CLAIM_MAX_ATTEMPTS
    )


def test_rate_limit_claim_wraps_lock_creation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    original_mkdir = Path.mkdir

    def fail_lock_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.name == bridge.RATE_LIMIT_LOCK_DIR:
            raise OSError("permission denied")
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_lock_mkdir)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to create"):
        bridge._claim_rate_limit(
            config,
            bridge.OperatorEvent(
                event_id="Ev0LOCKFAIL",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
        )


def test_rate_limit_claim_cleans_partial_lock_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    original_publish = bridge._audit._atomic_publish_json

    def fail_claim_write(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
        if path.name == "claim.json":
            raise OSError("disk full")
        original_publish(path, payload, exclusive=exclusive)

    monkeypatch.setattr(bridge._audit, "_atomic_publish_json", fail_claim_write)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to record"):
        bridge._claim_rate_limit(
            config,
            bridge.OperatorEvent(
                event_id="Ev0PARTIAL",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
        )

    assert not (audit_dir / bridge.RATE_LIMIT_LOCK_DIR).exists()


def test_rejected_rate_limit_claim_cleans_partial_lock_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config(audit_dir=audit_dir)
    original_publish = bridge._audit._atomic_publish_json

    def fail_claim_write(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
        if path.name == "claim.json":
            raise OSError("disk full")
        original_publish(path, payload, exclusive=exclusive)

    monkeypatch.setattr(bridge._audit, "_atomic_publish_json", fail_claim_write)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to record"):
        bridge.process_payload(
            _event(text="run-experiment feature/test bad; rm -rf repo"),
            config,
        )

    assert not (audit_dir / bridge.RATE_LIMIT_LOCK_DIR).exists()
    assert not (audit_dir / bridge.REJECTED_RATE_LIMIT_LOCK_DIR).exists()
    assert not (audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").exists()


def test_malformed_existing_audit_blocks_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    config = _config(dispatch_mode="execute", audit_dir=audit_dir)
    audit_dir.mkdir(parents=True)
    (audit_dir / "bad.json").write_text("not-json", encoding="utf-8")
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketAuditError, match="invalid"):
        bridge.process_payload(
            _event(), config, dispatch_transport=lambda **kwargs: calls.append(kwargs)
        )

    assert calls == []


def test_audit_retention_report_and_cleanup_are_path_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_AUDIT_RETENTION_DAYS", "14")
    audit_dir.mkdir(parents=True)
    old_event = "Ev0OLDRETENTION"
    fresh_event = "Ev0FRESHRETENTION"
    old_path = audit_dir / f"{bridge._sha256_text(old_event)}.json"
    fresh_path = audit_dir / f"{bridge._sha256_text(fresh_event)}.json"
    old_payload = {
        "channel_hash": "a" * 64,
        "command_kind": "status",
        "event_hash": bridge._sha256_text(old_event),
        "provider_type": "slack_socket_mode",
        "status": "dry_run",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "user_hash": "b" * 64,
    }
    fresh_payload = {
        **old_payload,
        "event_hash": bridge._sha256_text(fresh_event),
        "timestamp": bridge._utcnow().isoformat(),
    }
    old_path.write_text(json.dumps(old_payload), encoding="utf-8")
    fresh_path.write_text(json.dumps(fresh_payload), encoding="utf-8")

    assert bridge.main(["--audit-retention", "report", "--audit-dir", str(audit_dir)]) == 0
    report_stdout = capsys.readouterr().out
    report = json.loads(report_stdout)

    assert report == {
        "deleted_count": 0,
        "expired_count": 1,
        "mode": "report",
        "retention_days": 14,
        "status": "pass",
    }
    assert old_path.exists()
    assert fresh_path.exists()
    assert str(audit_dir) not in report_stdout
    assert old_event not in report_stdout
    assert fresh_event not in report_stdout

    assert bridge.main(["--audit-retention", "cleanup", "--audit-dir", str(audit_dir)]) == 0
    cleanup_stdout = capsys.readouterr().out
    cleanup = json.loads(cleanup_stdout)

    assert cleanup["deleted_count"] == 1
    assert cleanup["expired_count"] == 1
    assert cleanup["mode"] == "cleanup"
    assert not old_path.exists()
    assert fresh_path.exists()
    assert str(audit_dir) not in cleanup_stdout


def test_audit_retention_rejects_symlinked_artifact_ancestor(
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

    with pytest.raises(bridge.SlackSocketAuditError, match="symlink"):
        bridge.audit_retention_summary(
            _config_without_rate_limit(
                monkeypatch=monkeypatch,
                audit_dir=experiments / "slack_socket_bridge",
            ),
            cleanup=True,
        )

    assert not (outside / "slack_socket_bridge").exists()


def test_slack_app_manifest_is_socket_mode_and_secret_free() -> None:
    manifest_text = SLACK_MANIFEST_PATH.read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_text)

    assert manifest["display_information"]["name"] == "Experiment Runner"
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert manifest["settings"]["is_hosted"] is False
    assert manifest["settings"]["org_deploy_enabled"] is False
    assert manifest["features"]["bot_user"]["display_name"] == "experiment-runner"
    slash_commands = manifest["features"]["slash_commands"]
    assert slash_commands == [
        {
            "command": "/run-experiment",
            "description": (
                "Request a bounded Experiment Runner dispatch from an allowlisted operator."
            ),
            "usage_hint": "<branch> <hypothesis>",
            "should_escape": False,
        },
        {
            "command": "/pulseplate-runner",
            "description": "Show bounded Experiment Runner status, KPP outcome catalog, and MVP evidence summaries.",
            "usage_hint": "help | status | kpp-status | mvp-evidence",
            "should_escape": False,
        },
    ]
    assert manifest["oauth_config"]["scopes"]["bot"] == ["commands", "chat:write"]
    assert "url" not in slash_commands[0]
    assert "request_url" not in manifest_text
    assert "hooks.slack.com" not in manifest_text
    assert "xapp-" not in manifest_text
    assert "xox" not in manifest_text
    assert "SLACK_APP_TOKEN" not in manifest_text
    assert "SLACK_BOT_TOKEN" not in manifest_text
    assert "/Users/" not in manifest_text
    assert "/tmp/" not in manifest_text
    assert SLACK_IDENTIFIER_RE.search(manifest_text) is None


def test_slack_operator_command_surface_is_not_widened() -> None:
    manifest = yaml.safe_load(SLACK_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert bridge.ALLOWED_COMMANDS == {
        "help",
        "kpp-status",
        "mvp-evidence",
        "run-experiment",
        "status",
    }
    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.parse_operator_command("rejected")
    assert manifest["features"]["slash_commands"] == [
        {
            "command": "/run-experiment",
            "description": (
                "Request a bounded Experiment Runner dispatch from an allowlisted operator."
            ),
            "usage_hint": "<branch> <hypothesis>",
            "should_escape": False,
        },
        {
            "command": "/pulseplate-runner",
            "description": (
                "Show bounded Experiment Runner status, KPP outcome catalog, "
                "and MVP evidence summaries."
            ),
            "usage_hint": "help | status | kpp-status | mvp-evidence",
            "should_escape": False,
        },
    ]


def test_dispatch_workflow_is_manual_only_fixed_contract() -> None:
    workflow = _load_workflow(DISPATCH_WORKFLOW_PATH)
    workflow_text = DISPATCH_WORKFLOW_PATH.read_text(encoding="utf-8")
    triggers = _workflow_on(workflow)

    assert set(triggers) == {"workflow_dispatch"}
    assert "pull_request" not in triggers
    assert "pull_request_target" not in workflow_text
    assert "push" not in triggers
    assert "schedule" not in triggers
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["experiment-runner-dispatch-contract"]
    assert job["timeout-minutes"] == 10
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"approval_ref", "branch_ref", "hypothesis_sha256", "dry_run"}
    assert inputs["dry_run"]["default"] == "true"
    assert inputs["dry_run"]["options"] == ["true", "false"]
    assert inputs["approval_ref"]["default"] == "none"
    assert inputs["approval_ref"]["type"] == "string"
    steps = job["steps"]
    mask_step = next(step for step in steps if step["name"] == "Mask typed dispatch inputs")
    input_step = next(
        step for step in steps if step["name"] == "Validate typed dispatch inputs without raw echo"
    )
    approval_step = next(
        step for step in steps if step["name"] == "Validate live-dispatch approval reference shape"
    )
    summary_step = next(
        step for step in steps if step["name"] == "Record sanitized dispatch contract summary"
    )
    assert steps.index(mask_step) < steps.index(input_step)
    assert '"branch_ref", "hypothesis_sha256", "approval_ref"' in mask_step["run"]
    assert "::add-mask::" in mask_step["run"]
    assert "_escape_workflow_command_value" in mask_step["run"]
    assert 'return value.replace("%", "%25")' in mask_step["run"]
    assert (
        'replace("\\r", "%0D")' in mask_step["run"] or "replace('\\r', '%0D')" in mask_step["run"]
    )
    assert (
        'replace("\\n", "%0A")' in mask_step["run"] or "replace('\\n', '%0A')" in mask_step["run"]
    )
    assert 'print(f"::add-mask::{_escape_workflow_command_value(value)}")' in mask_step["run"]
    assert 'print(f"::add-mask::{value}")' not in mask_step["run"]
    assert "${{ inputs.branch_ref }}" not in mask_step["run"]
    assert "${{ inputs.hypothesis_sha256 }}" not in mask_step["run"]
    assert "${{ inputs.approval_ref }}" not in mask_step["run"]
    assert input_step["env"]["EXPERIMENT_SLACK_SOCKET_BRANCH_REF"] == "${{ inputs.branch_ref }}"
    assert (
        input_step["env"]["EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"]
        == "${{ inputs.hypothesis_sha256 }}"
    )
    assert "--validate-dispatch-inputs" in input_step["run"]
    assert "--validate-smoke-inputs" not in workflow_text
    assert approval_step["if"] == "inputs.dry_run == 'false'"
    assert "--validate-live-approval" in approval_step["run"]
    assert "if" not in summary_step
    assert "GITHUB_STEP_SUMMARY" in summary_step["run"]
    assert 'os.environ["GITHUB_EVENT_PATH"]' in summary_step["run"]
    assert 'os.environ.get("GITHUB_REF", "")' in summary_step["run"]
    assert "refs/heads/main" in summary_step["run"]
    assert 'if workflow_ref_full != "refs/heads/main"' in summary_step["run"]
    assert 'os.environ.get("GITHUB_REF_NAME", "")' not in summary_step["run"]
    assert "Experiment Runner dispatch workflow must run on main." in summary_step["run"]
    assert "hashlib.sha256" in summary_step["run"]
    assert "workflow_file: experiment-runner-dispatch.yml" in summary_step["run"]
    assert 'summary.write(f"- workflow_ref: {workflow_ref}\\n")' in summary_step["run"]
    assert 'summary.write("- workflow_ref: main\\n")' not in summary_step["run"]
    assert "workflow_input_dry_run" in summary_step["run"]
    assert "branch_hash" in summary_step["run"]
    assert "hypothesis_hash" in summary_step["run"]
    assert "approval_hash_prefix" in summary_step["run"]
    assert "bridge_required_not_workflow_proven" in summary_step["run"]
    assert "workflow_live_approval" in summary_step["run"]
    assert 'summary.write("- approval_hash_prefix: none\\n")' in summary_step["run"]
    assert 'if dry_run == "false" and approval_ref != "none"' in summary_step["run"]
    assert "approval_ref[:16]" not in summary_step["run"]
    assert 'approval_ref[:16] if approval_ref != "none"' not in summary_step["run"]
    assert "operator_ledger_status" in summary_step["run"]
    assert "not_written_by_workflow" in summary_step["run"]
    assert "operator_ledger_scope: local_bridge_only" in summary_step["run"]
    assert "local bridge ledger records this event" not in summary_step["run"]
    assert "Slack is not merge readiness" in summary_step["run"]
    assert "SLACK_APP_TOKEN" not in workflow_text
    assert "SLACK_BOT_TOKEN" not in workflow_text
    assert "SLACK_SIGNING_SECRET" not in workflow_text
    assert "pull-requests:" not in workflow_text
    assert "issues:" not in workflow_text
    assert "id-token:" not in workflow_text
    assert "continue-on-error" not in workflow_text
    assert "|| true" not in workflow_text
    assert "gh pr" not in workflow_text
    assert "gh workflow run" not in workflow_text
    assert "repository_dispatch" not in workflow_text
    assert "github.event.inputs.branch_ref" not in workflow_text
    assert "ref: ${{ inputs.branch_ref }}" not in workflow_text


def test_slack_operator_runbook_documents_status_evidence_authority_boundary() -> None:
    runbook = (
        REPO_ROOT / "docs" / "orchestration" / "EXPERIMENT_RUNNER_SLACK_SOCKET_OPERATOR_RUNBOOK.md"
    ).read_text(encoding="utf-8")

    assert "/pulseplate-runner help" in runbook
    assert "/pulseplate-runner status" in runbook
    assert "/pulseplate-runner mvp-evidence" in runbook
    assert "no raw user events" in runbook
    assert "They do not create PRs" in runbook
    assert "prove merge readiness" in runbook
    assert "replace GitHub Actions/current-head truth" in runbook
    assert "`SLACK_SIGNING_SECRET` is therefore not used" in runbook
    assert "Any future HTTP Slack" in runbook
    assert "ingress must add Slack signature verification" in runbook
    assert "Slack App Asset Policy" in runbook
    assert "experiment_runner_logo_slack.png" in runbook
    assert "source, ownership, and allowed use" in runbook
    assert "Local Operator Ledger and Report" in runbook
    assert "artifacts/orchestration/experiments/operator_ledger/" in runbook
    assert "No new Slack command or Slack authority is added" in runbook
    assert "EXPERIMENT_OPERATOR_LEDGER_TASK_PACKET_ID" in runbook
    assert "operator-plane-slack-bridge" in runbook
    assert "dry_run: false" in runbook
    assert "allows `dry_run: false` only when the reviewed approval digest" in runbook
    assert "until a later bounded dispatch" not in runbook
    assert "approval hash prefix" in runbook
    assert "Slack is not merge readiness" in runbook
    assert "dry_run`, `dispatched`, `failed`, and `rejected`" in runbook
    assert "operator_observability" in runbook
    assert "--write-report-set" in runbook
    assert "invalid_local_artifact" in runbook
    assert "Manual live smoke is operator evidence only" in runbook
    assert "not a required CI gate" in runbook
    assert "not merge-readiness proof" in runbook
    assert "not optional when a PR packet" in runbook
    assert "advisory` only limits authority" in runbook
    assert "--activation-readiness-report" in runbook
    assert "Private-Pilot Readiness Evidence" in runbook
    assert "Private-Pilot Activation Evidence" in runbook
    assert "experiment_private_pilot_activation.py" in runbook
    assert "private-pilot-activation-evidence" in runbook
    assert "activation-evidence.json" in runbook
    assert "--activation-evidence-json" in runbook
    assert "--record-activation-evidence" in runbook
    assert "private_pilot_activation_state" in runbook
    assert "private_pilot_last_smoke" in runbook
    assert "private_pilot_next_operator_action" in runbook
    assert "private_pilot_evidence_status" in runbook
    assert "--repo <owner/repo>" in runbook
    assert "GitHub auth" in runbook
    assert "presence/class" in runbook
    assert "exact allowlist match" in runbook
    assert "fixed workflow/ref status" in runbook
    assert "evidence_graph_admission_status=contract_only_not_runtime" in runbook
    assert "Malformed GitHub dispatch config returns a failed" in runbook
    assert "readiness label instead of printing the malformed value" in runbook
    assert "ready_for_manual_live_smoke" in runbook
    assert "blocked_by_missing_secret" in runbook
    assert "blocked_by_allowlist" in runbook
    assert "blocked_by_smoke_input" in runbook
    assert "manual_only" in runbook
    assert "Activation Readiness" in runbook
    assert "`SLACK_APP_TOKEN` must be an `xapp-` app-level Socket Mode" in runbook
    assert "`SLACK_BOT_TOKEN` must be an `xoxb-` bot token" in runbook
    assert "Semantic-Cache Gate Recheck" in runbook
    assert "closed / false / false / true" in runbook
    assert "GraphRAG" in runbook
    assert "semantic-cache implementation" in runbook
    assert "Einstein Arena / HTTPS Ingress Boundary" in runbook
    assert "timestamp freshness" in runbook
    assert "replay protection" in runbook
    assert "redacted audit contract" in runbook
    execute_gate = "EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED=" + "reviewed-dry-run-dispatch"
    assert execute_gate in runbook
    assert "EXPERIMENT_GITHUB_DISPATCH_REPO_ALLOWLIST" in runbook
    assert "GitHub App installation" in runbook
    assert "selected repository" in runbook
    assert "selected repository name" in runbook
    assert "token values or prefixes" in runbook
    assert "report-level evidence" in runbook
    assert "`pull_requests:write`" in runbook
    assert "`contents:write`" in runbook
    assert "`workflows:write`" in runbook
    assert "dispatch repository events" in runbook
    assert "Operators must not put emails, names, phone numbers" in runbook
    assert "SLACK_SIGNING_SECRET=" not in runbook
    assert "hooks.slack.com" not in runbook
    assert SLACK_IDENTIFIER_RE.search(runbook) is None


def test_smoke_workflow_is_manual_only_and_secret_safe() -> None:
    workflow = _load_workflow()
    workflow_text = SMOKE_WORKFLOW_PATH.read_text(encoding="utf-8")
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
        "audit_retention_days",
        "branch_ref",
        "channel_allowlist",
        "dry_run",
        "hypothesis_sha256",
        "team_allowlist",
        "user_allowlist",
    }
    assert inputs["dry_run"]["default"] == "true"
    assert inputs["audit_retention_days"]["default"] == "14"
    steps = job["steps"]
    mask_step = next(step for step in steps if step["name"] == "Mask runtime allowlist inputs")
    presence_step = next(
        step for step in steps if step["name"] == "Validate live Socket Mode prerequisites"
    )
    dry_config_step = next(
        step
        for step in steps
        if step["name"] == "Validate dry-run bridge config without Slack network"
    )
    input_step = next(
        step for step in steps if step["name"] == "Validate manual smoke inputs without raw echo"
    )
    retention_step = next(
        step for step in steps if step["name"] == "Report local Slack audit retention policy"
    )
    dry_evidence_step = next(
        step for step in steps if step["name"] == "Write redacted dry-run activation evidence"
    )
    dry_readiness_step = next(
        step
        for step in steps
        if step["name"] == "Report Socket Mode activation readiness without live secrets"
    )
    live_readiness_step = next(
        step
        for step in steps
        if step["name"] == "Report Socket Mode activation readiness for live smoke"
    )
    runtime_step = next(
        step for step in steps if step["name"] == "Run bounded live Socket Mode smoke"
    )
    live_evidence_step = next(
        step for step in steps if step["name"] == "Write redacted live activation evidence"
    )
    summary_step = next(
        step for step in steps if step["name"] == "Record sanitized live-smoke evidence summary"
    )
    upload_step = next(
        step
        for step in steps
        if step["name"] == "Upload redacted private-pilot activation evidence"
    )
    assert presence_step["env"]["SLACK_APP_TOKEN"] == "${{ secrets.SLACK_APP_TOKEN }}"
    assert presence_step["env"]["SLACK_BOT_TOKEN"] == "${{ secrets.SLACK_BOT_TOKEN }}"
    assert (
        presence_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST"]
        == "${{ inputs.channel_allowlist }}"
    )
    assert (
        presence_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST"]
        == "${{ inputs.user_allowlist }}"
    )
    assert (
        presence_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST"]
        == "${{ inputs.team_allowlist }}"
    )
    assert runtime_step["env"]["SLACK_APP_TOKEN"] == "${{ secrets.SLACK_APP_TOKEN }}"
    assert runtime_step["env"]["SLACK_BOT_TOKEN"] == "${{ secrets.SLACK_BOT_TOKEN }}"
    assert (
        runtime_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST"]
        == "${{ inputs.team_allowlist }}"
    )
    assert input_step["env"]["EXPERIMENT_SLACK_SOCKET_BRANCH_REF"] == "${{ inputs.branch_ref }}"
    assert (
        input_step["env"]["EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"]
        == "${{ inputs.hypothesis_sha256 }}"
    )
    assert dry_readiness_step["if"] == "inputs.dry_run != 'false'"
    assert dry_readiness_step["id"] == "dry_readiness"
    assert live_readiness_step["if"] == "inputs.dry_run == 'false'"
    assert live_readiness_step["id"] == "live_readiness"
    assert dry_config_step["id"] == "bridge_config"
    assert input_step["id"] == "smoke_inputs"
    assert retention_step["id"] == "audit_retention"
    assert dry_evidence_step["if"] == "inputs.dry_run != 'false'"
    assert presence_step["id"] == "live_prerequisites"
    assert runtime_step["id"] == "live_smoke"
    assert live_evidence_step["if"] == "inputs.dry_run == 'false'"
    assert "SLACK_APP_TOKEN" not in dry_readiness_step["env"]
    assert "SLACK_BOT_TOKEN" not in dry_readiness_step["env"]
    assert "EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST" not in dry_readiness_step["env"]
    assert "EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST" not in dry_readiness_step["env"]
    assert "EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST" not in dry_readiness_step["env"]
    assert (
        dry_readiness_step["env"]["EXPERIMENT_SLACK_SOCKET_BRANCH_REF"]
        == "${{ inputs.branch_ref }}"
    )
    assert (
        dry_readiness_step["env"]["EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"]
        == "${{ inputs.hypothesis_sha256 }}"
    )
    assert live_readiness_step["env"]["SLACK_APP_TOKEN"] == "${{ secrets.SLACK_APP_TOKEN }}"
    assert live_readiness_step["env"]["SLACK_BOT_TOKEN"] == "${{ secrets.SLACK_BOT_TOKEN }}"
    assert (
        live_readiness_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST"]
        == "${{ inputs.channel_allowlist }}"
    )
    assert (
        live_readiness_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST"]
        == "${{ inputs.user_allowlist }}"
    )
    assert (
        live_readiness_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST"]
        == "${{ inputs.team_allowlist }}"
    )
    assert (
        live_readiness_step["env"]["EXPERIMENT_SLACK_SOCKET_BRANCH_REF"]
        == "${{ inputs.branch_ref }}"
    )
    assert (
        live_readiness_step["env"]["EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"]
        == "${{ inputs.hypothesis_sha256 }}"
    )
    assert "SLACK_APP_TOKEN" not in dry_evidence_step["env"]
    assert "SLACK_BOT_TOKEN" not in dry_evidence_step["env"]
    assert (
        dry_evidence_step["env"]["EXPERIMENT_SLACK_SOCKET_BRANCH_REF"] == "${{ inputs.branch_ref }}"
    )
    assert (
        dry_evidence_step["env"]["EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"]
        == "${{ inputs.hypothesis_sha256 }}"
    )
    assert live_evidence_step["env"]["SLACK_APP_TOKEN"] == "${{ secrets.SLACK_APP_TOKEN }}"
    assert live_evidence_step["env"]["SLACK_BOT_TOKEN"] == "${{ secrets.SLACK_BOT_TOKEN }}"
    assert (
        live_evidence_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST"]
        == "${{ inputs.channel_allowlist }}"
    )
    assert (
        live_evidence_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST"]
        == "${{ inputs.user_allowlist }}"
    )
    assert (
        live_evidence_step["env"]["EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST"]
        == "${{ inputs.team_allowlist }}"
    )
    assert runtime_step["env"]["EXPERIMENT_SLACK_SOCKET_BRANCH_REF"] == "${{ inputs.branch_ref }}"
    assert (
        runtime_step["env"]["EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"]
        == "${{ inputs.hypothesis_sha256 }}"
    )
    assert "${{ secrets.SLACK_APP_TOKEN }}" in workflow_text
    assert "${{ secrets.SLACK_BOT_TOKEN }}" in workflow_text
    assert "--validate-secret-presence" in workflow_text
    assert "--validate-smoke-inputs" in workflow_text
    assert "--activation-readiness-report" in workflow_text
    assert "--validate-live-smoke" in workflow_text
    assert "build_private_pilot_activation_evidence" in workflow_text
    assert 'dispatch_outcome_class="dry_run_only"' in workflow_text
    assert "dispatch_outcome_class=smoke_recorded" in workflow_text
    assert "dispatch_outcome_class=smoke_failed_safely" in workflow_text
    assert "dispatch_outcome_class=blocked_before_dispatch" in workflow_text
    assert 'dispatch_outcome_class=os.environ["DISPATCH_OUTCOME_CLASS"]' in workflow_text
    assert "json.JSONDecodeError" in workflow_text
    assert "private-pilot-activation-evidence/activation-evidence.json" in workflow_text
    assert "--run-socket" not in workflow_text
    assert "--audit-retention report" in workflow_text
    assert "--slack-app-config-present" not in workflow_text
    assert "--slack-bot-config-present" not in workflow_text
    assert "--channel-allowlist-present" not in workflow_text
    assert "--user-allowlist-present" not in workflow_text
    assert "SLACK_APP_TOKEN=%s" in workflow_text
    assert "SLACK_BOT_TOKEN=%s" in workflow_text
    assert "EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST=%s" in workflow_text
    assert "EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST=%s" in workflow_text
    assert "EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST=%s" in workflow_text
    assert "slack-bolt" not in workflow_text
    assert steps.index(mask_step) < steps.index(presence_step)
    assert steps.index(mask_step) < steps.index(dry_readiness_step)
    assert steps.index(mask_step) < steps.index(live_readiness_step)
    assert steps.index(dry_readiness_step) < steps.index(dry_config_step)
    assert steps.index(live_readiness_step) < steps.index(dry_config_step)
    assert steps.index(dry_readiness_step) < steps.index(input_step)
    assert steps.index(live_readiness_step) < steps.index(input_step)
    assert steps.index(dry_readiness_step) < steps.index(retention_step)
    assert steps.index(live_readiness_step) < steps.index(retention_step)
    assert steps.index(retention_step) < steps.index(dry_evidence_step)
    assert steps.index(runtime_step) < steps.index(live_evidence_step)
    assert steps.index(dry_evidence_step) < steps.index(upload_step)
    assert steps.index(live_evidence_step) < steps.index(upload_step)
    assert steps.index(live_readiness_step) < steps.index(presence_step)
    assert steps.index(mask_step) < steps.index(runtime_step)
    assert steps.index(dry_readiness_step) < steps.index(runtime_step)
    assert steps.index(live_readiness_step) < steps.index(runtime_step)
    for status_step, output_name in (
        (dry_config_step, "config_status"),
        (input_step, "smoke_input_status"),
        (retention_step, "audit_retention_status"),
        (presence_step, "prerequisite_status"),
    ):
        assert "set +e" in status_step["run"]
        assert ">/dev/null 2>&1" in status_step["run"]
        assert f"{output_name}=$?" in status_step["run"]
        assert f"{output_name}=%s" in status_step["run"]
        assert "GITHUB_OUTPUT" in status_step["run"]
    assert ">/dev/null 2>&1" in runtime_step["run"]
    assert "smoke_status=$?" in runtime_step["run"]
    assert "GITHUB_OUTPUT" in runtime_step["run"]
    assert "prerequisite_status" in runtime_step["run"]
    assert "blocked_before_dispatch" in runtime_step["run"]
    assert "dispatch_outcome_class=smoke_failed_safely" in runtime_step["run"]
    assert (
        'initial_readiness_status="${{ steps.live_readiness.outputs.readiness_status }}"'
        in live_evidence_step["run"]
    )
    assert (
        'config_status="${{ steps.bridge_config.outputs.config_status }}"'
        in live_evidence_step["run"]
    )
    assert 'smoke_input_status="${{ steps.smoke_inputs.outputs.smoke_input_status }}"' in (
        live_evidence_step["run"]
    )
    assert (
        'audit_retention_status="${{ steps.audit_retention.outputs.audit_retention_status }}"'
        in live_evidence_step["run"]
    )
    assert (
        'prerequisite_status="${{ steps.live_prerequisites.outputs.prerequisite_status }}"'
        in live_evidence_step["run"]
    )
    assert (
        'smoke_status="${{ steps.live_smoke.outputs.smoke_status }}"' in live_evidence_step["run"]
    )
    assert (
        'dispatch_outcome_class="${{ steps.live_smoke.outputs.dispatch_outcome_class }}"'
        in live_evidence_step["run"]
    )
    assert "DISPATCH_OUTCOME_CLASS" in live_evidence_step["run"]
    assert 'exit "$smoke_status"' in live_evidence_step["run"]
    assert 'exit "$initial_readiness_status"' in live_evidence_step["run"]
    assert "blocked_by_invalid_config" in live_evidence_step["run"]
    assert "blocked_before_dispatch" in live_evidence_step["run"]
    assert (
        'initial_readiness_status="${{ steps.dry_readiness.outputs.readiness_status }}"'
        in dry_evidence_step["run"]
    )
    assert "blocked_before_dispatch" in dry_evidence_step["run"]
    assert 'exit "$initial_readiness_status"' in dry_evidence_step["run"]
    assert "json.JSONDecodeError" in dry_evidence_step["run"]
    for readiness_step in (dry_readiness_step, live_readiness_step):
        assert "render_activation_readiness_summary" in readiness_step["run"]
        assert "GITHUB_STEP_SUMMARY" in readiness_step["run"]
        assert "set +e" in readiness_step["run"]
        assert "readiness_status=$?" in readiness_step["run"]
        assert "readiness_status=%s" in readiness_step["run"]
        assert "GITHUB_OUTPUT" in readiness_step["run"]
        assert 'exit "$readiness_status"' not in readiness_step["run"]
    assert "deterministic_ci_requires_live_slack" in workflow_text
    assert "opened_http_ingress" in workflow_text
    assert "semantic_cache_enabled" in workflow_text
    assert "claimed_merge_readiness" in workflow_text
    assert 'os.environ["GITHUB_EVENT_PATH"]' in mask_step["run"]
    assert (
        '"branch_ref", "channel_allowlist", "user_allowlist", "team_allowlist", '
        '"hypothesis_sha256"' in mask_step["run"]
    )
    assert "::add-mask::" in mask_step["run"]
    assert "_escape_workflow_command_value" in mask_step["run"]
    assert 'return value.replace("%", "%25")' in mask_step["run"]
    assert (
        'replace("\\r", "%0D")' in mask_step["run"] or "replace('\\r', '%0D')" in mask_step["run"]
    )
    assert (
        'replace("\\n", "%0A")' in mask_step["run"] or "replace('\\n', '%0A')" in mask_step["run"]
    )
    assert 'print(f"::add-mask::{_escape_workflow_command_value(value)}")' in mask_step["run"]
    assert 'print(f"::add-mask::{value}")' not in mask_step["run"]
    assert "::add-mask::{value}" not in mask_step["run"]
    assert "${{ inputs.channel_allowlist }}" not in mask_step["run"]
    assert "${{ inputs.user_allowlist }}" not in mask_step["run"]
    assert "${{ inputs.hypothesis_sha256 }}" not in mask_step["run"]
    assert "$GITHUB_STEP_SUMMARY" in summary_step["run"]
    assert "raw tokens, token prefixes, Slack IDs" in summary_step["run"]
    assert upload_step["if"] == "always()"
    assert upload_step["uses"] == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    assert upload_step["with"] == {
        "if-no-files-found": "error",
        "name": "private-pilot-activation-evidence",
        "path": "private-pilot-activation-evidence/activation-evidence.json",
        "retention-days": 14,
    }
    assert "SLACK_SIGNING_SECRET" not in workflow_text
    assert "continue-on-error" not in workflow_text
    assert "|| true" not in workflow_text
    assert "pull-requests:" not in workflow_text
    assert "issues:" not in workflow_text
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text
    assert "repository_dispatch" not in workflow_text


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

    assert not (outside / "slack_socket_bridge").exists()


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


def test_audit_write_wraps_io_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    original_publish = bridge._audit._atomic_publish_json

    def fail_audit_write(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
        if path.name == "audit.json":
            raise OSError("disk full")
        original_publish(path, payload, exclusive=exclusive)

    monkeypatch.setattr(bridge._audit, "_atomic_publish_json", fail_audit_write)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to write"):
        bridge._write_audit(
            path=audit_dir / "audit.json",
            event=bridge.OperatorEvent(
                event_id="Ev0AUDITWRITE",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=_config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir),
            status="dry_run",
        )


def test_audit_exclusive_write_wraps_io_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    original_publish = bridge._audit._atomic_publish_json

    def fail_audit_open(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
        if path.name == "audit.json":
            raise OSError("disk full")
        original_publish(path, payload, exclusive=exclusive)

    monkeypatch.setattr(bridge._audit, "_atomic_publish_json", fail_audit_open)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to write"):
        bridge._write_audit_exclusive(
            path=audit_dir / "audit.json",
            event=bridge.OperatorEvent(
                event_id="Ev0AUDITEXCLUSIVE",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=_config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir),
            status="dry_run",
        )


def test_event_claim_wraps_io_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    original_publish = bridge._audit._atomic_publish_json

    def fail_claim_open(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
        if path.name == "audit.json":
            raise OSError("disk full")
        original_publish(path, payload, exclusive=exclusive)

    monkeypatch.setattr(bridge._audit, "_atomic_publish_json", fail_claim_open)

    with pytest.raises(bridge.SlackSocketAuditError, match="Unable to claim"):
        bridge._claim_event(
            audit_dir / "audit.json",
            event=bridge.OperatorEvent(
                event_id="Ev0CLAIMWRITE",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=_config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir),
        )


def test_event_claim_rejects_parent_traversal_before_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)
    escaped = audit_dir / ".." / "outside" / "audit.json"

    with pytest.raises(bridge.SlackSocketAuditError, match="artifacts/orchestration"):
        bridge._claim_event(
            escaped,
            event=bridge.OperatorEvent(
                event_id="Ev0TRAVERSAL",
                channel_id="C0ALERTS",
                user_id="U0OPERATOR",
                team_id="T0TEAM",
                text="status",
            ),
            command=bridge.OperatorCommand(kind="status"),
            config=config,
        )

    assert not (audit_dir.parent / "outside").exists()


def test_live_approval_sha256_returns_none_for_absent_and_none_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.delenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", raising=False)

    assert bridge._live_approval_sha256() is None

    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", "none")
    assert bridge._live_approval_sha256() is None

    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", "NONE")
    assert bridge._live_approval_sha256() is None


@pytest.mark.parametrize(
    "bad_value",
    [
        "not-a-digest",
        "xoxb-" + "a" * 24,
        "ghp_" + "a" * 24,
        "short",
        "g" * 64,
        "G" * 64 + "!",
        "a" * 63,
        "a" * 65,
        "abc\ndef",
        "abc`def",
        "../etc/passwd",
    ],
)
def test_live_approval_sha256_rejects_malformed_without_echoing(
    bad_value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", bad_value)

    assert bridge.main(["--validate-live-approval"]) == 1
    stdout = capsys.readouterr().out

    assert "FAIL: Slack live-dispatch approval" in stdout
    assert bad_value not in stdout


def test_live_approval_sha256_normalizes_uppercase_to_lowercase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    upper = "ABCDEF" + "0" * 58
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", upper)

    result = bridge._live_approval_sha256()

    assert result is not None
    assert result == upper.lower()
    assert result == "abcdef" + "0" * 58


def test_compute_live_approval_digest_is_deterministic_and_uses_null_separator() -> None:
    digest = bridge._compute_live_approval_digest("feature/test", "Validate bounded execution")
    expected = bridge._sha256_text("feature/test\0Validate bounded execution")
    assert digest == expected
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_validate_live_approval_cli_passes_for_valid_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", "a" * 64)

    assert bridge.main(["--validate-live-approval"]) == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)

    assert payload == {"approval_status": "valid", "status": "pass"}
    assert "a" * 64 not in stdout


def test_execute_mode_with_matching_live_approval_dispatches_dry_run_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "h" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    branch = "feature/live-test"
    hypothesis = "Live dispatch approval gate validation"
    approval = bridge._compute_live_approval_digest(branch, hypothesis)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", approval)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
    calls: list[dict[str, Any]] = []

    decision = bridge.process_payload(
        _event(text=f"{branch} {hypothesis}"),
        config,
        dispatch_transport=lambda **kwargs: calls.append(kwargs),
    )

    assert decision.status == "dispatched"
    assert len(calls) == 1
    assert calls[0]["inputs"]["dry_run"] == "false"
    assert calls[0]["inputs"]["approval_ref"] == approval
    assert calls[0]["inputs"]["branch_ref"] == branch
    assert calls[0]["inputs"]["hypothesis_sha256"] == bridge._sha256_text(hypothesis)
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    assert records[0].payload["status"] == "dispatched"
    assert records[0].payload["dispatch_mode"] == "execute"
    assert records[0].payload["human_review_outcome"] == "approved"
    assert records[0].payload["branch_hash"] == bridge._sha256_text(branch)
    assert records[0].payload["hypothesis_hash"] == bridge._sha256_text(hypothesis)


def test_execute_mode_with_mismatched_live_approval_rejects_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "i" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv(
        "EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256",
        bridge._compute_live_approval_digest("feature/other", "Other hypothesis"),
    )
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketDispatchError):
        bridge.process_payload(
            _event(text="feature/live-test Live dispatch approval gate validation"),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []
    audit = json.loads((audit_dir / f"{bridge._sha256_text('Ev0SLACK01')}.json").read_text())
    assert audit["status"] == "failed"
    assert audit["failure_class"] == "dispatch_failed"
    records = _ledger_records(audit_dir)
    assert len(records) == 1
    assert records[0].payload["status"] == "failed"
    assert records[0].payload["failure_class"] == "dispatch_failed"
    assert records[0].payload["dispatch_mode"] == "execute"
    assert records[0].payload["human_review_outcome"] == "pending"


def test_live_approval_audit_contains_truncated_hash_for_live_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "j" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    branch = "feature/audit-test"
    hypothesis = "Audit hash validation"
    approval = bridge._compute_live_approval_digest(branch, hypothesis)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", approval)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )

    decision = bridge.process_payload(
        _event(text=f"{branch} {hypothesis}"),
        config,
        dispatch_transport=lambda **kwargs: None,
    )

    audit = json.loads(decision.audit_path.read_text())
    assert audit["approval_hash"] == approval[:16]
    assert decision.approval_hash == approval[:16]
    assert decision.public_payload()["approval_hash"] == approval[:16]


def test_dry_run_audit_contains_none_approval_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    decision = bridge.process_payload(_event(), config)

    assert decision.status == "dry_run"
    audit = json.loads(decision.audit_path.read_text())
    assert audit["approval_hash"] == "none"
    assert decision.approval_hash is None
    assert decision.public_payload()["approval_hash"] == "none"


def test_live_dispatch_reply_shows_dry_run_false_and_approval_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "k" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    branch = "feature/reply-test"
    hypothesis = "Reply format validation"
    approval = bridge._compute_live_approval_digest(branch, hypothesis)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", approval)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )

    decision = bridge.process_payload(
        _event(text=f"{branch} {hypothesis}"),
        config,
        dispatch_transport=lambda **kwargs: None,
    )
    command = bridge.OperatorCommand(
        kind="run-experiment",
        branch_ref=branch,
        hypothesis=hypothesis,
    )
    reply = bridge._format_command_reply(command, config, decision=decision)

    assert "workflow_input_dry_run=false" in reply
    assert f"approval_hash={approval[:16]}" in reply
    assert branch not in reply
    assert hypothesis not in reply


def test_non_dispatch_command_does_not_carry_approval_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", "a" * 64)
    config = _config_without_rate_limit(monkeypatch=monkeypatch, audit_dir=audit_dir)

    decision = bridge.process_payload(
        _event(text="help", command="/pulseplate-runner"),
        config,
    )

    assert decision.status == "dry_run"
    assert decision.approval_hash is None
    assert decision.operator_ledger_ref is None
    assert _ledger_records(audit_dir) == []
    audit = json.loads(decision.audit_path.read_text())
    assert audit["approval_hash"] == "none"


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "run-experiment ../main Improve oracle evidence throughput",
        "run-experiment feature/test Improve; rm -rf repo",
        "run-experiment feature/test A=1 should not parse",
        "run-experiment feature/test short",
    ],
)
def test_live_dispatch_path_rejects_unsafe_inputs_via_existing_parser(
    unsafe_text: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_dir = _configure_repo(monkeypatch, tmp_path)
    _configure_env(monkeypatch)
    monkeypatch.setenv("GH_TOKEN", "ghp_" + "m" * 24)
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED", "reviewed-dry-run-dispatch")
    monkeypatch.setenv("EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256", "a" * 64)
    config = _config_without_rate_limit(
        monkeypatch=monkeypatch,
        dispatch_mode="execute",
        audit_dir=audit_dir,
    )
    calls: list[dict[str, Any]] = []

    with pytest.raises(bridge.SlackSocketCommandError):
        bridge.process_payload(
            _event(text=unsafe_text, command=None),
            config,
            dispatch_transport=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []
