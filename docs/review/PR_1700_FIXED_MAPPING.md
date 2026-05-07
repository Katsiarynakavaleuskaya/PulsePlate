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

- [x] Semantic-cache gate remains closed.
- [x] SC-G2 scaffold is pure and deterministic.
- [x] Checker/docs Phase1 integration fails closed.
- [x] Tests cover matching, hard misses, deterministic IDs/order, import guards,
  and dangerous wording.
- [x] No runtime/provider/RAG/cache files changed.

## Commit breakdown

- `a4fce6daa` - `feat(ai-runtime): add exact fuzzy cache scaffold`

## Pre-push checklist

- [x] Coordinator bootstrap completed.
- [x] Role-agent order completed pre-open.
- [x] Bounded local validation passed.
- [x] Pre-commit and pre-push hooks passed.

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

Post-open status at artifact creation:

- GitHub review threads: none known yet.
- CodeRabbit/Cubic/Sourcery: not yet dispositioned as no-actionable; merge
  readiness remains blocked until current-head bot/review status is clean or
  dispositioned.

## Fixed in Commit Mapping

No human or bot review threads have been resolved at artifact creation.

Pre-open agent findings fixed before PR open:

- QA false-green checker findings -> `a4fce6daa`
- Bug-hunter punctuation-only query and passive wording findings -> `a4fce6daa`

Post-open QA governance finding:

- Missing canonical mapping artifact -> fixed by this artifact commit.

## Merge Readiness

Not merge-ready at artifact creation. Required before merge:

- current-head CI clean;
- PR body gates pass;
- review threads mapped/resolved;
- CodeRabbit/Sourcery/Cubic no actionables or explicit dispositions;
- strict merge wrapper passes;
- mandatory wait-window observed.
