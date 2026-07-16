from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci import check_pr_merge_readiness as merge_gate
from scripts.ci.check_pr_merge_readiness import _is_actionable, _mapped_urls
from scripts.orchestration.pr_commit_identity import (
    CodexReviewEvidence,
    CommitRefKind,
    PrCommitEvidence,
    PrSnapshot,
    RepositoryCommitRef,
    SecurityOutageOverrideEvidence,
)
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    ReviewEvidenceError,
    build_security_outage_override_receipt,
    compute_material_manifest,
    render_embedded_review_seal,
)


def test_is_actionable_detects_known_markers() -> None:
    body = "Actionable comments posted: 1\nPrompt for AI Agents"
    assert _is_actionable(body) is True


def test_is_actionable_ignores_explicit_no_actionables() -> None:
    body = "No actionable comments were generated in the recent review."
    assert _is_actionable(body) is False


def test_mapped_urls_extracts_review_url_and_no_actionable_marker() -> None:
    pr_body = """
## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/acme/repo/pull/1#discussion_r1 -> abc1234
- No actionable review comments
"""
    urls, has_no_actionable = _mapped_urls(pr_body)
    assert "https://github.com/acme/repo/pull/1#discussion_r1" in urls
    assert has_no_actionable is True


def test_review_summary_is_covered_by_all_mapped_actionable_children() -> None:
    review_id = 4709310816
    summary_url = "https://github.com/owner/repo/pull/42#pullrequestreview-4709310816"
    child_one = "https://github.com/owner/repo/pull/42#discussion_r1"
    child_two = "https://github.com/owner/repo/pull/42#discussion_r2"
    items = [
        merge_gate.ActionableItem(
            author="coderabbitai[bot]",
            url=summary_url,
            created_at="2026-07-16T00:43:28Z",
            kind="review",
            review_id=review_id,
        ),
        merge_gate.ActionableItem(
            author="coderabbitai[bot]",
            url=child_one,
            created_at="2026-07-16T00:43:26Z",
            kind="review_comment",
            review_id=review_id,
        ),
        merge_gate.ActionableItem(
            author="coderabbitai[bot]",
            url=child_two,
            created_at="2026-07-16T00:43:26Z",
            kind="review_comment",
            review_id=review_id,
        ),
    ]

    assert merge_gate._covered_review_summary_urls(items, {child_one, child_two}) == {summary_url}
    assert merge_gate._covered_review_summary_urls(items, {child_one}) == set()


def test_standalone_actionable_review_summary_still_requires_mapping() -> None:
    summary = merge_gate.ActionableItem(
        author="reviewer[bot]",
        url="https://github.com/owner/repo/pull/42#pullrequestreview-7",
        created_at="2026-07-16T00:43:28Z",
        kind="review",
        review_id=7,
    )

    assert merge_gate._covered_review_summary_urls([summary], set()) == set()


def test_review_seal_rollout_boundary_is_explicit_and_self_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(merge_gate, "REVIEW_SEAL_REQUIRED_FROM_PR", 100)
    assert merge_gate._review_seal_v1_required(99, None) is False
    assert merge_gate._review_seal_v1_required(99, "v1") is True
    assert merge_gate._review_seal_v1_required(100, None) is True

    monkeypatch.setattr(merge_gate, "REVIEW_SEAL_REQUIRED_FROM_PR", None)
    assert merge_gate._review_seal_v1_required(99, "v1") is True
    with pytest.raises(ValueError, match="pending"):
        merge_gate._review_seal_v1_required(99, None)


def test_review_seal_rollout_activates_after_governance_pr() -> None:
    assert merge_gate.REVIEW_SEAL_REQUIRED_FROM_PR == 2142
    assert merge_gate._review_seal_v1_required(2141, None) is False
    assert merge_gate._review_seal_v1_required(2142, None) is True


def test_graphql_unresolved_threads_ignores_ghas_non_conversation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GHAS code-scanning threads are not resolvable conversations and should not block merge."""

    def _fake_api_request(*_args, **_kwargs):
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "isResolved": False,
                                    "isOutdated": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {
                                                    "login": "coderabbitai",
                                                }
                                            }
                                        ]
                                    },
                                },
                                {
                                    "isResolved": False,
                                    "isOutdated": True,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {
                                                    "login": "github-advanced-security",
                                                }
                                            }
                                        ]
                                    },
                                },
                            ],
                        }
                    }
                }
            }
        }

    monkeypatch.setattr(merge_gate, "_api_request", _fake_api_request)
    unresolved = merge_gate._graphql_unresolved_threads(
        repo="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=960,
        token="dummy",
    )

    assert unresolved == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"errors": [{"message": "partial"}], "data": {}},
        {"data": {"repository": None}},
        {"data": {"repository": {"pullRequest": None}}},
    ],
)
def test_graphql_unresolved_threads_fails_closed_for_partial_shapes(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> None:
    monkeypatch.setattr(merge_gate, "_api_request", lambda *_a, **_k: payload)
    with pytest.raises(ValueError):
        merge_gate._graphql_unresolved_threads("owner/repo", 42, "opaque")


def test_graphql_unresolved_threads_rejects_missing_next_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        merge_gate,
        "_api_request",
        lambda *_a, **_k: {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": True, "endCursor": None},
                        }
                    }
                }
            }
        },
    )
    with pytest.raises(ValueError, match="cursor is missing or repeated"):
        merge_gate._graphql_unresolved_threads("owner/repo", 42, "opaque")


def test_rest_pagination_rejects_non_list_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(merge_gate, "_api_request", lambda *_a, **_k: {"message": "oops"})
    with pytest.raises(ValueError, match="non-list"):
        merge_gate._api_request_paginated_list("https://api.github.com/example", "opaque")


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    git = shutil.which("git")
    assert git is not None
    run_env = dict(env or os.environ)
    allowed_git_prefixes = ("GIT_AUTHOR_", "GIT_COMMITTER_")
    for key in tuple(run_env):
        if key.startswith("GIT_") and not key.startswith(allowed_git_prefixes):
            run_env.pop(key)
    result = subprocess.run(
        [git, *args],
        cwd=repo,
        env=run_env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "PulsePlate Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "PulsePlate Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    _git(repo, "add", "-A", env=env)
    _git(repo, "commit", "-m", message, env=env)
    return _git(repo, "rev-parse", "HEAD")


def _receipt(base_sha: str, head_sha: str) -> dict[str, Any]:
    digest = "sha256:" + "a" * 64
    return {
        "artifacts": {
            "coverage_sha256": digest,
            "findings_sha256": digest,
            "work_ledger_sha256": digest,
        },
        "authority": RECEIPT_AUTHORITY,
        "base_revision": base_sha,
        "coverage_completeness": "complete",
        "findings_count": 0,
        "head_revision": head_sha,
        "manifest_sha256": digest,
        "producer": {"name": "codex-security-plugin", "version": "0.1.11"},
        "scan_id": "123e4567-e89b-42d3-a456-426614174000",
        "snapshot_digest": "codex-security-snapshot/v1:sha256:" + "b" * 64,
    }


def _outage_receipt(base_sha: str, head_sha: str, material_digest: str) -> dict[str, Any]:
    return build_security_outage_override_receipt(
        base_revision=base_sha,
        head_revision=head_sha,
        material_digest=material_digest,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-16T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )


def _check_node(
    name: str,
    *,
    status: str = "COMPLETED",
    conclusion: str = "SUCCESS",
    workflow_name: str | None = None,
    app_database_id: int | None = None,
    app_slug: str | None = None,
    started_at: str | None = "2026-07-16T11:00:00Z",
    suite_created_at: str = "2026-07-16T11:00:00Z",
) -> dict[str, Any]:
    expected_workflow, expected_app_id, expected_app_slug = (
        merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES[name]
    )
    resolved_workflow = expected_workflow if workflow_name is None else workflow_name
    return {
        "__typename": "CheckRun",
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "startedAt": started_at,
        "completedAt": "2026-07-16T11:01:00Z" if status == "COMPLETED" else None,
        "detailsUrl": f"https://github.com/checks/{name}",
        "checkSuite": {
            "createdAt": suite_created_at,
            "app": {
                "databaseId": expected_app_id if app_database_id is None else app_database_id,
                "slug": expected_app_slug if app_slug is None else app_slug,
            },
            "workflowRun": (
                {"workflow": {"name": resolved_workflow}} if resolved_workflow else None
            ),
        },
    }


def test_operator_outage_override_requires_exact_successful_security_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    stale_failed_security = _check_node(
        "security",
        conclusion="FAILURE",
        started_at="2026-07-16T10:59:00Z",
        suite_created_at="2026-07-16T10:59:00Z",
    )
    nodes.append(stale_failed_security)
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    merge_gate._validate_operator_outage_security_checks(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )


def test_operator_outage_override_accepts_trusted_skipped_inapplicable_security(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        _check_node(
            name,
            conclusion="SKIPPED" if name == "security" else "SUCCESS",
        )
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    merge_gate._validate_operator_outage_security_checks(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        security_required=merge_gate._operator_outage_security_required(("docs/README.md",)),
    )


def test_operator_outage_security_applicability_uses_material_risk_profile() -> None:
    assert merge_gate._operator_outage_security_required(("docs/README.md",)) is False
    assert (
        merge_gate._operator_outage_security_required(("scripts/ci/check_pr_merge_readiness.py",))
        is True
    )


def test_operator_outage_override_rejects_newer_queued_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    nodes.append(
        _check_node(
            "security",
            status="QUEUED",
            conclusion="",
            started_at=None,
            suite_created_at="2026-07-16T11:01:00Z",
        )
    )
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match="security=pending/status"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


@pytest.mark.parametrize(
    ("target", "newer_job"),
    [
        ("security", "pr_scope_guard"),
        ("security-scan", "build"),
    ],
)
def test_operator_outage_override_rejects_stale_success_before_newer_workflow_job(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    newer_job: str,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    newer_workflow_activity = _check_node(
        target,
        suite_created_at="2026-07-16T11:01:00Z",
    )
    newer_workflow_activity["name"] = newer_job
    newer_workflow_activity["detailsUrl"] = f"https://github.com/checks/{newer_job}"
    nodes.append(newer_workflow_activity)
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match=rf"{target}=missing-latest"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_operator_outage_override_rejects_equal_time_pending_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    equal_time_pending = _check_node(
        "security",
        status="QUEUED",
        conclusion="",
    )
    equal_time_pending["detailsUrl"] = "https://github.com/checks/a-pending-security"
    nodes.append(equal_time_pending)
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match="security=pending/status"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_operator_outage_override_rejects_equal_time_neutral_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    equal_time_neutral = _check_node(
        "security",
        conclusion="NEUTRAL",
    )
    equal_time_neutral["detailsUrl"] = "https://github.com/checks/a-neutral-security"
    nodes.append(equal_time_neutral)
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match="security=failed/NEUTRAL"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_operator_outage_override_rejects_unorderable_newer_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        _check_node(name)
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        if name != "security"
    ]
    nodes.extend(
        [
            _check_node(
                "security",
                suite_created_at="2026-07-16T10:00:00Z",
                started_at="2026-07-16T10:00:00Z",
            ),
            _check_node(
                "security",
                suite_created_at="",
                started_at="2026-07-16T12:00:00Z",
            ),
        ]
    )
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(
        ReviewEvidenceError,
        match="cannot order current-head security checks",
    ):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


@pytest.mark.parametrize(
    ("target", "status", "conclusion", "expected"),
    [
        ("security", "IN_PROGRESS", "", "security=pending/status"),
        ("security", "COMPLETED", "SKIPPED", "security=failed/SKIPPED"),
        ("CodeQL", "COMPLETED", "SKIPPED", "CodeQL=failed/SKIPPED"),
        ("security-scan", "COMPLETED", "FAILURE", "security-scan=failed/FAILURE"),
    ],
)
def test_operator_outage_override_rejects_non_successful_security_checks(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    status: str,
    conclusion: str,
    expected: str,
) -> None:
    nodes = [
        _check_node(
            name,
            status=status if name == target else "COMPLETED",
            conclusion=conclusion if name == target else "SUCCESS",
        )
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match=expected):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_operator_outage_override_rejects_missing_security_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        _check_node(name)
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        if name != "Private Python proxy health"
    ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match="Private Python proxy health=missing"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


@pytest.mark.parametrize(
    ("target", "kwargs"),
    [
        ("security", {"workflow_name": "Evil workflow"}),
        ("security-scan", {"app_database_id": 999}),
        ("CodeQL", {"app_slug": "foreign-codeql"}),
    ],
)
def test_operator_outage_override_rejects_foreign_check_producers(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    kwargs: dict[str, Any],
) -> None:
    nodes = [
        _check_node(name, **(kwargs if name == target else {}))
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match=f"{target}=untrusted-producer"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_operator_outage_override_rejects_foreign_status_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        _check_node(name)
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        if name != "CodeQL"
    ]
    nodes.append(
        {
            "__typename": "StatusContext",
            "context": "CodeQL",
            "state": "SUCCESS",
            "createdAt": "2026-07-16T11:01:00Z",
            "targetUrl": "https://example.invalid/spoof",
        }
    )
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match="CodeQL=untrusted-producer"):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def _artifact_with_seal(seal: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PR 42 — Review Governance",
            "",
            "Review-Seal-Version: v1",
            "",
            "## Discussion Thread Pass",
            "- [x] Discussion-thread pass completed",
            "- [x] Fixed in commit mapping completed",
            "",
            "## Fixed in Commit Mapping",
            "- No actionable review comments",
            "",
            "## Review Material Seal",
            render_embedded_review_seal(seal),
            "",
        ]
    )


def test_ci_gate_accepts_governance_only_head_and_rejects_stale_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    frozen = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=42
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": material_head,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": "https://github.com/owner/repo/pull/42#pullrequestreview-1",
            "reviewed_material_digest": frozen.digest,
            "status": "completed",
        },
        "codex_security": _receipt(base_sha, material_head),
        "material": {
            "base_ref_oid": base_sha,
            "digest": frozen.digest,
            "material_head_sha": material_head,
            "merge_base_sha": frozen.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    artifact = _artifact_with_seal(seal)
    mapping.write_text(artifact, encoding="utf-8")
    governance_head = _commit(repo, "governance closeout")
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=governance_head,
        commits=(
            PrCommitEvidence(material_head, None),
            PrCommitEvidence(governance_head, None),
        ),
    )
    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == governance_head else CommitRefKind.PR_COMMIT,
        ),
    )
    monkeypatch.setattr(merge_gate, "is_ancestor", lambda *_a, **_k: True)
    verifier_expected_commits: list[str | None] = []

    def verify_review(*_args: Any, **kwargs: Any) -> CodexReviewEvidence:
        verifier_expected_commits.append(kwargs.get("expected_commit_ref"))
        return CodexReviewEvidence(
            reference="https://github.com/owner/repo/pull/42#pullrequestreview-1",
            submitted_at="2026-07-15T11:00:00Z",
            commit_ref=material_head,
        )

    monkeypatch.setattr(merge_gate, "verify_codex_review_reference", verify_review)

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
    )
    assert validated["material"]["digest"] == frozen.digest
    assert verifier_expected_commits == [material_head]

    live_snapshot = {"value": snapshot}
    monkeypatch.setenv("GITHUB_TOKEN", "opaque")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_pr_merge_readiness.py",
            "--pr-number",
            "42",
            "--repo",
            "owner/repo",
        ],
    )
    monkeypatch.setattr(
        merge_gate,
        "_fetch_pr_context",
        lambda *_a, **_k: (
            42,
            "owner/repo",
            False,
            "Canonical artifact: docs/review/PR_42_FIXED_MAPPING.md",
        ),
    )
    monkeypatch.setattr(
        merge_gate,
        "fetch_pr_snapshot",
        lambda *_a, **_k: live_snapshot["value"],
    )
    monkeypatch.setattr(
        merge_gate,
        "_local_head_sha",
        lambda: live_snapshot["value"].head_sha,
    )
    monkeypatch.setattr(merge_gate, "fetch_review_threads", lambda *_a, **_k: ())
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", lambda **_k: [])
    monkeypatch.setattr(merge_gate, "read_mapping_artifact", lambda _pr: artifact)
    monkeypatch.setattr(merge_gate, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    assert merge_gate.main() == 0
    assert "CONTENT_BOUND_RECEIPT_VALID" in capsys.readouterr().out

    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: CodexReviewEvidence(
            reference="https://github.com/owner/repo/pull/42#pullrequestreview-1",
            submitted_at="2026-07-15T11:00:00Z",
            commit_ref=governance_head,
        ),
    )
    with pytest.raises(ReviewEvidenceError, match="sealed material head"):
        merge_gate._validate_v1_seal(
            artifact_text=artifact,
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
        )

    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: CodexReviewEvidence(
            reference="https://github.com/owner/repo/pull/42#pullrequestreview-1",
            submitted_at="2026-07-15T11:00:00Z",
            commit_ref=material_head,
        ),
    )

    source.write_text("ENFORCED = False\n", encoding="utf-8")
    changed_head = _commit(repo, "post-scan material change")
    changed_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=changed_head,
        commits=(*snapshot.commits, PrCommitEvidence(changed_head, None)),
    )
    with pytest.raises(ReviewEvidenceError, match="live material digest"):
        merge_gate._validate_v1_seal(
            artifact_text=artifact,
            repository="owner/repo",
            pr_number=42,
            snapshot=changed_snapshot,
            token="opaque",
        )
    live_snapshot["value"] = changed_snapshot
    assert merge_gate.main() == 1
    assert "Material review seal validation failed" in capsys.readouterr().out


def test_ci_gate_revalidates_live_operator_outage_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    frozen = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=42
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": material_head,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": "https://github.com/owner/repo/pull/42#pullrequestreview-1",
            "reviewed_material_digest": frozen.digest,
            "status": "completed",
        },
        "codex_security": _outage_receipt(base_sha, material_head, frozen.digest),
        "material": {
            "base_ref_oid": base_sha,
            "digest": frozen.digest,
            "material_head_sha": material_head,
            "merge_base_sha": frozen.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }
    artifact = _artifact_with_seal(seal)
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(artifact, encoding="utf-8")
    governance_head = _commit(repo, "governance closeout")
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=governance_head,
        commits=(
            PrCommitEvidence(material_head, None),
            PrCommitEvidence(governance_head, None),
        ),
    )
    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == governance_head else CommitRefKind.PR_COMMIT,
        ),
    )
    monkeypatch.setattr(merge_gate, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: CodexReviewEvidence(
            reference="https://github.com/owner/repo/pull/42#pullrequestreview-1",
            submitted_at="2026-07-16T11:00:00Z",
            commit_ref=material_head,
        ),
    )
    override_calls: list[tuple[str, str]] = []

    def verify_override(*_args: Any, **kwargs: Any) -> SecurityOutageOverrideEvidence:
        override_calls.append(
            (kwargs["expected_material_head_sha"], kwargs["expected_material_digest"])
        )
        return SecurityOutageOverrideEvidence(
            reference="https://github.com/owner/repo/pull/42#issuecomment-789",
            created_at="2026-07-16T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
            material_head_sha=material_head,
            material_digest=frozen.digest,
        )

    check_calls: list[int] = []
    monkeypatch.setattr(
        merge_gate,
        "verify_security_outage_override_reference",
        verify_override,
    )
    monkeypatch.setattr(
        merge_gate,
        "_validate_operator_outage_security_checks",
        lambda **_kwargs: check_calls.append(1),
    )

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
    )

    assert validated["codex_security"]["status"] == "tooling_unavailable"
    assert override_calls == [(material_head, frozen.digest)]
    assert check_calls == [1]

    override_calls.clear()
    check_calls.clear()
    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
        validate_outage_security_checks=False,
    )

    assert validated["codex_security"]["status"] == "tooling_unavailable"
    assert override_calls == [(material_head, frozen.digest)]
    assert check_calls == []


def test_merge_readiness_main_blocks_missing_mapping(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head_sha = "a" * 40
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha="b" * 40,
        head_sha=head_sha,
        commits=(PrCommitEvidence(head_sha, None),),
    )

    def missing_mapping(_pr_number: int) -> str:
        raise FileNotFoundError("missing review seal")

    monkeypatch.setenv("GITHUB_TOKEN", "opaque")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_pr_merge_readiness.py",
            "--pr-number",
            "42",
            "--repo",
            "owner/repo",
        ],
    )
    monkeypatch.setattr(
        merge_gate,
        "_fetch_pr_context",
        lambda *_a, **_k: (42, "owner/repo", False, "docs/review/PR_42_FIXED_MAPPING.md"),
    )
    monkeypatch.setattr(merge_gate, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(merge_gate, "_local_head_sha", lambda: head_sha)
    monkeypatch.setattr(merge_gate, "fetch_review_threads", lambda *_a, **_k: ())
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", lambda **_k: [])
    monkeypatch.setattr(merge_gate, "read_mapping_artifact", missing_mapping)

    assert merge_gate.main() == 1
    assert "canonical review artifact is invalid" in capsys.readouterr().out


def test_merge_readiness_checkout_uses_exact_pr_head_and_no_credentials() -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["merge_readiness_gate"]["steps"]
    checkout = next(step for step in steps if step.get("name") == "Checkout")
    assert checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
        "ref": "${{ github.event.pull_request.head.sha }}",
    }


def test_event_head_sha_is_required_and_exact(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps({"pull_request": {"head": {"sha": "a" * 40}}}),
        encoding="utf-8",
    )
    assert merge_gate._event_head_sha(event) == "a" * 40
    event.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="head.sha"):
        merge_gate._event_head_sha(event)
