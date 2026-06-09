# Semantic Cache Cost Provenance Telemetry Contract

## Purpose

PR-O1 defines metadata-only cost provenance fields for future semantic-cache
and orchestration context-compression review. This contract does not open the
semantic-cache gate, does not implement semantic cache, does not call providers,
and does not prove live savings.

The semantic-cache gate remains closed:

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Cache read allowed: false.
- Cache write allowed: false.
- Serving allowed: false.
- Provider calls allowed: false.
- Dedicated gate-open PR required: true.

## Scope

Allowed:

- deterministic fingerprints;
- prompt-module IDs, versions, fingerprints, and counts;
- token estimates with an explicit estimate policy version;
- integer cost estimates with an explicit cost policy version;
- provider and model labels as telemetry-only labels;
- reason codes for non-serving decisions;
- safe metadata that contains no raw prompt, query, response, provider payload,
  secret, credential, local path, account truth, or health-sensitive payload.

Blocked:

- raw prompts;
- raw queries;
- normalized queries;
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
- billing, entitlement, or account-truth decisions;
- production cost or ROI claims.

## Required Fields

Every token economy estimate must carry:

- estimate id;
- surface;
- route type;
- provider label;
- model label;
- token estimate version;
- prompt input chars;
- prompt output chars;
- prompt input tokens estimate;
- prompt output tokens estimate;
- baseline context tokens estimate;
- candidate context tokens estimate;
- tokens saved estimate;
- orchestration fanout multiplier;
- provider calls avoided count;
- cost saved microunits;
- cost estimate policy version;
- currency code;
- reason codes;
- produced at;
- metadata.

Every prompt module record must carry:

- module id;
- module version;
- surface;
- text fingerprint;
- char count;
- token estimate;
- token estimate version;
- policy version;
- metadata.

Cost and token fields are separate telemetry dimensions. Token estimates must
not be inferred from cost fields. Cost estimates must not be treated as billing,
entitlement, quota, or provider truth.

## Safety Rules

All strings in metadata, labels, and IDs must be safe for deterministic review.
Unsafe keys or values must fail closed, including nested values inside maps and
lists. Error output must identify the field class and must not echo raw
payloads, secrets, local paths, or user-specific text.

Provider labels such as Ollama, Perplexity, or Sonar-like families are labels
only. They do not select a provider, prove a provider call, mutate routing, or
authorize provider-specific pricing.

Reason codes are non-serving review metadata. Initial PR-O1 reason codes may
include:

- metadata_recorded;
- redaction_applied;
- pricing_unknown;
- provider_unknown;
- runtime_not_allowed;
- gate_closed.

## Follow-Up Gates

PR-O2 may use these records to plan graph-based context narrowing, but PR-O2
must remain a separate reviewed PR. Later runtime semantic-cache serving still
requires the semantic-cache gate-open process, current-head CI governance,
review disposition, observability, rollback thresholds, false-hit controls,
and human approval.

PR-O1 alone does not provide cache hit rate, provider-call avoidance, latency
improvement, quota improvement, cost savings, or merge-readiness evidence.
