# Evidence Event Schema

## Purpose

PR-E2 defines a unified append-only eval event schema for Evidence Graph
Runtime. The schema normalizes existing eval artifact metadata into deterministic
event records without changing product runtime behavior.

This contract is schema-first. It does not add an event store, writer, replay
engine, promotion ledger, semantic cache, GraphRAG, advisory wiki expansion,
OpenAPI change, DB migration, provider change, or user-facing behavior.

## Source Artifact Families

The schema can represent these current artifact families:

- RAG release gates: `traces.jsonl`, `metrics_summary.json`, `gate_report.md`,
  `rag_gate_result.json`, and executed-notebook metadata when already produced.
- RAGAS bootstrap reports: `faithfulness`, `answer_relevancy`,
  `context_precision`, and report-only JSON/Markdown outputs.
- Eval-validity sidecars: variant/outcome records, judgment validity items,
  item metadata, item statistics, instability flags, and curated
  invariance/mutation/worst-case metadata when already present.
- Evidence Graph linkage: E1 asset refs, upstream ids, rail, policy version,
  fingerprint, idempotency key, producer identity, validation status, and source
  artifact path.

## Event Model

Runtime contract: `core/evidence/events.py`.

Required event fields:

- `event_id`
- `event_type`
- `rail`
- `source_artifact`
- `asset_refs`
- `upstream_ids`
- `fingerprint`
- `idempotency_key`
- `policy_version`
- `producer`
- `produced_at`
- `validation_status`

Supported event types:

- `rag_gate_run`
- `rag_gate_report`
- `ragas_report`
- `eval_validity_record`
- `judgment_validity_record`
- `item_metadata`
- `item_statistics`
- `gate_metric`
- `gate_decision`

Supported event rails:

- `runtime`
- `advisory`
- `control_plane`
- `eval`

Supported validation statuses:

- `valid`
- `invalid`
- `degraded`
- `deferred`

## Deterministic Identity

`event_id` is derived from canonical event identity fields, including event type,
rail, source artifact, asset ref ids, upstream ids, fingerprint, idempotency key,
policy version, producer, and validation status. It intentionally excludes
`produced_at` so replay of the same semantic event remains idempotent.

Serialization must remain deterministic JSON with stable key order. Tests must
use fixed timestamps and must not depend on wall-clock time.

## Fail-Closed Validation

Event creation must reject:

- unknown event type, rail, or validation status;
- blank or malformed fingerprint;
- blank idempotency key;
- blank, absolute, home-relative, traversal, or local-dev-root source artifact
  paths;
- cross-rail asset refs for non-`eval` event rails;
- raw secret, raw prompt, raw response, user-health, or user-payload metadata.

The event object defensively copies caller-owned lists/dicts and returns
defensive metadata copies from accessors.

## Boundaries

This PR is not a second eval runner. RAGAS and RAG release gates remain upstream
artifact producers.

This PR is not the promotion ledger or replay engine. PR-E3 consumes normalized
event records later.

This PR is not semantic cache, GraphRAG, product RAG rewrite, provider routing,
OpenAPI, or DB persistence.

Karpathy/advisory wiki remains non-canonical workforce memory. It must not
become product runtime truth or an eval-event source of truth in PR-E2.

## Validation

Focused local validation for this schema:

```bash
.venv/bin/python -m pytest -q tests/core/evidence/test_events.py tests/core/evidence/test_assets.py tests/core/evidence/test_fingerprints.py
make validate-changed
pre-commit run --all-files
```

Full local `make verify` is intentionally deferred for PR-E2 by operator
approval because the full suite is machine-heavy. Merge readiness must rely on
documented narrow local gates plus current-head GitHub CI parity.
