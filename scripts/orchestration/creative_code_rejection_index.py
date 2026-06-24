"""Build and validate fingerprint-only creative-code rejection indexes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)

SCHEMA_VERSION = "1.0"
INDEX_TYPE = "creative_code_rejection_index"
POLICY_VERSION = "creative-code-specification-pr1"
SUCCESS_OUTPUT = "PASS: creative-code rejection index valid"

SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization[:._-]?bearer|private[_.:-]?key)",
    re.IGNORECASE,
)
UNSAFE_TOKEN_SEGMENT_RE = re.compile(
    r"(^|[._:-])("
    r"candidate[._:-]?patch|provider[._:-]?payload|raw[._:-]?(prompt|response|context)|"
    r"openai|anthropic|slack|github|model|network|runtime|repository|worktree|"
    r"pull[._:-]?request|branch|merge|release|semantic[._:-]?cache"
    r")([._:-]|$)",
    re.IGNORECASE,
)

TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "index_type",
        "index_id",
        "idempotency_key",
        "policy_version",
        "source_packet_id",
        "source_packet_fingerprint",
        "records",
    }
)
RECORD_KEYS = frozenset(
    {
        "variant_id",
        "variant_fingerprint",
        "reason_codes",
        "reviewer_roles",
    }
)


class CreativeCodeRejectionIndexError(ValueError):
    """Raised when a creative-code rejection index violates PR-1 boundaries."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeRejectionIndexError(
                f"creative-code rejection index has duplicate JSON key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_creative_code_rejection_index(path: Path) -> dict[str, Any]:
    """Read a rejection index JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeRejectionIndexError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeRejectionIndexError(
            "Unable to read creative-code rejection index JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodeRejectionIndexError("CreativeCodeRejectionIndex must be a JSON object.")
    return payload


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual_keys = set(payload)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing:
        raise CreativeCodeRejectionIndexError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodeRejectionIndexError(f"{label} has unsupported fields: {', '.join(extra)}")


def _require_const(
    payload: Mapping[str, Any],
    key: str,
    expected: Any,
    *,
    label: str,
) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodeRejectionIndexError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_safe_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeRejectionIndexError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_ID_RE.fullmatch(normalized):
        raise CreativeCodeRejectionIndexError(f"{label}.{key} must be a safe identifier.")
    _reject_unsafe_label(normalized, label=f"{label}.{key}")
    return normalized


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodeRejectionIndexError(f"{label}.{key} must be a sha256 digest.")
    return value


def _reject_unsafe_label(value: str, *, label: str) -> None:
    if SECRET_RE.search(value) or UNSAFE_TOKEN_SEGMENT_RE.search(value):
        raise CreativeCodeRejectionIndexError(
            f"{label} must not contain unsafe creative-code authority labels."
        )


def _normalize_token_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeCodeRejectionIndexError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeCodeRejectionIndexError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeCodeRejectionIndexError(f"{label}.{key}[{index}] must be a string.")
        token = item.strip()
        if not token or not SAFE_TOKEN_RE.fullmatch(token):
            raise CreativeCodeRejectionIndexError(f"{label}.{key}[{index}] must be a safe token.")
        _reject_unsafe_label(token, label=f"{label}.{key}[{index}]")
        if token in seen:
            raise CreativeCodeRejectionIndexError(f"{label}.{key} must not contain duplicates.")
        seen.add(token)
        normalized.append(token)
    return normalized


def _validate_record(raw_record: Any, *, index: int) -> dict[str, Any]:
    label = f"CreativeCodeRejectionIndex.records[{index}]"
    if not isinstance(raw_record, dict):
        raise CreativeCodeRejectionIndexError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_record, RECORD_KEYS, label=label)
    return {
        "variant_id": _require_safe_id(raw_record, "variant_id", label=label),
        "variant_fingerprint": _require_fingerprint(
            raw_record,
            "variant_fingerprint",
            label=label,
        ),
        "reason_codes": _normalize_token_list(
            raw_record,
            "reason_codes",
            label=label,
            allow_empty=False,
        ),
        "reviewer_roles": _normalize_token_list(
            raw_record,
            "reviewer_roles",
            label=label,
            allow_empty=True,
        ),
    }


def _expected_identity(
    *,
    source_packet_id: str,
    source_packet_fingerprint: str,
    records: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    fingerprint = fingerprint_payload(
        {
            "policy_version": POLICY_VERSION,
            "records": list(records),
            "source_packet_fingerprint": source_packet_fingerprint,
            "source_packet_id": source_packet_id,
        }
    )
    upstream_ids = (source_packet_id, source_packet_fingerprint)
    index_id = build_asset_id(
        asset_type="creative_code_rejection_index",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type="creative_code_rejection_index",
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return index_id, idempotency_key


def build_creative_code_rejection_index(
    *,
    source_packet_id: str,
    source_packet_fingerprint: str,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic fingerprint-only rejected-variant index."""

    base_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "index_type": INDEX_TYPE,
        "index_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "source_packet_id": source_packet_id,
        "source_packet_fingerprint": source_packet_fingerprint,
        "records": list(records),
    }
    normalized = validate_creative_code_rejection_index(base_payload, verify_identity=False)
    index_id, idempotency_key = _expected_identity(
        source_packet_id=normalized["source_packet_id"],
        source_packet_fingerprint=normalized["source_packet_fingerprint"],
        records=normalized["records"],
    )
    normalized["index_id"] = index_id
    normalized["idempotency_key"] = idempotency_key
    return normalized


def validate_creative_code_rejection_index(
    payload: Mapping[str, Any],
    *,
    verify_identity: bool = True,
) -> dict[str, Any]:
    """Validate and normalize a PR-1 fingerprint-only rejection index."""

    _require_exact_keys(payload, TOP_LEVEL_KEYS, label="CreativeCodeRejectionIndex")
    normalized = {
        "schema_version": _require_const(
            payload,
            "schema_version",
            SCHEMA_VERSION,
            label="CreativeCodeRejectionIndex",
        ),
        "index_type": _require_const(
            payload,
            "index_type",
            INDEX_TYPE,
            label="CreativeCodeRejectionIndex",
        ),
        "index_id": _require_safe_id(payload, "index_id", label="CreativeCodeRejectionIndex"),
        "idempotency_key": _require_safe_id(
            payload,
            "idempotency_key",
            label="CreativeCodeRejectionIndex",
        ),
        "policy_version": _require_const(
            payload,
            "policy_version",
            POLICY_VERSION,
            label="CreativeCodeRejectionIndex",
        ),
        "source_packet_id": _require_safe_id(
            payload,
            "source_packet_id",
            label="CreativeCodeRejectionIndex",
        ),
        "source_packet_fingerprint": _require_fingerprint(
            payload,
            "source_packet_fingerprint",
            label="CreativeCodeRejectionIndex",
        ),
    }
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise CreativeCodeRejectionIndexError(
            "CreativeCodeRejectionIndex.records must be an array."
        )
    records = [_validate_record(record, index=index) for index, record in enumerate(raw_records)]
    variant_ids = [record["variant_id"] for record in records]
    variant_fingerprints = [record["variant_fingerprint"] for record in records]
    if len(set(variant_ids)) != len(variant_ids):
        raise CreativeCodeRejectionIndexError("records must not repeat variant_id.")
    if len(set(variant_fingerprints)) != len(variant_fingerprints):
        raise CreativeCodeRejectionIndexError("records must not repeat variant_fingerprint.")
    normalized["records"] = records
    if verify_identity:
        expected_id, expected_key = _expected_identity(
            source_packet_id=normalized["source_packet_id"],
            source_packet_fingerprint=normalized["source_packet_fingerprint"],
            records=records,
        )
        if normalized["index_id"] != expected_id:
            raise CreativeCodeRejectionIndexError("index_id does not match index content.")
        if normalized["idempotency_key"] != expected_key:
            raise CreativeCodeRejectionIndexError("idempotency_key does not match index content.")
    return normalized


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        payload = read_creative_code_rejection_index(args.validate)
        validate_creative_code_rejection_index(payload)
    except CreativeCodeRejectionIndexError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
