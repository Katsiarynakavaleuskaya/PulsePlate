from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.ci import check_current_head_pr_checks as current_head_checks

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_FALLBACK_JOB_IDS = {
    "changes",
    "pr_scope_guard",
    "trivy_ignore_policy_expiry",
    "jwt_fastlane_unblock_guard",
    "pygments_exception_guard",
    "docs_phase1_gates",
    "pr_body_phase2_gates",
    "merge_readiness_gate",
    "private_python_proxy_health",
    "lint",
    "security",
    "openapi-sync",
    "test-pr",
    "test-main",
    "coverage-pr",
    "diff-coverage",
}


@pytest.fixture(autouse=True)
def _default_changed_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(current_head_checks, "_fetch_pr_changed_paths", lambda *args: set())


def _load_ci_workflow_jobs() -> dict[str, dict[str, object]]:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    return jobs


def _job_display_names(job_id: str, definition: dict[str, object]) -> set[str]:
    name = str(definition.get("name") or job_id)
    matrix = (definition.get("strategy") or {}).get("matrix") or {}
    python_versions = matrix.get("python-version")
    if job_id == "test-pr" and python_versions == ["3.13"]:
        return {f"{name} (3.13)"}
    matrix_include = matrix.get("include")
    if job_id == "test-main" and isinstance(matrix_include, list):
        check_names = {
            f"{name} ({entry.get('python-version')}, {entry.get('timeout-minutes')})"
            for entry in matrix_include
            if isinstance(entry, dict)
            and entry.get("python-version")
            and entry.get("timeout-minutes")
        }
        return set(sorted(check_names))
    return {name}


def test_fallback_ci_allowlist_matches_canonical_pr_workflow_jobs() -> None:
    jobs = _load_ci_workflow_jobs()
    expected_display_names = set()
    for job_id in CANONICAL_FALLBACK_JOB_IDS:
        expected_display_names.update(_job_display_names(job_id, jobs[job_id]))

    assert current_head_checks.CANONICAL_FALLBACK_CI_CHECK_NAMES == expected_display_names
    assert "test-feature" not in CANONICAL_FALLBACK_JOB_IDS


@pytest.mark.parametrize(
    ("entry", "changed_paths", "expected"),
    [
        (
            current_head_checks.CheckEntry(
                name="lint",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/ci-pending",
                workflow_name="CI",
                conclusion="",
            ),
            set(),
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="coverage-pr",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/ci-failed",
                workflow_name="CI",
                conclusion="FAILURE",
            ),
            set(),
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="security-scan",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-pending",
                workflow_name="Docker Build and Push",
                conclusion="",
            ),
            set(),
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="optional-e2e",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/optional-failed",
                workflow_name="Optional CI",
                conclusion="FAILURE",
            ),
            set(),
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="CI",
                source_kind="status_context",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/status-context",
                workflow_name="",
                conclusion="",
            ),
            set(),
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="CodeRabbit",
                source_kind="status_context",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/coderabbit",
                workflow_name="",
                conclusion="",
            ),
            set(),
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="lint",
                source_kind="check_run",
                state="passed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/ci-passed",
                workflow_name="CI",
                conclusion="SUCCESS",
            ),
            set(),
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="lint",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/lint-other-workflow",
                workflow_name="Docker Build and Push",
                conclusion="",
            ),
            set(),
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="iOS unit tests (xcodebuild)",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/ios-ci",
                workflow_name="CI",
                conclusion="",
            ),
            {"ios/PulsePlate/App.swift"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="iOS unit tests (xcodebuild)",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/ios-ci-workflow",
                workflow_name="CI",
                conclusion="",
            ),
            {".github/workflows/ci.yml"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="iOS unit tests (xcodebuild)",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/ios-action",
                workflow_name="CI",
                conclusion="",
            ),
            {".github/actions/python-setup/action.yml"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="Greenlight preflight (report-only)",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/greenlight",
                workflow_name="Greenlight iOS Preflight",
                conclusion="FAILURE",
            ),
            {"ios/PulsePlate/App.swift"},
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="build-and-test",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/frontend",
                workflow_name="Frontend CI",
                conclusion="",
            ),
            {".nvmrc"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="axe smoke",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/accessibility",
                workflow_name="Accessibility Tests",
                conclusion="",
            ),
            {".github/workflows/accessibility.yml"},
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="test-main (3.11, 60)",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/test-main",
                workflow_name="CI",
                conclusion="FAILURE",
            ),
            {".github/workflows/ci.yml"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="security-scan",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-runtime",
                workflow_name="Docker Build and Push",
                conclusion="FAILURE",
            ),
            {"requirements-docker-runtime.txt"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="security-scan",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-trivy-policy",
                workflow_name="Docker Build and Push",
                conclusion="FAILURE",
            ),
            {"trivy/ignore-policy.rego"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="security-scan",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-trivyignore",
                workflow_name="Docker Build and Push",
                conclusion="FAILURE",
            ),
            {".trivyignore"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="build",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/dockerignore",
                workflow_name="Docker Build and Push",
                conclusion="",
            ),
            {".dockerignore"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="build",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-startup-guard",
                workflow_name="Docker Build and Push",
                conclusion="",
            ),
            {"scripts/ci/check_python_startup_hooks.py"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="build",
                source_kind="check_run",
                state="pending",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-helper",
                workflow_name="Docker Build and Push",
                conclusion="",
            ),
            {"scripts/ci/check_docker_runtime_dependency_surface.py"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="build",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-telemetry-budget",
                workflow_name="Docker Build and Push",
                conclusion="FAILURE",
            ),
            {"docs/telemetry/docker_image_budget.production.json"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="publish",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/docker-publish-skipped",
                workflow_name="Docker Build and Push",
                conclusion="SKIPPED",
            ),
            {"scripts/ci/emergency_python_wheels.json"},
            False,
        ),
    ],
)
def test_is_blocking_fallback_advisory(
    entry: current_head_checks.CheckEntry, changed_paths: set[str], expected: bool
) -> None:
    assert current_head_checks._is_blocking_fallback_advisory(entry, changed_paths) is expected


def test_changed_paths_from_pr_file_includes_previous_filename_for_renames() -> None:
    assert current_head_checks._changed_paths_from_pr_file(
        {
            "filename": "docs/requirements-docker-runtime.txt",
            "previous_filename": "requirements-docker-runtime.txt",
        }
    ) == {
        "docs/requirements-docker-runtime.txt",
        "requirements-docker-runtime.txt",
    }


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


def test_stale_latest_entry_is_demoted_when_same_workflow_has_newer_activity() -> None:
    stale_latest = current_head_checks.CheckEntry(
        name="coverage-pr",
        source_kind="check_run",
        state="failed",
        timestamp="2026-03-12T08:36:42Z",
        details_url="https://example.invalid/cancelled",
        workflow_name="CI",
        conclusion="FAILURE",
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
        [stale_latest, newer_workflow_activity]
    )
    filtered_latest, updated_superseded = (
        current_head_checks._suppress_stale_latest_entries_with_newer_workflow_activity(
            [stale_latest, newer_workflow_activity],
            latest,
            superseded,
        )
    )

    assert "coverage-pr" not in filtered_latest
    assert stale_latest in updated_superseded


def test_same_timestamp_does_not_demote_latest_entry_on_details_url_only() -> None:
    candidate_latest = current_head_checks.CheckEntry(
        name="coverage-pr",
        source_kind="check_run",
        state="failed",
        timestamp="2026-03-12T08:36:42Z",
        details_url="https://example.invalid/current-candidate",
        workflow_name="CI",
        conclusion="FAILURE",
    )
    same_timestamp_other_job = current_head_checks.CheckEntry(
        name="Docs Phase1 gates",
        source_kind="check_run",
        state="passed",
        timestamp="2026-03-12T08:36:42Z",
        details_url="https://example.invalid/other-job",
        workflow_name="CI",
        conclusion="SUCCESS",
    )

    latest, superseded = current_head_checks._latest_entries(
        [candidate_latest, same_timestamp_other_job]
    )
    filtered_latest, updated_superseded = (
        current_head_checks._suppress_stale_latest_entries_with_newer_workflow_activity(
            [candidate_latest, same_timestamp_other_job],
            latest,
            superseded,
        )
    )

    assert filtered_latest["coverage-pr"] == candidate_latest
    assert candidate_latest not in updated_superseded


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


def test_main_passes_when_merge_state_is_not_clean_but_advisory_snapshot_is_clean(
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
    assert exit_code == 0
    assert "NOTE: GitHub mergeStateStatus=UNSTABLE is stale/non-blocking" in captured.out
    assert "no fallback-blocking current-head checks are pending or failed" in captured.out


def test_main_fails_when_security_scan_is_pending_in_fallback_mode(
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
                    "name": "security-scan",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending-security-scan",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Build and Push"}}},
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
    assert "Required check metadata unavailable" in captured.out
    assert "Current-head blocking fallback checks:" in captured.out
    assert "- security-scan: pending [Docker Build and Push]" in captured.out
    assert "Blocking fallback current-head checks remain pending or failed." in captured.out


def test_main_fails_when_merge_state_is_not_clean_and_attached_specialized_check_is_pending(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks, "_fetch_pr_changed_paths", lambda *args: {"Dockerfile"}
    )
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
                    "name": "security-scan",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending-security-scan",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Build and Push"}}},
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
    assert "Current-head blocking fallback checks:" in captured.out
    assert "- security-scan: pending [Docker Build and Push]" in captured.out


def test_main_passes_when_unattached_specialized_ci_job_is_pending_in_fallback_mode(
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
                    "name": "iOS unit tests (xcodebuild)",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending-ios-unit",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "CI"}}},
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
    assert exit_code == 0
    assert "- iOS unit tests (xcodebuild): pending [CI]" in captured.out
    assert "Current-head advisory checks:" in captured.out
    assert "current-head-checks: passed." in captured.out


def test_main_fails_when_attached_ios_ci_job_is_pending_in_fallback_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_changed_paths",
        lambda *args: {"ios/PulsePlate/App.swift"},
    )
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
                    "name": "iOS unit tests (xcodebuild)",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending-ios-unit",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "CI"}}},
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
    assert "- iOS unit tests (xcodebuild): pending [CI]" in captured.out
    assert "Current-head blocking fallback checks:" in captured.out


def test_main_keeps_greenlight_report_only_job_advisory_in_fallback_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_pr_changed_paths",
        lambda *args: {"ios/PulsePlate/App.swift"},
    )
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
                    "name": "Greenlight preflight (report-only)",
                    "status": "COMPLETED",
                    "conclusion": "FAILURE",
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": "2026-03-12T05:09:03Z",
                    "detailsUrl": "https://example.invalid/greenlight-failed",
                    "checkSuite": {
                        "workflowRun": {"workflow": {"name": "Greenlight iOS Preflight"}}
                    },
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
    assert exit_code == 0
    assert "- Greenlight preflight (report-only): failed [Greenlight iOS Preflight]" in captured.out
    assert "Current-head advisory checks:" in captured.out


def test_main_fails_when_merge_state_is_not_clean_and_canonical_fallback_check_is_pending(
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
                    "name": "Docs Phase1 gates",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending-ci-docs",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "CI"}}},
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
    assert "- Docs Phase1 gates: pending [CI]" in captured.out
    assert "Blocking fallback current-head checks remain pending or failed." in captured.out


def test_main_fails_when_merge_state_is_clean_and_canonical_fallback_check_is_pending(
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
                    "name": "Docs Phase1 gates",
                    "status": "IN_PROGRESS",
                    "conclusion": None,
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": None,
                    "detailsUrl": "https://example.invalid/pending-ci-docs-clean",
                    "checkSuite": {"workflowRun": {"workflow": {"name": "CI"}}},
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
    assert "GitHub mergeStateStatus=CLEAN" not in captured.out
    assert "- Docs Phase1 gates: pending [CI]" in captured.out
    assert "Blocking fallback current-head checks remain pending or failed." in captured.out


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


def test_main_does_not_fetch_changed_paths_when_required_metadata_is_available(
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

    def fail_if_called(*args: object) -> set[str]:
        raise AssertionError("changed paths should be fetched only in fallback mode")

    monkeypatch.setattr(current_head_checks, "_fetch_pr_changed_paths", fail_if_called)

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "current-head-checks: passed." in captured.out


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


def test_skipped_canonical_check_run_is_failed_for_required_and_fallback_gates() -> None:
    entry = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "lint",
            "status": "COMPLETED",
            "conclusion": "SKIPPED",
            "startedAt": "2026-06-29T05:05:00Z",
            "completedAt": "2026-06-29T05:05:30Z",
            "detailsUrl": "https://example.invalid/skipped",
            "checkSuite": {"workflowRun": {"workflow": {"name": "CI"}}},
        }
    )

    assert entry.state == "failed"
    assert current_head_checks._is_blocking_fallback_advisory(entry, set()) is True


def test_skipped_docker_publish_is_non_blocking_release_only_fallback() -> None:
    entry = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "publish",
            "status": "COMPLETED",
            "conclusion": "SKIPPED",
            "startedAt": "2026-06-29T19:12:16Z",
            "completedAt": "2026-06-29T19:12:16Z",
            "detailsUrl": "https://example.invalid/publish-skipped",
            "checkSuite": {"workflowRun": {"workflow": {"name": "Docker Build and Push"}}},
        }
    )

    assert entry.state == "failed"
    assert current_head_checks._is_blocking_fallback_advisory(entry, {"constraints.txt"}) is False
    assert (
        current_head_checks._format_entry(entry)
        == "- publish: skipped [Docker Build and Push] -> https://example.invalid/publish-skipped"
    )


def test_failed_docker_publish_still_blocks_attached_docker_fallback_surface() -> None:
    entry = current_head_checks.CheckEntry(
        name="publish",
        source_kind="check_run",
        state="failed",
        timestamp="2026-06-29T19:12:16Z",
        details_url="https://example.invalid/publish-failed",
        workflow_name="Docker Build and Push",
        conclusion="FAILURE",
    )

    assert current_head_checks._is_blocking_fallback_advisory(entry, {"constraints.txt"}) is True


def test_private_python_proxy_health_blocks_fallback_mode() -> None:
    entry = current_head_checks.CheckEntry(
        name="Private Python proxy health",
        source_kind="check_run",
        state="failed",
        timestamp="2026-06-29T05:05:30Z",
        details_url="https://example.invalid/proxy-health",
        workflow_name="CI",
        conclusion="FAILURE",
    )

    assert current_head_checks._is_blocking_fallback_advisory(entry, set()) is True


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


def test_main_passes_when_required_check_metadata_is_unavailable_and_optional_lane_fails(
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
    assert "current-head-checks: passed." in captured.out
