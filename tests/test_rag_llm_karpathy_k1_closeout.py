"""Regression guards for PR-K1 knowledge-promotion closeout docs."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


def _between(text: str, start: str, end: str, *, label: str) -> str:
    start_index = text.find(start)
    assert start_index != -1, f"Missing start anchor for {label}: {start!r}"
    end_index = text.find(end, start_index + len(start))
    assert end_index != -1, f"Missing end anchor for {label}: {end!r}"
    return text[start_index:end_index]


def test_k1_ledger_closeout_is_not_left_open_or_orphaned() -> None:
    ledger = _read("docs/roadmap/BACKLOG_LEDGER.md")
    item = _between(
        ledger,
        '<a id="ledger-p1-knowledge-promotion-from-validated-rag"></a>',
        '<a id="ledger-p1-verification-registry-admission"></a>',
        label="K1 ledger item",
    )

    assert "- [x] P1: Knowledge contracts and promotion from validated RAG evidence" in item
    assert "- Status: Closed by PR-K1 docs/review closeout" in item
    assert "PR `#1483`" in item
    assert "2026-04-20" in item
    assert "docs/review/PR_1483_FIXED_MAPPING.md" in item
    assert "closed / false / false / true" in item
    assert "keep the checkbox open" not in item
    assert "Deferred follow-up" not in item


def test_k1_roadmap_marks_landed_without_semantic_cache_rollout_claims() -> None:
    roadmap = _read("docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md")
    section = _between(roadmap, "## PR-K1 ", "## PR-V1 ", label="K1 roadmap section")

    assert "Landed via PR `#1483` on `2026-04-20`" in section
    assert "docs/backlog/review reconciliation" in section
    assert "semantic cache stays gate-closed, deferred, and out of scope" in section
    assert "semantic cache implementation" in section
    assert "approve Redis/GPTCache rollout" not in section
    assert "opens the semantic-cache gate" not in section.lower()


def test_semantic_cache_gate_markers_remain_closed_after_k1_closeout() -> None:
    gate = _read("docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md")

    assert "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->" in gate
    assert "<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->" in gate
    assert "<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->" in gate
    assert "<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->" in gate


def test_pr1483_deferred_fast_lane_return_annotations_are_resolved() -> None:
    fast_lane = _read("tests/test_remaining_modules.py")
    mapping = _read("docs/review/PR_1483_FIXED_MAPPING.md")

    assert (
        "def _runtime_policy(*, enabled: bool = True, allow_promotion: bool = True) "
        '-> "KnowledgePolicy":'
    ) in fast_lane
    assert 'def _runtime_candidate() -> "KnowledgeFactCandidate":' in fast_lane
    review_url = (
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483"
        "#pullrequestreview-4139572722"
    )
    block = _between(
        mapping,
        "Disposition: FIXED\nCommit: 5215db056\nEvidence: `tests/test_remaining_modules.py:1577`",
        "## Post-Merge Closeout",
        label="PR 1483 deferred CodeRabbit closeout block",
    )
    assert "docs/roadmap/BACKLOG_LEDGER.md:2380" in block
    assert "tests/test_rag_llm_karpathy_k1_closeout.py:63" in block
    assert f"{review_url} -> 5215db056" in block
    assert block.count(review_url) == 1
    assert mapping.count(review_url) == 1
    assert "Disposition: DEFERRED" not in block


def test_pr1483_mapping_uses_post_merge_closeout_instead_of_stale_readiness() -> None:
    mapping = _read("docs/review/PR_1483_FIXED_MAPPING.md")
    closeout = _between(
        mapping,
        "## Post-Merge Closeout",
        "<!-- markdownlint-enable MD034 -->",
        label="PR 1483 post-merge closeout",
    )
    merge_commit = "".join(
        (
            "ba42a25a",
            "6c8d2c6d",
            "030e313a",
            "b14e1173",
            "492a9e06",
        )
    )

    assert "State: `MERGED`" in closeout
    assert "Merged at: `2026-04-20T12:09:36Z`" in closeout
    assert merge_commit in closeout
    assert "Current readiness evidence for this closeout belongs to the new closeout PR" in closeout
    assert "## Merge Readiness" not in mapping
    assert "Current-head CI is green for PR branch head" not in mapping
    assert "origin/codex/pr-k1-knowledge-promotion" not in mapping
