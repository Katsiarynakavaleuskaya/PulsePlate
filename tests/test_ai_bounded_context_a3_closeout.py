from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path
import runpy
import subprocess
import sys
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/ci/check_ai_bounded_context_a3_closeout.py"
MERGE_COMMIT = "f8454715f88e44657cfad1c4675f93ea669dc490"  # pragma: allowlist secret
MAPPING_FIX_COMMIT = "52bdcccd1"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_gate() -> str:
    return f"""# Semantic Cache Gate

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->

Current `main` already contains:
- landed PR-A3 AI bounded-context packet via PR #1469
  `docs(architecture): define AI bounded-context packet and ownership map`

The runtime prerequisite train is tracked by canonical PR/backlog anchors:
3. `PR-A3` and [`ledger-p1-ai-bounded-context-packet`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet)
   are closed via PR #1469 `docs(architecture): define AI bounded-context
   packet and ownership map`, merged `2026-04-19T11:35:29Z` with merge commit
   `{MERGE_COMMIT}` from branch `codex/ai-bounded-context-packet`
4. `PR-A4` and [`ledger-p1-ai-bounded-context-extraction`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction)

## Hard Gate

3. `PR-A3` is closed via [`ledger-p1-ai-bounded-context-packet`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet),
   PR #1469 `docs(architecture): define AI bounded-context packet and
   ownership map`, merged `2026-04-19T11:35:29Z` with merge commit
   `{MERGE_COMMIT}` from branch `codex/ai-bounded-context-packet`
"""


def _valid_ledger() -> str:
    return f"""# Backlog

<a id="ledger-p1-ai-bounded-context-packet"></a>
- [x] P1: AI bounded-context packet
  - Target PR: PR-A3 / PR #1469
  - Status: Closed. PR #1469 `docs(architecture): define AI bounded-context packet and ownership map` merged on `2026-04-19T11:35:29Z` with merge commit `{MERGE_COMMIT}` from branch `codex/ai-bounded-context-packet`.
  - DoD:
    - PR #1469 merge evidence is machine-checkable in active roadmap/review docs
    - PR-A4 / `ledger-p1-ai-bounded-context-extraction` remains separate from A3 and is now closed by PR #1203 merge evidence
    - Semantic-cache markers remain `closed / false / false / true`; no semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO, provider, or default activation scope is implied by this closeout

<a id="ledger-p1-ai-bounded-context-extraction"></a>
- [x] P1: Extract AI runtime into a dedicated bounded context
  - Target PR: PR-A4 / PR #1203
  - Status: Closed. PR #1203 merged on `2026-03-21T06:01:31Z` with merge commit `831d62d8be0da7307e5a0f2673d8c33dbf53ca49` from branch `feat/ai-bounded-context-extraction`.
  - DoD:
    - Canonical AI runtime package structure exists and is documented
"""


def _valid_roadmap() -> str:
    return f"""# RAG Roadmap

#### Deferred optimization note
PR-A3 is already landed via PR #1469; the broader runtime sequence still
records PR-A4 separately by PR #1203 merge evidence and still requires a later
reviewed gate-open PR before semantic-cache work can begin.

## PR-A3 - AI bounded-context packet
#### Title
`docs(architecture): define AI bounded-context packet and ownership map`

#### Backlog target
`ledger-p1-ai-bounded-context-packet`

#### Current status
Landed via PR [#1469](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1469)
on `2026-04-19T11:35:29Z` with merge commit
`{MERGE_COMMIT}` from branch
`codex/ai-bounded-context-packet`.

#### DoD
- PR #1469 merge evidence is present in active roadmap/review docs
- packet exists as canonical architecture SoT for extraction PR
- PR-A4 / `ledger-p1-ai-bounded-context-extraction` remains separate from A3
  and is now closed by PR #1203 merge evidence
- semantic-cache markers remain `closed / false / false / true`; no semantic
  cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public
  route, OpenAPI, DTO, provider, or default activation scope is implied by this
  closeout

## PR-A4 - bounded-context extraction
"""


def _valid_mapping() -> str:
    return f"""# PR #1469 - Fixed in Commit Mapping

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1469#discussion_r1 -> {MAPPING_FIX_COMMIT}
Disposition: FIXED

## Post-Merge Closeout

- State: `MERGED`
- Title: `docs(architecture): define AI bounded-context packet and ownership map`
- PR #1469 merged at `2026-04-19T11:35:29Z`
- Merge commit: `{MERGE_COMMIT}`
- Original branch: `codex/ai-bounded-context-packet`
- Boundary: PR-A4 / `ledger-p1-ai-bounded-context-extraction` remains separate
  and open until its own extraction DoD is proven.
- Boundary: semantic-cache markers remain `closed / false / false / true`.
  Semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence,
  public routes, OpenAPI, DTOs, provider rewiring, and default activation remain
  out of scope.

## Historical Merge Readiness

This section is historical evidence only. PR #1469 is already merged, so this
closeout does not re-run or reassert the original readiness checklist.
"""


def _valid_a3_packet() -> str:
    return f"""# Wave 6 A3 AI Bounded-Context Packet

**Mode:** historical pre-open governance packet; landed via PR #1469 on
`2026-04-19T11:35:29Z` with merge commit
`{MERGE_COMMIT}` from branch
`codex/ai-bounded-context-packet`

## Closeout Status

This packet landed through PR #1469
`docs(architecture): define AI bounded-context packet and ownership map`, merged
on `2026-04-19T11:35:29Z` with merge commit
`{MERGE_COMMIT}` from branch
`codex/ai-bounded-context-packet`.

`PR-A4` / `ledger-p1-ai-bounded-context-extraction` remains separate from A3
and is now closed by PR #1203 merge evidence, and semantic-cache markers remain
`closed / false / false / true`.
"""


def _valid_c4_packet() -> str:
    return f"""# C4 AI Bounded Context Packet

## Status

Closeout note: PR-A3 landed via PR #1469
`docs(architecture): define AI bounded-context packet and ownership map`, merged
on `2026-04-19T11:35:29Z` with merge commit
`{MERGE_COMMIT}` from branch
`codex/ai-bounded-context-packet`.

It is a packet-only architecture artifact. It does not implement extraction.
"""


def _write_valid_repo(repo: Path) -> None:
    _write(repo / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(repo / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md", _valid_roadmap())
    _write(repo / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md", _valid_gate())
    _write(repo / "docs/review/PR_1469_FIXED_MAPPING.md", _valid_mapping())
    _write(
        repo / "docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md",
        _valid_a3_packet(),
    )
    _write(
        repo / "docs/architecture/C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md", _valid_c4_packet()
    )


def _checker_args(repo: Path) -> list[str]:
    return [
        sys.executable,
        str(CHECKER),
        "--repo-root",
        str(repo),
        "--ledger",
        str(repo / "docs/roadmap/BACKLOG_LEDGER.md"),
        "--roadmap",
        str(repo / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"),
        "--semantic-cache-gate",
        str(repo / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"),
        "--mapping",
        str(repo / "docs/review/PR_1469_FIXED_MAPPING.md"),
        "--a3-packet",
        str(repo / "docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md"),
        "--c4-packet",
        str(repo / "docs/architecture/C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md"),
    ]


def _errors(repo: Path) -> str:
    result = subprocess.run(_checker_args(repo), text=True, capture_output=True, check=False)
    return result.stderr


def test_checker_passes_on_current_repository() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER)], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "A3 bounded-context packet closeout guard passed" in result.stdout


def test_checker_passes_on_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    result = subprocess.run(_checker_args(tmp_path), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_validate_closeout_direct_api_passes_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    namespace = runpy.run_path(str(CHECKER))
    validate = cast(Callable[..., list[str]], namespace["validate_closeout"])
    assert (
        validate(
            repo_root=tmp_path,
            ledger=tmp_path / "docs/roadmap/BACKLOG_LEDGER.md",
            roadmap=tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md",
            semantic_cache_gate=tmp_path
            / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
            mapping=tmp_path / "docs/review/PR_1469_FIXED_MAPPING.md",
            a3_packet=tmp_path
            / "docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md",
            c4_packet=tmp_path / "docs/architecture/C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md",
        )
        == []
    )


def test_checker_rejects_mapping_fix_commit_as_merge_proof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(path.read_text().replace(MERGE_COMMIT, MAPPING_FIX_COMMIT), encoding="utf-8")
    assert "mapping fix commit" in _errors(
        tmp_path
    ) or "missing required evidence token" in _errors(tmp_path)


def test_checker_rejects_stale_a3_required_outside_a3_section(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text() + "\nThe next runtime lane still requires PR-A3 implementation.\n",
        encoding="utf-8",
    )
    assert "stale planned/pending wording" in _errors(tmp_path)


def test_checker_rejects_a3_closing_a4_extraction_ledger(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text().replace(
            "## PR-A4 - bounded-context extraction",
            "PR-A3 closes ledger-p1-ai-bounded-context-extraction.\n\n"
            "## PR-A4 - bounded-context extraction",
        ),
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_old_mapping_merge_readiness_section(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/review/PR_1469_FIXED_MAPPING.md"
    path.write_text(
        path.read_text().replace("## Historical Merge Readiness", "## Merge Readiness"),
        encoding="utf-8",
    )
    assert "stale live Merge Readiness heading remains" in _errors(tmp_path)


def test_checker_rejects_mixed_clause_semantic_cache_activation(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "PR-A3 does not open semantic cache, but approves Redis production-ready rollout.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_and_clause_semantic_cache_activation(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "PR-A3 does not open semantic cache and enables Redis rollout.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_forbidden_claims_in_packet_closeout_sections(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md"
    path.write_text(
        path.read_text().replace(
            "semantic-cache markers remain\n`closed / false / false / true`.",
            "semantic-cache markers remain\n`closed / false / false / true`.\n"
            "This closeout activates semantic cache.",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_scans_full_a3_ledger_section_for_forbidden_claims(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "Semantic cache is production-ready and enabled by default.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_and_clause_a4_extraction_closure(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text().replace(
            "## PR-A4 - bounded-context extraction",
            "PR-A3 does not close PR-A4 and closes extraction lane now.\n\n"
            "## PR-A4 - bounded-context extraction",
        ),
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_extraction_closure_without_a3_token_in_a3_section(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text().replace(
            "## PR-A4 - bounded-context extraction",
            "This closeout closes extraction lane now.\n\n## PR-A4 - bounded-context extraction",
        ),
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_extraction_closure_without_a3_token_in_packet_section(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md"
    path.write_text(
        path.read_text().replace(
            "`closed / false / false / true`.",
            "`closed / false / false / true`.\nThis closeout closes extraction lane now.",
        ),
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_extraction_closure_without_a3_token_in_gate(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nThis closeout closes extraction lane now.\n",
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_present_tense_activation_state(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "PR-A3 semantic cache is live in production.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_present_tense_activation_state_in_full_gate(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nSemantic cache is live in production by default.\n",
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_activation_state_with_without_clause(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "Semantic cache is live in production without a dedicated gate-open PR.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_comma_mixed_safe_negation_activation_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "Semantic cache is live in production, out of scope for this closeout.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_preserves_surface_context_across_conjunction_split(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "Semantic cache is not part of this closeout and is live in production.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_a4_closure_with_without_clause(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text().replace(
            "## PR-A4 - bounded-context extraction",
            "PR-A3 closes extraction lane without waiting for PR-A4.\n\n"
            "## PR-A4 - bounded-context extraction",
        ),
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_extraction_closure_without_lane_word(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text().replace(
            "## PR-A4 - bounded-context extraction",
            "This closeout closes extraction now.\n\n## PR-A4 - bounded-context extraction",
        ),
        encoding="utf-8",
    )
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_gate_positive_action_claim_without_closeout_token(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nSemantic cache rollout approved for production.\n",
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_gate_extraction_closure_without_closeout_token(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(path.read_text() + "\nExtraction lane closed.\n", encoding="utf-8")
    assert "A3 must not close A4/extraction" in _errors(tmp_path)


def test_checker_rejects_non_cache_surface_activation_state(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "Semantic-cache markers remain `closed / false / false / true`;",
            "GraphRAG is live in production.\n"
            "    - Semantic-cache markers remain `closed / false / false / true`;",
        ),
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_requires_merge_commit_in_mapping_closeout_section(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/review/PR_1469_FIXED_MAPPING.md"
    text = path.read_text()
    path.write_text(
        text.replace(f"Merge commit: `{MERGE_COMMIT}`", f"Merge commit: `{MAPPING_FIX_COMMIT}`")
        + f"\nHistorical note elsewhere: `{MERGE_COMMIT}`\n",
        encoding="utf-8",
    )
    assert "PR #1469 mapping closeout: missing required evidence token" in _errors(tmp_path)


def test_checker_requires_merge_commit_in_packet_closeout_section(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md"
    path.write_text(
        path.read_text().replace(
            f"with merge commit\n`{MERGE_COMMIT}`",
            f"with merge commit\n`{MAPPING_FIX_COMMIT}`",
        )
        + f"\n## Historical Note\n\nHistorical note elsewhere: `{MERGE_COMMIT}`\n",
        encoding="utf-8",
    )
    assert "A3 orchestration packet closeout: missing required evidence token" in _errors(tmp_path)


def test_checker_requires_merge_commit_in_semantic_gate_hard_gate(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    text = path.read_text()
    hard_gate_start = text.index("## Hard Gate")
    path.write_text(
        text[:hard_gate_start]
        + text[hard_gate_start:].replace(MERGE_COMMIT, MAPPING_FIX_COMMIT, 1)
        + f"\n## Historical Note\n\nHistorical note elsewhere: `{MERGE_COMMIT}`\n",
        encoding="utf-8",
    )
    assert "semantic-cache gate hard gate: missing required evidence token" in _errors(tmp_path)


def test_checker_rejects_local_path_leakage_variants(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/review/PR_1469_FIXED_MAPPING.md"
    path.write_text(
        path.read_text()
        + "\nEvidence: /Users/example/worktrees/a3/artifacts/orchestration/task_packets/x.json\n",
        encoding="utf-8",
    )
    assert "local path leakage" in _errors(tmp_path)


def test_checker_rejects_windows_local_path_leakage(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/review/PR_1469_FIXED_MAPPING.md"
    path.write_text(
        path.read_text()
        + "\nEvidence: C:\\Users\\alice\\worktrees\\a3\\artifacts\\orchestration\\x.json\n",
        encoding="utf-8",
    )
    assert "local path leakage" in _errors(tmp_path)


def test_checker_rejects_local_path_leakage_in_full_semantic_gate(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nEvidence: /Users/alice/worktrees/a3/artifacts/orchestration/x.json\n",
        encoding="utf-8",
    )
    assert "local path leakage" in _errors(tmp_path)


def test_checker_rejects_duplicate_semantic_cache_markers(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text().replace(
            "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
            "<!-- SEMANTIC_CACHE_GATE_STATUS: open -->\n<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
        ),
        encoding="utf-8",
    )
    assert "duplicate marker: SEMANTIC_CACHE_GATE_STATUS" in _errors(tmp_path)


def test_checker_rejects_closed_a4_extraction_checkbox_without_merge_evidence(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "831d62d8be0da7307e5a0f2673d8c33dbf53ca49",  # pragma: allowlist secret
            "bad-a4-merge-proof",
        ),
        encoding="utf-8",
    )
    assert "extraction item must be open or closed by PR #1203" in _errors(tmp_path)


def test_checker_rejects_a4_extraction_contradictory_open_and_closed_state(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(
        path.read_text().replace(
            "- [x] P1: Extract AI runtime into a dedicated bounded context",
            "- [ ] P1: Extract AI runtime into a dedicated bounded context\n"
            "- [x] P1: Extract AI runtime into a dedicated bounded context",
            1,
        ),
        encoding="utf-8",
    )
    assert "contradictory state (open and closed-by-#1203 markers present)" in _errors(tmp_path)


def test_checker_uses_stdlib_only_and_no_dynamic_imports() -> None:
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    imports: set[str] = set()
    forbidden_tokens: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute) and node.attr in {
            "spec_from_file_location",
            "module_from_spec",
            "exec_module",
        }:
            forbidden_tokens.append(node.attr)
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id == "sys"
                and node.value.attr == "modules"
            ):
                forbidden_tokens.append("sys.modules")
    assert imports <= {"__future__", "argparse", "re", "sys", "pathlib"}
    assert forbidden_tokens == []
