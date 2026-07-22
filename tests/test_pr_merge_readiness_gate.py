from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci import check_pr_merge_readiness as merge_gate
from scripts.ci.check_pr_merge_readiness import (
    _canonical_artifact_markdown_link_count,
    _is_actionable,
    _mapped_urls,
)
from scripts.orchestration.pr_commit_identity import (
    CodexConnectorAdvisoryReactionEvidence,
    CodexReviewEvidence,
    CodexReviewSourceUnavailabilityEvidence,
    CommitRefKind,
    PrCommitEvidence,
    PrSnapshot,
    RepositoryCommitRef,
    ReviewCreditOutageEvidence,
    SecurityOutageOverrideEvidence,
)
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    ReviewEvidenceError,
    build_review_credit_outage_receipt,
    build_review_source_positive_response_receipt,
    build_review_source_unavailability_receipt,
    build_security_outage_override_receipt,
    compute_material_manifest,
    render_embedded_review_seal,
)

OUTAGE_HEAD_SHA = "d" * 40


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


def test_canonical_artifact_link_count_requires_true_markdown_destination() -> None:
    body = """
Plain text: docs/review/PR_42_FIXED_MAPPING.md
- [canonical artifact](https://github.com/owner/repo/blob/codex/review/docs/review/PR_42_FIXED_MAPPING.md)
\\[escaped literal](docs/review/PR_42_FIXED_MAPPING.md)
    [indented code](docs/review/PR_42_FIXED_MAPPING.md)
<TAB>[tab-indented code](docs/review/PR_42_FIXED_MAPPING.md)
`[inline code](docs/review/PR_42_FIXED_MAPPING.md)`
``[double inline code](docs/review/PR_42_FIXED_MAPPING.md)``
<!-- [html comment](docs/review/PR_42_FIXED_MAPPING.md) -->
```markdown
[fenced example](docs/review/PR_42_FIXED_MAPPING.md)
```
""".replace("<TAB>", "\t")

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "codex/review") == 1


def test_canonical_artifact_link_count_accepts_full_github_blob_url() -> None:
    body = (
        "- [canonical artifact](https://github.com/owner/repo/blob/branch/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "branch") == 1


def test_canonical_artifact_link_count_does_not_require_fixed_link_text() -> None:
    body = (
        "- [fixed mapping](https://github.com/owner/repo/blob/branch/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "branch") == 1


def test_canonical_artifact_link_count_parses_encoded_ref_before_decoding() -> None:
    body = (
        "- [fixed mapping](https://github.com/owner/repo/blob/feature%23x/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "feature#x") == 1


def test_canonical_artifact_link_count_rejects_trailing_duplicate() -> None:
    url = "https://github.com/owner/repo/blob/main/docs/review/PR_42_FIXED_MAPPING.md"
    body = f"- [canonical artifact]({url}) and [duplicate]({url})"

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 0


def test_canonical_artifact_link_count_rejects_duplicate_with_another_label() -> None:
    url = "https://github.com/owner/repo/blob/main/docs/review/PR_42_FIXED_MAPPING.md"
    body = f"- [canonical artifact]({url})\n- [duplicate]({url})"

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 2


def test_merge_gate_does_not_require_optional_markdown_runtime_dependency() -> None:
    source = Path(merge_gate.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert "markdown_it" not in imported_roots


def test_canonical_artifact_link_count_rejects_duplicate_and_foreign_links() -> None:
    duplicate = "\n".join(
        [
            "- [canonical artifact](https://github.com/owner/repo/blob/codex/one/"
            "docs/review/PR_42_FIXED_MAPPING.md)",
            "- [canonical artifact](https://github.com/owner/repo/blob/codex/one/"
            "docs/review/PR_42_FIXED_MAPPING.md)",
        ]
    )
    foreign_host = "- [canonical artifact](https://example.com/docs/review/PR_42_FIXED_MAPPING.md)"
    foreign_repo = (
        "- [canonical artifact](https://github.com/other/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )
    wrong_relative = "- [canonical artifact](other/docs/review/PR_42_FIXED_MAPPING.md)"
    repo_relative = "- [canonical artifact](docs/review/PR_42_FIXED_MAPPING.md)"
    query_variant = (
        "- [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md?raw=1)"
    )
    fragment_variant = (
        "- [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md#section)"
    )

    assert _canonical_artifact_markdown_link_count(duplicate, 42, "owner/repo", "codex/one") == 2
    assert _canonical_artifact_markdown_link_count(foreign_host, 42, "owner/repo", "main") == 0
    assert _canonical_artifact_markdown_link_count(foreign_repo, 42, "owner/repo", "main") == 0
    assert _canonical_artifact_markdown_link_count(wrong_relative, 42, "owner/repo", "main") == 0
    assert _canonical_artifact_markdown_link_count(repo_relative, 42, "owner/repo", "main") == 0
    assert _canonical_artifact_markdown_link_count(query_variant, 42, "owner/repo", "main") == 0
    assert _canonical_artifact_markdown_link_count(fragment_variant, 42, "owner/repo", "main") == 0


def test_canonical_artifact_link_count_rejects_extra_segments_after_head_ref() -> None:
    body = (
        "- [canonical artifact](https://github.com/owner/repo/blob/main/other/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 0


@pytest.mark.parametrize(
    "body",
    [
        "<!-- - [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)",
        "```markdown\n- [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)",
        "~~~markdown\n- [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)",
    ],
)
def test_canonical_artifact_link_count_rejects_unclosed_non_rendered_regions(
    body: str,
) -> None:
    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 0


@pytest.mark.parametrize("tag", ["pre", "script", "style", "textarea", "div"])
def test_canonical_artifact_link_count_rejects_raw_html_blocks(tag: str) -> None:
    body = (
        f"<{tag}>\n"
        "- [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)\n"
        f"</{tag}>"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 0


def test_canonical_artifact_link_count_allows_link_after_void_html_tag() -> None:
    body = (
        "<br>\n"
        "- [canonical artifact](https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 1


def _pre_closeout_artifact(*urls: str) -> str:
    entries = "\n".join(f"- {url}" for url in urls)
    return f"""## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: deterministic pre-closeout fixture
Reason: fixture feedback is already satisfied
{entries}
"""


def _configure_pre_closeout_main(
    monkeypatch: pytest.MonkeyPatch,
    *,
    artifact: str,
    actionable_items: list[merge_gate.ActionableItem],
) -> None:
    head_sha = "a" * 40
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha="b" * 40,
        head_sha=head_sha,
        commits=(PrCommitEvidence(head_sha, None),),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "opaque")
    monkeypatch.setenv("GH_TOKEN", "opaque")
    monkeypatch.setattr(merge_gate, "REVIEW_SEAL_REQUIRED_FROM_PR", 100)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_pr_merge_readiness.py",
            "--pr-number",
            "42",
            "--repo",
            "owner/repo",
            "--pre-closeout",
        ],
    )
    monkeypatch.setattr(
        merge_gate,
        "_fetch_pr_context",
        lambda *_a, **_k: (
            42,
            "owner/repo",
            False,
            "- [canonical artifact](https://github.com/owner/repo/blob/codex/review/"
            "docs/review/PR_42_FIXED_MAPPING.md)",
            "codex/review",
        ),
    )
    monkeypatch.setattr(merge_gate, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(merge_gate, "_local_head_sha", lambda: head_sha)
    monkeypatch.setattr(
        merge_gate,
        "_pre_closeout_dirty_paths",
        lambda: {"docs/review/PR_42_FIXED_MAPPING.md"},
    )
    monkeypatch.setattr(merge_gate, "fetch_review_threads", lambda *_a, **_k: ())
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", lambda **_k: actionable_items)
    monkeypatch.setattr(merge_gate, "read_mapping_artifact", lambda _pr: artifact)
    monkeypatch.setattr(merge_gate, "assert_snapshot_unchanged", lambda *_a, **_k: None)


def test_direct_pre_closeout_requires_gh_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "opaque")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_pr_merge_readiness.py",
            "--pr-number",
            "42",
            "--repo",
            "owner/repo",
            "--pre-closeout",
        ],
    )

    assert merge_gate.main() == 1
    assert "GH_TOKEN is also required" in capsys.readouterr().out


def test_pre_closeout_rejects_non_mapping_dirty_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(
            "https://github.com/owner/repo/pull/42#issuecomment-previous"
        ),
        actionable_items=[],
    )
    monkeypatch.setattr(
        merge_gate,
        "_pre_closeout_dirty_paths",
        lambda: {
            "docs/review/PR_42_FIXED_MAPPING.md",
            "scripts/ci/check_pr_merge_readiness.py",
        },
    )

    assert merge_gate.main() == 1
    output = capsys.readouterr().out
    assert "canonical mapping artifact to be the only dirty path" in output
    assert "scripts/ci/check_pr_merge_readiness.py" in output


def test_pre_closeout_dirty_paths_normalizes_git_status_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(merge_gate.shutil, "which", lambda _name: "/usr/bin/git")

    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=["/usr/bin/git", "status"], timeout=30)

    monkeypatch.setattr(merge_gate.subprocess, "run", timeout)

    with pytest.raises(ValueError, match="git status timed out"):
        merge_gate._pre_closeout_dirty_paths()


def test_pre_closeout_dirty_paths_rejects_staged_mapping_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(merge_gate.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(
        merge_gate.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["/usr/bin/git", "status"],
            returncode=0,
            stdout="MM docs/review/PR_42_FIXED_MAPPING.md\n",
            stderr="",
        ),
    )

    with pytest.raises(ValueError, match="staged changes are forbidden"):
        merge_gate._pre_closeout_dirty_paths()


def test_pre_closeout_requires_explicit_top_level_review_mapping(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    review_id = 7
    top_level = "https://github.com/owner/repo/pull/42#pullrequestreview-7"
    child = "https://github.com/owner/repo/pull/42#discussion_r7"
    actionable_items = [
        merge_gate.ActionableItem(
            author="reviewer[bot]",
            url=top_level,
            created_at="2026-07-16T00:43:28Z",
            kind="review",
            review_id=review_id,
        ),
        merge_gate.ActionableItem(
            author="reviewer[bot]",
            url=child,
            created_at="2026-07-16T00:43:27Z",
            kind="review_comment",
            review_id=review_id,
        ),
    ]
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(child),
        actionable_items=actionable_items,
    )

    assert merge_gate.main() == 1
    output = capsys.readouterr().out
    assert f"UNMAPPED: reviewer[bot] [review] {top_level}" in output
    assert "pre-closeout review-governance check failed" in output


def test_pre_closeout_accepts_explicit_issue_inline_and_top_level_mappings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    issue = "https://github.com/owner/repo/pull/42#issuecomment-1"
    top_level = "https://github.com/owner/repo/pull/42#pullrequestreview-7"
    child = "https://github.com/owner/repo/pull/42#discussion_r7"
    actionable_items = [
        merge_gate.ActionableItem("bot[bot]", issue, "2026-07-16T00:43:26Z", "issue_comment"),
        merge_gate.ActionableItem("bot[bot]", top_level, "2026-07-16T00:43:27Z", "review", 7),
        merge_gate.ActionableItem("bot[bot]", child, "2026-07-16T00:43:28Z", "review_comment", 7),
    ]
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(issue, top_level, child),
        actionable_items=actionable_items,
    )

    assert merge_gate.main() == 0
    output = capsys.readouterr().out
    assert "all live actionable bot issue comments, bot inline comments" in output
    assert "not merge-readiness evidence" in output


def test_pre_closeout_fails_when_actionable_inventory_changes_during_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mapped = merge_gate.ActionableItem(
        "bot[bot]",
        "https://github.com/owner/repo/pull/42#issuecomment-1",
        "2026-07-16T00:43:26Z",
        "issue_comment",
    )
    late_review = merge_gate.ActionableItem(
        "bot[bot]",
        "https://github.com/owner/repo/pull/42#pullrequestreview-7",
        "2026-07-16T00:43:27Z",
        "review",
        7,
    )
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(mapped.url),
        actionable_items=[mapped],
    )
    inventories = iter(([mapped], [mapped, late_review]))
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", lambda **_k: next(inventories))

    assert merge_gate.main() == 1
    assert "actionable bot review inventory changed" in capsys.readouterr().out


def test_pre_closeout_fails_when_bot_edits_existing_actionable_body(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    url = "https://github.com/owner/repo/pull/42#issuecomment-1"
    initial = merge_gate.ActionableItem(
        "bot[bot]",
        url,
        "2026-07-16T00:43:26Z",
        "issue_comment",
        updated_at="2026-07-16T00:43:26Z",
        body_digest=merge_gate._comment_body_digest("P1: initial finding"),
    )
    edited = merge_gate.ActionableItem(
        "bot[bot]",
        url,
        "2026-07-16T00:43:26Z",
        "issue_comment",
        updated_at="2026-07-16T00:44:00Z",
        body_digest=merge_gate._comment_body_digest("P1: edited finding"),
    )
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(url),
        actionable_items=[initial],
    )
    inventories = iter(([initial], [edited]))
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", lambda **_k: next(inventories))

    assert merge_gate.main() == 1
    assert "actionable bot review inventory changed" in capsys.readouterr().out


def test_pre_closeout_fails_when_pr_body_changes_during_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(
            "https://github.com/owner/repo/pull/42#issuecomment-previous"
        ),
        actionable_items=[],
    )
    canonical_body = (
        "- [canonical artifact](https://github.com/owner/repo/blob/codex/review/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )
    contexts = iter(
        (
            (42, "owner/repo", False, canonical_body, "codex/review"),
            (42, "owner/repo", False, f"{canonical_body}\nconcurrent edit", "codex/review"),
        )
    )
    monkeypatch.setattr(merge_gate, "_fetch_pr_context", lambda *_a, **_k: next(contexts))

    assert merge_gate.main() == 1
    assert "live PR body or draft state changed" in capsys.readouterr().out


def test_pre_closeout_fails_when_dirty_paths_change_during_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(
            "https://github.com/owner/repo/pull/42#issuecomment-previous"
        ),
        actionable_items=[],
    )
    dirty_snapshots = iter(
        (
            {"docs/review/PR_42_FIXED_MAPPING.md"},
            {
                "docs/review/PR_42_FIXED_MAPPING.md",
                "scripts/ci/check_pr_merge_readiness.py",
            },
        )
    )
    monkeypatch.setattr(
        merge_gate,
        "_pre_closeout_dirty_paths",
        lambda: next(dirty_snapshots),
    )

    assert merge_gate.main() == 1
    assert "local working tree changed" in capsys.readouterr().out


def test_pre_closeout_fails_when_mapping_artifact_changes_during_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    initial_artifact = _pre_closeout_artifact(
        "https://github.com/owner/repo/pull/42#issuecomment-previous"
    )
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=initial_artifact,
        actionable_items=[],
    )
    artifacts = iter((initial_artifact, f"{initial_artifact}\nconcurrent edit\n"))
    monkeypatch.setattr(merge_gate, "read_mapping_artifact", lambda _pr: next(artifacts))

    assert merge_gate.main() == 1
    assert "canonical mapping artifact changed" in capsys.readouterr().out


def test_pre_closeout_fails_when_local_head_changes_during_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(
            "https://github.com/owner/repo/pull/42#issuecomment-previous"
        ),
        actionable_items=[],
    )
    heads = iter(("a" * 40, "c" * 40))
    monkeypatch.setattr(merge_gate, "_local_head_sha", lambda: next(heads))

    assert merge_gate.main() == 1
    assert "local HEAD changed" in capsys.readouterr().out


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
    observed_heads: list[str | None] = []

    def fetch_metadata(*args: Any, **_kwargs: Any) -> tuple[bool, str, str, list[dict[str, Any]]]:
        observed_heads.append(args[3])
        return False, "CLEAN", "main", nodes

    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        fetch_metadata,
    )

    merge_gate._validate_operator_outage_security_checks(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_head_sha=OUTAGE_HEAD_SHA,
    )
    assert observed_heads == [OUTAGE_HEAD_SHA]


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
        expected_head_sha=OUTAGE_HEAD_SHA,
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

    with pytest.raises(ReviewEvidenceError, match="security=pending/status") as exc_info:
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_head_sha=OUTAGE_HEAD_SHA,
        )
    message = str(exc_info.value)
    assert (
        "Pending or not-yet-visible exact-head checks may be retried only "
        "within the bounded CI wait" in message
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
            expected_head_sha=OUTAGE_HEAD_SHA,
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
            expected_head_sha=OUTAGE_HEAD_SHA,
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
            expected_head_sha=OUTAGE_HEAD_SHA,
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
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


@pytest.mark.parametrize(
    ("target", "status", "conclusion", "expected"),
    [
        ("security", "IN_PROGRESS", "", "security=pending/status"),
        ("security", "COMPLETED", "SKIPPED", "security=failed/SKIPPED"),
        (
            "Analyze (python)",
            "COMPLETED",
            "SKIPPED",
            r"Analyze \(python\)=failed/SKIPPED",
        ),
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

    with pytest.raises(ReviewEvidenceError, match=expected) as exc_info:
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_head_sha=OUTAGE_HEAD_SHA,
        )
    assert "failed or untrusted checks remain terminal" in str(exc_info.value)


def test_operator_outage_wait_retries_pending_checks_until_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []
    sleeps: list[float] = []

    def validate(**_kwargs: Any) -> None:
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise merge_gate._OutageSecurityChecksPending("security=pending/status")

    monkeypatch.setattr(merge_gate, "_validate_operator_outage_security_checks", validate)
    monkeypatch.setattr(merge_gate.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(merge_gate.time, "sleep", sleeps.append)

    merge_gate._wait_for_operator_outage_security_checks(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_head_sha=OUTAGE_HEAD_SHA,
        security_required=True,
        timeout_seconds=30,
        poll_interval_seconds=5,
    )

    assert attempts == [1, 2, 3]
    assert sleeps == [5.0, 5.0]


def test_operator_outage_wait_does_not_retry_terminal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []

    def validate(**_kwargs: Any) -> None:
        attempts.append(1)
        raise ReviewEvidenceError("security=failed/FAILURE")

    monkeypatch.setattr(merge_gate, "_validate_operator_outage_security_checks", validate)
    monkeypatch.setattr(
        merge_gate.time,
        "sleep",
        lambda _seconds: pytest.fail("terminal failures must not be retried"),
    )

    with pytest.raises(ReviewEvidenceError, match="security=failed/FAILURE"):
        merge_gate._wait_for_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_head_sha=OUTAGE_HEAD_SHA,
            security_required=True,
            timeout_seconds=30,
        )

    assert attempts == [1]


def test_operator_outage_wait_times_out_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((0.0, 6.0))

    monkeypatch.setattr(
        merge_gate,
        "_validate_operator_outage_security_checks",
        lambda **_kwargs: (_ for _ in ()).throw(
            merge_gate._OutageSecurityChecksPending("security-scan=missing")
        ),
    )
    monkeypatch.setattr(merge_gate.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(
        merge_gate.time,
        "sleep",
        lambda _seconds: pytest.fail("expired waits must not sleep"),
    )

    with pytest.raises(ReviewEvidenceError, match="timed out.*after 5s"):
        merge_gate._wait_for_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_head_sha=OUTAGE_HEAD_SHA,
            security_required=True,
            timeout_seconds=5,
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
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


@pytest.mark.parametrize(
    ("target", "kwargs"),
    [
        ("security", {"workflow_name": "Evil workflow"}),
        ("security-scan", {"app_database_id": 999}),
        ("Analyze (python)", {"app_slug": "foreign-codeql"}),
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

    with pytest.raises(
        ReviewEvidenceError,
        match=rf"{re.escape(target)}=untrusted-producer",
    ):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


def test_operator_outage_override_rejects_foreign_status_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        _check_node(name)
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        if name != "Analyze (python)"
    ]
    nodes.append(
        {
            "__typename": "StatusContext",
            "context": "Analyze (python)",
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

    with pytest.raises(
        ReviewEvidenceError,
        match=r"Analyze \(python\)=untrusted-producer",
    ):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_head_sha=OUTAGE_HEAD_SHA,
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


@pytest.mark.parametrize("reaction_content", ["+1", "heart", "hooray", "rocket"])
def test_ci_gate_accepts_trusted_positive_response_without_review_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reaction_content: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    (repo / "README.md").write_text("material\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    manifest = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=42
    )
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": build_review_source_positive_response_receipt(
            material_digest=manifest.digest,
            material_head_sha=material_head,
            response_reference=reaction_reference,
            response_created_at="2026-07-15T11:00:00Z",
            response_content=reaction_content,
        ),
        "codex_security": _receipt(base_sha, material_head),
        "material": {
            "base_ref_oid": base_sha,
            "digest": manifest.digest,
            "material_head_sha": material_head,
            "merge_base_sha": manifest.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }
    artifact = _artifact_with_seal(seal)
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=material_head,
        commits=(PrCommitEvidence(material_head, None),),
    )
    verifier_calls: list[tuple[str | None, str | None]] = []

    def verify_response(*_args: Any, **kwargs: Any) -> CodexConnectorAdvisoryReactionEvidence:
        verifier_calls.append(
            (kwargs.get("expected_commit_ref"), kwargs.get("expected_live_pr_head_ref"))
        )
        return CodexConnectorAdvisoryReactionEvidence(
            reference=reaction_reference,
            created_at="2026-07-15T11:00:00Z",
            content=reaction_content,
        )

    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(merge_gate, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(merge_gate, "verify_codex_review_reference", verify_response)

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
    )

    assert validated["code_review"]["review_claim"] == "none"
    assert validated["code_review"]["source_status"] == "positive_response"
    assert verifier_calls == [(material_head, material_head)]

    stale_seal = dict(seal)
    stale_seal["code_review"] = dict(seal["code_review"])
    stale_seal["code_review"]["response_content"] = "heart" if reaction_content != "heart" else "+1"
    with pytest.raises(ReviewEvidenceError, match="positive response receipt is stale"):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(stale_seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
        )

    mapping_path = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    mapping_path.parent.mkdir(parents=True)
    mapping_path.write_text("mapping-only\n", encoding="utf-8")
    mapping_head = _commit(repo, "mapping-only")
    mapping_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=mapping_head,
        commits=(*snapshot.commits, PrCommitEvidence(mapping_head, None)),
    )
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_COMMIT if value == material_head else CommitRefKind.PR_HEAD,
        ),
    )

    def verify_successor(*_args: Any, **kwargs: Any) -> CodexConnectorAdvisoryReactionEvidence:
        verifier_calls.append(
            (kwargs.get("expected_commit_ref"), kwargs.get("expected_live_pr_head_ref"))
        )
        return CodexConnectorAdvisoryReactionEvidence(
            reference="https://github.com/owner/repo/pull/42#reaction-789",
            created_at="2026-07-15T12:00:00Z",
            content=reaction_content,
        )

    monkeypatch.setattr(merge_gate, "verify_codex_review_reference", verify_successor)
    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=mapping_snapshot,
        token="opaque",
    )
    assert validated["code_review"]["response_reference"] == reaction_reference
    assert verifier_calls[-1] == (material_head, mapping_head)

    (repo / "README.md").write_text("later material\n", encoding="utf-8")
    changed_head = _commit(repo, "later material")
    changed_manifest = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=changed_head, pr_number=42
    )
    tampered_seal = json.loads(json.dumps(seal))
    tampered_seal["material"]["digest"] = changed_manifest.digest
    tampered_seal["code_review"] = build_review_source_positive_response_receipt(
        material_digest=changed_manifest.digest,
        material_head_sha=material_head,
        response_reference=reaction_reference,
        response_created_at="2026-07-15T11:00:00Z",
        response_content=reaction_content,
    )
    changed_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=changed_head,
        commits=(*mapping_snapshot.commits, PrCommitEvidence(changed_head, None)),
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="positive response material head has a different material digest",
    ):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(tampered_seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=changed_snapshot,
            token="opaque",
        )


def test_ci_gate_rejects_positive_response_in_exact_review_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    (repo / "README.md").write_text("material\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    manifest = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=42
    )
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": material_head,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": reaction_reference,
            "reviewed_material_digest": manifest.digest,
            "status": "completed",
        },
        "codex_security": _receipt(base_sha, material_head),
        "material": {
            "base_ref_oid": base_sha,
            "digest": manifest.digest,
            "material_head_sha": material_head,
            "merge_base_sha": manifest.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=material_head,
        commits=(PrCommitEvidence(material_head, None),),
    )

    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: CodexConnectorAdvisoryReactionEvidence(
            reference=reaction_reference,
            created_at="2026-07-15T11:00:00Z",
            content="+1",
        ),
    )

    with pytest.raises(
        ReviewEvidenceError,
        match="Codex positive response is not exact-head review evidence",
    ):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
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
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": material_head,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": reaction_reference,
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
    verifier_expected_heads: list[tuple[str | None, str | None]] = []

    def verify_review(*_args: Any, **kwargs: Any) -> CodexReviewEvidence:
        verifier_expected_heads.append(
            (
                kwargs.get("expected_commit_ref"),
                kwargs.get("expected_live_pr_head_ref"),
            )
        )
        return CodexReviewEvidence(
            reference=reaction_reference,
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
    assert verifier_expected_heads == [(material_head, governance_head)]

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
            "- [canonical artifact](https://github.com/owner/repo/blob/main/"
            "docs/review/PR_42_FIXED_MAPPING.md)",
            "main",
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

    check_calls: list[str] = []
    monkeypatch.setattr(
        merge_gate,
        "verify_security_outage_override_reference",
        verify_override,
    )
    monkeypatch.setattr(
        merge_gate,
        "_validate_operator_outage_security_checks",
        lambda **kwargs: check_calls.append(kwargs["expected_head_sha"]),
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
    assert check_calls == [governance_head]


def test_ci_gate_revalidates_review_credit_outage_against_material_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = "Katsiarynakavaleuskaya/PulsePlate"
    pr_number = 2142
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
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=pr_number
    )
    quota_reference = f"https://github.com/{repository}/pull/{pr_number}#issuecomment-456"
    override_reference = f"https://github.com/{repository}/pull/{pr_number}#issuecomment-654"
    prior_reference = f"https://github.com/{repository}/pull/{pr_number}#pullrequestreview-123"
    operator_reference = f"https://github.com/{repository}/pull/{pr_number}#pullrequestreview-789"
    code_review = build_review_credit_outage_receipt(
        material_digest=frozen.digest,
        material_head_sha=material_head,
        override_reference=override_reference,
        override_created_at="2026-07-16T11:15:00Z",
        quota_reference=quota_reference,
        quota_created_at="2026-07-16T11:05:00Z",
        prior_review_reference=prior_reference,
        prior_review_submitted_at="2026-07-16T10:30:00Z",
        prior_review_commit_ref=base_sha,
        operator_review_reference=operator_reference,
        operator_review_submitted_at="2026-07-16T11:10:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
        "codex_security": _receipt(base_sha, material_head),
        "material": {
            "base_ref_oid": base_sha,
            "digest": frozen.digest,
            "material_head_sha": material_head,
            "merge_base_sha": frozen.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": pr_number,
        "repository": repository,
        "schema_version": "pulseplate.pr-review-seal/v1",
    }
    artifact = _artifact_with_seal(seal)
    mapping = repo / "docs" / "review" / f"PR_{pr_number}_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(artifact, encoding="utf-8")
    governance_head = _commit(repo, "governance closeout")
    snapshot = PrSnapshot(
        repository=repository,
        pr_number=pr_number,
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
    verified_heads: list[str] = []

    def verify_credit(*_args: Any, **kwargs: Any) -> ReviewCreditOutageEvidence:
        verified_heads.append(kwargs["expected_material_head_sha"])
        return ReviewCreditOutageEvidence(
            override_reference=override_reference,
            override_created_at="2026-07-16T11:15:00Z",
            quota_reference=quota_reference,
            quota_created_at="2026-07-16T11:05:00Z",
            prior_review_reference=prior_reference,
            prior_review_submitted_at="2026-07-16T10:30:00Z",
            prior_review_commit_ref=base_sha,
            operator_review_reference=operator_reference,
            operator_review_submitted_at="2026-07-16T11:10:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
            material_head_sha=material_head,
            material_digest=frozen.digest,
        )

    monkeypatch.setattr(
        merge_gate,
        "verify_review_credit_outage_references",
        verify_credit,
    )
    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: pytest.fail("normal Codex review path must not run"),
    )

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository=repository,
        pr_number=pr_number,
        snapshot=snapshot,
        token="opaque",
    )

    assert validated["code_review"]["status"] == "tooling_unavailable"
    assert verified_heads == [material_head]


def test_ci_gate_reauthenticates_terminal_review_source_unavailability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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
    quota_reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    quota_body_sha256 = "sha256:" + "c" * 64
    code_review = build_review_source_unavailability_receipt(
        material_digest=frozen.digest,
        material_head_sha=material_head,
        quota_reference=quota_reference,
        quota_created_at="2020-01-01T00:00:00Z",
        quota_body_sha256=quota_body_sha256,
        source_status="usage_limit_reached",
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
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
    verified_refs: list[str] = []

    def verify_source(
        reference: str, *_args: Any, **_kwargs: Any
    ) -> CodexReviewSourceUnavailabilityEvidence:
        verified_refs.append(reference)
        return CodexReviewSourceUnavailabilityEvidence(
            reference=quota_reference,
            created_at="2020-01-01T00:00:00Z",
            source_status="usage_limit_reached",
            body_sha256=quota_body_sha256,
        )

    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_source_unavailability_reference",
        verify_source,
    )
    monkeypatch.setattr(
        merge_gate,
        "verify_codex_review_reference",
        lambda *_a, **_k: pytest.fail("normal Codex review path must not run"),
    )

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
    )
    assert validated["code_review"] == code_review
    assert verified_refs == [quota_reference]

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
            "- [canonical artifact](https://github.com/owner/repo/blob/main/"
            "docs/review/PR_42_FIXED_MAPPING.md)",
            "main",
        ),
    )
    monkeypatch.setattr(merge_gate, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(merge_gate, "_local_head_sha", lambda: governance_head)
    monkeypatch.setattr(merge_gate, "fetch_review_threads", lambda *_a, **_k: ())
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", lambda **_k: [])
    monkeypatch.setattr(merge_gate, "read_mapping_artifact", lambda _pr: artifact)
    monkeypatch.setattr(merge_gate, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    assert merge_gate.main() == 0
    output = capsys.readouterr().out
    assert "REVIEW_SOURCE_UNAVAILABLE_VALID usage_limit_reached" in output
    assert "MACHINE_BOUND_REVIEW_COMMIT" not in output
    assert "REVIEW_CREDIT_OUTAGE_OVERRIDE_VALID" not in output

    source.write_text("ENFORCED = False\n", encoding="utf-8")
    changed_head = _commit(repo, "post-scan material change")
    changed_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=changed_head,
        pr_number=42,
    )
    tampered_seal = json.loads(json.dumps(seal))
    tampered_seal["material"]["digest"] = changed_manifest.digest
    tampered_seal["code_review"] = build_review_source_unavailability_receipt(
        material_digest=changed_manifest.digest,
        material_head_sha=material_head,
        quota_reference=quota_reference,
        quota_created_at="2020-01-01T00:00:00Z",
        quota_body_sha256=quota_body_sha256,
        source_status="usage_limit_reached",
    )
    changed_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=changed_head,
        commits=(
            *snapshot.commits,
            PrCommitEvidence(changed_head, None),
        ),
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="unavailable material head has a different material digest",
    ):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(tampered_seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=changed_snapshot,
            token="opaque",
        )


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
        lambda *_a, **_k: (
            42,
            "owner/repo",
            False,
            "docs/review/PR_42_FIXED_MAPPING.md",
            "main",
        ),
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
    job = workflow["jobs"]["merge_readiness_gate"]
    assert job["needs"] == [
        "changes",
        "pr_body_phase2_gates",
        "private_python_proxy_health",
        "security",
        "trivy_ignore_policy_expiry",
    ]
    assert job["if"] == "${{ always() && github.event_name == 'pull_request' }}"
    assert job["timeout-minutes"] == 15
    assert job["permissions"] == {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "pull-requests": "read",
        "statuses": "read",
    }
    steps = job["steps"]
    checkout = next(step for step in steps if step.get("name") == "Checkout")
    assert checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
        "ref": "${{ github.event.pull_request.head.sha }}",
    }
    enforcement = next(
        step for step in steps if step.get("name") == "Enforce merge readiness policy"
    )
    run = enforcement["run"]
    assert '--event-path "$GITHUB_EVENT_PATH"' in run
    assert "--outage-security-wait-seconds 300" in run
    assert "--defer-outage-security-checks" not in run


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


def test_extract_pr_context_includes_exact_head_ref(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "repository": {"full_name": "owner/repo"},
                "pull_request": {
                    "number": 42,
                    "draft": False,
                    "body": "body",
                    "head": {"ref": "codex/review"},
                },
            }
        ),
        encoding="utf-8",
    )

    assert merge_gate._extract_pr_context(event) == (
        42,
        "owner/repo",
        False,
        "body",
        "codex/review",
    )


def test_fetch_pr_context_includes_exact_head_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        merge_gate,
        "_api_request",
        lambda *_args, **_kwargs: {
            "draft": False,
            "body": "body",
            "head": {"ref": "codex/review"},
        },
    )

    assert merge_gate._fetch_pr_context(42, "owner/repo", "opaque") == (
        42,
        "owner/repo",
        False,
        "body",
        "codex/review",
    )
