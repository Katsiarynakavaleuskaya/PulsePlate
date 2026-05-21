# PR #1787 Fixed Mapping

## Summary

Closeout/reconciliation PR for PR-A7 recursive methods W1. This PR records
that PR #1499 already merged on `2026-04-23T01:37:29Z` with merge commit
`1e7166e55c54448c0d6475338e1b9984efd0caf1` from branch
`codex/ai-recursive-methods-w1`.

## Scope Boundary

- Closeout only: reconcile ledger, roadmap, historical review mapping, and
  machine-checkable guard evidence.
- No runtime reimplementation.
- No semantic-cache gate opening.
- No Redis/GPTCache approval.
- No GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO,
  provider-side chain/tree-of-thought, or recursive-learning rollout.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: `docs/review/PR_1787_FIXED_MAPPING.md` now has required discussion-thread checkboxes; `scripts/ci/check_ai_recursive_methods_w1_closeout.py` expands landed-scope forbidden surfaces, comma negation breaks, raw-cache newline normalization, stale active-state checks, and historical-readiness checkbox checks; `tests/test_ai_recursive_methods_w1_closeout.py` covers the regressions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280833326 -> b4809f7e3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280856839 -> a8f18ade4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280856849 -> a8f18ade4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280856855 -> a8f18ade4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280919726 -> 2d1f43929
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280919738 -> 2d1f43929
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280919743 -> 2d1f43929
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280919750 -> 2d1f43929
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1787#discussion_r3280919753 -> 2d1f43929

## Commit Evidence

- Initial implementation: `384f26d7f`
  - Evidence: ledger/roadmap/PR #1499 mapping reconciliation plus the
    stdlib-only checker and regression tests.
- Post-open governance mapping: `ffa6269a6`
  - Evidence: adds this PR-numbered mapping artifact.
- QA Phase 2 mirror and size-governance fix: `b4809f7e3`
  - Evidence: this update changes the canonical heading to
    `## Fixed in Commit Mapping`, adds required discussion-thread checkboxes,
    and the PR body includes `## Split Justification`.
- Bug-hunter guard false-negative fix: `a8f18ade4`
  - Evidence: expands landed-scope forbidden surfaces and rejects comma-separated
    non-binding negation before forbidden positive claims.
- Security-auditor guard false-negative fix: `2d1f43929`
  - Evidence: closes raw-cache newline, `without` negation, stale active-state,
    broader forbidden-surface, and checked local-readiness false negatives.

## Premortem Findings

- FIXED: duplicate implementation risk. Evidence: no runtime files changed; the
  checker only requires landed runtime evidence files to exist.
- FIXED: semantic-cache activation ambiguity. Evidence: closeout checker plus
  `check_semantic_cache_gate.py` require closed gate markers.
- FIXED: Redis/GPTCache/backend approval ambiguity. Evidence: checker rejects
  positive backend approval/rollout claims.
- FIXED: stale historical readiness boxes. Evidence: PR #1499 mapping now marks
  readiness proof as historical only.
- FIXED: false-green guard bypasses found pre-open. Evidence: tests cover mixed
  negation, passive voice, database/vector database variants, raw data cache
  permissions, and dynamic-import policy compliance.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-4f6ef486326a.json`
- Result: accepted.
- Oracles: A7 closeout checker, semantic-cache gate checker, focused A7
  closeout pytest.
- Attribution: `coauthor_required=false`; no Experiment Runner co-author trailer
  because the oracle result did not materially change committed content.

## Tests And Bounded Checks

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/ci/check_ai_recursive_methods_w1_closeout.py`
- `python3 scripts/ci/check_semantic_cache_gate.py`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/review/PR_1499_FIXED_MAPPING.md`
- `python -m pytest -q tests/test_ai_recursive_methods_w1_closeout.py tests/test_recursive_rag.py tests/test_rag_orchestration.py tests/test_insight_rag_response_fields.py tests/test_core_ai_insight_runtime.py tests/test_insight_application_service.py tests/test_semantic_cache_gate.py tests/test_repo_policy_guards.py`
- `python -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_ai_recursive_methods_w1_closeout.py tests/test_ai_recursive_methods_w1_closeout.py`
- `make validate-changed`
- `pre-commit run --all-files`
- Pre-push hooks passed on push to `codex/ai-recursive-methods-w1-closeout`.

Full `make verify` is intentionally deferred under the operator-approved
machine-budget policy; this is not a merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open QA, bug-hunter, CodeRabbit/Codex connector, and security-auditor
findings are mapped in this artifact as FIXED. Any Sourcery, Cubic, or Codex
Security finding will be mapped here as FIXED, NOT-A-BUG, or DEFERRED with
evidence before resolution.

## Merge Readiness

Not claimed. Requires current-head CI, bot no-actionable state, review-thread
disposition checks, strict merge-readiness wrapper with auth, and final
wait-window.
