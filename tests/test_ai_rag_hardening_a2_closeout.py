from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import runpy
import subprocess
import sys
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/ci/check_ai_rag_hardening_a2_closeout.py"
MERGE_COMMIT = "146da0e0d269acea5ba946d239997705ebaf62c3"  # pragma: allowlist secret


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
- landed PR-A2 RAG hardening via PR #1415

The runtime prerequisite train is tracked by canonical PR/backlog anchors:
1. `PR-A1b` is reconciled elsewhere
2. `PR-A2` is closed via
   [`ledger-p1-rag-hardening-followthrough`](./BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough),
   PR #1415 `feat(rag): harden degraded retrieval paths and keep contracts
   additive`, merged `2026-04-14T20:59:47Z` with merge commit
   `{MERGE_COMMIT}` from branch `feat/rag-hardening-followthrough`
3. `PR-A3` remains separate

Do **not** start semantic cache work before all the following are true:
2. `PR-A2` is closed via
   [`ledger-p1-rag-hardening-followthrough`](./BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough),
   PR #1415 `feat(rag): harden degraded retrieval paths and keep contracts
   additive`, merged `2026-04-14T20:59:47Z` with merge commit
   `{MERGE_COMMIT}` from branch `feat/rag-hardening-followthrough`

## Rail Boundary
Semantic cache remains closed.
"""


def _valid_ledger() -> str:
    return f"""# Backlog

<a id="ledger-p1-rag-hardening-followthrough"></a>
- [x] P1: RAG hardening follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-A2 / PR #1415
  - Status: Closed. PR #1415 merged on `2026-04-14T20:59:47Z`
    with merge commit `{MERGE_COMMIT}` from branch
    `feat/rag-hardening-followthrough`; title
    `feat(rag): harden degraded retrieval paths and keep contracts additive`.
  - Reason (EN): Live GitHub/repo truth proves the dedicated A2 runtime RAG
    hardening slice already landed in PR #1415. This closeout records active
    roadmap/review docs as evidence without duplicating runtime implementation.
  - DoD:
    - PR #1415 merge evidence is machine-checkable in active roadmap/review docs
    - Semantic-cache markers remain `closed / false / false / true`

<a id="next"></a>
- [ ] Next item
"""


def _valid_roadmap() -> str:
    return f"""# RAG roadmap

## PR-A2 - RAG hardening follow-through
#### Title
`feat(rag): harden degraded retrieval paths and keep contracts additive`

#### Current status
Landed via PR [#1415](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415)
on `2026-04-14T20:59:47Z` with merge commit
`{MERGE_COMMIT}` from branch
`feat/rag-hardening-followthrough`.

#### Evidence boundary
Runtime evidence is limited to PR #1415 merge evidence, landed symbols, focused
deterministic tests, and review artifacts. This closeout does not claim new
benchmark results, latency wins, accuracy gains, RAGAS quality proof, or
production RAG robustness beyond the existing deterministic test evidence.

#### Out of scope
Semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence,
public routes, OpenAPI, DTOs, provider integration, recursive learning,
provider chain/tree-of-thought, and default activation remain out of scope.

## PR-A3
"""


def _valid_mapping() -> str:
    return f"""# PR 1415 - Fixed in Commit Mapping

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r1 -> abc123
Disposition: FIXED

## Post-Merge Closeout

- State: `MERGED`
- Title: `feat(rag): harden degraded retrieval paths and keep contracts additive`
- PR #1415 merged at `2026-04-14T20:59:47Z`
- Merge commit: `{MERGE_COMMIT}`
- Original branch: `feat/rag-hardening-followthrough`
- Evidence boundary: deterministic tests and landed symbols prove the closeout
  state only. This artifact does not claim new benchmark results, accuracy
  gains, latency wins, or production RAG robustness.
- Boundary: semantic-cache markers remain `closed / false / false / true`.
  Semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence,
  public routes, OpenAPI, DTOs, provider integration, recursive learning,
  provider chain/tree-of-thought, and default activation remain out of scope.

## Historical Merge Readiness

This section is historical evidence only. PR #1415 is already merged, so this
closeout does not re-run or reassert the original readiness checklist.
"""


def _write_runtime_markers(repo_root: Path) -> None:
    _write(
        repo_root / "core/rag/contracts.py",
        """from enum import Enum


class RAGDegradedReason(str, Enum):
    VECTOR_FALLBACK_NO_RESULTS = "vector_fallback_no_results"
    VECTOR_FALLBACK_EXCEPTION = "vector_fallback_exception"
    VECTOR_FALLBACK_SUBJECT_MISSING = "vector_fallback_subject_missing"
    FORMATTED_CONTEXT_MALFORMED = "formatted_context_malformed"
    REDACTED_CONTEXT_MALFORMED = "redacted_context_malformed"
""",
    )
    _write(
        repo_root / "core/rag/orchestration.py",
        """from core.rag.contracts import RAGDegradedReason


def _resolve_confidence() -> None:
    return None


def _non_rag_result(subject_id: int) -> object:
    result = build(subject_id=subject_id)
    return (
        result,
        RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
        RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
    )


def _run_orchestration(subject_id: int) -> object:
    asyncio.to_thread(retrieve_recursive_context_structured, subject_id=subject_id)
    asyncio.to_thread(retrieve_context_structured, subject_id=subject_id)
    _build_knowledge_candidates(subject_id=subject_id)
    return (
        RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
        RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
    )
""",
    )
    _write(
        repo_root / "core/rag/vector_rag.py",
        """from core.rag.contracts import RAGDegradedReason


def _normalize_embedding_vector() -> None:
    return None


def _retrieve_vector_postgres(session: object, subject_id: int) -> None:
    return None


def _retrieve_vector_from_db(session: object, subject_id: int) -> None:
    apply_user_rls_context(session, user_id=subject_id)
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )


def _retrieve_vector_sqlite() -> tuple[object, object]:
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )
""",
    )
    for path, names in {
        "tests/test_rag_orchestration.py": (
            "test_validation_disabled_ignores_stale_retriever_confidence",
            "test_vector_path_propagates_subject_id",
            "test_empty_formatted_context_returns_fail_safe_non_rag_result",
            "test_non_string_redacted_context_returns_fail_safe_non_rag_result",
            "test_rag_orchestration_denies_canonical_candidates_when_retrieval_is_degraded",
        ),
        "tests/test_vector_rag.py": (
            "test_missing_subject_id_returns_empty_without_encoding",
            "test_wrong_query_dimensions_return_empty_without_db_work",
            "test_retrieve_vector_sqlite_binds_subject_id",
            "test_vector_success_skips_malformed_rows_without_poisoning_whole_result",
        ),
        "tests/test_insight_rag_response_fields.py": (
            "test_rag_late_context_collapse_returns_non_rag_contract",
            "test_rag_late_redaction_collapse_returns_non_rag_contract",
            "test_rag_response_confidence_uses_active_output_chunks",
            "test_rag_response_confidence_uses_filtered_subset_chunks",
        ),
    }.items():
        _write(repo_root / path, "\n".join(f"def {name}(): pass" for name in names))


def _write_valid_repo(repo_root: Path) -> None:
    _write_runtime_markers(repo_root)
    _write(repo_root / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(
        repo_root / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md",
        _valid_roadmap(),
    )
    _write(repo_root / "docs/review/PR_1415_FIXED_MAPPING.md", _valid_mapping())
    _write(repo_root / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md", _valid_gate())


def _checker_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _errors(repo_root: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(repo_root)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_checker_env(),
    )
    if result.returncode == 0:
        return []
    return [line for line in f"{result.stderr}\n{result.stdout}".splitlines() if line.strip()]


def _errors_with_mapping(repo_root: Path, mapping: Path) -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo_root),
            "--mapping",
            str(mapping),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_checker_env(),
    )
    if result.returncode == 0:
        return []
    return [line for line in f"{result.stderr}\n{result.stdout}".splitlines() if line.strip()]


def _load_validate_closeout() -> Callable[..., list[str]]:
    namespace = runpy.run_path(str(CHECKER), run_name="a2_closeout_checker")
    return cast(Callable[..., list[str]], namespace["validate_closeout"])


def test_checker_passes_on_current_repository() -> None:
    assert _errors(REPO_ROOT) == []


def test_checker_passes_on_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    assert _errors(tmp_path) == []


def test_validate_closeout_direct_api_passes_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    validate_closeout = _load_validate_closeout()
    assert validate_closeout(repo_root=tmp_path) == []


def test_checker_accepts_negated_boundary_lists(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    assert _errors(tmp_path) == []


def test_checker_rejects_contrasted_benchmark_overclaim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout does not claim new\nbenchmark results",
            "This closeout does not claim benchmark results, but PR-A2 proves latency wins",
        ),
        encoding="utf-8",
    )
    assert any("benchmark/scientific overclaim" in error for error in _errors(tmp_path))


def test_checker_rejects_overclaim_after_conjunction_negation(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "does not claim new\nbenchmark results, latency wins, accuracy gains",
            "does not claim benchmark results and PR-A2 proves latency wins",
        ),
        encoding="utf-8",
    )
    assert any("benchmark/scientific overclaim" in error for error in _errors(tmp_path))


def test_checker_rejects_overclaim_after_deferred_wording(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout does not claim new\nbenchmark results",
            "Deferred note: PR-A2 proves latency wins",
        ),
        encoding="utf-8",
    )
    assert any("benchmark/scientific overclaim" in error for error in _errors(tmp_path))


def test_checker_rejects_stale_a2_pending_claim_without_repeated_pr_token(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace("Status: Closed.", "Status: Planned."), encoding="utf-8"
    )
    assert any("stale A2 active/pending claim" in error for error in _errors(tmp_path))


def test_checker_rejects_stale_a2_blocked_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace("Status: Closed.", "Status: Planned but blocked."),
        encoding="utf-8",
    )
    assert any("stale A2 active/pending claim" in error for error in _errors(tmp_path))


def test_checker_rejects_duplicate_closeout_anchor(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger()
        + '\n<a id="ledger-p1-rag-hardening-followthrough"></a>\n- [ ] Status: Planned\n',
        encoding="utf-8",
    )
    assert any("expected exactly one start anchor" in error for error in _errors(tmp_path))


def test_checker_allows_active_docs_phrase(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    assert _errors(tmp_path) == []


def test_checker_rejects_forbidden_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1415_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "Semantic cache, Redis/GPTCache",
            "PR-A2 opens semantic cache. Redis/GPTCache",
        ),
        encoding="utf-8",
    )
    assert any("forbidden runtime/scope expansion claim" in error for error in _errors(tmp_path))


def test_checker_rejects_closed_token_runtime_expansion_bypass(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1415_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "Semantic cache, Redis/GPTCache",
            "PR-A2 opens semantic cache for serving; historical closeout is closed. Redis/GPTCache",
        ),
        encoding="utf-8",
    )
    assert any("forbidden runtime/scope expansion claim" in error for error in _errors(tmp_path))


def test_checker_rejects_historical_token_runtime_expansion_bypass(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1415_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "Semantic cache, Redis/GPTCache",
            "Historical note: PR-A2 opens semantic cache. Redis/GPTCache",
        ),
        encoding="utf-8",
    )
    assert any("forbidden runtime/scope expansion claim" in error for error in _errors(tmp_path))


def test_checker_rejects_duplicate_conflicting_gate_marker(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    gate = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate.write_text(
        _valid_gate().replace(
            "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
            "<!-- SEMANTIC_CACHE_GATE_STATUS: open -->\n<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
        ),
        encoding="utf-8",
    )
    assert any("SEMANTIC_CACHE_GATE_STATUS" in error for error in _errors(tmp_path))


def test_checker_rejects_comment_only_landed_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/contracts.py",
        """# class RAGDegradedReason
# VECTOR_FALLBACK_NO_RESULTS = "vector_fallback_no_results"
# VECTOR_FALLBACK_EXCEPTION = "vector_fallback_exception"
# VECTOR_FALLBACK_SUBJECT_MISSING = "vector_fallback_subject_missing"
# FORMATTED_CONTEXT_MALFORMED = "formatted_context_malformed"
# REDACTED_CONTEXT_MALFORMED = "redacted_context_malformed"
""",
    )
    assert any("missing class RAGDegradedReason" in error for error in _errors(tmp_path))


def test_checker_rejects_nested_enum_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/contracts.py",
        """class Container:
    class RAGDegradedReason:
        VECTOR_FALLBACK_NO_RESULTS = "vector_fallback_no_results"
        VECTOR_FALLBACK_EXCEPTION = "vector_fallback_exception"
        VECTOR_FALLBACK_SUBJECT_MISSING = "vector_fallback_subject_missing"
        FORMATTED_CONTEXT_MALFORMED = "formatted_context_malformed"
        REDACTED_CONTEXT_MALFORMED = "redacted_context_malformed"
""",
    )
    assert any("missing class RAGDegradedReason" in error for error in _errors(tmp_path))


def test_checker_rejects_nested_runtime_function_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/orchestration.py",
        """from core.rag.contracts import RAGDegradedReason


def wrapper() -> object:
    def _resolve_confidence() -> None:
        return None

    def _non_rag_result(subject_id: int) -> object:
        return build(subject_id=subject_id)

    return (
        _resolve_confidence,
        _non_rag_result,
        RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
        RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
    )
""",
    )
    assert any(
        "missing module-level function _resolve_confidence" in error for error in _errors(tmp_path)
    )


def test_checker_rejects_string_only_test_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        'NAMES = "test_missing_subject_id_returns_empty_without_encoding '
        "test_wrong_query_dimensions_return_empty_without_db_work "
        "test_retrieve_vector_sqlite_binds_subject_id "
        'test_vector_success_skips_malformed_rows_without_poisoning_whole_result"\n',
    )
    assert any("missing test function" in error for error in _errors(tmp_path))


def test_checker_rejects_nested_required_test_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """def wrapper():
    def test_missing_subject_id_returns_empty_without_encoding(): pass
    def test_wrong_query_dimensions_return_empty_without_db_work(): pass
    def test_retrieve_vector_sqlite_binds_subject_id(): pass
    def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("missing test function" in error for error in _errors(tmp_path))


def test_checker_rejects_dead_helper_call_keyword_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/vector_rag.py",
        """from core.rag.contracts import RAGDegradedReason


def _normalize_embedding_vector() -> None:
    return None


def _retrieve_vector_postgres(session: object, subject_id: int) -> None:
    return None


def _retrieve_vector_from_db(session: object, subject_id: int) -> None:
    return None


def _retrieve_vector_sqlite() -> tuple[object, object]:
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )


def dead_helper(session: object, subject_id: int) -> None:
    apply_user_rls_context(session, user_id=subject_id)
""",
    )
    assert any(
        "missing call proof _retrieve_vector_from_db" in error for error in _errors(tmp_path)
    )


def test_checker_rejects_similar_method_call_keyword_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/vector_rag.py",
        """from core.rag.contracts import RAGDegradedReason


def _normalize_embedding_vector() -> None:
    return None


def _retrieve_vector_postgres(session: object, subject_id: int) -> None:
    return None


def _retrieve_vector_from_db(session: object, subject_id: int) -> tuple[object, object]:
    session.apply_user_rls_context(user_id=subject_id)
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )


def _retrieve_vector_sqlite() -> tuple[object, object]:
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )
""",
    )
    assert any(
        "missing call proof _retrieve_vector_from_db" in error for error in _errors(tmp_path)
    )


def test_checker_rejects_dead_helper_subject_id_keyword_marker_spoof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/orchestration.py",
        """from core.rag.contracts import RAGDegradedReason


def _resolve_confidence() -> None:
    return None


def _non_rag_result() -> None:
    return None


def _run_orchestration(subject_id: int) -> object:
    retrieve_context_structured()
    return (
        RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
        RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
    )


def dead_helper(subject_id: int) -> None:
    retrieve_context_structured(subject_id=subject_id)
    retrieve_recursive_context_structured(subject_id=subject_id)
    _build_knowledge_candidates(subject_id=subject_id)
""",
    )
    assert any("missing call proof _run_orchestration" in error for error in _errors(tmp_path))


def test_checker_rejects_degraded_reason_marker_spoof_outside_target_function(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/orchestration.py",
        """from core.rag.contracts import RAGDegradedReason


def _resolve_confidence() -> None:
    return None


def _non_rag_result() -> None:
    return None


def _run_orchestration(subject_id: int) -> None:
    retrieve_context_structured(subject_id=subject_id)
    retrieve_recursive_context_structured(subject_id=subject_id)
    _build_knowledge_candidates(subject_id=subject_id)


def dead_helper() -> tuple[object, object]:
    return (
        RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
        RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
    )
""",
    )
    assert any("missing AST reference _run_orchestration" in error for error in _errors(tmp_path))


def test_checker_rejects_unreachable_runtime_proof_after_return(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/orchestration.py",
        """from core.rag.contracts import RAGDegradedReason


def _resolve_confidence() -> None:
    return None


def _non_rag_result() -> None:
    return None


def _run_orchestration(subject_id: int) -> object:
    return object()
    asyncio.to_thread(retrieve_recursive_context_structured, subject_id=subject_id)
    asyncio.to_thread(retrieve_context_structured, subject_id=subject_id)
    _build_knowledge_candidates(subject_id=subject_id)
    return (
        RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
        RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
    )
""",
    )
    errors = _errors(tmp_path)
    assert any("missing AST reference _run_orchestration" in error for error in errors)
    assert any("missing call proof _run_orchestration" in error for error in errors)


def test_checker_rejects_runtime_symbol_rebound_after_definition(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "core/rag/vector_rag.py",
        """from core.rag.contracts import RAGDegradedReason


def _normalize_embedding_vector() -> None:
    return None


def _retrieve_vector_postgres(session: object, subject_id: int) -> None:
    return None


def _retrieve_vector_from_db(session: object, subject_id: int) -> tuple[object, object]:
    apply_user_rls_context(session, user_id=subject_id)
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )


_retrieve_vector_from_db = None


def _retrieve_vector_sqlite() -> tuple[object, object]:
    return (
        RAGDegradedReason.VECTOR_FALLBACK_SUBJECT_MISSING,
        RAGDegradedReason.VECTOR_FALLBACK_NO_RESULTS,
    )
""",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_destructuring_runtime_symbol_rebound(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    vector_path = tmp_path / "core/rag/vector_rag.py"
    vector_path.write_text(
        vector_path.read_text(encoding="utf-8")
        + "\n(_retrieve_vector_from_db, _other) = (None, None)\n",
        encoding="utf-8",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_namedexpr_runtime_symbol_rebound(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    vector_path = tmp_path / "core/rag/vector_rag.py"
    vector_path.write_text(
        vector_path.read_text(encoding="utf-8")
        + "\nif (_retrieve_vector_from_db := None):\n    pass\n",
        encoding="utf-8",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_nested_runtime_symbol_rebound_after_definition(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    vector_path = tmp_path / "core/rag/vector_rag.py"
    vector_path.write_text(
        vector_path.read_text(encoding="utf-8")
        + "\nif True:\n    _retrieve_vector_from_db = None\n",
        encoding="utf-8",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_import_rebinding_required_runtime_symbol(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    vector_path = tmp_path / "core/rag/vector_rag.py"
    vector_path.write_text(
        vector_path.read_text(encoding="utf-8")
        + "\nfrom other.module import _retrieve_vector_from_db\n",
        encoding="utf-8",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_wildcard_import_runtime_symbol_rebound(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    vector_path = tmp_path / "core/rag/vector_rag.py"
    vector_path.write_text(
        vector_path.read_text(encoding="utf-8") + "\nfrom other.module import *\n",
        encoding="utf-8",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_skipped_required_test(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest


@pytest.mark.skip(reason="disabled")
def test_missing_subject_id_returns_empty_without_encoding(): pass


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be skipped or xfailed" in error for error in _errors(tmp_path))


def test_checker_rejects_alias_bound_skipped_required_test(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

SKIP_REQUIRED = pytest.mark.skip(reason="disabled")


@SKIP_REQUIRED
def test_missing_subject_id_returns_empty_without_encoding(): pass


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be skipped or xfailed" in error for error in _errors(tmp_path))


def test_checker_rejects_computed_decorator_alias(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

DISABLE = [pytest.mark.skip(reason="disabled")]


@DISABLE[0]
def test_missing_subject_id_returns_empty_without_encoding(): pass


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be skipped or xfailed" in error for error in _errors(tmp_path))


def test_checker_rejects_subscripted_decorator_alias_assignment(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

DISABLE = (pytest.mark.skip(reason="disabled"),)[0]


@DISABLE
def test_missing_subject_id_returns_empty_without_encoding(): pass


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be skipped or xfailed" in error for error in _errors(tmp_path))


def test_checker_rejects_module_level_xfail_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

pytestmark = pytest.mark.xfail(reason="disabled")


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_module_level_pytest_xfail(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

pytest.xfail("disabled", allow_module_level=True)


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_annotated_pytestmark_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

pytestmark: object = pytest.mark.skip(reason="disabled")


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_conditional_pytestmark_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

if True:
    pytestmark = pytest.mark.skip(reason="disabled")


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_try_block_pytestmark_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

try:
    pytestmark = pytest.mark.skip(reason="disabled")
except Exception:
    pass


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_module_dunder_test_false_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """__test__ = False


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_module_dunder_test_zero_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """__test__ = 0


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_module_level_pytest_skip_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

pytest.skip("disabled", allow_module_level=True)


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_assignment_wrapped_module_level_skip(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

DISABLED = pytest.skip("disabled", allow_module_level=True)


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_import_pytest_as_alias_module_level_skip(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest as pt

pt.skip("disabled", allow_module_level=True)


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_kwargs_expanded_allow_module_level(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

pytest.skip("disabled", **{"allow_module_level": True})


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_computed_truthy_allow_module_level(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

pytest.skip("disabled", allow_module_level=(1 == 1))


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_kwargs_alias_allow_module_level(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

KW = {"allow_module_level": True}
pytest.skip("disabled", **KW)


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_imported_alias_module_level_pytest_skip(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """from pytest import skip as module_skip

ALLOW_MODULE = True
module_skip("disabled", allow_module_level=ALLOW_MODULE)


def test_missing_subject_id_returns_empty_without_encoding(): pass
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any(
        "required test module must not disable pytest collection" in error
        for error in _errors(tmp_path)
    )


def test_checker_rejects_function_local_skip_alias(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """def test_missing_subject_id_returns_empty_without_encoding():
    from pytest import skip as local_skip

    local_skip("disabled")


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be skipped or xfailed" in error for error in _errors(tmp_path))


def test_checker_rejects_getattr_based_test_skip(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest

getattr(pytest, "skip")("disabled", allow_module_level=True)


def test_missing_subject_id_returns_empty_without_encoding():
    getattr(pytest, "skip")("disabled")


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    errors = _errors(tmp_path)
    assert any(
        "required test module must not disable pytest collection" in error for error in errors
    )
    assert any("must not be skipped or xfailed" in error for error in errors)


def test_checker_rejects_in_test_pytest_skip_for_required_tests(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """import pytest


def test_missing_subject_id_returns_empty_without_encoding(): pytest.skip("disabled")
def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be skipped or xfailed" in error for error in _errors(tmp_path))


def test_checker_rejects_required_test_rebound_after_definition(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """def test_missing_subject_id_returns_empty_without_encoding(): pass
test_missing_subject_id_returns_empty_without_encoding = None


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_required_test_dunder_test_override_after_definition(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """def test_missing_subject_id_returns_empty_without_encoding(): pass
test_missing_subject_id_returns_empty_without_encoding.__test__ = 0


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    assert any("falsy __test__" in error for error in _errors(tmp_path))


def test_checker_rejects_computed_falsy_dunder_test_values(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """__test__ = bool(0)


def test_missing_subject_id_returns_empty_without_encoding(): pass
test_missing_subject_id_returns_empty_without_encoding.__test__ = bool(0)


def test_wrong_query_dimensions_return_empty_without_db_work(): pass
def test_retrieve_vector_sqlite_binds_subject_id(): pass
def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(): pass
""",
    )
    errors = _errors(tmp_path)
    assert any(
        "required test module must not disable pytest collection" in error for error in errors
    )
    assert any("falsy __test__" in error for error in errors)


def test_checker_rejects_uncollectable_required_test_class(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """class TestVectorRequired:
    def __init__(self) -> None:
        pass

    def test_missing_subject_id_returns_empty_without_encoding(self): pass
    def test_wrong_query_dimensions_return_empty_without_db_work(self): pass
    def test_retrieve_vector_sqlite_binds_subject_id(self): pass
    def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(self): pass
""",
    )
    assert any(
        "must not live in disabled or uncollectable class" in error for error in _errors(tmp_path)
    )


def test_checker_rejects_class_method_module_rebound(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """class TestVectorRequired:
    def test_missing_subject_id_returns_empty_without_encoding(self): pass
    def test_wrong_query_dimensions_return_empty_without_db_work(self): pass
    def test_retrieve_vector_sqlite_binds_subject_id(self): pass
    def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(self): pass


TestVectorRequired.test_missing_subject_id_returns_empty_without_encoding = None
""",
    )
    assert any("must not be rebound after definition" in error for error in _errors(tmp_path))


def test_checker_rejects_class_method_module_test_override(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    _write(
        tmp_path / "tests/test_vector_rag.py",
        """class TestVectorRequired:
    def test_missing_subject_id_returns_empty_without_encoding(self): pass
    def test_wrong_query_dimensions_return_empty_without_db_work(self): pass
    def test_retrieve_vector_sqlite_binds_subject_id(self): pass
    def test_vector_success_skips_malformed_rows_without_poisoning_whole_result(self): pass


TestVectorRequired.test_missing_subject_id_returns_empty_without_encoding.__test__ = 0
""",
    )
    assert any("falsy __test__" in error for error in _errors(tmp_path))


def test_checker_rejects_local_path_leakage_in_closeout_text(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1415_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nLocal evidence: /Users/example/worktrees/a2\n", encoding="utf-8"
    )
    assert any("local path leakage" in error for error in _errors(tmp_path))


def test_checker_rejects_punctuation_prefixed_worktrees_leakage(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1415_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nLocal evidence: (worktrees/ai-rag-hardening-a2-closeout)\n",
        encoding="utf-8",
    )
    assert any("local path leakage" in error for error in _errors(tmp_path))


def test_checker_rejects_capitalized_worktrees_leakage(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1415_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nLocal evidence: (Worktrees/ai-rag-hardening-a2-closeout)\n",
        encoding="utf-8",
    )
    assert any("local path leakage" in error for error in _errors(tmp_path))


def test_checker_redacts_external_override_path_errors(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    errors = _errors_with_mapping(tmp_path, Path("/tmp/a2-secret-missing.md"))
    joined = "\n".join(errors)
    assert "<external-path>: unable to read" in joined
    assert "/tmp/a2-secret-missing.md" not in joined
