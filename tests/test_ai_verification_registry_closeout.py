from __future__ import annotations

from pathlib import Path

import pytest

import scripts.ci.check_ai_verification_registry_closeout as closeout

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_ledger() -> str:
    return f"""# Backlog

<a id="ledger-p1-verification-registry-admission"></a>
- [x] P1: Verification registry and verify-before-write admission invariant
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-V1
  - Status: Closed via PR #{closeout.PR_NUMBER} on {closeout.MERGE_DATE}; merged commit `{closeout.MERGE_COMMIT}` from `{closeout.ORIGINAL_BRANCH}`.
  - Area: AI runtime / verification / knowledge admission
  - Finding Type: verification-bundle admission closeout
  - Reason (EN): PR-V1 is landed and reconciled. `main` has the bounded K1 knowledge seam, deterministic recursive verification diagnostics, philosophical runtime verification/falsification signals, and one canonical verification bundle for verify-before-write admission.
  - Delayed closeout: PR #{closeout.PR_NUMBER} merged before this ledger block was reconciled; this follow-up records repo/GitHub truth and does not duplicate implementation.
  - Links:
    - `docs/orchestration/WAVE6_V1_VERIFICATION_REGISTRY_PACKET_2026-04-21.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `core/verification/`
  - DoD:
    - `core/verification/*` exists as the canonical internal artifact/bundle registry
    - Existing recursive and philosophical verification signals are reused
    - Knowledge writes require an admissible verification bundle
    - Public routes, OpenAPI, response DTOs, and storage rollout remain unchanged
    - semantic cache, Redis/GPTCache, GraphRAG, and ContextManifest remain out of scope

<a id="next"></a>
- [ ] Next item
"""


def _valid_roadmap() -> str:
    return f"""# RAG roadmap

## PR-V1 — verification registry and verify-before-write admission
#### Title
`feat(ai-quality): add verification registry and verify-before-write admission invariant`

#### Status
Landed via PR #{closeout.PR_NUMBER} on {closeout.MERGE_DATE} with merge commit `{closeout.MERGE_COMMIT}`. This closeout reconciles stale roadmap/backlog/review truth.
No `core/verification/*` reimplementation is in scope.

#### Backlog target
`ledger-p1-verification-registry-admission`

#### Goal
Record the landed K1 knowledge seam hardening and keep later runtime/cache work pointed at the merged verification bundle.

#### In scope
- landed `core/verification/*` internal contracts, policy, and registry assembly evidence
- reuse of existing recursive verification diagnostics and philosophical runtime verification/falsification signals
- internal-only verification bundle threading through RAG/runtime/application seams
- verify-before-write admission for knowledge promotion only

#### Out of scope
- semantic cache implementation or gate opening
- cache/action runtime enablement
- DB persistence for verification artifacts
- route / OpenAPI / public response shape changes
- GraphRAG, Redis/GPTCache, or ContextManifest work

#### DoD
- write admission requires a passed canonical verification bundle
- degraded paths remain safe

---
"""


def _valid_mapping() -> str:
    return f"""# PR #{closeout.PR_NUMBER} mapping

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120227129 -> bc3f17550
Disposition: FIXED

## Post-Merge Closeout

- State: `MERGED`
- PR #{closeout.PR_NUMBER} merged at `{closeout.MERGE_TIMESTAMP}`
- Merge commit: `{closeout.MERGE_COMMIT}`
- Original branch: `{closeout.ORIGINAL_BRANCH}`
- Closeout scope: PR-V1 is not re-opened and implementation is not duplicated.
- Boundary: semantic-cache gate remained closed.
"""


def _valid_gate() -> str:
    return """# PulsePlate Semantic Cache Gate and Plan

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->
"""


def _write_valid_repo(tmp_path: Path) -> None:
    for relpath in closeout.REQUIRED_CORE_FILES:
        _write(tmp_path / relpath, "# exists\n")
    _write(tmp_path / "docs/roadmap/BACKLOG_LEDGER.md", _valid_ledger())
    _write(
        tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md",
        _valid_roadmap(),
    )
    _write(tmp_path / "docs/review/PR_1491_FIXED_MAPPING.md", _valid_mapping())
    _write(
        tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        _valid_gate(),
    )


def test_checker_passes_on_current_repository() -> None:
    assert closeout.validate_closeout(repo_root=REPO_ROOT) == []


def test_checker_passes_on_valid_minimal_fixture(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)

    assert closeout.validate_closeout(repo_root=tmp_path) == []


def test_checker_rejects_stale_active_ledger_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "PR-V1 is landed and reconciled.",
            "PR-V1 is landed and reconciled. write admission still lacks one first-class verification bundle.",
        ),
        encoding="utf-8",
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("stale missing verification-bundle claim" in error for error in errors)


def test_checker_rejects_structural_stale_bundle_claim_variant(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    ledger = tmp_path / "docs/roadmap/BACKLOG_LEDGER.md"
    ledger.write_text(
        _valid_ledger().replace(
            "PR-V1 is landed and reconciled.",
            "PR-V1 is landed and reconciled. Write admission still lacks a canonical "
            "verification bundle.",
        ),
        encoding="utf-8",
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("stale missing verification-bundle claim" in error for error in errors)


def test_checker_rejects_semantic_cache_gate_open_marker(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    gate = tmp_path / "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate.write_text(
        _valid_gate().replace(
            "SEMANTIC_CACHE_GATE_STATUS: closed", "SEMANTIC_CACHE_GATE_STATUS: open"
        ),
        encoding="utf-8",
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("SEMANTIC_CACHE_GATE_STATUS" in error for error in errors)


def test_checker_rejects_pr_v1_semantic_cache_open_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap() + "\nPR-V1 opens semantic-cache serving.\n", encoding="utf-8"
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("PR-V1 opens semantic cache" in error for error in errors)


@pytest.mark.parametrize(
    ("claim", "expected"),
    [
        ("PR-V1 can cache raw prompts safely.", "raw prompts cacheable"),
        (
            "PR-V1 can cache deterministic, bounded, review-mapped, provenance-only, "
            "operator-approved, replay-safe, non-runtime metadata around raw prompts safely.",
            "raw prompts cacheable",
        ),
        ("PR-V1 allows caching raw prompts safely.", "raw prompts cacheable"),
        ("PR-V1 can cache raw responses safely.", "raw responses cacheable"),
        ("PR-V1 allows caching raw responses safely.", "raw responses cacheable"),
        ("PR-V1 can cache raw sensitive data safely.", "raw sensitive data cacheable"),
        ("PR-V1 allows caching raw sensitive data safely.", "raw sensitive data cacheable"),
        ("Raw sensitive data is cacheable under PR-V1.", "raw sensitive data cacheable"),
        ("PR-V1 can cache raw account data safely.", "raw sensitive data cacheable"),
        ("PR-V1 allows caching raw account data safely.", "raw sensitive data cacheable"),
        ("PR-V1 can cache raw secrets safely.", "raw sensitive data cacheable"),
        ("PR-V1 allows caching raw secrets safely.", "raw sensitive data cacheable"),
        ("PR-V1 can cache raw credentials safely.", "raw sensitive data cacheable"),
        ("PR-V1 allows caching raw credentials safely.", "raw sensitive data cacheable"),
        ("PR-V1 can cache raw tokens safely.", "raw sensitive data cacheable"),
        ("PR-V1 allows caching raw tokens safely.", "raw sensitive data cacheable"),
        ("PR-V1 can cache raw PII safely.", "raw sensitive data cacheable"),
        ("PR-V1 allows caching raw PII safely.", "raw sensitive data cacheable"),
        ("PR-V1 approves Redis for semantic-cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("PR V1 approves Redis for semantic-cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("PR‑V1 approves Redis for semantic-cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("PR-V1 permits Redis for semantic-cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("PR-V1 allows GPTCache for semantic-cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("GPT Cache is approved for semantic-cache rollout.", "Redis/GPTCache"),
        ("GPT-Cache is approved for semantic-cache rollout.", "Redis/GPTCache"),
        ("PR-V1 grants permission for Redis rollout.", "PR-V1 approves Redis/GPTCache"),
        ("Redis has PR-V1 approval for rollout.", "Redis/GPTCache rollout approval"),
        ("PR-V1 permits semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR V1 permits semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 allows semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 approves semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 authorizes semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 selects semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 grants permission for semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 grants authorization for semantic-cache serving.", "PR-V1 approves semantic cache"),
        ("PR-V1 makes semantic-cache production ready.", "semantic cache"),
        ("PR-V1 opens\nsemantic-cache serving.", "PR-V1 opens semantic cache"),
        ("PR V1 opens semantic-cache serving.", "PR-V1 opens semantic cache"),
        ("PR-V1 opened semantic-cache serving.", "PR-V1 opens semantic cache"),
        ("PR-V1 enabled semantic-cache serving.", "PR-V1 enables semantic cache"),
        ("PR-V1 opens semantic‑cache serving.", "PR-V1 opens semantic cache"),
        ("PR-V1 opens semantic\ncache serving.", "PR-V1 opens semantic cache"),
        ("PR-\nV1 opens semantic-cache serving.", "PR-V1 opens semantic cache"),
        ("PR-V1 opens semantic\xa0cache serving.", "PR-V1 opens semantic cache"),
        ("Semantic-cache serving is permitted by PR-V1.", "semantic cache"),
        ("Semantic-cache serving has PR-V1 permission.", "semantic cache"),
        ("Semantic-cache serving is selected by PR-V1.", "semantic cache"),
        ("Semantic-cache serving has PR-V1 selection.", "semantic cache"),
        ("Semantic-cache serving is authorized by PR-V1.", "semantic cache"),
        ("Semantic-cache serving has PR-V1 authorization.", "semantic cache"),
        ("Semantic-cache serving was opened by PR-V1.", "semantic cache"),
        ("Redis is not only approved for semantic-cache rollout.", "Redis/GPTCache"),
        ("PR-V1 authorizes Redis for semantic-cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("Redis is authorized for semantic-cache rollout.", "Redis/GPTCache"),
        ("PR-V1 grants authorization for GPT Cache rollout.", "PR-V1 approves Redis/GPTCache"),
        ("PR-V1 can cache raw user prompts safely.", "raw prompts cacheable"),
        ("PR-V1 can cache raw LLM prompts safely.", "raw prompts cacheable"),
        ("PR-V1 can cache raw user responses safely.", "raw responses cacheable"),
    ],
)
def test_checker_rejects_forbidden_claim_variants(
    tmp_path: Path, claim: str, expected: str
) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(_valid_roadmap() + f"\n{claim}\n", encoding="utf-8")

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any(expected in error for error in errors)


def test_checker_allows_negated_gate_closed_policy_claims(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(
        _valid_roadmap()
        + "\nSemantic-cache serving is not production-ready.\n"
        + "Semantic-cache serving is not selected by PR-V1.\n"
        + "Semantic-cache serving is not authorized by PR-V1.\n"
        + "PR-V1 does not permit Redis for semantic-cache rollout.\n"
        + "PR-V1 does not authorize Redis for semantic-cache rollout.\n"
        + "PR-V1 does not permit semantic-cache serving.\n"
        + "PR V1 does not permit semantic-cache serving.\n"
        + "Semantic-cache has no approval for serving rollout.\n"
        + "Semantic-cache lacks approval for serving rollout.\n"
        + "PR-V1 is not a semantic-cache rollout or backend-selection approval.\n"
        + "Redis is not approved for semantic-cache rollout.\n"
        + "Redis lacks approval for semantic-cache rollout.\n"
        + "Semantic-cache is without approval for serving rollout.\n"
        + "GPTCache has no permission for semantic-cache rollout.\n"
        + "GPT Cache lacks approval for semantic-cache rollout.\n"
        + "PR-V1 does not permit Redis, and it does not permit semantic-cache serving.\n"
        + "PR-V1 does not permit Redis or semantic-cache serving.\n"
        + "Raw prompts are not cacheable.\n"
        + "Raw user prompts are not cacheable.\n"
        + "PR-V1 does not cache raw prompts.\n"
        + "PR-V1 does not cache raw LLM prompts.\n"
        + "Raw prompts cannot be cached.\n"
        + "Raw responses are never cached.\n"
        + "Raw prompts are prohibited from being cached.\n"
        + "Raw sensitive data is not cacheable.\n"
        + "Raw account data is not cacheable.\n",
        encoding="utf-8",
    )

    assert closeout.validate_closeout(repo_root=tmp_path) == []


@pytest.mark.parametrize(
    ("claim", "expected"),
    [
        (
            "No review item remains. PR-V1 opens semantic-cache serving.",
            "PR-V1 opens semantic cache",
        ),
        (
            "PR-V1 does not change routes but opens semantic-cache serving.",
            "PR-V1 opens semantic cache",
        ),
        (
            "Semantic-cache is not production-ready but PR-V1 opens semantic-cache serving.",
            "PR-V1 opens semantic cache",
        ),
        (
            "PR-V1 does not permit Redis for semantic-cache rollout and allows semantic-cache serving.",
            "semantic cache serving approval verb",
        ),
        (
            "Although PR-V1 does not permit Redis rollout, PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout because PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout while PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout since PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout if PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout despite PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout or PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout or PR-V1 allows semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout or permits semantic-cache serving.",
            "semantic cache serving approval verb",
        ),
        (
            "PR-V1 does not permit Redis rollout; PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout: PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout - PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout (PR-V1 approves semantic-cache serving).",
            "PR-V1 approves semantic cache",
        ),
        (
            "PR-V1 does not permit Redis rollout—PR-V1 approves semantic-cache serving.",
            "PR-V1 approves semantic cache",
        ),
        (
            "No stale finding left here. PR-V1 can cache raw account data safely.",
            "raw sensitive data cacheable",
        ),
        (
            "Raw prompts are not cacheable. PR-V1 can cache raw prompts safely.",
            "raw prompts cacheable",
        ),
    ],
)
def test_checker_rejects_forbidden_claims_after_unrelated_negated_text(
    tmp_path: Path, claim: str, expected: str
) -> None:
    _write_valid_repo(tmp_path)
    roadmap = tmp_path / "docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    roadmap.write_text(_valid_roadmap() + f"\n{claim}\n", encoding="utf-8")

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any(expected in error for error in errors)


def test_checker_allows_historical_stale_pr1491_text_outside_closeout(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1491_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping().replace(
            "## Post-Merge Closeout",
            "## Historical Review Evidence\n"
            "Evidence: current head needs one final current-head CI pass.\n\n"
            "## Post-Merge Closeout",
        ),
        encoding="utf-8",
    )

    assert closeout.validate_closeout(repo_root=tmp_path) == []


def test_checker_rejects_stale_pr1491_mapping_readiness_claim(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1491_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nEvidence: current head needs one final current-head CI pass.\n",
        encoding="utf-8",
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("pending final current-head CI claim" in error for error in errors)


def test_checker_rejects_stale_pr1491_mapping_readiness_claim_case_insensitive(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1491_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nEvidence: Current head needs one final current-head CI pass.\n",
        encoding="utf-8",
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("pending final current-head CI claim" in error for error in errors)


def test_checker_rejects_stale_pr1491_mapping_readiness_claim_wrapped(
    tmp_path: Path,
) -> None:
    _write_valid_repo(tmp_path)
    mapping = tmp_path / "docs/review/PR_1491_FIXED_MAPPING.md"
    mapping.write_text(
        _valid_mapping() + "\nEvidence: current head needs one final\ncurrent-head CI pass.\n",
        encoding="utf-8",
    )

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("pending final current-head CI claim" in error for error in errors)


def test_checker_rejects_missing_verification_registry_file(tmp_path: Path) -> None:
    _write_valid_repo(tmp_path)
    (tmp_path / "core/verification/registry.py").unlink()

    errors = closeout.validate_closeout(repo_root=tmp_path)

    assert any("core/verification/registry.py" in error for error in errors)
