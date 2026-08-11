from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from scripts.ci import check_pr_merge_readiness as merge_gate
from scripts.orchestration import pr_review_evidence as evidence_module
from scripts.ci.check_pr_merge_readiness import (
    _canonical_artifact_markdown_link_count,
    _is_actionable,
    _mapped_urls,
)
from scripts.orchestration.pr_commit_identity import (
    CommitRefKind,
    PrCommitEvidence,
    PrSnapshot,
    RepositoryCommitRef,
    ReviewCommentEvidence,
    ReviewThreadEvidence,
)
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    ReviewEvidenceError,
    build_provider_no_claim_pair,
    build_review_source_positive_response_receipt,
    build_review_source_unavailability_receipt,
    compute_material_manifest,
    render_embedded_review_seal,
)

OUTAGE_BASE_SHA = "c" * 40
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


def test_duplicate_reply_coverage_wires_recordless_snapshot_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://github.com/owner/repo/pull/42#discussion_r1"
    fix_sha = "a" * 40
    material_head_sha = "b" * 40
    live_head_sha = "c" * 40
    artifact = (
        "## Fixed in Commit Mapping\n"
        f"- https://github.com/owner/repo/pull/42#discussion_mapped -> {fix_sha}\n"
        "Disposition: FIXED\n"
        f"Commit: {fix_sha}\n"
        "- https://github.com/owner/repo/pull/42#discussion_not_bug\n"
        "Disposition: NOT-A-BUG\n"
        "Evidence: canonical contract\n"
    )
    captured: dict[str, Any] = {}

    def validate(**kwargs: Any) -> set[str]:
        captured.update(kwargs)
        return {url}

    monkeypatch.setattr(merge_gate, "validated_duplicate_reply_urls", validate)
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha="d" * 40,
        head_sha=live_head_sha,
        commits=(PrCommitEvidence(live_head_sha, None),),
    )
    covered = merge_gate._duplicate_reply_coverage(
        actionable_items=[
            merge_gate.ActionableItem(
                author="chatgpt-codex-connector",
                url=url,
                created_at="2026-07-15T10:00:00Z",
                kind="review_comment",
            )
        ],
        mapped_urls={"https://github.com/owner/repo/pull/42#discussion_mapped"},
        threads=(),
        artifact_text=artifact,
        seal={
            "material": {
                "digest": "sha256:" + "e" * 64,
                "material_head_sha": material_head_sha,
            }
        },
        snapshot=snapshot,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )

    assert covered == {url}
    assert captured["fingerprint_records"] == {}
    assert captured["mapping_entries"] == {
        "https://github.com/owner/repo/pull/42#discussion_mapped": fix_sha,
        "https://github.com/owner/repo/pull/42#discussion_not_bug": "",
    }
    assert captured["material_head_sha"] == material_head_sha


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


def test_canonical_artifact_link_count_rejects_comment_split_link() -> None:
    body = (
        "- [canonical artifact]<!-- hidden -->"
        "(https://github.com/owner/repo/blob/main/"
        "docs/review/PR_42_FIXED_MAPPING.md)"
    )

    assert _canonical_artifact_markdown_link_count(body, 42, "owner/repo", "main") == 0


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


def test_canonical_artifact_link_count_counts_inline_code_duplicate_url() -> None:
    url = "https://github.com/owner/repo/blob/main/docs/review/PR_42_FIXED_MAPPING.md"
    body = f"- [canonical artifact]({url})\n`{url}`"

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
    monkeypatch.setattr(
        merge_gate,
        "_wait_for_review_quiet_window",
        lambda **_k: pytest.fail("pre-closeout must not wait"),
    )


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


def _review_thread(*, resolved: bool = False) -> ReviewThreadEvidence:
    return ReviewThreadEvidence(
        node_id="PRRT_thread",
        is_resolved=resolved,
        comments=(
            ReviewCommentEvidence(
                url="https://github.com/owner/repo/pull/42#discussion_r1",
                body="Please keep this invariant fail closed.",
                created_at="2026-07-16T00:43:26Z",
                author_login="reviewer",
                author_association="MEMBER",
                original_commit_sha="a" * 40,
            ),
        ),
    )


def test_pre_closeout_fails_when_review_thread_inventory_changes_during_validation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(
            "https://github.com/owner/repo/pull/42#issuecomment-previous"
        ),
        actionable_items=[],
    )
    thread_snapshots = iter(((), (_review_thread(),)))
    monkeypatch.setattr(
        merge_gate,
        "fetch_review_threads",
        lambda *_a, **_k: next(thread_snapshots),
    )

    assert merge_gate.main() == 1
    assert "review-thread inventory changed during validation" in capsys.readouterr().out


def test_pre_closeout_accepts_stable_review_thread_inventory(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_pre_closeout_main(
        monkeypatch,
        artifact=_pre_closeout_artifact(
            "https://github.com/owner/repo/pull/42#issuecomment-previous"
        ),
        actionable_items=[],
    )
    stable_thread = _review_thread(resolved=True)
    fetch_count = 0

    def fetch_threads(*_args: Any, **_kwargs: Any) -> tuple[ReviewThreadEvidence, ...]:
        nonlocal fetch_count
        fetch_count += 1
        return (stable_thread,)

    monkeypatch.setattr(merge_gate, "fetch_review_threads", fetch_threads)

    assert merge_gate.main() == 0
    assert fetch_count == 2
    assert "pre-closeout-review-governance: passed" in capsys.readouterr().out


def test_review_thread_inventory_is_order_independent_and_content_bound() -> None:
    first = _review_thread()
    second = ReviewThreadEvidence(
        node_id="PRRT_other",
        is_resolved=True,
        comments=first.comments,
    )

    assert merge_gate._review_thread_inventory(
        (first, second)
    ) == merge_gate._review_thread_inventory((second, first))

    edited_comment = ReviewCommentEvidence(
        url=first.comments[0].url,
        body="Changed review content.",
        created_at=first.comments[0].created_at,
        author_login=first.comments[0].author_login,
        author_association=first.comments[0].author_association,
        original_commit_sha=first.comments[0].original_commit_sha,
    )
    edited = ReviewThreadEvidence(
        node_id=first.node_id,
        is_resolved=first.is_resolved,
        comments=(edited_comment,),
    )
    assert merge_gate._review_thread_inventory((edited,)) != merge_gate._review_thread_inventory(
        (first,)
    )


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


def test_review_activity_inventory_rejects_missing_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def paged(url: str, token: str) -> list[dict[str, Any]]:
        assert token == "opaque"
        if "/reviews?" not in url:
            return []
        return [
            {
                "body": "No issues found",
                "html_url": "https://github.com/owner/repo/pull/42#pullrequestreview-7",
                "id": 7,
                "state": "COMMENTED",
                "submitted_at": None,
                "user": {"id": 9, "login": "reviewer[bot]"},
            }
        ]

    monkeypatch.setattr(merge_gate, "_api_request_paginated_list", paged)

    with pytest.raises(ValueError, match="review created_at is missing or malformed"):
        merge_gate._review_activity_inventory("owner/repo", 42, "opaque")


def test_review_activity_inventory_accepts_pending_review_without_submitted_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def paged(url: str, token: str) -> list[dict[str, Any]]:
        assert token == "opaque"
        if "/reviews?" not in url:
            return []
        return [
            {
                "body": "draft review",
                "commit_id": "a" * 40,
                "html_url": "https://github.com/owner/repo/pull/42#pullrequestreview-7",
                "id": 7,
                "state": "PENDING",
                "submitted_at": None,
                "user": {"id": 9, "login": "reviewer"},
            }
        ]

    monkeypatch.setattr(merge_gate, "_api_request_paginated_list", paged)

    inventory = merge_gate._review_activity_inventory("owner/repo", 42, "opaque")

    assert inventory[0][0:4] == ("review", 7, 9, "reviewer")
    assert inventory[0][5:7] == (
        merge_gate._PENDING_REVIEW_TIMESTAMP,
        merge_gate._PENDING_REVIEW_TIMESTAMP,
    )
    assert inventory[0][8:10] == ("PENDING", "a" * 40)


def _configure_review_quiet_window(
    monkeypatch: pytest.MonkeyPatch,
    *,
    inventories: list[tuple[tuple[object, ...], ...]],
) -> tuple[PrSnapshot, dict[str, float]]:
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha="b" * 40,
        head_sha="a" * 40,
        commits=(PrCommitEvidence("a" * 40, None),),
    )
    clock = {"now": 0.0}
    iterator = iter(inventories)
    last = inventories[-1]

    def inventory(*_args: Any, **_kwargs: Any) -> tuple[tuple[object, ...], ...]:
        return next(iterator, last)

    monkeypatch.setattr(merge_gate, "_review_activity_inventory", inventory)
    monkeypatch.setattr(
        merge_gate,
        "_fetch_pr_context",
        lambda **_k: (42, "owner/repo", False, "body", "branch"),
    )
    monkeypatch.setattr(merge_gate, "fetch_review_threads", lambda *_a, **_k: ())
    monkeypatch.setattr(merge_gate, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    monkeypatch.setattr(merge_gate, "_review_quiet_monotonic", lambda: clock["now"])
    monkeypatch.setattr(
        merge_gate,
        "_review_quiet_sleep",
        lambda seconds: clock.__setitem__("now", clock["now"] + seconds),
    )
    monkeypatch.setattr(
        merge_gate,
        "_wait_for_operator_outage_security_checks",
        lambda **_k: pytest.fail("review wait must not call provider/security settlement"),
    )
    return snapshot, clock


def test_review_quiet_window_accepts_two_stable_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = (("review", 7, "digest"),)
    snapshot, clock = _configure_review_quiet_window(
        monkeypatch,
        inventories=[event],
    )

    observations, events = merge_gate._wait_for_review_quiet_window(
        repo="owner/repo",
        pr_number=42,
        token="opaque",
        expected_pr_context=(42, "owner/repo", False, "body", "branch"),
        snapshot=snapshot,
    )

    assert observations == 5
    assert events == 1
    assert clock["now"] == 60


def test_review_quiet_window_restarts_after_new_activity_without_external_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = (("review", 7, "first"),)
    second = (*first, ("review_comment", 8, "second"))
    snapshot, clock = _configure_review_quiet_window(
        monkeypatch,
        inventories=[first, first, second],
    )

    observations, events = merge_gate._wait_for_review_quiet_window(
        repo="owner/repo",
        pr_number=42,
        token="opaque",
        expected_pr_context=(42, "owner/repo", False, "body", "branch"),
        snapshot=snapshot,
    )

    assert observations == 7
    assert events == 2
    assert clock["now"] == 90


def test_review_quiet_window_times_out_when_activity_never_settles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventories = [(("review", event_id, f"digest-{event_id}"),) for event_id in range(1, 10)]
    snapshot, clock = _configure_review_quiet_window(
        monkeypatch,
        inventories=inventories,
    )

    with pytest.raises(ReviewEvidenceError, match="did not settle within the bounded 105s"):
        merge_gate._wait_for_review_quiet_window(
            repo="owner/repo",
            pr_number=42,
            token="opaque",
            expected_pr_context=(42, "owner/repo", False, "body", "branch"),
            snapshot=snapshot,
        )

    assert clock["now"] == 105


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


def _legacy_security_receipt(base_sha: str, head_sha: str) -> dict[str, Any]:
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
    identity_index = tuple(merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES).index(name) + 1
    run_id = 1_000 + identity_index
    job_id = 2_000 + identity_index
    resolved_workflow = expected_workflow if workflow_name is None else workflow_name
    return {
        "__typename": "CheckRun",
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "startedAt": started_at,
        "completedAt": "2026-07-16T11:01:00Z" if status == "COMPLETED" else None,
        "detailsUrl": (f"https://github.com/owner/repo/actions/runs/{run_id}/job/{job_id}"),
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


def _install_outage_actions_api(
    monkeypatch: pytest.MonkeyPatch,
    *,
    base_ref: str = "main",
    base_sha: str = OUTAGE_BASE_SHA,
    head_sha: str = OUTAGE_HEAD_SHA,
    run_overrides: dict[str, dict[str, Any]] | None = None,
    job_overrides: dict[str, dict[str, Any]] | None = None,
) -> None:
    runs: dict[int, dict[str, Any]] = {}
    jobs: dict[int, dict[str, Any]] = {}
    for identity_index, (name, identity) in enumerate(
        merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES.items(),
        start=1,
    ):
        workflow_name, _app_id, _app_slug = identity
        workflow_path = merge_gate._OUTAGE_OVERRIDE_REQUIRED_WORKFLOW_PATHS[name]
        run_id = 1_000 + identity_index
        job_id = 2_000 + identity_index
        check_id = 3_000 + identity_index
        run = {
            "created_at": f"2026-07-16T11:{identity_index:02d}:00Z",
            "event": "pull_request",
            "head_sha": head_sha,
            "id": run_id,
            "name": workflow_name,
            "path": workflow_path,
            "pull_requests": [
                {
                    "base": {"ref": base_ref, "sha": base_sha},
                    "head": {"sha": head_sha},
                    "number": 42,
                }
            ],
        }
        run.update((run_overrides or {}).get(name, {}))
        runs[run_id] = run
        job = {
            "check_run_url": (f"https://api.github.com/repos/owner/repo/check-runs/{check_id}"),
            "id": job_id,
            "run_attempt": 1,
            "run_id": run_id,
        }
        job.update((job_overrides or {}).get(name, {}))
        jobs[job_id] = job

    def api(url: str, *, token: str) -> dict[str, Any]:
        assert token == "opaque"
        item_id = int(url.rsplit("/", maxsplit=1)[-1])
        if "/actions/runs/" in url:
            return runs[item_id]
        if "/actions/jobs/" in url:
            return jobs[item_id]
        raise AssertionError(f"unexpected Actions API URL: {url}")

    monkeypatch.setattr(merge_gate, "_api_request", api)


@pytest.fixture
def outage_actions_api(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_outage_actions_api(monkeypatch)


def test_operator_outage_override_requires_exact_successful_security_bundle(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
) -> None:
    del outage_actions_api
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
        expected_base_sha=OUTAGE_BASE_SHA,
        expected_head_sha=OUTAGE_HEAD_SHA,
    )
    assert observed_heads == [OUTAGE_HEAD_SHA]


@pytest.mark.parametrize(
    ("run_override", "job_override", "expected_error"),
    (
        (
            {"event": "push"},
            {},
            r"Analyze \(python\)=untrusted-actions-run.*pull_request",
        ),
        (
            {"path": ".github/workflows/candidate.yml"},
            {},
            r"Analyze \(python\)=untrusted-actions-run.*exact PR/base/head",
        ),
        (
            {"head_sha": "e" * 40},
            {},
            r"Analyze \(python\)=untrusted-actions-run.*exact PR/base/head",
        ),
        (
            {
                "pull_requests": [
                    {
                        "base": {"ref": "main", "sha": "e" * 40},
                        "head": {"sha": OUTAGE_HEAD_SHA},
                        "number": 42,
                    }
                ]
            },
            {},
            r"Analyze \(python\)=untrusted-actions-run.*exact PR/base/head",
        ),
        (
            {},
            {"run_id": 999},
            r"Analyze \(python\)=untrusted-actions-run.*job identity",
        ),
    ),
)
def test_operator_outage_override_rejects_selected_non_pr_or_drifted_actions_identity(
    monkeypatch: pytest.MonkeyPatch,
    run_override: dict[str, Any],
    job_override: dict[str, Any],
    expected_error: str,
) -> None:
    target = "Analyze (python)"
    _install_outage_actions_api(
        monkeypatch,
        run_overrides={target: run_override},
        job_overrides={target: job_override},
    )
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(ReviewEvidenceError, match=expected_error):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
            material_paths=("Dockerfile",),
        )


def test_operator_outage_override_accepts_trusted_skipped_inapplicable_security(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
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
        expected_base_sha=OUTAGE_BASE_SHA,
        expected_head_sha=OUTAGE_HEAD_SHA,
        security_required=merge_gate._operator_outage_security_required(("docs/README.md",)),
    )


def test_operator_outage_security_applicability_uses_material_risk_profile() -> None:
    assert merge_gate._operator_outage_security_required(("docs/README.md",)) is False
    assert (
        merge_gate._operator_outage_security_required(("scripts/ci/check_pr_merge_readiness.py",))
        is True
    )


@pytest.mark.parametrize(
    ("base_ref", "material_paths", "expected"),
    (
        ("main", ("Dockerfile",), True),
        ("main", ("docs/README.md",), False),
        ("feat/stack", ("Dockerfile",), False),
        ("fix/stack", ("Dockerfile",), False),
    ),
)
def test_operator_outage_docker_security_applicability_uses_base_and_surface(
    base_ref: str,
    material_paths: tuple[str, ...],
    expected: bool,
) -> None:
    assert (
        merge_gate._operator_outage_docker_security_required(base_ref, material_paths) is expected
    )


@pytest.mark.parametrize("base_ref", ("feat/stack", "fix/stack"))
def test_operator_outage_override_does_not_wait_for_unattached_stacked_docker_lane(
    monkeypatch: pytest.MonkeyPatch,
    base_ref: str,
) -> None:
    _install_outage_actions_api(monkeypatch, base_ref=base_ref)
    nodes = [
        _check_node(name)
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        if name != "security-scan"
    ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", base_ref, nodes),
    )

    merge_gate._validate_operator_outage_security_checks(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_base_sha=OUTAGE_BASE_SHA,
        expected_head_sha=OUTAGE_HEAD_SHA,
        material_paths=("Dockerfile",),
    )


def test_operator_outage_override_requires_attached_main_docker_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_outage_actions_api(monkeypatch)
    nodes = [
        _check_node(name)
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        if name != "security-scan"
    ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(
        merge_gate._OutageSecurityChecksPending,
        match="security-scan=missing",
    ):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
            material_paths=("Dockerfile",),
        )


def test_operator_outage_override_rejects_newer_queued_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
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
            expected_base_sha=OUTAGE_BASE_SHA,
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
    outage_actions_api: None,
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

    with pytest.raises(ReviewEvidenceError, match=rf"{target}=missing-latest") as exc_info:
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )
    assert not isinstance(exc_info.value, merge_gate._OutageSecurityChecksPending)


def test_operator_outage_override_rejects_equal_time_pending_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    equal_time_pending = _check_node(
        "security",
        status="QUEUED",
        conclusion="",
    )
    nodes.append(equal_time_pending)
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(
        merge_gate._OutageSecurityChecksPending,
        match="security=pending/status",
    ):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


def test_operator_outage_override_rejects_equal_time_neutral_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    equal_time_neutral = _check_node(
        "security",
        conclusion="NEUTRAL",
    )
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
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


def test_operator_outage_override_rejects_unorderable_newer_security_attempt(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
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
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


@pytest.mark.parametrize(
    ("target", "status", "conclusion", "expected"),
    [
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
    outage_actions_api: None,
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
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )
    assert not isinstance(exc_info.value, merge_gate._OutageSecurityChecksPending)
    assert "skipped-when-applicable" in str(exc_info.value)


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
    monkeypatch.setattr(
        merge_gate,
        "time",
        SimpleNamespace(monotonic=lambda: 0.0, sleep=sleeps.append),
    )

    merge_gate._wait_for_operator_outage_security_checks(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_base_sha=OUTAGE_BASE_SHA,
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
        merge_gate,
        "time",
        SimpleNamespace(
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: pytest.fail("terminal failures must not be retried"),
        ),
    )

    with pytest.raises(ReviewEvidenceError, match="security=failed/FAILURE"):
        merge_gate._wait_for_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
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
    monkeypatch.setattr(
        merge_gate,
        "time",
        SimpleNamespace(
            monotonic=lambda: next(clock),
            sleep=lambda _seconds: pytest.fail("expired waits must not sleep"),
        ),
    )

    with pytest.raises(ReviewEvidenceError, match="timed out.*after 5s"):
        merge_gate._wait_for_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
            security_required=True,
            timeout_seconds=5,
        )


def test_operator_outage_wait_rejects_unbounded_timeout() -> None:
    with pytest.raises(ValueError, match="must not exceed 300 seconds"):
        merge_gate._wait_for_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
            security_required=True,
            timeout_seconds=301,
        )


def test_operator_outage_override_treats_missing_security_check_as_transient(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
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

    with pytest.raises(
        merge_gate._OutageSecurityChecksPending,
        match="Private Python proxy health=missing",
    ):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
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
    outage_actions_api: None,
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
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


def test_operator_outage_override_rejects_foreign_status_context(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
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
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
        )


@pytest.mark.parametrize("mode", ("missing", "pending"))
def test_provider_no_claim_transient_security_checks_request_bounded_settlement(
    monkeypatch: pytest.MonkeyPatch,
    outage_actions_api: None,
    mode: str,
) -> None:
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    if mode == "missing":
        nodes = [node for node in nodes if node["name"] != "security"]
    elif mode == "pending":
        nodes = [
            _check_node(
                name,
                status="QUEUED" if name == "security" else "COMPLETED",
                conclusion="" if name == "security" else "SUCCESS",
                started_at=None if name == "security" else "2026-07-16T11:00:00Z",
            )
            for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        ]
    monkeypatch.setattr(
        merge_gate,
        "_fetch_current_head_pr_metadata",
        lambda *_a, **_k: (False, "CLEAN", "main", nodes),
    )

    with pytest.raises(merge_gate._OutageSecurityChecksPending):
        merge_gate._validate_operator_outage_security_checks(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_base_sha=OUTAGE_BASE_SHA,
            expected_head_sha=OUTAGE_HEAD_SHA,
            evidence_label="provider-neutral no-claim evidence",
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


def _self_review_advisory_receipt(
    *,
    base_ref_oid: str,
    merge_base_sha: str,
    material_head_sha: str,
    material_digest: str,
    changed_files: tuple[str, ...],
    diff_summary: dict[str, int],
) -> dict[str, Any]:
    report = {
        "actionable_findings_count": 0,
        "base_ref_oid": base_ref_oid,
        "calibration": {},
        "coordinator_packet": {},
        "decision_log": [],
        "deferred_followups": [],
        "findings": [],
        "findings_count": 0,
        "gate_plan": [],
        "generated_at_utc": "2026-07-27T00:00:00Z",
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "merge_base_sha": merge_base_sha,
        "mode": "dry-run-report",
        "review_source_status": [],
        "role_review": [],
        "schema_version": "2.0.0",
        "scope_reviewed": {
            "changed_files": list(changed_files),
            "diff_summary": dict(diff_summary),
            "fixed_mapping_errors": [],
            "pr_metadata_available": True,
            "scoped_agents_md": ["AGENTS.md"],
        },
        "warnings": [],
    }
    canonical = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "actionable_findings_count": 0,
        "authority": "repo_native_pulseplate_pr_review_advisory",
        "blocking": False,
        "findings_count": 0,
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "report_payload": report,
        "report_sha256": "sha256:" + hashlib.sha256(canonical).hexdigest(),
        "review_claim": "none",
        "review_tool": "pulseplate-pr-review",
        "schema_version": "pulseplate.self-review-advisory/v1",
        "status": "advisory_report_attached",
    }


def _provider_no_claim_seal_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, Any], PrSnapshot, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    (repo / "README.md").write_text("material\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_head,
        pr_number=42,
    )
    assert manifest.diff_summary is not None
    code_review, codex_security = build_provider_no_claim_pair(
        base_revision=manifest.merge_base_sha,
        head_revision=material_head,
        material_digest=manifest.digest,
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
        "codex_security": codex_security,
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
        "self_review": _self_review_advisory_receipt(
            base_ref_oid=base_sha,
            merge_base_sha=manifest.merge_base_sha,
            material_head_sha=material_head,
            material_digest=manifest.digest,
            changed_files=("README.md",),
            diff_summary=manifest.diff_summary.as_dict(),
        ),
    }
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=material_head,
        commits=(PrCommitEvidence(material_head, None),),
    )
    return repo, seal, snapshot, material_head


def test_ci_gate_accepts_provider_no_claim_and_waits_bounded_without_providers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, seal, snapshot, material_head = _provider_no_claim_seal_context(
        tmp_path,
        monkeypatch,
    )
    _install_outage_actions_api(
        monkeypatch,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
    )

    successful_nodes = [
        _check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    ]
    missing_nodes = [node for node in successful_nodes if node["name"] != "security"]
    pending_nodes = [
        _check_node(
            name,
            status="QUEUED" if name == "security" else "COMPLETED",
            conclusion="" if name == "security" else "SUCCESS",
            started_at=None if name == "security" else "2026-07-16T11:00:00Z",
        )
        for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    ]
    metadata_snapshots = iter((missing_nodes, pending_nodes, successful_nodes))
    metadata_heads: list[str] = []
    sleeps: list[float] = []

    def fetch_metadata(
        _pr_number: int,
        _repository: str,
        _token: str,
        expected_head_sha: str,
    ) -> tuple[bool, str, str, list[dict[str, Any]]]:
        metadata_heads.append(expected_head_sha)
        return False, "CLEAN", "main", next(metadata_snapshots)

    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(merge_gate, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(merge_gate, "_fetch_current_head_pr_metadata", fetch_metadata)
    monkeypatch.setattr(
        merge_gate,
        "time",
        SimpleNamespace(monotonic=lambda: 0.0, sleep=sleeps.append),
    )

    validated = merge_gate._validate_v1_seal(
        artifact_text=_artifact_with_seal(seal),
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
        outage_security_wait_seconds=120,
        require_committed_closeout=False,
    )

    assert validated["code_review"]["review_claim"] == "none"
    assert validated["codex_security"]["scan_claim"] == "none"
    assert metadata_heads == [material_head, material_head, material_head]
    assert sleeps == [15.0, 15.0]

    wrong_paths_seal = json.loads(json.dumps(seal))
    self_review = wrong_paths_seal["self_review"]
    self_review["report_payload"]["scope_reviewed"]["changed_files"] = ["wrong/path.py"]
    canonical_report = json.dumps(
        self_review["report_payload"],
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    self_review["report_sha256"] = "sha256:" + hashlib.sha256(canonical_report).hexdigest()
    with pytest.raises(ReviewEvidenceError, match="exact material path set"):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(wrong_paths_seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
            enforce_outage_security_checks=False,
            require_committed_closeout=False,
        )

    wrong_diff_summary_seal = json.loads(json.dumps(seal))
    self_review = wrong_diff_summary_seal["self_review"]
    self_review["report_payload"]["scope_reviewed"]["diff_summary"]["changed_lines"] += 1
    canonical_report = json.dumps(
        self_review["report_payload"],
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    self_review["report_sha256"] = "sha256:" + hashlib.sha256(canonical_report).hexdigest()
    with pytest.raises(ReviewEvidenceError, match="diff summary.*exact material"):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(wrong_diff_summary_seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
            enforce_outage_security_checks=False,
            require_committed_closeout=False,
        )


@pytest.mark.parametrize("mode", ("missing", "pending"))
def test_ci_gate_provider_no_claim_security_settlement_times_out_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    repo, seal, snapshot, _material_head = _provider_no_claim_seal_context(
        tmp_path,
        monkeypatch,
    )
    _install_outage_actions_api(
        monkeypatch,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
    )
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    if mode == "missing":
        nodes = [node for node in nodes if node["name"] != "security"]
    elif mode == "pending":
        nodes = [
            _check_node(
                name,
                status="QUEUED" if name == "security" else "COMPLETED",
                conclusion="" if name == "security" else "SUCCESS",
                started_at=None if name == "security" else "2026-07-16T11:00:00Z",
            )
            for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        ]
    metadata_calls: list[str] = []

    def fetch_metadata(
        _pr_number: int,
        _repository: str,
        _token: str,
        expected_head_sha: str,
    ) -> tuple[bool, str, str, list[dict[str, Any]]]:
        metadata_calls.append(expected_head_sha)
        return False, "CLEAN", "main", nodes

    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(merge_gate, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(merge_gate, "_fetch_current_head_pr_metadata", fetch_metadata)
    clock = iter((0.0, 121.0))
    monkeypatch.setattr(
        merge_gate,
        "time",
        SimpleNamespace(
            monotonic=lambda: next(clock),
            sleep=lambda _seconds: pytest.fail("expired bounded settlement must not sleep"),
        ),
    )

    with pytest.raises(ReviewEvidenceError, match="timed out.*after 120s"):
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
            outage_security_wait_seconds=120,
            require_committed_closeout=False,
        )

    assert metadata_calls == [snapshot.head_sha]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("stale", "security=missing-latest"),
        ("failed", "security=failed/FAILURE"),
        ("untrusted", "security=untrusted-producer"),
        ("skipped_applicable", r"Analyze \(python\)=failed/SKIPPED"),
    ],
)
def test_ci_gate_provider_no_claim_terminal_security_checks_do_not_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    expected: str,
) -> None:
    repo, seal, snapshot, _material_head = _provider_no_claim_seal_context(
        tmp_path,
        monkeypatch,
    )
    _install_outage_actions_api(
        monkeypatch,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
    )
    nodes = [_check_node(name) for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES]
    if mode == "stale":
        newer_activity = _check_node(
            "security",
            suite_created_at="2026-07-16T11:01:00Z",
        )
        newer_activity["name"] = "pr_scope_guard"
        newer_activity["detailsUrl"] = "https://github.com/checks/pr_scope_guard"
        nodes.append(newer_activity)
    elif mode == "failed":
        nodes = [
            _check_node(
                name,
                conclusion="FAILURE" if name == "security" else "SUCCESS",
            )
            for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        ]
    elif mode == "untrusted":
        nodes = [
            _check_node(
                name,
                workflow_name="foreign-workflow" if name == "security" else None,
            )
            for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        ]
    else:
        nodes = [
            _check_node(
                name,
                conclusion="SKIPPED" if name == "Analyze (python)" else "SUCCESS",
            )
            for name in merge_gate._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
        ]

    metadata_calls: list[str] = []

    def fetch_metadata(
        _pr_number: int,
        _repository: str,
        _token: str,
        expected_head_sha: str,
    ) -> tuple[bool, str, str, list[dict[str, Any]]]:
        metadata_calls.append(expected_head_sha)
        return False, "CLEAN", "main", nodes

    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(merge_gate, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(merge_gate, "_fetch_current_head_pr_metadata", fetch_metadata)
    monkeypatch.setattr(
        merge_gate,
        "time",
        SimpleNamespace(
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: pytest.fail("terminal current-head checks must not be retried"),
        ),
    )

    with pytest.raises(ReviewEvidenceError, match=expected) as exc_info:
        merge_gate._validate_v1_seal(
            artifact_text=_artifact_with_seal(seal),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
            outage_security_wait_seconds=120,
            require_committed_closeout=False,
        )

    assert not isinstance(exc_info.value, merge_gate._OutageSecurityChecksPending)
    assert metadata_calls == [snapshot.head_sha]


@pytest.mark.parametrize(
    "legacy_kind",
    ("exact_review", "positive_response", "source_unavailability"),
)
def test_ci_gate_rejects_legacy_provider_review_seals_without_live_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_kind: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    (repo / "README.md").write_text("material\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    manifest = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=42
    )
    if legacy_kind == "positive_response":
        code_review = build_review_source_positive_response_receipt(
            material_digest=manifest.digest,
            material_head_sha=material_head,
            response_reference="https://github.com/owner/repo/pull/42#reaction-456",
            response_created_at="2026-07-15T11:00:00Z",
            response_content="+1",
        )
    elif legacy_kind == "source_unavailability":
        code_review = build_review_source_unavailability_receipt(
            material_digest=manifest.digest,
            material_head_sha=material_head,
            quota_reference="https://github.com/owner/repo/pull/42#issuecomment-456",
            quota_created_at="2026-07-15T11:00:00Z",
            quota_body_sha256="sha256:" + "c" * 64,
            source_status="usage_limit_reached",
        )
    else:
        code_review = {
            "review_commit_ref": material_head,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": ("https://github.com/owner/repo/pull/42#pullrequestreview-123"),
            "reviewed_material_digest": manifest.digest,
            "status": "completed",
        }
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
        "codex_security": _legacy_security_receipt(base_sha, material_head),
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
    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )

    with pytest.raises(ReviewEvidenceError, match="read-only"):
        merge_gate._validate_v1_seal(
            artifact_text=artifact,
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
        )


def test_merge_gate_exposes_no_legacy_provider_verifier_or_success_marker() -> None:
    legacy_symbols = {
        "verify_codex_review_reference",
        "verify_codex_review_source_unavailability_reference",
        "verify_review_credit_outage_references",
        "verify_security_outage_override_reference",
    }
    assert legacy_symbols.isdisjoint(vars(merge_gate))

    source = Path(merge_gate.__file__).read_text(encoding="utf-8")
    for success_marker in (
        "MACHINE_BOUND_REVIEW_COMMIT",
        "REVIEW_CREDIT_OUTAGE_OVERRIDE_VALID",
        "REVIEW_SOURCE_POSITIVE_RESPONSE_VALID",
        "REVIEW_SOURCE_UNAVAILABLE_VALID",
    ):
        assert success_marker not in source


def _configure_post_wait_revalidation_main(
    monkeypatch: pytest.MonkeyPatch,
    *,
    second_error: ReviewEvidenceError | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    head_sha = "a" * 40
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha="b" * 40,
        head_sha=head_sha,
        commits=(PrCommitEvidence(head_sha, None),),
    )
    pr_context = (
        42,
        "owner/repo",
        False,
        "- [canonical artifact](https://github.com/owner/repo/blob/branch/"
        "docs/review/PR_42_FIXED_MAPPING.md)",
        "branch",
    )
    validation_calls: list[dict[str, Any]] = []
    trace: list[str] = []
    inventory_count = 0

    def validate_seal(**kwargs: Any) -> dict[str, Any]:
        validation_calls.append(kwargs)
        trace.append(f"seal-{kwargs['outage_security_wait_seconds']}")
        if len(validation_calls) == 2 and second_error is not None:
            raise second_error
        return {"material": {"digest": "sha256:" + "c" * 64}}

    def actionable_inventory(**_kwargs: Any) -> list[merge_gate.ActionableItem]:
        nonlocal inventory_count
        inventory_count += 1
        trace.append(f"inventory-{inventory_count}")
        return []

    def quiet_window(**_kwargs: Any) -> tuple[int, int]:
        trace.append("quiet")
        return 2, 0

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
    monkeypatch.setattr(merge_gate, "_fetch_pr_context", lambda **_kwargs: pr_context)
    monkeypatch.setattr(merge_gate, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(merge_gate, "_local_head_sha", lambda: head_sha)
    monkeypatch.setattr(merge_gate, "fetch_review_threads", lambda *_a, **_k: ())
    monkeypatch.setattr(merge_gate, "_collect_actionable_items", actionable_inventory)
    monkeypatch.setattr(merge_gate, "read_mapping_artifact", lambda _pr: "artifact")
    monkeypatch.setattr(merge_gate, "validate_mapping_artifact_text", lambda _text: [])
    monkeypatch.setattr(merge_gate, "extract_fixed_mapping_section", lambda _text: "mapping")
    monkeypatch.setattr(merge_gate, "parse_fixed_mapping_entries", lambda _text: {})
    monkeypatch.setattr(merge_gate, "has_no_actionable_marker", lambda _text: True)
    monkeypatch.setattr(merge_gate, "review_seal_version", lambda _text: "v1")
    monkeypatch.setattr(merge_gate, "_validate_v1_seal", validate_seal)
    monkeypatch.setattr(merge_gate, "_prove_v1_fixed_commits", lambda **_kwargs: None)
    monkeypatch.setattr(
        merge_gate,
        "_canonical_artifact_markdown_link_count",
        lambda *_args: 1,
    )
    monkeypatch.setattr(merge_gate, "_duplicate_reply_coverage", lambda **_kwargs: set())
    monkeypatch.setattr(merge_gate, "_wait_for_review_quiet_window", quiet_window)
    monkeypatch.setattr(merge_gate, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    return validation_calls, trace


def test_merge_readiness_revalidates_seal_once_after_stable_review_wait(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    validation_calls, trace = _configure_post_wait_revalidation_main(monkeypatch)

    assert merge_gate.main() == 0

    assert len(validation_calls) == 2
    assert validation_calls[1]["outage_security_wait_seconds"] == 0
    assert validation_calls[1]["enforce_outage_security_checks"] is True
    assert validation_calls[1]["require_committed_closeout"] is True
    assert trace == ["inventory-1", "seal-300", "quiet", "seal-0", "inventory-2"]
    assert "REVIEW_WAIT_WINDOW_VALID" in capsys.readouterr().out


@pytest.mark.parametrize(
    "second_error",
    (
        ReviewEvidenceError(
            "provider-neutral no-claim evidence timed out waiting for exact-head "
            "security checks after 0s: security=pending/status"
        ),
        ReviewEvidenceError(
            "provider-neutral no-claim evidence requires successful current-head "
            "security checks: security=failed/FAILURE"
        ),
    ),
    ids=("pending", "failed"),
)
def test_merge_readiness_fails_closed_when_post_wait_seal_revalidation_is_not_green(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    second_error: ReviewEvidenceError,
) -> None:
    validation_calls, trace = _configure_post_wait_revalidation_main(
        monkeypatch,
        second_error=second_error,
    )

    assert merge_gate.main() == 1

    output = capsys.readouterr().out
    assert len(validation_calls) == 2
    assert validation_calls[1]["outage_security_wait_seconds"] == 0
    assert trace == ["inventory-1", "seal-300", "quiet", "seal-0", "inventory-2"]
    assert "Post-wait material review seal validation failed" in output
    assert str(second_error) in output
    assert "REVIEW_WAIT_WINDOW_VALID" not in output


def test_ci_gate_accepts_governance_only_head_and_rejects_stale_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    frozen = compute_material_manifest(
        repo, base_ref_oid=base_sha, head_ref_oid=material_head, pr_number=42
    )
    assert frozen.diff_summary is not None
    code_review, codex_security = build_provider_no_claim_pair(
        base_revision=frozen.merge_base_sha,
        head_revision=material_head,
        material_digest=frozen.digest,
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
        "codex_security": codex_security,
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
        "self_review": _self_review_advisory_receipt(
            base_ref_oid=base_sha,
            merge_base_sha=frozen.merge_base_sha,
            material_head_sha=material_head,
            material_digest=frozen.digest,
            changed_files=("src/policy.py",),
            diff_summary=frozen.diff_summary.as_dict(),
        ),
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
        "_wait_for_operator_outage_security_checks",
        lambda **_kwargs: None,
    )

    validated = merge_gate._validate_v1_seal(
        artifact_text=artifact,
        repository="owner/repo",
        pr_number=42,
        snapshot=snapshot,
        token="opaque",
    )
    assert validated["material"]["digest"] == frozen.digest

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
    monkeypatch.setattr(
        merge_gate,
        "_wait_for_review_quiet_window",
        lambda **_k: (2, 0),
    )

    assert merge_gate.main() == 0
    output = capsys.readouterr().out
    assert "CONTENT_BOUND_RECEIPT_VALID" in output
    assert "REVIEW_WAIT_WINDOW_VALID observations=2 quiet_seconds=60 events=0" in output

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


@pytest.mark.parametrize("descendant_kind", ("mapping-only", "empty"))
def test_ci_gate_rejects_any_descendant_after_the_mapping_closeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descendant_kind: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    frozen = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_head,
        pr_number=42,
    )
    assert frozen.diff_summary is not None
    code_review, codex_security = build_provider_no_claim_pair(
        base_revision=frozen.merge_base_sha,
        head_revision=material_head,
        material_digest=frozen.digest,
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
        "codex_security": codex_security,
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
        "self_review": _self_review_advisory_receipt(
            base_ref_oid=base_sha,
            merge_base_sha=frozen.merge_base_sha,
            material_head_sha=material_head,
            material_digest=frozen.digest,
            changed_files=("src/policy.py",),
            diff_summary=frozen.diff_summary.as_dict(),
        ),
    }
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    artifact = _artifact_with_seal(seal)
    mapping.write_text(artifact, encoding="utf-8")
    mapping_head = _commit(repo, "mapping closeout")

    if descendant_kind == "mapping-only":
        mapping.write_text(artifact + "\n<!-- second mapping commit -->\n", encoding="utf-8")
        descendant_head = _commit(repo, "second mapping-only descendant")
    else:
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "PulsePlate Test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "PulsePlate Test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }
        )
        _git(repo, "commit", "--allow-empty", "-m", "empty descendant", env=env)
        descendant_head = _git(repo, "rev-parse", "HEAD")

    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=descendant_head,
        commits=(
            PrCommitEvidence(material_head, None),
            PrCommitEvidence(mapping_head, None),
            PrCommitEvidence(descendant_head, None),
        ),
    )
    monkeypatch.setattr(merge_gate, "REPO_ROOT", repo)
    monkeypatch.setattr(
        merge_gate,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == descendant_head else CommitRefKind.PR_COMMIT,
        ),
    )

    with pytest.raises(ReviewEvidenceError, match="one mapping-only successor"):
        merge_gate._validate_v1_seal(
            artifact_text=mapping.read_text(encoding="utf-8"),
            repository="owner/repo",
            pr_number=42,
            snapshot=snapshot,
            token="opaque",
            enforce_outage_security_checks=False,
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
