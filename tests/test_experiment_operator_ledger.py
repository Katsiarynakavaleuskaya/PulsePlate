"""Tests for the local Experiment Runner operator ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.orchestration import experiment_operator_ledger as ledger


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _event(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "branch_hash": _hash("feature/operator-plane"),
        "channel_hash": _hash("C0SECRET"),
        "claimed_merge_readiness": False,
        "coauthor_decision": "not_required",
        "coauthor_required": False,
        "command_kind": "status",
        "created_pr": False,
        "dispatch_mode": "dry-run",
        "event_hash": _hash("Ev0SECRET"),
        "failure_class": "none",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "human_review_outcome": "pending",
        "hypothesis_hash": _hash("raw hypothesis must not render"),
        "oracle_result_hash": _hash("oracle result"),
        "oracle_result_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
        "policy_version": ledger.POLICY_VERSION,
        "product_runtime_changed": False,
        "provider_type": ledger.PROVIDER_TYPE,
        "redaction_version": ledger.REDACTION_VERSION,
        "resolved_review_threads": False,
        "retention_days": ledger.DEFAULT_RETENTION_DAYS,
        "schema_version": ledger.SCHEMA_VERSION,
        "slack_audit_hash": _hash("slack audit"),
        "slack_audit_ref": ("artifacts/orchestration/experiments/slack_socket_bridge/audit.json"),
        "status": "dry_run",
        "task_packet_id": "792c1fdf2e55",
        "team_hash": _hash("T0SECRET"),
        "user_hash": _hash("U0DENIED"),
        "workflow_file": "experiment-runner-dispatch.yml",
        "workflow_ref": "main",
    }
    payload.update(overrides)
    return payload


def _result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "experiment_id": "operator_report",
        "runner_mode": "candidate_patch",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": ["scripts/orchestration/experiment_operator_ledger.py"],
        "oracle_results": [
            {
                "command": "pytest tests/test_experiment_operator_ledger.py -q",
                "returncode": 0,
                "timed_out": False,
                "truncated": False,
                "stdout": "C0SECRET /Users/alice diff --git must not render",
                "stderr": "xoxb-secretsecretsecret must not render",
                "cwd": "/Users/alice/PulsePlate",
            }
        ],
        "budget_observations": {"wall_clock_seconds": 1},
        "shared_tree_untouched": True,
        "promotion_ready": True,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
        "candidate_patch": "diff --git a/secret b/secret\n+token",
    }
    payload.update(overrides)
    return payload


def _write_result(repo_root: Path, name: str, payload: dict[str, object]) -> Path:
    path = repo_root / ledger.EXPERIMENT_RESULTS_REPO_PREFIX / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _event_for_result(
    repo_root: Path,
    name: str = "operator-plane.json",
    payload: dict[str, object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    result_path = _write_result(repo_root, name, payload or _result())
    return _event(
        oracle_result_ref=f"{ledger.EXPERIMENT_RESULTS_REPO_PREFIX}{name}",
        oracle_result_hash=hashlib.sha256(result_path.read_bytes()).hexdigest(),
        **overrides,
    )


def _assert_no_raw_leak(value: str) -> None:
    forbidden = (
        "C0SECRET",
        "C0SECRETID",
        "U0DENIED",
        "T0SECRET",
        "Ev0SECRET",
        "operator_report",
        "feature/operator-plane",
        "raw hypothesis",
        "/Users/",
        "../outside",
        "xoxb-",
        "ghs_",
        "diff --git",
        "mergeable",
    )
    for sentinel in forbidden:
        assert sentinel not in value


def _slack_audit_path(repo_root: Path) -> Path:
    path = (
        repo_root
        / "artifacts"
        / "orchestration"
        / "experiments"
        / "slack_socket_bridge"
        / "audit.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "event_hash": _hash("Ev0SECRET"),
                "provider_type": "slack_socket_mode",
                "status": "dry_run",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def test_operator_ledger_writes_hash_only_event_and_blocks_duplicate(tmp_path: Path) -> None:
    event = _event()

    path = ledger.write_operator_ledger_event(event, repo_root=tmp_path)
    assert path.relative_to(tmp_path / "artifacts" / "orchestration" / "experiments")
    text = path.read_text(encoding="utf-8")
    record = json.loads(text)

    assert record["idempotency_key"] == path.stem
    assert isinstance(record["content_hash"], str)
    assert len(record["content_hash"]) == 64
    assert isinstance(record["idempotency_key_check"], str)
    assert len(record["idempotency_key_check"]) == 64
    assert record["branch_hash"] == _hash("feature/operator-plane")
    _assert_no_raw_leak(text)

    with pytest.raises(ledger.OperatorLedgerError, match="already exists"):
        ledger.write_operator_ledger_event(event, repo_root=tmp_path)
    assert path.read_text(encoding="utf-8") == text


def test_slack_bridge_operator_ledger_helper_writes_hash_only_event(tmp_path: Path) -> None:
    audit_path = _slack_audit_path(tmp_path)

    path = ledger.write_slack_bridge_operator_ledger_event(
        task_packet_id="packet-pr2",
        command_kind="run-experiment",
        status="dry_run",
        dispatch_mode="dry-run",
        workflow_file="experiment-runner-dispatch.yml",
        workflow_ref="main",
        event_hash=_hash("Ev0SECRET"),
        channel_hash=_hash("C0SECRET"),
        user_hash=_hash("U0DENIED"),
        team_hash=_hash("T0SECRET"),
        branch_hash=_hash("feature/operator-plane"),
        hypothesis_hash=_hash("raw hypothesis must not render"),
        slack_audit_path=audit_path,
        repo_root=tmp_path,
    )
    record = ledger.load_operator_ledger_events(repo_root=tmp_path)[0].payload
    text = path.read_text(encoding="utf-8")

    assert record["status"] == "dry_run"
    assert record["command_kind"] == "run-experiment"
    assert record["dispatch_mode"] == "dry-run"
    assert record["workflow_file"] == "experiment-runner-dispatch.yml"
    assert record["workflow_ref"] == "main"
    assert record["slack_audit_ref"] == (
        "artifacts/orchestration/experiments/slack_socket_bridge/audit.json"
    )
    assert record["slack_audit_hash"] == hashlib.sha256(audit_path.read_bytes()).hexdigest()
    assert record["created_pr"] is False
    assert record["resolved_review_threads"] is False
    assert record["claimed_merge_readiness"] is False
    _assert_no_raw_leak(text)


def test_slack_bridge_operator_ledger_preserves_subsecond_write_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_path = _slack_audit_path(tmp_path)
    timestamps = iter(
        (
            "2026-06-03T12:00:00.000100+00:00",
            "2026-06-03T12:00:00.000900+00:00",
        )
    )
    monkeypatch.setattr(ledger, "_utcnow_iso", lambda: next(timestamps))

    ledger.write_slack_bridge_operator_ledger_event(
        task_packet_id="packet-pr2",
        command_kind="run-experiment",
        status="dry_run",
        dispatch_mode="dry-run",
        workflow_file="experiment-runner-dispatch.yml",
        workflow_ref="main",
        event_hash=_hash("Ev0FIRST"),
        channel_hash=_hash("C0SECRET"),
        user_hash=_hash("U0DENIED"),
        team_hash=_hash("T0SECRET"),
        branch_hash=_hash("feature/operator-plane"),
        hypothesis_hash=_hash("raw hypothesis must not render"),
        slack_audit_path=audit_path,
        repo_root=tmp_path,
    )
    ledger.write_slack_bridge_operator_ledger_event(
        task_packet_id="packet-pr2",
        command_kind="run-experiment",
        status="failed",
        dispatch_mode="dry-run",
        workflow_file="experiment-runner-dispatch.yml",
        workflow_ref="main",
        event_hash=_hash("Ev0SECOND"),
        channel_hash=_hash("C0SECRET"),
        user_hash=_hash("U0DENIED"),
        team_hash=_hash("T0SECRET"),
        branch_hash=_hash("feature/operator-plane"),
        hypothesis_hash=_hash("raw hypothesis must not render"),
        slack_audit_path=audit_path,
        failure_class="rate_limited",
        repo_root=tmp_path,
    )

    records = ledger.load_operator_ledger_events(repo_root=tmp_path)
    summary = ledger.latest_operator_ledger_summary(repo_root=tmp_path)

    assert [record.payload["status"] for record in records] == ["dry_run", "failed"]
    assert records[0].payload["generated_at"].endswith(".000100+00:00")
    assert records[1].payload["generated_at"].endswith(".000900+00:00")
    assert "operator_ledger_status=failed" in summary
    assert "operator_ledger_failure_class=rate_limited" in summary


def test_slack_bridge_operator_ledger_helper_rejects_bad_packet_or_audit_ref(
    tmp_path: Path,
) -> None:
    audit_path = _slack_audit_path(tmp_path)

    with pytest.raises(ledger.OperatorLedgerError, match="task packet"):
        ledger.preflight_slack_bridge_operator_ledger_event(
            task_packet_id="C12345678",
            repo_root=tmp_path,
        )
    outside_audit = tmp_path.parent / f"outside-audit-{tmp_path.name}.json"
    outside_audit.write_text("{}", encoding="utf-8")
    with pytest.raises(ledger.OperatorLedgerError, match="must stay under artifacts"):
        ledger.write_slack_bridge_operator_ledger_event(
            task_packet_id="packet-pr2",
            command_kind="run-experiment",
            status="dry_run",
            dispatch_mode="dry-run",
            workflow_file="experiment-runner-dispatch.yml",
            workflow_ref="main",
            event_hash=_hash("Ev0SECRET"),
            channel_hash=_hash("C0SECRET"),
            user_hash=_hash("U0DENIED"),
            team_hash=_hash("T0SECRET"),
            branch_hash=_hash("feature/operator-plane"),
            hypothesis_hash=_hash("raw hypothesis must not render"),
            slack_audit_path=outside_audit,
            repo_root=tmp_path,
        )


def test_operator_ledger_event_write_keeps_temp_files_out_of_event_store(
    tmp_path: Path,
) -> None:
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    ledger_root = ledger.default_ledger_dir(tmp_path)
    event_entries = sorted((ledger_root / "events").iterdir())
    assert event_entries
    assert all(path.suffix == ".json" for path in event_entries)
    tmp_dir = ledger_root / "tmp"
    assert not tmp_dir.exists() or not list(tmp_dir.iterdir())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("branch_hash", "feature/operator-plane"),
        ("oracle_result_ref", "/Users/alice/result.json"),
        ("oracle_result_ref", "artifacts/orchestration/experiments/results/C0SECRET.json"),
        (
            "oracle_result_ref",
            "artifacts/orchestration/experiments/results/alice@example.com.json",
        ),
        (
            "oracle_result_ref",
            "artifacts/orchestration/experiments/results/ghs_abcd.efgh.ijkl.json",
        ),
        ("oracle_result_ref", "artifacts/orchestration/experiments/results/15551234567.json"),
        (
            "oracle_result_ref",
            "artifacts/orchestration/experiments/results/project/Users/alice.json",
        ),
        (
            "oracle_result_ref",
            "artifacts/orchestration/experiments/results/C:/Users/alice/result.json",
        ),
        (
            "slack_audit_ref",
            "artifacts/orchestration/experiments/slack_socket_bridge/U0DENIED.json",
        ),
        ("task_packet_id", "C12345678"),
        ("task_packet_id", "sk-secretsecret"),
        ("task_packet_id", "ghp_abcdefghijklmnopqrstuvwxyz123456"),
        ("task_packet_id", _hash("approval digest")),
        ("channel_hash", "none"),
        ("coauthor_decision", "required"),
        ("coauthor_required", True),
        ("event_hash", None),
        ("user_hash", "none"),
        ("status", "mergeable"),
        ("created_pr", True),
        ("retention_days", 0),
        ("workflow_file", "none"),
        ("workflow_ref", "none"),
    ],
)
def test_operator_ledger_rejects_unsafe_fields(
    field: str,
    value: object,
) -> None:
    event = _event(**{field: value})

    with pytest.raises(ledger.OperatorLedgerError):
        ledger.normalize_operator_ledger_event(event)


def test_operator_ledger_rejects_extra_raw_fields() -> None:
    event = _event(raw_slack_text="C0SECRET raw hypothesis xoxb-secretsecretsecret")

    with pytest.raises(ledger.OperatorLedgerError, match="schema"):
        ledger.normalize_operator_ledger_event(event)


def test_operator_ledger_rejects_future_timestamps() -> None:
    future = datetime.now(timezone.utc) + timedelta(days=1)

    with pytest.raises(ledger.OperatorLedgerError, match="timestamp"):
        ledger.normalize_operator_ledger_event(_event(generated_at=future.isoformat()))


@pytest.mark.parametrize(
    "event",
    [
        _event(status="dry_run", failure_class="surface_breach"),
        _event(status="dispatched", failure_class="dispatch_failed"),
        _event(status="observed", failure_class="malformed_evidence"),
        _event(status="failed", failure_class="none"),
        _event(status="rejected", failure_class="none"),
        _event(status="dispatched"),
        _event(status="dispatched", command_kind="run-experiment", dispatch_mode="dry-run"),
    ],
)
def test_operator_ledger_rejects_contradictory_status_failure_pairs(
    event: dict[str, object],
) -> None:
    with pytest.raises(ledger.OperatorLedgerError, match="invalid"):
        ledger.normalize_operator_ledger_event(event)


def test_operator_ledger_accepts_failed_status_with_failure_class() -> None:
    record = ledger.normalize_operator_ledger_event(
        _event(status="failed", failure_class="dispatch_failed")
    )

    assert record.payload["status"] == "failed"
    assert record.payload["failure_class"] == "dispatch_failed"


def test_operator_ledger_accepts_execute_dispatch_status() -> None:
    record = ledger.normalize_operator_ledger_event(
        _event(
            command_kind="run-experiment",
            status="dispatched",
            dispatch_mode="execute",
        )
    )

    assert record.payload["status"] == "dispatched"
    assert record.payload["command_kind"] == "run-experiment"
    assert record.payload["dispatch_mode"] == "execute"


def test_operator_ledger_accepts_absent_workflow_target_pair() -> None:
    record = ledger.normalize_operator_ledger_event(
        _event(workflow_file="none", workflow_ref="none")
    )

    assert record.payload["workflow_file"] == "none"
    assert record.payload["workflow_ref"] == "none"


def test_operator_ledger_accepts_date_like_artifact_filenames() -> None:
    record = ledger.normalize_operator_ledger_event(
        _event(
            oracle_result_ref=(
                "artifacts/orchestration/experiments/results/" "operator-summary-2026-06-02.md"
            )
        )
    )

    assert (
        record.payload["oracle_result_ref"]
        == "artifacts/orchestration/experiments/results/operator-summary-2026-06-02.md"
    )


def test_operator_ledger_report_and_status_summary_are_redacted(tmp_path: Path) -> None:
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    summary = ledger.latest_operator_ledger_summary(repo_root=tmp_path)
    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    markdown = ledger.render_operator_observability_markdown(report)
    rendered = "\n".join(summary) + json.dumps(report, sort_keys=True) + markdown

    assert "operator_ledger_status=dry_run" in summary
    assert "operator_ledger_scope=local_only" in summary
    assert "operator_ledger_authority=display_only" in summary
    assert report["event_count"] == 1
    assert report["authority_boundary"] == {
        "claimed_merge_readiness": False,
        "created_pr": False,
        "product_runtime_changed": False,
        "resolved_review_threads": False,
    }
    assert "not PR, review-thread, merge-readiness, or product truth" in markdown
    _assert_no_raw_leak(rendered)


def test_operator_ledger_report_projects_only_safe_result_metadata(tmp_path: Path) -> None:
    ledger.write_operator_ledger_event(
        _event_for_result(
            tmp_path,
            payload=_result(experiment_id="C0SECRETID"),
        ),
        repo_root=tmp_path,
    )

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    markdown = ledger.render_operator_observability_markdown(report)
    html = ledger.render_operator_observability_html(report)
    rendered = json.dumps(report, sort_keys=True) + markdown + html
    metadata = report["latest"]["result_metadata"]

    assert report["by_result_artifact_status"] == {"valid": 1}
    assert metadata == {
        "artifact_status": "valid",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
        "schema_version": "1.0",
        "experiment_id_hash": _hash("C0SECRETID")[:16],
        "runner_mode": "candidate_patch",
        "status": "accepted",
        "failure_class": "none",
        "mutated_paths_count": 1,
        "shared_tree_untouched": True,
        "promotion_ready": True,
        "contribution_kind": "none",
        "coauthor_required": False,
    }
    assert "oracle_results" not in rendered
    assert '"candidate_patch":' not in rendered
    assert "diff --git a/secret" not in rendered
    assert "+token" not in rendered
    assert "budget_observations" not in rendered
    assert "coauthor_reason" not in rendered
    assert "stdout" not in rendered
    assert "stderr" not in rendered
    assert "cwd" not in rendered
    _assert_no_raw_leak(rendered)


def test_operator_ledger_result_metadata_requires_matching_artifact_hash(
    tmp_path: Path,
) -> None:
    _write_result(tmp_path, "operator-plane.json", _result(experiment_id="C0SECRETID"))
    ledger.write_operator_ledger_event(
        _event(oracle_result_hash=_hash("different result bytes")),
        repo_root=tmp_path,
    )

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    rendered = json.dumps(report, sort_keys=True) + ledger.render_operator_observability_html(
        report
    )

    assert report["by_result_artifact_status"] == {"invalid": 1}
    assert report["latest"]["result_metadata"] == {
        "artifact_status": "invalid",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
    }
    _assert_no_raw_leak(rendered)


def test_operator_ledger_report_latest_includes_operator_review_state(
    tmp_path: Path,
) -> None:
    ledger.write_operator_ledger_event(
        _event(
            coauthor_decision="required",
            coauthor_required=True,
            command_kind="run-experiment",
            dispatch_mode="execute",
            human_review_outcome="approved",
            oracle_result_hash="none",
            oracle_result_ref="none",
            status="dispatched",
        ),
        repo_root=tmp_path,
    )

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    markdown = ledger.render_operator_observability_markdown(report)
    html = ledger.render_operator_observability_html(report)

    assert report["latest"]["dispatch_mode"] == "execute"
    assert report["latest"]["coauthor_required"] is True
    assert report["latest"]["coauthor_decision"] == "required"
    assert report["latest"]["human_review_outcome"] == "approved"
    assert "- dispatch_mode: `execute`" in markdown
    assert "coauthor_decision" in html
    assert "human_review_outcome" in html


def test_operator_ledger_report_does_not_count_absent_result_refs(
    tmp_path: Path,
) -> None:
    ledger.write_operator_ledger_event(
        _event(oracle_result_ref="none", oracle_result_hash="none"),
        repo_root=tmp_path,
    )

    report = ledger.build_operator_observability_report(repo_root=tmp_path)

    assert report["by_result_artifact_status"] == {"absent": 1}
    assert report["source_counts"] == {
        "operator_ledger_events": 1,
        "result_artifact_refs": 0,
    }
    assert report["latest"]["result_metadata"] == {
        "artifact_ref": "none",
        "artifact_status": "absent",
    }


def test_operator_ledger_result_metadata_fails_closed_for_malformed_artifact(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / ledger.EXPERIMENT_RESULTS_REPO_PREFIX / "operator-plane.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text("{not-json C0SECRET /Users/alice", encoding="utf-8")
    ledger.write_operator_ledger_event(
        _event(oracle_result_hash=hashlib.sha256(result_path.read_bytes()).hexdigest()),
        repo_root=tmp_path,
    )

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    rendered = json.dumps(report, sort_keys=True) + ledger.render_operator_observability_html(
        report
    )

    assert report["by_result_artifact_status"] == {"invalid": 1}
    assert report["latest"]["result_metadata"] == {
        "artifact_status": "invalid",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
    }
    assert "{not-json" not in rendered
    _assert_no_raw_leak(rendered)


def test_operator_ledger_result_metadata_fails_closed_for_hash_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_path = _write_result(tmp_path, "operator-plane.json", _result())
    ledger.write_operator_ledger_event(
        _event(oracle_result_hash=hashlib.sha256(result_path.read_bytes()).hexdigest()),
        repo_root=tmp_path,
    )

    def fail_hash(_: Path) -> str:
        raise ledger.OperatorLedgerError("hash unavailable")

    monkeypatch.setattr(ledger, "_sha256_file", fail_hash)

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    rendered = json.dumps(report, sort_keys=True) + ledger.render_operator_observability_html(
        report
    )

    assert report["by_result_artifact_status"] == {"invalid": 1}
    assert report["malformed_artifact_counts"] == {
        "invalid_result_artifacts": 1,
        "missing_result_artifacts": 0,
    }
    assert report["latest"]["result_metadata"] == {
        "artifact_status": "invalid",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
    }
    assert "hash unavailable" not in rendered
    _assert_no_raw_leak(rendered)


def test_operator_ledger_result_metadata_fails_closed_for_type_errors(
    tmp_path: Path,
) -> None:
    event = _event_for_result(
        tmp_path,
        payload=_result(
            oracle_results=[
                {
                    "command": "pytest tests/test_experiment_operator_ledger.py -q",
                    "returncode": {"not": "an-int"},
                    "stdout": "C0SECRET /Users/alice diff --git must not render",
                    "stderr": "xoxb-secretsecretsecret must not render",
                    "cwd": "/Users/alice/PulsePlate",
                }
            ]
        ),
    )
    ledger.write_operator_ledger_event(event, repo_root=tmp_path)

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    rendered = json.dumps(report, sort_keys=True) + ledger.render_operator_observability_html(
        report
    )

    assert report["by_result_artifact_status"] == {"invalid": 1}
    assert report["malformed_artifact_counts"] == {
        "invalid_result_artifacts": 1,
        "missing_result_artifacts": 0,
    }
    assert report["latest"]["result_metadata"] == {
        "artifact_status": "invalid",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
    }
    _assert_no_raw_leak(rendered)


def test_operator_ledger_result_metadata_fails_closed_for_symlinked_artifact(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside-result.json"
    outside.write_text(json.dumps(_result()), encoding="utf-8")
    result_path = tmp_path / ledger.EXPERIMENT_RESULTS_REPO_PREFIX / "operator-plane.json"
    result_path.parent.mkdir(parents=True)
    result_path.symlink_to(outside)
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    rendered = json.dumps(report, sort_keys=True) + ledger.render_operator_observability_html(
        report
    )

    assert report["by_result_artifact_status"] == {"invalid": 1}
    assert report["latest"]["result_metadata"] == {
        "artifact_status": "invalid",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
    }
    assert str(outside) not in rendered
    _assert_no_raw_leak(rendered)


def test_operator_ledger_result_metadata_reports_missing_artifact(
    tmp_path: Path,
) -> None:
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    rendered = (
        json.dumps(report, sort_keys=True)
        + ledger.render_operator_observability_markdown(report)
        + ledger.render_operator_observability_html(report)
    )

    assert report["by_result_artifact_status"] == {"missing": 1}
    assert report["latest"]["result_metadata"] == {
        "artifact_status": "missing",
        "artifact_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
    }
    assert "operator-plane.json" in rendered
    _assert_no_raw_leak(rendered)


def test_operator_ledger_result_metadata_fails_closed_for_traversal_ref(
    tmp_path: Path,
) -> None:
    metadata = ledger._safe_result_metadata_from_ref(
        "artifacts/orchestration/experiments/results/../outside.json",
        repo_root=tmp_path,
    )

    assert metadata == {"artifact_status": "invalid", "artifact_ref": "none"}


def test_operator_ledger_html_renderer_escapes_dynamic_values() -> None:
    report = {
        "authority_boundary": {
            "claimed_merge_readiness": False,
            "created_pr": False,
            "product_runtime_changed": False,
            "resolved_review_threads": False,
        },
        "by_command_kind": {"<script>": 1},
        "by_dispatch_mode": {},
        "by_failure_class": {},
        "by_result_artifact_status": {"valid": 1},
        "by_status": {"dry_run": 1},
        "event_count": 1,
        "latest": {
            "branch_hash": "<branch>",
            "command_kind": "status",
            "failure_class": "none",
            "hypothesis_hash": "<hypothesis>",
            "oracle_result_ref": "artifacts/orchestration/experiments/results/operator-plane.json",
            "result_metadata": {
                "artifact_status": "valid",
                "experiment_id_hash": "<img src=x onerror=alert(1)>",
            },
            "coauthor_decision": "not_required",
            "coauthor_required": False,
            "dispatch_mode": "dry-run",
            "human_review_outcome": "pending",
            "status": "dry_run",
            "workflow_file": "none",
            "workflow_ref": "none",
        },
        "policy_version": "<policy>",
        "redaction_version": "<redaction>",
        "report_scope": "local_operator_plane_only",
        "result_artifacts": [],
        "schema_version": ledger.SCHEMA_VERSION,
    }

    html = ledger.render_operator_observability_html(report)

    assert "<script>" not in html
    assert "<branch>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;branch&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_operator_ledger_invalid_local_artifact_summary_is_sanitized(tmp_path: Path) -> None:
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    (event_dir / "bad.json").write_text("{not-json", encoding="utf-8")

    summary = ledger.latest_operator_ledger_summary(repo_root=tmp_path)

    assert summary == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_symlinked_event_file_fails_closed(tmp_path: Path) -> None:
    record = ledger.normalize_operator_ledger_event(_event()).payload
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(record), encoding="utf-8")
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    (event_dir / "linked.json").symlink_to(outside)

    with pytest.raises(ledger.OperatorLedgerError, match="symlinked"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_missing_derived_key_fails_closed(tmp_path: Path) -> None:
    record = dict(ledger.normalize_operator_ledger_event(_event()).payload)
    record.pop("idempotency_key")
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    (event_dir / "missing-key.json").write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ledger.OperatorLedgerError, match="invalid"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_events_path_as_file_fails_closed(tmp_path: Path) -> None:
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.parent.mkdir(parents=True)
    event_dir.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ledger.OperatorLedgerError, match="directory"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_write_rejects_events_path_as_file(tmp_path: Path) -> None:
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.parent.mkdir(parents=True)
    event_dir.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ledger.OperatorLedgerError, match="event directory"):
        ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)


def test_operator_ledger_dir_rejects_nested_event_store(tmp_path: Path) -> None:
    with pytest.raises(ledger.OperatorLedgerError, match="reserved event store"):
        ledger.write_operator_ledger_event(
            _event(),
            ledger_dir=Path("artifacts/orchestration/experiments/operator_ledger/events/custom"),
            repo_root=tmp_path,
        )
    assert not (ledger.default_ledger_dir(tmp_path) / "events" / "custom").exists()


def test_operator_ledger_write_rejects_symlinked_tmp_dir(tmp_path: Path) -> None:
    ledger_root = ledger.default_ledger_dir(tmp_path)
    ledger_root.mkdir(parents=True)
    outside = tmp_path / "outside-tmp"
    outside.mkdir()
    (ledger_root / "tmp").symlink_to(outside)

    with pytest.raises(ledger.OperatorLedgerError, match="directory"):
        ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)
    assert not (ledger_root / "events").exists()
    assert not list(outside.iterdir())


def test_operator_ledger_root_path_as_file_fails_closed(tmp_path: Path) -> None:
    ledger_root = ledger.default_ledger_dir(tmp_path)
    ledger_root.parent.mkdir(parents=True)
    ledger_root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ledger.OperatorLedgerError, match="directory"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_event_filename_must_match_idempotency_key(tmp_path: Path) -> None:
    record = dict(ledger.normalize_operator_ledger_event(_event()).payload)
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    (event_dir / "renamed.json").write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ledger.OperatorLedgerError, match="invalid"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_content_hash_must_match_event_payload(tmp_path: Path) -> None:
    record = dict(ledger.normalize_operator_ledger_event(_event()).payload)
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    record["workflow_ref"] = "none"
    (event_dir / f"{record['idempotency_key']}.json").write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    with pytest.raises(ledger.OperatorLedgerError, match="invalid"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_idempotency_key_check_must_match_payload(
    tmp_path: Path,
) -> None:
    record = dict(ledger.normalize_operator_ledger_event(_event()).payload)
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    tampered_key = "a" * 24
    record["idempotency_key"] = tampered_key
    (event_dir / f"{tampered_key}.json").write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    with pytest.raises(ledger.OperatorLedgerError, match="invalid"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_load_uses_persisted_key_without_rederiving(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written = ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    def _unexpected_idempotency_derivation(payload: dict[str, object]) -> str:
        raise AssertionError("load path must not recompute PBKDF2 idempotency keys")

    monkeypatch.setattr(ledger, "_idempotency_key", _unexpected_idempotency_derivation)

    records = ledger.load_operator_ledger_events(repo_root=tmp_path)

    assert [record.idempotency_key for record in records] == [written.stem]


def test_operator_ledger_ignores_expired_events(tmp_path: Path) -> None:
    ledger.write_operator_ledger_event(
        _event(
            generated_at=datetime(2000, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
            retention_days=1,
        ),
        repo_root=tmp_path,
    )

    assert ledger.load_operator_ledger_events(repo_root=tmp_path) == []
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=absent",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_rejects_non_event_files_in_event_store(tmp_path: Path) -> None:
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)
    (event_dir / "report.md").write_text("not an event", encoding="utf-8")

    with pytest.raises(ledger.OperatorLedgerError, match="invalid"):
        ledger.load_operator_ledger_events(repo_root=tmp_path)
    assert ledger.latest_operator_ledger_summary(repo_root=tmp_path) == (
        "operator_ledger_status=invalid_local_artifact",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def test_operator_ledger_output_path_rejects_traversal_and_symlink(
    tmp_path: Path,
) -> None:
    with pytest.raises(ledger.OperatorLedgerError):
        ledger._validate_output_path(tmp_path / "outside.md", repo_root=tmp_path)
    with pytest.raises(ledger.OperatorLedgerError):
        ledger._validate_output_path(
            Path("artifacts/orchestration/experiments/../outside.md"),
            repo_root=tmp_path,
        )

    artifact_root = tmp_path / "artifacts" / "orchestration" / "experiments"
    artifact_root.mkdir(parents=True)
    target = tmp_path / "outside"
    target.mkdir()
    symlink = artifact_root / "operator_ledger_link"
    symlink.symlink_to(target)

    with pytest.raises(ledger.OperatorLedgerError):
        ledger._validate_output_path(
            Path("artifacts/orchestration/experiments/operator_ledger_link/report.md"),
            repo_root=tmp_path,
        )


def test_operator_ledger_cli_output_rejects_reserved_event_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    event_dir = ledger.default_ledger_dir(tmp_path) / "events"
    event_dir.mkdir(parents=True)

    assert (
        ledger.main(
            [
                "--summary",
                "--output",
                "artifacts/orchestration/experiments/operator_ledger/events/report.json",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "reserved event store" in failure
    assert str(tmp_path) not in failure


def test_operator_ledger_cli_output_rejects_default_event_store_with_custom_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)

    assert (
        ledger.main(
            [
                "--summary",
                "--ledger-dir",
                "artifacts/orchestration/experiments/custom_ledger",
                "--output",
                "artifacts/orchestration/experiments/operator_ledger/events/report.json",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "reserved event store" in failure
    assert str(tmp_path) not in failure
    assert not (
        tmp_path
        / "artifacts"
        / "orchestration"
        / "experiments"
        / "operator_ledger"
        / "events"
        / "report.json"
    ).exists()


def test_operator_ledger_cli_output_rejects_any_future_event_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)

    assert (
        ledger.main(
            [
                "--summary",
                "--ledger-dir",
                "artifacts/orchestration/experiments/custom_a",
                "--output",
                "artifacts/orchestration/experiments/custom_b/events/report.json",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "reserved event store" in failure
    assert str(tmp_path) not in failure
    assert not (
        tmp_path
        / "artifacts"
        / "orchestration"
        / "experiments"
        / "custom_b"
        / "events"
        / "report.json"
    ).exists()


def test_operator_ledger_cli_summary_writes_under_artifacts_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    assert (
        ledger.main(
            [
                "--summary",
                "--format",
                "markdown",
                "--output",
                "artifacts/orchestration/experiments/operator_ledger/report.md",
            ]
        )
        == 0
    )
    report = (
        tmp_path / "artifacts" / "orchestration" / "experiments" / "operator_ledger" / "report.md"
    ).read_text(encoding="utf-8")
    _assert_no_raw_leak(report)

    assert ledger.main(["--summary", "--output", str(tmp_path / "outside.json")]) == 1
    failure = capsys.readouterr().out
    assert "FAIL: Experiment operator ledger output must stay" in failure
    assert str(tmp_path) not in failure


def test_operator_ledger_cli_summary_writes_html_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    ledger.write_operator_ledger_event(_event_for_result(tmp_path), repo_root=tmp_path)

    assert (
        ledger.main(
            [
                "--summary",
                "--format",
                "html",
                "--output",
                "artifacts/orchestration/experiments/operator_ledger/report.html",
            ]
        )
        == 0
    )
    report = (
        tmp_path / "artifacts" / "orchestration" / "experiments" / "operator_ledger" / "report.html"
    ).read_text(encoding="utf-8")

    assert "<!doctype html>" in report
    assert "Latest Result Metadata" in report
    assert "experiment_id_hash" in report
    assert _hash("operator_report")[:16] in report
    assert ">candidate_patch<" in report
    assert "diff --git a/secret" not in report
    assert "+token" not in report
    assert "oracle_results" not in report
    _assert_no_raw_leak(report)


def test_operator_ledger_cli_writes_default_observability_report_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    ledger.write_operator_ledger_event(_event_for_result(tmp_path), repo_root=tmp_path)

    assert ledger.main(["--write-report-set"]) == 0
    stdout = capsys.readouterr().out
    output = json.loads(stdout)

    assert output == {
        "outputs": {
            "html": (
                "artifacts/orchestration/experiments/operator_observability/"
                "operator_observability_report.html"
            ),
            "json": (
                "artifacts/orchestration/experiments/operator_observability/"
                "operator_observability_report.json"
            ),
            "markdown": (
                "artifacts/orchestration/experiments/operator_observability/"
                "operator_observability_report.md"
            ),
        },
        "status": "written",
    }
    report_dir = ledger.default_observability_report_dir(tmp_path)
    rendered = "".join(
        (report_dir / f"operator_observability_report.{suffix}").read_text(encoding="utf-8")
        for suffix in ("json", "md", "html")
    )

    assert "Latest Result Metadata" in rendered
    assert "experiment_id_hash" in rendered
    assert _hash("operator_report")[:16] in rendered
    assert "oracle_results" not in rendered
    assert "diff --git a/secret" not in rendered
    assert str(tmp_path) not in stdout
    _assert_no_raw_leak(stdout + rendered)


def test_operator_ledger_cli_writes_empty_observability_report_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)

    assert ledger.main(["--write-report-set"]) == 0
    stdout = capsys.readouterr().out
    output = json.loads(stdout)
    report_dir = ledger.default_observability_report_dir(tmp_path)
    json_report = json.loads(
        (report_dir / "operator_observability_report.json").read_text(encoding="utf-8")
    )
    markdown = (report_dir / "operator_observability_report.md").read_text(encoding="utf-8")
    html = (report_dir / "operator_observability_report.html").read_text(encoding="utf-8")
    rendered = stdout + json.dumps(json_report, sort_keys=True) + markdown + html

    assert output["status"] == "written"
    assert json_report["event_count"] == 0
    assert json_report["latest"] is None
    assert json_report["activation_readiness"]["activation_state"] == "manual_only"
    assert json_report["activation_readiness"]["manual_live_smoke"] == "operator_evidence_only"
    assert json_report["by_status"] == {}
    assert json_report["by_dispatch_mode"] == {}
    assert json_report["by_failure_class"] == {}
    assert json_report["by_command_kind"] == {}
    assert json_report["by_result_artifact_status"] == {}
    assert json_report["result_artifacts"] == []
    assert json_report["source_counts"] == {
        "operator_ledger_events": 0,
        "result_artifact_refs": 0,
    }
    assert json_report["malformed_artifact_counts"] == {
        "invalid_result_artifacts": 0,
        "missing_result_artifacts": 0,
    }
    assert json_report["redaction_summary"] == {
        "approval_digests_stored": False,
        "health_data_stored": False,
        "local_paths_stored": False,
        "patch_text_stored": False,
        "provider_logs_stored": False,
        "raw_branch_refs_stored": False,
        "raw_hypotheses_stored": False,
        "raw_slack_text_stored": False,
        "slack_ids_stored": False,
        "token_prefixes_stored": False,
    }
    assert "Activation Readiness" in markdown
    assert "socket_mode_activation_state" in rendered
    assert "manual_live_smoke" in rendered
    assert "- Event count: `0`" in markdown
    assert "<p>none</p>" in html
    assert str(tmp_path) not in rendered
    _assert_no_raw_leak(rendered)


@pytest.mark.parametrize(
    "activation_state",
    (
        "ready_for_manual_live_smoke",
        "blocked_by_missing_secret",
        "blocked_by_allowlist",
        "manual_only",
    ),
)
def test_operator_observability_report_renders_activation_readiness_states(
    tmp_path: Path,
    activation_state: str,
) -> None:
    activation_readiness = {
        "activation_state": activation_state,
        "audit_retention_status": "valid",
        "branch_ref_status": "valid",
        "channel_allowlist_status": "present",
        "hypothesis_sha256_status": "valid",
        "manual_live_smoke": "operator_evidence_only",
        "slack_app_token_status": "valid",
        "slack_bot_token_status": "valid",
        "status": "pass",
        "team_allowlist_status": "present",
        "user_allowlist_status": "present",
    }

    report = ledger.build_operator_observability_report(
        repo_root=tmp_path,
        activation_readiness=activation_readiness,
    )
    rendered = (
        json.dumps(report, sort_keys=True)
        + ledger.render_operator_observability_markdown(report)
        + ledger.render_operator_observability_html(report)
    )

    assert report["activation_readiness"]["activation_state"] == activation_state
    assert "socket_mode_activation_state" in rendered
    assert activation_state in rendered
    assert "activation_authority" in rendered
    assert "display_only" in rendered
    assert "operator_evidence_only" in rendered
    assert str(tmp_path) not in rendered
    _assert_no_raw_leak(rendered)


def test_operator_ledger_report_set_is_idempotent_and_preserves_result_artifacts(
    tmp_path: Path,
) -> None:
    result_path = _write_result(tmp_path, "operator-plane.json", _result())
    original_result = result_path.read_bytes()
    ledger.write_operator_ledger_event(
        _event(oracle_result_hash=hashlib.sha256(original_result).hexdigest()),
        repo_root=tmp_path,
    )
    report = ledger.build_operator_observability_report(repo_root=tmp_path)

    first_outputs = ledger.write_operator_observability_report_set(report, repo_root=tmp_path)
    first_rendered = {
        suffix: (
            tmp_path
            / "artifacts"
            / "orchestration"
            / "experiments"
            / "operator_observability"
            / f"operator_observability_report.{suffix}"
        ).read_text(encoding="utf-8")
        for suffix in ("json", "md", "html")
    }
    second_outputs = ledger.write_operator_observability_report_set(report, repo_root=tmp_path)
    second_rendered = {
        suffix: (
            tmp_path
            / "artifacts"
            / "orchestration"
            / "experiments"
            / "operator_observability"
            / f"operator_observability_report.{suffix}"
        ).read_text(encoding="utf-8")
        for suffix in ("json", "md", "html")
    }

    assert first_outputs == second_outputs
    assert first_rendered == second_rendered
    assert result_path.read_bytes() == original_result
    _assert_no_raw_leak("".join(first_rendered.values()))


def test_operator_ledger_cli_report_set_rejects_reserved_event_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    ledger.write_operator_ledger_event(_event_for_result(tmp_path), repo_root=tmp_path)

    assert (
        ledger.main(
            [
                "--write-report-set",
                "--report-dir",
                "artifacts/orchestration/experiments/operator_observability/events",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out

    assert "reserved event store" in failure
    assert str(tmp_path) not in failure
    assert not (
        tmp_path
        / "artifacts"
        / "orchestration"
        / "experiments"
        / "operator_observability"
        / "events"
        / "operator_observability_report.json"
    ).exists()


def test_operator_ledger_cli_report_set_rejects_unsafe_report_dir_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    ledger.write_operator_ledger_event(_event_for_result(tmp_path), repo_root=tmp_path)

    assert (
        ledger.main(
            [
                "--write-report-set",
                "--report-dir",
                "artifacts/orchestration/experiments/C0SECRETID",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out

    assert "artifact reference is invalid" in failure
    assert "C0SECRETID" not in failure
    assert str(tmp_path) not in failure
    assert not (tmp_path / "artifacts" / "orchestration" / "experiments" / "C0SECRETID").exists()


def test_operator_ledger_cli_report_set_rejects_summary_combination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    assert ledger.main(["--write-report-set", "--summary", "--format", "markdown"]) == 1
    failure = capsys.readouterr().out

    assert "cannot combine with summary" in failure
    assert not ledger.default_observability_report_dir(tmp_path).exists()
    assert str(tmp_path) not in failure


def test_operator_ledger_cli_record_invalid_output_does_not_write_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    event_json = tmp_path / "event.json"
    event_json.write_text(json.dumps(_event()), encoding="utf-8")

    assert (
        ledger.main(
            [
                "--record",
                "--event-json",
                str(event_json),
                "--output",
                str(tmp_path / "outside.json"),
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "FAIL: Experiment operator ledger output must stay" in failure
    assert not (ledger.default_ledger_dir(tmp_path) / "events").exists()


def test_operator_ledger_cli_record_output_write_error_does_not_write_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    event_json = tmp_path / "event.json"
    event_json.write_text(json.dumps(_event()), encoding="utf-8")
    blocked_parent = tmp_path / "artifacts" / "orchestration" / "experiments" / "blocked"
    blocked_parent.parent.mkdir(parents=True)
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    assert (
        ledger.main(
            [
                "--record",
                "--event-json",
                str(event_json),
                "--output",
                "artifacts/orchestration/experiments/blocked/report.json",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "FAIL: Unable to write Experiment operator ledger output." in failure
    assert not (ledger.default_ledger_dir(tmp_path) / "events").exists()


def test_operator_ledger_cli_record_directory_output_does_not_write_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    event_json = tmp_path / "event.json"
    event_json.write_text(json.dumps(_event()), encoding="utf-8")
    output_dir = tmp_path / "artifacts" / "orchestration" / "experiments" / "operator_ledger"
    output_dir.mkdir(parents=True)

    assert (
        ledger.main(
            [
                "--record",
                "--event-json",
                str(event_json),
                "--output",
                "artifacts/orchestration/experiments/operator_ledger",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "FAIL: Unable to write Experiment operator ledger output." in failure
    assert not (ledger.default_ledger_dir(tmp_path) / "events").exists()


def test_operator_ledger_cli_output_write_errors_are_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    blocked_parent = tmp_path / "artifacts" / "orchestration" / "experiments" / "blocked"
    blocked_parent.parent.mkdir(parents=True)
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    assert (
        ledger.main(
            [
                "--summary",
                "--output",
                "artifacts/orchestration/experiments/blocked/report.md",
            ]
        )
        == 1
    )
    failure = capsys.readouterr().out
    assert "FAIL: Unable to write Experiment operator ledger output." in failure
    assert str(tmp_path) not in failure


def test_operator_ledger_cli_summary_requires_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)

    assert ledger.main(["--summary", "--format", "json"]) == 1
    failure = capsys.readouterr().out

    assert failure == "FAIL: Experiment operator ledger summary output requires --output.\n"
    _assert_no_raw_leak(failure)


def test_operator_ledger_cli_stdout_fails_closed_on_unsafe_rendered_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        ledger,
        "write_operator_observability_report_set",
        lambda *_, **__: {"json": "`/Users/alice/operator-secret`"},
    )

    assert ledger.main(["--write-report-set"]) == 1
    failure = capsys.readouterr().out

    assert failure == "FAIL: Experiment operator ledger output contains unsafe content.\n"
    _assert_no_raw_leak(failure)


def test_operator_ledger_direct_cli_summary_invocation_is_supported(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    run_id = hashlib.sha256(str(tmp_path).encode("utf-8")).hexdigest()
    artifact_ref = f"artifacts/orchestration/experiments/direct_cli_summary_{run_id}"
    isolated_ledger = f"{artifact_ref}/ledger"
    output_ref = f"{artifact_ref}/summary.json"
    output_path = repo_root / output_ref

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "orchestration" / "experiment_operator_ledger.py"),
                "--summary",
                "--ledger-dir",
                isolated_ledger,
                "--output",
                output_ref,
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout == ""
        assert "ModuleNotFoundError" not in result.stderr
        report = output_path.read_text(encoding="utf-8")
        assert "local_operator_plane_only" in report
        _assert_no_raw_leak(result.stdout + report)
    finally:
        shutil.rmtree(repo_root / artifact_ref, ignore_errors=True)


def test_operator_plane_backlog_epic_documents_boundaries() -> None:
    backlog = Path("docs/roadmap/BACKLOG_LEDGER.md").read_text(encoding="utf-8")
    section = backlog.split(
        '<a id="ledger-p1-experiment-runner-operator-plane-slack-closeout"></a>',
        1,
    )[1].split('<a id="ledger-p1-container-perl-cve-remediation"></a>', 1)[0]

    assert "Experiment Runner Operator Plane & Slack Closeout" in section
    assert "no new Slack command is added in PR-1" in section
    assert "PR-4" in section
    assert "operator_plane_slack" in section
    assert "not a required CI gate" in section
    assert "closed / false / false / true" in section
    assert "GraphRAG" in section
    assert "HTTPS Slack ingress requires a separate reviewed PR" in section
    assert "product AI runtime" in section
    assert "food data" in section
    assert "semantic cache" in section
    assert "review-thread resolution" in section
    assert "merge-readiness authority" in section
    assert "artifacts/orchestration/experiments/" in section
