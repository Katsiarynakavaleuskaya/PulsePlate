# Semantic Cache Rollout Gate Contract

## Purpose

This contract defines the conditions for a future semantic-cache gate-open PR.
It does not open the semantic-cache gate. It does not implement semantic cache.

The gate remains closed until a later reviewed PR explicitly changes the
machine-checkable gate markers in
`docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`.

## Current Status

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Dedicated gate-open PR required: true.

SC-G1 is a contract-only step. It describes how a future rollout may be
evaluated; it does not approve runtime cache behavior.

## Allowed Rail

Semantic cache belongs to the product AI runtime rail only.

It is not:

- advisory wiki;
- workforce memory;
- plugin/control-plane truth;
- billing/auth/entitlement truth;
- legal/compliance output truth;
- user-account truth;
- a second source of truth.

Advisory wiki pages as product truth are blocked. Advisory wiki pages may not
seed product cache entries.

## First Allowed Surface

The first future semantic-cache runtime surface may only be a bounded,
repetitive `/insight`-style product AI output.

Any future first implementation must be:

- feature-flagged;
- off by default;
- request-time disableable;
- easy to bypass;
- easy to roll back;
- isolated from billing, auth, entitlement, account, legal, compliance, and
  advisory surfaces.

## Required Rollout Sequence

Future work must follow this order:

1. SC-G1 rollout gate contract.
2. SC-G2 exact/fuzzy cache scaffold.
3. SC-G3 observability and false-hit harness.
4. SC-G4 bounded `/insight` semantic-cache experiment.
5. SC-G5 backend selection.

SC-G2 must be deterministic exact/fuzzy cache only: no embeddings, no semantic
similarity, no Redis, no GPTCache, no vector search, and no provider changes.
The phase-specific SC-G2 scaffold contract is
[`EXACT_FUZZY_CACHE_SCAFFOLD.md`](./EXACT_FUZZY_CACHE_SCAFFOLD.md), which keeps
SC-G2 pre-serving and lexical-only.

SC-G3 must run before any semantic-cache serving. It must define offline proxy
evaluation, negative controls, stop rules, and observability. The
phase-specific SC-G3 contract is
[`SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md`](./SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md),
which keeps SC-G3 offline only and non-serving.

SC-G4 is the first bounded semantic-cache experiment. It must stay
feature-flagged, off by default, and limited to the `/insight`-style product AI
surface.

SC-G5 may consider Redis/GPTCache only after safety evidence, rollback proof,
and current-head CI governance exist.

## Evidence Graph Linkage

Future cache records must link to Evidence Graph state rather than scattered
runtime artifacts.

Required linkage fields:

- source fingerprints;
- eval event IDs where applicable;
- admission decision IDs;
- promotion/replay lineage where applicable;
- policy version;
- model/provider key;
- transparency notice id;
- safety flags.

No cache hit may bypass safety checks, quota checks, input guards, transparency
notice requirements, admission policy, or replay-compatible lineage.

## Admission Requirements

Cache admission must use E4-compatible admission semantics or a dedicated cache
admission contract that is compatible with E4.

No cache hit may serve when source evidence is stale, degraded, invalid, or
policy-mismatched unless a reviewed policy explicitly permits that outcome and
records the reason code.

## False-Hit Risk Model

The future gate-open PR must define and test at least these risk classes:

- exact duplicate hit;
- normalized fuzzy hit;
- semantic false positive;
- stale-source hit;
- policy-version mismatch hit;
- model-version mismatch hit;
- user-context leakage hit.

Minimum false-hit formula:

```text
false_hit_rate = unsafe_or_incorrect_cached_serves / semantic_cache_serves
```

A false hit includes any cached serve that is unsupported by current source
fingerprints, stale, safety-mismatched, user-context/tier-mismatched,
contradicts a fresh runtime answer, contradicts an oracle fixture, or should
have fallen back.

The offline proxy evaluation must compare `fresh_runtime_answer` with
`candidate_cached_answer` before serving. It must include negative controls:
paraphrases that must miss, near-neighbor queries with different intent, stale
source fingerprints, changed user tier/context, denied admission metadata,
unsafe prompts, legal/compliance examples, and account-truth examples.

## Observability Requirements

Future metrics must optimize safety before hit rate:

- eligible_hit_rate;
- served_hit_rate;
- false_hit_rate;
- cache_precision_proxy;
- stale_answer_rate;
- fallback_rate;
- p50/p95 latency_saved;
- provider_calls_avoided;
- cost_saved;
- quota_consumption_delta;
- bypass rate;
- disabled-by-kill-switch count;
- admission-blocked-cache-hit count.

Hit rate alone is not a success metric.

## Kill Switch And Rollback

Future controls must include a kill switch and rollback path:

- environment flag;
- runtime flag snapshot;
- request-time disable;
- cache bypass;
- no-cache fallback path;
- purge/invalidation path;
- deterministic tests proving disabled state;
- rollback runbook;
- stop rules for safety false hits, stale-source serves, source-fingerprint
  mismatch, safety classification mismatch, and policy-version mismatch.

## Blocked Cache Surfaces

Blocked cache surfaces include:

- billing/auth/entitlement;
- legal/compliance outputs;
- user-account truth;
- HealthKit-derived sensitive payloads;
- diagnosis-like health data;
- raw prompts;
- raw model responses;
- secrets, tokens, credentials, or private keys;
- highly identifying user/account state;
- highly personalized coaching state;
- advisory wiki pages as product truth;
- GraphRAG or knowledge graph runtime output.

## Gate-Open Criteria

A future gate-open PR must include:

- explicit marker change in the semantic-cache gate doc;
- linked Evidence Graph lineage;
- admission/replay compatibility;
- observability plan;
- false-hit test harness;
- negative controls;
- rollout and rollback plan;
- kill switch proof;
- current-head CI governance;
- human approval.

Until those criteria are met, semantic cache remains blocked.
