"""Deterministic offline projection of explicit review-invariant families.

The CLI reads one closed JSON document from stdin and writes one canonical
relations artifact to stdout.  It has no repository, provider, runtime, or
review-thread authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Mapping
from itertools import combinations
from types import MappingProxyType
from typing import NoReturn, cast

SNAPSHOT_SCHEMA_VERSION = "review_invariant_family_snapshot.v1"
ARTIFACT_SCHEMA_VERSION = "review_invariant_family_relations.v1"
POLICY_VERSION = "review_invariant_family_relations.policy.v1"

MAX_STDIN_BYTES = 1_048_576
MAX_STDOUT_BYTES = 1_048_576
MAX_STDERR_BYTES = 4_096
MAX_FINDINGS = 2_048
MAX_FAMILIES = 32
MAX_MEMBERSHIPS = 4_096
MAX_RELATION_RECORDS = 496
MAX_DERIVED_PARTITION_REFS = 2_048
MAX_ID_ASCII_BYTES = 64

SNAPSHOT_DIGEST_DOMAIN = b"pulseplate.review-invariant-family.snapshot-core.v1"
ARTIFACT_DIGEST_DOMAIN = b"pulseplate.review-invariant-family.artifact-core.v1"

RELATION_VALUES: tuple[str, ...] = (
    "equal",
    "left_proper_subset",
    "right_proper_subset",
    "partial_overlap",
    "disjoint",
)

AUTHORITY_FIELDS: tuple[str, ...] = (
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
    "merge_authority",
)

_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?$", re.ASCII)
_FORBIDDEN_ID_PATTERN = (
    r"(?:[Aa][Cc][Cc][Ee][Ss][Ss][_-]?[Kk][Ee][Yy]|"
    r"[Aa][Ii][Zz][Aa]|[Aa][KkSs][Ii][Aa]|[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|"
    r"[Aa][Uu][Tt][Hh][Oo][Rr][Ii][Zz][Aa][Tt][Ii][Oo][Nn]|"
    r"[Bb][Ee][Aa][Rr][Ee][Rr]|[Cc][Ll][Ii][Ee][Nn][Tt][_-]?[Ss][Ee][Cc][Rr][Ee][Tt]|"
    r"[Cc][Rr][Ee][Dd][Ee][Nn][Tt][Ii][Aa][Ll]|[Gg][Hh][PpOoUuSsRr]_|"
    r"[Gg][Ll][Pp][Aa][Tt]-|"
    r"[Gg][Ii][Tt][Hh][Uu][Bb][_-]?[Pp][Aa][Tt]|[Nn][Pp][Mm]_|"
    r"[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|"
    r"[Pp][Rr][Ii][Vv][Aa][Tt][Ee][_-]?[Kk][Ee][Yy]|[Ss][Ee][Cc][Rr][Ee][Tt]|"
    r"[Ss][Kk][_-]?(?:[Ll][Ii][Vv][Ee]|[Tt][Ee][Ss][Tt]|[Pp][Rr][Oo][Jj])|"
    r"[Tt][Oo][Kk][Ee][Nn]|[Xx][Aa][Pp][Pp]-|[Xx][Oo][Xx][AaBbCcPpRrSs]-)"
)
_FORBIDDEN_ID_RE = re.compile(_FORBIDDEN_ID_PATTERN, re.ASCII)
_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$", re.ASCII)
_IDEMPOTENCY_RE = re.compile(
    r"^review-invariant-family-relations\.v1:[a-f0-9]{64}$",
    re.ASCII,
)


def _freeze(value: object) -> object:
    """Recursively freeze the static policy projection."""

    if isinstance(value, dict):
        frozen = {key: _freeze(item) for key, item in value.items()}
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


POLICY_PROJECTION: Mapping[str, object] = cast(
    Mapping[str, object],
    _freeze(
        {
            "policy_version": POLICY_VERSION,
            "schema_versions": {
                "snapshot": SNAPSHOT_SCHEMA_VERSION,
                "relations": ARTIFACT_SCHEMA_VERSION,
            },
            "bounds": {
                "max_stdin_bytes": MAX_STDIN_BYTES,
                "max_stdout_bytes": MAX_STDOUT_BYTES,
                "max_stderr_bytes": MAX_STDERR_BYTES,
                "max_findings": MAX_FINDINGS,
                "max_families": MAX_FAMILIES,
                "max_memberships": MAX_MEMBERSHIPS,
                "max_relation_records": MAX_RELATION_RECORDS,
                "max_derived_partition_refs": MAX_DERIVED_PARTITION_REFS,
                "max_id_ascii_bytes": MAX_ID_ASCII_BYTES,
            },
            "id_pattern": _ID_RE.pattern,
            "forbidden_id_pattern": _FORBIDDEN_ID_PATTERN,
            "relation_values": list(RELATION_VALUES),
            "authority_fields": list(AUTHORITY_FIELDS),
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
                "similarity",
            ],
            "canonicalization": {
                "json": "ascii_compact_sorted_keys",
                "stdout_terminator": "one_lf",
                "utf8_bom_policy": "reject",
                "numeric_lexeme_policy": "reject_all",
                "membership_source": "explicit_only",
                "pair_order": "family_id_lexicographic",
                "partition_order": "finding_id_lexicographic",
            },
            "digests": {
                "algorithm": "sha256",
                "separator": "nul",
                "snapshot_core_domain": SNAPSHOT_DIGEST_DOMAIN.decode("ascii"),
                "artifact_core_domain": ARTIFACT_DIGEST_DOMAIN.decode("ascii"),
                "artifact_core_excludes": [
                    "artifact_fingerprint",
                    "idempotency_key",
                ],
                "idempotency_uses_full_artifact_digest": True,
            },
        }
    ),
)

_SNAPSHOT_KEYS = frozenset(
    {
        "schema_version",
        "universe_finding_ids",
        "families",
        *AUTHORITY_FIELDS,
    }
)
_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "policy_version",
        "snapshot",
        "snapshot_fingerprint",
        "relations",
        "unknown_finding_ids",
        "artifact_fingerprint",
        "idempotency_key",
        *AUTHORITY_FIELDS,
    }
)
_FAMILY_KEYS = frozenset({"family_id", "finding_ids"})
_RELATION_KEYS = frozenset(
    {
        "left_family_id",
        "right_family_id",
        "relation",
        "intersection_finding_ids",
        "left_only_finding_ids",
        "right_only_finding_ids",
    }
)

_SAFE_ERROR_CODES = frozenset(
    {
        "arguments_not_allowed",
        "stdin_too_large",
        "stdin_empty",
        "utf8_bom_not_allowed",
        "invalid_utf8",
        "invalid_json",
        "duplicate_key",
        "numeric_token_not_allowed",
        "document_not_object",
        "schema_branch_not_recognized",
        "schema_validation_failed",
        "authority_boundary_violation",
        "invalid_id",
        "duplicate_id",
        "finding_limit_exceeded",
        "family_limit_exceeded",
        "membership_limit_exceeded",
        "membership_outside_universe",
        "relation_limit_exceeded",
        "derived_partition_ref_limit_exceeded",
        "artifact_replay_mismatch",
        "stdout_too_large",
        "output_transport_failure",
        "internal_error",
    }
)


class ContractError(Exception):
    """Sanitized, stable contract failure."""

    def __init__(self, code: str) -> None:
        safe_code = code if code in _SAFE_ERROR_CODES else "internal_error"
        self.code = safe_code
        super().__init__(safe_code)


def _raise_duplicate_key(_pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in _pairs:
        if key in result:
            raise ContractError("duplicate_key")
        result[key] = value
    return result


def _reject_numeric_token(_raw: str) -> NoReturn:
    raise ContractError("numeric_token_not_allowed")


def _strict_json_document(raw: bytes) -> object:
    if not raw:
        raise ContractError("stdin_empty")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ContractError("utf8_bom_not_allowed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("invalid_utf8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_raise_duplicate_key,
            parse_int=_reject_numeric_token,
            parse_float=_reject_numeric_token,
            parse_constant=_reject_numeric_token,
        )
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError("invalid_json") from exc


def _require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ContractError("schema_validation_failed")
    return cast(dict[str, object], value)


def _require_array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ContractError("schema_validation_failed")
    return cast(list[object], value)


def _require_exact_keys(value: Mapping[str, object], expected: frozenset[str]) -> None:
    if frozenset(value) != expected:
        raise ContractError("schema_validation_failed")


def _require_false_authority(value: Mapping[str, object]) -> None:
    for field in AUTHORITY_FIELDS:
        if value.get(field) is not False:
            raise ContractError("authority_boundary_violation")


def _require_id(value: object) -> str:
    if not isinstance(value, str):
        raise ContractError("invalid_id")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_id") from exc
    if (
        len(encoded) > MAX_ID_ASCII_BYTES
        or _ID_RE.fullmatch(value) is None
        or _FORBIDDEN_ID_RE.search(value) is not None
    ):
        raise ContractError("invalid_id")
    return value


def _normalize_id_list(
    value: object,
    *,
    maximum: int,
    limit_code: str,
) -> list[str]:
    raw_items = _require_array(value)
    if len(raw_items) > maximum:
        raise ContractError(limit_code)
    normalized = [_require_id(item) for item in raw_items]
    if len(set(normalized)) != len(normalized):
        raise ContractError("duplicate_id")
    return sorted(normalized)


def _choose_two(count: int) -> int:
    return count * (count - 1) // 2


def _precompute_partition_reference_count(
    universe: list[str],
    families: list[dict[str, object]],
) -> int:
    family_count = len(families)
    pair_count = _choose_two(family_count)
    if pair_count > MAX_RELATION_RECORDS:
        raise ContractError("relation_limit_exceeded")

    membership_counts = {finding_id: 0 for finding_id in universe}
    for family in families:
        for finding_id in cast(list[str], family["finding_ids"]):
            membership_counts[finding_id] += 1

    derived_refs = 0
    for membership_count in membership_counts.values():
        absent_count = family_count - membership_count
        derived_refs += pair_count - _choose_two(absent_count)
        if derived_refs > MAX_DERIVED_PARTITION_REFS:
            raise ContractError("derived_partition_ref_limit_exceeded")
    return derived_refs


def _normalize_snapshot(value: object) -> dict[str, object]:
    snapshot = _require_object(value)
    _require_exact_keys(snapshot, _SNAPSHOT_KEYS)
    _require_false_authority(snapshot)
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ContractError("schema_validation_failed")

    universe = _normalize_id_list(
        snapshot.get("universe_finding_ids"),
        maximum=MAX_FINDINGS,
        limit_code="finding_limit_exceeded",
    )
    universe_set = set(universe)
    raw_families = _require_array(snapshot.get("families"))
    if len(raw_families) > MAX_FAMILIES:
        raise ContractError("family_limit_exceeded")

    families: list[dict[str, object]] = []
    seen_family_ids: set[str] = set()
    membership_count = 0
    for raw_family in raw_families:
        family = _require_object(raw_family)
        _require_exact_keys(family, _FAMILY_KEYS)
        family_id = _require_id(family.get("family_id"))
        if family_id in seen_family_ids:
            raise ContractError("duplicate_id")
        seen_family_ids.add(family_id)
        finding_ids = _normalize_id_list(
            family.get("finding_ids"),
            maximum=MAX_FINDINGS,
            limit_code="finding_limit_exceeded",
        )
        membership_count += len(finding_ids)
        if membership_count > MAX_MEMBERSHIPS:
            raise ContractError("membership_limit_exceeded")
        if not set(finding_ids).issubset(universe_set):
            raise ContractError("membership_outside_universe")
        families.append({"family_id": family_id, "finding_ids": finding_ids})

    families.sort(key=lambda item: cast(str, item["family_id"]))
    _precompute_partition_reference_count(universe, families)

    normalized: dict[str, object] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "universe_finding_ids": universe,
        "families": families,
    }
    for field in AUTHORITY_FIELDS:
        normalized[field] = False
    return normalized


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ContractError("internal_error") from exc


def _domain_digest(domain: bytes, core: object) -> str:
    digest = hashlib.sha256(domain + b"\0" + _canonical_json_bytes(core)).hexdigest()
    return digest


def _relation_name(left: set[str], right: set[str]) -> str:
    if left == right:
        return "equal"
    if left < right:
        return "left_proper_subset"
    if right < left:
        return "right_proper_subset"
    if left.intersection(right):
        return "partial_overlap"
    return "disjoint"


def _build_artifact(normalized_snapshot: dict[str, object]) -> dict[str, object]:
    raw_families = cast(list[dict[str, object]], normalized_snapshot["families"])
    family_sets = {
        cast(str, family["family_id"]): set(cast(list[str], family["finding_ids"]))
        for family in raw_families
    }
    relations: list[dict[str, object]] = []
    for left_family, right_family in combinations(raw_families, 2):
        left_id = cast(str, left_family["family_id"])
        right_id = cast(str, right_family["family_id"])
        left = family_sets[left_id]
        right = family_sets[right_id]
        relations.append(
            {
                "left_family_id": left_id,
                "right_family_id": right_id,
                "relation": _relation_name(left, right),
                "intersection_finding_ids": sorted(left.intersection(right)),
                "left_only_finding_ids": sorted(left.difference(right)),
                "right_only_finding_ids": sorted(right.difference(left)),
            }
        )

    known_finding_ids: set[str] = set()
    for family_set in family_sets.values():
        known_finding_ids.update(family_set)
    universe = cast(list[str], normalized_snapshot["universe_finding_ids"])
    unknown = sorted(set(universe).difference(known_finding_ids))

    snapshot_digest = _domain_digest(SNAPSHOT_DIGEST_DOMAIN, normalized_snapshot)
    artifact_core: dict[str, object] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "snapshot": normalized_snapshot,
        "snapshot_fingerprint": f"sha256:{snapshot_digest}",
        "relations": relations,
        "unknown_finding_ids": unknown,
    }
    for field in AUTHORITY_FIELDS:
        artifact_core[field] = False

    artifact_digest = _domain_digest(ARTIFACT_DIGEST_DOMAIN, artifact_core)
    artifact = dict(artifact_core)
    artifact["artifact_fingerprint"] = f"sha256:{artifact_digest}"
    artifact["idempotency_key"] = f"review-invariant-family-relations.v1:{artifact_digest}"
    return artifact


def _validate_artifact_shape(value: object) -> dict[str, object]:
    artifact = _require_object(value)
    _require_exact_keys(artifact, _ARTIFACT_KEYS)
    _require_false_authority(artifact)
    if artifact.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ContractError("schema_validation_failed")
    if artifact.get("policy_version") != POLICY_VERSION:
        raise ContractError("schema_validation_failed")

    snapshot_fingerprint = artifact.get("snapshot_fingerprint")
    artifact_fingerprint = artifact.get("artifact_fingerprint")
    idempotency_key = artifact.get("idempotency_key")
    if (
        not isinstance(snapshot_fingerprint, str)
        or _DIGEST_RE.fullmatch(snapshot_fingerprint) is None
    ):
        raise ContractError("schema_validation_failed")
    if (
        not isinstance(artifact_fingerprint, str)
        or _DIGEST_RE.fullmatch(artifact_fingerprint) is None
    ):
        raise ContractError("schema_validation_failed")
    if not isinstance(idempotency_key, str) or _IDEMPOTENCY_RE.fullmatch(idempotency_key) is None:
        raise ContractError("schema_validation_failed")

    normalized_snapshot = _normalize_snapshot(artifact.get("snapshot"))
    raw_relations = _require_array(artifact.get("relations"))
    if len(raw_relations) > MAX_RELATION_RECORDS:
        raise ContractError("relation_limit_exceeded")
    submitted_partition_refs = 0
    for raw_relation in raw_relations:
        relation = _require_object(raw_relation)
        _require_exact_keys(relation, _RELATION_KEYS)
        _require_id(relation.get("left_family_id"))
        _require_id(relation.get("right_family_id"))
        if relation.get("relation") not in RELATION_VALUES:
            raise ContractError("schema_validation_failed")
        for field in (
            "intersection_finding_ids",
            "left_only_finding_ids",
            "right_only_finding_ids",
        ):
            submitted_partition = _normalize_id_list(
                relation.get(field),
                maximum=MAX_DERIVED_PARTITION_REFS,
                limit_code="derived_partition_ref_limit_exceeded",
            )
            submitted_partition_refs += len(submitted_partition)
            if submitted_partition_refs > MAX_DERIVED_PARTITION_REFS:
                raise ContractError("derived_partition_ref_limit_exceeded")
    _normalize_id_list(
        artifact.get("unknown_finding_ids"),
        maximum=MAX_FINDINGS,
        limit_code="finding_limit_exceeded",
    )
    return normalized_snapshot


def process_document(value: object) -> dict[str, object]:
    """Validate one schema branch and return the recomputed canonical artifact."""

    if not isinstance(value, dict):
        raise ContractError("document_not_object")
    document = cast(dict[str, object], value)
    schema_version = document.get("schema_version")
    if schema_version == SNAPSHOT_SCHEMA_VERSION:
        return _build_artifact(_normalize_snapshot(document))
    if schema_version == ARTIFACT_SCHEMA_VERSION:
        normalized_snapshot = _validate_artifact_shape(document)
        recomputed = _build_artifact(normalized_snapshot)
        if document != recomputed:
            raise ContractError("artifact_replay_mismatch")
        return recomputed
    raise ContractError("schema_branch_not_recognized")


def process_input_bytes(raw: bytes) -> bytes:
    """Process bounded stdin bytes without writing either transport stream."""

    if len(raw) > MAX_STDIN_BYTES:
        raise ContractError("stdin_too_large")
    artifact = process_document(_strict_json_document(raw))
    rendered = _canonical_json_bytes(artifact) + b"\n"
    if len(rendered) > MAX_STDOUT_BYTES:
        raise ContractError("stdout_too_large")
    return rendered


def _write_contract_error(code: str) -> None:
    safe_code = code if code in _SAFE_ERROR_CODES else "internal_error"
    payload = f"contract_error:{safe_code}\n".encode("ascii")
    payload = payload[:MAX_STDERR_BYTES]
    try:
        sys.stderr.buffer.write(payload)
        sys.stderr.buffer.flush()
    except (OSError, ValueError):
        try:
            sys.stderr.close()
        except (OSError, ValueError):
            pass
        return


def main() -> int:
    """Run the stdin/stdout CLI with fail-closed, buffered output."""

    if len(sys.argv) != 1:
        _write_contract_error("arguments_not_allowed")
        return 2
    try:
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
        rendered = process_input_bytes(raw)
    except ContractError as exc:
        _write_contract_error(exc.code)
        return 2
    except Exception:
        _write_contract_error("internal_error")
        return 2

    try:
        written = sys.stdout.buffer.write(rendered)
        if written != len(rendered):
            raise OSError("short stdout write")
        sys.stdout.buffer.flush()
    except (OSError, ValueError):
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        _write_contract_error("output_transport_failure")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
