# Semantic Cache Provider / Model-Tier Routing Telemetry Contract

## Purpose

PR-O3 defines metadata-only provider/model-tier routing telemetry for future
orchestration cost decisions. It records inert provider labels, model-tier
labels, policy metadata, and reason codes. It does not open the semantic-cache
gate, does not select a provider, does not call providers, does not wire
Ollama, Perplexity, Sonar, or GPT clients, does not implement runtime routing,
does not serve cached payloads, and does not prove live savings.

The semantic-cache gate remains closed:

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Runtime routing allowed: false.
- Runtime handoff allowed: false.
- Cache read allowed: false.
- Cache write allowed: false.
- Serving allowed: false.
- Provider calls allowed: false.
- Provider wiring allowed: false.
- Model downgrade allowed: false.
- Pricing truth allowed: false.
- Selected route: no_runtime_selection.
- Telemetry phase: PR-O3.
- Dedicated gate-open PR required: true.

## Scope

Allowed:

- provider labels are labels only: `gpt`, `ollama`, `perplexity_sonar`,
  `perplexity_agent`, and `unknown_provider`;
- model-tier labels: `frontier_required`, `standard_advisory`,
  `local_preprocess_advisory`, `search_synthesis_advisory`, and
  `unknown_tier`;
- deterministic policy snapshot IDs and routing telemetry IDs from canonical
  metadata;
- role lists for required frontier review and candidate pre-synthesis advisory
  work;
- `TokenEconomyEstimate` ID references when available;
- relative cost rank labels only, not provider-specific price data;
- safe metadata that contains no raw prompt, query, answer, response, provider
  payload, secret, credential, local absolute path, account truth, billing
  truth, entitlement truth, or health-sensitive payload.

Blocked:

- raw prompts;
- raw queries;
- normalized queries;
- raw model responses;
- raw answers;
- provider payloads;
- provider API payloads;
- provider calls;
- provider clients;
- Ollama wiring;
- Perplexity wiring;
- Sonar wiring;
- GPT client wiring;
- OpenAPI or public response fields;
- DB, Redis, GPTCache, or cache backend writes;
- embeddings;
- semantic similarity;
- vector search;
- GraphRAG runtime output;
- runtime router selection;
- provider-specific prices or billing truth;
- final reasoning, final review, final synthesis, security review, QA review,
  CodeRabbit/Codex Security review, or merge-readiness review on any tier other
  than `frontier_required`;
- live savings, production cost, ROI, latency, quota, cache-hit-rate, or
  merge-readiness claims.

## Required Fields

Every provider/model-tier record must carry:

- record id;
- provider label;
- model tier label;
- allowed advisory roles;
- blocked runtime roles;
- quality floor;
- relative cost rank;
- metadata.

Every policy snapshot must carry:

- policy id;
- policy version;
- authority boundary;
- records;
- reason codes;
- metadata.

Every provider/model-tier routing telemetry record must carry:

- telemetry id;
- telemetry phase;
- policy snapshot id;
- selected route;
- required frontier roles;
- candidate pre-synthesis roles;
- blocked runtime roles;
- provider labels;
- model tier labels;
- token economy estimate ids;
- reason codes;
- metadata.

Required reason codes:

- `gate_closed`;
- `metadata_only`;
- `provider_labels_only`;
- `no_runtime_selection`;
- `frontier_review_preserved`;
- `no_provider_call`;
- `no_cache_serving`;
- `no_embeddings`;
- `no_graphrag_runtime`;
- `estimate_only`.

## Safety Rules

Provider/model-tier telemetry is advisory orchestration metadata. It must not
replace `required_context`, `context_pack_compression`, coordinator-first
execution, role dispatch, review-thread disposition, fixed mapping,
semantic-cache gate checks, Experiment Runner evidence, or merge-readiness
gates.

Final reasoning, security review, QA review, PR review, final synthesis, and
merge-readiness review remain `frontier_required`. Advisory labels can describe
future pre-synthesis mechanical work only; they must not downgrade the model for
review, security, or final decision work.

Provider labels are labels only. They do not select a provider, prove a provider
call, mutate routing, authorize provider-specific pricing, create billing truth,
or create entitlement truth. No provider-specific prices are encoded. Relative
cost rank is an ordinal planning label only.

Token savings are estimates only. They are not cache hit rate, provider-call
avoidance proof, latency improvement, quota improvement, production cost
savings, ROI, merge-readiness evidence, or permission to open runtime routing.

## Follow-Up Gates

PR-O4 and later PRs may use PR-O3 telemetry only through separate reviewed gates.
Runtime semantic-cache serving still requires the semantic-cache gate-open
process, current-head CI governance, review disposition, observability,
rollback thresholds, false-hit controls, provider wiring review, and human
approval.

PR-O3 alone does not provide provider calls, runtime routing, provider-specific
prices, live savings, cache hit rate, provider-call avoidance, latency
improvement, quota improvement, cost savings, merge-readiness evidence, or
serving permission.
