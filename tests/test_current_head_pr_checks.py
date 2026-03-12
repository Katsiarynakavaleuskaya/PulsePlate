from __future__ import annotations

import pytest

from scripts.ci import check_current_head_pr_checks as current_head_checks


def test_latest_entries_prefers_newest_duplicate_and_marks_older_superseded() -> None:
    older = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="failed",
        timestamp="2026-03-12T04:48:16Z",
        details_url="https://example.invalid/older",
        workflow_name="Docker Image CI",
    )
    newer = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-03-12T05:05:00Z",
        details_url="https://example.invalid/newer",
        workflow_name="Docker Image CI",
    )

    latest, superseded = current_head_checks._latest_entries([newer, older])

    assert latest["build"] == newer
    assert superseded == [older]


def test_required_snapshot_adds_pending_placeholder_for_missing_required_check() -> None:
    snapshot = current_head_checks._required_snapshot(
        latest_entries={},
        required_names={"Merge readiness gate"},
    )

    assert snapshot == [
        current_head_checks.CheckEntry(
            name="Merge readiness gate",
            source_kind="missing",
            state="pending",
            timestamp="",
            details_url="",
            workflow_name="",
        )
    ]


def test_main_passes_when_latest_current_head_is_clean_and_old_failure_is_superseded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_metadata",
        lambda *args: (
            False,
            "CLEAN",
            "main",
            [
                {
                    "__typename": "CheckRun",
                    "name": "build",
                    "status": "COMPLETED",
                    "conclusion": "FAILURE",
                    "startedAt": "2026-03-12T04:48:16Z",
                    "completedAt": "2026-03-12T04:48:49Z",
                    "detailsUrl": "https://example.invalid/failed",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Image CI"}}},
                },
                {
                    "__typename": "CheckRun",
                    "name": "build",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": "2026-03-12T05:09:03Z",
                    "detailsUrl": "https://example.invalid/passed",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Image CI"}}},
                },
            ],
        ),
    )
    monkeypatch.setattr(
        current_head_checks, "_fetch_required_check_names", lambda *args: {"build"}
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Current-head required checks:" in captured.out
    assert "Superseded non-blocking checks:" in captured.out
    assert "current-head-checks: passed." in captured.out


def test_main_fails_when_latest_required_check_is_pending(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_metadata",
        lambda *args: (
            False,
            "UNSTABLE",
            "main",
            [
                {
                    "__typename": "CheckRun",
                    "name": "build",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Image CI"}}},
                }
            ],
        ),
    )
    monkeypatch.setattr(
        current_head_checks, "_fetch_required_check_names", lambda *args: {"build"}
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: current-head check filter failed." in captured.out
    assert "Blocking current-head checks remain pending or failed." in captured.out


def test_main_fails_when_merge_state_is_not_clean_even_if_latest_snapshot_passes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_metadata",
        lambda *args: (
            False,
            "UNSTABLE",
            "main",
            [
                {
                    "__typename": "CheckRun",
                    "name": "build",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": "2026-03-12T05:09:03Z",
                    "detailsUrl": "https://example.invalid/passed",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Image CI"}}},
                }
            ],
        ),
    )
    monkeypatch.setattr(
        current_head_checks, "_fetch_required_check_names", lambda *args: {"build"}
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "GitHub mergeStateStatus=UNSTABLE" in captured.out


def test_main_uses_all_latest_checks_when_required_set_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_metadata",
        lambda *args: (
            False,
            "CLEAN",
            "main",
            [
                {
                    "__typename": "StatusContext",
                    "context": "CodeRabbit",
                    "state": "SUCCESS",
                    "createdAt": "2026-03-12T05:02:15Z",
                    "targetUrl": "",
                }
            ],
        ),
    )
    monkeypatch.setattr(current_head_checks, "_fetch_required_check_names", lambda *args: set())

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "- CodeRabbit: passed" in captured.out
