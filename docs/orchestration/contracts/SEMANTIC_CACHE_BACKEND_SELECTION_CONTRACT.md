# Semantic Cache Backend Selection Contract

## Purpose

SC-G5 backend selection defines an offline, deterministic, label-only
evaluation matrix for future semantic-cache backend candidates. It does not
open the semantic-cache gate. It does not enable runtime caching. It does not
approve Redis/GPTCache rollout. It does not select a backend for serving by
default.

SC-G5 does not open the semantic-cache gate.

Gate remains closed.

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Default activation: none.
- Decision output: recommendation-only metadata.
- Redis/GPTCache status: candidate backend labels only.

## Position In Rollout

Required rollout order remains:

1. SC-G1 rollout gate contract.
2. SC-G2 exact/fuzzy cache scaffold.
3. SC-G3 observability and false-hit harness.
4. SC-G4 bounded `/insight` semantic-cache experiment.
5. SC-G5 backend selection.

SC-G5 consumes SC-G2 lineage, SC-G3 observability and false-hit evidence, and
SC-G4 bounded `/insight` decision metadata. It does not replace those
contracts and does not duplicate matching, false-hit evaluation, or experiment
eligibility logic.

## Candidate Labels Only

Allowed backend candidates are inert labels:

- `in_memory_label`;
- `redis_label`;
- `gptcache_label`.

These labels are not clients, adapters, stores, connection strings, dependency
selectors, environment variables, probes, imports, or runtime configuration.
Redis/GPTCache are candidate labels only and are not approved, enabled,
supported, active, or selected for serving by this contract.

## Required Evidence

Every backend label evaluation requires:

- SC-G2 contract and lineage evidence;
- SC-G3 audit, negative-control, metric, stop-rule, and kill-switch evidence;
- SC-G4 bounded `/insight` metadata-only decision evidence;
- source fingerprints;
- eval event IDs;
- admission decision ID;
- promotion IDs;
- replay entry IDs;
- evidence fingerprints;
- current-head CI governance proof;
- human approval record before a future gate-open PR may act on the selection.

Safety is a hard gate before ranking. Any false-hit, stale-answer,
policy-mismatch, model-mismatch, context-leakage, admission-blocked, blocked
surface, missing negative-control, missing fresh-runtime comparison, missing
rollback, missing kill-switch, or missing current-head CI proof makes the
candidate ineligible.

## Deterministic Ranking

Eligible candidates are ranked only after safety and rollback proof pass.
Ranking uses integer public values only:

- lowest `false_hit_rate_bps`;
- lowest `stale_answer_rate_bps`;
- lowest policy, model, and context mismatch counts;
- lowest rollback blast radius basis points;
- latency and cost as tie-breakers only;
- stable backend label and candidate ID as final tie-breakers.

Hit rate, latency saved, provider calls avoided, and cost saved are not success
metrics until safety passes.

## Required Rollback Proof

Each candidate must include backend-specific rollback proof:

- kill switch proof;
- request bypass proof;
- no-cache fallback proof;
- purge/invalidation proof;
- disabled-state test IDs;
- stop-rule replay IDs;
- rollback runbook ID;
- rollback blast radius basis points.

Missing rollback proof forces no selection.

## Blocked Runtime And Backend Scope

SC-G5 blocks:

- runtime serving;
- `/insight` route wiring;
- FastAPI;
- OpenAPI;
- DB writes;
- migrations;
- provider calls;
- environment reads;
- network calls;
- file writes;
- Redis imports or clients;
- GPTCache imports or clients;
- cache backend adapters;
- connection strings;
- availability probes;
- vector search;
- embeddings;
- semantic similarity backends;
- dependency additions.

## Blocked Payloads And Product-Truth Sources

SC-G5 must not contain, persist, rank, or emit:

- raw prompts;
- raw queries;
- normalized queries;
- raw model responses;
- raw answers;
- provider payloads;
- secrets, credentials, authorization headers, cookies, API keys, or private
  keys;
- local paths;
- HealthKit-derived sensitive payloads;
- diagnosis-like health data;
- highly personalized coaching state;
- user-account truth;
- billing/auth/entitlement truth;
- legal/compliance output truth.

SC-G5 must not use advisory wiki, workforce memory, local support plane,
GraphRAG, knowledge graph runtime output, plugin/control-plane output, or any
second source of truth as product cache source or backend-selection authority.

## Machine-Readable State

```json
{
  "acceptance_criteria": [
    "gate remains closed",
    "runtime_allowed remains false",
    "implementation_allowed remains false",
    "backend candidates are labels only",
    "Redis/GPTCache are not approved for rollout",
    "no runtime imports or backend clients",
    "safety hard-gates ranking",
    "rollback proof is required"
  ],
  "allowed_backend_labels": [
    "in_memory_label",
    "redis_label",
    "gptcache_label"
  ],
  "blocked_payload_fields": [
    "raw prompts",
    "raw queries",
    "normalized queries",
    "raw model responses",
    "raw answers",
    "provider payloads",
    "secrets",
    "credentials",
    "authorization headers",
    "cookies",
    "API keys",
    "private keys",
    "local paths",
    "HealthKit-derived sensitive payloads",
    "diagnosis-like health data",
    "highly personalized coaching state",
    "user-account truth",
    "billing/auth/entitlement truth",
    "legal/compliance output truth"
  ],
  "blocked_runtime_dependencies": [
    "FastAPI",
    "OpenAPI",
    "DB writes",
    "migrations",
    "provider calls",
    "environment reads",
    "network calls",
    "file writes",
    "Redis imports or clients",
    "GPTCache imports or clients",
    "cache backend adapters",
    "connection strings",
    "availability probes",
    "vector search",
    "embeddings",
    "semantic similarity backends",
    "dependency additions"
  ],
  "blocked_truth_sources": [
    "advisory wiki",
    "workforce memory",
    "local support plane",
    "GraphRAG",
    "knowledge graph runtime output",
    "plugin/control-plane output",
    "second source of truth"
  ],
  "candidate_backend_labels": [
    "in_memory_label",
    "redis_label",
    "gptcache_label"
  ],
  "default_activation": "none",
  "forbidden_claims": [
    "active semantic-cache claim",
    "enabled semantic-cache claim",
    "open semantic-cache claim",
    "approved Redis rollout claim",
    "approved GPTCache rollout claim",
    "serving backend selection claim",
    "production readiness claim",
    "raw prompt caching claim",
    "raw response caching claim"
  ],
  "gate_status": "closed",
  "implementation_allowed": false,
  "label_only_backends": true,
  "required_evidence": [
    "SC-G2 lineage evidence",
    "SC-G3 false-hit evidence",
    "SC-G4 bounded insight decision evidence",
    "source fingerprints",
    "eval event IDs",
    "admission decision ID",
    "promotion IDs",
    "replay entry IDs",
    "evidence fingerprints",
    "current-head CI governance proof",
    "human approval record"
  ],
  "required_rollback_proof": [
    "kill switch proof",
    "request bypass proof",
    "no-cache fallback proof",
    "purge/invalidation proof",
    "disabled-state test IDs",
    "stop-rule replay IDs",
    "rollback runbook ID",
    "rollback blast radius basis points"
  ],
  "rollout_phase": "SC-G5",
  "runtime_allowed": false,
  "selection_mode": "recommendation_only"
}
```

## Premortem Closure

- Accidental gate open: closed markers remain the source of truth and this
  contract repeats runtime/implementation false.
- Redis/GPTCache import drift: labels are inert and backend imports, clients,
  connection strings, probes, and dependency additions are blocked.
- Latency over safety: safety hard-gates ranking before latency or cost can
  break ties.
- Prose-only rollback: rollback proof fields are required and
  machine-checkable.
- Advisory wiki truth drift: advisory wiki, workforce memory, support plane,
  GraphRAG, and plugin/control-plane outputs are blocked as product truth.
