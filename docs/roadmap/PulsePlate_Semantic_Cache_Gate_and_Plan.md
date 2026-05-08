# PulsePlate Semantic Cache Gate and Plan

**Last reconciled:** 6 May 2026
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

Current `main` already contains:
- merged `A1` fallback/readiness runtime truth
- landed PRO/VIP tier-aware monthly quota machinery
- deterministic orchestration confidence recomputation

The remaining runtime prerequisites are tracked by canonical PR/backlog anchors:
1. `PR-A1b` and [`ledger-p1-pro-monthly-quota-ledger-reconciliation`](./BACKLOG_LEDGER.md#ledger-p1-pro-monthly-quota-ledger-reconciliation)
2. `PR-A2` and [`ledger-p1-rag-hardening-followthrough`](./BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough)
3. `PR-A3` and [`ledger-p1-ai-bounded-context-packet`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet)
4. `PR-A4` and [`ledger-p1-ai-bounded-context-extraction`](./BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction)
5. `PR-A5` and [`ledger-p1-llm-reliability-security-gates`](./BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates)

Semantic cache can be considered only **after** those runtime rails are closed.

## Hard Gate

Do **not** start semantic cache work before all the following are true:

1. `PR-A1b` is reconciled in docs/backlog via [`ledger-p1-pro-monthly-quota-ledger-reconciliation`](./BACKLOG_LEDGER.md#ledger-p1-pro-monthly-quota-ledger-reconciliation)
2. `PR-A2` is closed via [`ledger-p1-rag-hardening-followthrough`](./BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough)
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
