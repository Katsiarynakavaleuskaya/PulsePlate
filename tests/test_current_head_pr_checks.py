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
    "ci_test_reuse",
    "ci_test_evidence",
}


@pytest.fixture(autouse=True)
def _default_changed_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(current_head_checks, "_fetch_pr_changed_paths", lambda *args: set())
    monkeypatch.setattr(
        current_head_checks,
        "_live_pr_refs",
        lambda _number, _repo, _token, expected: ("b" * 40, expected or "a" * 40),
    )
    monkeypatch.setattr(current_head_checks, "verify_base_test_reuse", lambda **_kwargs: None)


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


# These fixtures exercise native provenance and real Git objects, independently
# of the candidate-authored JSON locators.
from copy import deepcopy
import io
import stat
import urllib.parse
import zipfile
from typing import Any

from scripts.ci import mapping_only_ci_reuse as ci_reuse
from scripts.orchestration import pr_commit_identity as reuse_identity
from scripts.orchestration import pr_review_context as reuse_context
from scripts.orchestration import pr_review_evidence as reuse_evidence


class _NativeReuseHarness:
    def __init__(
        self, root: Path, monkeypatch: pytest.MonkeyPatch, profile: str = "backend"
    ) -> None:
        self.root = root
        self.repository = "owner/repo"
        self.number = 42
        self.repo_id = 66
        self.urls: list[str] = []
        self.runs: dict[int, dict[str, Any]] = {}
        self.native_jobs: dict[int, list[dict[str, Any]]] = {}
        self.artifacts: dict[int, list[dict[str, Any]]] = {}
        self.archives: dict[int, bytes] = {}
        self.checks: dict[int, dict[str, Any]] = {}
        self.pr_override: dict[str, Any] | None = None
        self.base_ref = "main"
        self.native_branch_override: Any = None
        self.tree_override: dict[str, Any] | None = None
        self.graph_override: dict[str, Any] | None = None
        self.download_hook: Any = None
        self.latest_override: list[dict[str, Any]] | None = None
        git = reuse_context._binary("git")
        reuse_context._run_command([git, "init", str(root)], cwd=root)
        self.git(["config", "user.name", "CI proof fixture"])
        self.git(["config", "user.email", "ci-proof@example.invalid"])
        (root / ".github/workflows").mkdir(parents=True)
        (root / "scripts/ci").mkdir(parents=True)
        (root / "app").mkdir()
        (root / "AGENTS.md").write_text("Fixture policy\n")
        (root / ".github/workflows/ci.yml").write_bytes(
            (REPO_ROOT / ".github/workflows/ci.yml").read_bytes()
        )
        (root / ci_reuse.HELPER_PATH).write_bytes((REPO_ROOT / ci_reuse.HELPER_PATH).read_bytes())
        self.material_paths = ["app/planning.py"] if profile != "ios_only" else []
        if profile in {"backend_ios", "ios_only"}:
            self.material_paths.append("ios/Planning.swift")
        if profile == "main_matrix":
            original_profile = ci_reuse.ci_risk_profile.build_risk_profile
            from dataclasses import replace

            monkeypatch.setattr(
                ci_reuse.ci_risk_profile,
                "build_risk_profile",
                lambda paths: replace(original_profile(paths), run_main_ci_diagnostic=True),
            )
        for path in self.material_paths:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("value = 1\n")
        self.git(["add", "."])
        self.git(["commit", "-m", "BASE fixture"])
        self.base = self.git(["rev-parse", "HEAD"]).strip()
        self.native_base_sha = self.base
        for path in self.material_paths:
            (root / path).write_text("value = 2\n")
        self.git(["add", "."])
        self.git(["commit", "-m", "Material fixture"])
        self.material = self.git(["rev-parse", "HEAD"]).strip()
        self.head = self.material
        self.synthetic_material = self.synthetic(self.material)
        monkeypatch.setattr(ci_reuse, "REPO_ROOT", root)
        monkeypatch.setattr(reuse_evidence, "_REPO_ROOT", root)
        monkeypatch.setattr(reuse_identity, "github_api_request", self.request)
        monkeypatch.setattr(reuse_identity, "github_artifact_download", self.download)
        self.git(["checkout", "--detach", self.base])
        self.source_run = self.add_run(101, self.material, complete=True)
        context = self.context()
        material = reuse_evidence.compute_material_manifest(
            root, base_ref_oid=self.base, head_ref_oid=self.material, pr_number=42
        )
        self.policy = ci_reuse._policy(root, context, material)
        self.source_job_rows = self.add_jobs(self.source_run, self.policy, reused=False)
        direct_plan = ci_reuse._document(context, self.source_run, schema=ci_reuse.PLAN_SCHEMA)
        self.source_manifest = ci_reuse.collect_execution(
            repo_root=root,
            context=context,
            run=self.source_run,
            token="opaque-test-token",
            checkout_sha=self.synthetic_material,
            plan=direct_plan,
        )
        assert self.source_manifest is not None
        self.source_artifact = self.add_artifact(
            self.source_run,
            self.writer(self.source_run),
            ci_reuse.WRITER_UPLOAD,
            "ci-test-execution-101-1",
            "ci-test-execution.json",
            ci_reuse._canonical(self.source_manifest),
        )
        self.seal_mapping(monkeypatch)
        self.target_run = self.add_run(102, self.head, complete=False)
        self.target_context = self.context()
        self.synthetic_head = self.synthetic(self.head)
        self.git(["checkout", "--detach", self.base])
        self.plan = ci_reuse.plan_reuse(
            repo_root=root,
            context=self.target_context,
            run=self.target_run,
            token="opaque-test-token",
            checkout_sha=self.synthetic_head,
        )
        assert self.plan["mode"] == "reused", self.plan["reason"]

    def git(self, args: list[str], *, raw: bytes | None = None) -> str:
        return reuse_evidence._run_git(self.root, args, input_bytes=raw).decode("utf-8")

    def synthetic(self, head: str) -> str:
        tree = self.git(["rev-parse", f"{head}^{{tree}}"]).strip()
        return self.git(
            ["commit-tree", tree, "-p", self.base, "-p", head, "-m", "Synthetic event checkout"]
        ).strip()

    def context(self) -> ci_reuse.Context:
        return ci_reuse._context(self.repository, 42, "opaque-test-token")

    def seal_mapping(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.git(["checkout", "--detach", self.material])
        material = reuse_evidence.compute_material_manifest(
            self.root, base_ref_oid=self.base, head_ref_oid=self.material, pr_number=42
        )
        report: dict[str, Any] = {
            "actionable_findings_count": 0,
            "base_ref_oid": self.base,
            "calibration": {},
            "coordinator_packet": {},
            "decision_log": [],
            "deferred_followups": [],
            "findings": [],
            "findings_count": 0,
            "gate_plan": [],
            "generated_at_utc": "2026-09-12T00:00:00Z",
            "material_digest": material.digest,
            "material_head_sha": self.material,
            "merge_base_sha": self.base,
            "mode": "dry-run-report",
            "review_source_status": [],
            "role_review": [],
            "schema_version": "2.0.0",
            "scope_reviewed": {
                "changed_files": self.material_paths,
                "diff_summary": material.diff_summary.as_dict(),
                "fixed_mapping_errors": [],
                "pr_metadata_available": True,
                "scoped_agents_md": ["AGENTS.md"],
            },
            "warnings": [],
        }
        report_path = self.root / "report.json"
        report_path.write_bytes(ci_reuse._canonical(report))
        receipt = reuse_evidence.ingest_repo_native_self_review_receipt(
            report_path, material_manifest=material
        )
        report_path.unlink()
        review, security = reuse_evidence.build_provider_no_claim_pair(
            base_revision=self.base, head_revision=self.material, material_digest=material.digest
        )
        seal = {
            "authority": reuse_evidence.RECEIPT_AUTHORITY,
            "code_review": review,
            "codex_security": security,
            "material": {
                "base_ref_oid": self.base,
                "digest": material.digest,
                "material_head_sha": self.material,
                "merge_base_sha": self.base,
                "policy_version": reuse_evidence.MATERIAL_POLICY_VERSION,
            },
            "pr_number": 42,
            "repository": self.repository,
            "schema_version": reuse_evidence.SEAL_SCHEMA_VERSION,
            "self_review": receipt,
        }
        mapping = self.root / "docs/review/PR_42_FIXED_MAPPING.md"
        mapping.parent.mkdir(parents=True)
        mapping.write_text(reuse_evidence.render_embedded_review_seal(seal))
        self.git(["add", "docs/review/PR_42_FIXED_MAPPING.md"])
        self.git(["commit", "-m", "One mapping closeout"])
        self.head = self.git(["rev-parse", "HEAD"]).strip()

    def add_run(
        self, run_id: int, head: str, *, complete: bool, attempt: int = 1
    ) -> dict[str, Any]:
        run = {
            "id": run_id,
            "run_attempt": attempt,
            "workflow_id": 77,
            "check_suite_id": run_id + 1000,
            "head_sha": head,
            "head_branch": "codex/fixture",
            "name": "CI",
            "path": ci_reuse.WORKFLOW_PATH,
            "event": "pull_request",
            "repository": {"id": self.repo_id, "full_name": self.repository},
            "head_repository": {"id": self.repo_id, "full_name": self.repository},
            "pull_requests": [{"number": 42, "base": {"sha": self.base}, "head": {"sha": head}}],
            "url": f"https://api.github.com/repos/{self.repository}/actions/runs/{run_id}",
            "created_at": f"2026-09-12T10:{run_id - 100:02}:00Z",
            "run_started_at": f"2026-09-12T10:{run_id - 100:02}:00Z",
            "status": "completed" if complete else "in_progress",
            "conclusion": "failure" if complete else None,
        }
        self.runs[run_id] = run
        self.artifacts[run_id] = []
        self.native_jobs[run_id] = []
        return run

    def step(self, name: str, number: int, *, success: bool = True) -> dict[str, Any]:
        return {
            "name": name,
            "number": number,
            "status": "completed",
            "conclusion": "success" if success else "skipped",
            "started_at": "2026-09-12T11:00:00Z",
            "completed_at": "2026-09-12T11:00:20Z",
        }

    def add_job(
        self, run: dict[str, Any], name: str, steps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        job_id = run["id"] * 100 + len(self.native_jobs[run["id"]]) + 1
        job = {
            "id": job_id,
            "run_id": run["id"],
            "run_attempt": run["run_attempt"],
            "head_sha": run["head_sha"],
            "workflow_name": "CI",
            "name": name,
            "run_url": run["url"],
            "check_run_url": f"https://api.github.com/repos/{self.repository}/check-runs/{job_id}",
            "status": "completed",
            "conclusion": "success",
            "steps": steps,
        }
        self.native_jobs[run["id"]].append(job)
        self.checks[job_id] = {
            "id": job_id,
            "name": name,
            "head_sha": run["head_sha"],
            "status": "completed",
            "conclusion": "success",
            "app": {"id": ci_reuse.GITHUB_ACTIONS_APP_ID, "slug": "github-actions"},
            "check_suite": {"id": run["check_suite_id"]},
        }
        return job

    def add_jobs(
        self, run: dict[str, Any], policy: ci_reuse.BasePolicy, *, reused: bool
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for cell in policy.cells:
            names = [
                "Checkout trusted base",
                ci_reuse.VERIFY_STEP,
                *policy.critical[cell.job_id],
                ci_reuse.DIRECT_MARKER,
                ci_reuse.REUSED_MARKER,
            ]
            steps = [
                self.step(
                    name,
                    index + 1,
                    success=(
                        name
                        in {
                            "Checkout trusted base",
                            ci_reuse.VERIFY_STEP,
                            ci_reuse.REUSED_MARKER,
                            ci_reuse.UPLOAD_PR,
                            ci_reuse.UPLOAD_MAIN,
                        }
                        if reused
                        else name not in {ci_reuse.VERIFY_STEP, ci_reuse.REUSED_MARKER}
                    ),
                )
                for index, name in enumerate(names)
            ]
            job = self.add_job(run, cell.check_name, steps)
            selected.append(job)
            if cell.coverage_name:
                self.add_artifact(
                    run,
                    job,
                    ci_reuse.UPLOAD_PR if cell.job_id == "test-pr" else ci_reuse.UPLOAD_MAIN,
                    f"{cell.coverage_name}-{run['id']}-{run['run_attempt']}",
                    "coverage.xml",
                    b'<?xml version="1.0"?><!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd"><coverage lines-valid="10" lines-covered="10" line-rate="1"><packages/></coverage>',
                )
        self.add_job(
            run,
            ci_reuse.WRITER_NAME,
            [
                self.step("Checkout trusted base", 1),
                self.step(ci_reuse.WRITER_COLLECT, 2),
                self.step(ci_reuse.WRITER_UPLOAD, 3),
            ],
        )
        return selected

    def writer(self, run: dict[str, Any]) -> dict[str, Any]:
        return next(
            job for job in self.native_jobs[run["id"]] if job["name"] == ci_reuse.WRITER_NAME
        )

    def add_artifact(
        self,
        run: dict[str, Any],
        producer: dict[str, Any],
        upload: str,
        name: str,
        member: str,
        content: bytes,
    ) -> dict[str, Any]:
        archive = _reuse_zip(member, content)
        artifact_id = run["id"] * 1000 + len(self.artifacts[run["id"]]) + 1
        metadata = {
            "id": artifact_id,
            "name": name,
            "size_in_bytes": len(archive),
            "digest": ci_reuse._digest(archive),
            "expired": False,
            "created_at": "2026-09-12T11:00:10Z",
            "updated_at": "2026-09-12T11:00:10Z",
            "expires_at": "2099-09-12T11:00:10Z",
            "url": f"https://api.github.com/repos/{self.repository}/actions/artifacts/{artifact_id}",
            "archive_download_url": f"https://api.github.com/repos/{self.repository}/actions/artifacts/{artifact_id}/zip",
            "workflow_run": {
                "id": run["id"],
                "head_sha": run["head_sha"],
                "repository_id": self.repo_id,
                "head_repository_id": self.repo_id,
            },
        }
        self.artifacts[run["id"]].append(metadata)
        self.archives[artifact_id] = archive
        return metadata

    def download(self, url: str, *, token: str, max_bytes: int) -> bytes:
        assert token == "opaque-test-token"
        artifact_id = int(url.split("/")[-2])
        if self.download_hook:
            self.download_hook(artifact_id)
        return self.archives[artifact_id]

    def request(self, url: str, *, token: str, method: str = "GET", payload: Any = None) -> Any:
        assert token == "opaque-test-token"
        self.urls.append(url)
        if url == "https://api.github.com/graphql":
            assert method == "POST" and payload["variables"]["number"] == 42
            return self.graph_override or {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "baseRefOid": self.base,
                            "headRefOid": self.head,
                            "commits": {
                                "nodes": [
                                    {"commit": {"oid": sha, "pushedDate": "2026-09-12T10:00:00Z"}}
                                    for sha in dict.fromkeys((self.material, self.head))
                                ],
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                            },
                        }
                    }
                }
            }
        parsed = urllib.parse.urlsplit(url)
        assert parsed.netloc == "api.github.com"
        path = parsed.path.removeprefix(f"/repos/{self.repository}/")
        if path.startswith("branches/"):
            assert path == "branches/" + urllib.parse.quote(self.base_ref, safe="")
            if self.native_branch_override is not None:
                if isinstance(self.native_branch_override, Exception):
                    raise self.native_branch_override
                return deepcopy(self.native_branch_override)
            return {
                "name": self.base_ref,
                "commit": {
                    "sha": self.native_base_sha,
                    "url": f"https://api.github.com/repos/{self.repository}/commits/{self.native_base_sha}",
                },
                "_links": {
                    "self": f"https://api.github.com/repos/{self.repository}/branches/{urllib.parse.quote(self.base_ref, safe='')}"
                },
            }
        if path == "pulls/42":
            return self.pr_override or {
                "number": 42,
                "state": "open",
                "base": {
                    "sha": self.base,
                    "ref": self.base_ref,
                    "repo": {"id": self.repo_id, "full_name": self.repository},
                },
                "head": {
                    "sha": self.head,
                    "ref": "codex/fixture",
                    "repo": {"id": self.repo_id, "full_name": self.repository},
                },
            }
        if path == "actions/workflows/ci.yml/runs":
            query = urllib.parse.parse_qs(parsed.query)
            runs = (
                self.latest_override
                if self.latest_override is not None
                else [run for run in self.runs.values() if run["head_sha"] == query["head_sha"][0]]
            )
            return {"total_count": len(runs), "workflow_runs": deepcopy(runs)}
        if path.startswith("actions/runs/"):
            parts = path.split("/")
            run_id = int(parts[2])
            if len(parts) == 3:
                return deepcopy(self.runs[run_id])
            if parts[-1] == "jobs":
                return {
                    "total_count": len(self.native_jobs[run_id]),
                    "jobs": deepcopy(self.native_jobs[run_id]),
                }
            if parts[-1] == "artifacts":
                return {
                    "total_count": len(self.artifacts[run_id]),
                    "artifacts": deepcopy(self.artifacts[run_id]),
                }
        if path.startswith("actions/artifacts/"):
            artifact_id = int(path.split("/")[-1])
            return deepcopy(
                next(
                    artifact
                    for artifacts in self.artifacts.values()
                    for artifact in artifacts
                    if artifact["id"] == artifact_id
                )
            )
        if path.startswith("check-runs/"):
            return deepcopy(self.checks[int(path.split("/")[-1])])
        if path.startswith("git/commits/"):
            sha = path.split("/")[-1]
            parents = self.git(["rev-list", "--parents", "-n", "1", sha]).strip().split()[1:]
            return {
                "sha": sha,
                "parents": [{"sha": parent} for parent in parents],
                "tree": {"sha": self.git(["rev-parse", f"{sha}^{{tree}}"]).strip()},
            }
        if path.startswith("git/trees/"):
            tree_sha = path.split("/")[-1]
            if self.tree_override is not None:
                return deepcopy(self.tree_override)
            entries = []
            for row in self.git(["ls-tree", "-r", tree_sha]).splitlines():
                fields, name = row.split("\t", 1)
                mode, kind, sha = fields.split()
                entries.append({"mode": mode, "type": kind, "sha": sha, "path": name})
            return {"sha": tree_sha, "truncated": False, "tree": entries}
        raise AssertionError(f"Unexpected native API path {path}")

    def project(
        self, *, plan: dict[str, Any] | None = None, coverage_output: Path | None = None
    ) -> str:
        return ci_reuse.project_reuse(
            repo_root=self.root,
            context=self.target_context,
            run=self.target_run,
            token="opaque-test-token",
            checkout_sha=self.synthetic_head,
            plan=plan or self.plan,
            job_id="test-pr",
            matrix_value="3.13",
            coverage_output=coverage_output or self.root / "coverage.xml",
        )

    def target_manifest(self) -> dict[str, Any]:
        self.add_jobs(self.target_run, self.policy, reused=True)
        manifest = ci_reuse.collect_execution(
            repo_root=self.root,
            context=self.target_context,
            run=self.target_run,
            token="opaque-test-token",
            checkout_sha=self.synthetic_head,
            plan=self.plan,
        )
        assert manifest is not None
        self.add_artifact(
            self.target_run,
            self.writer(self.target_run),
            ci_reuse.WRITER_UPLOAD,
            "ci-test-execution-102-1",
            "ci-test-execution.json",
            ci_reuse._canonical(manifest),
        )
        return manifest


def _reuse_zip(name: str, content: bytes, *, unix_mode: int = stat.S_IFREG | 0o600) -> bytes:
    destination = io.BytesIO()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        member = zipfile.ZipInfo(name)
        member.external_attr = unix_mode << 16
        archive.writestr(member, content)
    return destination.getvalue()


@pytest.fixture
def native_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> _NativeReuseHarness:
    return _NativeReuseHarness(tmp_path, monkeypatch, getattr(request, "param", "backend"))


@pytest.mark.parametrize("latest", ["absent", "pending", "failure", "cancelled"])
def test_mapping_reuse_incomplete_current_run_cannot_mask_prior_reused_checks(
    native_reuse: _NativeReuseHarness, latest: str
) -> None:
    harness = native_reuse
    harness.target_manifest()
    ci_reuse.verify_current_reuse(
        repo_root=harness.root,
        repository=harness.repository,
        pr_number=42,
        token="opaque-test-token",
    )
    if latest == "absent":
        harness.runs.pop(102)
    else:
        run = harness.add_run(103, harness.head, complete=latest != "pending")
        if latest != "pending":
            run["conclusion"] = latest
    harness.source_run["run_attempt"] = 2
    expected = (
        "canonical current-head CI run is unavailable"
        if latest == "absent"
        else "source_evidence_writer_absent"
    )
    with pytest.raises(ci_reuse.ReuseError, match=expected):
        ci_reuse.verify_current_reuse(
            repo_root=harness.root,
            repository=harness.repository,
            pr_number=42,
            token="opaque-test-token",
        )


def test_mapping_reuse_real_mapping_successor_source_failure_outside_tests_and_final_refresh(
    native_reuse: _NativeReuseHarness,
) -> None:
    assert native_reuse.source_run["conclusion"] == "failure"
    assert native_reuse.plan["source"]["run"]["run_id"] == 101
    assert native_reuse.project() == "reused"
    assert (native_reuse.root / "coverage.xml").read_bytes().startswith(b"<?xml")
    manifest = native_reuse.target_manifest()
    assert manifest["mode"] == "reused"
    assert manifest["source"] == native_reuse.plan["source"]
    ci_reuse.verify_current_reuse(
        repo_root=native_reuse.root,
        repository="owner/repo",
        pr_number=42,
        token="opaque-test-token",
        expected_head_sha=native_reuse.head,
        expected_base_sha=native_reuse.base,
    )
    assert sum(url.endswith("pulls/42") for url in native_reuse.urls) >= 5


@pytest.mark.parametrize(
    "fault",
    [
        "newer_pending",
        "newer_failure",
        "newer_cancelled",
        "mixed_attempt",
        "foreign_app",
        "missing_critical",
        "neutral_critical",
        "both_markers",
        "inherited_source",
        "array_source_mode",
        "object_source_mode",
        "missing_cell",
        "duplicate_cell",
        "extra_cell",
        "missing_coverage",
        "expired_coverage",
        "wrong_artifact_head",
        "outside_upload",
        "archive_digest",
        "member_digest",
        "unsafe_zip",
        "unsafe_xml",
        "forged_plan",
        "raced_source",
        "raced_source_base",
        "raced_head",
        "raced_base",
        "wrong_merge_parents",
        "different_merge_tree",
    ],
)
def test_mapping_reuse_projection_rejects_contradictory_or_raced_native_evidence(
    native_reuse: _NativeReuseHarness, fault: str
) -> None:
    harness = native_reuse
    source_job = harness.source_job_rows[0]
    coverage = harness.artifacts[101][0]
    plan = deepcopy(harness.plan)
    if fault in {"newer_pending", "newer_failure", "newer_cancelled"}:
        harness.add_run(103, harness.material, complete=fault != "newer_pending")
        if fault == "newer_cancelled":
            harness.runs[103]["conclusion"] = "cancelled"
    elif fault == "mixed_attempt":
        source_job["run_attempt"] = 2
    elif fault == "foreign_app":
        harness.checks[source_job["id"]]["app"]["id"] = 999
    elif fault in {"missing_critical", "neutral_critical"}:
        step = next(
            step for step in source_job["steps"] if step["name"].startswith("Critical smoke")
        )
        if fault == "missing_critical":
            source_job["steps"].remove(step)
        else:
            step["conclusion"] = "neutral"
    elif fault == "both_markers":
        next(step for step in source_job["steps"] if step["name"] == ci_reuse.REUSED_MARKER)[
            "conclusion"
        ] = "success"
    elif fault in {"inherited_source", "array_source_mode", "object_source_mode"}:
        manifest = deepcopy(harness.source_manifest)
        manifest["mode"] = {
            "inherited_source": "reused",
            "array_source_mode": [],
            "object_source_mode": {},
        }[fault]
        manifest["source"] = deepcopy(plan["source"])
        manifest = ci_reuse._finish_document(manifest)
        archive = _reuse_zip("ci-test-execution.json", ci_reuse._canonical(manifest))
        harness.archives[harness.source_artifact["id"]] = archive
        harness.source_artifact["size_in_bytes"] = len(archive)
        harness.source_artifact["digest"] = ci_reuse._digest(archive)
        plan["source"]["artifact"]["archive_digest"] = harness.source_artifact["digest"]
        plan["source"]["artifact"]["member_digest"] = ci_reuse._digest(
            ci_reuse._canonical(manifest)
        )
        plan["upstream_assets"] = [deepcopy(plan["source"])]
        plan = ci_reuse._finish_document(plan)
    elif fault == "missing_cell":
        harness.native_jobs[101].remove(source_job)
    elif fault == "duplicate_cell":
        duplicate = deepcopy(source_job)
        duplicate["id"] += 99
        harness.native_jobs[101].append(duplicate)
    elif fault == "extra_cell":
        harness.add_job(harness.source_run, "test-main (3.14, 90)", [])
    elif fault == "missing_coverage":
        harness.artifacts[101].remove(coverage)
    elif fault == "expired_coverage":
        coverage["expires_at"] = "2020-01-01T00:00:00Z"
    elif fault == "wrong_artifact_head":
        coverage["workflow_run"]["head_sha"] = "f" * 40
    elif fault == "outside_upload":
        coverage["created_at"] = "2026-09-12T10:30:00Z"
    elif fault == "archive_digest":
        harness.archives[coverage["id"]] += b"tampered"
    elif fault == "member_digest":
        plan["source"]["artifact"]["member_digest"] = "sha256:" + "f" * 64
        plan = ci_reuse._finish_document(plan)
    elif fault in {"unsafe_zip", "unsafe_xml"}:
        content = b'<!DOCTYPE coverage [<!ENTITY x "boom">]><coverage lines-valid="1" lines-covered="1" line-rate="1">&x;</coverage>'
        archive = _reuse_zip(
            "../coverage.xml" if fault == "unsafe_zip" else "coverage.xml", content
        )
        harness.archives[coverage["id"]] = archive
        coverage["size_in_bytes"] = len(archive)
        coverage["digest"] = ci_reuse._digest(archive)
    elif fault == "forged_plan":
        plan["universe"] = []
        plan = ci_reuse._finish_document(plan)
    elif fault in {"raced_source", "raced_source_base"}:

        def race(artifact_id: int) -> None:
            if fault == "raced_source":
                harness.source_run["run_attempt"] = 2
            else:
                harness.source_run["pull_requests"][0]["base"]["sha"] = "d" * 40

        harness.download_hook = race
    elif fault in {"raced_head", "raced_base"}:
        harness.pr_override = {
            "number": 42,
            "state": "open",
            "base": {
                "sha": "f" * 40 if fault == "raced_base" else harness.base,
                "ref": harness.base_ref,
                "repo": {"id": harness.repo_id, "full_name": harness.repository},
            },
            "head": {
                "sha": "f" * 40 if fault == "raced_head" else harness.head,
                "ref": "codex/fixture",
                "repo": {"id": harness.repo_id, "full_name": harness.repository},
            },
        }
    elif fault == "wrong_merge_parents":
        harness.synthetic_head = harness.synthetic_material
    elif fault == "different_merge_tree":
        tree_sha = harness.git(["rev-parse", f"{harness.head}^{{tree}}"]).strip()
        harness.tree_override = {
            "sha": tree_sha,
            "truncated": False,
            "tree": [
                {"path": "app/planning.py", "type": "blob", "mode": "100644", "sha": "f" * 40}
            ],
        }
    if fault in {
        "array_source_mode",
        "object_source_mode",
        "foreign_app",
        "mixed_attempt",
        "both_markers",
        "inherited_source",
        "duplicate_cell",
        "extra_cell",
        "wrong_artifact_head",
        "outside_upload",
        "archive_digest",
        "unsafe_zip",
        "unsafe_xml",
        "raced_source",
        "raced_source_base",
        "raced_head",
        "raced_base",
        "wrong_merge_parents",
        "different_merge_tree",
    }:
        with pytest.raises(
            (
                ci_reuse.ReuseError,
                reuse_identity.CommitIdentityError,
                reuse_evidence.ReviewEvidenceError,
            )
        ):
            ci_reuse.plan_reuse(
                repo_root=harness.root,
                context=harness.target_context,
                run=harness.target_run,
                token="opaque-test-token",
                checkout_sha=harness.synthetic_head,
            )
    with pytest.raises(
        (
            ci_reuse.ReuseError,
            reuse_identity.CommitIdentityError,
            reuse_evidence.ReviewEvidenceError,
        )
    ):
        harness.project(plan=plan)


@pytest.mark.parametrize(
    "fault",
    [
        "absent",
        "missing_writer",
        "missing_cell",
        "failed_job",
        "missing_artifact",
        "expired_artifact",
        "old_source_base",
        "missing_step",
        "missing_markers",
    ],
)
def test_mapping_reuse_missing_source_executes_without_older_green_search(
    native_reuse: _NativeReuseHarness,
    fault: str,
) -> None:
    harness = native_reuse
    if fault == "absent":
        harness.runs.pop(101)
    elif fault == "missing_writer":
        harness.native_jobs[101] = [
            job for job in harness.native_jobs[101] if job["name"] != ci_reuse.WRITER_NAME
        ]
    elif fault == "missing_cell":
        harness.native_jobs[101].remove(harness.source_job_rows[0])
    elif fault == "failed_job":
        job = harness.source_job_rows[0]
        job["conclusion"] = "failure"
        harness.checks[job["id"]]["conclusion"] = "failure"
    elif fault == "missing_artifact":
        harness.artifacts[101].remove(harness.artifacts[101][0])
    elif fault == "expired_artifact":
        harness.artifacts[101][0]["expires_at"] = "2020-01-01T00:00:00Z"
    elif fault == "old_source_base":
        harness.source_run["pull_requests"][0]["base"]["sha"] = "d" * 40
    elif fault == "missing_step":
        job = harness.source_job_rows[0]
        job["steps"] = [
            step for step in job["steps"] if not step["name"].startswith("Critical smoke")
        ]
    else:
        next(
            step
            for step in harness.source_job_rows[0]["steps"]
            if step["name"] == ci_reuse.DIRECT_MARKER
        )["conclusion"] = "skipped"
    plan = ci_reuse.plan_reuse(
        repo_root=harness.root,
        context=harness.target_context,
        run=harness.target_run,
        token="opaque-test-token",
        checkout_sha=harness.synthetic_head,
    )
    assert plan["mode"] == "executed"
    assert (
        plan["reason"]
        == {
            "absent": "source_absent",
            "missing_writer": "source_evidence_writer_absent",
            "missing_cell": "native_test_universe_incomplete",
            "failed_job": "selected_native_job_not_successful",
            "missing_artifact": "attempt_specific_artifact_absent",
            "expired_artifact": "source_artifact_expired",
            "old_source_base": "latest_source_base_differs",
            "missing_step": "required_native_execution_step_not_successful",
            "missing_markers": "native_execution_proof_absent",
        }[fault]
    )
    assert plan["source"] is None
    assert (
        ci_reuse.project_reuse(
            repo_root=harness.root,
            context=harness.target_context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=plan,
            job_id="test-pr",
            matrix_value="3.13",
            coverage_output=None,
        )
        == "executed"
    )


def test_mapping_reuse_new_pending_source_selects_ordinary_plan(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    harness.source_run["pull_requests"][0]["base"]["sha"] = "d" * 40
    harness.add_run(103, harness.material, complete=False)
    plan = ci_reuse.plan_reuse(
        repo_root=harness.root,
        context=harness.target_context,
        run=harness.target_run,
        token="opaque-test-token",
        checkout_sha=harness.synthetic_head,
    )
    assert plan["mode"] == "executed"
    assert plan["reason"] == "latest_source_not_completed"
    assert plan["source"] is None


def test_mapping_reuse_final_verifier_refreshes_source_after_successful_projection(
    native_reuse: _NativeReuseHarness,
) -> None:
    assert native_reuse.project() == "reused"
    native_reuse.target_manifest()
    native_reuse.add_run(103, native_reuse.material, complete=False)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse.verify_current_reuse(
            repo_root=native_reuse.root,
            repository="owner/repo",
            pr_number=42,
            token="opaque-test-token",
        )


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b"\xff", b"{"])
def test_mapping_reuse_rejects_malformed_duplicate_and_nonfinite_json(raw: bytes) -> None:
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._json(raw)


@pytest.mark.parametrize(
    "member,mode",
    [
        ("../coverage.xml", stat.S_IFREG | 0o600),
        ("coverage.xml", stat.S_IFLNK | 0o777),
        ("coverage.xml/", stat.S_IFDIR | 0o700),
    ],
)
def test_mapping_reuse_zip_rejects_traversal_links_and_directories(member: str, mode: int) -> None:
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._zip_member(
            _reuse_zip(member, b"content", unix_mode=mode),
            expected_member="coverage.xml",
            limit=100,
        )


def test_mapping_reuse_zip_rejects_duplicates_and_expansion_budget() -> None:
    destination = io.BytesIO()
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("coverage.xml", b"one")
        archive.writestr("unexpected.xml", b"two")
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._zip_member(destination.getvalue(), expected_member="coverage.xml", limit=100)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._zip_member(
            _reuse_zip("coverage.xml", b"too large"), expected_member="coverage.xml", limit=2
        )
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._zip_member(b"not ZIP", expected_member="coverage.xml", limit=100)


@pytest.mark.parametrize(
    "raw",
    [
        b'<coverage lines-valid="1" lines-covered="2" line-rate="1"/>',
        b'<coverage lines-valid="x" lines-covered="0" line-rate="0"/>',
        b'<coverage lines-valid="1" lines-covered="0" line-rate="NaN"/>',
        b"<html/>",
        b'<!DOCTYPE coverage [<!ENTITY x SYSTEM "file:///etc/passwd">]><coverage>&x;</coverage>',
    ],
)
def test_mapping_reuse_coverage_xml_rejects_unsafe_or_invalid_counts(raw: bytes) -> None:
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._coverage_xml(raw)


def test_mapping_reuse_local_writer_rejects_symlink_parent_and_divergent_replay(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.xml"
    ci_reuse._safe_write(target, b"exact")
    ci_reuse._safe_write(target, b"exact")
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._safe_write(target, b"other")
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._safe_write(link / "escape.xml", b"unsafe")
    file_link = tmp_path / "file-link.xml"
    file_link.symlink_to(target)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._safe_read(file_link, 100)


@pytest.mark.parametrize(
    "raw",
    [
        b"jobs: {test-pr: 1, test-pr: 2}",
        b"jobs: &anchor {test-pr: 1}\ncopy: *anchor",
        b"!!python/object:os.system {}",
        b"jobs: [",
    ],
)
def test_mapping_reuse_yaml_is_safe_closed_and_rejects_ambiguous_structures(raw: bytes) -> None:
    with pytest.raises(ci_reuse.Ineligible):
        ci_reuse._yaml(raw)


def test_mapping_reuse_native_api_pagination_rejects_incomplete_or_duplicate_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reuse_identity, "github_api_request", lambda *args, **kwargs: {"total_count": 2, "jobs": []}
    )
    with pytest.raises(ci_reuse.ReuseError, match="incomplete"):
        ci_reuse._pages("owner/repo", "actions/runs/101/jobs", "jobs", "opaque-test-token")
    monkeypatch.setattr(
        reuse_identity,
        "github_api_request",
        lambda *args, **kwargs: {"total_count": 2, "jobs": [{"id": 1}, {"id": 1}]},
    )
    with pytest.raises(ci_reuse.ReuseError, match="duplicate"):
        ci_reuse._pages("owner/repo", "actions/runs/101/jobs", "jobs", "opaque-test-token")


class _ArtifactHttpResponse:
    def __init__(
        self, status: int, raw: bytes = b"", headers: dict[str, str] | None = None
    ) -> None:
        self.status = status
        self.raw = io.BytesIO(raw)
        self.headers = headers or {}

    def getheader(self, name: str) -> str | None:
        return self.headers.get(name)

    def read1(self, size: int) -> bytes:
        return self.raw.read(size)


class _ArtifactHttpConnection:
    responses: list[_ArtifactHttpResponse] = []
    requests: list[dict[str, Any]] = []
    closes = 0

    def __init__(self, host: str, timeout: float) -> None:
        self.host = host
        self.timeout = timeout

    def request(self, *, method: str, url: str, headers: dict[str, str]) -> None:
        self.requests.append(
            {
                "host": self.host,
                "timeout": self.timeout,
                "method": method,
                "url": url,
                "headers": headers,
            }
        )

    def getresponse(self) -> _ArtifactHttpResponse:
        return self.responses.pop(0)

    def close(self) -> None:
        type(self).closes += 1


@pytest.fixture
def artifact_http(monkeypatch: pytest.MonkeyPatch) -> type[_ArtifactHttpConnection]:
    _ArtifactHttpConnection.responses = []
    _ArtifactHttpConnection.requests = []
    _ArtifactHttpConnection.closes = 0
    monkeypatch.setattr(reuse_identity.http.client, "HTTPSConnection", _ArtifactHttpConnection)
    return _ArtifactHttpConnection


def test_native_artifact_transport_302_strips_authorization_and_cookies(
    artifact_http: type[_ArtifactHttpConnection],
) -> None:
    artifact_http.responses = [
        _ArtifactHttpResponse(
            302,
            headers={
                "Location": "https://production-resultstore-fixture.blob.core.windows.net/artifacts/test.zip?opaque=signed"
            },
        ),
        _ArtifactHttpResponse(200, b"ZIP", {"Content-Length": "3"}),
    ]
    assert (
        reuse_identity.github_artifact_download(
            "https://api.github.com/repos/owner/repo/actions/artifacts/42/zip",
            token="opaque-test-token",
            max_bytes=10,
        )
        == b"ZIP"
    )
    assert artifact_http.requests[0]["headers"]["Authorization"] == "Bearer opaque-test-token"
    assert "Authorization" not in artifact_http.requests[1]["headers"]
    assert all("Cookie" not in request["headers"] for request in artifact_http.requests)
    assert artifact_http.requests[1]["url"].endswith("?opaque=signed")
    assert artifact_http.closes == 2


@pytest.mark.parametrize(
    "location",
    [
        "http://production-resultstore-fixture.blob.core.windows.net/test.zip",
        urllib.parse.urlunsplit(
            (
                "https",
                ":".join(("fixture", "opaque"))
                + "@production-resultstore-fixture.blob.core.windows.net",
                "/test.zip",
                "",
                "",
            )
        ),
        urllib.parse.urlunsplit(
            (
                "https",
                "fixture@production-resultstore-fixture.blob.core.windows.net",
                "/test.zip",
                "",
                "",
            )
        ),
        urllib.parse.urlunsplit(
            (
                "https",
                ":opaque@production-resultstore-fixture.blob.core.windows.net",
                "/test.zip",
                "",
                "",
            )
        ),
        "https://production-resultstore-fixture.blob.core.windows.net:444/test.zip",
        "https://api.github.com/repos/other/repo/test.zip",
        "https://127.0.0.1/test.zip",
        "https://host.blob.core.windows.net.attacker.invalid/test.zip",
        "https://host.blob.core.windows.net/test.zip#fragment",
    ],
)
def test_native_artifact_transport_rejects_untrusted_redirects_and_sanitizes_secrets(
    artifact_http: type[_ArtifactHttpConnection], location: str
) -> None:
    artifact_http.responses = [
        _ArtifactHttpResponse(302, b"secret-error-body", {"Location": location})
    ]
    with pytest.raises(reuse_identity.CommitIdentityError) as caught:
        reuse_identity.github_artifact_download(
            "https://api.github.com/repos/owner/repo/actions/artifacts/42/zip",
            token="opaque-secret-token",
            max_bytes=10,
        )
    assert "opaque-secret-token" not in str(caught.value)
    assert location not in str(caught.value)
    assert len(artifact_http.requests) == 1 and artifact_http.closes == 1


@pytest.mark.parametrize(
    "response",
    [
        _ArtifactHttpResponse(200, b"large payload", {"Content-Length": "100"}),
        _ArtifactHttpResponse(200, b"large payload"),
        _ArtifactHttpResponse(200, b"tiny", {"Content-Length": "8"}),
        _ArtifactHttpResponse(200, b"tiny", {"Content-Length": "NaN"}),
        _ArtifactHttpResponse(403, b"secret-error-body"),
    ],
)
def test_native_artifact_transport_rejects_limits_incomplete_reads_and_http_errors(
    artifact_http: type[_ArtifactHttpConnection], response: _ArtifactHttpResponse
) -> None:
    artifact_http.responses = [
        _ArtifactHttpResponse(
            302, headers={"Location": "https://host.blob.core.windows.net/test.zip?secret=signed"}
        ),
        response,
    ]
    with pytest.raises(reuse_identity.CommitIdentityError) as caught:
        reuse_identity.github_artifact_download(
            "https://api.github.com/repos/owner/repo/actions/artifacts/42/zip",
            token="opaque-test-token",
            max_bytes=10,
        )
    assert "secret" not in str(caught.value)
    assert artifact_http.closes == 2


@pytest.mark.parametrize(
    "url,token,budget",
    [
        ("https://api.github.com/repos/owner/repo/actions/artifacts/42/zip?extra=1", "token", 10),
        ("https://api.github.com/repos/owner/repo/actions/artifacts/0/zip", "token", 10),
        ("https://api.github.com/repos/owner/repo/actions/artifacts/42/zip", "bad\ntoken", 10),
        ("https://api.github.com/repos/owner/repo/actions/artifacts/42/zip", "", 10),
        ("https://api.github.com/repos/owner/repo/actions/artifacts/42/zip", "token", True),
        ("https://api.github.com/repos/owner/repo/actions/artifacts/42/zip", "token", 0),
    ],
)
def test_native_artifact_transport_requires_exact_endpoint_token_and_budget(
    artifact_http: type[_ArtifactHttpConnection], url: str, token: str, budget: Any
) -> None:
    with pytest.raises(reuse_identity.CommitIdentityError):
        reuse_identity.github_artifact_download(url, token=token, max_bytes=budget)
    assert not artifact_http.requests


def test_native_artifact_transport_rejects_api_direct_bytes_redirect_loops_and_time_budget(
    artifact_http: type[_ArtifactHttpConnection], monkeypatch: pytest.MonkeyPatch
) -> None:
    endpoint = "https://api.github.com/repos/owner/repo/actions/artifacts/42/zip"
    artifact_http.responses = [_ArtifactHttpResponse(200, b"ZIP")]
    with pytest.raises(reuse_identity.CommitIdentityError, match="native"):
        reuse_identity.github_artifact_download(endpoint, token="token")
    artifact_http.responses = [
        _ArtifactHttpResponse(302, headers={"Location": "https://host.blob.core.windows.net/one"})
        for _ in range(3)
    ]
    with pytest.raises(reuse_identity.CommitIdentityError, match="redirect"):
        reuse_identity.github_artifact_download(endpoint, token="token")
    moments = iter([0.0, 100.0])
    monkeypatch.setattr(reuse_identity.time, "monotonic", lambda: next(moments))
    with pytest.raises(reuse_identity.CommitIdentityError, match="time budget"):
        reuse_identity.github_artifact_download(endpoint, token="token")


@pytest.mark.parametrize("native_reuse", ["backend_ios", "ios_only", "main_matrix"], indirect=True)
def test_mapping_reuse_complete_base_derived_ios_and_literal_matrix_cells(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    for cell in harness.policy.cells:
        output = harness.root / f"coverage-{cell.matrix_value}.xml" if cell.coverage_name else None
        assert (
            ci_reuse.project_reuse(
                repo_root=harness.root,
                context=harness.target_context,
                run=harness.target_run,
                token="opaque-test-token",
                checkout_sha=harness.synthetic_head,
                plan=harness.plan,
                job_id=cell.job_id,
                matrix_value=cell.matrix_value,
                coverage_output=output,
            )
            == "reused"
        )
    manifest = harness.target_manifest()
    assert len(manifest["jobs"]) == len(harness.policy.cells)
    ci_reuse.verify_current_reuse(
        repo_root=harness.root, repository="owner/repo", pr_number=42, token="opaque-test-token"
    )


def test_mapping_reuse_base_authority_and_whole_protected_material_cannot_self_admit(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    harness.git(["checkout", "--detach", harness.head])
    with pytest.raises(ci_reuse.ReuseError, match="BASE checkout"):
        harness.project()
    harness.git(["checkout", "--detach", harness.base])
    (harness.root / ci_reuse.HELPER_PATH).write_text("candidate mutation")
    with pytest.raises(ci_reuse.ReuseError, match="tracked modifications"):
        harness.project()
    harness.git(["checkout", "--", ci_reuse.HELPER_PATH])
    harness.target_manifest()

    def protected(*args: Any, **kwargs: Any) -> ci_reuse.BasePolicy:
        raise ci_reuse.Ineligible("whole_pr_protected_material")

    monkeypatch.setattr(ci_reuse, "_policy", protected)
    with pytest.raises(ci_reuse.ReuseError, match="ineligible whole material"):
        ci_reuse.verify_current_reuse(
            repo_root=harness.root, repository="owner/repo", pr_number=42, token="opaque-test-token"
        )


def test_mapping_reuse_actual_protected_delta_and_absent_capability_publish_nothing(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    harness.git(["checkout", "--detach", harness.material])
    workflow = harness.root / ".github/workflows/ci.yml"
    workflow.write_bytes(workflow.read_bytes() + b"\n# Material producer change\n")
    harness.git(["add", ".github/workflows/ci.yml"])
    harness.git(["commit", "-m", "Protected material fixture"])
    harness.head = harness.git(["rev-parse", "HEAD"]).strip()
    context = harness.context()
    material = reuse_evidence.compute_material_manifest(
        harness.root, base_ref_oid=harness.base, head_ref_oid=harness.head, pr_number=42
    )
    harness.git(["checkout", "--detach", harness.base])
    with pytest.raises(ci_reuse.Ineligible, match="whole_pr_protected"):
        ci_reuse._policy(harness.root, context, material)
    run = harness.add_run(103, harness.head, complete=False)
    plan = ci_reuse._document(context, run, schema=ci_reuse.PLAN_SCHEMA)
    assert (
        ci_reuse.collect_execution(
            repo_root=harness.root,
            context=context,
            run=run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic(harness.head),
            plan=plan,
        )
        is None
    )


def test_mapping_reuse_cli_edited_event_project_collect_and_current_verify(
    native_reuse: _NativeReuseHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness = native_reuse
    event = harness.root / "event.json"
    event.write_text(
        json.dumps(
            {
                "action": "edited",
                "repository": {"full_name": harness.repository},
                "pull_request": {
                    "number": 42,
                    "head": {"sha": harness.head},
                    "base": {"sha": harness.base},
                },
            }
        )
    )
    output = harness.root / "github-output.txt"
    monkeypatch.setenv("GH_TOKEN", "opaque-test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", harness.repository)
    monkeypatch.setenv("GITHUB_SHA", harness.synthetic_head)
    monkeypatch.setenv("GITHUB_RUN_ID", "102")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    common = [
        "--event-path",
        str(event),
        "--repo-root",
        str(harness.root),
        "--github-output",
        str(output),
    ]
    assert ci_reuse.main(["plan", *common]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "reused"
    monkeypatch.setenv("CI_REUSE_PLAN_JSON", json.dumps(plan))
    assert (
        ci_reuse.main(
            [
                "project",
                *common,
                "--job-id",
                "test-pr",
                "--matrix-value",
                "3.13",
                "--coverage-output",
                str(harness.root / "coverage.xml"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["mode"] == "reused"
    harness.add_jobs(harness.target_run, harness.policy, reused=True)
    manifest_path = harness.root / "ci-test-execution.json"
    assert ci_reuse.main(["collect", *common, "--output", str(manifest_path)]) == 0
    assert json.loads(capsys.readouterr().out)["publish"] is True
    manifest = json.loads(manifest_path.read_text())
    harness.add_artifact(
        harness.target_run,
        harness.writer(harness.target_run),
        ci_reuse.WRITER_UPLOAD,
        "ci-test-execution-102-1",
        "ci-test-execution.json",
        ci_reuse._canonical(manifest),
    )
    assert (
        ci_reuse.main(
            [
                "verify-current",
                "--repo-root",
                str(harness.root),
                "--repo",
                harness.repository,
                "--pr-number",
                "42",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["verified"] is True
    assert "mode=reused\n" in output.read_text() and "publish=true\n" in output.read_text()
    monkeypatch.setenv("CI_REUSE_PLAN_JSON", '{"mode":"reused","unexpected":"opaque"}')
    assert ci_reuse.main(["project", *common, "--job-id", "test-pr"]) == 1
    captured = capsys.readouterr()
    assert "opaque" not in captured.err


@pytest.mark.parametrize("field", ["baseRefOid", "headRefOid", "commit_oid"])
@pytest.mark.parametrize("value", [int("1" * 40), True, False, None, "A" * 40, " " + "1" * 40])
def test_canonical_pr_graph_rejects_coerced_or_normalized_sha_inputs(
    field: str, value: Any
) -> None:
    pr: dict[str, Any] = {
        "baseRefOid": "1" * 40,
        "headRefOid": "2" * 40,
        "commits": {
            "nodes": [{"commit": {"oid": "2" * 40, "pushedDate": "2026-09-12T10:00:00Z"}}],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        },
    }
    if field == "commit_oid":
        pr["commits"]["nodes"][0]["commit"]["oid"] = value
    else:
        pr[field] = value

    def native_graph(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"data": {"repository": {"pullRequest": pr}}}

    with pytest.raises(reuse_identity.CommitIdentityError, match="lowercase"):
        reuse_identity.fetch_pr_snapshot(
            "owner/repo", 42, token="opaque-test-token", request_json=native_graph
        )


@pytest.mark.parametrize(
    "call,args",
    [
        (ci_reuse._object, (1, "record")),
        (ci_reuse._object, ({1: "value"}, "record")),
        (ci_reuse._positive, (True, "ID")),
        (ci_reuse._positive, ("1", "ID")),
        (ci_reuse._sha, ("A" * 40, "SHA")),
        (ci_reuse._sha, (1, "SHA")),
        (ci_reuse._hash, ("SHA256:" + "a" * 64, "digest")),
        (ci_reuse._time, ("2026-99-99T00:00:00Z", "time")),
        (ci_reuse._time, (True, "time")),
        (ci_reuse._expression, (True,)),
        (ci_reuse._safe_filter, ("!ios/**",)),
        (ci_reuse._safe_filter, ("ios/*",)),
        (ci_reuse._safe_filter, ("ios//**",)),
        (ci_reuse._safe_filter, ("../ios/**",)),
    ],
)
def test_mapping_reuse_scalar_identity_and_closed_filter_boundaries(
    call: Any, args: tuple[Any, ...]
) -> None:
    with pytest.raises(ci_reuse.ReuseError):
        call(*args)


def test_mapping_reuse_json_and_xml_depth_number_and_size_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested = ci_reuse._json(b"[" * 100 + b"0" + b"]" * 100)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._validate_document(nested, schema=ci_reuse.PLAN_SCHEMA)
    native_decoder = ci_reuse.json.loads

    def exhausted_decoder(*args: Any, **kwargs: Any) -> Any:
        raise RecursionError("native decoder budget exhausted")

    monkeypatch.setattr(ci_reuse.json, "loads", exhausted_decoder)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._json(b"{}")
    monkeypatch.setattr(ci_reuse.json, "loads", native_decoder)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._json(b"9" * 5000)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._json(b"{}", limit=1)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._coverage_xml(
            b'<coverage lines-valid="1" lines-covered="1" line-rate="1">'
            + b"<x>" * 129
            + b"</x>" * 129
            + b"</coverage>"
        )
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._coverage_xml(
            b'<coverage lines-valid="99999999999999999" lines-covered="1" line-rate="1"/>'
        )
    with pytest.raises(ci_reuse.Ineligible):
        ci_reuse._yaml(b"[" * 100 + b"0" + b"]" * 100)
    with pytest.raises(ci_reuse.Ineligible):
        ci_reuse._yaml(b"x" * (ci_reuse.MAX_MANIFEST_BYTES + 1))
    with pytest.raises(ci_reuse.Ineligible):
        ci_reuse._yaml(b"[one, two]")


def test_mapping_reuse_native_run_and_job_identity_rejection_boundaries(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    run = deepcopy(harness.source_run)
    mutations = [
        {"repository": None},
        {"repository": {"id": True, "full_name": "owner/repo"}},
        {"head_repository": {"id": 999, "full_name": "owner/repo"}},
        {"event": "push"},
        {"path": "other.yml"},
        {"head_branch": "other"},
        {"pull_requests": []},
        {
            "pull_requests": [
                {"number": 42, "base": {"sha": "f" * 40}, "head": {"sha": harness.material}}
            ]
        },
        {"url": "https://api.github.com/repos/foreign/repo/actions/runs/101"},
    ]
    for mutation in mutations:
        bad = deepcopy(run)
        bad.update(mutation)
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._validate_run(bad, harness.target_context, harness.material)
    job = harness.source_job_rows[0]
    for mutation in (
        {"run_attempt": True},
        {"run_attempt": 2},
        {"check_run_url": "https://api.github.com/repos/foreign/repo/check-runs/1"},
        {"run_id": 999},
        {"workflow_name": "foreign"},
    ):
        bad_job = deepcopy(job)
        bad_job.update(mutation)
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._job_identity(bad_job, harness.target_context, run, "opaque-test-token")
    check = harness.checks[job["id"]]
    for mutation in (
        {"name": "other"},
        {"status": "queued"},
        {"conclusion": "failure"},
        {"app": {"id": 999, "slug": "github-actions"}},
        {"check_suite": {"id": 999}},
    ):
        original = deepcopy(check)
        check.update(mutation)
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._job_identity(job, harness.target_context, run, "opaque-test-token")
        check.clear()
        check.update(original)
    for raw_steps in (
        [{"name": "one", "number": 1}, {"name": "one", "number": 2}],
        [{"name": "one", "number": 1}, {"name": "two", "number": 1}],
        None,
    ):
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._steps({"steps": raw_steps})
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._success_step(
            {"one": {**harness.step("one", 1), "completed_at": "2026-09-12T10:00:00Z"}}, "one"
        )


def test_mapping_reuse_current_attempt_and_full_pr_context_do_not_coerce(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    for value in ("01", "0", "-1", "1.0", "true"):
        monkeypatch.setenv("GITHUB_RUN_ID", value)
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._env_id("GITHUB_RUN_ID")
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._env_id("GITHUB_RUN_ID")
    monkeypatch.setenv("GITHUB_RUN_ID", "102")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    with pytest.raises(ci_reuse.ReuseError, match="attempt changed"):
        ci_reuse._current_run(harness.target_context, "opaque-test-token")
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._context("invalid", 42, "opaque-test-token")
    with pytest.raises(ci_reuse.ReuseError, match="head or base"):
        ci_reuse._context("owner/repo", 42, "opaque-test-token", expected_base="f" * 40)
    original = harness.request(
        f"https://api.github.com/repos/{harness.repository}/pulls/42", token="opaque-test-token"
    )
    for mutation in (
        {"state": "closed"},
        {
            "head": {
                "sha": harness.head,
                "ref": "",
                "repo": {"id": harness.repo_id, "full_name": harness.repository},
            }
        },
        {
            "head": {
                "sha": harness.head,
                "ref": "codex/fixture",
                "repo": {"id": harness.repo_id, "full_name": "foreign/repo"},
            }
        },
    ):
        harness.pr_override = {**deepcopy(original), **mutation}
        with pytest.raises(ci_reuse.ReuseError):
            harness.context()
    harness.pr_override = None


def test_mapping_reuse_whole_tree_refuses_truncation_duplicate_paths_and_invalid_modes(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    tree_sha = harness.git(["rev-parse", f"{harness.synthetic_head}^{{tree}}"]).strip()
    leaf = {"path": "app/planning.py", "sha": "f" * 40, "type": "blob", "mode": "100644"}
    for mutation in (
        {"truncated": True, "tree": [leaf]},
        {"truncated": False, "tree": [leaf, leaf]},
        {"truncated": False, "tree": [{**leaf, "path": "../escape"}]},
        {"truncated": False, "tree": [{**leaf, "mode": "999999"}]},
    ):
        harness.tree_override = {"sha": tree_sha, **mutation}
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._commit_tree(
                harness.target_context,
                harness.synthetic_head,
                tested_head=harness.head,
                token="opaque-test-token",
            )
    harness.tree_override = None


def test_mapping_reuse_base_yaml_universe_unknown_structures_select_ordinary(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    original_blob = ci_reuse._blob
    workflow = yaml.safe_load(original_blob(harness.root, harness.base, ci_reuse.WORKFLOW_PATH))
    material = reuse_evidence.compute_material_manifest(
        harness.root, base_ref_oid=harness.base, head_ref_oid=harness.material, pr_number=42
    )
    mutations: list[tuple[tuple[Any, ...], Any]] = [
        (("name",), "Other"),
        (("jobs", "ci_test_evidence", "name"), "Other"),
        (("jobs", "ci_test_evidence", "steps"), []),
        (("jobs", "ci_test_reuse", "steps", 0, "with", "fetch-depth"), 1),
        (("jobs", "changes", "steps"), None),
        (("env", "PYTHON_VERSION"), 3.13),
        (("jobs", "test-pr", "needs"), None),
        (("jobs", "test-pr", "needs"), ["changes", "changes"]),
        (("jobs", "test-pr", "needs"), ["unknown"]),
        (("jobs", "test-pr", "if"), "always()"),
        (("jobs", "test-pr", "name"), "${{ matrix.unknown }}"),
        (("jobs", "test-pr", "steps"), None),
        (("jobs", "test-pr", "steps", 0, "name"), "Checkout candidate"),
        (("jobs", "test-pr", "strategy", "matrix"), {"python-version": ["3.12"]}),
        (("jobs", "test-main", "strategy", "matrix"), {"include": []}),
        (
            ("jobs", "test-main", "strategy", "matrix"),
            {"include": [{"python-version": ["3.13"], "timeout-minutes": 90}]},
        ),
        (
            ("jobs", "test-main", "strategy", "matrix"),
            {"include": [{"python-version": "latest", "timeout-minutes": 90}]},
        ),
        (
            ("jobs", "test-main", "strategy", "matrix"),
            {
                "include": [
                    {"python-version": "3.13", "timeout-minutes": 90},
                    {"python-version": "3.13", "timeout-minutes": 90},
                ]
            },
        ),
        (("jobs", "ios-tests", "strategy"), {"matrix": {"unknown": [1]}}),
    ]
    for path, replacement in mutations:
        candidate = deepcopy(workflow)
        cursor = candidate
        for part in path[:-1]:
            cursor = cursor[part]
        cursor[path[-1]] = replacement
        raw = yaml.safe_dump(candidate).encode()

        def mutated_blob(root: Path, ref: str, name: str) -> bytes:
            return raw if name == ci_reuse.WORKFLOW_PATH else original_blob(root, ref, name)

        monkeypatch.setattr(ci_reuse, "_blob", mutated_blob)
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._policy(harness.root, harness.target_context, material)
    monkeypatch.setattr(ci_reuse, "_blob", original_blob)


def test_mapping_reuse_native_artifact_metadata_and_safe_io_rejection_boundaries(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    artifact = harness.artifacts[101][0]
    producer = harness.source_job_rows[0]
    for mutation in (
        {"expired": True},
        {"url": "https://api.github.com/repos/foreign/repo/actions/artifacts/1"},
        {"archive_download_url": "https://other.invalid/archive"},
        {
            "workflow_run": {
                "id": 101,
                "repository_id": True,
                "head_repository_id": harness.repo_id,
                "head_sha": harness.material,
            }
        },
        {"size_in_bytes": ci_reuse.MAX_ARCHIVE_BYTES + 1},
        {"updated_at": "2020-01-01T00:00:00Z"},
    ):
        metadata = {**deepcopy(artifact), **mutation}
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._artifact_metadata(
                harness.target_context,
                harness.source_run,
                metadata,
                name=artifact["name"],
                producer=producer,
                upload_step=ci_reuse.UPLOAD_PR,
            )
    target = harness.root / "bounded.json"
    target.write_bytes(b"large")
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._safe_read(target, 1)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._safe_read(harness.root / "missing", 100)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._safe_read(harness.root, 100)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._open_parent(harness.root / ".." / "escape")
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._output(target, {"mode": "reused\nforged=true"})
    ci_reuse._output(None, {"mode": "reused"})


def test_mapping_reuse_document_and_projection_cell_malformed_boundaries(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    for mutation in (
        {"schema_version": "other"},
        {"mode": "neutral"},
        {"mode": []},
        {"mode": {}},
        {"fingerprint": "sha256:" + "0" * 64},
        {"run": {"run_id": 102}},
        {"run": {**harness.plan["run"], "run_attempt": True}},
        {"run": {**harness.plan["run"], "head_sha": "f" * 40}},
        {"idempotency_key": "other"},
        {"universe": {}},
        {"reason": "forged\noutput"},
        {"source": None},
    ):
        document = {**deepcopy(harness.plan), **mutation}
        if "fingerprint" not in mutation:
            document = ci_reuse._finish_document(document)
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._validate_document(document, schema=ci_reuse.PLAN_SCHEMA)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse.project_reuse(
            repo_root=harness.root,
            context=harness.target_context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=harness.plan,
            job_id="test-main",
            matrix_value="3.14",
            coverage_output=None,
        )
    with pytest.raises(ci_reuse.ReuseError, match="requires a safe output"):
        ci_reuse.project_reuse(
            repo_root=harness.root,
            context=harness.target_context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=harness.plan,
            job_id="test-pr",
            matrix_value="3.13",
            coverage_output=None,
        )
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._coverage_rows(
            harness.target_context,
            harness.source_run,
            [(harness.policy.cells[0], harness.source_job_rows[0], "executed")],
            "opaque-test-token",
            asserted=[],
        )
    selected = [(harness.policy.cells[0], harness.source_job_rows[0], "executed")]
    original = deepcopy(harness.source_manifest["jobs"][0])
    for mutation in ({"mode": "reused"}, {"coverage": None}, {"native_job_id": 99}):
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._coverage_rows(
                harness.target_context,
                harness.source_run,
                selected,
                "opaque-test-token",
                asserted=[{**original, **mutation}],
            )


def test_mapping_reuse_final_metadata_refresh_and_replayed_coverage_are_immutable(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    writer_artifact = harness.source_artifact
    coverage_id = harness.artifacts[101][0]["id"]

    def expire_previous_artifact(artifact_id: int) -> None:
        if artifact_id == coverage_id:
            writer_artifact["expires_at"] = "2020-01-01T00:00:00Z"

    harness.download_hook = expire_previous_artifact
    with pytest.raises(ci_reuse.ReuseError, match="expired"):
        harness.project()
    writer_artifact["expires_at"] = "2099-09-12T11:00:10Z"
    harness.download_hook = None
    harness.add_jobs(harness.target_run, harness.policy, reused=True)
    target_coverage = harness.artifacts[102][0]
    changed_xml = (
        b'<coverage lines-valid="11" lines-covered="11" line-rate="1"><packages/></coverage>'
    )
    archive = _reuse_zip("coverage.xml", changed_xml)
    target_coverage["digest"] = ci_reuse._digest(archive)
    target_coverage["size_in_bytes"] = len(archive)
    harness.archives[target_coverage["id"]] = archive
    with pytest.raises(ci_reuse.ReuseError, match="authenticated direct source"):
        ci_reuse.collect_execution(
            repo_root=harness.root,
            context=harness.target_context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=harness.plan,
        )


def test_mapping_reuse_native_step_order_and_missing_current_aggregate_are_blocking(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    job = harness.source_job_rows[0]
    smoke = next(step for step in job["steps"] if step["name"].startswith("Critical smoke"))
    finalize = next(step for step in job["steps"] if step["name"] == "Finalize coverage artifacts")
    smoke["number"], finalize["number"] = finalize["number"], smoke["number"]
    with pytest.raises(ci_reuse.ReuseError, match="out of order"):
        harness.project()
    smoke["number"], finalize["number"] = finalize["number"], smoke["number"]
    harness.add_jobs(harness.target_run, harness.policy, reused=True)
    with pytest.raises(ci_reuse.ReuseError, match="attempt_specific_artifact_absent"):
        ci_reuse.verify_current_reuse(
            repo_root=harness.root, repository="owner/repo", pr_number=42, token="opaque-test-token"
        )


def test_mapping_reuse_target_seal_requires_current_provider_neutral_recognizers(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    monkeypatch.setattr(
        reuse_evidence, "is_provider_no_claim_review_receipt", lambda receipt: False
    )
    with pytest.raises(ci_reuse.ReuseError):
        harness.project()


def test_native_artifact_transport_read_time_and_network_failure_are_sanitized(
    artifact_http: type[_ArtifactHttpConnection], monkeypatch: pytest.MonkeyPatch
) -> None:
    endpoint = "https://api.github.com/repos/owner/repo/actions/artifacts/42/zip"
    artifact_http.responses = [
        _ArtifactHttpResponse(
            302, headers={"Location": "https://host.blob.core.windows.net/archive"}
        ),
        _ArtifactHttpResponse(200, b"body"),
    ]
    moments = iter([0.0, 1.0, 2.0, 100.0])
    monkeypatch.setattr(reuse_identity.time, "monotonic", lambda: next(moments))
    with pytest.raises(reuse_identity.CommitIdentityError, match="time budget"):
        reuse_identity.github_artifact_download(endpoint, token="opaque-secret-token")
    monkeypatch.setattr(reuse_identity.time, "monotonic", lambda: 0.0)

    def failed_request(self: _ArtifactHttpConnection, **kwargs: Any) -> None:
        raise OSError("opaque-secret-token")

    monkeypatch.setattr(_ArtifactHttpConnection, "request", failed_request)
    with pytest.raises(reuse_identity.CommitIdentityError) as caught:
        reuse_identity.github_artifact_download(endpoint, token="opaque-secret-token")
    assert "opaque-secret-token" not in str(caught.value)


@pytest.mark.parametrize("native_reuse", ["backend_ios"], indirect=True)
def test_mapping_reuse_matching_ios_path_does_not_hide_unknown_later_filter(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    native_blob = ci_reuse._blob
    workflow = yaml.safe_load(native_blob(harness.root, harness.base, ci_reuse.WORKFLOW_PATH))
    step = next(step for step in workflow["jobs"]["changes"]["steps"] if step.get("id") == "filter")
    filters = yaml.safe_load(step["with"]["filters"])
    filters["ios"].append("ios/*")
    step["with"]["filters"] = yaml.safe_dump(filters)
    mutated = yaml.safe_dump(workflow).encode()
    monkeypatch.setattr(
        ci_reuse,
        "_blob",
        lambda root, ref, path: (
            mutated if path == ci_reuse.WORKFLOW_PATH else native_blob(root, ref, path)
        ),
    )
    material = reuse_evidence.compute_material_manifest(
        harness.root, base_ref_oid=harness.base, head_ref_oid=harness.material, pr_number=42
    )
    with pytest.raises(ci_reuse.Ineligible, match="ios_filter"):
        ci_reuse._policy(harness.root, harness.target_context, material)


def test_mapping_reuse_serializer_failures_are_bounded_local_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._canonical({"value": float("nan")})
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._canonical({"value": object()})

    def exhausted_encoder(*args: Any, **kwargs: Any) -> Any:
        raise RecursionError("native encoder budget exhausted")

    monkeypatch.setattr(ci_reuse.json, "dumps", exhausted_encoder)
    with pytest.raises(ci_reuse.ReuseError):
        ci_reuse._canonical({})


def test_mapping_reuse_cli_ordinary_collect_and_missing_flags_preserve_execution(
    native_reuse: _NativeReuseHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness = native_reuse
    event = harness.root / "event.json"
    event.write_text(
        json.dumps(
            {
                "repository": {"full_name": harness.repository},
                "pull_request": {
                    "number": 42,
                    "head": {"sha": harness.head},
                    "base": {"sha": harness.base},
                },
            }
        )
    )
    monkeypatch.setenv("GH_TOKEN", "opaque-test-token")
    monkeypatch.setenv("GITHUB_SHA", harness.synthetic_head)
    monkeypatch.setenv("GITHUB_RUN_ID", "102")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.delenv("CI_REUSE_PLAN_JSON", raising=False)
    common = ["--event-path", str(event), "--repo-root", str(harness.root)]
    assert ci_reuse.main(["verify-current", "--repo", harness.repository]) == 1
    assert ci_reuse.main(["plan"]) == 1
    assert ci_reuse.main(["project", *common, "--job-id", "test-pr"]) == 1
    plan = ci_reuse._document(
        harness.target_context, harness.target_run, schema=ci_reuse.PLAN_SCHEMA
    )
    monkeypatch.setenv("CI_REUSE_PLAN_JSON", json.dumps(plan))
    assert ci_reuse.main(["project", *common]) == 1
    assert ci_reuse.main(["collect", *common]) == 1
    harness.add_jobs(harness.target_run, harness.policy, reused=False)
    manifest_path = harness.root / "ordinary-execution.json"
    assert ci_reuse.main(["collect", *common, "--output", str(manifest_path)]) == 0
    manifest = json.loads(manifest_path.read_text())
    assert manifest["mode"] == "executed" and manifest["source"] is None
    harness.add_artifact(
        harness.target_run,
        harness.writer(harness.target_run),
        ci_reuse.WRITER_UPLOAD,
        "ci-test-execution-102-1",
        "ci-test-execution.json",
        ci_reuse._canonical(manifest),
    )
    ci_reuse.verify_current_reuse(
        repo_root=harness.root,
        repository=harness.repository,
        pr_number=42,
        token="opaque-test-token",
    )
    assert "opaque-test-token" not in capsys.readouterr().err


def test_mapping_reuse_git_mapping_symlink_mode_cannot_carry_valid_seal_text(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    mapping = "docs/review/PR_42_FIXED_MAPPING.md"
    blob = harness.git(["rev-parse", f"{harness.head}:{mapping}"]).strip()
    harness.git(["checkout", "--detach", harness.material])
    # Index-only Git fixture: no unsafe filesystem symlink is constructed.
    harness.git(["update-index", "--add", "--cacheinfo", f"120000,{blob},{mapping}"])
    harness.git(["commit", "-m", "Symlink-shaped mapping fixture"])
    harness.head = harness.git(["rev-parse", "HEAD"]).strip()
    context = harness.context()
    harness.git(["checkout", "--detach", harness.base])
    with pytest.raises(ci_reuse.Ineligible, match="canonical_seal_unavailable"):
        ci_reuse._material(harness.root, context, successor=True)


def test_mapping_reuse_older_run_rerun_is_latest_activity_and_never_searches_older_success(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    first = deepcopy(harness.source_run)
    newer = harness.add_run(103, harness.material, complete=True)
    first["run_attempt"] = 2
    first["run_started_at"] = "2026-09-12T12:00:00Z"
    first["status"] = "queued"
    first["conclusion"] = None
    harness.runs[101] = first
    latest = ci_reuse._latest_run(harness.target_context, harness.material, "opaque-test-token")
    assert latest is not None and (latest["id"], latest["run_attempt"]) == (101, 2)
    ordinary = ci_reuse.plan_reuse(
        repo_root=harness.root,
        context=harness.target_context,
        run=harness.target_run,
        token="opaque-test-token",
        checkout_sha=harness.synthetic_head,
    )
    assert ordinary["mode"] == "executed"
    with pytest.raises(ci_reuse.ReuseError):
        harness.project()
    first["status"] = "completed"
    first["conclusion"] = "failure"
    latest = ci_reuse._latest_run(harness.target_context, harness.material, "opaque-test-token")
    assert latest is not None and latest["id"] == 101
    # Completion of an old long run does not outrank a newer attempt start.
    first["run_started_at"] = "2026-09-12T10:01:00Z"
    first["updated_at"] = "2026-09-12T13:00:00Z"
    latest = ci_reuse._latest_run(harness.target_context, harness.material, "opaque-test-token")
    assert latest is not None and latest["id"] == newer["id"]
    first["run_started_at"] = newer["run_started_at"]
    with pytest.raises(ci_reuse.Ineligible, match="order_ambiguous"):
        ci_reuse._latest_run(harness.target_context, harness.material, "opaque-test-token")


def test_mapping_reuse_closed_job_writer_runner_and_checkout_shapes_reject_extensions(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    native_blob = ci_reuse._blob
    workflow = yaml.safe_load(native_blob(harness.root, harness.base, ci_reuse.WORKFLOW_PATH))
    material = reuse_evidence.compute_material_manifest(
        harness.root, base_ref_oid=harness.base, head_ref_oid=harness.material, pr_number=42
    )
    variants: list[dict[str, Any]] = []
    for job_id in (
        "ci_test_reuse",
        "ci_test_evidence",
        "test-pr",
        "test-main",
        "ios-tests",
        "ios-ui-smoke",
    ):
        for key, value in (
            ("container", {"image": "untrusted"}),
            ("services", {"db": {"image": "untrusted"}}),
            ("uses", "other/workflow.yml"),
            ("runs-on", "self-hosted"),
        ):
            modified = deepcopy(workflow)
            modified["jobs"][job_id][key] = value
            variants.append(modified)
    modified = deepcopy(workflow)
    modified["jobs"]["ci_test_evidence"]["steps"].insert(
        1, {"name": "Unknown startup", "run": "execute candidate"}
    )
    variants.append(modified)
    modified = deepcopy(workflow)
    modified["jobs"]["ci_test_reuse"]["steps"][0]["with"]["repository"] = "foreign/repo"
    variants.append(modified)
    modified = deepcopy(workflow)
    modified["jobs"]["test-pr"]["steps"][0]["with"]["path"] = "candidate"
    variants.append(modified)
    for variant in variants:
        raw = yaml.safe_dump(variant).encode()
        monkeypatch.setattr(
            ci_reuse,
            "_blob",
            lambda root, ref, path: (
                raw if path == ci_reuse.WORKFLOW_PATH else native_blob(root, ref, path)
            ),
        )
        with pytest.raises(ci_reuse.ReuseError):
            ci_reuse._policy(harness.root, harness.target_context, material)
    monkeypatch.setattr(ci_reuse, "_blob", native_blob)


def _authenticate_native_fork(harness: _NativeReuseHarness) -> ci_reuse.Context:
    pr = harness.request(
        f"https://api.github.com/repos/{harness.repository}/pulls/42", token="opaque-test-token"
    )
    fork = {"id": 68, "full_name": "contributor/repo", "fork": True}
    pr["head"]["repo"] = fork
    harness.pr_override = pr
    harness.target_run["head_repository"] = deepcopy(fork)
    context = harness.context()
    assert context.is_fork
    return context


def test_mapping_reuse_authenticated_fork_cli_control_executes_normally_without_manifest(
    native_reuse: _NativeReuseHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness = native_reuse
    context = _authenticate_native_fork(harness)
    event = harness.root / "fork-event.json"
    event.write_text(
        json.dumps(
            {
                "action": "opened",
                "repository": {"full_name": harness.repository},
                "pull_request": {
                    "number": 42,
                    "head": {"sha": harness.head},
                    "base": {"sha": harness.base},
                },
            }
        )
    )
    output = harness.root / "fork-github-output.txt"
    monkeypatch.setenv("GH_TOKEN", "opaque-test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", harness.repository)
    monkeypatch.setenv("GITHUB_RUN_ID", "102")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", harness.synthetic_head)
    common = [
        "--event-path",
        str(event),
        "--repo-root",
        str(harness.root),
        "--github-output",
        str(output),
    ]
    # Ordinary-only forks must not need local fork commit objects, a seal,
    # material derivation or any source evidence to let native tests start.
    native_ensure = ci_reuse._ensure_git
    ensured: list[str] = []

    def base_only_objects(root: Path, sha: str) -> None:
        ensured.append(sha)
        assert sha == harness.base
        native_ensure(root, sha)

    monkeypatch.setattr(ci_reuse, "_ensure_git", base_only_objects)
    assert ci_reuse.main(["plan", *common]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "executed" and plan["reason"] == "fork_pr_ordinary_only"
    assert plan["source"] is None and plan["upstream_assets"] == []
    assert (
        plan["repository"],
        plan["repository_id"],
        plan["pr_number"],
        plan["head_sha"],
        plan["base_sha"],
        plan["run"]["run_id"],
    ) == (harness.repository, 66, 42, harness.head, harness.base, 102)
    assert plan["checkout_sha"] == harness.synthetic_head
    assert set(ensured) == {harness.base}
    workflow = _load_ci_workflow_jobs()
    for job_id in ci_reuse.CRITICAL_STEPS:
        direct = next(step for step in workflow[job_id]["steps"] if step.get("name") == "Checkout")
        verifier = next(
            step for step in workflow[job_id]["steps"] if step.get("name") == ci_reuse.VERIFY_STEP
        )
        assert direct["if"] == "steps.ci_reuse.outputs.mode != 'reused'"
        assert "needs.ci_test_reuse.outputs.mode == 'reused'" in verifier["if"]
    monkeypatch.setenv("CI_REUSE_PLAN_JSON", json.dumps(plan))
    assert ci_reuse.main(["project", *common, "--job-id", "test-pr", "--matrix-value", "3.13"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "executed"
    harness.add_jobs(harness.target_run, harness.policy, reused=False)
    manifest = harness.root / "fork-substitution.json"
    assert ci_reuse.main(["collect", *common, "--output", str(manifest)]) == 0
    assert json.loads(capsys.readouterr().out)["publish"] is False
    assert not manifest.exists()
    assert (
        ci_reuse.main(
            [
                "verify-current",
                "--repo-root",
                str(harness.root),
                "--repo",
                harness.repository,
                "--pr-number",
                "42",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["verified"] is True
    assert "mode=executed\n" in output.read_text() and "publish=false\n" in output.read_text()
    ci_reuse.verify_current_reuse(
        repo_root=harness.root,
        repository=harness.repository,
        pr_number=42,
        token="opaque-test-token",
        expected_head_sha=context.head_sha,
        expected_base_sha=context.base_sha,
    )


def test_mapping_reuse_authenticated_fork_never_accepts_asserted_plan_or_native_claim(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    context = _authenticate_native_fork(harness)
    with pytest.raises(ci_reuse.ReuseError, match="fork PR"):
        ci_reuse.project_reuse(
            repo_root=harness.root,
            context=context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=harness.plan,
            job_id="test-pr",
            matrix_value="3.13",
            coverage_output=None,
        )
    with pytest.raises(ci_reuse.ReuseError, match="ordinary-only plan"):
        ci_reuse.collect_execution(
            repo_root=harness.root,
            context=context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=harness.plan,
        )
    with pytest.raises(ci_reuse.ReuseError, match="fork PR"):
        ci_reuse._source(
            context,
            reuse_evidence.compute_material_manifest(
                harness.root, base_ref_oid=harness.base, head_ref_oid=harness.material, pr_number=42
            ),
            harness.material,
            harness.policy,
            "opaque-test-token",
            target_tree_digest=harness.plan["merge_tree_digest"],
        )
    harness.add_jobs(harness.target_run, harness.policy, reused=True)
    with pytest.raises(ci_reuse.ReuseError, match="native test reuse claim"):
        ci_reuse.verify_current_reuse(
            repo_root=harness.root,
            repository=harness.repository,
            pr_number=42,
            token="opaque-test-token",
        )


def test_mapping_reuse_fork_substitution_publication_and_foreign_base_are_rejected(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    _authenticate_native_fork(harness)
    harness.add_jobs(harness.target_run, harness.policy, reused=False)
    harness.add_artifact(
        harness.target_run,
        harness.writer(harness.target_run),
        ci_reuse.WRITER_UPLOAD,
        "ci-test-execution-102-1",
        "ci-test-execution.json",
        b"{}",
    )
    with pytest.raises(ci_reuse.ReuseError, match="cannot publish substitution evidence"):
        ci_reuse.verify_current_reuse(
            repo_root=harness.root,
            repository=harness.repository,
            pr_number=42,
            token="opaque-test-token",
        )
    assert harness.pr_override is not None
    harness.pr_override["base"]["repo"]["full_name"] = "foreign/repo"
    with pytest.raises(ci_reuse.ReuseError, match="canonical BASE"):
        harness.context()


@pytest.mark.parametrize("native_reuse", ["main_matrix"], indirect=True)
def test_mapping_reuse_derives_python_and_timeout_parameters_from_base(
    native_reuse: _NativeReuseHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = native_reuse
    native_blob = ci_reuse._blob
    workflow = yaml.safe_load(native_blob(harness.root, harness.base, ci_reuse.WORKFLOW_PATH))
    workflow["env"]["PYTHON_VERSION"] = "3.14.1"
    workflow["jobs"]["test-pr"]["strategy"]["matrix"] = {"python-version": ["3.14"]}
    workflow["jobs"]["test-main"]["strategy"]["matrix"] = {
        "include": [
            {"python-version": "3.10.17", "timeout-minutes": 55},
            {"python-version": "3.14", "timeout-minutes": 120},
        ]
    }
    for job_id in ("ci_test_reuse", "ci_test_evidence", "test-pr", "ios-ui-smoke"):
        workflow["jobs"][job_id]["timeout-minutes"] = 45
    workflow["jobs"]["ios-tests"][
        "timeout-minutes"
    ] = "${{ fromJSON(vars.IOS_TESTS_JOB_TIMEOUT_MINUTES || '75') }}"
    raw = yaml.safe_dump(workflow).encode()
    monkeypatch.setattr(
        ci_reuse,
        "_blob",
        lambda root, ref, path: (
            raw if path == ci_reuse.WORKFLOW_PATH else native_blob(root, ref, path)
        ),
    )
    material = reuse_evidence.compute_material_manifest(
        harness.root, base_ref_oid=harness.base, head_ref_oid=harness.material, pr_number=42
    )
    policy = ci_reuse._policy(harness.root, harness.target_context, material)
    assert {cell.check_name for cell in policy.cells} == {
        "test-pr (3.14)",
        "test-main (3.10.17, 55)",
        "test-main (3.14, 120)",
    }
    assert policy.cells[0].coverage_name == "coverage-xml-3.14.1"
    assert policy.config_digest != harness.policy.config_digest
    for invalid in (
        0,
        True,
        181,
        "${{ fromJSON(vars.IOS_TESTS_JOB_TIMEOUT_MINUTES || '0') }}",
        "${{ arbitrary() }}",
    ):
        definition = deepcopy(workflow["jobs"]["ios-tests"])
        definition["timeout-minutes"] = invalid
        with pytest.raises(ci_reuse.Ineligible):
            ci_reuse._job_shape("ios-tests", definition)


def test_mapping_reuse_stale_pr_snapshot_executes_without_source_publication(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    harness.target_manifest()
    ci_reuse.verify_current_reuse(
        repo_root=harness.root,
        repository=harness.repository,
        pr_number=42,
        token="opaque-test-token",
    )
    harness.native_base_sha = harness.material
    context = harness.context()
    assert context.base_sha == harness.base and context.current_base_sha == harness.material
    plan = ci_reuse.plan_reuse(
        repo_root=harness.root,
        context=context,
        run=harness.target_run,
        token="opaque-test-token",
        checkout_sha=harness.synthetic_head,
    )
    assert plan["mode"] == "executed" and plan["reason"] == "snapshot_base_behind_native_target"
    assert plan["source"] is None
    assert (
        ci_reuse.collect_execution(
            repo_root=harness.root,
            context=context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=plan,
        )
        is None
    )
    with pytest.raises(ci_reuse.ReuseError, match="no longer independently admissible"):
        ci_reuse.project_reuse(
            repo_root=harness.root,
            context=context,
            run=harness.target_run,
            token="opaque-test-token",
            checkout_sha=harness.synthetic_head,
            plan=harness.plan,
            job_id="test-pr",
            matrix_value="3.13",
            coverage_output=harness.root / "behind-projection.xml",
        )
    with pytest.raises(ci_reuse.ReuseError, match="snapshot_base_behind_native_target"):
        ci_reuse.verify_current_reuse(
            repo_root=harness.root,
            repository=harness.repository,
            pr_number=42,
            token="opaque-test-token",
        )


@pytest.mark.parametrize("change", ["advance", "retarget"])
def test_mapping_reuse_refresh_observes_native_base_change_with_stale_snapshot(
    native_reuse: _NativeReuseHarness, change: str
) -> None:
    harness = native_reuse
    frozen = harness.context()
    if change == "advance":
        harness.native_base_sha = harness.material
    else:
        harness.base_ref = "release/stable"
    with pytest.raises(ci_reuse.ReuseError, match="native PR base ref or target"):
        ci_reuse._refresh(frozen, harness.target_run, "opaque-test-token")
    assert harness.base == frozen.base_sha and harness.head == frozen.head_sha


def test_mapping_reuse_native_base_advance_during_asserted_proof_is_terminal(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse

    def advance(artifact_id: int) -> None:
        harness.native_base_sha = harness.material

    harness.download_hook = advance
    with pytest.raises(ci_reuse.ReuseError, match="native PR base ref or target"):
        harness.project()


@pytest.mark.parametrize("fault", ["missing", "name", "sha", "branch_url", "commit_url"])
def test_mapping_reuse_native_branch_identity_rejects_unusable_evidence(
    native_reuse: _NativeReuseHarness, fault: str
) -> None:
    harness = native_reuse
    branch = {
        "name": harness.base_ref,
        "commit": {
            "sha": harness.base,
            "url": f"https://api.github.com/repos/{harness.repository}/commits/{harness.base}",
        },
        "_links": {"self": f"https://api.github.com/repos/{harness.repository}/branches/main"},
    }
    if fault == "missing":
        harness.native_branch_override = reuse_identity.CommitIdentityError(
            "native branch unavailable"
        )
    elif fault == "name":
        branch["name"] = "other"
    elif fault == "sha":
        branch["commit"]["sha"] = True
    elif fault == "branch_url":
        branch["_links"]["self"] = "https://api.github.com/repos/foreign/repo/branches/main"
    else:
        branch["commit"][
            "url"
        ] = f"https://api.github.com/repos/foreign/repo/commits/{harness.base}"
    if fault != "missing":
        harness.native_branch_override = branch
    with pytest.raises((ci_reuse.ReuseError, reuse_identity.CommitIdentityError)):
        harness.context()


def test_mapping_reuse_native_branch_name_with_slash_is_encoded(
    native_reuse: _NativeReuseHarness,
) -> None:
    harness = native_reuse
    harness.base_ref = "release/stable"
    context = harness.context()
    assert context.base_ref == "release/stable" and context.current_base_sha == harness.base
    assert (
        f"https://api.github.com/repos/{harness.repository}/branches/release%2Fstable"
        in harness.urls
    )
