# Review Invariant-Family Relations Shadow Contract

## Status and authority

This document is the sole policy source of truth for the L1 deterministic
invariant-family relations sidecar. The JSON Schema and Python
`POLICY_PROJECTION` are exact mirrors of the uniquely delimited policy block
below; tests reject drift among the three copies.

The sidecar is an offline, snapshot-relative derived view. It does not review a
change, infer a family, approve a finding, post a comment, resolve a thread,
update fixed mapping, promote knowledge, route an agent, mutate runtime state,
or authorize a merge. It has no product-runtime or public-API integration.

<!-- BEGIN REVIEW_INVARIANT_FAMILY_RELATIONS_POLICY_V1 -->
```json
{
  "policy_version": "review_invariant_family_relations.policy.v1",
  "schema_versions": {
    "snapshot": "review_invariant_family_snapshot.v1",
    "relations": "review_invariant_family_relations.v1"
  },
  "bounds": {
    "max_stdin_bytes": 1048576,
    "max_stdout_bytes": 1048576,
    "max_stderr_bytes": 4096,
    "max_findings": 2048,
    "max_families": 32,
    "max_memberships": 4096,
    "max_relation_records": 496,
    "max_derived_partition_refs": 2048,
    "max_id_ascii_bytes": 64
  },
  "id_pattern": "^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?$",
  "forbidden_id_pattern": "(?:[Aa][Cc][Cc][Ee][Ss][Ss][_-]?[Kk][Ee][Yy]|[Aa][KkSs][Ii][Aa]|[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|[Aa][Uu][Tt][Hh][Oo][Rr][Ii][Zz][Aa][Tt][Ii][Oo][Nn]|[Bb][Ee][Aa][Rr][Ee][Rr]|[Cc][Ll][Ii][Ee][Nn][Tt][_-]?[Ss][Ee][Cc][Rr][Ee][Tt]|[Cc][Rr][Ee][Dd][Ee][Nn][Tt][Ii][Aa][Ll]|[Gg][Hh][PpOoUuSsRr]_|[Gg][Ll][Pp][Aa][Tt]-|[Gg][Ii][Tt][Hh][Uu][Bb][_-]?[Pp][Aa][Tt]|[Nn][Pp][Mm]_|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Rr][Ii][Vv][Aa][Tt][Ee][_-]?[Kk][Ee][Yy]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Ss][Kk][_-]?(?:[Ll][Ii][Vv][Ee]|[Tt][Ee][Ss][Tt]|[Pp][Rr][Oo][Jj])|[Tt][Oo][Kk][Ee][Nn]|[Xx][Oo][Xx][AaBbPpRrSs]-)",
  "relation_values": [
    "equal",
    "left_proper_subset",
    "right_proper_subset",
    "partial_overlap",
    "disjoint"
  ],
  "authority_fields": [
    "side_effects_allowed",
    "posting_allowed",
    "thread_resolution_allowed",
    "mapping_authority",
    "implementation_authority",
    "approval_authority",
    "review_authority",
    "security_authority",
    "runtime_authority",
    "learning_authority",
    "reflection_authority",
    "kpp_authority",
    "oracle_authority",
    "routing_authority",
    "promotion_authority",
    "merge_authority"
  ],
  "inference_sources_forbidden": [
    "prose",
    "paths",
    "roles",
    "severity",
    "statuses",
    "oracles",
    "learning",
    "reflection",
    "artifacts",
    "providers",
    "similarity"
  ],
  "canonicalization": {
    "json": "ascii_compact_sorted_keys",
    "stdout_terminator": "one_lf",
    "utf8_bom_policy": "reject",
    "numeric_lexeme_policy": "reject_all",
    "membership_source": "explicit_only",
    "pair_order": "family_id_lexicographic",
    "partition_order": "finding_id_lexicographic"
  },
  "digests": {
    "algorithm": "sha256",
    "separator": "nul",
    "snapshot_core_domain": "pulseplate.review-invariant-family.snapshot-core.v1",
    "artifact_core_domain": "pulseplate.review-invariant-family.artifact-core.v1",
    "artifact_core_excludes": [
      "artifact_fingerprint",
      "idempotency_key"
    ],
    "idempotency_uses_full_artifact_digest": true
  }
}
```
<!-- END REVIEW_INVARIANT_FAMILY_RELATIONS_POLICY_V1 -->

## Closed document branches

`review_invariant_family_relations.v1.schema.json` is one closed Draft 2020-12
schema with a single `oneOf`. The discriminator is `schema_version`:

- `review_invariant_family_snapshot.v1` is the source branch. It contains one
  finite universe of finding IDs and zero or more explicitly declared families.
- `review_invariant_family_relations.v1` is the replay branch. It contains the
  full normalized snapshot, every canonical pair relation and partition,
  `unknown_finding_ids`, both fingerprints, the idempotency key, and the closed
  authority fields.

Both variants require every authority field in the policy projection to be the
JSON literal `false`. Every object is closed: missing, additional, mistyped,
`null`, or coerced fields are invalid. Family IDs are unique. Finding IDs are
unique within the universe and within each family. Every membership must name a
finding in the finite universe.

Draft 2020-12 `uniqueItems` compares whole family objects and cannot express
cross-item uniqueness of one property. Schema validation is therefore
structural only for the family array: every consumer must also run the CLI
semantic validator, which enforces unique `family_id` values, membership
subsets, bounds, normalization, and all replay recomputation invariants.

The ID grammar is ASCII-only, at most 64 bytes, and excludes whitespace,
slashes, dots, colons, URL syntax, query syntax, and other path/secret-bearing
punctuation. IDs are opaque labels; they are not storage for review text,
paths, URLs, credentials, tokens, provider payloads, or user data.

## Explicit-set semantics

Only the submitted membership lists define the family sets. The sidecar never
infers membership from prose, paths, roles, severity, statuses, oracle output,
learning or reflection artifacts, provider output, or similarity. Input
permutations are normalized by lexicographic family ID and finding ID.

For every lexicographically oriented pair `(left, right)`, the artifact carries
three disjoint, complete partitions over `left union right`:

- `intersection_finding_ids = left intersect right`
- `left_only_finding_ids = left minus right`
- `right_only_finding_ids = right minus left`

The relation is exactly one of:

- `equal` when `left = right`, including empty/empty;
- `left_proper_subset` when `left` is a strict subset of `right`, including an
  empty left and non-empty right;
- `right_proper_subset` when `right` is a strict subset of `left`, including an
  empty right and non-empty left;
- `partial_overlap` when the intersection and both side-only partitions are
  non-empty;
- `disjoint` when the intersection is empty and neither set is a subset of the
  other.

`unknown_finding_ids` is separate from all pair relations and equals the finite
universe minus the union of every explicit membership. No claim is made beyond
the submitted snapshot.

## Bounds before materialization

The implementation rejects limit-plus-one inputs. In addition to direct input,
family, membership, relation-record, output, and diagnostic limits, it computes
the exact number of derived partition references before creating any pair
partition.

Let `F` be the number of families and `k` the number of those families that
explicitly contain a particular universe finding. That finding contributes
`C(F,2) - C(F-k,2)` derived partition references. The sum across the universe
must not exceed 2048. This preflight occurs before pair partition materializes;
the final serialized byte-length check remains mandatory.

## Strict JSON and transport

The command accepts no arguments and reads one document from stdin. It reads at
most 1048577 bytes so an oversized stream is detected without an unbounded
read. UTF-8 is required and a UTF-8 BOM is rejected. Duplicate object keys at
any depth, trailing documents, malformed JSON, and every JSON numeric token are
rejected. Numeric tokens include integers, decimals, exponents such as
`1e999`, and non-standard `NaN` or `Infinity`. The document variants contain no
number-valued fields; policy limits are schema metadata, not input values.

Success is canonical `ensure_ascii` JSON with sorted keys, compact separators,
and exactly one trailing LF on stdout, then exit 0. The full artifact and final
output size are validated in memory before the first stdout byte. Contract and
schema failures write no stdout, emit one stable bounded ASCII error code on
stderr without submitted values or a traceback, and exit 2.

The implementation performs one buffered stdout write after validation and
requires its return count to equal the complete rendered payload length. A
short write or transport exception is `output_transport_failure`; the command
does not retry. The operating system may already have accepted a prefix. The
command reports a sanitized transport failure when possible, but it cannot
retract bytes already accepted by a broken pipe or failing sink.

## Fingerprints and replay

Canonical core bytes never include the transport LF.

The snapshot fingerprint is SHA-256 over the ASCII snapshot-core domain, one
NUL byte, and the canonical normalized snapshot bytes. The artifact fingerprint
uses a distinct ASCII artifact-core domain, one NUL byte, and canonical artifact
core bytes. Artifact core excludes exactly `artifact_fingerprint` and
`idempotency_key`; it includes the embedded snapshot and snapshot fingerprint.
The idempotency key contains the full 64-hex artifact digest.

On the replay branch the validator revalidates and normalizes the embedded
snapshot, rechecks every bound and closed authority field, recomputes every
pair, partition, unknown ID, fingerprint, and idempotency key, and compares the
entire submitted artifact with the recomputed artifact. Any field, ordering,
partition, authority, digest, or idempotency mismatch fails closed. A valid
replay emits only the recomputed canonical bytes.

## Integration boundary

The script uses only the Python standard library. It has no output path,
filesystem access, environment access, network or GitHub access, provider call,
subprocess, application/runtime import, bootstrap or dispatch import, oracle or
learning import, review-helper import, mapping integration, workflow hook,
public route, OpenAPI surface, or merge-admission role. L2/L3 work, if ever
promoted, requires a separate reviewed contract and cannot be inferred from
this L1 artifact.
