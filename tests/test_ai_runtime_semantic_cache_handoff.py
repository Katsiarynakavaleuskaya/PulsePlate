from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/ci/check_ai_runtime_semantic_cache_handoff.py"

A4_SHA = "831d62d8be0da7307e5a0f2673d8c33dbf53ca49"  # pragma: allowlist secret
A5_SHA = "2f8a9af461cec483aa81a774cce7496c6bf65a8a"  # pragma: allowlist secret
SC_G5_SHA = "cb1db8b40141817b3ca856de570b8fc02e2ae9fa"  # pragma: allowlist secret


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_ledger() -> str:
    return f"""# Backlog

<a id="ledger-p1-ai-bounded-context-extraction"></a>
- [x] P1: Extract AI runtime into a dedicated bounded context
  - Target PR: PR-A4 / PR #1203
  - Status: Closed. PR #1203 `feat(ai): extract bounded AI runtime ownership into canonical core/ai seam` merged on `2026-03-21T06:01:31Z` with merge commit `{A4_SHA}` from branch `feat/ai-bounded-context-extraction`.
  - DoD:
    - Semantic-cache markers remain `closed / false / false / true`.

<a id="ledger-p1-llm-reliability-security-gates"></a>
- [x] P1: LLM reliability and security CI gates for retrieval, faithfulness, prompt-injection, and privacy
  - Target PR: PR-A5 / PR #1395
  - Status: Closed. PR #1395 `feat(ai): add PR-A5 runtime gates` merged on `2026-04-12T11:45:35Z` with merge commit `{A5_SHA}` from branch `feat/pr-a5-runtime-gates`.
  - DoD:
    - Semantic-cache markers remain `closed / false / false / true`.
"""


def _valid_rag_roadmap() -> str:
    return f"""# RAG Roadmap

The runtime prerequisite train is closed, but a later reviewed gate-open PR must
still change semantic-cache machine markers before runtime semantic-cache work
can begin.

## PR-A4 - bounded-context extraction

Landed via PR #1203 `feat(ai): extract bounded AI runtime ownership into
canonical core/ai seam` on `2026-03-21T06:01:31Z` with merge commit `{A4_SHA}`
from branch `feat/ai-bounded-context-extraction`.

## PR-A5 - LLM reliability/security gates

Landed via PR #1395 `feat(ai): add PR-A5 runtime gates` on
`2026-04-12T11:45:35Z` with merge commit `{A5_SHA}` from branch
`feat/pr-a5-runtime-gates`.
"""


def _valid_gate() -> str:
    return f"""# Semantic Cache Gate

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->

The runtime prerequisite train is closed.

PR #1203 `feat(ai): extract bounded AI runtime ownership into canonical core/ai
seam` merged `2026-03-21T06:01:31Z` with merge commit `{A4_SHA}` from branch
`feat/ai-bounded-context-extraction`.

PR #1395 `feat(ai): add PR-A5 runtime gates` merged `2026-04-12T11:45:35Z`
with merge commit `{A5_SHA}` from branch `feat/pr-a5-runtime-gates`.

PR #1742 `feat(ai-runtime): add semantic-cache backend selection contract`
merged `2026-05-16T21:03:48Z` with merge commit `{SC_G5_SHA}`.

Runtime semantic-cache serving remains blocked until a later reviewed gate-open
PR changes the machine markers.
"""


def _valid_report() -> str:
    report = {
        "report_version": "2026-05-25",
        "rollout_phase": "PHILOSOPHY-PR4-SC0-RECONCILED",
        "gate_open_allowed": False,
        "runtime_handoff_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
        "preconditions": [
            {
                "id": "pr_a1b_reconciled",
                "status": "merge_verified_closed",
                "blocks_gate_open": False,
                "evidence": "PR #1461 and PR #1466",
            },
            {
                "id": "pr_a2_rag_hardening_closed",
                "status": "merge_verified_closed",
                "blocks_gate_open": False,
                "evidence": "PR #1415",
            },
            {
                "id": "pr_a3_bounded_context_packet_closed",
                "status": "merge_verified_closed",
                "blocks_gate_open": False,
                "evidence": "PR #1469",
            },
            {
                "id": "pr_a4_bounded_context_extraction_closed",
                "status": "merge_verified_closed",
                "blocks_gate_open": False,
                "evidence": (
                    "PR #1203 `feat(ai): extract bounded AI runtime ownership "
                    "into canonical core/ai seam` merged 2026-03-21T06:01:31Z "
                    f"with merge commit {A4_SHA} from branch "
                    "feat/ai-bounded-context-extraction"
                ),
            },
            {
                "id": "pr_a5_llm_reliability_security_closed",
                "status": "merge_verified_closed",
                "blocks_gate_open": False,
                "evidence": (
                    "PR #1395 `feat(ai): add PR-A5 runtime gates` merged "
                    f"2026-04-12T11:45:35Z with merge commit {A5_SHA} from "
                    "branch feat/pr-a5-runtime-gates"
                ),
            },
            {
                "id": "dedicated_gate_open_pr_changes_markers",
                "status": "absent",
                "blocks_gate_open": True,
                "evidence": "PR #1837 reconciles prerequisites but no gate-open PR has changed markers",
            },
            {
                "id": "pr1789_alignment_rule_schema_landed",
                "status": "source_present_not_merge_verified",
                "blocks_gate_open": True,
                "evidence": "PR-1789 alignment-rule trust schema is present but merge-verified proof pending",
            },
        ],
        "handoff_decision": {
            "reason_codes": [
                "semantic_cache_gate_closed",
                "dedicated_gate_open_pr_absent",
                "alignment_rule_schema_predecessor_pending",
            ],
            "blocking_precondition_count": 2,
            "runtime_handoff_allowed": False,
            "cache_read_allowed": False,
            "cache_write_allowed": False,
            "serving_allowed": False,
        },
    }
    return json.dumps(report, indent=2) + "\n"


def _write_valid_repo(repo: Path) -> None:
    _write(repo / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(repo / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md", _valid_rag_roadmap())
    _write(repo / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md", _valid_gate())
    _write(
        repo / "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        _valid_report(),
    )
    _write(
        repo / "scripts/ci/check_philosophy_gate_open_preconditions.py",
        'STATUS = "merge_verified_closed"\nPHASE = "PHILOSOPHY-PR4-SC0-RECONCILED"\n',
    )


def _checker_args(repo: Path) -> list[str]:
    return [
        sys.executable,
        str(CHECKER),
        "--repo-root",
        str(repo),
        "--ledger",
        str(repo / "docs/roadmap/BACKLOG_LEDGER.md"),
        "--rag-roadmap",
        str(repo / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"),
        "--semantic-gate",
        str(repo / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"),
        "--preconditions-report",
        str(repo / "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"),
        "--preconditions-checker",
        str(repo / "scripts/ci/check_philosophy_gate_open_preconditions.py"),
    ]


def _errors(repo: Path) -> str:
    result = subprocess.run(_checker_args(repo), text=True, capture_output=True, check=False)
    return result.stderr


def test_checker_passes_on_current_repository() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER)], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "semantic-cache runtime prerequisite handoff guard passed" in result.stdout


def test_checker_passes_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    result = subprocess.run(_checker_args(tmp_path), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_checker_rejects_stale_runtime_sequence_wording(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text() + "\nThe runtime sequence still requires PR-A4 through PR-A5.\n",
        encoding="utf-8",
    )
    assert "stale wording remains" in _errors(tmp_path)


def test_checker_rejects_forbidden_satisfied_phrase(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nSemantic cache prerequisites are satisfied.\n",
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_rejects_live_but_blocked_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nSemantic cache is live but blocked.\n",
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" in _errors(tmp_path)


def test_checker_allows_negated_live_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text() + "\nSemantic cache is not live and stays blocked.\n",
        encoding="utf-8",
    )
    assert "forbidden runtime/scope expansion claim" not in _errors(tmp_path)


def test_checker_rejects_open_gate_marker(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    path.write_text(
        path.read_text().replace(
            "SEMANTIC_CACHE_GATE_STATUS: closed",
            "SEMANTIC_CACHE_GATE_STATUS: open",
        ),
        encoding="utf-8",
    )
    assert "expected SEMANTIC_CACHE_GATE_STATUS=closed" in _errors(tmp_path)


def test_checker_rejects_runtime_precondition_reopening(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["preconditions"][3]["status"] = "not_verified_by_pr4"
    report["preconditions"][3]["blocks_gate_open"] = True
    report["handoff_decision"]["reason_codes"].append("runtime_prerequisites_not_verified")
    report["handoff_decision"]["blocking_precondition_count"] = 3
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    assert "must be merge_verified_closed" in _errors(tmp_path)


def test_checker_rejects_missing_blocking_precondition_evidence_for_reason_code(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["preconditions"] = [
        item
        for item in report["preconditions"]
        if item.get("id") != "dedicated_gate_open_pr_changes_markers"
    ]
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    assert "missing blocker precondition for reason code dedicated_gate_open_pr_absent" in _errors(
        tmp_path
    )


def test_checker_rejects_repo_root_only_when_invalid_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    path.write_text(
        path.read_text() + "\nThe runtime sequence still requires PR-A4 through PR-A5.\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "active docs: stale wording remains (A4/A5 still required)" in result.stderr


def test_checker_rejects_review_fix_sha_as_merge_proof(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    path = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    path.write_text(path.read_text() + "\nMerge proof: 8d5f7e7bb.\n", encoding="utf-8")
    assert "review-fix SHA must not be used as merge proof" in _errors(tmp_path)


def test_checker_uses_stdlib_only() -> None:
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert imports <= {"__future__", "argparse", "json", "pathlib", "re", "sys"}
