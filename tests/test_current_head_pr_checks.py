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
        conclusion="FAILURE",
    )
    newer = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-03-12T05:05:00Z",
        details_url="https://example.invalid/newer",
        workflow_name="Docker Image CI",
        conclusion="SUCCESS",
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
            conclusion="",
        )
    ]


def test_cancelled_latest_is_demoted_when_same_workflow_has_newer_activity() -> None:
    cancelled_latest = current_head_checks.CheckEntry(
        name="coverage-pr",
        source_kind="check_run",
        state="failed",
        timestamp="2026-03-12T08:36:42Z",
        details_url="https://example.invalid/cancelled",
        workflow_name="CI",
        conclusion="CANCELLED",
    )
    newer_workflow_activity = current_head_checks.CheckEntry(
        name="Docs Phase1 gates",
        source_kind="check_run",
        state="passed",
        timestamp="2026-03-12T08:40:32Z",
        details_url="https://example.invalid/newer-workflow-activity",
        workflow_name="CI",
        conclusion="SUCCESS",
    )

    latest, superseded = current_head_checks._latest_entries(
        [cancelled_latest, newer_workflow_activity]
    )
    filtered_latest, updated_superseded = (
        current_head_checks._suppress_cancelled_latest_entries_with_newer_workflow_activity(
            [cancelled_latest, newer_workflow_activity],
            latest,
            superseded,
        )
    )

    assert "coverage-pr" not in filtered_latest
    assert cancelled_latest in updated_superseded


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
        current_head_checks, "_fetch_required_check_names", lambda *args: ({"build"}, True)
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
        current_head_checks, "_fetch_required_check_names", lambda *args: ({"build"}, True)
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: current-head check filter failed." in captured.out
    assert "Blocking current-head checks remain pending or failed." in captured.out


def test_main_passes_when_merge_state_is_not_clean_but_required_snapshot_is_clean(
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
        current_head_checks, "_fetch_required_check_names", lambda *args: ({"build"}, True)
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "current-head-checks: passed." in captured.out


def test_main_fails_when_merge_state_is_not_clean_and_required_metadata_is_unavailable(
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
        current_head_checks, "_fetch_required_check_names", lambda *args: (set(), False)
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "GitHub mergeStateStatus=UNSTABLE" in captured.out


def test_main_passes_when_required_check_set_is_empty_but_available(
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
    monkeypatch.setattr(
        current_head_checks, "_fetch_required_check_names", lambda *args: (set(), True)
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Current-head required checks:" in captured.out
    assert "- none" in captured.out


def test_status_context_expected_is_treated_as_pending() -> None:
    entry = current_head_checks._normalize_node(
        {
            "__typename": "StatusContext",
            "context": "CodeRabbit",
            "state": "EXPECTED",
            "createdAt": "2026-03-12T05:02:15Z",
            "targetUrl": "https://example.invalid/pending",
        }
    )

    assert entry.state == "pending"


def test_main_passes_for_draft_pr_without_strict_checks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_metadata",
        lambda *args: (True, "DRAFT", "main", []),
    )
    monkeypatch.setattr(
        current_head_checks, "_fetch_required_check_names", lambda *args: ({"build"}, True)
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1129", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "current-head-checks: PR is draft; skipping strict checks." in captured.out


def test_main_fails_when_token_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "")

    exit_code = current_head_checks.main(
        ["--pr-number", "1129", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "GH_TOKEN or GITHUB_TOKEN is required" in captured.out


def test_main_fails_when_github_metadata_query_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")

    def raise_http_error(*args, **kwargs):
        raise current_head_checks.urllib.error.HTTPError(
            url="https://api.github.com/graphql",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(current_head_checks, "_fetch_pr_metadata", raise_http_error)

    exit_code = current_head_checks.main(
        ["--pr-number", "1129", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: failed to query GitHub check state: HTTP 503" in captured.out


def test_main_uses_merge_state_only_when_required_check_metadata_is_unavailable(
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
                    "name": "optional-e2e",
                    "status": "COMPLETED",
                    "conclusion": "FAILURE",
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": "2026-03-12T05:09:03Z",
                    "detailsUrl": "https://example.invalid/failed-optional",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Optional CI"}}},
                }
            ],
        ),
    )
    monkeypatch.setattr(
        current_head_checks, "_fetch_required_check_names", lambda *args: (set(), False)
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1129", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Required check metadata unavailable" in captured.out
    assert "Current-head advisory checks:" in captured.out
    assert "- optional-e2e: failed [Optional CI]" in captured.out
