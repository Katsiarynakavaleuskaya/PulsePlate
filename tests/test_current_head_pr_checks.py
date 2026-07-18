from __future__ import annotations

import json
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
                name="caddy-contract",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/caddy-skipped-unattached",
                workflow_name="Frontend CI",
                conclusion="SKIPPED",
            ),
            {"constraints.txt"},
            False,
        ),
        (
            current_head_checks.CheckEntry(
                name="caddy-contract",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/caddy-skipped-attached",
                workflow_name="Frontend CI",
                conclusion="SKIPPED",
            ),
            {"deploy/Caddyfile.production"},
            True,
        ),
        (
            current_head_checks.CheckEntry(
                name="build-and-test",
                source_kind="check_run",
                state="failed",
                timestamp="2026-03-12T08:36:42Z",
                details_url="https://example.invalid/frontend-constraints",
                workflow_name="Frontend CI",
                conclusion="FAILURE",
            ),
            {"constraints.txt"},
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


def test_latest_entries_uses_suite_creation_when_older_success_finishes_later() -> None:
    older_success = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "security",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "2026-07-16T10:00:00Z",
            "completedAt": "2026-07-16T12:00:00Z",
            "detailsUrl": "https://example.invalid/older-success",
            "checkSuite": {
                "createdAt": "2026-07-16T10:00:00Z",
                "workflowRun": {"workflow": {"name": "CI"}},
            },
        }
    )
    newer_pending = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "security",
            "status": "IN_PROGRESS",
            "conclusion": None,
            "startedAt": "2026-07-16T11:00:00Z",
            "completedAt": None,
            "detailsUrl": "https://example.invalid/newer-pending",
            "checkSuite": {
                "createdAt": "2026-07-16T11:00:00Z",
                "workflowRun": {"workflow": {"name": "CI"}},
            },
        }
    )

    latest, superseded = current_head_checks._latest_entries([older_success, newer_pending])

    assert latest["security"] == newer_pending
    assert superseded == [older_success]


def test_latest_entries_uses_suite_creation_when_older_run_starts_late() -> None:
    older_success = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "security",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "2026-07-16T12:00:00Z",
            "completedAt": "2026-07-16T12:05:00Z",
            "detailsUrl": "https://example.invalid/older-success",
            "checkSuite": {
                "createdAt": "2026-07-16T10:00:00Z",
                "workflowRun": {"workflow": {"name": "CI"}},
            },
        }
    )
    newer_queued = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "security",
            "status": "QUEUED",
            "conclusion": None,
            "startedAt": None,
            "completedAt": None,
            "detailsUrl": "https://example.invalid/newer-queued",
            "checkSuite": {
                "createdAt": "2026-07-16T11:00:00Z",
                "workflowRun": {"workflow": {"name": "CI"}},
            },
        }
    )

    latest, superseded = current_head_checks._latest_entries([older_success, newer_queued])

    assert latest["security"] == newer_queued
    assert superseded == [older_success]


def test_latest_entries_fails_closed_for_equal_suite_creation_times() -> None:
    passed = current_head_checks.CheckEntry(
        name="security",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-16T11:00:00Z",
        details_url="https://example.invalid/z-success",
        workflow_name="CI",
        conclusion="SUCCESS",
    )
    pending = current_head_checks.CheckEntry(
        name="security",
        source_kind="check_run",
        state="pending",
        timestamp="2026-07-16T11:00:00Z",
        details_url="https://example.invalid/a-pending",
        workflow_name="CI",
        conclusion="",
    )

    latest, superseded = current_head_checks._latest_entries([passed, pending])

    assert latest["security"] == pending
    assert superseded == [passed]


def test_latest_entries_fails_closed_for_equal_time_neutral_check_run() -> None:
    success = current_head_checks.CheckEntry(
        name="security",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-16T11:00:00Z",
        details_url="https://example.invalid/z-success",
        workflow_name="CI",
        conclusion="SUCCESS",
    )
    neutral = current_head_checks.CheckEntry(
        name="security",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-16T11:00:00Z",
        details_url="https://example.invalid/a-neutral",
        workflow_name="CI",
        conclusion="NEUTRAL",
    )

    latest, superseded = current_head_checks._latest_entries([success, neutral])

    assert latest["security"] == neutral
    assert superseded == [success]


@pytest.mark.parametrize(
    "check_suite",
    (
        None,
        [],
        {"createdAt": ""},
        {"createdAt": "not-a-timestamp"},
        {"createdAt": "2026-07-16T12:00:00"},
    ),
)
def test_check_run_without_valid_suite_creation_time_fails_closed(
    check_suite: object,
) -> None:
    with pytest.raises(ValueError, match="checkSuite.createdAt"):
        current_head_checks._normalize_node(
            {
                "__typename": "CheckRun",
                "name": "security",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
                "startedAt": "2026-07-16T12:00:00Z",
                "completedAt": "2026-07-16T12:05:00Z",
                "detailsUrl": "https://example.invalid/malformed-success",
                "checkSuite": check_suite,
            }
        )


def test_check_run_suite_creation_time_is_canonicalized_to_utc() -> None:
    entry = current_head_checks._normalize_node(
        {
            "__typename": "CheckRun",
            "name": "security",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "2026-07-16T13:00:00+02:00",
            "completedAt": "2026-07-16T13:05:00+02:00",
            "detailsUrl": "https://example.invalid/success",
            "checkSuite": {"createdAt": "2026-07-16T13:00:00+02:00"},
        }
    )

    assert entry.timestamp == "2026-07-16T11:00:00.000000Z"


def test_fetch_pr_metadata_rejects_repeated_pagination_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def repeated_cursor(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "isDraft": False,
                        "mergeStateStatus": "CLEAN",
                        "baseRefName": "main",
                        "headRefOid": "a" * 40,
                        "statusCheckRollup": {
                            "contexts": {
                                "nodes": [],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "cursor-1",
                                },
                            }
                        },
                    }
                }
            }
        }

    monkeypatch.setattr(current_head_checks, "_api_request", repeated_cursor)

    with pytest.raises(ValueError, match="pagination cursor repeated"):
        current_head_checks._fetch_pr_metadata(2142, "owner/repo", "opaque")

    assert calls == 2


@pytest.mark.parametrize(
    ("page_info", "expected"),
    [
        ({"hasNextPage": "true", "endCursor": "cursor-1"}, "must be boolean"),
        ({"hasNextPage": True, "endCursor": 1}, "cursor is malformed"),
    ],
)
def test_fetch_pr_metadata_rejects_malformed_pagination_fields(
    monkeypatch: pytest.MonkeyPatch,
    page_info: dict[str, object],
    expected: str,
) -> None:
    response = {
        "data": {
            "repository": {
                "pullRequest": {
                    "isDraft": False,
                    "mergeStateStatus": "CLEAN",
                    "baseRefName": "main",
                    "headRefOid": "a" * 40,
                    "statusCheckRollup": {"contexts": {"nodes": [], "pageInfo": page_info}},
                }
            }
        }
    }
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(ValueError, match=expected):
        current_head_checks._fetch_pr_metadata(2142, "owner/repo", "opaque")


def test_fetch_pr_metadata_rejects_non_boolean_is_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        "data": {
            "repository": {
                "pullRequest": {
                    "isDraft": "false",
                    "mergeStateStatus": "CLEAN",
                    "baseRefName": "main",
                    "headRefOid": "a" * 40,
                    "statusCheckRollup": {
                        "contexts": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    },
                }
            }
        }
    }
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(ValueError, match="isDraft must be boolean"):
        current_head_checks._fetch_pr_metadata(2142, "owner/repo", "opaque")


def test_fetch_pr_metadata_enforces_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def unique_cursor(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "isDraft": False,
                        "mergeStateStatus": "CLEAN",
                        "baseRefName": "main",
                        "headRefOid": "a" * 40,
                        "statusCheckRollup": {
                            "contexts": {
                                "nodes": [],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": f"cursor-{calls}",
                                },
                            }
                        },
                    }
                }
            }
        }

    monkeypatch.setattr(current_head_checks, "_api_request", unique_cursor)

    with pytest.raises(ValueError, match="exceeded page limit"):
        current_head_checks._fetch_pr_metadata(2142, "owner/repo", "opaque")

    assert calls == current_head_checks._MAX_STATUS_CHECK_PAGES


def test_fetch_pr_metadata_rejects_mixed_head_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "isDraft": False,
                            "mergeStateStatus": "CLEAN",
                            "baseRefName": "main",
                            "headRefOid": "a" * 40,
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [],
                                    "pageInfo": {
                                        "hasNextPage": True,
                                        "endCursor": "cursor-1",
                                    },
                                }
                            },
                        }
                    }
                }
            },
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "isDraft": False,
                            "mergeStateStatus": "CLEAN",
                            "baseRefName": "main",
                            "headRefOid": "b" * 40,
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            },
                        }
                    }
                }
            },
        ]
    )
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: next(responses),
    )

    with pytest.raises(ValueError, match="SNAPSHOT_CHANGED"):
        current_head_checks._fetch_pr_metadata(2142, "owner/repo", "opaque")


def test_fetch_pr_metadata_rejects_explicit_head_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        "data": {
            "repository": {
                "pullRequest": {
                    "isDraft": False,
                    "mergeStateStatus": "CLEAN",
                    "baseRefName": "main",
                    "headRefOid": "b" * 40,
                    "statusCheckRollup": {
                        "contexts": {
                            "nodes": [],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    },
                }
            }
        }
    }
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(ValueError, match="SNAPSHOT_CHANGED"):
        current_head_checks._fetch_pr_metadata(
            2142,
            "owner/repo",
            "opaque",
            "a" * 40,
        )


def test_required_check_parser_preserves_app_and_unbound_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: {
            "contexts": ["bound", "unbound", "unbound-null", "legacy"],
            "checks": [
                {"context": "bound", "app_id": 15368},
                {"context": "unbound", "app_id": -1},
                {"context": "unbound-null", "app_id": None},
            ],
        },
    )

    required, available = current_head_checks._fetch_required_check_names(
        "owner/repo", "main", "opaque"
    )

    assert available is True
    assert required == {
        current_head_checks.RequiredCheck("bound", 15368),
        current_head_checks.RequiredCheck("unbound", None),
        current_head_checks.RequiredCheck("unbound-null", None),
        current_head_checks.RequiredCheck("legacy", None),
    }


@pytest.mark.parametrize("app_id", ["15368", True, 0, -2, -1.0, [], {}])
def test_required_check_parser_rejects_malformed_app_id(
    monkeypatch: pytest.MonkeyPatch,
    app_id: object,
) -> None:
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: {
            "contexts": ["build"],
            "checks": [{"context": "build", "app_id": app_id}],
        },
    )

    with pytest.raises(ValueError, match="malformed app_id"):
        current_head_checks._fetch_required_check_names("owner/repo", "main", "opaque")


def test_required_app_identity_ignores_foreign_app_collision() -> None:
    trusted = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-17T10:00:00Z",
        details_url="https://example.invalid/trusted",
        workflow_name="CI",
        conclusion="SUCCESS",
        app_database_id=15368,
        app_slug="github-actions",
    )
    foreign = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-17T10:01:00Z",
        details_url="https://example.invalid/foreign",
        workflow_name="Foreign",
        conclusion="SUCCESS",
        app_database_id=999,
        app_slug="foreign",
    )

    snapshot = current_head_checks._required_snapshot(
        [trusted, foreign],
        {current_head_checks.RequiredCheck("build", 15368)},
    )

    assert snapshot == [trusted]


def test_foreign_app_success_cannot_replace_failed_or_missing_required_app() -> None:
    trusted_failure = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="failed",
        timestamp="2026-07-17T10:00:00Z",
        details_url="https://example.invalid/trusted-failure",
        workflow_name="CI",
        conclusion="FAILURE",
        app_database_id=15368,
        app_slug="github-actions",
    )
    foreign_success = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-17T10:01:00Z",
        details_url="https://example.invalid/foreign-success",
        workflow_name="CI",
        conclusion="SUCCESS",
        app_database_id=999,
        app_slug="foreign",
    )
    required = {current_head_checks.RequiredCheck("build", 15368)}

    failed = current_head_checks._required_snapshot(
        [trusted_failure, foreign_success],
        required,
    )
    missing = current_head_checks._required_snapshot(
        [foreign_success],
        required,
    )

    assert failed == [trusted_failure]
    assert missing[0].source_kind == "missing"
    assert missing[0].state == "pending"
    assert missing[0].app_database_id == 15368


def test_required_app_identity_is_not_satisfied_by_status_context() -> None:
    status_context = current_head_checks.CheckEntry(
        name="build",
        source_kind="status_context",
        state="passed",
        timestamp="2026-07-17T10:00:00Z",
        details_url="https://example.invalid/status",
        workflow_name="",
        conclusion="",
    )

    bound = current_head_checks._required_snapshot(
        [status_context],
        {current_head_checks.RequiredCheck("build", 15368)},
    )
    unbound = current_head_checks._required_snapshot(
        [status_context],
        {"build"},
    )
    structured_unbound = current_head_checks._required_snapshot(
        [status_context],
        {current_head_checks.RequiredCheck("build", None)},
    )

    assert bound[0].source_kind == "missing"
    assert bound[0].state == "pending"
    assert bound[0].app_database_id == 15368
    assert unbound == [status_context]
    assert structured_unbound == [status_context]


def test_required_same_name_check_and_status_both_remain_blocking() -> None:
    passing_check = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-17T10:01:00Z",
        details_url="https://example.invalid/check",
        workflow_name="CI",
        conclusion="SUCCESS",
        app_database_id=15368,
    )
    failing_status = current_head_checks.CheckEntry(
        name="build",
        source_kind="status_context",
        state="failed",
        timestamp="2026-07-17T10:02:00Z",
        details_url="https://example.invalid/status",
        workflow_name="",
        conclusion="",
    )

    snapshot = current_head_checks._required_snapshot(
        [passing_check, failing_status],
        {current_head_checks.RequiredCheck("build", 15368)},
    )

    assert snapshot == [passing_check, failing_status]


def test_required_same_name_status_cannot_hide_failed_check_run() -> None:
    failing_check = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="failed",
        timestamp="2026-07-17T10:01:00Z",
        details_url="https://example.invalid/check",
        workflow_name="CI",
        conclusion="FAILURE",
    )
    passing_status = current_head_checks.CheckEntry(
        name="build",
        source_kind="status_context",
        state="passed",
        timestamp="2026-07-17T10:02:00Z",
        details_url="https://example.invalid/status",
        workflow_name="",
        conclusion="",
    )

    snapshot = current_head_checks._required_snapshot(
        [failing_check, passing_status],
        {current_head_checks.RequiredCheck("build")},
    )

    assert snapshot == [failing_check, passing_status]


def test_required_status_cannot_hide_stale_suppressed_check_run() -> None:
    stale_check = current_head_checks.CheckEntry(
        name="build",
        source_kind="check_run",
        state="passed",
        timestamp="2026-07-17T10:01:00Z",
        details_url="https://example.invalid/build",
        workflow_name="CI",
        conclusion="SUCCESS",
    )
    newer_workflow_activity = current_head_checks.CheckEntry(
        name="lint",
        source_kind="check_run",
        state="pending",
        timestamp="2026-07-17T10:02:00Z",
        details_url="https://example.invalid/lint",
        workflow_name="CI",
        conclusion="",
    )
    passing_status = current_head_checks.CheckEntry(
        name="build",
        source_kind="status_context",
        state="passed",
        timestamp="2026-07-17T10:03:00Z",
        details_url="https://example.invalid/status",
        workflow_name="",
        conclusion="",
    )

    snapshot = current_head_checks._required_snapshot(
        [stale_check, newer_workflow_activity, passing_status],
        {current_head_checks.RequiredCheck("build")},
    )

    assert snapshot[0].source_kind == "missing"
    assert snapshot[0].state == "pending"
    assert snapshot[1] == passing_status


@pytest.mark.parametrize("field", ("checks", "contexts"))
@pytest.mark.parametrize("malformed", ({}, "", 0, False))
def test_required_check_parser_rejects_falsey_malformed_containers(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    malformed: object,
) -> None:
    payload: dict[str, object] = {"checks": [], "contexts": []}
    payload[field] = malformed
    monkeypatch.setattr(
        current_head_checks,
        "_api_request",
        lambda *_args, **_kwargs: payload,
    )

    with pytest.raises(ValueError, match="response lists are malformed"):
        current_head_checks._fetch_required_check_names("owner/repo", "main", "opaque")


def test_normalize_node_rejects_unknown_graphql_union_member() -> None:
    with pytest.raises(ValueError, match="unsupported status-check node type"):
        current_head_checks._normalize_node(
            {
                "__typename": "FutureStatusCheck",
                "context": "build",
                "state": "SUCCESS",
                "createdAt": "2026-07-17T10:00:00Z",
            }
        )


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


def test_main_forwards_event_head_to_metadata_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_head_sha = "c" * 40
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": 2142,
                    "head": {"sha": event_head_sha},
                },
                "repository": {"full_name": "owner/repo"},
            }
        ),
        encoding="utf-8",
    )
    observed_heads: list[str | None] = []

    def fetch_metadata(
        _pr_number: int,
        _repo: str,
        _token: str,
        expected_head_sha: str | None,
    ) -> tuple[bool, str, str, list[dict[str, object]]]:
        observed_heads.append(expected_head_sha)
        return True, "CLEAN", "main", []

    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "opaque")
    monkeypatch.setattr(current_head_checks, "_fetch_pr_metadata", fetch_metadata)
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_required_check_names",
        lambda *_args: (set(), True),
    )

    assert current_head_checks.main(["--event-path", str(event_path)]) == 0
    assert observed_heads == [event_head_sha]


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
                    "checkSuite": {
                        "createdAt": "2026-03-12T04:48:16Z",
                        "workflowRun": {"workflow": {"name": "Docker Image CI"}},
                    },
                },
                {
                    "__typename": "CheckRun",
                    "name": "build",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": "2026-03-12T05:09:03Z",
                    "detailsUrl": "https://example.invalid/passed",
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Image CI"}},
                    },
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Image CI"}},
                    },
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


def test_main_fails_when_latest_required_check_is_neutral(
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
                    "name": "security",
                    "status": "COMPLETED",
                    "conclusion": "NEUTRAL",
                    "startedAt": "2026-03-12T05:05:00Z",
                    "completedAt": "2026-03-12T05:09:03Z",
                    "detailsUrl": "https://example.invalid/neutral",
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "CI"}},
                    },
                }
            ],
        ),
    )
    monkeypatch.setattr(
        current_head_checks,
        "_fetch_required_check_names",
        lambda *args: ({"security"}, True),
    )

    exit_code = current_head_checks.main(
        ["--pr-number", "1127", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "- security: failed [CI]" in captured.out
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Image CI"}},
                    },
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Image CI"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Build and Push"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Build and Push"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "CI"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "CI"}},
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
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Greenlight iOS Preflight"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "CI"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "CI"}},
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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Docker Image CI"}},
                    },
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
            "checkSuite": {
                "createdAt": "2026-06-29T05:05:00Z",
                "workflowRun": {"workflow": {"name": "CI"}},
            },
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
            "checkSuite": {
                "createdAt": "2026-06-29T19:12:16Z",
                "workflowRun": {"workflow": {"name": "Docker Build and Push"}},
            },
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


def test_main_fails_cleanly_when_github_metadata_is_malformed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(current_head_checks, "_github_token", lambda: "token")

    def raise_validation_error(*_args: object, **_kwargs: object) -> None:
        raise ValueError("GraphQL status-check pagination cursor repeated")

    monkeypatch.setattr(current_head_checks, "_fetch_pr_metadata", raise_validation_error)

    exit_code = current_head_checks.main(
        ["--pr-number", "1129", "--repo", "Katsiarynakavaleuskaya/PulsePlate"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert (
        "ERROR: failed to validate GitHub check state: "
        "GraphQL status-check pagination cursor repeated"
    ) in captured.out


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
                    "checkSuite": {
                        "createdAt": "2026-03-12T05:05:00Z",
                        "workflowRun": {"workflow": {"name": "Optional CI"}},
                    },
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
