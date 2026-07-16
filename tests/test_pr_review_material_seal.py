"""Focused fail-closed tests for real PR commits and material review seals."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any, cast

import pytest

from scripts.orchestration.pr_commit_identity import (
    CommitIdentityError,
    CommitRefKind,
    GitHubHttpError,
    PrCommitEvidence,
    PrSnapshot,
    ReviewCommentEvidence,
    RepositoryCommitRef,
    ReviewExecutionRef,
    ReviewThreadEvidence,
    assert_snapshot_unchanged,
    classify_commit_ref,
    fetch_pr_snapshot,
    fetch_review_threads,
    is_ancestor,
    verify_codex_review_reference,
)
from scripts.orchestration import pr_commit_identity as identity_module
from scripts.orchestration import pr_review_closeout as closeout_module
from scripts.orchestration import pr_review_evidence as evidence_module
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    SEAL_BEGIN,
    SEAL_END,
    MaterialManifest,
    ReviewEvidenceError,
    compute_material_manifest,
    ingest_codex_security_receipt,
    parse_duplicate_disposition_reply,
    parse_embedded_review_seal,
    render_embedded_review_seal,
    unavailable_review_ref_fingerprint,
    validated_duplicate_reply_urls,
)
from scripts.orchestration.review_mapping_artifact import (
    parse_canonical_fingerprint_records,
    validate_mapping_artifact_text,
)

BASE_SHA = "1" * 40
FIX_SHA = "2" * 40
HEAD_SHA = "3" * 40
OUTSIDE_SHA = "4" * 40
UNAVAILABLE_SHA = "5" * 40
DIGEST = "sha256:" + "a" * 64
SNAPSHOT_DIGEST = "codex-security-snapshot/v1:sha256:" + "b" * 64
SCAN_ID = "123e4567-e89b-42d3-a456-426614174000"


def _snapshot() -> PrSnapshot:
    return PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        commits=(
            PrCommitEvidence(FIX_SHA, "2026-07-15T10:00:00Z"),
            PrCommitEvidence(HEAD_SHA, "2026-07-15T11:00:00Z"),
        ),
    )


def _material_manifest(head_sha: str, *, digest: str = DIGEST) -> MaterialManifest:
    return MaterialManifest(
        base_ref_oid=BASE_SHA,
        head_ref_oid=head_sha,
        merge_base_sha=BASE_SHA,
        pr_number=42,
        entries=(),
        digest=digest,
    )


def _graphql_page(
    *,
    commits: list[tuple[str, str | None]],
    has_next: bool,
    cursor: str | None,
) -> dict[str, Any]:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "baseRefOid": BASE_SHA,
                    "headRefOid": HEAD_SHA,
                    "commits": {
                        "nodes": [
                            {"commit": {"oid": sha, "pushedDate": pushed_at}}
                            for sha, pushed_at in commits
                        ],
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    },
                }
            }
        }
    }


def test_pr_snapshot_requires_complete_cursor_pagination() -> None:
    responses = iter(
        [
            _graphql_page(
                commits=[(FIX_SHA, "2026-07-15T10:00:00Z")],
                has_next=True,
                cursor="cursor-1",
            ),
            _graphql_page(
                commits=[(HEAD_SHA, "2026-07-15T11:00:00Z")],
                has_next=False,
                cursor=None,
            ),
        ]
    )

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return next(responses)

    snapshot = fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)

    assert snapshot.commit_shas == {FIX_SHA, HEAD_SHA}
    assert snapshot.base_sha == BASE_SHA
    assert snapshot.head_sha == HEAD_SHA


def test_pr_snapshot_fails_closed_for_missing_next_cursor() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return _graphql_page(
            commits=[(HEAD_SHA, "2026-07-15T11:00:00Z")],
            has_next=True,
            cursor=None,
        )

    with pytest.raises(CommitIdentityError, match="cursor is missing or repeated"):
        fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)


@pytest.mark.parametrize("commit_count", [1, 100, 101, 251])
def test_pr_snapshot_covers_graphql_page_boundaries(commit_count: int) -> None:
    commit_shas = [f"{index:040x}" for index in range(1, commit_count)] + [HEAD_SHA]
    pages = [commit_shas[index : index + 100] for index in range(0, commit_count, 100)]
    requested_cursors: list[str | None] = []

    def request_json(*_args: Any, **kwargs: Any) -> Any:
        cursor = kwargs["payload"]["variables"]["cursor"]
        requested_cursors.append(cursor)
        page_index = len(requested_cursors) - 1
        expected_cursor = None if page_index == 0 else f"cursor-{page_index}"
        assert cursor == expected_cursor
        has_next = page_index + 1 < len(pages)
        end_cursor = f"cursor-{page_index + 1}" if has_next else None
        return _graphql_page(
            commits=[(sha, "2026-07-15T10:00:00Z") for sha in pages[page_index]],
            has_next=has_next,
            cursor=end_cursor,
        )

    snapshot = fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)

    assert len(snapshot.commits) == commit_count
    assert snapshot.commits[-1].sha == HEAD_SHA
    assert len(requested_cursors) == len(pages)


def test_pr_snapshot_rejects_empty_connection() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return _graphql_page(commits=[], has_next=False, cursor=None)

    with pytest.raises(CommitIdentityError, match="connection is empty"):
        fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)


def test_pr_snapshot_rejects_repeated_non_adjacent_cursor() -> None:
    responses = iter(
        [
            _graphql_page(
                commits=[(FIX_SHA, "2026-07-15T10:00:00Z")],
                has_next=True,
                cursor="cursor-1",
            ),
            _graphql_page(
                commits=[(OUTSIDE_SHA, "2026-07-15T10:30:00Z")],
                has_next=True,
                cursor="cursor-2",
            ),
            _graphql_page(
                commits=[(HEAD_SHA, "2026-07-15T11:00:00Z")],
                has_next=True,
                cursor="cursor-1",
            ),
        ]
    )

    with pytest.raises(CommitIdentityError, match="cursor is missing or repeated"):
        fetch_pr_snapshot(
            "owner/repo",
            42,
            token="opaque",
            request_json=lambda *_args, **_kwargs: next(responses),
        )


def test_pr_snapshot_rejects_incomplete_terminal_set_without_head() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return _graphql_page(
            commits=[(FIX_SHA, "2026-07-15T10:00:00Z")],
            has_next=False,
            cursor=None,
        )

    with pytest.raises(CommitIdentityError, match="live PR head is absent"):
        fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)


@pytest.mark.parametrize(
    ("sha", "expected_kind"),
    [
        (HEAD_SHA, CommitRefKind.PR_HEAD),
        (FIX_SHA, CommitRefKind.PR_COMMIT),
        (OUTSIDE_SHA, CommitRefKind.REPO_COMMIT_OUTSIDE_PR),
    ],
)
def test_commit_classification_requires_commit_api_existence(
    sha: str, expected_kind: CommitRefKind
) -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {"sha": sha}

    resolution = classify_commit_ref(sha, _snapshot(), token="opaque", request_json=request_json)

    assert isinstance(resolution, RepositoryCommitRef)
    assert resolution.kind is expected_kind


@pytest.mark.parametrize(
    "error",
    [
        GitHubHttpError(404, "Not Found"),
        GitHubHttpError(422, "Unprocessable Entity", "No commit found for SHA"),
    ],
)
def test_unavailable_review_ref_never_reaches_ancestry(error: GitHubHttpError) -> None:
    calls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        calls.append(url)
        raise error

    resolution = classify_commit_ref(
        UNAVAILABLE_SHA,
        _snapshot(),
        token="opaque",
        request_json=request_json,
    )
    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.REVIEW_REF_UNAVAILABLE

    with pytest.raises(TypeError, match="RepositoryCommitRef"):
        is_ancestor(
            cast(RepositoryCommitRef, resolution),
            RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD),
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )
    assert len(calls) == 1


def test_api_outage_is_unknown_not_unavailable() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise GitHubHttpError(503, "Service Unavailable")

    resolution = classify_commit_ref(
        UNAVAILABLE_SHA,
        _snapshot(),
        token="opaque",
        request_json=request_json,
    )

    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.API_UNKNOWN


@pytest.mark.parametrize(
    "failure",
    [
        GitHubHttpError(403, "Forbidden"),
        GitHubHttpError(429, "Rate Limited"),
        GitHubHttpError(500, "Server Error"),
        TimeoutError(),
        CommitIdentityError("malformed response"),
    ],
)
def test_all_unproven_api_failures_remain_unknown(failure: Exception) -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise failure

    resolution = classify_commit_ref(
        UNAVAILABLE_SHA, _snapshot(), token="opaque", request_json=request_json
    )
    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.API_UNKNOWN


def test_compare_accepts_only_bound_ancestor_response() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": HEAD_SHA}],
            "merge_base_commit": {"sha": FIX_SHA},
        }

    assert is_ancestor(
        ancestor,
        descendant,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )


@pytest.mark.parametrize("commits", [None, [], [{"sha": OUTSIDE_SHA}]])
def test_compare_rejects_missing_or_mismatched_descendant(commits: Any) -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "commits": commits,
            "merge_base_commit": {"sha": FIX_SHA},
        }

    with pytest.raises(CommitIdentityError, match="does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


def test_compare_accepts_identical_repository_commit_without_api_call() -> None:
    commit = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("identical commits must not call the Compare API")

    assert is_ancestor(
        commit,
        commit,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )


def test_codex_review_reference_requires_exact_trusted_submitted_review() -> None:
    reference = "https://github.com/owner/repo/pull/42#pullrequestreview-123"

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "commit_id": HEAD_SHA,
            "html_url": reference,
            "state": "COMMENTED",
            "submitted_at": "2026-07-15T11:00:00Z",
            "user": {"login": "chatgpt-codex-connector[bot]"},
        }

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        request_json=request_json,
    )
    assert evidence.commit_ref == HEAD_SHA

    with pytest.raises(CommitIdentityError, match="expected material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=OUTSIDE_SHA,
            request_json=request_json,
        )

    with pytest.raises(CommitIdentityError, match="submitted trusted Codex"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: {
                "commit_id": HEAD_SHA,
                "html_url": reference,
                "state": "COMMENTED",
                "submitted_at": "2026-07-15T11:00:00Z",
                "user": {"login": "spoofed[bot]"},
            },
        )


def _codex_no_findings_body(commit_prefix: str = HEAD_SHA[:10]) -> str:
    return f"""Codex Review: Didn't find any major issues. Breezy!

**Reviewed commit:** `{commit_prefix}`

<details> <summary>ℹ️ About Codex in GitHub</summary>
<br/>

[Your team has set up Codex to review pull requests in this repo](https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you
- Open a pull request for review
- Mark a draft as ready
- Comment "@codex review".

If Codex has suggestions, it will comment; otherwise it will react with 👍.



Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".

</details>"""


def _codex_no_findings_comment(reference: str, *, body: str | None = None) -> dict[str, Any]:
    return {
        "body": _codex_no_findings_body() if body is None else body,
        "created_at": "2026-07-15T11:00:00Z",
        "html_url": reference,
        "performed_via_github_app": {
            "id": 1_144_995,
            "owner": {"login": "openai"},
            "slug": "chatgpt-codex-connector",
        },
        "updated_at": "2026-07-15T11:00:00Z",
        "user": {"login": "chatgpt-codex-connector[bot]", "type": "Bot"},
    }


def test_codex_no_findings_comment_is_bound_to_expected_full_head() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    requested_urls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        requested_urls.append(url)
        if url.endswith("/commits/" + HEAD_SHA[:10]):
            return {"sha": HEAD_SHA}
        return _codex_no_findings_comment(reference)

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        request_json=request_json,
    )

    assert evidence.commit_ref == HEAD_SHA
    assert evidence.submitted_at == "2026-07-15T11:00:00Z"
    assert requested_urls == [
        "https://api.github.com/repos/owner/repo/issues/comments/456",
        f"https://api.github.com/repos/owner/repo/commits/{HEAD_SHA[:10]}",
    ]


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda response: response["user"].update(login="spoofed[bot]"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["user"].update(type="User"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"].update(id=1),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"].update(slug="spoofed"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"]["owner"].update(login="spoofed"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response.update(
                html_url="https://github.com/owner/repo/pull/43#issuecomment-456"
            ),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response.update(updated_at="2026-07-15T11:01:00Z"),
            "edited after creation",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(
                    "Didn't find any major issues. Breezy!", "Found a major issue."
                )
            ),
            "not an exact Codex no-findings response",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(
                    "Didn't find any major issues. Breezy!",
                    "Didn't find any major issues. But one issue exists.",
                )
            ),
            "not an exact Codex no-findings response",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(HEAD_SHA[:10], "ABCDEF1234")
            ),
            "invalid commit evidence",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(
                    f"**Reviewed commit:** `{HEAD_SHA[:10]}`",
                    (
                        f"**Reviewed commit:** `{HEAD_SHA[:10]}`\n"
                        f"**Reviewed commit:** `{HEAD_SHA[:10]}`"
                    ),
                )
            ),
            "invalid commit evidence",
        ),
    ],
)
def test_codex_no_findings_comment_rejects_untrusted_or_ambiguous_evidence(
    mutate: Any, error: str
) -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    response = _codex_no_findings_comment(reference)
    mutate(response)

    with pytest.raises(CommitIdentityError, match=error):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=lambda *_a, **_k: response,
        )


def test_codex_no_findings_comment_requires_exact_full_head_binding() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    response = _codex_no_findings_comment(
        reference,
        body=_codex_no_findings_body(OUTSIDE_SHA[:10]),
    )

    with pytest.raises(CommitIdentityError, match="does not match the material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=lambda *_a, **_k: response,
        )


def test_codex_no_findings_comment_rejects_unresolved_short_commit() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"

    def request_json(url: str, **_kwargs: Any) -> Any:
        if "/commits/" in url:
            return {"sha": OUTSIDE_SHA}
        return _codex_no_findings_comment(reference)

    with pytest.raises(CommitIdentityError, match="does not resolve to the material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=request_json,
        )

    with pytest.raises(CommitIdentityError, match="requires an expected full material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: _codex_no_findings_comment(reference),
        )


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
    return _git(repo, "rev-parse", "HEAD", env=env)


def test_material_digest_ignores_only_exact_current_pr_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base = _commit(repo, "base")

    source = repo / "src" / "nested" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    before_closeout = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=material_head, pr_number=42
    )
    assert [entry.path for entry in before_closeout.entries] == ["src/nested/policy.py"]

    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text("mapping\n", encoding="utf-8")
    mapping_head = _commit(repo, "mapping closeout")
    after_closeout = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=mapping_head, pr_number=42
    )
    assert after_closeout.digest == before_closeout.digest

    (repo / "docs" / "operator.md").write_text("material docs\n", encoding="utf-8")
    docs_head = _commit(repo, "other docs")
    after_other_docs = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=docs_head, pr_number=42
    )
    assert after_other_docs.digest != before_closeout.digest


def _write_json(path: Path, value: Any) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _build_scan_bundle(root: Path) -> Path:
    coverage = {
        "completeness": "complete",
        "deferred": [],
        "documentType": "codex-security.coverage",
        "excludePaths": [],
        "explicitExclusions": [],
        "includePaths": ["."],
        "inventoryStrategy": "diff",
        "mode": "branch_diff",
        "openQuestions": [],
        "scanId": SCAN_ID,
        "schemaVersion": "1.0",
        "surfaces": [],
    }
    findings = {
        "documentType": "codex-security.findings",
        "findings": [],
        "scanId": SCAN_ID,
        "schemaVersion": "1.0",
    }
    coverage_raw = _write_json(root / "coverage.json", coverage)
    findings_raw = _write_json(root / "findings.json", findings)
    ledger_path = root / "artifacts" / "02_discovery" / "work_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True)
    ledger_raw = b'{"status":"reviewed"}\n'
    ledger_path.write_bytes(ledger_raw)

    manifest = {
        "documentType": "codex-security.scan-manifest",
        "scan": {
            "artifacts": [
                {
                    "mediaType": "application/json",
                    "path": "findings.json",
                    "sha256": hashlib.sha256(findings_raw).hexdigest(),
                },
                {
                    "mediaType": "application/json",
                    "path": "coverage.json",
                    "sha256": hashlib.sha256(coverage_raw).hexdigest(),
                },
                {
                    "mediaType": "application/octet-stream",
                    "path": "artifacts/02_discovery/work_ledger.jsonl",
                    "sha256": hashlib.sha256(ledger_raw).hexdigest(),
                },
            ],
            "completedAt": "2026-07-15T11:00:00Z",
            "coverageRef": "coverage.json",
            "findingsRef": "findings.json",
            "id": SCAN_ID,
            "producer": {"name": "codex-security-plugin", "version": "0.1.11"},
            "scope": {},
            "sealedAt": "2026-07-15T11:00:00Z",
            "startedAt": "2026-07-15T10:00:00Z",
            "status": "completed",
            "target": {
                "baseRevision": BASE_SHA,
                "displayName": "repo",
                "headRevision": HEAD_SHA,
                "kind": "git_diff",
                "snapshotDigest": SNAPSHOT_DIGEST,
                "targetId": "target_sha256_" + "c" * 64,
            },
            "threatModel": {},
        },
        "schemaVersion": "1.0",
    }
    _write_json(root / "scan-manifest.json", manifest)
    return root / "scan-manifest.json"


def test_scan_receipt_validates_real_bundle_and_contains_no_local_path(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")

    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )

    assert receipt["authority"] == RECEIPT_AUTHORITY
    assert receipt["findings_count"] == 0
    assert str(tmp_path) not in json.dumps(receipt)


def test_scan_receipt_rejects_symlinked_artifact(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    coverage_path = manifest_path.parent / "coverage.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(coverage_path.read_bytes())
    coverage_path.unlink()
    coverage_path.symlink_to(outside)

    with pytest.raises(ReviewEvidenceError, match="symlink"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_symlinked_manifest(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    outside = tmp_path / "outside-manifest.json"
    outside.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()
    manifest_path.symlink_to(outside)

    with pytest.raises(ReviewEvidenceError, match="symlink"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_uses_one_stable_root_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "scan"
    manifest_path = _build_scan_bundle(root)
    original_reader = evidence_module._read_contained_artifact_from_descriptor
    swapped = False

    def swap_root_after_manifest(descriptor: int, relative: Any, *, max_bytes: int) -> bytes:
        nonlocal swapped
        raw = original_reader(descriptor, relative, max_bytes=max_bytes)
        if str(relative) == "scan-manifest.json" and not swapped:
            swapped = True
            root.rename(tmp_path / "original-scan")
            root.mkdir()
            (root / "coverage.json").write_text("{}", encoding="utf-8")
        return raw

    monkeypatch.setattr(
        evidence_module,
        "_read_contained_artifact_from_descriptor",
        swap_root_after_manifest,
    )
    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )
    assert receipt["coverage_completeness"] == "complete"


def test_scan_receipt_rejects_hash_drift(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    (manifest_path.parent / "findings.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ReviewEvidenceError, match="hash mismatch"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def _seal(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": HEAD_SHA,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": "https://github.com/owner/repo/pull/42#pullrequestreview-1",
            "reviewed_material_digest": DIGEST,
            "status": "completed",
        },
        "codex_security": receipt,
        "material": {
            "base_ref_oid": BASE_SHA,
            "digest": DIGEST,
            "material_head_sha": HEAD_SHA,
            "merge_base_sha": BASE_SHA,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }


def _mapping_artifact_with_seal(seal: dict[str, Any]) -> str:
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


def test_authenticated_closeout_validation_rejects_nonexistent_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(_seal(receipt)), encoding="utf-8")
    manifest = MaterialManifest(
        base_ref_oid=BASE_SHA,
        head_ref_oid=HEAD_SHA,
        merge_base_sha=BASE_SHA,
        pr_number=42,
        entries=(),
        digest=DIGEST,
    )
    verifier_expected_commits: list[str | None] = []

    def reject_review(*_args: Any, **kwargs: Any) -> Any:
        verifier_expected_commits.append(kwargs.get("expected_commit_ref"))
        raise CommitIdentityError("GitHub review not found")

    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: manifest,
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(closeout_module, "verify_codex_review_reference", reject_review)
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    with pytest.raises(CommitIdentityError, match="review not found"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )

    assert verifier_expected_commits == [HEAD_SHA]


def test_embedded_seal_round_trip_is_strict_and_canonical(tmp_path: Path) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    rendered = render_embedded_review_seal(_seal(receipt))

    assert parse_embedded_review_seal(rendered) == _seal(receipt)

    noncanonical = rendered.replace('"authority":', '"authority" :', 1)
    with pytest.raises(ReviewEvidenceError, match="not canonical"):
        parse_embedded_review_seal(noncanonical)


def test_embedded_seal_rejects_duplicate_keys() -> None:
    text = f'{SEAL_BEGIN}\n{{"authority":"x","authority":"y"}}\n{SEAL_END}'

    with pytest.raises(ReviewEvidenceError, match="duplicate key"):
        parse_embedded_review_seal(text)


def test_snapshot_recheck_detects_force_push() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "baseRefOid": BASE_SHA,
                        "headRefOid": OUTSIDE_SHA,
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="SNAPSHOT_CHANGED"):
        assert_snapshot_unchanged(_snapshot(), token="opaque", request_json=request_json)


def test_sanitized_pr_2137_refs_share_one_fingerprint_and_never_compare() -> None:
    synthetic_refs = ("6" * 40, "7" * 40, "8" * 40)
    compare_calls = 0

    def request_json(url: str, **_kwargs: Any) -> Any:
        nonlocal compare_calls
        if "/compare/" in url:
            compare_calls += 1
        raise GitHubHttpError(404, "Not Found")

    fingerprints: set[str] = set()
    for review_ref in synthetic_refs:
        resolution = classify_commit_ref(
            review_ref, _snapshot(), token="opaque", request_json=request_json
        )
        assert isinstance(resolution, ReviewExecutionRef)
        assert resolution.kind is CommitRefKind.REVIEW_REF_UNAVAILABLE
        fingerprints.add(
            unavailable_review_ref_fingerprint(
                pr_number=42,
                material_digest=DIGEST,
                verified_real_fix_sha=FIX_SHA,
            )
        )
    assert fingerprints == {
        unavailable_review_ref_fingerprint(
            pr_number=42,
            material_digest=DIGEST,
            verified_real_fix_sha=FIX_SHA,
        )
    }
    assert compare_calls == 0


def test_sanitized_pr_2137_abbreviated_fix_dedupes_three_unavailable_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fix = "fe7ff2017029ee9ede21264f2fbe19dca1ce23a2"  # pragma: allowlist secret
    real_head = "5a916507" + "a" * 32
    original_commits = (
        "2d828000" + "a" * 32,
        "69168f8e" + "b" * 32,
        real_head,
    )
    unavailable_refs = (
        "66c8634758c59916d46106e8e223e804c86733aa",  # pragma: allowlist secret
        "2aa032f808cdedc8f4b9a6514a5051cd6ff801be",  # pragma: allowlist secret
        "f31fd6332eb85cd4f9cff1131db69781896ebb8a",  # pragma: allowlist secret
    )
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=2137,
        base_sha=BASE_SHA,
        head_sha=real_head,
        commits=(
            PrCommitEvidence(real_fix, "2026-07-14T09:00:00Z"),
            *(
                PrCommitEvidence(sha, f"2026-07-14T{10 + index:02d}:00:00Z")
                for index, sha in enumerate(original_commits)
            ),
        ),
    )
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=2137,
        material_digest=DIGEST,
        verified_real_fix_sha=real_fix,
    )
    root_urls = tuple(
        f"https://github.com/owner/repo/pull/2137#discussion_r{index}" for index in range(1, 4)
    )
    findings = tuple(
        ReviewCommentEvidence(
            url=url,
            body=(
                "Commit ancestry finding: FIX fe7ff201... is reported unreachable "
                f"from reviewer execution ref {unavailable_ref}."
            ),
            created_at=f"2026-07-14T{13 + index:02d}:00:00Z",
            author_login="chatgpt-codex-connector",
            author_association="NONE",
            original_commit_sha=original_commits[index],
        )
        for index, (url, unavailable_ref) in enumerate(zip(root_urls, unavailable_refs))
    )
    threads = (
        ReviewThreadEvidence("canonical", True, (findings[0],)),
        *(
            ReviewThreadEvidence(
                f"duplicate-{index}",
                True,
                (
                    findings[index],
                    ReviewCommentEvidence(
                        url=f"{root_urls[index]}-reply",
                        body=_duplicate_reply(fingerprint),
                        created_at=f"2026-07-14T{16 + index:02d}:00:00Z",
                        author_login="maintainer",
                        author_association="OWNER",
                        original_commit_sha=original_commits[index],
                    ),
                ),
            )
            for index in (1, 2)
        ),
    )
    record = type(
        "Record",
        (),
        {
            "material_digest": DIGEST,
            "verified_fix": real_fix,
            "urls": (root_urls[0],),
        },
    )()
    ancestry_calls: list[tuple[str, str]] = []

    def classify(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value in unavailable_refs:
            return ReviewExecutionRef(value, CommitRefKind.REVIEW_REF_UNAVAILABLE, "unavailable")
        return RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == real_head else CommitRefKind.PR_COMMIT,
        )

    def ancestor(left: RepositoryCommitRef, right: RepositoryCommitRef, **_kwargs: Any) -> bool:
        ancestry_calls.append((left.sha, right.sha))
        assert left.sha not in unavailable_refs
        assert right.sha not in unavailable_refs
        return True

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", ancestor)
    monkeypatch.setattr(
        evidence_module,
        "compute_material_manifest",
        lambda _root, *, head_ref_oid, **_kwargs: _material_manifest(head_ref_oid),
    )
    covered = validated_duplicate_reply_urls(
        candidate_urls=set(root_urls[1:]),
        threads=threads,
        fingerprint_records={fingerprint: record},
        material_digest=DIGEST,
        repo_root=Path(),
        snapshot=snapshot,
        repository="owner/repo",
        token="opaque",
    )

    assert covered == set(root_urls[1:])
    assert ancestry_calls
    assert all(
        left not in unavailable_refs and right not in unavailable_refs
        for left, right in ancestry_calls
    )


def _comment_connection(
    comments: list[dict[str, Any]], *, has_next: bool, cursor: str | None
) -> dict[str, Any]:
    return {
        "nodes": comments,
        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
    }


def _comment(url_suffix: str) -> dict[str, Any]:
    return {
        "author": {"login": "chatgpt-codex-connector"},
        "authorAssociation": "NONE",
        "body": "Potential issue: commit ancestry",
        "createdAt": "2026-07-15T10:00:00Z",
        "originalCommit": {"oid": FIX_SHA},
        "url": f"https://github.com/owner/repo/pull/42#discussion_r{url_suffix}",
    }


def test_review_threads_paginate_outer_and_inner_connections() -> None:
    calls = 0

    def request_json(_url: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        variables = kwargs["payload"]["variables"]
        if "id" in variables:
            return {
                "data": {
                    "node": {
                        "comments": _comment_connection(
                            [_comment("2")], has_next=False, cursor=None
                        )
                    }
                }
            }
        if variables["cursor"] is None:
            return {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "nodes": [
                                    {
                                        "comments": _comment_connection(
                                            [_comment("1")],
                                            has_next=True,
                                            cursor="comments-1",
                                        ),
                                        "id": "thread-1",
                                        "isResolved": True,
                                    }
                                ],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "threads-1",
                                },
                            }
                        }
                    }
                }
            }
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("3")], has_next=False, cursor=None
                                    ),
                                    "id": "thread-2",
                                    "isResolved": False,
                                }
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    threads = fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)

    assert calls == 3
    assert [len(thread.comments) for thread in threads] == [2, 1]


def test_review_comment_pagination_fails_closed_for_missing_cursor() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("1")], has_next=True, cursor=None
                                    ),
                                    "id": "thread-1",
                                    "isResolved": True,
                                }
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="cursor is missing or repeated"):
        fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)


def test_review_comments_use_one_global_retained_comment_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(identity_module, "_MAX_REVIEW_COMMENTS", 1)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("1")], has_next=False, cursor=None
                                    ),
                                    "id": "thread-1",
                                    "isResolved": True,
                                },
                                {
                                    "comments": _comment_connection(
                                        [_comment("2")], has_next=False, cursor=None
                                    ),
                                    "id": "thread-2",
                                    "isResolved": False,
                                },
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="global safety limit"):
        fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)


def test_review_comments_use_one_global_nested_page_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(identity_module, "_MAX_REVIEW_COMMENT_PAGES", 1)
    calls = 0

    def request_json(_url: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        variables = kwargs["payload"]["variables"]
        if "id" in variables:
            return {
                "data": {
                    "node": {
                        "comments": _comment_connection(
                            [_comment("2")], has_next=False, cursor=None
                        )
                    }
                }
            }
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("1")], has_next=True, cursor="comments-1"
                                    ),
                                    "id": "thread-1",
                                    "isResolved": True,
                                },
                                {
                                    "comments": _comment_connection(
                                        [_comment("3")], has_next=True, cursor="comments-2"
                                    ),
                                    "id": "thread-2",
                                    "isResolved": False,
                                },
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="global page limit"):
        fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)
    assert calls == 2


def test_material_digest_tracks_rename_mode_binary_and_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    tracked = repo / "tool.sh"
    tracked.write_text("echo one\n", encoding="utf-8")
    base = _commit(repo, "base")

    tracked.write_text("echo two\n", encoding="utf-8")
    first_head = _commit(repo, "content")
    first = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=first_head, pr_number=42
    )

    tracked.chmod(0o755)
    mode_head = _commit(repo, "mode")
    mode = compute_material_manifest(repo, base_ref_oid=base, head_ref_oid=mode_head, pr_number=42)
    assert mode.digest != first.digest

    tracked.rename(repo / "renamed.sh")
    (repo / "payload.bin").write_bytes(b"\x00\xff\x00")
    (repo / "tool-link").symlink_to("renamed.sh")
    final_head = _commit(repo, "rename binary symlink")
    final = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=final_head, pr_number=42
    )
    assert final.digest != mode.digest
    assert {entry.status for entry in final.entries} >= {"A", "D"}
    assert {entry.path for entry in final.entries} >= {
        "payload.bin",
        "renamed.sh",
        "tool-link",
        "tool.sh",
    }


def test_scan_receipt_rejects_path_traversal_and_incomplete_coverage(
    tmp_path: Path,
) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["artifacts"][0]["path"] = "../findings.json"
    _write_json(manifest_path, manifest)
    with pytest.raises(ReviewEvidenceError, match="escapes the scan root"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )

    manifest_path = _build_scan_bundle(tmp_path / "scan-2")
    coverage_path = manifest_path.parent / "coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["deferred"] = ["security surface"]
    coverage_raw = _write_json(coverage_path, coverage)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["scan"]["artifacts"]:
        if artifact["path"] == "coverage.json":
            artifact["sha256"] = hashlib.sha256(coverage_raw).hexdigest()
    _write_json(manifest_path, manifest)
    with pytest.raises(ReviewEvidenceError, match="coverage is incomplete"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def _duplicate_reply(fingerprint: str) -> str:
    return "\n".join(
        [
            "Disposition: NOT-A-BUG",
            f"Fingerprint: {fingerprint}",
            f"Duplicate-Of: {fingerprint}",
            "Evidence: material digest and verified FIX SHA",
            "Reason: reviewer ref is unavailable; canonical disposition reused",
        ]
    )


def test_duplicate_reply_requires_trusted_resolved_thread_and_real_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42, material_digest=DIGEST, verified_real_fix_sha=FIX_SHA
    )
    record = type(
        "Record",
        (),
        {
            "material_digest": DIGEST,
            "verified_fix": FIX_SHA,
            "urls": ("https://github.com/owner/repo/pull/42#discussion_canonical",),
        },
    )()
    canonical_finding = ReviewCommentEvidence(
        url=record.urls[0],
        body=f"Potential issue: commit ancestry says {FIX_SHA} cannot reach {UNAVAILABLE_SHA}",
        created_at="2026-07-15T09:00:00Z",
        author_login="chatgpt-codex-connector",
        author_association="NONE",
        original_commit_sha=FIX_SHA,
    )
    finding = ReviewCommentEvidence(
        **{
            **canonical_finding.__dict__,
            "url": "https://github.com/owner/repo/pull/42#discussion_duplicate",
            "created_at": "2026-07-15T10:00:00Z",
        }
    )
    reply = ReviewCommentEvidence(
        url="https://github.com/owner/repo/pull/42#discussion_r2",
        body=_duplicate_reply(fingerprint),
        created_at="2026-07-15T11:00:00Z",
        author_login="maintainer",
        author_association="OWNER",
        original_commit_sha=FIX_SHA,
    )
    canonical_thread = ReviewThreadEvidence("canonical-thread", True, (canonical_finding,))
    thread = ReviewThreadEvidence("duplicate-thread", True, (finding, reply))

    def classify(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value == UNAVAILABLE_SHA:
            return ReviewExecutionRef(
                value=value,
                kind=CommitRefKind.REVIEW_REF_UNAVAILABLE,
                reason="unavailable",
            )
        return RepositoryCommitRef(value, CommitRefKind.PR_COMMIT)

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(
        evidence_module,
        "compute_material_manifest",
        lambda _root, *, head_ref_oid, **_kwargs: _material_manifest(head_ref_oid),
    )

    covered = validated_duplicate_reply_urls(
        candidate_urls={finding.url},
        threads=(canonical_thread, thread),
        fingerprint_records={fingerprint: record},
        material_digest=DIGEST,
        repo_root=Path(),
        snapshot=_snapshot(),
        repository="owner/repo",
        token="opaque",
    )
    assert covered == {finding.url}

    spoofed = ReviewThreadEvidence(
        "thread",
        True,
        (finding, ReviewCommentEvidence(**{**reply.__dict__, "author_association": "NONE"})),
    )
    assert not validated_duplicate_reply_urls(
        candidate_urls={finding.url},
        threads=(canonical_thread, spoofed),
        fingerprint_records={fingerprint: record},
        material_digest=DIGEST,
        repo_root=Path(),
        snapshot=_snapshot(),
        repository="owner/repo",
        token="opaque",
    )

    def classify_unknown(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value == UNAVAILABLE_SHA:
            return ReviewExecutionRef(
                value=value,
                kind=CommitRefKind.API_UNKNOWN,
                reason="rate limited",
            )
        return RepositoryCommitRef(value, CommitRefKind.PR_COMMIT)

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify_unknown)
    with pytest.raises(ReviewEvidenceError, match="API_UNKNOWN"):
        validated_duplicate_reply_urls(
            candidate_urls={finding.url},
            threads=(canonical_thread, thread),
            fingerprint_records={fingerprint: record},
            material_digest=DIGEST,
            repo_root=Path(),
            snapshot=_snapshot(),
            repository="owner/repo",
            token="opaque",
        )


def test_duplicate_reply_binds_finding_original_commits_to_material_digest(
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
    material_sha = _commit(repo, "material")
    material_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_sha,
        pr_number=42,
    )
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text("governance-only\n", encoding="utf-8")
    governance_sha = _commit(repo, "governance closeout")
    governance_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=governance_sha,
        pr_number=42,
    )
    assert governance_manifest.digest == material_manifest.digest
    source.write_text("ENFORCED = False\n", encoding="utf-8")
    changed_sha = _commit(repo, "material change")
    changed_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=changed_sha,
        pr_number=42,
    )
    assert changed_manifest.digest != material_manifest.digest

    def classify(value: str, snapshot: PrSnapshot, **_kwargs: Any) -> Any:
        if value == UNAVAILABLE_SHA:
            return ReviewExecutionRef(
                value=value,
                kind=CommitRefKind.REVIEW_REF_UNAVAILABLE,
                reason="unavailable",
            )
        return RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == snapshot.head_sha else CommitRefKind.PR_COMMIT,
        )

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", lambda *_a, **_k: True)

    canonical_url = "https://github.com/owner/repo/pull/42#discussion_canonical"
    duplicate_url = "https://github.com/owner/repo/pull/42#discussion_duplicate"

    def evidence(
        *, digest: str, canonical_original: str, duplicate_original: str
    ) -> tuple[str, Any, tuple[ReviewThreadEvidence, ...]]:
        fingerprint = unavailable_review_ref_fingerprint(
            pr_number=42,
            material_digest=digest,
            verified_real_fix_sha=material_sha,
        )
        record = type(
            "Record",
            (),
            {
                "material_digest": digest,
                "verified_fix": material_sha,
                "urls": (canonical_url,),
            },
        )()
        finding_body = (
            f"Potential issue: commit ancestry says {material_sha} cannot reach {UNAVAILABLE_SHA}"
        )
        canonical = ReviewCommentEvidence(
            url=canonical_url,
            body=finding_body,
            created_at="2026-07-15T09:00:00Z",
            author_login="chatgpt-codex-connector",
            author_association="NONE",
            original_commit_sha=canonical_original,
        )
        duplicate = ReviewCommentEvidence(
            url=duplicate_url,
            body=finding_body,
            created_at="2026-07-15T10:00:00Z",
            author_login="chatgpt-codex-connector",
            author_association="NONE",
            original_commit_sha=duplicate_original,
        )
        reply = ReviewCommentEvidence(
            url=f"{duplicate_url}-reply",
            body=_duplicate_reply(fingerprint),
            created_at="2026-07-15T11:00:00Z",
            author_login="maintainer",
            author_association="OWNER",
            original_commit_sha=duplicate_original,
        )
        threads = (
            ReviewThreadEvidence("canonical", True, (canonical,)),
            ReviewThreadEvidence("duplicate", True, (duplicate, reply)),
        )
        return fingerprint, record, threads

    governance_fingerprint, governance_record, governance_threads = evidence(
        digest=material_manifest.digest,
        canonical_original=material_sha,
        duplicate_original=governance_sha,
    )
    governance_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=governance_sha,
        commits=(
            PrCommitEvidence(material_sha, None),
            PrCommitEvidence(governance_sha, None),
        ),
    )
    assert validated_duplicate_reply_urls(
        candidate_urls={duplicate_url},
        threads=governance_threads,
        fingerprint_records={governance_fingerprint: governance_record},
        material_digest=material_manifest.digest,
        repo_root=repo,
        snapshot=governance_snapshot,
        repository="owner/repo",
        token="opaque",
    ) == {duplicate_url}

    stale_fingerprint, stale_record, stale_threads = evidence(
        digest=changed_manifest.digest,
        canonical_original=material_sha,
        duplicate_original=changed_sha,
    )
    changed_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=changed_sha,
        commits=(
            PrCommitEvidence(material_sha, None),
            PrCommitEvidence(governance_sha, None),
            PrCommitEvidence(changed_sha, None),
        ),
    )
    with pytest.raises(ReviewEvidenceError, match="different material digest"):
        validated_duplicate_reply_urls(
            candidate_urls={duplicate_url},
            threads=stale_threads,
            fingerprint_records={stale_fingerprint: stale_record},
            material_digest=changed_manifest.digest,
            repo_root=repo,
            snapshot=changed_snapshot,
            repository="owner/repo",
            token="opaque",
        )


def test_duplicate_reply_parser_rejects_extra_fields() -> None:
    fingerprint = "sha256:" + "a" * 64
    assert parse_duplicate_disposition_reply(_duplicate_reply(fingerprint)) == fingerprint
    with pytest.raises(ReviewEvidenceError, match="five exact fields"):
        parse_duplicate_disposition_reply(_duplicate_reply(fingerprint) + "\nExtra: no")


def test_closeout_renderer_round_trips_fingerprint_record(tmp_path: Path) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42, material_digest=DIGEST, verified_real_fix_sha=FIX_SHA
    )
    state = {
        "dispositions": [
            {
                "cause": "unavailable_review_ref_ancestry",
                "disposition": "NOT-A-BUG",
                "evidence": "GitHub Commit API 404",
                "fingerprint": fingerprint,
                "material_digest": DIGEST,
                "reason": "review execution ref is unavailable",
                "url": "https://github.com/owner/repo/pull/42#discussion_r1",
                "verified_fix": FIX_SHA,
            }
        ],
        "experiment_result": None,
        "packet": None,
        "pr_number": 42,
    }
    rendered = closeout_module._render_mapping(state, _seal(receipt))
    assert validate_mapping_artifact_text(rendered) == []
    records = parse_canonical_fingerprint_records(rendered, pr_number=42)
    assert records[fingerprint].verified_fix == FIX_SHA


def _rendered_fingerprint_mapping(tmp_path: Path) -> tuple[str, str, str]:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    url = "https://github.com/owner/repo/pull/42#discussion_r1"
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42, material_digest=DIGEST, verified_real_fix_sha=FIX_SHA
    )
    state = {
        "dispositions": [
            {
                "cause": "unavailable_review_ref_ancestry",
                "disposition": "NOT-A-BUG",
                "evidence": "GitHub Commit API 404",
                "fingerprint": fingerprint,
                "material_digest": DIGEST,
                "reason": "review execution ref is unavailable",
                "url": url,
                "verified_fix": FIX_SHA,
            }
        ],
        "experiment_result": None,
        "packet": None,
        "pr_number": 42,
    }
    return closeout_module._render_mapping(state, _seal(receipt)), fingerprint, url


def test_mapping_validator_rejects_non_recomputing_fingerprint(tmp_path: Path) -> None:
    rendered, fingerprint, _url = _rendered_fingerprint_mapping(tmp_path)
    tampered = rendered.replace(fingerprint, "sha256:" + "b" * 64, 1)

    assert any(
        "canonical fingerprint record does not recompute" in error
        for error in validate_mapping_artifact_text(tampered)
    )


def test_mapping_validator_rejects_fingerprint_for_different_material(
    tmp_path: Path,
) -> None:
    rendered, fingerprint, _url = _rendered_fingerprint_mapping(tmp_path)
    other_digest = "sha256:" + "c" * 64
    other_fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42,
        material_digest=other_digest,
        verified_real_fix_sha=FIX_SHA,
    )
    tampered = rendered.replace(fingerprint, other_fingerprint, 1).replace(
        f"Material-Digest: {DIGEST}",
        f"Material-Digest: {other_digest}",
        1,
    )

    assert any(
        "canonical fingerprint record does not match sealed material" in error
        for error in validate_mapping_artifact_text(tampered)
    )


def test_mapping_validator_rejects_fingerprint_with_multiple_urls(tmp_path: Path) -> None:
    rendered, _fingerprint, url = _rendered_fingerprint_mapping(tmp_path)
    tampered = rendered.replace(
        f"- {url}",
        f"- {url}\n- https://github.com/owner/repo/pull/42#discussion_r2",
        1,
    )

    assert any(
        "canonical fingerprint record must identify exactly one URL" in error
        for error in validate_mapping_artifact_text(tampered)
    )


@pytest.mark.parametrize(
    ("module", "error_type"),
    [
        (evidence_module, ReviewEvidenceError),
        (closeout_module, closeout_module.CloseoutError),
    ],
)
def test_git_path_normalizes_relative_which_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    error_type: type[Exception],
) -> None:
    del error_type
    executable = tmp_path / "tools" / "git"
    executable.parent.mkdir()
    executable.write_text("git", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "tools/git")

    assert module._git_path() == str(executable.resolve())


@pytest.mark.parametrize(
    ("module", "error_type"),
    [
        (evidence_module, ReviewEvidenceError),
        (closeout_module, closeout_module.CloseoutError),
    ],
)
def test_git_path_rejects_unresolvable_which_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    error_type: type[Exception],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "missing/git")

    with pytest.raises(error_type, match="could not be resolved"):
        module._git_path()


def _write_backlog_entry(path: Path, *, include_dod: bool = True) -> None:
    lines = [
        '<a id="ledger-p1-governance-followup"></a>',
        "- [ ] P1: Governance follow-up",
        "  - Owner: @owner",
        "  - Priority: P1",
        "  - Target PR: #999",
        "  - Reason (EN): Keep the current PR bounded.",
        "  - Links: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`",
    ]
    if include_dod:
        lines.append("  - DoD: Ship the bounded follow-up with deterministic tests.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_deferred_disposition_requires_complete_canonical_backlog_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "BACKLOG_LEDGER.md"
    _write_backlog_entry(ledger)
    monkeypatch.setattr(closeout_module, "BACKLOG_LEDGER_PATH", ledger)
    reference = "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-governance-followup"

    assert closeout_module._validated_backlog_reference(reference) == reference


def test_deferred_disposition_rejects_incomplete_backlog_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "BACKLOG_LEDGER.md"
    _write_backlog_entry(ledger, include_dod=False)
    monkeypatch.setattr(closeout_module, "BACKLOG_LEDGER_PATH", ledger)

    with pytest.raises(closeout_module.CloseoutError, match="DoD"):
        closeout_module._validated_backlog_reference(
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-governance-followup"
        )


def test_deferred_disposition_rejects_noncanonical_backlog_reference() -> None:
    with pytest.raises(closeout_module.CloseoutError, match="BACKLOG_LEDGER"):
        closeout_module._validated_backlog_reference("docs/roadmap/OTHER.md#ledger-p1-item")


def test_authoritative_docs_preserve_phase2_body_scaffolding() -> None:
    template = (closeout_module.REPO_ROOT / ".github/pull_request_template.md").read_text(
        encoding="utf-8"
    )
    agents = (closeout_module.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    runbook = (closeout_module.REPO_ROOT / "RUNBOOK_AGENT.md").read_text(encoding="utf-8")

    assert template.count("docs/review/PR_<N>_FIXED_MAPPING.md") == 1
    assert "## Discussion Thread Pass" in template
    assert "### Fixed in Commit Mapping" in template
    assert "- [ ] Discussion-thread pass completed" in template
    assert "- [ ] Fixed in commit mapping completed" in template
    for document in (agents, runbook):
        assert "## Discussion Thread Pass" in document
        assert "### Fixed in Commit Mapping" in document
        assert "checked checklist" in document


def test_closeout_init_is_atomic_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(closeout_module, "STATE_ROOT", tmp_path / "state")
    args = Namespace(
        repo="owner/repo",
        pr_number=42,
        packet="artifacts/orchestration/task_packets/packet.json",
        experiment_result="artifacts/orchestration/experiments/results/result.json",
    )
    closeout_module._cmd_init(args)
    first = closeout_module._state_path(42).read_bytes()
    closeout_module._cmd_init(args)
    assert closeout_module._state_path(42).read_bytes() == first
