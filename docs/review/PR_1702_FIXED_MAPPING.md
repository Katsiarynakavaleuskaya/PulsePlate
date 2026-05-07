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
future cache-serving work. It protects PulsePlate from premature cache rollout
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
| `.github/workflows/ci.yml` | Adds SC-G3 tests to route-contract coverage bundles so diff-cover observes the new backend module |
| `tests/guards/test_security_devtooling_regression_guards.py` | Resolves docs leakage guard base ref from GitHub PR event when local base refs are unavailable |
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
- `python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths tests/core/ai/test_cache_observability.py tests/test_semantic_cache_observability_contract.py`
- `python -m mypy --no-incremental --cache-dir=/dev/null tests/guards/test_security_devtooling_regression_guards.py tests/core/ai/test_cache_observability.py`
- `python -m coverage erase && python -m coverage run -m pytest -q tests/core/ai/test_cache_observability.py tests/test_semantic_cache_observability_contract.py tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py && python -m coverage xml && python -m diff_cover.diff_cover_tool coverage.xml --compare-branch=origin/main --fail-under=97 ...`
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

- `ba05a98b4` - SC-G3 backend/offline harness, contracts, gates, tests,
  roadmap/backlog sync.
- `bebb0089a` - Add SC-G3 tests to CI route-contract coverage and close
  diff-cover gaps with focused backend tests.
- `1994b6503` - Resolve docs leakage guard base ref from GitHub PR event in
  CI shards without local base refs.
- `aebaf00fa` - Fetch missing base SHA in shallow CI checkouts before docs
  leakage diff evaluation.
- `3949dd377` - Add missing blocked-surface metric schema requirement and
  classify kill-switch-disabled cases as fallback, not false hit.
- `171ebf112` - Fetch the GitHub base branch ref before falling back to raw
  base SHA diff candidates in shallow CI checkouts.

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

Post-open packet `artifacts/orchestration/task_packets/491ff8345781.json`
assigned `qa-engineer-agent -> bug-hunter`. The first QA explorer did not
return and was closed; replacement QA pass returned no actionable findings at
`37b8439c4`. Bug-hunter and live bot review comments were handled with code,
checker, schema, test, and mapping fixes before merge readiness.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 5b07640e6
Evidence: `core/ai/cache_observability.py` includes query identity in safe request fingerprints; `scripts/ci/check_semantic_cache_gate.py` requires explicit blocked/no anchors and broader Redis/GPTCache/provider/runtime forbidden wording; `docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.schema.json` constrains safety arrays; `tests/core/ai/test_cache_observability.py` annotates `_audit_event` and covers distinct fuzzy audit identity; `tests/test_semantic_cache_observability_contract.py` covers stricter schema/checker behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3203874281 -> 5b07640e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4246776756 -> 5b07640e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3203875208 -> 5b07640e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3203875238 -> 5b07640e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3203875245 -> 5b07640e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4246808012 -> 5b07640e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3203903291 -> 5b07640e6
Commit: a346cea40
Evidence: `docs/review/PR_1702_FIXED_MAPPING.md` Discussion Thread Pass includes the two canonical checkboxes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3203931637 -> a346cea40
Commit: c65ca1fa1
Evidence: `docs/review/PR_1702_FIXED_MAPPING.md` applies the CodeRabbit style nit by using `cache-serving`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4246839117 -> c65ca1fa1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4246970326 -> 5b07640e6
Commit: e6a10ae39
Evidence: `tests/helpers/semantic_cache_import_guard.py` now treats allowed SC-G2 contract imports as exact or qualified prefixes, and `tests/core/ai/test_cache_observability.py` covers `from core.ai.exact_fuzzy_cache import create_exact_fuzzy_cache_record`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3204115756 -> e6a10ae39
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4247055915 -> e6a10ae39
Commit: 3b0e0d6e1
Evidence: `scripts/ci/check_semantic_cache_gate.py` now uses tight explicit-prohibition anchor regexes; `tests/core/ai/test_cache_observability.py` preserves empty metadata inputs; `tests/test_semantic_cache_observability_contract.py` asserts specific missing-anchor errors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3204162209 -> 3b0e0d6e1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3204162222 -> 3b0e0d6e1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4247108532 -> 3b0e0d6e1

Commit: 3949dd377
Evidence: `docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.schema.json` includes `blocked_surface_hit_count` in `required_metrics` and raises `minItems` to 25; `core/ai/cache_observability.py` excludes kill-switch-only blocking from false-hit classification; `tests/core/ai/test_cache_observability.py` and `tests/test_semantic_cache_observability_contract.py` cover both fixes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3204426905 -> 3949dd377
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#pullrequestreview-4247408633 -> 3949dd377
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1702#discussion_r3204426937 -> 3949dd377

## Post-Open Agent Mapping

- PR open baseline: `ba05a98b4`
- Mapping artifact: `0060b9729`
- Post-open bug-hunter malformed hit audit event finding: `e9d629b70`
- Post-open bug-hunter blocked-backend checker wording finding: `e9d629b70`
- Post-open bug-hunter import guard wording/allowlist finding: `e9d629b70`
- Replacement QA no-actionable pass: `37b8439c4`
- QA pass recorded in mapping: `37b8439c4`
- CodeRabbit SC-G2 qualified import allowlist finding: `e6a10ae39`
- CodeRabbit tight regex / explicit metadata / anchor assertion findings: `3b0e0d6e1`
- Current-head CI diff-coverage failure at run `25517610754`, job
  `74895099360`: `bebb0089a`
- Current-head CI docs leakage guard base-ref failure at run `25518898784`, job
  `74897945961`: `1994b6503`
- Current-head CI shallow base object failure at run `25520086660`, job
  `74901689252`: `aebaf00fa`
- Current-head CI shallow base branch/SHA diff failure at run `25520806855`,
  job `74904151062`: `171ebf112`

## Merge Readiness

Not merge-ready yet. Requires the new current-head CI run after `171ebf112`,
strict merge wrapper, review-thread disposition, and bot review pass with no
actionables.
