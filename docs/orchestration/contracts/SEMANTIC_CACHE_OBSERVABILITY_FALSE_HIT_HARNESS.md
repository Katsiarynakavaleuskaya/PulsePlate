# Semantic Cache Observability And False-Hit Harness Contract

## Purpose

SC-G3 defines an offline only, non-serving safety harness for future
semantic-cache review. It does not open the semantic-cache gate, does not enable
runtime caching, and does not enable `/insight` serving.

The gate remains closed:

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Dedicated gate-open PR required: true.

SC-G3 is a deterministic backend contract layer over SC-G2 exact/fuzzy lookup
outputs. It models audit event records, false hit outcomes, negative controls,
observability metrics, stop rules, rollback thresholds, and kill switch
snapshot state before any future runtime experiment.

## Scope

Allowed:

- offline only analysis;
- non-serving audit event construction;
- deterministic false hit evaluation;
- deterministic negative controls;
- stop rules and rollback thresholds;
- kill switch snapshot modeling;
- integer basis-point observability metrics;
- Evidence Graph lineage reuse from SC-G2 records;
- admission blocked hit modeling;
- stale source, policy mismatch, model mismatch, and context leakage modeling.

Blocked:

- runtime serving;
- `/insight` route wiring;
- raw prompts;
- raw model responses;
- raw query text;
- normalized query text in observability payloads;
- embeddings;
- semantic similarity;
- vector search;
- Redis;
- GPTCache;
- provider calls;
- FastAPI, OpenAPI, DB, or migration changes;
- advisory wiki product truth.

## Audit Event Contract

The audit event is safe metadata only. It may contain:

- audit event id;
- idempotency key;
- surface;
- request fingerprint;
- candidate record id;
- candidate response fingerprint;
- lookup decision;
- match mode;
- policy version;
- provider key;
- model key;
- user tier;
- context fingerprint;
- transparency notice id;
- source fingerprints;
- eval event ids;
- admission decision id;
- promotion ids;
- replay entry ids;
- reason codes;
- explicit produced_at timestamp;
- reviewed safe metadata.

The audit event must not contain raw prompts, raw model responses, raw query
text, normalized query text, secrets, credentials, HealthKit payloads, account
truth, legal/compliance output truth, or path-like local artifacts.

## False Hit Harness

The false hit harness evaluates hypothetical cache decisions without serving
cached output. It consumes SC-G2 lookup output and candidate record fingerprints;
it does not duplicate matching logic and does not introduce embeddings or
semantic similarity.

Risk classes:

- exact_duplicate_hit;
- normalized_fuzzy_hit;
- semantic_false_positive;
- stale_source_hit;
- policy_version_mismatch_hit;
- model_version_mismatch_hit;
- user_context_leakage_hit;
- admission_blocked_hit;
- blocked_surface_hit.

`semantic_false_positive` is a label only for future risk modeling. It is not a
semantic runtime, model call, embedding lookup, vector search, Redis, or
GPTCache backend.

Negative controls must include:

- stale source fingerprints;
- policy mismatch;
- model mismatch;
- user tier mismatch;
- context leakage;
- admission blocked hit;
- blocked surfaces;
- unsafe prompt examples as labels only;
- account truth examples as labels only;
- HealthKit and sensitive health examples as labels only;
- legal/compliance examples as labels only.

Any negative control candidate hit must fall back. A blocked or mismatched
candidate hit is a false hit in this offline harness.

## Observability Metrics

Metrics use integer counts and integer basis points only:

- eligible_request_count;
- candidate_hit_count;
- safe_hit_count;
- false_hit_count;
- fallback_count;
- bypass_count;
- kill_switch_disabled_count;
- admission_blocked_hit_count;
- stale_source_hit_count;
- policy_mismatch_hit_count;
- model_mismatch_hit_count;
- context_leakage_hit_count;
- blocked_surface_hit_count;
- eligible_hit_rate_bps;
- served_hit_rate_bps;
- false_hit_rate_bps;
- cache_precision_proxy_bps;
- stale_answer_rate_bps;
- fallback_rate_bps;
- bypass_rate_bps;
- latency_saved_p50_ms;
- latency_saved_p95_ms;
- provider_calls_avoided_count;
- cost_saved_microunits.

Zero-denominator metrics must produce deterministic zero rates, not NaN, None,
or optimistic precision. Hit rate alone is not a success metric.

## Stop Rules And Rollback Thresholds

Stop rules must trigger rollback when any safety threshold is breached:

- false hit rate above policy threshold;
- stale answer rate above policy threshold;
- policy mismatch hits above policy threshold;
- model mismatch hits above policy threshold;
- context leakage hits above policy threshold;
- blocked surface hits when blocked surface hits are not allowed.

Rollback output is a deterministic decision with reason codes. A rollback
decision is evidence for stopping future serving, not a serving mechanism.

## Kill Switch Snapshot

The kill switch snapshot is explicit input and includes:

- environment enabled;
- runtime enabled;
- request disabled;
- bypass forced.

If the snapshot disables hypothetical serving, the harness must emit fallback
and block safe-hit classification. SC-G3 never reads environment state directly.

## Blocked Surfaces

Blocked surfaces include:

- billing/auth/entitlement;
- legal/compliance outputs;
- user-account truth;
- HealthKit-derived sensitive payloads;
- raw prompts;
- raw model responses;
- raw query text;
- normalized query text;
- secrets, tokens, credentials, and private keys;
- highly personalized coaching state;
- advisory wiki pages as product truth;
- GraphRAG or knowledge graph runtime output.

## Rollout Position

The semantic-cache rollout order remains:

1. SC-G1 rollout gate contract.
2. SC-G2 exact/fuzzy cache scaffold.
3. SC-G3 observability and false-hit harness.
4. SC-G4 bounded `/insight` semantic-cache experiment.
5. SC-G5 backend selection.

SC-G4 remains a future bounded `/insight` experiment. SC-G4 still requires a
separate reviewed PR, feature flag, off-by-default behavior, current-head CI
governance, and human approval. SC-G5 backend selection remains blocked until
measured safety evidence and rollback proof exist.
