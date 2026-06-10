# Semantic Cache Context Compression Telemetry Contract

## Purpose

PR-O2 defines metadata-only context-pack compression telemetry for repeated
orchestration and merge-readiness context. This contract does not open the
semantic-cache gate, does not implement semantic cache, does not serve cached
payloads, does not call providers, and does not prove live savings.

The semantic-cache gate remains closed:

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Runtime handoff allowed: false.
- Cache read allowed: false.
- Cache write allowed: false.
- Serving allowed: false.
- Provider calls allowed: false.
- Dedicated gate-open PR required: true.

## Scope

Allowed:

- deterministic context graph node IDs and edge IDs;
- repo-relative paths for changed files, contracts, tests, agent rules, review
  artifacts, and roadmap entries;
- path fingerprints, source fingerprints, policy versions, idempotency keys,
  and reason codes;
- selected context references and omitted duplicate references;
- baseline and candidate context character estimates;
- baseline and candidate context token estimates;
- saved-token estimates with an explicit token-estimate policy;
- orchestration fanout multipliers;
- safe provider/model labels as inert telemetry labels only;
- safe metadata that contains no raw prompt, query, context, answer, response,
  provider payload, secret, credential, local absolute path, account truth, or
  health-sensitive payload.

Blocked:

- raw prompts;
- raw queries;
- normalized queries;
- raw context snippets;
- raw model responses;
- raw answers;
- provider payloads;
- provider calls;
- OpenAPI or public response fields;
- DB or cache backend writes;
- Redis;
- GPTCache;
- embeddings;
- semantic similarity;
- vector search;
- GraphRAG runtime output;
- runtime handoff;
- billing, entitlement, or account-truth decisions;
- production cost, ROI, latency, quota, cache-hit-rate, or merge-readiness
  claims.

## Required Fields

Every compressed context pack must carry:

- context pack id;
- policy version;
- authority boundary;
- required context;
- selected context refs;
- omitted duplicate refs;
- graph nodes;
- graph edges;
- estimate;
- reason codes;
- metadata.

Every graph node must carry:

- node id;
- node type;
- path;
- path fingerprint;
- token estimate;
- required flag;
- metadata.

Every graph edge must carry:

- edge id;
- source;
- target;
- edge type;
- metadata.

Every context compression estimate must carry:

- estimate id;
- baseline context chars estimate;
- candidate context chars estimate;
- baseline context tokens estimate;
- candidate context tokens estimate;
- tokens saved estimate;
- orchestration fanout multiplier;
- fanout tokens saved estimate;
- token estimate version;
- reason codes.

The schema-level `required_followups` field must carry a non-empty array of
unique string keys naming the required follow-up gates for any future PR that
uses this telemetry. Example:

```json
{
  "required_followups": [
    "semantic_cache_gate_open_pr",
    "runtime_serving_review",
    "provider_wiring_review"
  ]
}
```

## Safety Rules

Context compression is advisory orchestration metadata. It must not replace
`required_context`, coordinator-first execution, role dispatch, review-thread
disposition, fixed mapping, semantic-cache gate checks, Experiment Runner
evidence, or merge-readiness gates.

Required governance context must remain explicit or retain a non-lossy
fingerprinted reference. This includes root `AGENTS.md`, nearest scoped
`AGENTS.md`, `RUNBOOK_AGENT.md`, the active task packet, role definitions for
required passes, semantic-cache gate documents, relevant contracts, and
merge-readiness governance when applicable.

Token savings are estimates only. They are not cache hit rate, provider-call
avoidance proof, latency improvement, quota improvement, production cost
savings, ROI, merge-readiness evidence, or approval to downgrade the review
model. They must not downgrade the review model.

Provider labels such as Ollama, Perplexity, or Sonar-like families are labels
only. They do not select a provider, prove a provider call, mutate routing,
authorize provider-specific pricing, or create billing truth.

## Follow-Up Gates

PR-O3 and later PRs may use PR-O2 telemetry to evaluate provider-routing or
runtime candidates only through separate reviewed gates. Runtime semantic-cache
serving still requires the semantic-cache gate-open process, current-head CI
governance, review disposition, observability, rollback thresholds, false-hit
controls, and human approval.

PR-O2 alone does not provide cache hit rate, provider-call avoidance, latency
improvement, quota improvement, cost savings, merge-readiness evidence, or
serving permission.
