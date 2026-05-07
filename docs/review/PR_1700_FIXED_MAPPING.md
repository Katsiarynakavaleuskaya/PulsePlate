# PR #1700 Fixed Mapping

## Summary

PR #1700 adds SC-G2 exact/fuzzy cache scaffold contracts while keeping the
semantic-cache gate closed.

## Goal

Define deterministic exact/fuzzy scaffold contracts, checker coverage, and
tests without runtime serving, `/insight` wiring, embeddings, Redis/GPTCache,
vector search, providers, DB, FastAPI, or OpenAPI changes.

## Business reason

This PR prevents future semantic-cache implementation from bypassing lexical
scaffold review, false-hit controls, lineage/admission/replay references, and
fail-closed gate governance.

## Scope

- Pure deterministic `core/ai/exact_fuzzy_cache.py`.
- SC-G2 contract doc and schema.
- Semantic-cache checker and docs Phase1 integration.
- Focused unit, contract, import, and determinism tests.

## Out of scope

Runtime cache serving, `/insight` wiring, semantic similarity, embeddings,
Redis, GPTCache, vector search, provider changes, DB migrations, FastAPI,
OpenAPI, frontend/iOS work, and advisory wiki product-cache authority.

## Files touched

- `core/ai/exact_fuzzy_cache.py`
- `core/ai/__init__.py`
- `docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md`
- `docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.schema.json`
- `docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md`
- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/ci/check_semantic_cache_gate.py`
- `scripts/ci/check_docs_phase1_gates.py`
- `tests/core/ai/test_exact_fuzzy_cache.py`
- `tests/test_semantic_cache_scaffold_contract.py`
- `tests/helpers/semantic_cache_import_guard.py`
- `tests/test_docs_phase1_gates.py`

## Tests

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `.venv/bin/python scripts/ci/check_semantic_cache_gate.py`
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- `.venv/bin/python -m pytest -q tests/core/ai/test_exact_fuzzy_cache.py tests/test_semantic_cache_scaffold_contract.py tests/test_semantic_cache_gate.py tests/test_semantic_cache_rollout_gate.py tests/test_docs_phase1_gates.py tests/test_repo_policy_guards.py`
- `.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null core/ai/exact_fuzzy_cache.py tests/core/ai/test_exact_fuzzy_cache.py scripts/ci/check_semantic_cache_gate.py scripts/ci/check_docs_phase1_gates.py`
- `make validate-changed`
- `pre-commit run --all-files`
- pre-push hooks

## Security notes

SC-G2 stores only derived keys, fingerprints, lineage IDs, policy/provider/model
keys, transparency notice IDs, and safety flags. It does not store raw prompts,
raw model responses, secrets, HealthKit payloads, account truth, entitlement
truth, legal/compliance truth, or runtime cache state.

## Premortem

| Failure mode | Mitigation | Evidence |
|---|---|---|
| Gate accidentally opens | Markers unchanged and checker requires closed state | `scripts/ci/check_semantic_cache_gate.py` |
| Embeddings/backend scope enters SC-G2 | Forbidden wording and import guards | `tests/test_semantic_cache_scaffold_contract.py` |
| Empty normalized query false-hit | Punctuation-only text fails closed | `tests/core/ai/test_exact_fuzzy_cache.py` |
| Cross-context/tier/source false-hit | Partition equality hard-miss tests | `tests/core/ai/test_exact_fuzzy_cache.py` |
| Runtime import creep | AST import/call guards | `tests/helpers/semantic_cache_import_guard.py` |

## Rollback / risks

Rollback is revert-only because this PR has no runtime state, DB migration, cache
backend, or serving path.

## DoD

- [ ] Semantic-cache gate remains closed.
- [ ] SC-G2 scaffold is pure and deterministic.
- [ ] Checker/docs Phase1 integration fails closed.
- [ ] Tests cover matching, hard misses, deterministic IDs/order, import guards,
  and dangerous wording.
- [ ] No runtime serving/provider/RAG/cache backend/DB wiring changed; only the
  internal SC-G2 scaffold module under `core/ai` was added.

## Commit breakdown

- `a4fce6daa` - `feat(ai-runtime): add exact fuzzy cache scaffold`
- `9ee894de5` - `fix(ai-runtime): harden exact fuzzy scaffold review guards`
- `0cddad988` - `fix(ai-runtime): remove duplicate scaffold phase error`
- `955e5a958` - `docs(review): update PR 1700 fixed mapping`
- `a4acaa035` - `fix(ai-runtime): address scaffold review cleanups`
- `9afa5d8e6` - `docs(review): map PR 1700 bot findings`
- `28802d950` - `fix(ai-runtime): tighten scaffold guard contracts`

## Pre-push checklist

- [ ] Coordinator bootstrap completed.
- [ ] Role-agent order completed pre-open.
- [ ] Bounded local validation passed.
- [ ] Pre-commit and pre-push hooks passed.

## Post-merge checklist

- Sync local main with fetch + ff-only merge.
- Confirm clean working tree.
- Remove SC-G2 worktree/branch artifacts.
- Run preflight + agent consistency sanity.
- Do not start SC-G3 automatically.

## AGENTS.md updates

No AGENTS.md update in this PR.

## Deferred / Follow-ups

- SC-G3 observability and false-hit harness.
- SC-G4 bounded `/insight` semantic-cache experiment after SC-G3 and a
  dedicated gate-open PR.
- SC-G5 backend selection only after safety and rollback proof.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Current actionable review comments have been dispositioned below. Merge
readiness remains blocked until current-head CI, bot status, and the strict
wrapper are clean.

## Fixed in Commit Mapping

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3201964074 -> 9ee894de5
Commit: 9ee894de5
Evidence: `core/ai/__init__.py` keeps the SC-G2 scaffold out of eager facade exports; `tests/test_semantic_cache_scaffold_contract.py` covers facade isolation.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3201984604 -> 0cddad988
Commit: 0cddad988
Evidence: `scripts/ci/check_semantic_cache_gate.py` removes the duplicate SC-G3 missing-phase error; `tests/test_semantic_cache_scaffold_contract.py` covers the single-error regression.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3202053566 -> 955e5a958
Commit: 955e5a958
Evidence: `docs/review/PR_1700_FIXED_MAPPING.md` includes the required checked Discussion Thread Pass checkboxes and `scripts/ci/check_pr_body_phase2_gates.py --pr-number 1700 --body ...` passed locally.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3202053571 -> 955e5a958
Commit: 955e5a958
Evidence: `docs/review/PR_1700_FIXED_MAPPING.md` uses canonical mapping lines with disposition, commit, and evidence fields; `scripts/ci/check_pr_body_phase2_gates.py --pr-number 1700 --body ...` passed locally.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#pullrequestreview-4244613938 -> a4acaa035
Commit: a4acaa035
Evidence: `core/ai/exact_fuzzy_cache.py`, `scripts/ci/check_semantic_cache_gate.py`, `scripts/ci/check_docs_phase1_gates.py`, and `tests/test_semantic_cache_scaffold_contract.py` address the valid CodeRabbit cleanup findings.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3202121235 -> 28802d950
Commit: 28802d950
Evidence: `docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.schema.json` constrains `blocked_surfaces` to the documented enum; `tests/test_semantic_cache_scaffold_contract.py` asserts the enum and minimum count.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3202121237 -> 28802d950
Commit: 28802d950
Evidence: `tests/helpers/semantic_cache_import_guard.py` blocks `datetime.datetime.now` and `datetime.datetime.utcnow`; `tests/test_semantic_cache_scaffold_contract.py` covers the guard.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3202121272 -> 28802d950
Commit: 28802d950
Evidence: `scripts/ci/check_semantic_cache_gate.py` now requires the blocked-list `embeddings` anchor rather than any embedding mention; `tests/test_semantic_cache_scaffold_contract.py` covers the fail-closed case.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1700#discussion_r3202121280 -> 28802d950
Commit: 28802d950
Evidence: `scripts/ci/check_semantic_cache_gate.py` now requires partition-field anchors from the partition contract; `tests/test_semantic_cache_scaffold_contract.py` covers broad `surface` wording drift.

## Merge Readiness

Not merge-ready at artifact creation. Required before merge:

- current-head CI clean;
- PR body gates pass;
- review threads mapped/resolved;
- CodeRabbit/Sourcery/Cubic no actionables or explicit dispositions;
- strict merge wrapper passes;
- mandatory wait-window observed.
