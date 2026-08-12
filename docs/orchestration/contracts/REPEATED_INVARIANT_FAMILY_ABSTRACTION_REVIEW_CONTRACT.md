# Repeated Invariant-Family Abstraction Review Contract

## Status and authority

This contract defines the optional L2 consumer of the canonical L1
`review_invariant_family_relations.v1` artifact. L2 is a bounded post-open
review trigger. It does not infer family membership, recompute set relations,
execute roles, fix code, resolve threads, update mappings, grant implementation
or merge authority, or replace any ordinary post-open or current-head gate.

The L1 source remains
`scripts/orchestration/review_invariant_family_relations.py`. The only permitted
repository consumer of its `process_input_bytes(...)` API is
`scripts/orchestration/task_bootstrap.py`. Qoder/role dispatch validates the
closed packet projection and never calls or reimplements L1.

## Input boundary

`task_bootstrap.py` exposes exactly one opt-in argument:

```text
--review-invariant-family-relations-input artifacts/orchestration/review_invariant_family_relations/<basename>.json
```

The argument is valid only with `--pr-phase post_open_review`. The path must be
repo-relative and exactly one direct-child `.json` file under the fixed,
gitignored `artifacts/orchestration/review_invariant_family_relations/` root.
It is incompatible with `--invariant-change-class`; v1 classification and the
closed v2 projection cannot silently replace one another.
Absolute paths, traversal, alternate separators, nested descendants, symlinks,
non-regular files, missing platform no-follow support, changed-during-read
files, and inputs above L1's 1 MiB bound fail closed.

The reader opens each fixed directory component and the final file through
pinned descriptors with `O_NOFOLLOW`. It does not create the root or input. It
reads bounded bytes, calls L1 `process_input_bytes(...)` exactly once, and
parses only those returned canonical bytes. L2 adds no JSON parser, schema,
validator, replay implementation, membership inference, or relation engine.

## Trigger and projection

The only trigger is `explicit_family_cardinality_gte_2`: a normalized L1 family
is repeated when its explicit `finding_ids` cardinality is at least two. The
membership source is exactly `explicit_input_only`. L2 does not infer a causal,
semantic, textual, role, path, severity, status, oracle, learning, provider, or
similarity relationship.

With the input flag, `invariant_review` is the closed `invariant_review.v2`
object with exactly these top-level fields:

- `schema_version`
- `state`
- `coverage_claim`
- `required_roles`
- `boundary_classes`
- `required_output_fields`
- `stop_condition`
- `family_repeat`
- `implementation_authority`
- `merge_authority`

It omits v1 `change_classes` and `trigger_evidence`. Its fixed values are:

- `schema_version=invariant_review.v2`
- `coverage_claim=explicit_normalized_snapshot_membership_only`
- `state=required_pending` only when `repeated_families` is non-empty;
  otherwise `not_required`
- `required_roles=[logic-agent, philosophy-agent]` only while pending;
  otherwise `[]`
- the existing v1 boundary classes and stop condition
- the existing eight v1 output fields plus
  `family_membership_assessment`, `set_relation_interpretation`,
  `abstraction_level`, `root_cause_hypothesis`, `recommended_resolution`, and
  `evidence_refs`
- `implementation_authority=false` and `merge_authority=false`

`family_repeat` contains exactly:

- the L1 source schema/policy versions, snapshot fingerprint, artifact
  fingerprint, and idempotency key;
- `trigger_rule=explicit_family_cardinality_gte_2`;
- `membership_source=explicit_input_only`;
- repeated family rows copied as exact `family_id` / `finding_ids` projections;
- unchanged L1 relation rows whose left or right endpoint is a repeated family;
- `unknown_findings_present`, a boolean projection of L1's separate
  `unknown_finding_ids` list.

No semantic or causal conclusion follows from a repeated family or relation
row. Those rows only scope human/role-agent review questions.

## Dispatch behavior

When `state=required_pending`, the active role set and order are exactly:

```text
agent-coordinator -> logic-agent -> philosophy-agent -> qa-engineer-agent -> bug-hunter -> security-auditor
```

No extra requested role is admitted. No implementation-owner flag is emitted.
Packet creation and manifest generation do not execute a role. Logic and
Philosophy remain analysis passes; QA, Bug Hunter, and Security preserve the
ordinary post-open sequence.

When `state=not_required`, no L2 dispatch order is authored and the ordinary
post-open tail remains unchanged. When the input flag is absent, the complete
v1 packet behavior, identity, and manifest remain unchanged.

Qoder accepts closed v1 and v2 branches. For v2 it validates the exact packet,
family-repeat, role, authority, phase, and dispatch shapes without recomputing
L1 relations or inferring any omitted fact.

## Identity and review outcomes

Input-free identity is the existing v1 identity. With input, identity is framed
from the existing base packet ID, canonical L1 `artifact_fingerprint`, the
fixed trigger rule, and a deterministic fingerprint of the exact closed
`invariant_review.v2` projection plus the exact canonical `required_context`
and primary/secondary/reviewer and requested-agent disposition projections.
Equivalent canonical L1 input replays therefore retain the same identity;
changing the canonical artifact, state, family-repeat rows, closed v2
projection, role context, or role assignment changes it. This is an internal
packet-identity check and does not recompute or validate L1 relations.
Control characters in the L2 base-identity text fields fail closed before the
legacy delimiter-framed base ID is used; the input-free v1 identity is
unchanged.

The closed recommendation vocabulary for role-agent output metadata is:

- `bounded_object_fix`
- `family_fix`
- `mechanism_fix`
- `authority_rescope`
- `no_change_required`
- `unknown_requires_human`

These labels are advisory review outcomes, not GitHub review-thread
dispositions. In particular, L2 uses `no_change_required`; it does not emit a
GitHub disposition, resolve a thread, or write fixed mapping.

## Security and non-goals

The lane adds no network, provider, subprocess, environment, workflow, public
API, product runtime, database, OpenAPI, frontend, iOS, learning, reflection,
KPP, oracle, mapping, thread-resolution, approval, promotion, or merge surface.
Raw review bodies, prompts, credentials, tokens, absolute local paths, and
provider payloads remain outside both input and packet output.

The second-materially-novel-carrier stop condition remains authoritative: a
new carrier that does not fit this finite explicit-membership projection stops
and requires a separately reviewed rescope instead of widening L2.

## Implementation evidence

- Safe input read and the sole L1 API call:
  `scripts.orchestration.task_bootstrap._read_invariant_family_relations_input`
- Exact family-repeat and v2 packet projections:
  `scripts.orchestration.task_bootstrap._build_family_repeat_projection` and
  `scripts.orchestration.task_bootstrap._build_invariant_review_v2_packet`
- Artifact/trigger/projection-bound packet identity:
  `scripts.orchestration.bootstrap_sync_policy.compute_invariant_family_review_packet_id`
- Active-role admission and exact dispatch selection:
  `scripts.orchestration.task_bootstrap.INVARIANT_FAMILY_REVIEW_ROLE_ORDER`
- Closed Qoder v2 validation without L1 recomputation:
  `scripts.orchestration.qoder_dispatch_bridge._validate_invariant_review_v2` and
  `scripts.orchestration.qoder_dispatch_bridge._validated_v2_dispatch_role_order`
