# Semantic Cache Bounded Insight Experiment Contract

## Purpose

SC-G4 bounded `/insight` semantic-cache experiment defines a deterministic,
metadata-only decision layer for a future product AI runtime experiment. It does
not open the semantic-cache gate. It does not enable runtime caching. It does
not enable `/insight` serving.

SC-G4 does not open the semantic-cache gate.
SC-G4 does not enable `/insight` serving.

Gate remains closed.

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Experiment default: off by default.
- Allowed surface: bounded `/insight`-style product AI only.
- Backend selection: SC-G5 remains future.

## Position In Rollout

Required rollout order remains:

1. SC-G1 rollout gate contract.
2. SC-G2 exact/fuzzy cache scaffold.
3. SC-G3 observability and false-hit harness.
4. SC-G4 bounded `/insight` semantic-cache experiment.
5. SC-G5 backend selection.

SC-G4 may evaluate whether a future bounded `/insight` cache candidate is
eligible for an experiment, but it remains non-serving. A decision of
`experiment_eligible` is safe metadata only. It is not a cached answer, not a
runtime route, and not global semantic-cache approval.

## Required Flag Semantics

The experiment is off by default and requires all of these explicit signals:

- environment flag enabled;
- runtime flag snapshot enabled;
- explicit request opt-in;
- request disable is false;
- kill switch snapshot permits the hypothetical experiment;
- no bypass is forced.

Fail-closed fallback is mandatory when any signal is absent or disabled:

- environment flag disabled;
- runtime flag disabled;
- request not opted in;
- request disable;
- kill switch disabled;
- bypass forced.

Disable means provider fresh path or stable fallback only. Disable never means
serving a cached answer.

## Required Evidence Graph Linkage

Every SC-G4 decision must carry safe IDs and fingerprints only:

- source fingerprints;
- eval event IDs;
- admission decision ID;
- promotion IDs;
- replay entry IDs;
- policy version;
- provider key as non-secret provider/version reference;
- model key as non-secret model/version reference;
- context fingerprint;
- user tier;
- transparency notice id;
- response fingerprint;
- safety flags;
- request fingerprint.

Missing Evidence Graph linkage forces fallback. Source fingerprint mismatch
forces fallback. Policy mismatch, provider mismatch, model mismatch, context
mismatch, user tier mismatch, transparency notice mismatch, admission blocked,
false-hit blocked, stop-rule blocked, and blocked surface all force fallback.

## Blocked Payloads And Surfaces

SC-G4 must not contain or persist:

- raw prompts;
- raw queries;
- normalized queries;
- raw model responses;
- raw answers;
- provider payloads;
- secrets, credentials, authorization headers, cookies, or API keys;
- local paths;
- HealthKit-derived sensitive payloads;
- diagnosis-like health data;
- highly personalized coaching state;
- user-account truth.

SC-G4 must not use these as product cache sources or surfaces:

- advisory wiki;
- workforce memory;
- billing/auth/entitlement;
- legal/compliance outputs;
- account truth;
- GraphRAG or knowledge graph runtime output.

Advisory wiki pages are not product cache truth and may not seed product cache
entries.

## Blocked Runtime And Backend Scope

SC-G4 blocks:

- FastAPI;
- OpenAPI;
- DB writes;
- migrations;
- provider calls;
- runtime wiring;
- Redis;
- GPTCache;
- vector search;
- embeddings;
- semantic similarity backends;
- raw payload storage;
- cache backend selection.

SC-G5 backend selection remains future and may consider Redis/GPTCache only
after safety evidence, rollback proof, current-head CI governance, and human
approval exist.

## Observability And Rollback

SC-G4 consumes SC-G2 and SC-G3 contracts:

- SC-G2 exact/fuzzy lookup request, lookup result, and candidate record;
- SC-G3 audit event;
- SC-G3 false-hit evaluation;
- SC-G3 observability metrics;
- SC-G3 stop decision;
- SC-G3 kill switch snapshot.

SC-G4 does not duplicate matching logic and does not implement semantic
inference. `semantic_false_positive` remains an SC-G3 risk label only.

Required rollback and stop proof:

- no-cache fallback path;
- purge/invalidation path documented for later serving PRs;
- stop rules for false-hit rate, stale-source hit, policy mismatch, model
  mismatch, context leakage, and blocked surfaces;
- rollback thresholds;
- kill switch snapshot;
- deterministic disabled-state tests.

## Machine-Readable State

```json
{
  "acceptance_criteria": [
    "gate remains closed",
    "off by default",
    "request disable forces fallback",
    "kill switch forces fallback",
    "missing Evidence Graph linkage forces fallback",
    "no raw payload persistence",
    "SC-G5 backend selection remains future"
  ],
  "allowed_surface": "bounded_insight_style_product_ai",
  "blocked_backends": [
    "Redis",
    "GPTCache",
    "embeddings",
    "vector search",
    "semantic similarity backend"
  ],
  "blocked_payload_fields": [
    "raw prompts",
    "raw queries",
    "normalized queries",
    "raw model responses",
    "raw answers",
    "provider payloads",
    "secrets",
    "authorization headers",
    "cookies",
    "API keys"
  ],
  "blocked_surfaces": [
    "advisory wiki",
    "workforce memory",
    "billing/auth/entitlement",
    "legal/compliance outputs",
    "account truth",
    "HealthKit-derived sensitive payloads",
    "GraphRAG"
  ],
  "default_state": "off",
  "feature_flag_sources": [
    "environment flag",
    "runtime flag snapshot",
    "explicit request opt-in",
    "request disable",
    "kill switch snapshot"
  ],
  "gate_status": "closed",
  "implementation_allowed": false,
  "required_decision_fields": [
    "decision",
    "reason_codes",
    "source_fingerprints",
    "policy_version",
    "provider_key",
    "model_key",
    "context_fingerprint",
    "user_tier",
    "transparency_notice_id",
    "response_fingerprint",
    "request_fingerprint"
  ],
  "required_evidence_linkage_fields": [
    "source_fingerprints",
    "eval_event_ids",
    "admission_decision_id",
    "promotion_ids",
    "replay_entry_ids",
    "policy_version"
  ],
  "rollout_phase": "SC-G4",
  "runtime_allowed": false
}
```

## Premortem Closure

- Accidental gate open: checker requires closed gate and rejects active/open
  wording.
- Default enabled drift: code and contract require off by default and explicit
  opt-in.
- Hidden runtime serving path: import guards reject runtime/provider/backend
  imports and app-side cache wiring while the gate is closed.
- Cross-context leakage: context, tier, source, policy, provider, model, and
  transparency mismatches force fallback.
- Raw prompt/response persistence: metadata validators and contract checker
  reject raw prompt/query/response/answer payloads.
- Advisory wiki cache source: blocked surface and checker anchors reject
  advisory wiki product cache truth.
- Redis/GPTCache drift: SC-G5 backend selection remains future.
