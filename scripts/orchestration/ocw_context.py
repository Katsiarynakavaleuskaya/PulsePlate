"""Bounded advisory OCW delivery over independently admitted current inputs.

Canonical graph admission and serialization remain in core.evidence. This module
does not read source labels, execute tools, mutate answers or persist context.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, cast

from core.evidence.federation import ClaimNeighborhoodV1, QualifiedEvidenceRefV1
from core.evidence.fingerprints import _canonical_json_bytes, fingerprint_payload

MAX_OCW_BYTES = 65_536
POLICY_VERSION = "ocw1a-consumer-v1"
_BINDING_KEYS = frozenset(
    (
        "task_packet_id",
        "role_context_order",
        "run_id",
        "case_id",
        "message",
        "answer",
        "claim_ref",
        "context_ref",
        "time_scope",
        "input_fingerprint",
        "result_fingerprint",
    )
)
_SOURCE_KEYS = frozenset(("ref", "version", "content", "payload"))


def _bound_material(value: object) -> None:
    """Cheap aggregate admission before encoding or copying this closed material.

    This counts native container members, string characters and an integer
    decimal-digit lower bound without formatting the integer; native JSON
    encoding and the existing fingerprint owner still own JSON semantics. The
    conservative lower bound rejects oversized/cyclic input without allocating a
    hash preimage or a UTF-8 copy of its text.
    """
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        if depth > 32 or type(item) not in (dict, list, str, int, float, bool, type(None)):
            raise ValueError("ocw_json")
        if type(item) is float and not math.isfinite(item):
            raise ValueError("ocw_json")
        count += 1
        if type(item) is str:
            count += len(item)
        elif type(item) is int:
            count += max(0, item.bit_length() * 3 // 10 - 1)
        elif type(item) in (dict, list):
            collection = cast(dict[str, object] | list[object], item)
            count += len(collection)
            if count > MAX_OCW_BYTES:
                raise ValueError("ocw_wire_limit")
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError("ocw_json")
                pending.extend((key, depth + 1) for key in item)
                pending.extend((child, depth + 1) for child in item.values())
            else:
                pending.extend((child, depth + 1) for child in cast(list[object], item))
        if count > MAX_OCW_BYTES:
            raise ValueError("ocw_wire_limit")


def _binding(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _BINDING_KEYS:
        raise ValueError("ocw_invocation")
    data = cast(dict[str, Any], value)
    for key, item in data.items():
        if key == "role_context_order":
            if type(item) is not int or item < 1:
                raise ValueError("ocw_invocation")
        elif type(item) is not str or not item.strip():
            raise ValueError("ocw_invocation")
    return deepcopy(data)


def _sources(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) > 10_000:
        raise ValueError("ocw_source")
    sources = cast(list[object], value)
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in sources:
        if type(raw) is not dict or set(raw) != _SOURCE_KEYS:
            raise ValueError("ocw_source")
        source = cast(dict[str, Any], raw)
        ref = source["ref"]
        if type(ref) is not dict or set(ref) != {"namespace", "snapshot_fingerprint", "local_id"}:
            raise ValueError("ocw_source")
        if any(type(ref[key]) is not str for key in ref) or ref["namespace"] != "evidence.asset":
            raise ValueError("ocw_source")
        qualified = QualifiedEvidenceRefV1(**ref)
        qualified.to_dict()
        key = (qualified.namespace, qualified.snapshot_fingerprint, qualified.local_id)
        if key in seen:
            raise ValueError("ocw_source")
        seen.add(key)
        version, content, payload = source["version"], source["content"], source["payload"]
        if type(version) is not str or not version.strip():
            raise ValueError("ocw_source")
        if content is not None and type(content) is not str:
            raise ValueError("ocw_source_payload")
        result.append(deepcopy(source))
    return result


def validate_ocw_invocation(value: object) -> dict[str, Any]:
    """Validate caller-owned expectations, without deriving them from observations."""
    if type(value) is not dict or set(value) != {"binding", "sources"}:
        raise ValueError("ocw_invocation")
    _bound_material(value)
    data = cast(dict[str, Any], value)
    return {"binding": _binding(data["binding"]), "sources": _sources(data["sources"])}


def validate_ocw_wire_size(attachment: dict[str, Any], *, pretty: bool) -> int:
    """Measure the actual JSON value at outer-envelope depth one; reject whole."""
    if type(attachment) is not dict or type(pretty) is not bool:
        raise ValueError("ocw_json")
    _bound_material(attachment)
    encoder = json.JSONEncoder(
        ensure_ascii=False, indent=2 if pretty else None, sort_keys=False, allow_nan=False
    )
    # Native encoding of this one fixed outer member has exactly the same
    # indentation/escaping as its value in the final multi-member envelope.
    overhead = len(encoder.encode({"ocw_evidence": None}).encode("utf-8")) - len(b"null")
    size = 0
    try:
        for chunk in encoder.iterencode({"ocw_evidence": attachment}):
            size += len(chunk.encode("utf-8"))
            if size - overhead > MAX_OCW_BYTES:
                raise ValueError("ocw_wire_limit")
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError("ocw_json") from exc
    except ValueError as exc:
        if str(exc) == "ocw_wire_limit":
            raise
        raise ValueError("ocw_json") from exc
    return size - overhead


def build_ocw_evidence_attachment(
    neighborhood: ClaimNeighborhoodV1, *, expected_invocation: object, observed: object
) -> dict[str, Any]:
    """Deliver one exact current advisory observation and its canonical neighborhood."""
    if type(neighborhood) is not ClaimNeighborhoodV1:
        raise ValueError("neighborhood_binding")
    expected = validate_ocw_invocation(expected_invocation)
    if type(observed) is not dict or set(observed) != {
        "binding",
        "sources",
        "authority_granted",
        "answer_change_allowed",
    }:
        raise ValueError("ocw_binding")
    candidate = cast(dict[str, Any], observed)
    if (
        candidate["authority_granted"] is not False
        or candidate["answer_change_allowed"] is not False
    ):
        raise ValueError("ocw_authority")
    actual = validate_ocw_invocation(
        {"binding": candidate["binding"], "sources": candidate["sources"]}
    )
    validate_ocw_wire_size(expected, pretty=False)
    validate_ocw_wire_size(actual, pretty=False)
    if _canonical_json_bytes(actual) != _canonical_json_bytes(expected):
        raise ValueError("ocw_binding")
    graph = neighborhood.to_dict()
    binding = expected["binding"]
    if (
        binding["input_fingerprint"] != graph["input_fingerprint"]
        or binding["result_fingerprint"] != graph["result_fingerprint"]
        or {key: binding[key] for key in ("claim_ref", "context_ref", "time_scope")}
        != graph["query"]
    ):
        raise ValueError("ocw_binding")
    sources = expected["sources"]
    required_refs = [
        QualifiedEvidenceRefV1(
            "evidence.asset", binding["input_fingerprint"], item.asset.asset_id
        ).to_dict()
        for item in neighborhood.assets
    ]
    if [source["ref"] for source in sources] != required_refs:
        raise ValueError("ocw_source")
    delivered: list[dict[str, Any]] = []
    for source, item in zip(sources, neighborhood.assets):
        if source["version"] != item.asset.version:
            raise ValueError("ocw_source")
        content = source["content"]
        delivered.append(
            {
                **source,
                "content_status": (
                    "missing" if content is None else "empty" if not content.strip() else "loaded"
                ),
                "asset_payload_fingerprint": item.asset.fingerprint,
            }
        )
    attachment: dict[str, Any] = {
        "schema_version": "pulseplate.ocw-evidence.v1",
        "asset_type": "context_bundle",
        "rail": "advisory",
        "version": "v1",
        "policy_version": POLICY_VERSION,
        "invocation": binding,
        "neighborhood": graph,
        "sources": delivered,
        "upstream_refs": graph["upstream_refs"],
        "upstream_binding": "informational_source_refs_only",
        "replay_behavior": "read_only_exact_invocation",
        "admission_behavior": "independent_current_binding_and_canonical_neighborhood",
        "authority_granted": False,
        "answer_change_allowed": False,
    }
    validate_ocw_wire_size(attachment, pretty=False)
    for source, actual_source, item in zip(delivered, actual["sources"], neighborhood.assets):
        content = source["content"]
        # The asset owner's ORIGINAL JSON payload has no invented body schema.
        # Raw body/version match independent capture expectations separately.
        if content is not None and fingerprint_payload(source["payload"]) != item.asset.fingerprint:
            raise ValueError("ocw_source_payload")
        if (
            content is not None
            and fingerprint_payload(actual_source["payload"]) != item.asset.fingerprint
        ):
            raise ValueError("ocw_source_payload")
        source["body_sha256"] = (
            None
            if content is None
            else "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
        )
    validate_ocw_wire_size(attachment, pretty=False)
    attachment["material_fingerprint"] = fingerprint_payload(attachment)
    attachment["idempotency_key"] = fingerprint_payload(
        {
            "purpose": POLICY_VERSION,
            "invocation": binding,
            "material_fingerprint": attachment["material_fingerprint"],
        }
    )
    validate_ocw_wire_size(attachment, pretty=False)
    return attachment
