# Evidence Metadata Admission Contract

PR-E4 adds a pure, deterministic admission layer over the Evidence Graph
Runtime contracts from PR-E1, PR-E2, and PR-E3.

This contract decides whether an evidence target may be used for:

- `allow_execute`
- `allow_promote`
- `allow_serve`

The layer is internal only. It does not write files, call providers, read or
write databases, change OpenAPI, add routes, run evals, or enable semantic
cache.

## Inputs

`AdmissionInput` is the normalized metadata shape used by all admission
decisions.

Required fields:

- `target_id`
- `target_type`
- `fingerprint`
- `idempotency_key`
- `policy_version`
- `produced_at`
- `validation_status`
- `coverage_rate`
- `verification_rate`
- `fallback_rate`
- `upstream_ids`

Optional linkage:

- `source_event_id`
- `promotion_id`
- `event_type`
- `promotion_decision`
- `degraded_reason`
- `metadata`

Inputs fail closed on blank identity fields, malformed fingerprints, unsupported
validation statuses, non-finite or out-of-range metrics, unsafe metadata, and
path-like metadata strings.

## Policy

`AdmissionPolicy` defines deterministic thresholds and allowlists:

- `policy_version`
- `min_verification_rate`
- `min_coverage_rate`
- `max_fallback_rate`
- `allow_degraded`
- `allowed_validation_statuses`
- `stale_after_seconds`
- `allowed_event_types`
- `allowed_decisions`

Current time is never read inside the admission helper. Callers must pass an
explicit `now` timestamp, which keeps replay and tests deterministic.

## Decisions

`AdmissionDecision` returns:

- `decision_id`
- `action`
- `allowed`
- `policy_version`
- `target_id`
- `target_type`
- `fingerprint`
- `idempotency_key`
- `produced_at`
- `reason_codes`
- `blocking_reasons`
- `warnings`
- `metadata`

`decision_id` is derived from canonical decision fields using
`fingerprint_payload(...)`. Wall-clock time is not part of decision identity.

## Semantics

`allow_execute` blocks malformed identity, invalid fingerprint, unsupported
status, stale or future input, degraded input unless policy explicitly permits
it, and unsafe metadata.

`allow_promote` is the strict path. It requires:

- `validation_status == "valid"`
- non-stale input
- `verification_rate >= min_verification_rate`
- `coverage_rate >= min_coverage_rate`
- `fallback_rate <= max_fallback_rate`
- non-empty upstream lineage
- allowed event type and promotion decision when present
- no degraded reason unless policy explicitly permits degraded mode

`allow_serve` allows valid non-stale evidence when policy permits the target
event or promotion decision. It blocks stale, degraded, or invalid evidence
unless degraded serving is explicitly allowed by policy.

## Metadata Safety

Admission metadata is frozen defensively and returned only as a copy.

Forbidden metadata includes:

- raw prompt or response fields;
- user-health or medical payload fields;
- secret-bearing keys or obvious token strings;
- bytes or non-JSON-compatible values;
- path-like strings, including current-directory values such as `.`, `./`, and
  `./.`.

Metadata safety is intentionally local to `core/evidence/admission.py` in E4 to
avoid a broad cross-module refactor.

## Boundaries

E4 is not:

- semantic cache;
- Redis, GPTCache, or cache-hit logic;
- GraphRAG or knowledge graph runtime;
- product RAG behavior;
- `core/knowledge/promotion.py`;
- eval runner behavior;
- online eval, goldens, judge calibration, or dashboards;
- runtime routes, providers, OpenAPI, DB, billing, auth, or user-facing behavior.

Semantic cache prerequisites are not complete after E4. E4 only satisfies the
active metadata admission prerequisite; semantic cache still requires a separate
dedicated gate, observability, false-hit guardrails, and rollout contract.

## E5 Handoff

The next Evidence Graph slice is PR-E5 advisory wiki evidence bridge. E5 may
connect advisory artifacts to evidence identity and admission metadata, but it
must preserve advisory wiki as non-canonical workforce memory rather than
product runtime truth.
