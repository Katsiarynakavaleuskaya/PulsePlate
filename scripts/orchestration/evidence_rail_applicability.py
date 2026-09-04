#!/usr/bin/env python3
"""Select non-authoritative evidence-rail treatments from one task packet."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from types import MappingProxyType
from typing import Any, NoReturn, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.bootstrap_sync_policy import (
    INVARIANT_CHANGE_CLASSES,
    INVARIANT_FAMILY_REPEAT_TRIGGER_RULE,
    INVARIANT_REVIEW_BOUNDARY_CLASSES,
    INVARIANT_REVIEW_COVERAGE_CLAIM,
    INVARIANT_REVIEW_REQUIRED_OUTPUT_FIELDS,
    INVARIANT_REVIEW_REQUIRED_ROLES,
    INVARIANT_REVIEW_STOP_CONDITION,
    INVARIANT_REVIEW_V1_FIELDS,
    INVARIANT_REVIEW_V2_FIELDS,
    INVARIANT_REVIEW_V2_REQUIRED_OUTPUT_FIELDS,
    INVARIANT_REVIEW_FAMILY_REPEAT_FIELDS,
    requires_security_review,
    resolve_analysis_envelope_mode,
)
from scripts.orchestration.context_pack import canonical_task_candidate_paths
from scripts.orchestration.design_lane_contract import normalize_design_lane_packet_projection

SCHEMA_VERSION = "evidence_rail_applicability.v1"
POLICY_VERSION = "evidence_rail_applicability.policy.v1"
TASK_PACKET_SCHEMA_VERSION = "3.1"
PACKET_ROOT = PurePosixPath("artifacts/orchestration/task_packets")
MAX_PACKET_BYTES = 2_000_000
MAX_CAPTURED_BYTES = 8_192
MAX_CANDIDATE_PATHS = 256
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 50_000

RAILS = ("teleology", "euler", "experiment_runner", "creative")
SIDECAR_RAILS = ("teleology", "euler", "experiment_runner")
RULE_IDS = ("higher_assurance", "design", "docs_only", "conservative")
REASON_CODES = (
    "invariant_review_required",
    "security_review_required",
    "design_lane_applicable",
    "docs_only_scope",
    "conservative_default",
    "runner_required_by_existing_pr_policy",
    "higher_assurance_scope_preempts_creative",
    "docs_only_euler_not_selected",
    "creative_scope_not_selected",
    "manual_additive_upgrade",
)
TASK_CLASSIFICATION_LABELS = (
    "pr_governance",
    "design",
    "creative_research",
    "experiment",
    "review",
    "bugfix",
    "implementation",
)
PR_PHASES = ("none", "pre_open", "post_open_review", "merge_ready")
ENVELOPE_MODES = ("analysis", "docs_only")
INVARIANT_REVIEW_STATES = ("not_required", "required_pending")
INVARIANT_REVIEW_V2_COVERAGE_CLAIM = "explicit_normalized_snapshot_membership_only"
INVARIANT_FAMILY_REPEAT_MEMBERSHIP_SOURCE = "explicit_input_only"
INVARIANT_FAMILY_SOURCE_SCHEMA_VERSION = "review_invariant_family_relations.v1"
INVARIANT_FAMILY_SOURCE_POLICY_VERSION = "review_invariant_family_relations.policy.v1"
INVARIANT_FAMILY_RELATION_VALUES = (
    "equal",
    "left_proper_subset",
    "right_proper_subset",
    "partial_overlap",
    "disjoint",
)
INVARIANT_FAMILY_ROW_FIELDS = frozenset({"family_id", "finding_ids"})
INVARIANT_FAMILY_RELATION_FIELDS = frozenset(
    {
        "left_family_id",
        "right_family_id",
        "relation",
        "intersection_finding_ids",
        "left_only_finding_ids",
        "right_only_finding_ids",
    }
)
AUTOMATION_FLAG_FIELDS = frozenset(
    {
        "coordinator_first_required",
        "skill_routing_applied",
        "native_subagent_bridge_available",
        "security_review_required",
        "invariant_class_review_required",
        "judgment_lane_enabled",
        "pr_lifecycle_enabled",
        "design_lane_enabled",
    }
)
OPTIONAL_AUTOMATION_FLAG_FIELDS = frozenset({"creative_pilot_enabled"})
AUTHORITY = (
    ("approval_authority", False),
    ("causality_authority", False),
    ("ci_authority", False),
    ("enrollment_authority", False),
    ("implementation_authority", False),
    ("merge_authority", False),
    ("outcome_authority", False),
    ("promotion_authority", False),
    ("release_authority", False),
    ("review_authority", False),
    ("routing_authority", False),
)

_PACKET_ID_RE = re.compile(r"^[a-f0-9]{12}$", re.ASCII)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$", re.ASCII)
_IDEMPOTENCY_RE = re.compile(r"^review-invariant-family-relations\.v1:[a-f0-9]{64}$", re.ASCII)


class EvidenceRailApplicabilityError(ValueError):
    """Fail-closed error carrying only one stable public category."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


class RailTreatment(str, Enum):
    """Closed treatment vocabulary; values select planning depth only."""

    FULL = "full"
    COMPACT = "compact"
    FINITE_REVIEW = "finite_review"
    REQUIRED = "required"
    RECOMMEND = "recommend"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class TaskPacketSnapshot:
    """Immutable, fingerprint-bound view of one safely read task packet."""

    packet_path: str
    task_packet_id: str
    task_packet_fingerprint: str
    packet: Mapping[str, Any]


@dataclass(frozen=True)
class ApplicabilitySignals:
    """Closed structured signals consumed by the treatment matrix."""

    invariant_review: bool
    security_review: bool
    design_lane: bool
    docs_only: bool


@dataclass(frozen=True)
class EvidenceRailApplicability:
    """Canonical, non-authoritative treatment projection."""

    task_packet_id: str
    task_packet_fingerprint: str
    rule_id: str
    additive_rails: tuple[str, ...]
    treatments: tuple[tuple[str, RailTreatment, tuple[str, ...]], ...]
    applicable_sidecar_rails: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        """Return the exact JSON-ready v1 wire shape."""

        return {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "task_packet_id": self.task_packet_id,
            "task_packet_fingerprint": self.task_packet_fingerprint,
            "rule_id": self.rule_id,
            "additive_rails": list(self.additive_rails),
            "treatments": {
                rail: {"treatment": treatment.value, "reasons": list(reasons)}
                for rail, treatment, reasons in self.treatments
            },
            "applicable_sidecar_rails": list(self.applicable_sidecar_rails),
            "authority": dict(AUTHORITY),
        }


class _StrictArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> NoReturn:
        raise EvidenceRailApplicabilityError("INVALID_INPUT")


def _error(category: str = "INVALID_INPUT") -> NoReturn:
    raise EvidenceRailApplicabilityError(category)


def _reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _error()
        result[key] = value
    return result


def _validate_json_complexity(value: Any) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            _error()
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def _strict_json_bytes(raw: bytes, *, limit: int) -> Any:
    if not raw or len(raw) > limit or raw.startswith(b"\xef\xbb\xbf"):
        _error()
    try:
        text = raw.decode("utf-8")
        decoder = json.JSONDecoder(
            object_pairs_hook=_reject_duplicate,
            parse_constant=lambda _value: _error(),
        )
        value, end = decoder.raw_decode(text)
    except EvidenceRailApplicabilityError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc
    if text[end:].strip():
        _error()
    _validate_json_complexity(value)
    return value


def _normalize_packet_path(packet_path: str | Path) -> tuple[str, tuple[str, ...]]:
    if not isinstance(packet_path, (str, Path)):
        _error()
    raw = packet_path.as_posix() if isinstance(packet_path, Path) else packet_path
    if (
        not raw
        or raw != raw.strip()
        or "\\" in raw
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
    ):
        _error()
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or path.as_posix() != raw
        or path.parent != PACKET_ROOT
        or path.suffix != ".json"
        or _PACKET_ID_RE.fullmatch(path.stem) is None
    ):
        _error()
    return raw, path.parts


def _required_open_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        _error("STORAGE_UNAVAILABLE")
    return value


def _metadata_tuple(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_packet_bytes(parts: tuple[str, ...]) -> bytes:
    directory_flags = (
        os.O_RDONLY
        | _required_open_flag("O_DIRECTORY")
        | _required_open_flag("O_NOFOLLOW")
        | _required_open_flag("O_CLOEXEC")
    )
    file_flags = (
        os.O_RDONLY
        | _required_open_flag("O_NOFOLLOW")
        | _required_open_flag("O_CLOEXEC")
        | _required_open_flag("O_NONBLOCK")
    )
    directory_fds: list[int] = []
    file_fd = -1
    try:
        directory_fds.append(os.open(REPO_ROOT, directory_flags))
        for component in parts[:-1]:
            directory_fds.append(os.open(component, directory_flags, dir_fd=directory_fds[-1]))
        file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fds[-1])
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _error()
        if before.st_size <= 0 or before.st_size > MAX_PACKET_BYTES:
            _error()
        chunks: list[bytes] = []
        remaining = MAX_PACKET_BYTES + 1
        while remaining:
            chunk = os.read(file_fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(file_fd)
        path_metadata = os.stat(parts[-1], dir_fd=directory_fds[-1], follow_symlinks=False)
        if (
            len(raw) > MAX_PACKET_BYTES
            or len(raw) != before.st_size
            or _metadata_tuple(before) != _metadata_tuple(after)
            or _metadata_tuple(after) != _metadata_tuple(path_metadata)
            or not stat.S_ISREG(path_metadata.st_mode)
            or path_metadata.st_nlink != 1
        ):
            _error()
        return raw
    except EvidenceRailApplicabilityError:
        raise
    except NotImplementedError as exc:
        raise EvidenceRailApplicabilityError("STORAGE_UNAVAILABLE") from exc
    except OSError as exc:
        raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc
    finally:
        close_failed = False
        for descriptor in (file_fd, *reversed(directory_fds)):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    close_failed = True
        if sys.exc_info()[1] is None and close_failed:
            _error("STORAGE_UNAVAILABLE")


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _exact_dict(value: Any, fields: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        _error()
    return cast(dict[str, Any], value)


def _require_bool(value: Any) -> bool:
    if type(value) is not bool:
        _error()
    return cast(bool, value)


def _string_list(value: Any, *, limit: int = 256) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > limit
        or any(type(item) is not str or not item for item in value)
    ):
        _error()
    return cast(list[str], value)


def _canonical_string_list(value: Any, *, limit: int = 256) -> list[str]:
    items = _string_list(value, limit=limit)
    if items != sorted(set(items)):
        _error()
    return items


def _validate_invariant_v1(
    value: Any,
    *,
    pr_phase: str,
    phase_flag: bool,
) -> bool:
    review = _exact_dict(value, INVARIANT_REVIEW_V1_FIELDS)
    if review.get("schema_version") != "invariant_review.v1":
        _error()
    change_classes = _string_list(review.get("change_classes"), limit=4)
    canonical_classes = [item for item in INVARIANT_CHANGE_CLASSES if item in change_classes]
    if change_classes != canonical_classes or len(change_classes) != len(set(change_classes)):
        _error()
    required_now = bool(change_classes) and pr_phase in {"none", "pre_open"}
    expected_state = "required_pending" if required_now else "not_required"
    if review.get("state") != expected_state or phase_flag is not required_now:
        _error()
    if review.get("coverage_claim") != INVARIANT_REVIEW_COVERAGE_CLAIM:
        _error()
    expected_roles = list(INVARIANT_REVIEW_REQUIRED_ROLES) if required_now else []
    if review.get("required_roles") != expected_roles:
        _error()
    if review.get("boundary_classes") != list(INVARIANT_REVIEW_BOUNDARY_CLASSES):
        _error()
    if review.get("required_output_fields") != list(INVARIANT_REVIEW_REQUIRED_OUTPUT_FIELDS):
        _error()
    if review.get("stop_condition") != INVARIANT_REVIEW_STOP_CONDITION:
        _error()
    if (
        review.get("implementation_authority") is not False
        or review.get("merge_authority") is not False
    ):
        _error()

    trigger_evidence = review.get("trigger_evidence")
    if not isinstance(trigger_evidence, list) or len(trigger_evidence) > MAX_CANDIDATE_PATHS:
        _error()
    evidenced_classes: set[str] = set()
    for row in trigger_evidence:
        if not isinstance(row, dict) or set(row) not in (
            {"change_class", "source"},
            {"change_class", "source", "path"},
        ):
            _error()
        change_class = row.get("change_class")
        source = row.get("source")
        if change_class not in INVARIANT_CHANGE_CLASSES or source not in {
            "explicit",
            "bounded_path_hint",
        }:
            _error()
        if source == "explicit" and set(row) != {"change_class", "source"}:
            _error()
        if source == "bounded_path_hint":
            if set(row) != {"change_class", "source", "path"}:
                _error()
            try:
                canonical_task_candidate_paths([row.get("path")], mode="strict_wire")
            except ValueError as exc:
                raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc
        evidenced_classes.add(cast(str, change_class))
    if evidenced_classes != set(change_classes):
        _error()
    return bool(change_classes)


def _validate_relation_string_list(value: Any) -> list[str]:
    return _canonical_string_list(value, limit=MAX_CANDIDATE_PATHS)


def _validate_invariant_v2(
    value: Any,
    *,
    pr_phase: str,
    phase_flag: bool,
) -> bool:
    review = _exact_dict(value, INVARIANT_REVIEW_V2_FIELDS)
    if review.get("schema_version") != "invariant_review.v2":
        _error()
    if pr_phase != "post_open_review":
        _error()
    state = review.get("state")
    if state not in INVARIANT_REVIEW_STATES:
        _error()
    if review.get("coverage_claim") != INVARIANT_REVIEW_V2_COVERAGE_CLAIM:
        _error()
    if review.get("boundary_classes") != list(INVARIANT_REVIEW_BOUNDARY_CLASSES):
        _error()
    if review.get("required_output_fields") != list(INVARIANT_REVIEW_V2_REQUIRED_OUTPUT_FIELDS):
        _error()
    if review.get("stop_condition") != INVARIANT_REVIEW_STOP_CONDITION:
        _error()
    if (
        review.get("implementation_authority") is not False
        or review.get("merge_authority") is not False
    ):
        _error()

    family_repeat = _exact_dict(review.get("family_repeat"), INVARIANT_REVIEW_FAMILY_REPEAT_FIELDS)
    if (
        family_repeat.get("source_schema_version") != INVARIANT_FAMILY_SOURCE_SCHEMA_VERSION
        or family_repeat.get("source_policy_version") != INVARIANT_FAMILY_SOURCE_POLICY_VERSION
        or family_repeat.get("trigger_rule") != INVARIANT_FAMILY_REPEAT_TRIGGER_RULE
        or family_repeat.get("membership_source") != INVARIANT_FAMILY_REPEAT_MEMBERSHIP_SOURCE
    ):
        _error()
    snapshot_fingerprint = family_repeat.get("snapshot_fingerprint")
    artifact_fingerprint = family_repeat.get("artifact_fingerprint")
    if (
        not isinstance(snapshot_fingerprint, str)
        or _SHA256_RE.fullmatch(snapshot_fingerprint) is None
        or not isinstance(artifact_fingerprint, str)
        or _SHA256_RE.fullmatch(artifact_fingerprint) is None
    ):
        _error()
    idempotency_key = family_repeat.get("idempotency_key")
    if (
        not isinstance(idempotency_key, str)
        or _IDEMPOTENCY_RE.fullmatch(idempotency_key) is None
        or idempotency_key
        != "review-invariant-family-relations.v1:" + artifact_fingerprint.removeprefix("sha256:")
    ):
        _error()
    _require_bool(family_repeat.get("unknown_findings_present"))

    repeated = family_repeat.get("repeated_families")
    if not isinstance(repeated, list) or len(repeated) > MAX_CANDIDATE_PATHS:
        _error()
    family_ids: list[str] = []
    for row in repeated:
        family = _exact_dict(row, INVARIANT_FAMILY_ROW_FIELDS)
        family_id = family.get("family_id")
        finding_ids = _canonical_string_list(family.get("finding_ids"), limit=MAX_CANDIDATE_PATHS)
        if not isinstance(family_id, str) or not family_id or len(finding_ids) < 2:
            _error()
        family_ids.append(family_id)
    if family_ids != sorted(set(family_ids)):
        _error()

    relations = family_repeat.get("relations_touching_repeated_families")
    if not isinstance(relations, list) or len(relations) > MAX_CANDIDATE_PATHS:
        _error()
    relation_pairs: list[tuple[str, str]] = []
    repeated_set = set(family_ids)
    for row in relations:
        relation = _exact_dict(row, INVARIANT_FAMILY_RELATION_FIELDS)
        left = relation.get("left_family_id")
        right = relation.get("right_family_id")
        if (
            not isinstance(left, str)
            or not isinstance(right, str)
            or not left < right
            or (left not in repeated_set and right not in repeated_set)
            or relation.get("relation") not in INVARIANT_FAMILY_RELATION_VALUES
        ):
            _error()
        for field in (
            "intersection_finding_ids",
            "left_only_finding_ids",
            "right_only_finding_ids",
        ):
            _validate_relation_string_list(relation.get(field))
        relation_pairs.append((left, right))
    if relation_pairs != sorted(set(relation_pairs)):
        _error()

    required = bool(repeated)
    expected_state = "required_pending" if required else "not_required"
    expected_roles = list(INVARIANT_REVIEW_REQUIRED_ROLES) if required else []
    if (
        state != expected_state
        or review.get("required_roles") != expected_roles
        or phase_flag is not required
    ):
        _error()
    return required


def _validate_packet_projection(packet: Any, *, filename_id: str) -> None:
    if not isinstance(packet, dict) or packet.get("schema_version") != TASK_PACKET_SCHEMA_VERSION:
        _error()
    task_packet_id = packet.get("task_packet_id")
    if (
        not isinstance(task_packet_id, str)
        or _PACKET_ID_RE.fullmatch(task_packet_id) is None
        or task_packet_id != filename_id
    ):
        _error()
    pr_phase = packet.get("pr_phase")
    if pr_phase not in PR_PHASES:
        _error()
    candidate_paths = packet.get("candidate_paths")
    if not isinstance(candidate_paths, list) or len(candidate_paths) > MAX_CANDIDATE_PATHS:
        _error()
    try:
        canonical_paths = canonical_task_candidate_paths(candidate_paths, mode="strict_wire")
    except ValueError as exc:
        raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc

    automation = packet.get("automation_flags")
    if not isinstance(automation, dict):
        _error()
    if not AUTOMATION_FLAG_FIELDS.issubset(automation) or not set(automation).issubset(
        AUTOMATION_FLAG_FIELDS | OPTIONAL_AUTOMATION_FLAG_FIELDS
    ):
        _error()
    for value in automation.values():
        _require_bool(value)
    security_flag = cast(bool, automation["security_review_required"])
    if security_flag is not requires_security_review(canonical_paths):
        _error()

    skill_routing = packet.get("skill_routing")
    if not isinstance(skill_routing, dict):
        _error()
    envelope_mode = skill_routing.get("envelope_mode_hint")
    if envelope_mode not in ENVELOPE_MODES:
        _error()
    if envelope_mode != resolve_analysis_envelope_mode(canonical_paths):
        _error()
    classification = _exact_dict(
        skill_routing.get("task_classification"), frozenset({"label", "score", "reasons"})
    )
    classification_label = classification.get("label")
    if classification_label not in TASK_CLASSIFICATION_LABELS:
        _error()
    if type(classification.get("score")) is not int:
        _error()
    _string_list(classification.get("reasons"), limit=64)

    invariant_value = packet.get("invariant_review")
    if not isinstance(invariant_value, dict):
        _error()
    invariant_schema = invariant_value.get("schema_version")
    invariant_flag = cast(bool, automation["invariant_class_review_required"])
    if invariant_schema == "invariant_review.v1":
        _validate_invariant_v1(
            invariant_value,
            pr_phase=cast(str, pr_phase),
            phase_flag=invariant_flag,
        )
    elif invariant_schema == "invariant_review.v2":
        _validate_invariant_v2(
            invariant_value,
            pr_phase=cast(str, pr_phase),
            phase_flag=invariant_flag,
        )
    else:
        _error()

    try:
        normalize_design_lane_packet_projection(
            design_lane_mode=packet.get("design_lane_mode"),
            design_lane_contract=packet.get("design_lane_contract"),
            design_lane_enabled=automation["design_lane_enabled"],
        )
    except ValueError as exc:
        raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc


def read_task_packet_snapshot(packet_path: str | Path) -> TaskPacketSnapshot:
    """Safely read and validate one exact schema-3.1 task packet snapshot."""

    normalized_path, parts = _normalize_packet_path(packet_path)
    raw = _read_packet_bytes(parts)
    packet = _strict_json_bytes(raw, limit=MAX_PACKET_BYTES)
    _validate_packet_projection(packet, filename_id=PurePosixPath(normalized_path).stem)
    task_packet_id = cast(str, packet["task_packet_id"])
    return TaskPacketSnapshot(
        packet_path=normalized_path,
        task_packet_id=task_packet_id,
        task_packet_fingerprint="sha256:" + hashlib.sha256(raw).hexdigest(),
        packet=cast(Mapping[str, Any], _deep_freeze(packet)),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _error()
    return cast(Mapping[str, Any], value)


def extract_applicability_signals(snapshot: TaskPacketSnapshot) -> ApplicabilitySignals:
    """Extract only structured, producer-bound signals from a validated snapshot."""

    packet = snapshot.packet
    automation = _mapping(packet.get("automation_flags"))
    invariant = _mapping(packet.get("invariant_review"))
    invariant_schema = invariant.get("schema_version")
    if invariant_schema == "invariant_review.v1":
        change_classes = invariant.get("change_classes")
        invariant_signal = isinstance(change_classes, tuple) and bool(change_classes)
    elif invariant_schema == "invariant_review.v2":
        family_repeat = _mapping(invariant.get("family_repeat"))
        repeated = family_repeat.get("repeated_families")
        invariant_signal = (
            invariant.get("state") == "required_pending"
            and isinstance(repeated, tuple)
            and bool(repeated)
        )
    else:  # Defensive: the reader rejects this before snapshots are constructed.
        _error()

    skill_routing = _mapping(packet.get("skill_routing"))
    classification = _mapping(skill_routing.get("task_classification"))
    try:
        design_projection = normalize_design_lane_packet_projection(
            design_lane_mode=packet.get("design_lane_mode"),
            design_lane_contract=packet.get("design_lane_contract"),
            design_lane_enabled=automation.get("design_lane_enabled"),
        )
    except ValueError as exc:  # Defensive: the reader validates before freezing.
        raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc
    design_signal = bool(
        classification.get("label") == "design" and design_projection.execution_ready
    )
    return ApplicabilitySignals(
        invariant_review=invariant_signal,
        security_review=automation.get("security_review_required") is True,
        design_lane=design_signal,
        docs_only=skill_routing.get("envelope_mode_hint") == "docs_only",
    )


def _normalize_requested_additive_rails(additive_rails: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(additive_rails, Sequence) or isinstance(additive_rails, (str, bytes)):
        _error()
    normalized: set[str] = set()
    for rail in additive_rails:
        if type(rail) is not str or rail not in SIDECAR_RAILS:
            _error()
        normalized.add(rail)
    return tuple(sorted(normalized))


def _decision_rows(
    signals: ApplicabilitySignals,
    requested_additive_rails: tuple[str, ...],
) -> tuple[
    str,
    tuple[str, ...],
    tuple[tuple[str, RailTreatment, tuple[str, ...]], ...],
    tuple[str, ...],
]:
    if signals.invariant_review or signals.security_review:
        rule_id = "higher_assurance"
        assurance_reasons = tuple(
            reason
            for enabled, reason in (
                (signals.invariant_review, "invariant_review_required"),
                (signals.security_review, "security_review_required"),
            )
            if enabled
        )
        creative_reason = (
            "higher_assurance_scope_preempts_creative"
            if signals.design_lane
            else "creative_scope_not_selected"
        )
        rows = (
            ("teleology", RailTreatment.FULL, assurance_reasons),
            ("euler", RailTreatment.FINITE_REVIEW, assurance_reasons),
            (
                "experiment_runner",
                RailTreatment.REQUIRED,
                ("runner_required_by_existing_pr_policy",),
            ),
            ("creative", RailTreatment.NOT_APPLICABLE, (creative_reason,)),
        )
    elif signals.design_lane:
        rule_id = "design"
        rows = (
            ("teleology", RailTreatment.FULL, ("design_lane_applicable",)),
            ("euler", RailTreatment.FINITE_REVIEW, ("design_lane_applicable",)),
            (
                "experiment_runner",
                RailTreatment.REQUIRED,
                ("runner_required_by_existing_pr_policy",),
            ),
            ("creative", RailTreatment.RECOMMEND, ("design_lane_applicable",)),
        )
    elif signals.docs_only:
        rule_id = "docs_only"
        manual_euler = "euler" in requested_additive_rails
        rows = (
            ("teleology", RailTreatment.COMPACT, ("docs_only_scope",)),
            (
                "euler",
                RailTreatment.FINITE_REVIEW if manual_euler else RailTreatment.NOT_APPLICABLE,
                (
                    ("manual_additive_upgrade",)
                    if manual_euler
                    else ("docs_only_euler_not_selected",)
                ),
            ),
            (
                "experiment_runner",
                RailTreatment.REQUIRED,
                ("runner_required_by_existing_pr_policy",),
            ),
            (
                "creative",
                RailTreatment.NOT_APPLICABLE,
                ("creative_scope_not_selected",),
            ),
        )
    else:
        rule_id = "conservative"
        rows = (
            ("teleology", RailTreatment.FULL, ("conservative_default",)),
            ("euler", RailTreatment.FINITE_REVIEW, ("conservative_default",)),
            (
                "experiment_runner",
                RailTreatment.REQUIRED,
                ("runner_required_by_existing_pr_policy",),
            ),
            (
                "creative",
                RailTreatment.NOT_APPLICABLE,
                ("creative_scope_not_selected",),
            ),
        )

    applicable = tuple(
        sorted(
            rail
            for rail, treatment, _reasons in rows
            if rail in SIDECAR_RAILS and treatment is not RailTreatment.NOT_APPLICABLE
        )
    )
    effective_additive = tuple(
        rail for rail in requested_additive_rails if rail == "euler" and rule_id == "docs_only"
    )
    return rule_id, effective_additive, rows, applicable


def decide_evidence_rail_applicability(
    *,
    task_packet_id: str,
    task_packet_fingerprint: str,
    signals: ApplicabilitySignals,
    additive_rails: Sequence[str] = (),
) -> EvidenceRailApplicability:
    """Apply the closed precedence matrix to validated structured signals."""

    if (
        not isinstance(task_packet_id, str)
        or _PACKET_ID_RE.fullmatch(task_packet_id) is None
        or not isinstance(task_packet_fingerprint, str)
        or _SHA256_RE.fullmatch(task_packet_fingerprint) is None
        or not isinstance(signals, ApplicabilitySignals)
    ):
        _error()
    requested = _normalize_requested_additive_rails(additive_rails)
    rule_id, effective_additive, rows, applicable = _decision_rows(signals, requested)
    return EvidenceRailApplicability(
        task_packet_id=task_packet_id,
        task_packet_fingerprint=task_packet_fingerprint,
        rule_id=rule_id,
        additive_rails=effective_additive,
        treatments=rows,
        applicable_sidecar_rails=applicable,
    )


def build_evidence_rail_applicability(
    snapshot: TaskPacketSnapshot,
    additive_rails: Sequence[str] = (),
) -> EvidenceRailApplicability:
    """Build one fingerprint-bound treatment projection from a packet snapshot."""

    if not isinstance(snapshot, TaskPacketSnapshot):
        _error()
    return decide_evidence_rail_applicability(
        task_packet_id=snapshot.task_packet_id,
        task_packet_fingerprint=snapshot.task_packet_fingerprint,
        signals=extract_applicability_signals(snapshot),
        additive_rails=additive_rails,
    )


def canonical_evidence_rail_json(value: EvidenceRailApplicability) -> str:
    """Return one canonical ASCII JSON line without a trailing newline."""

    if not isinstance(value, EvidenceRailApplicability):
        _error()
    try:
        return json.dumps(
            value.to_mapping(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceRailApplicabilityError("INTERNAL_ERROR") from exc


def _projection_mapping(value: Any) -> dict[str, Any]:
    fields = frozenset(
        {
            "schema_version",
            "policy_version",
            "task_packet_id",
            "task_packet_fingerprint",
            "rule_id",
            "additive_rails",
            "treatments",
            "applicable_sidecar_rails",
            "authority",
        }
    )
    projection = _exact_dict(value, fields)
    if (
        projection.get("schema_version") != SCHEMA_VERSION
        or projection.get("policy_version") != POLICY_VERSION
        or projection.get("rule_id") not in RULE_IDS
    ):
        _error()
    packet_id = projection.get("task_packet_id")
    packet_fingerprint = projection.get("task_packet_fingerprint")
    if (
        not isinstance(packet_id, str)
        or _PACKET_ID_RE.fullmatch(packet_id) is None
        or not isinstance(packet_fingerprint, str)
        or _SHA256_RE.fullmatch(packet_fingerprint) is None
    ):
        _error()
    additive = _canonical_string_list(projection.get("additive_rails"), limit=3)
    if any(rail not in SIDECAR_RAILS for rail in additive):
        _error()
    sidecar = _canonical_string_list(projection.get("applicable_sidecar_rails"), limit=3)
    if not sidecar or any(rail not in SIDECAR_RAILS for rail in sidecar):
        _error()
    treatments = projection.get("treatments")
    if not isinstance(treatments, dict) or set(treatments) != set(RAILS):
        _error()
    for rail in RAILS:
        row = _exact_dict(treatments.get(rail), frozenset({"treatment", "reasons"}))
        try:
            RailTreatment(row.get("treatment"))
        except (TypeError, ValueError) as exc:
            raise EvidenceRailApplicabilityError("INVALID_INPUT") from exc
        reasons = _string_list(row.get("reasons"), limit=len(REASON_CODES))
        if (
            not reasons
            or len(reasons) != len(set(reasons))
            or any(reason not in REASON_CODES for reason in reasons)
        ):
            _error()
    authority = projection.get("authority")
    if authority != dict(AUTHORITY) or any(value is not False for value in authority.values()):
        _error()
    return projection


def _captured_projection(raw: bytes | str) -> tuple[dict[str, Any], bytes]:
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not isinstance(raw_bytes, bytes) or len(raw_bytes) > MAX_CAPTURED_BYTES:
        _error()
    parsed = _strict_json_bytes(raw_bytes, limit=MAX_CAPTURED_BYTES)
    projection = _projection_mapping(parsed)
    canonical = json.dumps(
        projection,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    if raw_bytes not in {canonical, canonical + b"\n"}:
        _error()
    return projection, canonical


def validate_evidence_rail_applicability(
    value: bytes | str | Mapping[str, Any],
    snapshot: TaskPacketSnapshot,
) -> EvidenceRailApplicability:
    """Validate exact captured JSON and bind it to the current packet snapshot."""

    if not isinstance(snapshot, TaskPacketSnapshot):
        _error()
    if isinstance(value, (bytes, str)):
        projection, _canonical = _captured_projection(value)
    elif isinstance(value, Mapping):
        projection = _projection_mapping(dict(value))
    else:
        _error()
    if (
        projection["task_packet_id"] != snapshot.task_packet_id
        or projection["task_packet_fingerprint"] != snapshot.task_packet_fingerprint
    ):
        _error()
    expected = build_evidence_rail_applicability(
        snapshot,
        additive_rails=cast(list[str], projection["additive_rails"]),
    )
    if projection != expected.to_mapping():
        _error()
    return expected


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = _StrictArgumentParser(
        prog="evidence_rail_applicability",
        description="Build or validate one packet-bound evidence-rail treatment projection.",
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=_StrictArgumentParser
    )
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--packet", required=True)
    build_parser.add_argument(
        "--additive-rail",
        action="append",
        choices=SIDECAR_RAILS,
        default=[],
    )
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--packet", required=True)
    validate_parser.add_argument("--emit", choices=("sidecar-mask",), required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the sanitized local CLI."""

    try:
        args = _parse_args(argv)
        snapshot = read_task_packet_snapshot(args.packet)
        if args.command == "build":
            result = build_evidence_rail_applicability(
                snapshot,
                additive_rails=args.additive_rail,
            )
            sys.stdout.write(canonical_evidence_rail_json(result) + "\n")
            return 0
        raw = sys.stdin.buffer.read(MAX_CAPTURED_BYTES + 1)
        result = validate_evidence_rail_applicability(raw, snapshot)
        sys.stdout.write(",".join(result.applicable_sidecar_rails) + "\n")
        return 0
    except EvidenceRailApplicabilityError as exc:
        print(exc.category, file=sys.stderr)
        return 1
    except Exception:
        print("INTERNAL_ERROR", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
