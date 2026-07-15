from __future__ import annotations

import json
import os
import shutil
import subprocess
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
)
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    ReviewEvidenceError,
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
    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: CodexReviewEvidence(
            reference="https://github.com/owner/repo/pull/42#pullrequestreview-1",
            submitted_at="2026-07-15T11:00:00Z",
            commit_ref=material_head,
        ),
    )

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
    )
    assert validated["material"]["digest"] == frozen.digest

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
