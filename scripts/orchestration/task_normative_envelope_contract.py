"""Pure contract for the non-authoritative task normative envelope v1 shadow."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Literal, cast

from core.evidence.fingerprints import JsonValue, fingerprint_payload
from core.evidence.policies import validate_fingerprint

ActionReversibility = Literal[
    "read_only",
    "reversible_change",
    "irreversible_change",
]
AssessmentState = Literal[
    "consistent",
    "mismatch",
    "insufficient_evidence",
]
_ReasonCode = Literal[
    "capability_action_exceeds_authority",
    "capability_scope_exceeds_authority",
    "parent_action_authority_widened",
    "parent_resource_scope_widened",
    "parent_obligation_dropped",
    "parent_prohibition_dropped",
    "parent_non_tradeable_constraint_dropped",
    "parent_delegation_forbidden",
    "parent_fingerprint_mismatch",
    "missing_purpose_claim",
    "missing_objective",
    "missing_evaluation",
    "missing_capability_evidence",
    "missing_human_override",
    "missing_recovery_or_compensation",
    "missing_irreversible_approval_requirement",
]

_SCHEMA_VERSION: Literal["task_normative_envelope.v1"] = "task_normative_envelope.v1"
_POLICY_VERSION: Literal["task-normative-envelope-policy.v1"] = "task-normative-envelope-policy.v1"
_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,31}:[A-Za-z0-9][A-Za-z0-9_.:-]{0,94}")
_TASK_PACKET_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_ACTION_REVERSIBILITY_VALUES: tuple[ActionReversibility, ...] = (
    "read_only",
    "reversible_change",
    "irreversible_change",
)


@dataclass(frozen=True, slots=True)
class NormativeBoundaryV1:
    """Declared obligations, prohibitions, and non-tradeable constraints."""

    obligation_refs: tuple[str, ...]
    prohibition_refs: tuple[str, ...]
    non_tradeable_constraint_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DelegatedAuthorityV1:
    """Bounded authority delegated to the task."""

    action_classes: tuple[str, ...]
    resource_scope_refs: tuple[str, ...]
    authority_basis_refs: tuple[str, ...]
    delegation_allowed: bool


@dataclass(frozen=True, slots=True)
class CapabilityClaimV1:
    """Claimed capability and its evidence references."""

    action_classes: tuple[str, ...]
    resource_scope_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TaskNormativeEnvelopeV1:
    """Deterministic, non-authoritative task envelope."""

    schema_version: Literal["task_normative_envelope.v1"]
    policy_version: Literal["task-normative-envelope-policy.v1"]
    task_packet_id: str
    purpose_claim_refs: tuple[str, ...]
    objective_refs: tuple[str, ...]
    normative_boundary: NormativeBoundaryV1
    delegated_authority: DelegatedAuthorityV1
    capability_claim: CapabilityClaimV1
    evaluation_refs: tuple[str, ...]
    approval_requirement_refs: tuple[str, ...]
    action_reversibility: ActionReversibility
    human_override_ref: str | None
    recovery_or_compensation_ref: str | None
    parent_envelope_fingerprint: str | None
    envelope_fingerprint: str
    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    approval_authority: Literal[False] = False
    promotion_authority: Literal[False] = False
    merge_authority: Literal[False] = False


@dataclass(frozen=True, slots=True)
class TaskNormativeAssessmentV1:
    """Advisory consistency assessment with bounded mismatch witnesses."""

    state: AssessmentState
    reason_codes: tuple[_ReasonCode, ...]
    excess_action_classes: tuple[str, ...]
    excess_resource_scope_refs: tuple[str, ...]
    dropped_obligation_refs: tuple[str, ...]
    dropped_prohibition_refs: tuple[str, ...]
    dropped_non_tradeable_constraint_refs: tuple[str, ...]
    blocking_authority: Literal[False] = field(default=False, init=False)
    merge_authority: Literal[False] = field(default=False, init=False)


def build_task_normative_envelope(
    *,
    task_packet_id: str,
    purpose_claim_refs: tuple[str, ...],
    objective_refs: tuple[str, ...],
    normative_boundary: NormativeBoundaryV1,
    delegated_authority: DelegatedAuthorityV1,
    capability_claim: CapabilityClaimV1,
    evaluation_refs: tuple[str, ...],
    approval_requirement_refs: tuple[str, ...] = (),
    action_reversibility: ActionReversibility,
    human_override_ref: str | None = None,
    recovery_or_compensation_ref: str | None = None,
    parent: TaskNormativeEnvelopeV1 | None = None,
) -> TaskNormativeEnvelopeV1:
    """Normalize builder inputs and return a validated canonical envelope."""

    if parent is not None:
        validate_task_normative_envelope(parent)
    normalized_boundary = _normalize_boundary(normative_boundary)
    normalized_authority = _normalize_authority(delegated_authority)
    normalized_capability = _normalize_capability(capability_claim)
    normalized_reversibility = _normalize_action_reversibility(action_reversibility)
    normalized_task_packet_id = _normalize_task_packet_id(task_packet_id)
    normalized_purpose_claim_refs = _normalize_refs(
        purpose_claim_refs,
        "purpose_claim_refs",
    )
    normalized_objective_refs = _normalize_refs(objective_refs, "objective_refs")
    normalized_evaluation_refs = _normalize_refs(evaluation_refs, "evaluation_refs")
    normalized_approval_requirement_refs = _normalize_refs(
        approval_requirement_refs,
        "approval_requirement_refs",
    )
    normalized_human_override_ref = _normalize_optional_ref(
        human_override_ref,
        "human_override_ref",
    )
    normalized_recovery_or_compensation_ref = _normalize_optional_ref(
        recovery_or_compensation_ref,
        "recovery_or_compensation_ref",
    )
    temporary_envelope = TaskNormativeEnvelopeV1(
        schema_version=_SCHEMA_VERSION,
        policy_version=_POLICY_VERSION,
        task_packet_id=normalized_task_packet_id,
        purpose_claim_refs=normalized_purpose_claim_refs,
        objective_refs=normalized_objective_refs,
        normative_boundary=normalized_boundary,
        delegated_authority=normalized_authority,
        capability_claim=normalized_capability,
        evaluation_refs=normalized_evaluation_refs,
        approval_requirement_refs=normalized_approval_requirement_refs,
        action_reversibility=normalized_reversibility,
        human_override_ref=normalized_human_override_ref,
        recovery_or_compensation_ref=normalized_recovery_or_compensation_ref,
        parent_envelope_fingerprint=(parent.envelope_fingerprint if parent is not None else None),
        envelope_fingerprint="",
    )
    identity = _task_normative_envelope_to_stable_mapping_unchecked(temporary_envelope)
    envelope = replace(
        temporary_envelope,
        envelope_fingerprint=fingerprint_payload(cast(JsonValue, identity)),
    )
    validate_task_normative_envelope(envelope)
    return envelope


def task_normative_envelope_to_stable_mapping(
    envelope: TaskNormativeEnvelopeV1,
    *,
    include_fingerprint: bool = True,
) -> dict[str, object]:
    """Return the explicit JSON-ready stable mapping for an envelope."""

    if type(include_fingerprint) is not bool:
        raise ValueError("invalid include_fingerprint")
    validate_task_normative_envelope(envelope)
    mapping = _task_normative_envelope_to_stable_mapping_unchecked(envelope)
    if include_fingerprint:
        mapping["envelope_fingerprint"] = envelope.envelope_fingerprint
    return mapping


def validate_task_normative_envelope(
    envelope: TaskNormativeEnvelopeV1,
) -> None:
    """Validate exact types, canonical form, fixed flags, and fingerprint."""

    if type(envelope) is not TaskNormativeEnvelopeV1:
        raise ValueError("invalid task_normative_envelope")
    _require_exact_string(envelope.schema_version, "schema_version")
    if envelope.schema_version != _SCHEMA_VERSION:
        raise ValueError("invalid schema_version")
    _require_exact_string(envelope.policy_version, "policy_version")
    if envelope.policy_version != _POLICY_VERSION:
        raise ValueError("invalid policy_version")
    if envelope.task_packet_id != _normalize_task_packet_id(envelope.task_packet_id):
        raise ValueError("invalid task_packet_id")
    _validate_canonical_refs(envelope.purpose_claim_refs, "purpose_claim_refs")
    _validate_canonical_refs(envelope.objective_refs, "objective_refs")
    _validate_boundary(envelope.normative_boundary)
    _validate_authority(envelope.delegated_authority)
    _validate_capability(envelope.capability_claim)
    _validate_canonical_refs(envelope.evaluation_refs, "evaluation_refs")
    _validate_canonical_refs(envelope.approval_requirement_refs, "approval_requirement_refs")
    if envelope.action_reversibility != _normalize_action_reversibility(
        envelope.action_reversibility
    ):
        raise ValueError("invalid action_reversibility")
    _validate_canonical_optional_ref(envelope.human_override_ref, "human_override_ref")
    _validate_canonical_optional_ref(
        envelope.recovery_or_compensation_ref,
        "recovery_or_compensation_ref",
    )
    _validate_canonical_optional_fingerprint(
        envelope.parent_envelope_fingerprint,
        "parent_envelope_fingerprint",
    )
    for name in (
        "execution_authority",
        "routing_authority",
        "approval_authority",
        "promotion_authority",
        "merge_authority",
    ):
        if getattr(envelope, name) is not False:
            raise ValueError(f"invalid {name}")
    _validate_canonical_fingerprint(envelope.envelope_fingerprint, "envelope_fingerprint")
    identity = _task_normative_envelope_to_stable_mapping_unchecked(envelope)
    expected_fingerprint = fingerprint_payload(cast(JsonValue, identity))
    if envelope.envelope_fingerprint != expected_fingerprint:
        raise ValueError("invalid envelope_fingerprint")


def assess_task_normative_envelope(
    envelope: TaskNormativeEnvelopeV1,
    *,
    parent: TaskNormativeEnvelopeV1 | None = None,
) -> TaskNormativeAssessmentV1:
    """Assess local consistency and, when exactly bound, the immediate parent."""

    validate_task_normative_envelope(envelope)
    if parent is not None:
        validate_task_normative_envelope(parent)
    if (envelope.parent_envelope_fingerprint is None) != (parent is None):
        raise ValueError("invalid parent binding")

    mismatch_reasons: set[_ReasonCode] = set()
    insufficient_reasons: set[_ReasonCode] = set()
    excess_actions = set(envelope.capability_claim.action_classes).difference(
        envelope.delegated_authority.action_classes
    )
    excess_scopes = set(envelope.capability_claim.resource_scope_refs).difference(
        envelope.delegated_authority.resource_scope_refs
    )
    dropped_obligations: set[str] = set()
    dropped_prohibitions: set[str] = set()
    dropped_constraints: set[str] = set()

    if excess_actions:
        mismatch_reasons.add("capability_action_exceeds_authority")
    if excess_scopes:
        mismatch_reasons.add("capability_scope_exceeds_authority")
    if not envelope.purpose_claim_refs:
        insufficient_reasons.add("missing_purpose_claim")
    if not envelope.objective_refs:
        insufficient_reasons.add("missing_objective")
    if not envelope.evaluation_refs:
        insufficient_reasons.add("missing_evaluation")
    has_capability_claim = bool(
        envelope.capability_claim.action_classes or envelope.capability_claim.resource_scope_refs
    )
    if has_capability_claim and not envelope.capability_claim.evidence_refs:
        insufficient_reasons.add("missing_capability_evidence")
    if envelope.action_reversibility != "read_only":
        if envelope.human_override_ref is None:
            insufficient_reasons.add("missing_human_override")
        if envelope.recovery_or_compensation_ref is None:
            insufficient_reasons.add("missing_recovery_or_compensation")
    if (
        envelope.action_reversibility == "irreversible_change"
        and not envelope.approval_requirement_refs
    ):
        insufficient_reasons.add("missing_irreversible_approval_requirement")

    if parent is not None:
        if envelope.parent_envelope_fingerprint != parent.envelope_fingerprint:
            mismatch_reasons.add("parent_fingerprint_mismatch")
        else:
            parent_action_excess = set(envelope.delegated_authority.action_classes).difference(
                parent.delegated_authority.action_classes
            )
            parent_scope_excess = set(envelope.delegated_authority.resource_scope_refs).difference(
                parent.delegated_authority.resource_scope_refs
            )
            dropped_obligations = set(parent.normative_boundary.obligation_refs).difference(
                envelope.normative_boundary.obligation_refs
            )
            dropped_prohibitions = set(parent.normative_boundary.prohibition_refs).difference(
                envelope.normative_boundary.prohibition_refs
            )
            dropped_constraints = set(
                parent.normative_boundary.non_tradeable_constraint_refs
            ).difference(envelope.normative_boundary.non_tradeable_constraint_refs)
            excess_actions.update(parent_action_excess)
            excess_scopes.update(parent_scope_excess)
            if parent_action_excess:
                mismatch_reasons.add("parent_action_authority_widened")
            if parent_scope_excess:
                mismatch_reasons.add("parent_resource_scope_widened")
            if dropped_obligations:
                mismatch_reasons.add("parent_obligation_dropped")
            if dropped_prohibitions:
                mismatch_reasons.add("parent_prohibition_dropped")
            if dropped_constraints:
                mismatch_reasons.add("parent_non_tradeable_constraint_dropped")
            if parent.delegated_authority.delegation_allowed is False:
                mismatch_reasons.add("parent_delegation_forbidden")

    reason_codes = tuple(sorted(mismatch_reasons | insufficient_reasons))
    state: AssessmentState
    if mismatch_reasons:
        state = "mismatch"
    elif insufficient_reasons:
        state = "insufficient_evidence"
    else:
        state = "consistent"
    return TaskNormativeAssessmentV1(
        state=state,
        reason_codes=reason_codes,
        excess_action_classes=tuple(sorted(excess_actions)),
        excess_resource_scope_refs=tuple(sorted(excess_scopes)),
        dropped_obligation_refs=tuple(sorted(dropped_obligations)),
        dropped_prohibition_refs=tuple(sorted(dropped_prohibitions)),
        dropped_non_tradeable_constraint_refs=tuple(sorted(dropped_constraints)),
    )


def _normalize_boundary(boundary: NormativeBoundaryV1) -> NormativeBoundaryV1:
    if type(boundary) is not NormativeBoundaryV1:
        raise ValueError("invalid normative_boundary")
    return NormativeBoundaryV1(
        obligation_refs=_normalize_refs(boundary.obligation_refs, "obligation_refs"),
        prohibition_refs=_normalize_refs(boundary.prohibition_refs, "prohibition_refs"),
        non_tradeable_constraint_refs=_normalize_refs(
            boundary.non_tradeable_constraint_refs,
            "non_tradeable_constraint_refs",
        ),
    )


def _normalize_authority(authority: DelegatedAuthorityV1) -> DelegatedAuthorityV1:
    if type(authority) is not DelegatedAuthorityV1:
        raise ValueError("invalid delegated_authority")
    if type(authority.delegation_allowed) is not bool:
        raise ValueError("invalid delegation_allowed")
    return DelegatedAuthorityV1(
        action_classes=_normalize_refs(authority.action_classes, "authority_action_classes"),
        resource_scope_refs=_normalize_refs(
            authority.resource_scope_refs,
            "authority_resource_scope_refs",
        ),
        authority_basis_refs=_normalize_refs(
            authority.authority_basis_refs,
            "authority_basis_refs",
        ),
        delegation_allowed=authority.delegation_allowed,
    )


def _normalize_capability(capability: CapabilityClaimV1) -> CapabilityClaimV1:
    if type(capability) is not CapabilityClaimV1:
        raise ValueError("invalid capability_claim")
    return CapabilityClaimV1(
        action_classes=_normalize_refs(capability.action_classes, "capability_action_classes"),
        resource_scope_refs=_normalize_refs(
            capability.resource_scope_refs,
            "capability_resource_scope_refs",
        ),
        evidence_refs=_normalize_refs(capability.evidence_refs, "capability_evidence_refs"),
    )


def _validate_boundary(boundary: NormativeBoundaryV1) -> None:
    if type(boundary) is not NormativeBoundaryV1:
        raise ValueError("invalid normative_boundary")
    _validate_canonical_refs(boundary.obligation_refs, "obligation_refs")
    _validate_canonical_refs(boundary.prohibition_refs, "prohibition_refs")
    _validate_canonical_refs(
        boundary.non_tradeable_constraint_refs,
        "non_tradeable_constraint_refs",
    )


def _validate_authority(authority: DelegatedAuthorityV1) -> None:
    if type(authority) is not DelegatedAuthorityV1:
        raise ValueError("invalid delegated_authority")
    _validate_canonical_refs(authority.action_classes, "authority_action_classes")
    _validate_canonical_refs(authority.resource_scope_refs, "authority_resource_scope_refs")
    _validate_canonical_refs(authority.authority_basis_refs, "authority_basis_refs")
    if type(authority.delegation_allowed) is not bool:
        raise ValueError("invalid delegation_allowed")


def _validate_capability(capability: CapabilityClaimV1) -> None:
    if type(capability) is not CapabilityClaimV1:
        raise ValueError("invalid capability_claim")
    _validate_canonical_refs(capability.action_classes, "capability_action_classes")
    _validate_canonical_refs(capability.resource_scope_refs, "capability_resource_scope_refs")
    _validate_canonical_refs(capability.evidence_refs, "capability_evidence_refs")


def _normalize_refs(refs: tuple[str, ...], category: str) -> tuple[str, ...]:
    if type(refs) is not tuple:
        raise ValueError(f"invalid {category}")
    normalized: set[str] = set()
    for ref in refs:
        if type(ref) is not str:
            raise ValueError(f"invalid {category}")
        _reject_c0_or_del(ref, category)
        value = ref.strip()
        if _REF_RE.fullmatch(value) is None:
            raise ValueError(f"invalid {category}")
        normalized.add(value)
    return tuple(sorted(normalized))


def _validate_canonical_refs(refs: tuple[str, ...], category: str) -> None:
    if refs != _normalize_refs(refs, category):
        raise ValueError(f"invalid {category}")


def _normalize_task_packet_id(task_packet_id: str) -> str:
    _require_exact_string(task_packet_id, "task_packet_id")
    _reject_c0_or_del(task_packet_id, "task_packet_id")
    normalized = task_packet_id.strip()
    if _TASK_PACKET_ID_RE.fullmatch(normalized) is None:
        raise ValueError("invalid task_packet_id")
    return normalized


def _normalize_action_reversibility(value: ActionReversibility) -> ActionReversibility:
    _require_exact_string(value, "action_reversibility")
    _reject_c0_or_del(value, "action_reversibility")
    if value not in _ACTION_REVERSIBILITY_VALUES:
        raise ValueError("invalid action_reversibility")
    return value


def _normalize_optional_ref(value: str | None, category: str) -> str | None:
    if value is None:
        return None
    _require_exact_string(value, category)
    _reject_c0_or_del(value, category)
    normalized = value.strip()
    if _REF_RE.fullmatch(normalized) is None:
        raise ValueError(f"invalid {category}")
    return normalized


def _validate_canonical_optional_ref(value: str | None, category: str) -> None:
    if value != _normalize_optional_ref(value, category):
        raise ValueError(f"invalid {category}")


def _normalize_optional_fingerprint(value: str | None, category: str) -> str | None:
    if value is None:
        return None
    _require_exact_string(value, category)
    try:
        return validate_fingerprint(value)
    except ValueError as exc:
        raise ValueError(f"invalid {category}") from exc


def _validate_canonical_optional_fingerprint(value: str | None, category: str) -> None:
    if value != _normalize_optional_fingerprint(value, category):
        raise ValueError(f"invalid {category}")


def _validate_canonical_fingerprint(value: str, category: str) -> None:
    _require_exact_string(value, category)
    try:
        normalized = validate_fingerprint(value)
    except ValueError as exc:
        raise ValueError(f"invalid {category}") from exc
    if value != normalized:
        raise ValueError(f"invalid {category}")


def _require_exact_string(value: object, category: str) -> None:
    if type(value) is not str:
        raise ValueError(f"invalid {category}")


def _reject_c0_or_del(value: str, category: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"invalid {category}")


def _boundary_to_mapping(boundary: NormativeBoundaryV1) -> dict[str, object]:
    return {
        "obligation_refs": list(boundary.obligation_refs),
        "prohibition_refs": list(boundary.prohibition_refs),
        "non_tradeable_constraint_refs": list(boundary.non_tradeable_constraint_refs),
    }


def _authority_to_mapping(authority: DelegatedAuthorityV1) -> dict[str, object]:
    return {
        "action_classes": list(authority.action_classes),
        "resource_scope_refs": list(authority.resource_scope_refs),
        "authority_basis_refs": list(authority.authority_basis_refs),
        "delegation_allowed": authority.delegation_allowed,
    }


def _capability_to_mapping(capability: CapabilityClaimV1) -> dict[str, object]:
    return {
        "action_classes": list(capability.action_classes),
        "resource_scope_refs": list(capability.resource_scope_refs),
        "evidence_refs": list(capability.evidence_refs),
    }


def _task_normative_envelope_to_stable_mapping_unchecked(
    envelope: TaskNormativeEnvelopeV1,
) -> dict[str, object]:
    return {
        "schema_version": envelope.schema_version,
        "policy_version": envelope.policy_version,
        "task_packet_id": envelope.task_packet_id,
        "purpose_claim_refs": list(envelope.purpose_claim_refs),
        "objective_refs": list(envelope.objective_refs),
        "normative_boundary": _boundary_to_mapping(envelope.normative_boundary),
        "delegated_authority": _authority_to_mapping(envelope.delegated_authority),
        "capability_claim": _capability_to_mapping(envelope.capability_claim),
        "evaluation_refs": list(envelope.evaluation_refs),
        "approval_requirement_refs": list(envelope.approval_requirement_refs),
        "action_reversibility": envelope.action_reversibility,
        "human_override_ref": envelope.human_override_ref,
        "recovery_or_compensation_ref": envelope.recovery_or_compensation_ref,
        "parent_envelope_fingerprint": envelope.parent_envelope_fingerprint,
        "execution_authority": envelope.execution_authority,
        "routing_authority": envelope.routing_authority,
        "approval_authority": envelope.approval_authority,
        "promotion_authority": envelope.promotion_authority,
        "merge_authority": envelope.merge_authority,
    }


__all__ = (
    "ActionReversibility",
    "AssessmentState",
    "NormativeBoundaryV1",
    "DelegatedAuthorityV1",
    "CapabilityClaimV1",
    "TaskNormativeEnvelopeV1",
    "TaskNormativeAssessmentV1",
    "build_task_normative_envelope",
    "task_normative_envelope_to_stable_mapping",
    "validate_task_normative_envelope",
    "assess_task_normative_envelope",
)
