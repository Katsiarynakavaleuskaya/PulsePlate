"""Contract tests for the non-authoritative task normative envelope shadow."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from inspect import Parameter, signature
from typing import Literal, get_type_hints

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.task_normative_envelope_contract import (
    ActionReversibility,
    AssessmentState,
    CapabilityClaimV1,
    DelegatedAuthorityV1,
    NormativeBoundaryV1,
    TaskNormativeAssessmentV1,
    TaskNormativeEnvelopeV1,
    assess_task_normative_envelope,
    build_task_normative_envelope,
    task_normative_envelope_to_stable_mapping,
    validate_task_normative_envelope,
)

MISMATCH_REASONS = {
    "capability_action_exceeds_authority",
    "capability_scope_exceeds_authority",
    "parent_action_authority_widened",
    "parent_resource_scope_widened",
    "parent_obligation_dropped",
    "parent_prohibition_dropped",
    "parent_non_tradeable_constraint_dropped",
    "parent_delegation_forbidden",
    "parent_fingerprint_mismatch",
}
INSUFFICIENT_REASONS = {
    "missing_purpose_claim",
    "missing_objective",
    "missing_evaluation",
    "missing_capability_evidence",
    "missing_human_override",
    "missing_recovery_or_compensation",
    "missing_irreversible_approval_requirement",
}


def _boundary(
    *,
    obligations: tuple[str, ...] = ("norm:preserve",),
    prohibitions: tuple[str, ...] = ("norm:no_delete",),
    constraints: tuple[str, ...] = ("constraint:bounded",),
) -> NormativeBoundaryV1:
    return NormativeBoundaryV1(
        obligation_refs=obligations,
        prohibition_refs=prohibitions,
        non_tradeable_constraint_refs=constraints,
    )


def _authority(
    *,
    actions: tuple[str, ...] = ("action:read",),
    scopes: tuple[str, ...] = ("scope:packet",),
    basis: tuple[str, ...] = ("basis:operator",),
    delegation_allowed: bool = True,
) -> DelegatedAuthorityV1:
    return DelegatedAuthorityV1(
        action_classes=actions,
        resource_scope_refs=scopes,
        authority_basis_refs=basis,
        delegation_allowed=delegation_allowed,
    )


def _capability(
    *,
    actions: tuple[str, ...] = ("action:read",),
    scopes: tuple[str, ...] = ("scope:packet",),
    evidence: tuple[str, ...] = ("evidence:test",),
) -> CapabilityClaimV1:
    return CapabilityClaimV1(
        action_classes=actions,
        resource_scope_refs=scopes,
        evidence_refs=evidence,
    )


def _build(**overrides: object) -> TaskNormativeEnvelopeV1:
    arguments: dict[str, object] = {
        "task_packet_id": "packet:abc123",
        "purpose_claim_refs": ("purpose:ship",),
        "objective_refs": ("objective:bounded",),
        "normative_boundary": _boundary(),
        "delegated_authority": _authority(),
        "capability_claim": _capability(),
        "evaluation_refs": ("evaluation:focused_tests",),
        "approval_requirement_refs": (),
        "action_reversibility": "read_only",
        "human_override_ref": None,
        "recovery_or_compensation_ref": None,
    }
    arguments.update(overrides)
    return build_task_normative_envelope(**arguments)


def _child(parent: TaskNormativeEnvelopeV1, **overrides: object) -> TaskNormativeEnvelopeV1:
    arguments: dict[str, object] = {
        "task_packet_id": "packet:child",
        "purpose_claim_refs": ("purpose:ship",),
        "objective_refs": ("objective:bounded",),
        "normative_boundary": parent.normative_boundary,
        "delegated_authority": parent.delegated_authority,
        "capability_claim": parent.capability_claim,
        "evaluation_refs": ("evaluation:focused_tests",),
        "approval_requirement_refs": (),
        "action_reversibility": "read_only",
        "human_override_ref": None,
        "recovery_or_compensation_ref": None,
        "parent": parent,
    }
    arguments.update(overrides)
    return build_task_normative_envelope(**arguments)


def test_valid_read_only_root_is_consistent_and_non_authoritative() -> None:
    envelope = _build(
        normative_boundary=_boundary(
            obligations=("norm:shared",),
            prohibitions=("norm:shared",),
        ),
        delegated_authority=_authority(basis=()),
    )

    assessment = assess_task_normative_envelope(envelope)

    assert assessment.state == "consistent"
    assert assessment.reason_codes == ()
    assert envelope.execution_authority is False
    assert envelope.routing_authority is False
    assert envelope.approval_authority is False
    assert envelope.promotion_authority is False
    assert envelope.merge_authority is False
    assert assessment.blocking_authority is False
    assert assessment.merge_authority is False
    assert validate_task_normative_envelope(envelope) is None


def test_minimal_valid_root_uses_builder_defaults() -> None:
    parameters = signature(build_task_normative_envelope).parameters
    assert tuple(parameters) == (
        "task_packet_id",
        "purpose_claim_refs",
        "objective_refs",
        "normative_boundary",
        "delegated_authority",
        "capability_claim",
        "evaluation_refs",
        "approval_requirement_refs",
        "action_reversibility",
        "human_override_ref",
        "recovery_or_compensation_ref",
        "parent",
    )
    assert parameters["approval_requirement_refs"].default == ()
    assert parameters["action_reversibility"].default is Parameter.empty
    assert parameters["human_override_ref"].default is None
    assert parameters["recovery_or_compensation_ref"].default is None
    assert parameters["parent"].default is None

    envelope = build_task_normative_envelope(
        task_packet_id="packet:minimal",
        purpose_claim_refs=("purpose:ship",),
        objective_refs=("objective:bounded",),
        normative_boundary=_boundary(),
        delegated_authority=_authority(),
        capability_claim=_capability(),
        evaluation_refs=("evaluation:focused_tests",),
        action_reversibility="read_only",
    )

    assert envelope.approval_requirement_refs == ()
    assert envelope.human_override_ref is None
    assert envelope.recovery_or_compensation_ref is None
    assert envelope.parent_envelope_fingerprint is None


@pytest.mark.parametrize(
    ("capability_actions", "capability_scopes"),
    [
        (("action:read", "action:write"), ("scope:packet", "scope:report")),
        (("action:read",), ("scope:packet",)),
        ((), ()),
    ],
)
def test_equal_or_narrower_capability_is_consistent(
    capability_actions: tuple[str, ...],
    capability_scopes: tuple[str, ...],
) -> None:
    authority = _authority(
        actions=("action:read", "action:write"),
        scopes=("scope:packet", "scope:report"),
    )
    capability = _capability(actions=capability_actions, scopes=capability_scopes)

    assessment = assess_task_normative_envelope(
        _build(delegated_authority=authority, capability_claim=capability)
    )

    assert assessment.state == "consistent"


def test_valid_child_narrows_authority_and_adds_norms() -> None:
    parent = _build(
        normative_boundary=_boundary(
            obligations=("norm:preserve",),
            prohibitions=("norm:no_delete",),
            constraints=("constraint:bounded",),
        ),
        delegated_authority=_authority(
            actions=("action:read", "action:write"),
            scopes=("scope:packet", "scope:report"),
        ),
        capability_claim=_capability(actions=("action:read",), scopes=("scope:packet",)),
        approval_requirement_refs=("approval:operator",),
        action_reversibility="irreversible_change",
        human_override_ref="control:human_override",
        recovery_or_compensation_ref="control:compensation",
    )
    child = _child(
        parent,
        normative_boundary=_boundary(
            obligations=("norm:preserve", "norm:report"),
            prohibitions=("norm:no_delete", "norm:no_publish"),
            constraints=("constraint:bounded", "constraint:offline"),
        ),
        delegated_authority=_authority(actions=("action:read",), scopes=("scope:packet",)),
        capability_claim=_capability(actions=("action:read",), scopes=("scope:packet",)),
    )

    assessment = assess_task_normative_envelope(child, parent=parent)

    assert assessment.state == "consistent"
    assert assessment.reason_codes == ()


@pytest.mark.parametrize(
    ("reversibility", "approval_refs", "override_ref", "recovery_ref"),
    [
        ("reversible_change", (), "control:human_override", "control:rollback"),
        (
            "irreversible_change",
            ("approval:operator",),
            "control:human_override",
            "control:compensation",
        ),
    ],
)
def test_valid_change_controls_are_consistent(
    reversibility: ActionReversibility,
    approval_refs: tuple[str, ...],
    override_ref: str,
    recovery_ref: str,
) -> None:
    assessment = assess_task_normative_envelope(
        _build(
            action_reversibility=reversibility,
            approval_requirement_refs=approval_refs,
            human_override_ref=override_ref,
            recovery_or_compensation_ref=recovery_ref,
        )
    )

    assert assessment.state == "consistent"


def test_local_capability_action_and_scope_excess_are_witnessed() -> None:
    envelope = _build(
        delegated_authority=_authority(actions=("action:read",), scopes=("scope:packet",)),
        capability_claim=_capability(
            actions=("action:delete", "action:read"),
            scopes=("scope:packet", "scope:secrets"),
        ),
    )

    assessment = assess_task_normative_envelope(envelope)

    assert assessment.state == "mismatch"
    assert assessment.reason_codes == (
        "capability_action_exceeds_authority",
        "capability_scope_exceeds_authority",
    )
    assert assessment.excess_action_classes == ("action:delete",)
    assert assessment.excess_resource_scope_refs == ("scope:secrets",)


def test_parent_action_and_scope_widening_are_witnessed() -> None:
    parent = _build()
    child = _child(
        parent,
        delegated_authority=_authority(
            actions=("action:read", "action:write"),
            scopes=("scope:packet", "scope:report"),
        ),
        capability_claim=_capability(actions=("action:read",), scopes=("scope:packet",)),
    )

    assessment = assess_task_normative_envelope(child, parent=parent)

    assert assessment.reason_codes == (
        "parent_action_authority_widened",
        "parent_resource_scope_widened",
    )
    assert assessment.excess_action_classes == ("action:write",)
    assert assessment.excess_resource_scope_refs == ("scope:report",)


@pytest.mark.parametrize(
    ("boundary", "reason", "witness_field", "witness"),
    [
        (
            _boundary(obligations=()),
            "parent_obligation_dropped",
            "dropped_obligation_refs",
            ("norm:preserve",),
        ),
        (
            _boundary(prohibitions=()),
            "parent_prohibition_dropped",
            "dropped_prohibition_refs",
            ("norm:no_delete",),
        ),
        (
            _boundary(constraints=()),
            "parent_non_tradeable_constraint_dropped",
            "dropped_non_tradeable_constraint_refs",
            ("constraint:bounded",),
        ),
    ],
)
def test_parent_norm_drops_are_independently_classified(
    boundary: NormativeBoundaryV1,
    reason: str,
    witness_field: str,
    witness: tuple[str, ...],
) -> None:
    parent = _build()
    assessment = assess_task_normative_envelope(
        _child(parent, normative_boundary=boundary),
        parent=parent,
    )

    assert assessment.state == "mismatch"
    assert assessment.reason_codes == (reason,)
    assert getattr(assessment, witness_field) == witness


def test_non_delegable_parent_is_a_mismatch() -> None:
    parent = _build(delegated_authority=_authority(delegation_allowed=False))
    child = _child(parent)

    assessment = assess_task_normative_envelope(child, parent=parent)

    assert assessment.reason_codes == ("parent_delegation_forbidden",)


def test_parent_argument_must_match_root_or_bound_shape() -> None:
    parent = _build()
    child = _child(parent)

    with pytest.raises(ValueError, match="parent"):
        assess_task_normative_envelope(child)
    with pytest.raises(ValueError, match="parent"):
        assess_task_normative_envelope(parent, parent=parent)


def test_structurally_invalid_parent_raises_before_assessment() -> None:
    parent = _build()
    child = _child(parent)
    tampered_parent = replace(parent, envelope_fingerprint="sha256:" + "0" * 64)

    with pytest.raises(ValueError, match="fingerprint"):
        assess_task_normative_envelope(child, parent=tampered_parent)
    with pytest.raises(ValueError, match="fingerprint"):
        _build(parent=tampered_parent)


def test_wrong_valid_parent_only_adds_fingerprint_mismatch() -> None:
    expected_parent = _build(task_packet_id="packet:expected")
    wrong_parent = _build(
        task_packet_id="packet:wrong",
        delegated_authority=_authority(actions=(), scopes=(), delegation_allowed=False),
        normative_boundary=_boundary(obligations=(), prohibitions=(), constraints=()),
        capability_claim=_capability(actions=(), scopes=(), evidence=()),
    )
    child = _child(expected_parent)

    assessment = assess_task_normative_envelope(child, parent=wrong_parent)

    assert assessment.state == "mismatch"
    assert assessment.reason_codes == ("parent_fingerprint_mismatch",)
    assert assessment.excess_action_classes == ()
    assert assessment.excess_resource_scope_refs == ()
    assert assessment.dropped_obligation_refs == ()
    assert assessment.dropped_prohibition_refs == ()
    assert assessment.dropped_non_tradeable_constraint_refs == ()


def test_exact_parent_witnesses_union_local_and_parent_excess() -> None:
    parent = _build()
    child = _child(
        parent,
        delegated_authority=_authority(
            actions=("action:read", "action:write"),
            scopes=("scope:packet", "scope:report"),
        ),
        capability_claim=_capability(
            actions=("action:delete", "action:read"),
            scopes=("scope:packet", "scope:secrets"),
        ),
    )

    assessment = assess_task_normative_envelope(child, parent=parent)

    assert assessment.excess_action_classes == ("action:delete", "action:write")
    assert assessment.excess_resource_scope_refs == ("scope:report", "scope:secrets")


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"purpose_claim_refs": ()}, "missing_purpose_claim"),
        ({"objective_refs": ()}, "missing_objective"),
        ({"evaluation_refs": ()}, "missing_evaluation"),
        (
            {"capability_claim": _capability(evidence=())},
            "missing_capability_evidence",
        ),
        (
            {"capability_claim": _capability(actions=(), scopes=(), evidence=())},
            None,
        ),
    ],
)
def test_missing_claim_and_capability_evidence_rules(
    overrides: dict[str, object],
    reason: str | None,
) -> None:
    assessment = assess_task_normative_envelope(_build(**overrides))

    if reason is None:
        assert assessment.state == "consistent"
        assert assessment.reason_codes == ()
    else:
        assert assessment.state == "insufficient_evidence"
        assert assessment.reason_codes == (reason,)


@pytest.mark.parametrize(
    ("overrides", "reasons"),
    [
        (
            {"action_reversibility": "reversible_change"},
            ("missing_human_override", "missing_recovery_or_compensation"),
        ),
        (
            {"action_reversibility": "irreversible_change"},
            (
                "missing_human_override",
                "missing_irreversible_approval_requirement",
                "missing_recovery_or_compensation",
            ),
        ),
        (
            {
                "action_reversibility": "irreversible_change",
                "human_override_ref": "control:human_override",
                "recovery_or_compensation_ref": "control:compensation",
            },
            ("missing_irreversible_approval_requirement",),
        ),
    ],
)
def test_missing_change_controls_are_independent(
    overrides: dict[str, object],
    reasons: tuple[str, ...],
) -> None:
    assessment = assess_task_normative_envelope(_build(**overrides))

    assert assessment.state == "insufficient_evidence"
    assert assessment.reason_codes == reasons


def test_mismatch_precedes_independent_insufficient_evidence() -> None:
    envelope = _build(
        purpose_claim_refs=(),
        evaluation_refs=(),
        delegated_authority=_authority(actions=(), scopes=()),
        capability_claim=_capability(
            actions=("action:write",), scopes=("scope:report",), evidence=()
        ),
    )

    assessment = assess_task_normative_envelope(envelope)

    assert assessment.state == "mismatch"
    assert set(assessment.reason_codes) == {
        "capability_action_exceeds_authority",
        "capability_scope_exceeds_authority",
        "missing_capability_evidence",
        "missing_evaluation",
        "missing_purpose_claim",
    }


def test_reason_codes_are_lexicographically_sorted_unique_and_closed() -> None:
    envelope = _build(
        purpose_claim_refs=(),
        objective_refs=(),
        evaluation_refs=(),
        action_reversibility="irreversible_change",
        delegated_authority=_authority(actions=(), scopes=()),
        capability_claim=_capability(
            actions=("action:write",), scopes=("scope:report",), evidence=()
        ),
    )

    reasons = assess_task_normative_envelope(envelope).reason_codes

    assert reasons == tuple(sorted(set(reasons)))
    assert set(reasons) <= MISMATCH_REASONS | INSUFFICIENT_REASONS
    assert len(MISMATCH_REASONS | INSUFFICIENT_REASONS) == 16


def test_permutations_duplicates_and_builder_trimming_preserve_fingerprint() -> None:
    canonical = _build(
        purpose_claim_refs=("purpose:one", "purpose:two"),
        delegated_authority=_authority(
            actions=("action:read", "action:write"),
            scopes=("scope:packet", "scope:report"),
        ),
    )
    normalized = _build(
        task_packet_id="\u2003packet:abc123\u2003",
        purpose_claim_refs=(" purpose:two ", "purpose:one", "purpose:two"),
        delegated_authority=_authority(
            actions=(" action:write ", "action:read", "action:write"),
            scopes=("scope:report", " scope:packet ", "scope:report"),
            basis=("basis:operator", " basis:operator "),
        ),
    )

    assert normalized == canonical
    assert normalized.envelope_fingerprint == canonical.envelope_fingerprint


def test_semantic_field_change_changes_fingerprint() -> None:
    baseline = _build()
    changed = _build(objective_refs=("objective:different",))

    assert changed.envelope_fingerprint != baseline.envelope_fingerprint


def test_stable_mapping_is_json_ready_and_excludes_only_fingerprint() -> None:
    envelope = _build()

    complete = task_normative_envelope_to_stable_mapping(envelope)
    identity = task_normative_envelope_to_stable_mapping(envelope, include_fingerprint=False)

    assert json.loads(json.dumps(complete, sort_keys=True)) == complete
    assert complete["normative_boundary"]["obligation_refs"] == ["norm:preserve"]
    assert complete["delegated_authority"]["action_classes"] == ["action:read"]
    assert complete["capability_claim"]["evidence_refs"] == ["evidence:test"]
    assert complete["parent_envelope_fingerprint"] is None
    assert complete["execution_authority"] is False
    assert complete["envelope_fingerprint"] == envelope.envelope_fingerprint
    assert set(complete) - set(identity) == {"envelope_fingerprint"}
    assert identity == {
        key: value for key, value in complete.items() if key != "envelope_fingerprint"
    }


@pytest.mark.parametrize(
    "mutator",
    [
        lambda envelope: replace(envelope, purpose_claim_refs=["purpose:ship"]),
        lambda envelope: replace(
            envelope,
            purpose_claim_refs=("purpose:ship", "purpose:ship"),
        ),
        lambda envelope: replace(
            envelope,
            purpose_claim_refs=("purpose:z", "purpose:a"),
        ),
        lambda envelope: replace(envelope, purpose_claim_refs=(" purpose:ship ",)),
        lambda envelope: replace(envelope, normative_boundary={"obligation_refs": []}),
        lambda envelope: replace(envelope, action_reversibility="sometimes"),
        lambda envelope: replace(envelope, schema_version="task_normative_envelope.v2"),
        lambda envelope: replace(envelope, policy_version="other-policy.v1"),
    ],
)
def test_direct_noncanonical_dataclass_is_rejected(mutator: object) -> None:
    envelope = _build()
    malformed = mutator(envelope)

    with pytest.raises(ValueError):
        validate_task_normative_envelope(malformed)
    with pytest.raises(ValueError):
        task_normative_envelope_to_stable_mapping(malformed)


@pytest.mark.parametrize(
    ("field_name", "raw_value"),
    [
        ("purpose_claim_refs", "not_namespaced"),
        ("purpose_claim_refs", "1bad:value"),
        ("purpose_claim_refs", "purpose:_bad"),
        ("purpose_claim_refs", "bad/value:ref"),
        ("purpose_claim_refs", "bad\\value:ref"),
        ("purpose_claim_refs", "purpose:internal space"),
        ("purpose_claim_refs", "purpose:na\u00efve"),
        ("purpose_claim_refs", "purpose:bad\nref"),
        ("purpose_claim_refs", "purpose:bad\tref"),
        ("purpose_claim_refs", "\npurpose:outer"),
        ("purpose_claim_refs", "\tpurpose:outer"),
        ("purpose_claim_refs", "purpose:trimmed\x7f"),
        ("purpose_claim_refs", " " * 3),
        ("purpose_claim_refs", "N" * 32 + ":" + "v" * 96),
        ("task_packet_id", "bad/packet"),
        ("task_packet_id", "bad packet"),
        ("task_packet_id", "p\u00e4cket"),
        ("task_packet_id", "packet\ninternal"),
        ("task_packet_id", "\npacket"),
        ("task_packet_id", "\tpacket"),
        ("task_packet_id", "P" * 129),
        ("human_override_ref", "\ncontrol:human_override"),
        ("recovery_or_compensation_ref", "\tcontrol:rollback"),
        ("action_reversibility", "\tread_only"),
        ("action_reversibility", "read_only\x7f"),
        ("action_reversibility", " read_only "),
        ("action_reversibility", "\u2003read_only\u2003"),
    ],
)
def test_invalid_identifiers_fail_without_echoing_rejected_value(
    field_name: str,
    raw_value: str,
) -> None:
    value: object = (raw_value,) if field_name == "purpose_claim_refs" else raw_value

    with pytest.raises(ValueError) as exc_info:
        _build(**{field_name: value})

    assert raw_value not in str(exc_info.value)


def test_identifier_length_boundaries_are_accepted_and_case_is_preserved() -> None:
    boundary_ref = "N" * 32 + ":" + "V" * 95
    boundary_packet_id = "P" * 128

    envelope = _build(
        task_packet_id=boundary_packet_id,
        purpose_claim_refs=(boundary_ref,),
    )

    assert envelope.purpose_claim_refs == (boundary_ref,)
    assert envelope.task_packet_id == boundary_packet_id
    assert len(boundary_ref) == 128
    assert len(boundary_packet_id) == 128


class _StringSubclass(str):
    pass


class _FalseyAuthority:
    def __bool__(self) -> bool:
        return False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda envelope: replace(
            envelope,
            delegated_authority=replace(envelope.delegated_authority, delegation_allowed=0),
        ),
        lambda envelope: replace(envelope, task_packet_id=_StringSubclass("packet:abc123")),
        lambda envelope: replace(envelope, execution_authority=0),
        lambda envelope: replace(envelope, routing_authority=_FalseyAuthority()),
    ],
)
def test_bool_as_int_string_subclass_and_falsey_authority_impostors_are_rejected(
    mutator: object,
) -> None:
    envelope = _build()
    malformed = mutator(envelope)

    with pytest.raises(ValueError):
        validate_task_normative_envelope(malformed)


def test_recomputed_fingerprint_does_not_authorize_falsey_flag() -> None:
    envelope = _build()
    identity = task_normative_envelope_to_stable_mapping(envelope, include_fingerprint=False)
    identity["execution_authority"] = 0
    malformed = replace(
        envelope,
        execution_authority=0,
        envelope_fingerprint=fingerprint_payload(identity),
    )

    with pytest.raises(ValueError, match="execution_authority"):
        validate_task_normative_envelope(malformed)


@pytest.mark.parametrize(
    "fingerprint",
    [
        "sha256:" + "0" * 64,
        " SHA256:" + "A" * 64 + " ",
        "sha256:short",
    ],
)
def test_tampered_or_noncanonical_fingerprints_are_rejected(fingerprint: str) -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        validate_task_normative_envelope(replace(_build(), envelope_fingerprint=fingerprint))


def test_exact_dataclass_field_inventory_and_literal_false_authority() -> None:
    assert (
        ActionReversibility
        == Literal[
            "read_only",
            "reversible_change",
            "irreversible_change",
        ]
    )
    assert (
        AssessmentState
        == Literal[
            "consistent",
            "mismatch",
            "insufficient_evidence",
        ]
    )
    assert tuple(field.name for field in fields(NormativeBoundaryV1)) == (
        "obligation_refs",
        "prohibition_refs",
        "non_tradeable_constraint_refs",
    )
    assert tuple(field.name for field in fields(DelegatedAuthorityV1)) == (
        "action_classes",
        "resource_scope_refs",
        "authority_basis_refs",
        "delegation_allowed",
    )
    assert tuple(field.name for field in fields(CapabilityClaimV1)) == (
        "action_classes",
        "resource_scope_refs",
        "evidence_refs",
    )
    assert tuple(field.name for field in fields(TaskNormativeEnvelopeV1)) == (
        "schema_version",
        "policy_version",
        "task_packet_id",
        "purpose_claim_refs",
        "objective_refs",
        "normative_boundary",
        "delegated_authority",
        "capability_claim",
        "evaluation_refs",
        "approval_requirement_refs",
        "action_reversibility",
        "human_override_ref",
        "recovery_or_compensation_ref",
        "parent_envelope_fingerprint",
        "envelope_fingerprint",
        "execution_authority",
        "routing_authority",
        "approval_authority",
        "promotion_authority",
        "merge_authority",
    )
    assert tuple(field.name for field in fields(TaskNormativeAssessmentV1)) == (
        "state",
        "reason_codes",
        "excess_action_classes",
        "excess_resource_scope_refs",
        "dropped_obligation_refs",
        "dropped_prohibition_refs",
        "dropped_non_tradeable_constraint_refs",
        "blocking_authority",
        "merge_authority",
    )

    envelope_hints = get_type_hints(TaskNormativeEnvelopeV1)
    assessment_hints = get_type_hints(TaskNormativeAssessmentV1)
    validator_hints = get_type_hints(validate_task_normative_envelope)
    assert envelope_hints["schema_version"] == Literal["task_normative_envelope.v1"]
    assert envelope_hints["policy_version"] == Literal["task-normative-envelope-policy.v1"]
    assert validator_hints["return"] is type(None)
    for field_name in (
        "execution_authority",
        "routing_authority",
        "approval_authority",
        "promotion_authority",
        "merge_authority",
    ):
        assert envelope_hints[field_name] == Literal[False]
    for field_name in ("blocking_authority", "merge_authority"):
        assert assessment_hints[field_name] == Literal[False]

    assessment_fields = {field.name: field for field in fields(TaskNormativeAssessmentV1)}
    assessment_parameters = signature(TaskNormativeAssessmentV1).parameters
    assessment = assess_task_normative_envelope(_build())
    assessment_arguments: dict[str, object] = {
        "state": "consistent",
        "reason_codes": (),
        "excess_action_classes": (),
        "excess_resource_scope_refs": (),
        "dropped_obligation_refs": (),
        "dropped_prohibition_refs": (),
        "dropped_non_tradeable_constraint_refs": (),
    }
    for field_name in ("blocking_authority", "merge_authority"):
        assert assessment_fields[field_name].init is False
        assert field_name not in assessment_parameters
        with pytest.raises(TypeError):
            TaskNormativeAssessmentV1(**assessment_arguments, **{field_name: True})
        with pytest.raises(TypeError):
            replace(assessment, **{field_name: True})
    assert assessment.blocking_authority is False
    assert assessment.merge_authority is False
