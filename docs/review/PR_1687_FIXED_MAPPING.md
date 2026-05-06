# PR #1687 Fixed Mapping

## Summary

Reconciles the semantic-cache gate after Evidence Graph E5 and keeps the gate
machine-checkably closed.

## Goal

Prevent future agents from treating Evidence Graph E1-E5 as approval to
implement semantic cache.

## Business reason

This PR prevents a high-cost/high-risk AI-runtime mistake: introducing semantic
cache as a shortcut before product AI runtime gates, admission policy,
observability, false-hit guardrails, and rollout contracts are explicitly
approved. It preserves the value of Evidence Graph E1-E5 while keeping cache
rollout controlled.

This PR does not add visible product features.

## Scope

- Add fail-closed semantic-cache gate markers.
- Add a deterministic stdlib-only gate checker.
- Add focused tests for unsafe markers and dangerous wording.
- Narrowly update Evidence Graph and backlog docs.

## Out of scope

- Semantic cache implementation.
- Redis, GPTCache, embeddings, vector search, or runtime cache behavior.
- Provider, RAG, FastAPI route, OpenAPI, DB, frontend, iOS, design, advisory
  wiki runtime authority, GraphRAG, online eval, judge calibration, golden,
  dashboard, App Store, or release-control-plane changes.

## Files touched

- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/ci/check_semantic_cache_gate.py`
- `tests/test_semantic_cache_gate.py`
- `docs/review/PR_1687_FIXED_MAPPING.md`

## Tests

Passed locally:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/ci/check_semantic_cache_gate.py
.venv/bin/python -m pytest -q tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py tests/test_repo_policy_guards.py
MYPYPATH=. .venv/bin/python -m mypy --explicit-package-bases --no-incremental --cache-dir=/dev/null scripts/ci/check_semantic_cache_gate.py scripts/ci/check_docs_phase1_gates.py tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py
make validate-changed
pre-commit run --all-files
```

Full `make verify` was intentionally not run under the operator-approved
machine-heavy exception.

## Security notes

- The checker is stdlib-only, offline, and deterministic.
- The checker has no runtime, provider, cache, RAG, or eval imports.
- The checker fails closed if semantic-cache markers are missing or unsafe.
- The checker rejects wording that implies premature cache approval.

## Premortem

- PR accidentally opens semantic cache instead of guarding it: fixed with
  closed markers and a checker that rejects unsafe marker values.
- PR implies Evidence Graph E1-E5 completed cache prerequisites: fixed in the
  gate doc, Evidence epic, backlog wording, and forbidden-claim tests.
- PR lets advisory wiki become product cache source: fixed by required boundary
  wording and a dangerous-claim regression test.
- PR creates second source of truth for cache status: mitigated by making the
  semantic-cache gate doc the checked marker source and linking roadmap/backlog
  wording to that gate.
- Checker is brittle: mitigated by exact marker/phrase checks and narrow
  dangerous-claim checks instead of NLP parsing; review feedback hardened
  marker parsing for hyphenated future values and normalized rollout-order
  matching.
- Checker is too weak: mitigated by marker, status, rollout-order,
  forbidden-claim, import-boundary, and docs Phase1 wiring tests.
- Runtime/provider/cache imports drift in: mitigated by AST import guard.
- Runtime/cache files are modified by accident: fixed by keeping this PR to
  docs, checker, and tests only.
- Existing deferral language is weakened: fixed by adding explicit gate-closed
  markers and dedicated gate-open PR language.
- Mapping/checklists replace real guard fixes: code, docs, and tests changed
  before this mapping artifact.

## Rollback / risks

Rollback is to revert this PR. There are no runtime callers, migrations,
providers, routes, or cache implementation.

Residual risk: future semantic-cache implementation still needs a separate
gate-open PR and current-head CI governance.

## DoD

- [x] Semantic cache gate doc reconciled after Evidence Graph E5.
- [x] Gate status is machine-checkable.
- [x] Checker exists and fails closed on premature cache-open claims.
- [x] Tests cover gate-closed status and dangerous wording regressions.
- [x] No semantic cache implementation.
- [x] No runtime/provider/RAG/cache files changed.
- [x] No advisory wiki product-cache authority.
- [x] Backlog/Evidence docs reflect next step clearly.

## Commit breakdown

- `f8aff50e6` - `docs(ai-runtime): reconcile semantic cache gate`
- `facb35b81` - `fix(ci): harden semantic cache gate parser`
- `bb6fc3071` - `fix(ci): enforce semantic cache gate in docs checks`
- `2cc69d457` - `fix(ci): support direct docs gate execution`

## Pre-push checklist

- [x] Coordinator bootstrap packet created: `3c71c0ad7c80`
- [x] Preflight passed
- [x] Agent consistency passed
- [x] Semantic-cache gate checker passed
- [x] Focused tests passed
- [x] Narrow mypy passed
- [x] `make validate-changed` passed
- [x] `pre-commit run --all-files` passed
- [x] Pre-push hooks passed
- [x] Full `make verify` intentionally deferred under machine-heavy exception

## Post-merge checklist

- Sync local `main` with fetch + ff-only merge.
- Confirm working tree clean.
- Do not start semantic cache implementation automatically.
- Next implementation PR must be explicitly selected by operator based on
  current repo truth.

## AGENTS.md updates

N/A. No agent instruction changes were needed.

## Deferred / Follow-ups

- Dedicated semantic-cache gate-open PR only when operator explicitly opens that
  scope.
- Product AI runtime cache design remains blocked pending observability,
  false-hit guardrails, rollout contract, and current-head CI governance.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Evidence: `facb35b81` hardens marker parsing and adds regression coverage for hyphenated marker values. `bb6fc3071` wires semantic-cache validation into Docs Phase1 gates and adds regression coverage for unsafe marker changes. `2cc69d457` preserves direct-script execution for the CI docs gate.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1687#discussion_r3196267076 -> facb35b81
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1687#discussion_r3196271692 -> 2cc69d457

## Merge Readiness

Not merge-ready at artifact creation.

Required before merge:

- current-head PR CI clean;
- PR body gates clean;
- CodeRabbit/Sourcery/Cubic no-actionables confirmed;
- mandatory post-open `qa-engineer-agent -> bug-hunter` pass complete;
- strict merge-readiness wrapper passes;
- review wait-window observed.
