# NOOS-1A Evidence Relation Structural Audit v1

<!-- markdownlint-disable MD013 -->

This offline eval distinguishes a claim's link to evidence from an assertion
about two world referents. It checks structural requirements over one supplied,
finite inventory. It does not establish causality, scientific method quality,
reviewer independence, source authorship, or completeness of external evidence.

## Commands and limits

Run from the repository root:

```bash
python -m scripts.evals.evidence_relation_audit validate --input SNAPSHOT.jsonl
python -m scripts.evals.evidence_relation_audit report --input SNAPSHOT.jsonl --output REPORT.json
```

`validate` checks the entire snapshot without writing. `report` writes one
canonical JSON report. Negative assessments are successful report data; process
exit zero does not admit a causal assertion. The reader rejects malformed UTF-8,
BOM, duplicate object keys, non-JSON constants, trailing JSON content, blank
lines, raw carriage-return lines, symlinks, hardlinks, nonregular files,
ambiguous or missing references, invalid record identities and scope omissions.
Limits are 8 MiB for input and report, 256 KiB per line, 10,000 records,
JSON nesting depth 32, 512 references per record, and 50,000 emitted adverse
link references. An over-limit report is rejected whole before publication.

The output parent must be owned by the current user and not group- or
world-writable. The CLI creates a 0600 stage in that parent, syncs it, publishes
with a no-replace hard link, then syncs and removes the stage. It never
overwrites an existing destination. A post-link durability error returns a
failure while retaining the complete linked destination for inspection.

## Snapshot records

Each JSONL line is exactly one object with `kind` equal to `asset`,
`epistemic_link`, or `world_relation`. All fields are required; extra fields
fail. `asset` contains `use_kind` plus an `EvidenceAssetRef` object with
`asset_id`, `asset_type`, `version`, `rail`, `upstream_ids`, `idempotency_key`,
`policy_version`, and `fingerprint`. `use_kind` is one of `evidence`, `method`,
`independent_review`, `context`; it is independent of `asset_type`.
Asset and idempotency identities are recomputed using the existing evidence
helpers, and every upstream must exist in this snapshot on the same rail.
The asset fingerprint is a declared content identity; source bytes are not
included in the snapshot and are not authenticated by this audit.

An `epistemic_link` has `id`, `claim_ref`, `evidence_ref`, `relation`,
`context_ref`, `time_scope`, `attribution`, `produced_at`,
`source_fingerprint`, `record_fingerprint`, and `revision_of_ref` (null or a
prior link ID). Relations are `supported_by`, `contradicted_by`,
`derived_from`, `replicated_by`, and `invalidated_by`. Direction is claim to
evidence. `contradicted_by` and `invalidated_by` are represented adverse links;
an invalidation does not erase other links.

A `world_relation` has `id`, `subject_ref`, `object_ref`, `claim_ref`,
`relation`, `epistemic_status`, `context_ref`, `time_scope`, `attribution`,
`produced_at`, `source_fingerprint`, `record_fingerprint`, `method_refs`,
`independent_review_refs`, `epistemic_link_refs`, and `revision_of_ref` (null
or a prior assertion ID). The reference fields are arrays of unique IDs.
`epistemic_status` is `not_claimed`, `candidate`, or `adjudicated`.
`produced_at` needs an explicit time-zone offset. No current clock enters the
report. The assertion is `subject relation object`: for `caused_by`, the
subject is the claimed result and object the claimed cause; for
`observed_after`, subject is observed later than object.

All epistemic links selected by an assertion must match its exact
`claim_ref` + `context_ref` + `time_scope`. Every represented adverse link for
that key must be selected, so favorable-only selection cannot hide conflict.
Other scopes are outside this literal comparison; no semantic equivalence or
external completeness is inferred. Revisions retain both records and both
assessments. Self-revision, cross-type revision and revision cycles fail.
World endpoint cycles are not generally prohibited: reciprocal association
assertions are distinct records.

`record_fingerprint` is `fingerprint_payload` of the complete JSON object
excluding only `record_fingerprint` itself. The report fingerprint covers the
complete canonical report excluding only `report_fingerprint`; the input
fingerprint covers all supplied records sorted by validated kind and ID.
These fingerprints detect changed bound data. They are not signatures.

## Structural matrix

| World relation | Structural outcome |
| --- | --- |
| `observed_after` | Temporal only when status is `not_claimed`; never causal pass. |
| `associated_with` | Requires a method reference and the mandatory context reference; remains qualified. |
| `contributed_to` | Requires a method reference and status `candidate` or `adjudicated`; remains qualified. |
| `caused_by` | Requires `adjudicated`, method and independent-review references, and zero represented unresolved adverse links in exact scope. |

The positive `caused_by` label is
`structural_requirements_satisfied_for_supplied_scope`. Method, review and
adjudication are input declarations. All authority and answer-change flags
are literally false. The audit does not downgrade, promote, change an answer,
or decide whether a claimed method/reviewer is actually sound or independent.

The immutable symbolic corpus at
`tests/fixtures/evidence_relation_audit_v1.jsonl` contains seven frozen
matrix controls and one scoped contradiction. The expected pass vector is
`false, false, false, false, false, false, true, false`; these are structural
controls, not model-authored scientific judgments. The tests also verify
permutation/replay bytes, revision retention, malformed input, reference
integrity, output preservation, local-only behavior and derived-output bounds.

## Boundary

This contract extends the existing offline eval lane. It introduces no
FitChef/RAG runtime, API/OpenAPI, client, DB, provider, semantic-cache,
Evidence Graph serving, knowledge promotion, or sidecar authority. The next
NOOS-1B slice must separately evaluate concrete FitChef answer content and
business outcomes; this structural baseline makes no such measurement claim.
