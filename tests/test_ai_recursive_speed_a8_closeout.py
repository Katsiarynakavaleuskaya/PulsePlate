from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import runpy
import subprocess
import sys
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/ci/check_ai_recursive_speed_a8_closeout.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_gate() -> str:
    return """# Semantic Cache Gate

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->
"""


def _valid_ledger() -> str:
    return """# Backlog

<a id="ledger-p1-recursive-methods"></a>
- [ ] P1: Recursive methods for LLM/RAG/AI assistant (multi-hop retrieval, recursive reasoning, self-refinement, self-verification, learning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-A7 / PR #1499
  - Status: W1 landed via PR #1499. A8 speed optimization landed via PR #1506 and was hardened by PR #1578. Parent P1 checkbox stays open until the full recursive-framework DoD is proven.
  - Reason (EN): Previously cited latency and quality percentage ranges are benchmark hypotheses only, not shipped performance claims.
  - DoD:
    - Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.
  - Merged increments (tracking only; parent P1 checkbox stays open until full DoD):
    - PR: [#1506](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1506) - merged 2026-04-23T20:41:25Z with merge commit `19fdbd3098a6aef780a71e94e94980cb3d0f61ee` from branch `codex/ai-recursive-speed-optimization-w1`; title `feat(ai-runtime): add philosophical speed optimization to recursive stack`.
    - Scope: deterministic recursive optimization hints and bounded early stopping seams; no fresh benchmark result.
    - PR: [#1578](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1578) - merged 2026-04-29T20:32:42Z with merge commit `37995a6e8d4e9451b85e7e6284e9bd0cd5afff45` from branch `codex/wave6-a8-recursive-speed-optimization`; title `feat(ai-runtime): add philosophical speed optimization to recursive stack`.
    - Closeout note: semantic cache remains closed. Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, recursive learning, provider chain-of-thought, provider tree-of-thought, and default activation remain out of scope.
"""


def _valid_roadmap() -> str:
    return """# RAG roadmap

## PR-A8 - speed optimization for recursive stack
#### Title
`feat(ai-runtime): add philosophical speed optimization to recursive stack`

#### Current status
Landed via PR #1506 on 2026-04-23T20:41:25Z with merge commit `19fdbd3098a6aef780a71e94e94980cb3d0f61ee` from branch `codex/ai-recursive-speed-optimization-w1`; hardened by PR #1578 on 2026-04-29T20:32:42Z with merge commit `37995a6e8d4e9451b85e7e6284e9bd0cd5afff45` from branch `codex/wave6-a8-recursive-speed-optimization`. This closeout reconciles stale roadmap/backlog/review truth.

#### Landed and hardened scope
- deterministic recursive optimization hints
- bounded early-stop diagnostics
- thin app/service handoff without public contract changes

#### Benchmark boundary
Runtime evidence is limited to landed symbols, tests, and review artifacts. This closeout does not claim fresh benchmark results. Any latency or quality number remains a hypothesis target that requires benchmark validation.

#### Out of scope
Semantic cache remains closed. Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, recursive learning, provider chain-of-thought, provider tree-of-thought, and default activation remain out of scope.

---

## PR-A9
"""


def _valid_mapping(number: str, merged_at: str, commit: str, branch: str) -> str:
    return f"""# PR #{number} - Fixed in Commit Mapping (canonical)

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/{number}#discussion_r1 -> abc123
Disposition: FIXED

## Post-Merge Closeout

- State: `MERGED`
- Title: `feat(ai-runtime): add philosophical speed optimization to recursive stack`
- PR #{number} merged at `{merged_at}`
- Merge commit: `{commit}`
- Original branch: `{branch}`
- Closeout scope: recursive speed optimization evidence is historical and landed.
- Boundary: semantic cache remains closed; Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, recursive learning, provider chain-of-thought, provider tree-of-thought, and default activation remain out of scope.

## Historical Merge Readiness

This section is historical evidence only. PR #{number} is already merged, so this closeout does not re-run or reassert the original readiness checklist.
"""


def _write_valid_repo(tmp_path: Path) -> None:
    _write(
        tmp_path / "core/ai/insight_runtime.py",
        (
            "class RecursiveRolloutPolicy:\n"
            "    pass\n\n"
            "def _build_recursive_optimization_hints() -> None:\n"
            "    return None\n"
        ),
    )
    _write(
        tmp_path / "core/rag/contracts.py",
        "class RecursiveOptimizationHints:\n    pass\n",
    )
    _write(
        tmp_path / "core/rag/orchestration.py",
        (
            "def orchestrate() -> object:\n"
            "    recursive_optimization_hints = object()\n"
            "    return recursive_optimization_hints\n"
        ),
    )
    _write(
        tmp_path / "core/rag/recursive_retrieval.py",
        (
            "early_stop_aggressive_short_circuit = 'enabled'\n"
            "early_stop_pragmatic_usefulness = 'enabled'\n\n"
            "def _should_short_circuit_from_hints() -> bool:\n"
            "    return True\n"
        ),
    )
    _write(
        tmp_path / "app/services/insight_runtime.py",
        (
            "def prepare(recursive_optimization_hints: object | None = None) -> object | None:\n"
            "    return recursive_optimization_hints\n"
        ),
    )
    _write(tmp_path / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(
        tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md",
        _valid_roadmap(),
    )
    _write(
        tmp_path / "docs/review/PR_1506_FIXED_MAPPING.md",
        _valid_mapping(
            "1506",
            "2026-04-23T20:41:25Z",
            "".join(("19fdbd30", "98a6aef7", "80a71e94", "e94980cb", "3d0f61ee")),
            "codex/ai-recursive-speed-optimization-w1",
        ),
    )
    _write(
        tmp_path / "docs/review/PR_1578_FIXED_MAPPING.md",
        _valid_mapping(
            "1578",
            "2026-04-29T20:32:42Z",
            "".join(("37995a6e", "8d4e9451", "b85e7e62", "84e9bd0c", "d5afff45")),
            "codex/wave6-a8-recursive-speed-optimization",
        ),
    )
    _write(tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md", _valid_gate())


def _errors(repo_root: Path) -> list[str]:
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
            "--mapping-1506",
            str(repo_root / "docs/review/PR_1506_FIXED_MAPPING.md"),
            "--mapping-1578",
            str(repo_root / "docs/review/PR_1578_FIXED_MAPPING.md"),
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


def _errors_with_repo_root_only(repo_root: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(repo_root)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    return [line for line in f"{result.stderr}\n{result.stdout}".splitlines() if line.strip()]


def _load_validate_closeout() -> Callable[..., list[str]]:
    namespace = runpy.run_path(str(CHECKER), run_name="a8_closeout_checker")
    return cast(Callable[..., list[str]], namespace["validate_closeout"])


def test_checker_passes_on_current_repository() -> None:
    assert _errors(REPO_ROOT) == []


def test_checker_passes_on_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert _errors(tmp_path) == []


def test_validate_closeout_direct_api_passes_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert _load_validate_closeout()(repo_root=tmp_path) == []


def test_checker_rejects_missing_pr1578_evidence(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1578_FIXED_MAPPING.md"
    mapping.write_text(
        mapping.read_text(encoding="utf-8").replace(
            "codex/wave6-a8-recursive-speed-optimization", "codex/stale-branch"
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("PR #1578 original branch" in error for error in errors)


def test_checker_requires_pr_evidence_in_active_docs_not_only_mapping(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(_valid_ledger().replace("#1506", "#9999"), encoding="utf-8")
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(_valid_roadmap().replace("#1506", "#9999"), encoding="utf-8")

    errors = _errors(tmp_path)

    assert any("PR #1506 active docs evidence" in error for error in errors)


def test_checker_resolves_default_docs_relative_to_repo_root(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1506_FIXED_MAPPING.md"
    mapping.write_text(
        mapping.read_text(encoding="utf-8").replace(
            "codex/ai-recursive-speed-optimization-w1", "codex/stale-branch"
        ),
        encoding="utf-8",
    )

    errors = _errors_with_repo_root_only(tmp_path)

    assert any("PR #1506 original branch" in error for error in errors)


def test_checker_rejects_missing_landed_symbol(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "core/rag/recursive_retrieval.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace("_should_short_circuit_from_hints", ""),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("recursive_retrieval.py landed symbol" in error for error in errors)


def test_checker_rejects_comment_only_landed_symbol(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "core/rag/recursive_retrieval.py"
    path.write_text(
        (
            "# _should_short_circuit_from_hints\n"
            "# early_stop_aggressive_short_circuit\n"
            "# early_stop_pragmatic_usefulness\n"
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("recursive_retrieval.py landed symbol" in error for error in errors)


def test_checker_rejects_string_literal_only_landed_symbol(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "core/rag/recursive_retrieval.py"
    path.write_text(
        (
            '"_should_short_circuit_from_hints"\n'
            '"early_stop_aggressive_short_circuit"\n'
            '"early_stop_pragmatic_usefulness"\n'
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("recursive_retrieval.py landed symbol" in error for error in errors)


def test_checker_rejects_dict_key_only_landed_symbol(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "core/rag/recursive_retrieval.py"
    path.write_text(
        (
            '{"_should_short_circuit_from_hints": 1, '
            '"early_stop_aggressive_short_circuit": 1, '
            '"early_stop_pragmatic_usefulness": 1}\n'
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("recursive_retrieval.py landed symbol" in error for error in errors)


def test_checker_rejects_unscoped_negation_with_positive_forbidden_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 semantic cache is not pending and enables production-ready rollout.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_unrelated_negation_with_positive_forbidden_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 is not pending, semantic cache is active.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_stale_pr_a8_active_writing(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 is an active implementation lane.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors)


def test_checker_rejects_reversed_stale_pr_a8_active_writing(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "Active implementation lane for PR-A8.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors)


def test_checker_rejects_closed_parent_recursive_methods_checkbox(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "- [ ] P1: Recursive methods for LLM/RAG/AI assistant",
            "- [x] P1: Recursive methods for LLM/RAG/AI assistant",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("parent P1 checkbox" in error for error in errors)


def test_checker_rejects_open_semantic_cache_gate_marker(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    gate = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate.write_text(
        _valid_gate().replace(
            "SEMANTIC_CACHE_GATE_STATUS: closed", "SEMANTIC_CACHE_GATE_STATUS: open"
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("SEMANTIC_CACHE_GATE_STATUS" in error for error in errors)


def test_checker_rejects_forbidden_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 enables semantic cache and Redis production-ready rollout.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_mixed_negation_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 does not open semantic cache, but approves Redis production-ready rollout.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_and_joined_mixed_negation_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 does not open semantic cache and approves Redis production-ready rollout.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


@pytest.mark.parametrize(
    "claim",
    (
        "PR-A8 authorizes GraphRAG rollout.",
        "PR-A8 permits ContextManifest runtime use.",
        "PR-A8 ships public route changes.",
        "PR-A8 ships public endpoint changes.",
        "PR-A8 adds DB persistence.",
        "PR-A8 adds database persistence.",
        "PR-A8 allows provider chain-of-thought.",
        "PR-A8 enables semantic caching.",
        "PR-A8 is opening semantic cache for production.",
        "PR-A8 is activating Redis rollout.",
        "PR-A8 turns semantic cache on by default.",
        "PR-A8 ships public API changes.",
    ),
)
def test_checker_rejects_runtime_expansion_action_verbs(tmp_path: Path, claim: str) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            claim,
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors), claim


def test_checker_rejects_stale_a8_wording_in_ledger(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger() + "\nPR-A8 is an active implementation lane.\n", encoding="utf-8"
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors)


def test_checker_rejects_line_wrapped_stale_a8_wording(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 is an\nactive implementation lane.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors)


def test_checker_allows_negated_active_lane_wording(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 is not an active implementation lane.",
        ),
        encoding="utf-8",
    )

    assert _errors(tmp_path) == []


@pytest.mark.parametrize(
    "claim",
    (
        "PR-A8 is not pending but remains an active implementation lane.",
        "PR-A8 is not pending and is an active implementation lane.",
    ),
)
def test_checker_rejects_mixed_negation_stale_a8_wording(tmp_path: Path, claim: str) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            claim,
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors), claim


def test_checker_rejects_stale_a8_wording_outside_a8_sections(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        "PR-A8 is an active implementation lane.\n\n" + _valid_roadmap(), encoding="utf-8"
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors)


def test_checker_rejects_section_local_stale_a8_wording(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "Active implementation lane.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("stale PR-A8 active/pending wording" in error for error in errors)


def test_checker_rejects_forbidden_runtime_claim_outside_a8_sections(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap() + "\n## Other Roadmap Item\n\nPR-A8 enables semantic cache by default.\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_bare_a8_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap() + "\n## Other Roadmap Item\n\nA8 enables semantic cache by default.\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_section_local_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "Enables semantic cache by default.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_section_local_semantic_cache_activation(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "Semantic cache is active for live traffic.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_line_wrapped_runtime_expansion_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "PR-A8 enables\nsemantic cache by default.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("forbidden PR-A8 runtime expansion claim" in error for error in errors)


def test_checker_rejects_unvalidated_benchmark_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.",
            "PR-A8 proves latency reduction 50-60% average and quality maintained >=95%.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("unvalidated benchmark claim" in error for error in errors)


def test_checker_rejects_section_local_benchmark_overclaim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "This closeout reconciles stale roadmap/backlog/review truth.",
            "Latency reduction 50-60% average and quality maintained >=95%.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("unvalidated benchmark claim" in error for error in errors)


def test_checker_rejects_line_wrapped_benchmark_overclaim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.",
            "PR-A8 proves latency reduction\n50-60% average and quality maintained >=95%.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("unvalidated benchmark claim" in error for error in errors)


def test_checker_rejects_contrasted_benchmark_overclaim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.",
            "Hypothesis target requires benchmark validation, but PR-A8 proves latency reduction 50-60% and quality maintained >=95%.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("unvalidated benchmark claim" in error for error in errors)


def test_checker_rejects_qualified_a8_benchmark_overclaim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.",
            "Hypothesis target (requires benchmark validation): PR-A8 proves latency reduction 50-60% and quality maintained >=95%.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("unvalidated benchmark claim" in error for error in errors)


def test_checker_rejects_bare_a8_benchmark_overclaim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.",
            "Hypothesis target (requires benchmark validation): A8 proves latency reduction 50-60% and quality maintained >=95%.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("unvalidated benchmark claim" in error for error in errors)


def test_checker_allows_negated_semantic_cache_status(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap() + "\n## Safety Notes\n\nSemantic cache is not active for live traffic.\n",
        encoding="utf-8",
    )

    assert _errors(tmp_path) == []


def test_checker_allows_negated_a8_benchmark_disclaimer(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained >=95%.",
            "PR-A8 does not guarantee latency reduction 50-60%.",
        ),
        encoding="utf-8",
    )

    assert _errors(tmp_path) == []


def test_checker_allows_explicit_out_of_scope_claims(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "default activation remain out of scope.",
            "default activation remain out of scope. PR-A8 does not open semantic cache.",
        ),
        encoding="utf-8",
    )

    assert _errors(tmp_path) == []
