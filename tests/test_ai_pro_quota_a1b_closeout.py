from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import runpy
import subprocess
import sys
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/ci/check_ai_pro_quota_a1b_closeout.py"

PR_1379_COMMIT = "".join(("1ddf8c67", "78ca1f13", "c2bfce2e", "052db540", "9e8d06ba"))
PR_1461_COMMIT = "".join(("cd01d9c6", "db898132", "02f85b8b", "9f4c8378", "e72380ea"))
PR_1466_COMMIT = "".join(("fa0979e7", "34b88575", "e01e3eca", "9ddd4d57", "ade86c05"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_gate() -> str:
    return """# PulsePlate Semantic Cache Gate and Plan

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->

Semantic cache remains closed and out of scope.
"""


def _valid_ledger() -> str:
    return f"""# Backlog

<a id="ledger-p1-pro-monthly-quota-ledger-reconciliation"></a>
- [x] P1: Reconcile PRO monthly quota ledger with live runtime truth
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-A1b (`docs(ai-runtime): reconcile A1b PRO quota closeout`)
  - Status: Closed. PR #1461 merged on 2026-04-19T11:34:45Z with merge commit `{PR_1461_COMMIT}` from branch `codex/wave6-a1b-pro-quota-reconciliation`; follow-up PR #1466 merged on 2026-04-19T11:34:46Z with merge commit `{PR_1466_COMMIT}` from branch `codex/pr1461-mapping-fix`.
  - Reason (EN): PR-A1b is docs/governance closeout only. Runtime truth remains PR #1379, merged on 2026-04-10T12:08:46Z with merge commit `{PR_1379_COMMIT}` from branch `feat/insight-fallback-chain`. PR-A1b does not reopen runtime quota logic.
  - Gate boundary: semantic-cache markers remain `closed / false / false / true`; Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, provider/auth/billing changes, and default activation remain out of scope.
  - Links:
    - `app/security/llm_monthly_quota.py`
    - `app/bootstrap/startup_guards.py`
    - `app/routers/cbt_insight.py`
    - `app/services/fitchef_runtime.py`
    - `tests/test_cbt_insight_api.py`

<a id="next"></a>
- [ ] Next item
"""


def _valid_roadmap() -> str:
    return f"""# RAG roadmap

## PR-A1b - PRO monthly quota ledger reconciliation
#### Title
`docs(ai-runtime): reconcile A1b PRO quota closeout`

#### Current status
Closed via PR #1461 on 2026-04-19T11:34:45Z with merge commit `{PR_1461_COMMIT}` from branch `codex/wave6-a1b-pro-quota-reconciliation`; follow-up PR #1466 on 2026-04-19T11:34:46Z with merge commit `{PR_1466_COMMIT}` from branch `codex/pr1461-mapping-fix`.

#### Runtime anchor
Runtime truth remains PR #1379, merged on 2026-04-10T12:08:46Z with merge commit `{PR_1379_COMMIT}` from branch `feat/insight-fallback-chain`. PR-A1b does not reopen runtime quota logic.

#### Landed closeout scope
- docs/governance closeout
- stale ledger and roadmap reconciliation
- guard coverage for A1b historical truth

#### Out of scope
Semantic cache remains closed. Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, provider/auth/billing changes, and default activation remain out of scope.

---

## PR-A2
"""


def _valid_packet() -> str:
    return f"""# Wave 6 A1b PRO Quota Reconciliation Task Packet

## Historical closeout status

This packet is historical. PR #1461 merged on 2026-04-19T11:34:45Z with merge commit `{PR_1461_COMMIT}` from branch `codex/wave6-a1b-pro-quota-reconciliation`, and PR #1466 merged on 2026-04-19T11:34:46Z with merge commit `{PR_1466_COMMIT}` from branch `codex/pr1461-mapping-fix`. Future A1b work uses a ready-for-review closeout, not the old active lane.

Runtime truth remains PR #1379, merged on 2026-04-10T12:08:46Z with merge commit `{PR_1379_COMMIT}` from branch `feat/insight-fallback-chain`.
"""


def _valid_mapping() -> str:
    return f"""# PR #1461 - Fixed in Commit Mapping (canonical)

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1461#discussion_r1 -> abc123
Disposition: FIXED

## Post-Merge Closeout

- State: `MERGED`
- PR #1461 merged at `2026-04-19T11:34:45Z`
- PR #1461 merge commit: `{PR_1461_COMMIT}`
- Original branch: `codex/wave6-a1b-pro-quota-reconciliation`
- PR #1466 merged at `2026-04-19T11:34:46Z`
- PR #1466 merge commit: `{PR_1466_COMMIT}`
- PR #1466 original branch: `codex/pr1461-mapping-fix`
- PR #1466 did not create a separate fixed-mapping artifact; it corrected this PR #1461 artifact.

## Historical Merge Readiness

This section is historical evidence only. PR #1461 is already merged, so this closeout does not re-run or reassert the original readiness checklist.
"""


def _write_runtime_markers(repo_root: Path) -> None:
    _write(
        repo_root / "app/security/llm_monthly_quota.py",
        (
            'PRO_TIER = "PRO"\n'
            "_PRO_LIMIT_ENV = 'PRO_LLM_INSIGHT_REQUESTS_PER_MONTH'\n"
            "_TIER_LIMIT_ENV = {PRO_TIER: _PRO_LIMIT_ENV}\n"
            "def require_pro_llm_monthly_limit() -> int:\n"
            "    return 20\n"
            "def attempt_consume_llm_monthly_quota(raw_key: str, *, tier: str) -> bool:\n"
            "    return True\n"
        ),
    )
    _write(
        repo_root / "app/bootstrap/startup_guards.py",
        "def run_startup_guards() -> None:\n    require_pro_llm_monthly_limit()\n",
    )
    _write(
        repo_root / "app/routers/cbt_insight.py",
        "def cbt_insight(_tier: str = Depends(require_pro_tier)) -> None:\n    pass\n",
    )
    _write(
        repo_root / "app/services/fitchef_runtime.py",
        "attempt_consume_llm_monthly_quota(api_key, tier=effective_tier)\n",
    )
    _write(
        repo_root / "tests/test_cbt_insight_api.py",
        (
            "def test_pro_tier_accepted_when_feature_enabled(): pass\n"
            "def test_unsafe_query_rejected_before_rag_and_quota(): pass\n"
            "def test_missing_transparency_registry_returns_503_without_consuming_quota(): pass\n"
            "def test_incomplete_transparency_registry_returns_503_without_consuming_quota(): pass\n"
        ),
    )


def _write_valid_repo(repo_root: Path) -> None:
    _write_runtime_markers(repo_root)
    _write(repo_root / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(
        repo_root / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md",
        _valid_roadmap(),
    )
    _write(
        repo_root
        / "docs/orchestration/WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md",
        _valid_packet(),
    )
    _write(repo_root / "docs/review/PR_1461_FIXED_MAPPING.md", _valid_mapping())
    _write(repo_root / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md", _valid_gate())


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
            "--packet",
            str(
                repo_root
                / "docs/orchestration/WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md"
            ),
            "--mapping-1461",
            str(repo_root / "docs/review/PR_1461_FIXED_MAPPING.md"),
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
    namespace = runpy.run_path(str(CHECKER), run_name="a1b_closeout_checker")
    return cast(Callable[..., list[str]], namespace["validate_closeout"])


def test_checker_passes_on_current_repository() -> None:
    assert _errors(REPO_ROOT) == []


def test_checker_passes_on_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert _errors(tmp_path) == []


def test_validate_closeout_direct_api_passes_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert _load_validate_closeout()(repo_root=tmp_path) == []


def test_checker_resolves_default_docs_relative_to_repo_root(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert _errors_with_repo_root_only(tmp_path) == []


def test_checker_rejects_invalid_default_docs_relative_to_repo_root(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(PR_1461_COMMIT, "not-a-real-pr1461-merge-commit"),
        encoding="utf-8",
    )

    errors = _errors_with_repo_root_only(tmp_path)

    assert any("PR #1461" in error for error in errors)


@pytest.mark.parametrize(
    ("replacement", "expected"),
    [
        ("not-a-real-pr1379-merge-commit", "PR #1379"),
        ("not-a-real-pr1461-merge-commit", "PR #1461"),
        ("not-a-real-pr1466-merge-commit", "PR #1466"),
    ],
)
def test_checker_rejects_wrong_merge_sha(tmp_path: Path, replacement: str, expected: str) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    original = ledger.read_text(encoding="utf-8")
    if expected == "PR #1379":
        token = PR_1379_COMMIT
    elif expected == "PR #1461":
        token = PR_1461_COMMIT
    else:
        token = PR_1466_COMMIT
    ledger.write_text(original.replace(token, replacement), encoding="utf-8")

    errors = _errors(tmp_path)

    assert any(expected in error for error in errors)


@pytest.mark.parametrize(
    ("stale", "expected"),
    [
        ("Status: A1b in progress", "stale active wording"),
        ("A1b docs lane is the next canonical slice", "stale active wording"),
        ("A1b may open in draft", "stale active wording"),
        ("A1b must late-rebase onto origin/main", "stale active wording"),
    ],
)
def test_checker_rejects_stale_active_a1b_wording(
    tmp_path: Path, stale: str, expected: str
) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(_valid_ledger().replace("Status: Closed.", stale), encoding="utf-8")

    errors = _errors(tmp_path)

    assert any(expected in error for error in errors)


def test_checker_requires_pr1466_evidence_in_active_docs(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(_valid_roadmap().replace("PR #1466", "PR #9999"), encoding="utf-8")
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(_valid_ledger().replace("PR #1466", "PR #9999"), encoding="utf-8")

    errors = _errors(tmp_path)

    assert any("PR #1466" in error for error in errors)


def test_checker_rejects_semantic_cache_gate_open_marker(tmp_path: Path) -> None:
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


def test_checker_rejects_semantic_cache_gate_overclaim_even_when_markers_closed(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    gate = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate.write_text(
        _valid_gate() + "\nPR-A1b opens semantic-cache serving for Redis.\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("semantic-cache gate" in error and "semantic-cache" in error for error in errors)


@pytest.mark.parametrize(
    ("claim", "expected"),
    [
        ("A1b does not reopen runtime, but implements quota enforcement.", "runtime-scope"),
        ("PR-A1b changes provider/auth/billing behavior.", "runtime-scope"),
        ("Semantic cache remains closed, but Redis is approved.", "semantic-cache"),
        (
            "Semantic cache remains closed and Redis is approved for production-ready rollout.",
            "semantic-cache",
        ),
        ("Semantic cache remains closed plus GPTCache is enabled.", "semantic-cache"),
        ("A1b opens semantic-cache serving.", "semantic-cache"),
        (
            "PR-A1b does not reopen runtime quota logic despite changing provider/auth/billing behavior.",
            "runtime-scope",
        ),
    ],
)
def test_checker_rejects_runtime_or_semantic_cache_contrast_bypass(
    tmp_path: Path, claim: str, expected: str
) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace("#### Out of scope", f"{claim}\n\n#### Out of scope"),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any(expected in error for error in errors)


def test_checker_rejects_forbidden_claim_in_pr1461_post_merge_mapping(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "## Historical Merge Readiness",
            "Evidence: PR-A1b opens semantic-cache serving for Redis.\n\n## Historical Merge Readiness",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("PR_1461_FIXED_MAPPING" in error and "semantic-cache" in error for error in errors)


def test_checker_rejects_forbidden_claim_anywhere_in_pr1461_mapping(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1461#discussion_r1 -> abc123",
            "- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1461#discussion_r1 -> abc123\n"
            "Evidence: PR-A1b opens semantic-cache serving for Redis.",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("PR_1461_FIXED_MAPPING" in error and "semantic-cache" in error for error in errors)


def test_checker_rejects_local_path_leakage_in_mapping(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nEvidence: /Users/example/worktrees/a1b\n", encoding="utf-8"
    )

    errors = _errors(tmp_path)

    assert any("local artifact/worktree path" in error for error in errors)


def test_checker_rejects_unix_absolute_worktree_path_leakage(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(_valid_mapping() + "\nEvidence: /tmp/worktrees/a1b/foo\n", encoding="utf-8")

    errors = _errors(tmp_path)

    assert any("local artifact/worktree path" in error for error in errors)


def test_current_pr_mapping_uses_only_phase2_safe_artifact_path() -> None:
    mapping = (REPO_ROOT / "docs/review/PR_1817_FIXED_MAPPING.md").read_text(encoding="utf-8")

    assert "/Users/" not in mapping
    assert "worktrees/" not in mapping
    assert (
        "Artifact: `artifacts/orchestration/experiments/results/exp-236fcd2ee840.json`" in mapping
    )


def test_checker_rejects_stale_mapping_readiness_checklist(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\n## Merge Readiness\n\n- [ ] Current-head CI is green\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("Merge Readiness" in error or "unchecked" in error for error in errors)


def test_checker_rejects_stale_mapping_readiness_heading_at_any_level(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\n### Merge Readiness\n\n- [x] Current-head CI is green\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("Merge Readiness" in error for error in errors)


def test_checker_rejects_stale_mapping_readiness_heading_case_variant(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\n### merge readiness\n\n- [x] Current-head CI is green\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("Merge Readiness" in error for error in errors)


def test_checker_rejects_stale_mapping_readiness_setext_heading(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1461_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nMerge Readiness\n---\n\n- [x] Current-head CI is green\n",
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("Merge Readiness" in error for error in errors)


def test_checker_rejects_runtime_expansion_without_explicit_a1b_token(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap().replace(
            "#### Out of scope",
            "Closeout review: This closeout changes provider/auth/billing behavior.\n\n"
            "#### Out of scope",
        ),
        encoding="utf-8",
    )

    errors = _errors(tmp_path)

    assert any("runtime-scope expansion" in error for error in errors)


def test_checker_rejects_missing_landed_runtime_marker(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    source = tmp_path / "app/services/fitchef_runtime.py"
    source.write_text("attempt_consume_llm_monthly_quota(api_key)\n", encoding="utf-8")

    errors = _errors(tmp_path)

    assert any("tier=effective_tier" in error for error in errors)
