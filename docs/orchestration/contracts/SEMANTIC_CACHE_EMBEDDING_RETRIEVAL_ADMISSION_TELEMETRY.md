# Semantic Cache Embedding / Retrieval Admission Telemetry Contract

## Purpose

PR-O4 defines metadata-only embedding/retrieval admission telemetry for future
orchestration cost decisions. It records safe evidence references, deterministic
candidate labels, policy metadata, reason codes, and closed-gate authority
flags. It does not open the semantic-cache gate, does not generate embeddings,
does not compare semantic similarity, does not execute retrieval runtime, does
not call providers, does not wire Ollama, Perplexity, Sonar, or GPT clients,
does not read or write caches, does not serve cached payloads, and does not
prove live savings.

The semantic-cache gate remains closed:

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Admission allowed: false.
- Embedding allowed: false.
- Retrieval runtime allowed: false.
- Semantic similarity allowed: false.
- Vector search allowed: false.
- Provider calls allowed: false.
- Provider wiring allowed: false.
- Cache read allowed: false.
- Cache write allowed: false.
- Serving allowed: false.
- Model downgrade allowed: false.
- Pricing truth allowed: false.
- Selected embedding backend: none.
- Selected retrieval runtime: none.
- Telemetry phase: PR-O4.
- Dedicated gate-open PR required: true.

## Scope

Allowed:

- deterministic evidence refs using safe repo-relative paths and
  `sha256:` fingerprints only;
- deterministic candidate labels for future embedding, retrieval, or hybrid
  review;
- policy snapshot metadata with authority boundary
  `metadata_only_non_serving`;
- packet telemetry with `admission_allowed=false`, `embedding_allowed=false`,
  `retrieval_runtime_allowed=false`, `semantic_similarity_allowed=false`,
  `vector_search_allowed=false`, `provider_calls_allowed=false`,
  `cache_read_allowed=false`, `cache_write_allowed=false`, and
  `serving_allowed=false`;
- selected embedding backend fixed to `none`;
- selected retrieval runtime fixed to `none`;
- reason codes and follow-up gates that document why admission is deferred.

Blocked:

- raw prompts;
- raw queries;
- normalized queries;
- raw context snippets;
- raw model responses;
- raw answers;
- provider payloads;
- provider API payloads;
- embedding vectors;
- retrieval queries;
- similarity scores;
- secrets;
- credentials;
- local absolute paths;
- account truth;
- billing truth;
- entitlement truth;
- health-sensitive payloads;
- embedding models or embedding generation;
- semantic similarity;
- vector indexes;
- vector search;
- retrieval runtime;
- GraphRAG runtime;
- provider clients or provider calls;
- Ollama wiring;
- Perplexity wiring;
- Sonar wiring;
- GPT client wiring;
- Redis, GPTCache, DB, OpenAPI, frontend, or iOS changes;
- runtime admission decisions;
- backend selection decisions;
- cache read, cache write, or serving decisions;
- final review or merge-readiness model downgrade;
- provider-specific pricing truth;
- live savings, production cost, retrieval quality, cache-hit-rate, quota,
  latency, ROI, or merge-readiness claims.

## Required Fields

Every evidence ref must carry:

- ref id;
- ref type;
- source path;
- source fingerprint;
- metadata.

Every admission candidate must carry:

- candidate id;
- candidate type;
- surface label;
- evidence ref ids;
- admission state;
- reason codes;
- metadata.

Every policy snapshot must carry:

- policy id;
- policy version;
- authority boundary;
- gate status;
- evidence ref types;
- candidate types;
- reason codes;
- metadata.

Every embedding/retrieval admission telemetry record must carry:

- telemetry id;
- telemetry phase;
- policy snapshot id;
- evidence refs;
- candidates;
- admission allowed;
- embedding allowed;
- retrieval runtime allowed;
- semantic similarity allowed;
- vector search allowed;
- provider calls allowed;
- cache read allowed;
- cache write allowed;
- serving allowed;
- selected embedding backend;
- selected retrieval runtime;
- required followups;
- reason codes;
- metadata.

Required reason codes:

- `gate_closed`;
- `metadata_only`;
- `admission_deferred`;
- `no_embeddings`;
- `no_vector_search`;
- `no_runtime_retrieval`;
- `no_provider_call`;
- `no_cache_serving`;
- `future_gate_required`.

## Safety Rules

Embedding/retrieval admission telemetry is advisory orchestration metadata. It
must not replace `required_context`, `context_pack_compression`,
`provider_model_tier_routing`, coordinator-first execution, role dispatch,
review-thread disposition, fixed mapping, semantic-cache gate checks,
Experiment Runner evidence, or merge-readiness gates.

Admission state is always `deferred_gate_closed` while this contract is active.
The word "candidate" means a future reviewed label, not eligibility,
admission, routing, serving, cache use, retrieval execution, or backend
selection.

Token and cost fields are estimates only when present through separate
telemetry. They are not cache hit rate, provider-call avoidance proof, latency
improvement, quota improvement, production cost savings, ROI, retrieval-quality
evidence, merge-readiness evidence, billing truth, or permission to open
runtime retrieval.

Final reasoning, security review, QA review, PR review, final synthesis, and
merge-readiness review remain governed by the existing frontier-review policy.
PR-O4 must not downgrade review quality or authorize final review on cheaper
tiers.

## Follow-Up Gates

Future runtime embedding or retrieval work requires a separate reviewed
gate-open PR that changes the machine-checkable semantic-cache markers and
defines replay safety, lineage, admission policy, observability, false-hit
guardrails, rollback thresholds, provider wiring review, and current-head CI
governance.

PR-O4 alone does not provide embeddings, semantic similarity, vector search,
retrieval runtime, provider calls, provider wiring, cache reads, cache writes,
serving, provider-specific prices, live savings, retrieval quality, cache hit
rate, provider-call avoidance, latency improvement, quota improvement, cost
savings, merge-readiness evidence, or runtime admission permission.
