"""Validate governed creative-code candidate packets.

PR-0 is a closed authority contract only. The validator is intentionally
stricter than JSON parsing so unknown fields, duplicate keys, unsafe paths, and
authority expansion fail before any future implementation lane can consume a
packet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

from scripts.orchestration.experiment_contract import (
    validate_creative_research_origin,
    validate_mutable_candidate_surface,
)

SCHEMA_VERSION = "1.0"
PACKET_TYPE = "creative_code_candidate"
GATE_STATUS = "closed"
AUTHORITY_CLASS = "code-specification"
POLICY_VERSION = "creative-code-authority-pr0"
SUCCESS_OUTPUT = "PASS: creative-code candidate contract valid"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "packet_type",
        "candidate_id",
        "idempotency_key",
        "policy_version",
        "gate_status",
        "authority_class",
        "source_creative_research",
        "variant_count",
        "sandbox_required",
        "human_review_required",
        "fallback",
        "target_surface",
        "immutable_oracles",
        "authority",
        "scientific_claim_status",
        "evidence_bundle",
        "future_telemetry_contract",
    }
)
SOURCE_KEYS = frozenset(
    {"bundle_id", "candidate_id", "promotion_decision", "fingerprint", "evidence_ref"}
)
EVIDENCE_KEYS = frozenset({"artifact_refs", "required_tests", "negative_controls"})
FUTURE_TELEMETRY_KEYS = frozenset({"emit_no_earlier_than", "minimum_fields"})

AUTHORITY_TRUE_KEYS: tuple[str, ...] = ("generate_specifications",)
AUTHORITY_FALSE_KEYS: tuple[str, ...] = (
    "generate_candidate_patch",
    "write_repository",
    "write_shared_worktree",
    "create_branch",
    "push_branch",
    "open_pull_request",
    "open_draft_pr",
    "mark_ready_for_review",
    "resolve_review_threads",
    "merge",
    "release",
    "call_models",
    "call_network",
    "read_secrets",
    "modify_openapi_or_clients",
    "use_semantic_cache",
    "public_multi_tenant_use",
    "slack_github_authority_expansion",
)
AUTHORITY_KEYS = frozenset((*AUTHORITY_TRUE_KEYS, *AUTHORITY_FALSE_KEYS))

SCIENTIFIC_CLAIM_STATUSES = frozenset(
    {"hypothesis_only", "evidence_supported_plan", "inconclusive"}
)
FUTURE_TELEMETRY_FIELDS: tuple[str, ...] = (
    "packet_id",
    "source_candidate_id",
    "variant_count",
    "generation_status",
    "oracle_status",
    "failure_class",
    "human_decision",
    "cost_metadata_available",
)
FORBIDDEN_PATH_PREFIXES: tuple[str, ...] = (
    ".git/",
    ".github/workflows/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "artifacts/",
    "build/",
    "dist/",
    "node_modules/",
    "worktrees/",
)
FORBIDDEN_PATHS = frozenset(
    {
        ".git",
        ".github/workflows",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "artifacts",
        "build",
        "dist",
        "node_modules",
        "worktrees",
    }
)


class CreativeCodeContractError(ValueError):
    """Raised when a creative-code candidate packet violates PR-0 authority."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeContractError(
                f"creative-code candidate contract has duplicate JSON key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_creative_code_candidate_packet(path: Path) -> dict[str, Any]:
    """Read a JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeContractError(
            "Unable to read creative-code candidate contract JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodeContractError("CreativeCodeCandidatePacket must be a JSON object.")
    return payload


def _require_exact_keys(
    payload: dict[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual_keys = set(payload)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing:
        raise CreativeCodeContractError(f"{label} is missing required fields: {', '.join(missing)}")
    if extra:
        raise CreativeCodeContractError(f"{label} has unsupported fields: {', '.join(extra)}")


def _require_const(payload: dict[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodeContractError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: dict[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise CreativeCodeContractError(f"{label}.{key} must be non-empty.")
    if not ID_RE.fullmatch(normalized):
        raise CreativeCodeContractError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_non_empty_string(payload: dict[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise CreativeCodeContractError(f"{label}.{key} must be non-empty.")
    return normalized


def _require_string_list(
    payload: dict[str, Any],
    key: str,
    *,
    label: str,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise CreativeCodeContractError(f"{label}.{key} must be a non-empty array.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeCodeContractError(f"{label}.{key}[{index}] must be a string.")
        cleaned = item.strip()
        if not cleaned:
            raise CreativeCodeContractError(f"{label}.{key}[{index}] must be non-empty.")
        if cleaned in seen:
            raise CreativeCodeContractError(f"{label}.{key} must not contain duplicates.")
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _normalize_repo_relative_path(raw_path: str, *, label: str) -> str:
    if not isinstance(raw_path, str):
        raise CreativeCodeContractError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeCodeContractError(f"{label} must be non-empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeCodeContractError(f"{label} must not contain control characters.")
    if "\\" in value:
        raise CreativeCodeContractError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or Path(value).is_absolute():
        raise CreativeCodeContractError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeCodeContractError(f"{label} must not be a URL or scheme path.")

    path = PurePosixPath(value)
    parts = path.parts
    if not parts or "." in parts or ".." in parts:
        raise CreativeCodeContractError(f"{label} must not contain traversal segments.")
    normalized = path.as_posix()
    if normalized in FORBIDDEN_PATHS or any(
        normalized.startswith(prefix) for prefix in FORBIDDEN_PATH_PREFIXES
    ):
        raise CreativeCodeContractError(f"{label} points to a forbidden local surface.")
    return normalized


def _validate_repo_relative_path_list(
    payload: dict[str, Any],
    key: str,
    *,
    label: str,
) -> list[str]:
    raw_items = _require_string_list(payload, key, label=label)
    normalized: list[str] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(raw_items):
        path = _normalize_repo_relative_path(raw_item, label=f"{label}.{key}[{index}]")
        if path in seen:
            raise CreativeCodeContractError(f"{label}.{key} must not contain duplicates.")
        seen.add(path)
        normalized.append(path)
    return normalized


def _paths_overlap(left: str, right: str) -> bool:
    left_prefix = left.rstrip("/") + "/"
    right_prefix = right.rstrip("/") + "/"
    return left == right or left.startswith(right_prefix) or right.startswith(left_prefix)


def _validate_source(raw_source: Any) -> dict[str, str]:
    if not isinstance(raw_source, dict):
        raise CreativeCodeContractError(
            "CreativeCodeCandidatePacket.source_creative_research must be a JSON object."
        )
    _require_exact_keys(
        raw_source,
        SOURCE_KEYS,
        label="CreativeCodeCandidatePacket.source_creative_research",
    )
    source = {
        "bundle_id": _require_id(
            raw_source,
            "bundle_id",
            label="CreativeCodeCandidatePacket.source_creative_research",
        ),
        "candidate_id": _require_id(
            raw_source,
            "candidate_id",
            label="CreativeCodeCandidatePacket.source_creative_research",
        ),
        "promotion_decision": _require_non_empty_string(
            raw_source,
            "promotion_decision",
            label="CreativeCodeCandidatePacket.source_creative_research",
        ).lower(),
        "fingerprint": _require_non_empty_string(
            raw_source,
            "fingerprint",
            label="CreativeCodeCandidatePacket.source_creative_research",
        ),
        "evidence_ref": _normalize_repo_relative_path(
            _require_non_empty_string(
                raw_source,
                "evidence_ref",
                label="CreativeCodeCandidatePacket.source_creative_research",
            ),
            label="CreativeCodeCandidatePacket.source_creative_research.evidence_ref",
        ),
    }
    try:
        validate_creative_research_origin(
            {
                "bundle_id": source["bundle_id"],
                "candidate_id": source["candidate_id"],
                "promotion_decision": source["promotion_decision"],
            }
        )
    except ValueError as exc:
        raise CreativeCodeContractError(str(exc)) from exc
    if source["promotion_decision"] != "promote":
        raise CreativeCodeContractError(
            "source_creative_research.promotion_decision must equal 'promote'."
        )
    if not SHA256_RE.fullmatch(source["fingerprint"]):
        raise CreativeCodeContractError(
            "source_creative_research.fingerprint must be a sha256 digest."
        )
    return source


def _validate_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodeContractError(
            "CreativeCodeCandidatePacket.authority must be a JSON object."
        )
    _require_exact_keys(
        raw_authority, AUTHORITY_KEYS, label="CreativeCodeCandidatePacket.authority"
    )
    for key in AUTHORITY_TRUE_KEYS:
        if raw_authority.get(key) is not True:
            raise CreativeCodeContractError(f"authority.{key} must remain true in PR-0.")
    for key in AUTHORITY_FALSE_KEYS:
        if raw_authority.get(key) is not False:
            raise CreativeCodeContractError(f"authority.{key} must remain false in PR-0.")
    return {key: bool(raw_authority[key]) for key in AUTHORITY_KEYS}


def _validate_evidence_bundle(raw_evidence: Any) -> dict[str, list[str]]:
    if not isinstance(raw_evidence, dict):
        raise CreativeCodeContractError(
            "CreativeCodeCandidatePacket.evidence_bundle must be a JSON object."
        )
    _require_exact_keys(
        raw_evidence,
        EVIDENCE_KEYS,
        label="CreativeCodeCandidatePacket.evidence_bundle",
    )
    return {
        "artifact_refs": _validate_repo_relative_path_list(
            raw_evidence,
            "artifact_refs",
            label="CreativeCodeCandidatePacket.evidence_bundle",
        ),
        "required_tests": _validate_repo_relative_path_list(
            raw_evidence,
            "required_tests",
            label="CreativeCodeCandidatePacket.evidence_bundle",
        ),
        "negative_controls": _require_string_list(
            raw_evidence,
            "negative_controls",
            label="CreativeCodeCandidatePacket.evidence_bundle",
        ),
    }


def _validate_future_telemetry(raw_telemetry: Any) -> dict[str, Any]:
    if not isinstance(raw_telemetry, dict):
        raise CreativeCodeContractError(
            "CreativeCodeCandidatePacket.future_telemetry_contract must be a JSON object."
        )
    _require_exact_keys(
        raw_telemetry,
        FUTURE_TELEMETRY_KEYS,
        label="CreativeCodeCandidatePacket.future_telemetry_contract",
    )
    _require_const(
        raw_telemetry,
        "emit_no_earlier_than",
        "PR-1",
        label="CreativeCodeCandidatePacket.future_telemetry_contract",
    )
    fields = _require_string_list(
        raw_telemetry,
        "minimum_fields",
        label="CreativeCodeCandidatePacket.future_telemetry_contract",
    )
    if set(fields) != set(FUTURE_TELEMETRY_FIELDS) or len(fields) != len(FUTURE_TELEMETRY_FIELDS):
        raise CreativeCodeContractError(
            "future_telemetry_contract.minimum_fields must match the PR-0 field set."
        )
    return {"emit_no_earlier_than": "PR-1", "minimum_fields": fields}


def validate_creative_code_candidate_packet(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a PR-0 creative-code candidate packet."""

    _require_exact_keys(payload, TOP_LEVEL_KEYS, label="CreativeCodeCandidatePacket")
    normalized: dict[str, Any] = {
        "schema_version": _require_const(
            payload, "schema_version", SCHEMA_VERSION, label="CreativeCodeCandidatePacket"
        ),
        "packet_type": _require_const(
            payload, "packet_type", PACKET_TYPE, label="CreativeCodeCandidatePacket"
        ),
        "candidate_id": _require_id(payload, "candidate_id", label="CreativeCodeCandidatePacket"),
        "idempotency_key": _require_id(
            payload, "idempotency_key", label="CreativeCodeCandidatePacket"
        ),
        "policy_version": _require_const(
            payload, "policy_version", POLICY_VERSION, label="CreativeCodeCandidatePacket"
        ),
        "gate_status": _require_const(
            payload, "gate_status", GATE_STATUS, label="CreativeCodeCandidatePacket"
        ),
        "authority_class": _require_const(
            payload,
            "authority_class",
            AUTHORITY_CLASS,
            label="CreativeCodeCandidatePacket",
        ),
        "source_creative_research": _validate_source(payload["source_creative_research"]),
    }

    variant_count = payload.get("variant_count")
    if not isinstance(variant_count, int) or isinstance(variant_count, bool):
        raise CreativeCodeContractError("variant_count must be an integer.")
    if not 3 <= variant_count <= 5:
        raise CreativeCodeContractError("variant_count must be between 3 and 5.")
    normalized["variant_count"] = variant_count

    if payload.get("sandbox_required") is not True:
        raise CreativeCodeContractError("sandbox_required must be true.")
    if payload.get("human_review_required") is not True:
        raise CreativeCodeContractError("human_review_required must be true.")
    normalized["sandbox_required"] = True
    normalized["human_review_required"] = True
    normalized["fallback"] = _require_non_empty_string(
        payload, "fallback", label="CreativeCodeCandidatePacket"
    )

    target_surface = _validate_repo_relative_path_list(
        payload, "target_surface", label="CreativeCodeCandidatePacket"
    )
    immutable_oracles = _validate_repo_relative_path_list(
        payload, "immutable_oracles", label="CreativeCodeCandidatePacket"
    )
    try:
        normalized["target_surface"] = validate_mutable_candidate_surface(target_surface)
    except ValueError as exc:
        raise CreativeCodeContractError(str(exc)) from exc
    normalized["immutable_oracles"] = immutable_oracles

    for target in normalized["target_surface"]:
        for oracle in immutable_oracles:
            if _paths_overlap(target, oracle):
                raise CreativeCodeContractError(
                    "target_surface must not overlap immutable_oracles."
                )

    normalized["authority"] = _validate_authority(payload["authority"])
    scientific_status = _require_non_empty_string(
        payload, "scientific_claim_status", label="CreativeCodeCandidatePacket"
    )
    if scientific_status not in SCIENTIFIC_CLAIM_STATUSES:
        raise CreativeCodeContractError(
            "scientific_claim_status must not overclaim verified discovery."
        )
    normalized["scientific_claim_status"] = scientific_status
    normalized["evidence_bundle"] = _validate_evidence_bundle(payload["evidence_bundle"])
    normalized["future_telemetry_contract"] = _validate_future_telemetry(
        payload["future_telemetry_contract"]
    )
    return normalized


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        payload = read_creative_code_candidate_packet(args.validate)
        validate_creative_code_candidate_packet(payload)
    except CreativeCodeContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
