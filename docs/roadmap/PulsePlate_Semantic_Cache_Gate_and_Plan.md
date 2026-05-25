# PulsePlate Semantic Cache Gate and Plan

**Last reconciled:** 24 May 2026
**Rail:** Product AI runtime rail only
**Status:** Gate-closed deferred optimization, not active execution scope

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->

## Summary

Semantic cache is **not** part of the current active Wave 6 train.

Evidence Graph E1-E5 reduced future cache risk by adding evidence asset
lineage, eval events, replay contracts, admission contracts, and advisory wiki
bridge boundaries. Those contracts do not open this gate by themselves.

Semantic cache remains gate-closed until a reviewed gate-open PR changes the
machine-checkable markers above and includes product AI runtime scope,
replay-safe lineage, admission policy, observability, false-hit guardrails,
rollout contract, and current-head CI governance.

The rollout contract is defined in
[`SEMANTIC_CACHE_ROLLOUT_GATE.md`](../orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md).
That contract describes how a future gate-open PR may be evaluated; it does not
open the gate and does not implement semantic cache.

The SC-G2 exact/fuzzy scaffold contract is defined in
[`EXACT_FUZZY_CACHE_SCAFFOLD.md`](../orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md).
That contract is pre-serving and lexical only; it does not enable embeddings,
semantic similarity, runtime caching, or `/insight` wiring.

The phase-three observability and false-hit harness contract is defined in
[`SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md`](../orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md).
That contract is offline only and non-serving; it adds audit-event,
negative-control, metric, stop-rule, rollback-threshold, and kill-switch
contracts without opening the gate or wiring runtime cache behavior.

The SC-G4 bounded `/insight` experiment contract is defined in
[`SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md`](../orchestration/contracts/SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md).
That contract is metadata-only, off by default, request-disableable,
kill-switchable, fail-closed, and non-serving; it does not open the global
semantic-cache gate, wire `/insight`, or approve any backend.

The backend selection contract is defined in
[`SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md`](../orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md).
That contract is offline, label-only, recommendation-only, and non-serving; it
does not open the global semantic-cache gate, approve Redis/GPTCache rollout, or
activate any backend by default.

The Philosophy Epic V2 PR-1 admission contract is defined in
[`PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md`](../orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md).
That contract is policy-only, gate-closed, and non-serving; it defines which
philosophical request classes may enter a future semantic-cache path after gate
open and references merged SC-G5 (`cb1db8b40`) without duplicating the backend
selection matrix.

The Philosophy Epic V2 PR-2 policy oracle is defined by
[`PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`](../orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json)
and the generated oracle fixture
[`philosophy_admission_claim_oracle.json`](../../tests/fixtures/orchestration/philosophy_admission_claim_oracle.json).
Those artifacts make forbidden and allowed philosophical admission claim
families deterministic; they do not approve cache serving or runtime behavior.

The Philosophy Epic V2 PR-3 admission dry-run report is defined by
[`PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json`](../orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json).
That report is governance-only and non-serving. It connects the PR-2
policy/oracle to synthetic verification-bundle states and keeps every dry-run
decision at `cache_read_allowed=false`, `cache_write_allowed=false`, and
`serving_allowed=false`. A passed verification bundle is necessary for future
consideration, but never sufficient while the semantic-cache gate remains
closed.

The Philosophy Epic V2 PR-4 gate-open preconditions report is defined by
[`PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json`](../orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json).
That report is a blocked handoff inventory, not a gate-opening approval. It
validates PR-2 policy/oracle truth, PR-3 dry-run truth, this roadmap's closed
machine markers, and runtime prerequisite anchors while keeping
`gate_open_allowed=false`, `runtime_handoff_allowed=false`,
`cache_read_allowed=false`, `cache_write_allowed=false`, and
`serving_allowed=false`. Ledger anchor presence does not verify prerequisite
closure; a later reviewed gate-open PR must still change the machine-checkable
markers before runtime semantic-cache work can begin.

Philosophy Epic V2 PR-4 landed in PR #1791 on 2026-05-22 with merge commit
`b16175721933012ae53162b8268888c960458d46`, after the PR #1789 alignment-rule
schema prerequisite landed on 2026-05-21 with merge commit
`651c56bb510125b4df011a6d48de6f82a8f6e0b7`. PR-4.1 is a status
reconciliation only: it does not change the closed machine markers above and
does not permit semantic-cache runtime admission, cache reads, cache writes, or
serving. PR-4.2 reconciles the separate alignment-rule ledger row as completed
against PR #1789 only; it does not change the closed machine markers above.
Future PR-4 status reconciliation updates must use the PR-4.1 packet
source-truth section as the update checklist and keep this roadmap to the
minimal status mirror.

Philosophy Epic V2 PR-5 adds the source-corpus index defined by
[`PHILOSOPHY_SOURCE_CORPUS_INDEX.json`](../orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json).
That index preserves the six operator-provided philosophy PDFs as design
evidence with sanitized titles, page counts, fingerprints, repo anchors, and
false runtime flags. It is not PR-A2, does not change the closed machine markers
above, and does not permit semantic-cache runtime admission, cache reads, cache
writes, serving, providers, `/insight`, Redis, GPTCache, embeddings, vector
search, DB, OpenAPI, frontend, or iOS changes.

Current `main` already contains:
- merged `A1` fallback/readiness runtime truth
- landed PRO/VIP tier-aware monthly quota machinery
- landed PR-A2 RAG hardening via PR #1415
- deterministic orchestration confidence recomputation

The runtime prerequisite train is tracked by canonical PR/backlog anchors:
1. `PR-A1b` is reconciled via [`ledger-p1-pro-monthly-quota-ledger-reconciliation`](./BACKLOG_LEDGER.md#ledger-p1-pro-monthly-quota-ledger-reconciliation), PR #1461, and PR #1466
2. `PR-A2` is closed via
   [`ledger-p1-rag-hardening-followthrough`](./BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough),
   PR #1415 `feat(rag): harden degraded retrieval paths and keep contracts
   additive`, merged `2026-04-14T20:59:47Z` with merge commit
   `146da0e0d269acea5ba946d239997705ebaf62c3` from branch
   `feat/rag-hardening-followthrough`
3. `PR-A3` and [`ledger-p1-ai-bounded-context-packet`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet)
4. `PR-A4` and [`ledger-p1-ai-bounded-context-extraction`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction)
5. `PR-A5` and [`ledger-p1-llm-reliability-security-gates`](./BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates)

Semantic cache can be considered only **after** those runtime rails are closed.

## Hard Gate

Do **not** start semantic cache work before all the following are true:

1. `PR-A1b` is reconciled in docs/backlog via [`ledger-p1-pro-monthly-quota-ledger-reconciliation`](./BACKLOG_LEDGER.md#ledger-p1-pro-monthly-quota-ledger-reconciliation), PR #1461, and PR #1466
2. `PR-A2` is closed via
   [`ledger-p1-rag-hardening-followthrough`](./BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough),
   PR #1415 `feat(rag): harden degraded retrieval paths and keep contracts
   additive`, merged `2026-04-14T20:59:47Z` with merge commit
   `146da0e0d269acea5ba946d239997705ebaf62c3` from branch
   `feat/rag-hardening-followthrough`
3. `PR-A3` is closed via [`ledger-p1-ai-bounded-context-packet`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet)
4. `PR-A4` is closed via [`ledger-p1-ai-bounded-context-extraction`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction)
5. at least `PR-A5` is closed via [`ledger-p1-llm-reliability-security-gates`](./BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates)

## Rail Boundary

Semantic cache belongs only to the **product AI runtime rail**.

It must not be mixed into:
- not advisory wiki
- not workforce memory
- not a second source of truth
- not billing/auth/entitlement truth
- not a compliance/legal output cache
- not user-account truth surfaces

## Future Rollout Order

If the gate opens later, the rollout order is fixed:

1. SC-G1 rollout gate contract
2. SC-G2 exact/fuzzy cache scaffold
3. SC-G3 observability and false-hit harness
4. SC-G4 bounded `/insight` semantic-cache experiment
5. SC-G5 backend selection
6. Philosophy admission contract reconciliation for philosophical request classes
7. Philosophy admission policy oracle and dry-run verification-bundle adapter
8. Philosophy gate-open preconditions blocked handoff inventory

## First-Pass Safety Limits

The first semantic cache slice must stay narrow:
- only repetitive `/insight`-style product AI surfaces
- no billing
- no entitlement
- no auth/session
- no legal/compliance outputs
- no highly user-specific account truth

## Required Metadata and Metrics

Any future semantic cache record must include:
- normalized query
- SC-G2 exact/fuzzy key when the phase is exact/fuzzy scaffold only
- SC-G4 semantic key only after SC-G3 false-hit harness and a reviewed gate-open PR
- response fingerprint, not raw answer payload, before any future serving gate
- provider actually used
- source fingerprints / source hashes
- reason codes
- transparency notice id
- TTL
- model/version key
- safety/classification flags

For SC-G4 specifically, the current decision layer must use safe fingerprints,
IDs, reason codes, and metadata only. It must not store raw prompts, raw
queries, normalized queries, raw model responses, raw answers, or provider
payloads.

Minimum metrics:
- eligible_hit_rate
- served_hit_rate
- false_hit_rate
- cache_precision_proxy
- stale_answer_rate
- fallback_rate
- p50/p95 latency_saved
- provider_calls_avoided
- cost_saved
- quota_consumption_delta

## Reminder

Trigger phrase for future planning:

`Check semantic cache gate for PulsePlate`

When that phrase is used, re-verify the gate against current GitHub truth, backlog state, and `main`.
