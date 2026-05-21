from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/ci/check_ai_recursive_methods_w1_closeout.py"
PR_NUMBER = "1499"
MERGE_DATE = "2026-04-23"
MERGE_TIMESTAMP = "2026-04-23T01:37:29Z"
MERGE_COMMIT = "".join(("1e7166e5", "5c54448c", "0d647533", "8e1b9984", "efd0caf1"))
ORIGINAL_BRANCH = "codex/ai-recursive-methods-w1"
REQUIRED_RUNTIME_FILES = (
    "core/rag/recursive_retrieval.py",
    "core/rag/orchestration.py",
    "core/ai/insight_runtime.py",
    "app/services/insight_runtime.py",
    "app/services/insight_application_service.py",
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_checker(repo_root: Path) -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo_root),
            "--ledger",
            str(repo_root / "docs/roadmap/BACKLOG_LEDGER.md"),
            "--roadmap",
            str(repo_root / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"),
            "--mapping",
            str(repo_root / "docs/review/PR_1499_FIXED_MAPPING.md"),
            "--semantic-cache-gate",
            str(repo_root / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    return [line for line in f"{result.stderr}\n{result.stdout}".splitlines() if line.strip()]


def _valid_ledger() -> str:
    return f"""# Backlog

<a id="ledger-p1-recursive-methods"></a>
- [ ] P1: Recursive methods for LLM/RAG/AI assistant
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-A7 / PR #{PR_NUMBER}
  - Status: W1 landed via PR #{PR_NUMBER} on {MERGE_DATE} with merge commit `{MERGE_COMMIT}` from branch `{ORIGINAL_BRANCH}`; this closeout reconciles stale truth and does not duplicate implementation. Parent P1 checkbox stays open until the full recursive-framework DoD is proven.
  - DoD:
    - Integration tests pass.
  - Merged increments (tracking only; parent P1 checkbox stays open until full DoD):
    - PR: #{PR_NUMBER}
    - Scope: bounded recursive RAG and bounded recursive verification.
    - Closeout note: semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, public DTOs, provider-side tree-of-thought, and recursive learning remain out of scope.

<a id="next"></a>
- [ ] Next item
"""


def _valid_roadmap() -> str:
    return f"""# RAG roadmap

## PR-A7 - recursive methods W1
#### Title
`feat(ai-runtime): rollout recursive RAG and bounded recursive verification`

#### Status
Landed via PR #{PR_NUMBER} on {MERGE_DATE} with merge commit `{MERGE_COMMIT}` from branch `{ORIGINAL_BRANCH}`. This closeout reconciles stale backlog/roadmap/review truth and does not duplicate runtime implementation. The parent recursive-methods P1 item remains open until the full recursive framework DoD is separately proven.

#### Backlog target
`ledger-p1-recursive-methods`

#### Goal
Promote recursive methods as a bounded runtime improvement.

#### Landed W1 scope
- bounded recursive RAG and bounded recursive verification on existing product-AI insight seams
- recursive budgets and thin app/service handoff
- existing `VerificationBundle` truth preserved

#### Out of scope
- semantic cache implementation or gate opening
- Redis/GPTCache rollout or backend approval
- GraphRAG, ContextManifest, embeddings, or vector database rollout
- DB persistence, public route, OpenAPI, DTO, or response-shape changes
- provider-side tree-of-thought / chain-of-thought expansion
- recursive learning or user-feedback adaptation

#### Constraint
Use budgets, caching, early stopping, and deterministic depth control.

---

## PR-A8
"""


def _valid_mapping() -> str:
    return f"""# PR #{PR_NUMBER} mapping

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#discussion_r3127164224 -> 1067c5acd
Disposition: FIXED

## Post-Merge Closeout

- State: `MERGED`
- PR #{PR_NUMBER} merged at `{MERGE_TIMESTAMP}`
- Merge commit: `{MERGE_COMMIT}`
- Original branch: `{ORIGINAL_BRANCH}`
- Closeout scope: PR-A7 W1 is not re-opened and implementation is not duplicated.
- Parent scope: the broader recursive-methods P1 item remains open.
- Boundary: semantic-cache gate remained closed. Redis/GPTCache rollout,
  GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO, and
  response-shape changes remained out of scope for this closeout.

## Historical Merge Readiness

This section is historical evidence only. PR #{PR_NUMBER} is already merged, so this closeout does not re-run or reassert the original readiness checklist.
"""


def _valid_gate() -> str:
    return """# PulsePlate Semantic Cache Gate and Plan

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->
"""


def _write_valid_repo(tmp_path: Path) -> None:
    for relpath in REQUIRED_RUNTIME_FILES:
        _write(tmp_path / relpath, "# exists\n")
    _write(tmp_path / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(
        tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md",
        _valid_roadmap(),
    )
    _write(tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md", _valid_mapping())
    _write(
        tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        _valid_gate(),
    )


def test_checker_passes_on_current_repository() -> None:
    assert _run_checker(REPO_ROOT) == []


def test_checker_passes_on_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert _run_checker(tmp_path) == []


def test_checker_rejects_stale_active_pr1499_ledger_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "W1 landed via PR #1499",
            "In progress via PR #1499",
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("PR #1499 in-progress claim" in error for error in errors)


def test_checker_rejects_closed_parent_recursive_checkbox(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "- [ ] P1: Recursive methods for LLM/RAG/AI assistant",
            "- [x] P1: Recursive methods for LLM/RAG/AI assistant",
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("parent P1 checkbox is closed" in error for error in errors)


def test_checker_rejects_semantic_cache_gate_open_marker(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    gate = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate.write_text(
        _valid_gate().replace(
            "SEMANTIC_CACHE_GATE_STATUS: closed", "SEMANTIC_CACHE_GATE_STATUS: open"
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("SEMANTIC_CACHE_GATE_STATUS" in error for error in errors)


@pytest.mark.parametrize(
    ("claim", "expected"),
    [
        ("PR-A7 opens semantic-cache serving.", "PR-A7 opens semantic cache"),
        ("PR-A7\nopens semantic-cache serving.", "PR-A7 opens semantic cache"),
        ("PR-A7\n\nopens semantic-cache serving.", "PR-A7 opens semantic cache"),
        ("PR\nA7 opens semantic-cache serving.", "PR-A7 opens semantic cache"),
        ("PR #1499 enables semantic cache.", "PR-A7 opens semantic cache"),
        ("PR-A7 opens semanticcache serving.", "PR-A7 opens semantic cache"),
        ("#1499 opens semantic-cache serving.", "PR-A7 opens semantic cache"),
        ("PR-1499 opens semantic-cache serving.", "PR-A7 opens semantic cache"),
        (
            "PR-A7 is not merely documentation and opens semantic-cache serving.",
            "PR-A7 opens semantic cache",
        ),
        (
            "PR-A7 is not merely documentation, opens semantic-cache serving.",
            "PR-A7 opens semantic cache",
        ),
        (
            "No GraphRAG rollout and semantic-cache serving is enabled.",
            "semantic cache direct activation",
        ),
        (
            "Without extra approvals PR-A7 opens semantic-cache serving.",
            "PR-A7 opens semantic cache",
        ),
        ("Semantic-cache serving is enabled by PR-A7.", "semantic cache enabled"),
        ("Semantic-cache opened.", "semantic cache direct activation"),
        ("Semantic-cache enabled.", "semantic cache direct activation"),
        ("Semantic-cache is approved.", "semantic cache direct activation"),
        ("Semantic-cache was enabled.", "semantic cache direct activation"),
        ("Semantic-cache was approved.", "semantic cache direct activation"),
        ("Semanticcache enabled.", "semantic cache direct activation"),
        ("Semantic-cache open.", "semantic cache direct activation"),
        ("Semantic-cache gate is approved.", "semantic cache direct activation"),
        ("Semantic-cache serving is selected.", "semantic cache direct activation"),
        ("Semantic-cache remains open.", "semantic cache active status"),
        ("Semantic-cache stays open.", "semantic cache active status"),
        ("Semantic-cache\nis open.", "semantic cache active status"),
        ("Semantic-cache is production-ready.", "semantic cache active status"),
        ("Semantic-cache has been opened.", "semantic cache active status"),
        ("PR-A7 approves Redis for semantic-cache rollout.", "PR-A7 approves Redis"),
        ("PR-A7 chooses Redis for semantic-cache.", "PR-A7 approves Redis"),
        ("GPTCache is rollout-ready for semantic-cache serving.", "Redis/GPTCache"),
        ("PR-A7 authorizes GraphRAG rollout.", "forbidden runtime surface"),
        (
            "PR-A7 does not open semantic-cache serving, but opens GraphRAG rollout.",
            "forbidden runtime surface",
        ),
        (
            "GraphRAG is out of scope, but approved by PR-A7.",
            "forbidden runtime surface",
        ),
        ("No, GraphRAG rollout is approved by PR-A7.", "forbidden runtime surface"),
        ("PR-A7 authorizes Context Manifest rollout.", "forbidden runtime surface"),
        ("PR-A7 approves context-manifest rollout.", "forbidden runtime surface"),
        ("PR-A7 approved database persistence.", "forbidden runtime surface"),
        ("PR-A7 approves DB rollout.", "forbidden runtime surface"),
        ("PR-A7 approves database rollout.", "forbidden runtime surface"),
        ("PR-A7 approves vector database rollout.", "forbidden runtime surface"),
        ("PR-A7 approves vector-search rollout.", "forbidden runtime surface"),
        ("PR-A7 approves OpenAPI route changes.", "forbidden runtime surface"),
        ("GraphRAG rollout is approved.", "forbidden runtime surface"),
        ("GraphRAG rollout was approved.", "forbidden runtime surface"),
        ("GraphRAG rollout got approved.", "forbidden runtime surface"),
        ("GraphRAG rollout became approved.", "forbidden runtime surface"),
        ("GraphRAG rollout stays open.", "forbidden runtime surface"),
        ("Graph-RAG rollout is approved.", "forbidden runtime surface"),
        ("GraphRAG is implemented.", "forbidden runtime surface"),
        ("GraphRAG rollout remains open.", "forbidden runtime surface"),
        ("Context Manifest is supported.", "forbidden runtime surface"),
        ("Context Manifest is live.", "forbidden runtime surface"),
        ("GraphRAG rollout is approved by PR-A7.", "forbidden runtime surface"),
        (
            "No GraphRAG rollout, GraphRAG rollout is approved by PR-A7.",
            "forbidden runtime surface",
        ),
        (
            "GraphRAG is out of scope or approved by PR-A7.",
            "forbidden runtime surface",
        ),
        (
            "No GraphRAG rollout or GraphRAG rollout is approved by PR-A7.",
            "forbidden runtime surface",
        ),
        ("PR-A7 approves Graph-RAG rollout.", "forbidden runtime surface"),
        ("Context Manifest rollout is authorized by PR-A7.", "forbidden runtime surface"),
        ("Database rollout is approved by PR-A7.", "forbidden runtime surface"),
        ("OpenAPI route changes are approved by PR-A7.", "forbidden runtime surface"),
        ("PR-A7 permits raw prompt and raw response caching.", "raw prompt/response"),
        ("PR-A7 allows\nraw responses.", "raw prompt/response"),
        ("PR-A7 allows\n\nraw responses.", "raw prompt/response"),
        ("Raw responses\nare cacheable.", "raw prompt/response"),
        ("PR-A7 permits\nraw account data caching.", "raw prompt/response"),
        ("PR-A7 authorizes\nraw HealthKit data caching.", "raw prompt/response"),
        ("PR-A7 can cache\nraw secret data.", "raw prompt/response"),
        ("PR #1499 allows caching raw responses.", "raw prompt/response"),
        ("PR-A7 can cache raw answers.", "raw prompt/response"),
        ("Semantic cache stores raw prompts.", "raw prompt/response"),
        ("PR-A7 permits raw account data caching.", "raw prompt/response"),
        ("PR-A7 allows raw HealthKit data caching.", "raw prompt/response"),
        ("PR-A7 authorizes raw secret data caching.", "raw prompt/response"),
    ],
)
def test_checker_rejects_forbidden_positive_claims(
    tmp_path: Path, claim: str, expected: str
) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace("\n---\n\n## PR-A8", f"\n{claim}\n\n---\n\n## PR-A8"),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any(expected in error for error in errors)


def test_checker_allows_explicit_out_of_scope_negative_claims(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap()
        + "\nPR-A7 does not open semantic-cache serving.\n"
        + "Redis is not approved for semantic-cache rollout.\n"
        + "GraphRAG is out of scope for PR-A7.\n"
        + "Semantic-cache gate remained closed.\n"
        + "Raw prompt/response caching remains blocked.\n"
        + "Raw prompt/response caching remains blocked by policy.\n"
        + "GraphRAG isn't approved by PR-A7.\n",
        encoding="utf-8",
    )

    assert _run_checker(tmp_path) == []


@pytest.mark.parametrize(
    "landed_scope_claim",
    [
        "DB persistence for recursive evidence writes",
        "public route changes for recursive methods",
        "Context Manifest rollout",
        "provider-side tree-of-thought expansion",
        "provider-side chain-of-thought expansion",
        "recursive learning",
        "user-feedback adaptation",
        "response-shape changes",
        "vector database rollout",
        "vector search",
        "embeddings rollout",
    ],
)
def test_checker_rejects_forbidden_landed_scope_items(
    tmp_path: Path, landed_scope_claim: str
) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "- existing `VerificationBundle` truth preserved",
            f"- existing `VerificationBundle` truth preserved\n- {landed_scope_claim}",
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("landed scope includes forbidden surface" in error for error in errors)


def test_checker_allows_negated_forbidden_landed_scope_items(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "- existing `VerificationBundle` truth preserved",
            "- existing `VerificationBundle` truth preserved\n- no DB persistence changes\n- no GraphRAG rollout",
        ),
        encoding="utf-8",
    )

    assert _run_checker(tmp_path) == []


def test_checker_rejects_mixed_landed_scope_line_after_negated_item(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "- existing `VerificationBundle` truth preserved",
            "- existing `VerificationBundle` truth preserved\n- no DB persistence changes but GraphRAG rollout",
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("landed scope includes forbidden surface" in error for error in errors)


def test_checker_rejects_stale_pr1499_mapping_readiness_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nfinal merge-cycle reconfirmation is still pending.\n",
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("pending final merge-cycle claim" in error for error in errors)


def test_checker_rejects_required_checks_still_pending_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nrequired checks are still pending.\n",
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("required-checks pending claim" in error for error in errors)


def test_checker_rejects_broader_stale_a7_active_closeout_claim(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            '<a id="next"></a>',
            'PR-A7 lane remains active and pending final closure tasks.\n\n<a id="next"></a>',
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("PR-A7 stale active/pending closeout claim" in error for error in errors)


def test_checker_rejects_forbidden_claim_outside_pr1499_closeout_block(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "## Post-Merge Closeout",
            "PR-A7 opens semantic-cache serving.\n\n## Post-Merge Closeout",
        ),
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("PR-A7 opens semantic cache" in error for error in errors)


def test_checker_rejects_checked_historical_readiness_assertions(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping()
        + "\n- [x] Current-head CI is green for PR branch head\n"
        + "* [x] Current-head CI is green for PR branch head\n"
        + "+ [x] Current-head CI is green for PR branch head\n"
        + "1. [x] Current-head CI is green for PR branch head\n"
        + "- [x] Required checks complete (no pending jobs)\n",
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("checked current-head CI assertion" in error for error in errors)
    assert any("checked required-checks assertion" in error for error in errors)


def test_checker_rejects_checked_generic_ci_and_all_required_checks(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping()
        + "\n- [x] CI green on latest pushed head\n"
        + "- [x] All required checks complete (no pending jobs)\n",
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("checked CI-green assertion" in error for error in errors)
    assert any("checked required-checks assertion" in error for error in errors)


def test_checker_rejects_checked_historical_local_readiness_assertions(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1499_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping()
        + "\n- [x] Pre-commit green on latest pushed head\n"
        + "- [x] `make verify` green on latest pushed head\n",
        encoding="utf-8",
    )

    errors = _run_checker(tmp_path)

    assert any("checked pre-commit assertion" in error for error in errors)
    assert any("checked make verify assertion" in error for error in errors)


def test_checker_rejects_missing_recursive_runtime_file(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    (tmp_path / "core/rag/orchestration.py").unlink()

    errors = _run_checker(tmp_path)

    assert any("core/rag/orchestration.py" in error for error in errors)
