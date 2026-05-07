# PR #1697 Fixed Mapping

## Summary

SC-G1 defines the semantic-cache rollout gate contract while keeping the PR #1687 gate markers closed.

## Goal

Make the future semantic-cache gate-opening path explicit, deterministic, and machine-checkable before any runtime/cache/provider/RAG implementation PR can start.

## Business reason

This PR protects PulsePlate from premature semantic-cache rollout, stale or false-positive AI responses, advisory wiki leakage into product truth, and expensive runtime/provider mistakes.

## Scope

- Added `docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md`.
- Added `docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.schema.json`.
- Extended `scripts/ci/check_semantic_cache_gate.py` to validate the rollout contract by default.
- Extended Docs Phase1 semantic-cache validation to include the rollout contract.
- Added deterministic tests for gate-closed markers, dangerous wording, rollout phases, schema keys, blocked surfaces, and import boundaries.
- Updated semantic-cache roadmap/backlog wording narrowly.

## Out of scope

No changes to:

- Semantic cache implementation, Redis, GPTCache, embeddings, or vector search.
- `/insight` runtime cache, provider behavior, or RAG behavior.
- FastAPI routes, OpenAPI, or DB migrations.
- Frontend, iOS, or design files.
- GraphRAG or advisory wiki runtime authority.
- Online eval, judge calibration, goldens, or dashboards.
- Release-control-plane behavior.

## Files touched

- `docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md`
- `docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.schema.json`
- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/ci/check_semantic_cache_gate.py`
- `scripts/ci/check_docs_phase1_gates.py`
- `tests/test_semantic_cache_gate.py`
- `tests/test_semantic_cache_rollout_gate.py`
- `tests/test_docs_phase1_gates.py`

## Tests

Passed locally on current branch before PR open:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `.venv/bin/python scripts/ci/check_semantic_cache_gate.py`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md`
- `.venv/bin/python -m pytest -q tests/test_semantic_cache_gate.py tests/test_semantic_cache_rollout_gate.py tests/test_docs_phase1_gates.py tests/test_repo_policy_guards.py`
- `.venv/bin/python -m mypy --explicit-package-bases --no-incremental --cache-dir=/dev/null scripts/ci/check_semantic_cache_gate.py scripts/ci/check_docs_phase1_gates.py tests/test_semantic_cache_gate.py tests/test_semantic_cache_rollout_gate.py tests/test_docs_phase1_gates.py`
- `make validate-changed`
- `pre-commit run --all-files`
- Pre-push hooks: backend tests, full Bandit, docker build test

Full `make verify` was intentionally not run for this docs + deterministic guard PR; this uses the operator-approved bounded-gate path.

## Security notes

Semantic cache remains closed. The checker fails closed on dangerous wording that implies cache is active, implemented, enabled, open, approved, ready, or unlocked by Evidence Graph E1-E5. The rollout contract blocks advisory wiki product-cache authority, raw prompt/response/secret/user-health/account-truth caching, billing/auth/entitlement/legal/compliance/account surfaces, and runtime/provider/cache/RAG imports in checker tests.

## Premortem

- Accidental gate open: markers are unchanged and duplicate/unsafe markers fail tests.
- Contract read as implementation approval: contract and checker require explicit no-open/no-implementation language.
- Advisory wiki leakage into product cache: blocked in contract and dangerous wording tests.
- Jumping to embeddings/backend cache: SC-G2 exact/fuzzy scaffold is required before SC-G4 semantic experiment; Redis/GPTCache deferred to SC-G5.
- Missing false-hit model, observability, kill switch, rollback, admission, replay: each is required by checker/tests.
- Runtime/provider/cache/RAG imports: AST import guards cover checker/test boundaries.
- Checklist-only mitigation: all credible risks were converted into docs/checker/test changes before this artifact.

## Rollback / risks

Rollback is a docs/checker/test revert. Main risk is checker wording being too strict for future copy edits; tests keep phrase checks narrow and deterministic, and future gate-open PRs can intentionally update markers/checker with human approval.

## DoD

- Semantic-cache rollout gate contract exists.
- Gate remains closed; PR #1687 markers remain closed/false.
- SC-G1 through SC-G5 are documented and checked.
- Exact/fuzzy cache precedes semantic cache.
- Future `/insight` surface is bounded, feature-flagged, and off by default.
- False-hit risk model, observability, kill switch, rollback, blocked surfaces, Evidence Graph linkage, admission, and replay requirements are documented and tested.
- Schema/sample contract shape exists and is tested.
- No runtime/provider/RAG/cache files changed.

## Commit breakdown

- `fc63aded4` docs/checker/tests for SC-G1 semantic-cache rollout gate contract.
- `bab416651` adds the canonical PR #1697 fixed-mapping artifact.
- `9e1f1d962` aligns the mapping artifact with Phase2 parser gates.
- `e65ca8a16` fixes Sourcery review feedback by stabilizing forbidden-claim labels,
  switching rollout contract validation to regex anchors, and sharing the semantic-cache
  import guard helper.
- `4a1d07219` fixes Cubic review feedback by broadening raw prompt/response
  forbidden-claim detection and closing keyword-argument dynamic import bypasses.
- `71bd1dc85` fixes CodeRabbit review feedback by enforcing first-occurrence
  rollout phase ordering, closing direct/relative import guard bypasses, and
  improving fixed-mapping readability.
- `27ba93516` maps CodeRabbit feedback in the canonical fixed mapping artifact.
- `727cefbda` fixes CodeRabbit follow-up feedback by closing the
  `from package import submodule` semantic-cache import guard bypass.

## Pre-push checklist

- Coordinator-first bootstrap completed.
- Declared role order executed through custom orchestration agents.
- Required repo-native skills used as passive helpers: workflow, premortem, ledger, gates, guards, PR review.
- Bounded local validation passed.
- Pre-commit and pre-push hooks passed.

## Post-merge checklist

- Sync local main with fetch + ff-only merge.
- Confirm working tree clean.
- Do not start semantic-cache implementation automatically.
- Next PR must be explicitly selected by operator based on current repo truth.

## AGENTS.md updates

None. Existing semantic-cache and Evidence Graph invariants already cover this docs + guard PR.

## Deferred / Follow-ups

- SC-G2 exact/fuzzy cache scaffold remains future work and still must not add embeddings, Redis, or GPTCache.
- Semantic cache implementation remains blocked until a dedicated future gate-open PR changes the closed markers with approval.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open review lane bootstrap completed with packet `9442dc7099f0` for `qa-engineer-agent` and `bug-hunter`. Sourcery, Codex, Cubic, and CodeRabbit feedback were fixed or dispositioned and mapped below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#pullrequestreview-4239573839 -> e65ca8a16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197502775 -> e65ca8a16
Disposition: FIXED
Commit: e65ca8a16
Evidence: `scripts/ci/check_semantic_cache_gate.py:46`, `scripts/ci/check_semantic_cache_gate.py:101`, `tests/test_semantic_cache_gate.py:189`, `tests/helpers/semantic_cache_import_guard.py:23`; focused checker/tests/mypy/validate-changed passed locally after the fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#pullrequestreview-4239609396 -> 4a1d07219
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197509415 -> 4a1d07219
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197534582 -> 4a1d07219
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197534596 -> 4a1d07219
Disposition: FIXED
Commit: 4a1d07219
Evidence: `scripts/ci/check_semantic_cache_gate.py:90`, `scripts/ci/check_semantic_cache_gate.py:91`, `tests/test_semantic_cache_gate.py:244`, `tests/test_semantic_cache_gate.py:328`, `tests/helpers/semantic_cache_import_guard.py:60`; focused checker/tests/mypy/validate-changed passed locally after the fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#pullrequestreview-4239705867 -> 71bd1dc85
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197615815 -> 71bd1dc85
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197615841 -> 71bd1dc85
Disposition: FIXED
Commit: 71bd1dc85
Evidence: `scripts/ci/check_semantic_cache_gate.py:184`, `scripts/ci/check_semantic_cache_gate.py:217`, `tests/test_semantic_cache_gate.py:263`, `tests/helpers/semantic_cache_import_guard.py:23`, `docs/review/PR_1697_FIXED_MAPPING.md:24`; focused checker/tests/mypy/validate-changed passed locally after the fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197699569
Disposition: NOT-A-BUG
Evidence: PR #1697 is explicitly scoped as docs + deterministic guard/test, not docs-only; PR body includes `## Split Justification`, `pr_scope_guard` passed on current-head CI, and this artifact lists the executable checker/test scope in `Scope` and `Files touched`.
Reason: The comment applies a docs-only rule, but the operator-approved plan and PR body classify this lane as docs + deterministic guard/test. No runtime/cache/provider/RAG implementation files are touched.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#pullrequestreview-4239806990 -> 727cefbda
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1697#discussion_r3197699573 -> 727cefbda
Disposition: FIXED
Commit: 727cefbda
Evidence: `tests/helpers/semantic_cache_import_guard.py:33`, `tests/test_semantic_cache_gate.py:379`; focused checker/tests/mypy/validate-changed and pre-commit passed locally after the fix.

## Merge Readiness

Not merge-ready at artifact creation. Requires current-head CI, PR body gates, review-thread disposition mapping, CodeRabbit/Sourcery/Cubic no-actionables, and strict merge wrapper.
