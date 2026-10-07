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
python -m scripts.evals.evidence_relation_audit inspect --input SNAPSHOT.jsonl \
  --claim-ref CLAIM --context-ref CONTEXT --time-scope PERIOD --output NEIGHBORHOOD.json
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

For invocations whose first argument is exactly inspect, native root and
subparser argument errors return 2 with only
evidence_relation_audit: argument_error, before reading or writing.
Native argparse owns grammar and normal help. Legacy validate/report
argument-error, exit and report-byte contracts remain unchanged. Invalid
literal query tokens delegate to the canonical relation token recognizer.

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
Evidence Graph serving, knowledge promotion, or sidecar authority. NOOS-1B
owns the separate evaluation of concrete FitChef answer content and business
outcomes; this structural baseline makes no such measurement claim.

## GRAPH-FED-1 read-only inspection

core/evidence/federation.py reuses the whole canonical snapshot parser and
structural audit before selection. Public interfaces are
build_evidence_projection(snapshot) and select_claim_neighborhood(projection,
claim_ref=..., context_ref=..., time_scope=...).
The immutable QualifiedEvidenceRefV1 identity is exactly namespace plus
canonical snapshot fingerprint plus local ID. Namespaces are evidence.asset,
evidence.link, evidence.assertion, and evidence.assessment. Qualification
does not relax v1's globally unique original IDs. Assessments use their
assertion's local ID in the separate derived namespace.

Direct snapshot/projection/result objects undergo exact original
class/container/primitive admission before conversion or serialization.
Existing source aggregate 10,000, per-reference 512 and combined world-reference
512 bounds reject before adapter materialization. The complete canonical
parser and whole audit, including its 50,000 adverse-reference bound, still
run even for an absent query. Raw assessment causal flags require exact bool;
legitimate canonical True is preserved. Authority/answer-change flags must be
literally False, rejecting True and numeric 0/1 before masked serialization
or ordinary equality. Every derived field must match the one canonical audit.

After whole canonical parsing and audit, but before any whole qualified
projection or hash preimage is allocated, construction applies an 8 MiB
conservative derived-material byte estimate. Build, selection and both public
serializers reuse this same check, including absent queries over the supplied
source. A canonical-valid source can therefore produce report_limit when its
derived representation exceeds this budget; its source validity is unchanged.

The estimate counts each bounded raw record's actual canonical JSON bytes,
192 bytes for that record's fixed wrapper keys/syntax, and the full encoded
ASCII size of every qualified reference occurrence, including repeated F
values and array commas. It reserves 2 KiB for the fixed projection/report,
maximum literal query and derived identity envelopes. It then adds the larger
of the projection reference inventory or the informational asset-reference
inventory, whose entries reserve 64 syntax bytes plus their actual qualified
reference, rail and fingerprint bytes. This upper estimate covers the whole
projection and any exact main/history neighborhood subset without constructing
the expanded dictionaries. Raw records are encoded one at a time, under the
existing canonical 512-reference limit; canonical grammar/audit owners and
their bounds are unchanged.

An exceeded derived budget rejects the whole operation with report_limit
before qualification/fingerprinting. There is no trimming, dropped reference,
new raw-source cap, raised limit or MemoryError-only recovery. Final inspect
encoding separately uses native incremental JSON chunks and a byte buffer
bounded by the existing 8 MiB output limit, counting the terminal newline
before extending the buffer. Private publication occurs only after complete
successful encoding. Budget constants are not new public metadata: successful
canonical report bytes, source F, result R and replay identity remain unchanged.

For one literal query, main contains **every** exact claim/context/time link
and assertion, including positive links unlisted by any assertion. A claim is
known only through a link/assertion claim_ref occurrence; assets and opaque
world endpoints are not a claim registry.

| Lookup state | Exact main seeds |
| --- | --- |
| claim_absent | No claim occurrence in the supplied inventory. |
| scope_absent | Claim occurs elsewhere; no exact links or assertions. |
| no_epistemic_links | Exact assertions exist, but no exact links. |
| present | Exact links exist, with any number of exact assertions. |

All four are successful data outcomes. History never changes the seed state.
Selection closes iteratively over the complete bidirectional same-namespace
revision components, including predecessors, successors and sibling forks.
Selected assertions add all explicit epistemic-link and canonical assessment
references; those links' revision components are included too. Required
evidence/context/method/review assets close over explicit upstream IDs.
Main is exactly the query seeds; history is selected records outside those
seeds. Unreferenced positives/assertions sharing only a historical key remain
excluded. Original periods, timestamps, fingerprints and declarations survive;
there is no latest-is-truth rule or added upstream-cycle policy.

Every selected assertion retains its separate canonical assessment and every
emitted qualified reference resolves. Internal tuples are immutable;
serialization returns fresh nested containers. complete_for_supplied_inventory
quantifies these exact seed/closure/reference sets, not external knowledge.
Overbounds reject whole without truncation. The existing CLI reader and
private no-replace writer remain the only I/O owners; core has no I/O or
runtime/provider/cache integration and no general facade export.

### One informational result envelope

ClaimNeighborhoodV1 is one plain offline presentation report, classified
gate_report, advisory, v1, policy graph-fed1-inspection-v1. Its qualified
informational upstream_refs equal the selected asset/upstream closure and
preserve original asset rails and fingerprints. These references are not
E1 admitted lineage. Full canonical input fingerprint binds even an empty
lookup. No synthetic source asset, E1 asset helper, per-rail result duplicate,
registry, event, promotion, cache write or serving permission is introduced.

result_fingerprint is fingerprint_payload of **every public field except
only** result_fingerprint and idempotency_key. This includes full input
binding, literal query, lookup state, original/derived main/history records,
assets and qualified references, metadata, completeness, replay/admission
meanings and false authority flags. The deterministic idempotency_key is
fingerprint_payload of:

    {
      "purpose": "graph-fed1-read-only-replay",
      "policy_version": "graph-fed1-inspection-v1",
      "input_fingerprint": "<canonical F>",
      "query": {"claim_ref": "<claim>", "context_ref": "<context>", "time_scope": "<period>"},
      "result_fingerprint": "<result R>"
    }

This is a read-only replay identity, not an E1 asset-write key. Replay derives
identical bytes for identical canonical source/query/policy; an existing output
path still fails no-replace. Original reference-array order remains bound.
Raw input-file bytes/hash are separate unchanged-input evidence. Producer
source fingerprints, asset fingerprints, record fingerprints, input F, result R
and replay identity have different subjects; none is a signature, source
authentication, currentness, scientific truth or approval.

The existing frozen symbolic corpus is a fixture-only inspection source.
For C2, its declared context and T1, the exact main is link L1, assertion
W8 and its negative assessment, four required assets and empty history.
An actual observed CLI invocation plus independent full record/reference
reconciliation and unchanged input is required before claiming consumer proof.
Removing projection/inspect preserves sources and legacy validate/report;
there is no data migration or provider switch.
