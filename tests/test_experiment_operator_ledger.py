"""Tests for the local Experiment Runner operator ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

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
        "generated_at": datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc).isoformat(),
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


def _assert_no_raw_leak(value: str) -> None:
    forbidden = (
        "C0SECRET",
        "U0DENIED",
        "T0SECRET",
        "Ev0SECRET",
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


def test_operator_ledger_writes_hash_only_event_and_blocks_duplicate(tmp_path: Path) -> None:
    event = _event()

    path = ledger.write_operator_ledger_event(event, repo_root=tmp_path)
    assert path.relative_to(tmp_path / "artifacts" / "orchestration" / "experiments")
    text = path.read_text(encoding="utf-8")
    record = json.loads(text)

    assert record["idempotency_key"] == path.stem
    assert record["branch_hash"] == _hash("feature/operator-plane")
    _assert_no_raw_leak(text)

    with pytest.raises(ledger.OperatorLedgerError, match="already exists"):
        ledger.write_operator_ledger_event(event, repo_root=tmp_path)
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("branch_hash", "feature/operator-plane"),
        ("oracle_result_ref", "/Users/alice/result.json"),
        ("status", "mergeable"),
        ("created_pr", True),
        ("retention_days", 0),
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


def test_operator_ledger_report_and_status_summary_are_redacted(tmp_path: Path) -> None:
    ledger.write_operator_ledger_event(_event(), repo_root=tmp_path)

    summary = ledger.latest_operator_ledger_summary(repo_root=tmp_path)
    report = ledger.build_operator_observability_report(repo_root=tmp_path)
    markdown = ledger.render_operator_observability_markdown(report)
    rendered = "\n".join(summary) + json.dumps(report, sort_keys=True) + markdown

    assert "operator_ledger_status=dry_run" in summary
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


def test_operator_plane_backlog_epic_documents_boundaries() -> None:
    backlog = Path("docs/roadmap/BACKLOG_LEDGER.md").read_text(encoding="utf-8")
    section = backlog.split(
        '<a id="ledger-p1-experiment-runner-operator-plane-slack-closeout"></a>',
        1,
    )[1].split('<a id="ledger-p1-container-perl-cve-remediation"></a>', 1)[0]

    assert "Experiment Runner Operator Plane & Slack Closeout" in section
    assert "no new Slack command is added in PR-1" in section
    assert "product AI runtime" in section
    assert "food data" in section
    assert "semantic cache" in section
    assert "review-thread resolution" in section
    assert "merge-readiness authority" in section
    assert "artifacts/orchestration/experiments/" in section
