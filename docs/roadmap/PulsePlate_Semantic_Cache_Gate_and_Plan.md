# PulsePlate Semantic Cache Gate and Plan

**Last reconciled:** 10 April 2026
**Rail:** Product AI runtime rail only
**Status:** Deferred optimization gate, not active execution scope

## Summary

Semantic cache is **not** part of the current active Wave 6 train.

Current `main` already contains:
- merged `A1` fallback/readiness runtime truth
- landed PRO/VIP tier-aware monthly quota machinery
- deterministic orchestration confidence recomputation

The remaining active train is:
1. docs reconciliation after merged `A1`
2. `A2` residual RAG hardening
3. `A3` bounded-context packet
4. `A4` bounded-context extraction
5. `A5` reliability/security gates

Semantic cache can be considered only **after** those runtime rails are closed.

## Hard Gate

Do **not** start semantic cache work before all of the following are true:

1. `A1` merged and reconciled in docs/backlog
2. `A2` closed
3. `A3` closed
4. `A4` closed
5. at least `A5` reliability/security gates closed

## Rail Boundary

Semantic cache belongs only to the **product AI runtime rail**.

It must not be mixed into:
- Karpathy/advisory/wiki rail
- workforce memory
- billing/auth/entitlement truth
- compliance-sensitive outputs
- user-account truth surfaces

## Future Rollout Order

If the gate opens later, the rollout order is fixed:

1. docs contract for insight runtime caching semantics
2. exact/fuzzy cache
3. bounded semantic cache for `/insight`
4. observability and false-hit guardrails
5. only then Redis/GPTCache backend

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
