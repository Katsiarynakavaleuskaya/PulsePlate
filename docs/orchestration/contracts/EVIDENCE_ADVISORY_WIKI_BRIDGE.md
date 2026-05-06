# Evidence Advisory Wiki Bridge

PR-E5 adds a deterministic bridge between existing advisory wiki artifacts and
Evidence Graph contracts.

The bridge is intentionally narrow:

- advisory wiki artifacts remain non-canonical workforce memory;
- repo code, backend contracts, DB/runtime state, OpenAPI, tests, legal and
  compliance records remain canonical truth;
- the bridge does not compile, ingest, promote, mutate, query, or serve wiki
  content;
- the bridge does not unlock semantic cache, GraphRAG, product RAG behavior, or
  product answers.

## Objects

### `AdvisoryWikiArtifactRef`

Represents metadata for an existing wiki artifact.

Required normalized fields:

- `artifact_id`
- `corpus`
- `slug`
- `source_rel_path`
- `page_path`
- `promoted_path`
- `content_hash`
- `policy_version`
- `idempotency_key`
- `advisory_only`
- `promoted`
- `upstream_ids`
- `metadata`

`content_hash` accepts a raw 64-character SHA-256 hex value or
`sha256:<hex>` and stores `sha256:<hex>`.

`artifact_id` and `idempotency_key` are derived from canonical content with
`fingerprint_payload`. They do not depend on wall-clock time, randomness,
filesystem reads, network access, or caller-owned mutable structures.

### `WikiEvidenceBridgePolicy`

Defines deterministic admission into the bridge:

- `policy_version`
- `allowed_corpora`
- `require_content_hash`
- `require_source_rel_path`
- `allow_promoted_only`
- `allowed_admission_statuses`
- `advisory_only_enforced`
- `allowed_asset_types`

`advisory_only_enforced` must remain true.

## Path Rules

`source_rel_path` may point under `docs/**` as provenance because existing wiki
ingest may summarize repository docs.

`page_path` and `promoted_path` must not point under `docs/**`; bridge outputs
must not become canonical documentation authority.

All bridge paths reject:

- traversal such as `../x`;
- absolute paths such as `/tmp/x`;
- home paths such as `~/x`;
- Windows drive paths such as `C:/x`;
- current-directory references such as `.`, `./`, and `./.`.

## Metadata Safety

Metadata is defensively copied into immutable JSON-compatible structures and
validated fail-closed.

Rejected metadata includes:

- raw prompts, responses, queries, user-health payloads, and secrets;
- `rail=runtime` or equivalent runtime authority claims;
- canonical/product/source-of-truth claims;
- unsafe path-like values, including `.`, `./`, and `./.`.

## Evidence Asset Mapping

Wiki artifacts may map only to advisory `EvidenceAssetRef` records.

Allowed asset types:

- `knowledge_candidate`
- `context_bundle`
- `verification_bundle`

Default asset type is `knowledge_candidate`.

The bridge must not map wiki artifacts to the `runtime` rail. It also must not
change cross-rail policy behavior in `core/evidence/policies.py`.

## Admission Adapter

`wiki_artifact_to_admission_input(...)` adapts a wiki artifact into E4
`AdmissionInput` for advisory review/query/promotion workflows only.

The adapter requires explicit:

- `produced_at`
- `coverage_rate`
- `verification_rate`
- `fallback_rate`
- `validation_status`

It never invents metrics. It carries `serve_scope=advisory_review_only`; this
does not authorize user-facing product serving.

## Deferred

This PR does not add `wiki_artifact_to_eval_event(...)`.

Existing PR-E2 eval event types are eval-oriented. Forcing wiki ingest/promote
metadata into `item_metadata` would blur rail semantics. A later schema PR may
add wiki-specific advisory event types if the product needs event-plane lineage
for wiki operations.

Semantic cache remains blocked until a dedicated semantic-cache gate opens with
lineage, admission, replay, observability, false-hit guardrails, and rollout
contracts.

## Premortem Evidence

E5 mitigates the main failure modes in code and tests:

- Recreating the wiki compiler: `core/evidence/wiki_bridge.py` accepts metadata
  only and import guards reject `scripts/orchestration` and wiki CLI imports.
- Granting runtime authority: wiki artifacts always carry `advisory_only=True`
  and map only to advisory evidence assets.
- Importing local support-plane mutation tooling: import guards reject
  `local_support_plane`, wiki mutation CLIs, runtime providers, DB/session,
  cache, GraphRAG, and eval runner modules.
- Mapping to runtime rail: `wiki_artifact_to_evidence_asset_ref(...)` hardcodes
  `rail="advisory"`.
- Bypassing E1/E4 contracts: asset mapping uses `create_evidence_asset_ref`;
  admission mapping creates E4 `AdmissionInput`.
- Claiming semantic cache readiness: this contract keeps semantic cache
  explicitly deferred to a dedicated future gate.
- Storing raw payloads or secrets: metadata validation rejects prompt, response,
  query, user-health, and secret fields/values.
- Accepting unsafe paths: bridge paths reject traversal, absolute, home,
  Windows drive, and current-directory values; docs output paths are blocked for
  page/promoted artifacts.
- Mutating caller-owned structures: metadata and upstream IDs are normalized and
  defensively copied.
- Checklist-only fixes: focused tests cover mapping, authority boundaries,
  metadata/path safety, deterministic IDs, serialization, mutation safety, and
  forbidden imports.
