# Task Normative Envelope V1 Shadow Contract

Status: bounded shadow contract; non-authoritative; no runtime integration.

## Purpose

`TaskNormativeEnvelopeV1` is a deterministic, offline description of one task's
declared purpose, norms, delegated authority, capability evidence, evaluation,
and change controls. It can identify a finite set of local or immediate-parent
inconsistencies. It cannot execute, route, approve, promote, block, or merge
anything.

The implementation is the pure library
`scripts/orchestration/task_normative_envelope_contract.py`. It has no CLI,
filesystem access, logging, network calls, subprocesses, provider calls, or
integration with `task_bootstrap.py`, agent dispatch, review governance, CI, or
product runtime.

## Frozen data model

The v1 model has exactly five frozen slot dataclasses.

### `NormativeBoundaryV1`

- `obligation_refs: tuple[str, ...]`
- `prohibition_refs: tuple[str, ...]`
- `non_tradeable_constraint_refs: tuple[str, ...]`

### `DelegatedAuthorityV1`

- `action_classes: tuple[str, ...]`
- `resource_scope_refs: tuple[str, ...]`
- `authority_basis_refs: tuple[str, ...]`
- `delegation_allowed: bool`

An empty `authority_basis_refs` tuple is valid. V1 records the references but
does not make their presence an assessment requirement.

### `CapabilityClaimV1`

- `action_classes: tuple[str, ...]`
- `resource_scope_refs: tuple[str, ...]`
- `evidence_refs: tuple[str, ...]`

### `TaskNormativeEnvelopeV1`

- `schema_version`
- `policy_version`
- `task_packet_id`
- `purpose_claim_refs`
- `objective_refs`
- `normative_boundary`
- `delegated_authority`
- `capability_claim`
- `evaluation_refs`
- `approval_requirement_refs`
- `action_reversibility`
- `human_override_ref`
- `recovery_or_compensation_ref`
- `parent_envelope_fingerprint`
- `envelope_fingerprint`
- `execution_authority: Literal[False]`
- `routing_authority: Literal[False]`
- `approval_authority: Literal[False]`
- `promotion_authority: Literal[False]`
- `merge_authority: Literal[False]`

The schema version is `task_normative_envelope.v1`. The policy version is
`task-normative-envelope-policy.v1`.

`action_reversibility` is exactly one of:

- `read_only`
- `reversible_change`
- `irreversible_change`

### `TaskNormativeAssessmentV1`

- `state`
- `reason_codes`
- `excess_action_classes`
- `excess_resource_scope_refs`
- `dropped_obligation_refs`
- `dropped_prohibition_refs`
- `dropped_non_tradeable_constraint_refs`
- `blocking_authority: Literal[False]`
- `merge_authority: Literal[False]`

`state` is exactly one of `consistent`, `mismatch`, or
`insufficient_evidence`.

## Public operations

The module exposes exactly four public functions:

1. `build_task_normative_envelope(...)`
2. `task_normative_envelope_to_stable_mapping(...)`
3. `validate_task_normative_envelope(...)`
4. `assess_task_normative_envelope(...)`

The builder is the normalization boundary for references and task packet IDs.
It does not normalize `action_reversibility`: control characters, `DEL`, and
values that require outer trimming are invalid. The validator accepts only an
already canonical envelope, returns `None`, and does not repair direct dataclass
construction. The stable-mapping function validates before projecting. The
builder accepts an optional structurally valid `parent` envelope and derives
`parent_envelope_fingerprint` only from that parent; callers cannot provide a
raw parent fingerprint.

The builder's keyword-only tail is frozen in this order: optional
`approval_requirement_refs=()`, required `action_reversibility`, optional
`human_override_ref=None`, optional `recovery_or_compensation_ref=None`, and
optional `parent=None`. Python permits the required keyword-only reversibility
argument to follow the defaulted approval tuple; it must not acquire a default.

## Token grammar and canonicalization

Every reference uses this ASCII grammar:

```text
[A-Za-z][A-Za-z0-9_.-]{0,31}:[A-Za-z0-9][A-Za-z0-9_.:-]{0,94}
```

Every task packet ID uses this ASCII grammar:

```text
[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}
```

Before trimming, the builder rejects every C0 control character (`U+0000`–
`U+001F`) and `DEL` (`U+007F`) in every reference, optional reference, and task
packet ID. It then strips other outer whitespace, validates the resulting
token, and sorts and deduplicates every reference tuple. It preserves case.
Direct validation requires exact built-in types and canonical values: tuples
cannot be lists, string subclasses are rejected, and reference tuples cannot
contain duplicate, unsorted, or untrimmed values.

Validation errors are category-only. They do not include rejected identifiers,
references, or other raw field values.

## Stable mapping and fingerprint

The stable mapping is an explicit JSON-ready dictionary. Nested dataclasses are
projected into explicit dictionaries and tuples are projected into lists. The
identity mapping contains every envelope field except `envelope_fingerprint`.

`envelope_fingerprint` is computed with the shared
`core.evidence.fingerprints.fingerprint_payload` helper over that identity
mapping. Fingerprint syntax is checked through the shared
`core.evidence.policies.validate_fingerprint` helper, and direct validation
also requires the supplied value to already be canonical and to equal the
recomputed identity fingerprint.

All five envelope authority flags are literal `False` and participate in the
fingerprinted identity. False-like substitutes such as `0` or an object with a
false boolean value are invalid. Assessment authority flags are also literal
`False`.

The builder first constructs an internal temporary envelope with an empty
fingerprint, fingerprints the explicit private unchecked identity mapping,
replaces only the fingerprint field, validates the completed envelope, and then
returns it. The public mapping function is never used to fingerprint that
temporary object because the public function must reject invalid envelopes.

## Root and child examples

The root omits `parent`. The child passes the validated parent object; it never
copies a raw fingerprint into the builder.

```python
from scripts.orchestration.task_normative_envelope_contract import (
    CapabilityClaimV1,
    DelegatedAuthorityV1,
    NormativeBoundaryV1,
    build_task_normative_envelope,
)

boundary = NormativeBoundaryV1(
    obligation_refs=("norm:preserve",),
    prohibition_refs=("norm:no_delete",),
    non_tradeable_constraint_refs=("constraint:bounded",),
)
authority = DelegatedAuthorityV1(
    action_classes=("action:read",),
    resource_scope_refs=("scope:packet",),
    authority_basis_refs=(),
    delegation_allowed=True,
)
capability = CapabilityClaimV1(
    action_classes=("action:read",),
    resource_scope_refs=("scope:packet",),
    evidence_refs=("evidence:test",),
)

root = build_task_normative_envelope(
    task_packet_id="packet:root",
    purpose_claim_refs=("purpose:review",),
    objective_refs=("objective:bounded",),
    normative_boundary=boundary,
    delegated_authority=authority,
    capability_claim=capability,
    evaluation_refs=("evaluation:focused_tests",),
    approval_requirement_refs=(),
    action_reversibility="read_only",
    human_override_ref=None,
    recovery_or_compensation_ref=None,
)

child = build_task_normative_envelope(
    task_packet_id="packet:child",
    purpose_claim_refs=("purpose:review",),
    objective_refs=("objective:bounded",),
    normative_boundary=boundary,
    delegated_authority=authority,
    capability_claim=capability,
    evaluation_refs=("evaluation:focused_tests",),
    approval_requirement_refs=(),
    action_reversibility="read_only",
    human_override_ref=None,
    recovery_or_compensation_ref=None,
    parent=root,
)
```

## Local assessment

Capability action classes must be a subset of delegated action classes.
Capability resource scopes must be a subset of delegated resource scopes.
Non-empty capability action or scope claims require at least one capability
evidence reference.

A task requires at least one purpose claim, objective, and evaluation reference.
A `reversible_change` requires a human override and recovery or compensation
reference. An `irreversible_change` requires those two controls and at least one
approval requirement reference.

When both mismatch and insufficient-evidence reasons exist, the state is
`mismatch`. Otherwise any insufficient-evidence reason produces
`insufficient_evidence`; no reasons produces `consistent`. Reason codes and
witnesses are sorted and deduplicated.

## Immediate-parent assessment

A root envelope has no parent fingerprint and must be assessed without a
parent. A parent-bound envelope has a parent fingerprint and must be assessed
with a structurally valid parent. Either shape mismatch raises `ValueError`.

If the supplied valid parent's fingerprint does not match the child's binding,
assessment adds `parent_fingerprint_mismatch` and skips every parent comparison.
Local checks still run.

If the fingerprint matches exactly, v1 performs only these finite comparisons:

- child delegated action classes cannot widen the parent's action classes;
- child resource scopes cannot widen the parent's resource scopes;
- child obligations cannot drop parent obligations;
- child prohibitions cannot drop parent prohibitions;
- child non-tradeable constraints cannot drop parent constraints; and
- a parent with `delegation_allowed=False` cannot delegate the child.

Comparisons use set membership. Only the immediate supplied parent is inspected;
there is no recursive ancestry traversal.

## Frozen reasons and witnesses

The nine mismatch reasons are exactly:

- `capability_action_exceeds_authority`
- `capability_scope_exceeds_authority`
- `parent_action_authority_widened`
- `parent_resource_scope_widened`
- `parent_obligation_dropped`
- `parent_prohibition_dropped`
- `parent_non_tradeable_constraint_dropped`
- `parent_delegation_forbidden`
- `parent_fingerprint_mismatch`

The seven insufficient-evidence reasons are exactly:

- `missing_purpose_claim`
- `missing_objective`
- `missing_evaluation`
- `missing_capability_evidence`
- `missing_human_override`
- `missing_recovery_or_compensation`
- `missing_irreversible_approval_requirement`

The five witness fields are exactly:

- `excess_action_classes`
- `excess_resource_scope_refs`
- `dropped_obligation_refs`
- `dropped_prohibition_refs`
- `dropped_non_tradeable_constraint_refs`

V1 does not add an authority-basis requirement, a norm-conflict classifier, a
parent reversibility comparison, another reason code, or another witness.

## Authority and integration boundary

The envelope and assessment are advisory shadow artifacts only. A valid or
`consistent` result does not prove that an action is correct, safe, complete,
approved, authorized, or mergeable. It grants no coordinator, dispatcher,
review, security, CI, GitHub, product-runtime, or human authority.

N1 explicitly excludes:

- `task_bootstrap.py`, coordinator, dispatcher, role, or agent integration;
- product runtime, routes, API/OpenAPI, web, iOS, provider, quota, or rate limits;
- CI, review disposition, fixed mapping, branch protection, or merge gates;
- execution, routing, approval, promotion, blocking, merge, or human authority;
- recursive ancestry, graph traversal, or transitive parent inference;
- free-text or semantic interpretation of purpose, norms, authority, or evidence;
- persistence, JSON schemas, artifact writers, databases, migrations, telemetry,
  Evidence Graph, advisory wiki, workforce memory, RAG, or semantic cache;
- policy expansion, norm-conflict adjudication, authority-basis requirements,
  parent reversibility comparison, or additional reasons or witnesses; and
- CLI, filesystem, logging, network, subprocess, provider, or external-write
  behavior.

Every excluded surface requires a separate reviewed lane. Nothing in N1 implies
that such a lane is approved.

## Empirical gates for N2 and N3

The sequence is exact:

```text
N1 internal shadow contract
-> 3-5 sanitized completed trajectories
-> GO / DEFER / STOP
-> N2 consumer inventory only after GO
-> N3 read-only lineage projection only after sufficient outcomes
```

Trajectories must be completed and sanitized. They must not include raw task
prose, prompts, responses, secrets, personal data, local paths, or provider
payloads. N1 does not persist or collect them; any evidence handling belongs to
a separately governed review process.

The decision is `GO` if and only if all four conditions hold:

1. At least one previously implicit authority or corrigibility mismatch is found.
2. There is no more than one false positive.
3. No semantic prose interpretation is required.
4. The reviewer judges the assessment more useful than a simple task-packet check.

The decision is `DEFER` or `STOP` if any of these conditions holds:

1. Five cases yield zero novel mismatch.
2. More than one false positive is observed.
3. Utility requires free-text interpretation.

`GO` authorizes only an N2 consumer inventory. It does not authorize a consumer,
integration, enforcement, or runtime change. N3 may be considered only after
sufficient later outcomes and is limited to a read-only lineage projection.

## Rollback

Before any consumer exists, rollback is deletion of the pure module, its focused
tests, this contract document, and the isolated umbrella ledger entry. N1 has no
consumer and no persisted artifact, so rollback requires no runtime-state or
data migration.
