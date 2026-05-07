# PR #1702 Fixed Mapping

## Summary

PR #1702 adds SC-G3 as an offline-only deterministic cache observability and
false-hit harness layer. Semantic-cache markers remain closed and no runtime
serving, `/insight` wiring, embeddings, Redis/GPTCache, provider calls, DB,
FastAPI, or OpenAPI changes are introduced.

## Goal

Define and test the safety layer required before any future bounded
semantic-cache experiment can be considered.

## Business Reason

The PR reduces stale-answer, false-hit, leakage, and rollback risk before any
future cache serving work. It protects PulsePlate from premature cache rollout
and expensive provider/runtime mistakes.

## Scope

- Offline backend contracts in `core/ai/cache_observability.py`.
- SC-G3 contract doc and schema.
- Semantic-cache gate checker integration.
- Docs Phase1 gate integration.
- Focused unit, checker, schema, import, and nondeterminism guard tests.
- Narrow roadmap/backlog sync.

## Out Of Scope

- Runtime cache serving.
- `/insight` wiring.
- Gate-open marker changes.
- Embeddings, semantic similarity, vector search, Redis, GPTCache, providers.
- FastAPI, OpenAPI, DB, migrations, GraphRAG, dashboards, online evals, or
  product behavior changes.

## Files Touched

| File | Purpose |
| --- | --- |
| `core/ai/cache_observability.py` | Offline SC-G3 backend contract and helpers |
| `tests/core/ai/test_cache_observability.py` | Deterministic backend coverage |
| `docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md` | SC-G3 governance contract |
| `docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.schema.json` | Machine-readable SC-G3 contract shape |
| `scripts/ci/check_semantic_cache_gate.py` | SC-G3 fail-closed validator |
| `scripts/ci/check_docs_phase1_gates.py` | Docs Phase1 SC-G3 integration |
| `tests/test_semantic_cache_observability_contract.py` | Contract/checker/schema tests |
| `tests/helpers/semantic_cache_import_guard.py` | Extra forbidden time APIs |
| `docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md` | Narrow SC-G3 link |
| `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` | Narrow SC-G3 link, markers unchanged |
| `docs/roadmap/BACKLOG_LEDGER.md` | Current follow-up updated to SC-G3 |

## Tests

- `python scripts/orchestration/check_preflight.py`
- `python scripts/orchestration/check_agent_consistency.py`
- `python scripts/ci/check_semantic_cache_gate.py`
- `python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- `python -m pytest -q tests/core/ai/test_cache_observability.py tests/core/ai/test_exact_fuzzy_cache.py tests/test_semantic_cache_observability_contract.py tests/test_semantic_cache_rollout_gate.py tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py tests/test_repo_policy_guards.py`
- `python -m mypy --no-incremental --cache-dir=/dev/null core/ai/cache_observability.py tests/core/ai/test_cache_observability.py scripts/ci/check_semantic_cache_gate.py scripts/ci/check_docs_phase1_gates.py`
- `make validate-changed`
- `pre-commit run --all-files`
- Push hooks: changed-file mypy, pip-audit, backend pre-push tests, full-repo
  bandit, docker build test.

## Security Notes

- Audit serialization excludes raw query, normalized query, raw prompt, raw
  response, and raw answer payloads.
- Metadata rejects prompt/response/secret/token/credential/HealthKit/account
  and path-like leakage.
- Import guards reject runtime/provider/cache/RAG/eval imports and
  nondeterministic wall-clock/random APIs, with an explicit allowlist for the
  required SC-G2 `core.ai.exact_fuzzy_cache` contract import.
- Bandit changed-files and full-repo pre-push hooks passed.

## Premortem

| Failure Mode | Mitigation | Evidence |
| --- | --- | --- |
| SC-G3 accidentally serves cache output | Offline-only module, no runtime import, no facade export | `tests/core/ai/test_cache_observability.py` |
| Raw prompt/response leakage | Fingerprints/IDs only and unsafe metadata validation | `test_audit_serialization_excludes_raw_query_prompt_response` |
| Stale-source hit accepted | Harness blocks changed source fingerprints | stale-source evaluation test |
| Policy/model/context leakage | Harness blocks mismatched fields | policy/model/context tests |
| Kill switch ignored | Snapshot forces fallback classification | kill-switch test |
| Stop thresholds ignored | Stop decision triggers rollback | stop-rule test |
| Docs imply gate open | Checker rejects live-serving/gate-open wording | `tests/test_semantic_cache_observability_contract.py` |

## Rollback / Risks

Rollback is a clean revert of this PR. No runtime route, DB, provider,
Redis/GPTCache, OpenAPI, or `/insight` changes are present.

## DoD

- SC-G3 offline observability/false-hit harness exists.
- Semantic-cache gate remains closed.
- SC-G1/SC-G2 rollout order remains intact.
- No runtime serving or `/insight` wiring.
- Audit events are safe metadata only.
- Negative controls, metrics, stop rules, rollback thresholds, and kill-switch
  snapshot are documented and tested.
- Checker and Docs Phase1 gate fail closed on unsafe wording.

## Commit Breakdown

- `d0f9c3259` - SC-G3 backend/offline harness, contracts, gates, tests,
  roadmap/backlog sync.

## Pre-Push Checklist

- [x] Preflight passed.
- [x] Agent consistency passed.
- [x] Focused pytest bundle passed.
- [x] Narrow mypy passed.
- [x] `make validate-changed` passed after commit.
- [x] `pre-commit run --all-files` passed.
- [x] Push hooks passed.

## Post-Merge Checklist

- Sync local `main` with fetch + ff-only merge.
- Confirm working tree clean.
- Run preflight and agent consistency.
- Do not start SC-G4 automatically.

## AGENTS Updates

None.

## Deferred / Follow-Ups

SC-G4 remains future-only: bounded `/insight` semantic-cache experiment,
feature-flagged and off by default, only after SC-G3 lands and a later reviewed
PR is selected.

## Discussion Thread Pass

No GitHub review threads at PR open. Post-open packet
`artifacts/orchestration/task_packets/491ff8345781.json` assigned
`qa-engineer-agent -> bug-hunter`. The first QA explorer did not return and was
closed; replacement QA pass returned no actionable findings at
`4baed94e8a2aa68a29cdd3991f87f56357866487`. Bug-hunter returned three
actionable findings; all were fixed before mapping.

## Fixed In Commit Mapping

- PR open baseline -> `d0f9c3259`
- Mapping artifact -> `2ae7177ff`
- Post-open bug-hunter malformed hit audit event finding -> `2008d659e`
- Post-open bug-hunter blocked-backend checker wording finding -> `2008d659e`
- Post-open bug-hunter import guard wording/allowlist finding -> `2008d659e`
- Replacement QA no-actionable pass -> `4baed94e8`

## Merge Readiness

Not merge-ready yet. Requires current-head CI, strict merge wrapper,
review-thread disposition, and bot review pass with no actionables.
