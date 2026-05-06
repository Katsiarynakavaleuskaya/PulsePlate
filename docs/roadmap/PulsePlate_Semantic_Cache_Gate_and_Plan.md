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
- user-account truth surfaces

## Future Rollout Order

If the gate opens later, the rollout order is fixed:

1. docs contract for insight runtime caching semantics
2. exact/fuzzy cache
3. bounded semantic cache for `/insight`
4. observability / false-hit guardrails
5. Redis/GPTCache backend only later

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
- embedding or compatible similarity key
- answer payload
- provider actually used
- source fingerprints / source hashes
- reason codes
- transparency notice id
- TTL
- model/version key
- safety/classification flags

Minimum metrics:
- hit-rate
- false-hit rate / precision proxy
- latency saved
- cost saved
- stale-answer rate

## Reminder

Trigger phrase for future planning:

`Check semantic cache gate for PulsePlate`

When that phrase is used, re-verify the gate against current GitHub truth, backlog state, and `main`.
