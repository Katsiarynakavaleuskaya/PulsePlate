"""Closed terminal-outcome contract for governed creative-code promotions.

The terminal outcome is a local, sanitized observation over one validated PR-3
promotion lineage. It is not review, merge-readiness, provider, product-runtime,
or repository authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, cast

from core.evidence.events import EvidenceEvalEvent, create_eval_event
from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from core.evidence.policies import normalize_upstream_ids
from scripts.orchestration.creative_code_pr_promotion_contract import (
    CreativeCodePRPromotionContractError,
    promotion_plan_fingerprint,
    validate_creative_code_pr_promotion_plan,
    validate_creative_code_pr_promotion_receipt,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    CreativeCodeTelemetryContractError,
    normalize_cost_metadata,
    reject_unsafe_telemetry_value,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-code-terminal-outcome-v1"
ARTIFACT_TYPE = "creative_code_terminal_outcome"
SUCCESS_OUTPUT = "PASS: creative-code terminal outcome valid"
MAX_JSON_OBJECT_BYTES = 1_048_576
MAX_EVIDENCE_PROJECTION_BYTES = 65_536
MAX_CLOSURE_EPOCH = 1_000_000
CANONICAL_REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
EVIDENCE_PROJECTION_POLICY_VERSION = "creative-code-terminal-outcome-evidence-v1"
EVIDENCE_PROJECTION_SOURCE_ARTIFACT = (
    "docs/orchestration/contracts/creative_code_terminal_outcome.v1.schema.json"
)
EVIDENCE_PROJECTION_PRODUCER_NAME = "creative_code_terminal_outcome"
EVIDENCE_PROJECTION_PRODUCER_VERSION = "1.0"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PROMOTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
RFC3339_RE = re.compile(
    r"^(?P<base>[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]+)?(?P<offset>[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)

TERMINAL_STATES = frozenset({"merged", "closed_unmerged"})
CLOSED_REASON_CODES = frozenset(
    {
        "superseded",
        "abandoned",
        "validation_failed",
        "governance_blocked",
        "rescoped",
        "unknown",
    }
)
REVIEW_COLLECTION_STATES = frozenset({"complete", "unavailable"})
REVIEW_OBSERVATIONS = frozenset(
    {"actionables_observed", "no_actionables_observed", "evidence_unavailable"}
)
GOVERNANCE_OBSERVATIONS = frozenset(
    {"blockers_observed", "no_blockers_observed", "evidence_unavailable"}
)
POST_MERGE_OBSERVATIONS = frozenset(
    {
        "complete_observed",
        "incomplete_observed",
        "evidence_unavailable",
        "not_applicable",
    }
)
CURRENT_MAIN_CI_STATES = frozenset({"success", "failure", "not_observed"})

OBSERVATION_KEYS = frozenset(
    {
        "promotion_id",
        "repository",
        "pull_request_number",
        "promoted_head_sha",
        "closure_epoch",
        "terminal_state",
        "merge_sha",
        "reason_code",
        "review",
        "post_merge",
        "process",
        "cost_metadata",
        "sanitized",
    }
)
REVIEW_KEYS = frozenset(
    {
        "collection_state",
        "inventory_fingerprint",
        "review_seal_fingerprint",
        "sources_configured",
        "sources_observed",
        "findings_total",
        "fixed",
        "not_a_bug",
        "deferred",
        "unresolved_actionable",
    }
)
POST_MERGE_KEYS = frozenset(
    {
        "validation_inventory_fingerprint",
        "commands_configured",
        "commands_executed",
        "commands_passed",
        "current_main_ci",
        "current_main_sha",
    }
)
PROCESS_KEYS = frozenset({"review_cycles", "repair_cycles", "validation_attempts"})
LINEAGE_KEYS = frozenset(
    {
        "promotion_id",
        "source_request_id",
        "source_result_id",
        "source_bundle_id",
        "selected_variant_id",
        "receipt_id",
        "plan_fingerprint",
        "validation_fingerprint",
        "approval_id",
        "patch_fingerprint",
        "repository",
        "pull_request_number",
        "base_sha",
        "promoted_head_sha",
    }
)
OUTCOME_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "outcome_id",
        "idempotency_key",
        "lineage",
        "closure_epoch",
        "terminal_state",
        "merge_sha",
        "reason_code",
        "review_evidence",
        "review_observation",
        "governance_observation",
        "post_merge_evidence",
        "post_merge_observation",
        "process",
        "cost_metadata",
        "sanitized",
    }
)


class CreativeCodeTerminalOutcomeError(ValueError):
    """Raised when terminal evidence or lineage is invalid."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeTerminalOutcomeError("terminal outcome JSON has a duplicate key.")
        seen.add(key)
        payload[key] = value
    return payload


def _reject_non_finite_json_constant(value: str) -> None:
    raise CreativeCodeTerminalOutcomeError(f"non-finite JSON value is forbidden: {value}")


def decode_terminal_outcome_bytes(raw: bytes) -> dict[str, Any]:
    """Decode one bounded terminal-outcome object from the exact supplied bytes."""

    if len(raw) > MAX_JSON_OBJECT_BYTES:
        raise CreativeCodeTerminalOutcomeError("terminal_json_too_large")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CreativeCodeTerminalOutcomeError("terminal_json_bom_rejected")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
            parse_constant=_reject_non_finite_json_constant,
        )
    except CreativeCodeTerminalOutcomeError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise CreativeCodeTerminalOutcomeError("terminal_json_read_failed") from exc
    if not isinstance(payload, dict):
        raise CreativeCodeTerminalOutcomeError("terminal JSON must be an object.")
    return payload


def read_json_object(path: str | Path) -> dict[str, Any]:
    """Read one JSON object while rejecting duplicate keys and unsafe encodings."""

    try:
        source = Path(path)
        info = source.stat()
        if info.st_size > MAX_JSON_OBJECT_BYTES:
            raise CreativeCodeTerminalOutcomeError("terminal_json_too_large")
        with source.open("rb") as handle:
            raw = handle.read(MAX_JSON_OBJECT_BYTES + 1)
        if len(raw) > MAX_JSON_OBJECT_BYTES:
            raise CreativeCodeTerminalOutcomeError("terminal_json_too_large")
        if len(raw) != info.st_size:
            raise CreativeCodeTerminalOutcomeError("terminal_json_changed_during_read")
        payload = decode_terminal_outcome_bytes(raw)
    except CreativeCodeTerminalOutcomeError:
        raise
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise CreativeCodeTerminalOutcomeError("terminal_json_read_failed") from exc
    if not isinstance(payload, dict):
        raise CreativeCodeTerminalOutcomeError("terminal JSON must be an object.")
    return payload


def _reject_duplicate_projection_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeTerminalOutcomeError(
                "terminal evidence projection JSON has a duplicate key."
            )
        seen.add(key)
        payload[key] = value
    return payload


def _reject_non_finite_projection_constant(value: str) -> None:
    raise CreativeCodeTerminalOutcomeError(
        f"terminal evidence projection contains non-finite JSON: {value}"
    )


def _decode_terminal_evidence_projection(raw: bytes) -> list[dict[str, Any]]:
    if len(raw) > MAX_EVIDENCE_PROJECTION_BYTES:
        raise CreativeCodeTerminalOutcomeError("evidence_projection_too_large")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CreativeCodeTerminalOutcomeError("evidence_projection_bom_rejected")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_projection_keys,
            parse_constant=_reject_non_finite_projection_constant,
        )
    except CreativeCodeTerminalOutcomeError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise CreativeCodeTerminalOutcomeError("evidence_projection_decode_failed") from exc
    if not isinstance(payload, list) or len(payload) != 3:
        raise CreativeCodeTerminalOutcomeError(
            "evidence projection must be a JSON array of exactly three events."
        )
    if any(not isinstance(event, dict) for event in payload):
        raise CreativeCodeTerminalOutcomeError(
            "every evidence projection event must be a JSON object."
        )
    return cast(list[dict[str, Any]], payload)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the one canonical byte representation used for immutable replay."""

    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def terminal_evidence_projection_bytes(events: list[EvidenceEvalEvent]) -> bytes:
    """Return canonical bytes for the one fixed three-event projection bundle."""

    if len(events) != 3:
        raise CreativeCodeTerminalOutcomeError(
            "evidence projection must contain exactly three events."
        )
    return (
        json.dumps(
            [event.to_dict() for event in events],
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _require_exact_keys(
    payload: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise CreativeCodeTerminalOutcomeError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodeTerminalOutcomeError(f"{label} has unsupported fields.")


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if type(value) is not type(expected) or value != expected:
        raise CreativeCodeTerminalOutcomeError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_string(
    payload: Mapping[str, Any], key: str, pattern: re.Pattern[str], *, label: str
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise CreativeCodeTerminalOutcomeError(f"{label}.{key} has invalid format.")
    return value


def _require_repository(payload: Mapping[str, Any], *, label: str) -> str:
    repository = payload.get("repository")
    if repository != CANONICAL_REPOSITORY:
        raise CreativeCodeTerminalOutcomeError(
            f"{label}.repository must equal {CANONICAL_REPOSITORY!r}."
        )
    return CANONICAL_REPOSITORY


def _require_int(
    payload: Mapping[str, Any],
    key: str,
    *,
    min_value: int,
    max_value: int,
    label: str,
) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeCodeTerminalOutcomeError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodeTerminalOutcomeError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _optional_fingerprint(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodeTerminalOutcomeError(f"{label} must be null or a sha256 digest.")
    return value


def _optional_sha(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodeTerminalOutcomeError(f"{label} must be null or lowercase 40-hex.")
    return value


def _optional_reason(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in CLOSED_REASON_CODES:
        raise CreativeCodeTerminalOutcomeError(f"{label} is unsupported.")
    return value


def _nullable_counter(raw: Mapping[str, Any], key: str, *, label: str) -> int | None:
    if raw.get(key) is None:
        return None
    return _require_int(raw, key, min_value=0, max_value=1_000_000, label=label)


def _normalize_review(
    raw_review: Any,
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(raw_review, dict):
        raise CreativeCodeTerminalOutcomeError("review must be a JSON object.")
    label = "review"
    _require_exact_keys(raw_review, REVIEW_KEYS, label=label)
    state = raw_review.get("collection_state")
    if state not in REVIEW_COLLECTION_STATES:
        raise CreativeCodeTerminalOutcomeError("review.collection_state is unsupported.")

    inventory = _optional_fingerprint(
        raw_review.get("inventory_fingerprint"),
        label="review.inventory_fingerprint",
    )
    seal = _optional_fingerprint(
        raw_review.get("review_seal_fingerprint"),
        label="review.review_seal_fingerprint",
    )
    counter_keys = (
        "sources_configured",
        "sources_observed",
        "findings_total",
        "fixed",
        "not_a_bug",
        "deferred",
        "unresolved_actionable",
    )
    counters = {key: _nullable_counter(raw_review, key, label=label) for key in counter_keys}
    normalized: dict[str, Any] = {
        "collection_state": state,
        "inventory_fingerprint": inventory,
        "review_seal_fingerprint": seal,
        **counters,
    }

    if state == "unavailable":
        if (
            inventory is not None
            or seal is not None
            or any(counters[key] is not None for key in counter_keys)
        ):
            raise CreativeCodeTerminalOutcomeError(
                "unavailable review evidence must contain only null evidence fields."
            )
        return normalized, "evidence_unavailable", "evidence_unavailable"

    if inventory is None:
        raise CreativeCodeTerminalOutcomeError(
            "complete review evidence requires inventory_fingerprint."
        )
    if any(counters[key] is None for key in counter_keys):
        raise CreativeCodeTerminalOutcomeError("complete review evidence requires every counter.")
    configured = cast(int, counters["sources_configured"])
    observed = cast(int, counters["sources_observed"])
    if configured < 1 or observed != configured:
        raise CreativeCodeTerminalOutcomeError(
            "complete review evidence requires a non-empty fully observed source inventory."
        )
    total = cast(int, counters["findings_total"])
    dispositions = sum(
        cast(int, counters[key])
        for key in ("fixed", "not_a_bug", "deferred", "unresolved_actionable")
    )
    if total != dispositions:
        raise CreativeCodeTerminalOutcomeError(
            "review.findings_total must equal all disposition counters."
        )
    if cast(int, counters["unresolved_actionable"]) > 0:
        return normalized, "actionables_observed", "blockers_observed"
    if seal is not None:
        return normalized, "no_actionables_observed", "no_blockers_observed"
    return normalized, "evidence_unavailable", "evidence_unavailable"


def _normalize_post_merge(
    raw_post_merge: Any,
    *,
    terminal_state: str,
) -> tuple[dict[str, Any], str]:
    if not isinstance(raw_post_merge, dict):
        raise CreativeCodeTerminalOutcomeError("post_merge must be a JSON object.")
    label = "post_merge"
    _require_exact_keys(raw_post_merge, POST_MERGE_KEYS, label=label)
    inventory = _optional_fingerprint(
        raw_post_merge.get("validation_inventory_fingerprint"),
        label="post_merge.validation_inventory_fingerprint",
    )
    configured = _require_int(
        raw_post_merge,
        "commands_configured",
        min_value=0,
        max_value=1_000_000,
        label=label,
    )
    executed = _require_int(
        raw_post_merge,
        "commands_executed",
        min_value=0,
        max_value=1_000_000,
        label=label,
    )
    passed = _require_int(
        raw_post_merge,
        "commands_passed",
        min_value=0,
        max_value=1_000_000,
        label=label,
    )
    current_main_ci = raw_post_merge.get("current_main_ci")
    if current_main_ci not in CURRENT_MAIN_CI_STATES:
        raise CreativeCodeTerminalOutcomeError("post_merge.current_main_ci is unsupported.")
    current_main_sha = _optional_sha(
        raw_post_merge.get("current_main_sha"),
        label="post_merge.current_main_sha",
    )
    if passed > executed or executed > configured:
        raise CreativeCodeTerminalOutcomeError(
            "post_merge command counters must satisfy passed <= executed <= configured."
        )
    if current_main_ci == "not_observed" and current_main_sha is not None:
        raise CreativeCodeTerminalOutcomeError("unobserved current-main CI must not carry a SHA.")
    if current_main_ci != "not_observed" and current_main_sha is None:
        raise CreativeCodeTerminalOutcomeError(
            "observed current-main CI requires current_main_sha."
        )
    normalized = {
        "validation_inventory_fingerprint": inventory,
        "commands_configured": configured,
        "commands_executed": executed,
        "commands_passed": passed,
        "current_main_ci": current_main_ci,
        "current_main_sha": current_main_sha,
    }

    if terminal_state == "closed_unmerged":
        if normalized != {
            "validation_inventory_fingerprint": None,
            "commands_configured": 0,
            "commands_executed": 0,
            "commands_passed": 0,
            "current_main_ci": "not_observed",
            "current_main_sha": None,
        }:
            raise CreativeCodeTerminalOutcomeError(
                "closed_unmerged post-merge evidence must be not_applicable."
            )
        return normalized, "not_applicable"

    observed = configured > 0 or current_main_ci != "not_observed"
    if not observed:
        return normalized, "evidence_unavailable"
    if inventory is None:
        raise CreativeCodeTerminalOutcomeError(
            "observed post-merge evidence requires validation_inventory_fingerprint."
        )
    if current_main_ci == "failure" or executed < configured or passed < executed:
        return normalized, "incomplete_observed"
    return normalized, "complete_observed"


def _normalize_process(raw_process: Any) -> dict[str, int]:
    if not isinstance(raw_process, dict):
        raise CreativeCodeTerminalOutcomeError("process must be a JSON object.")
    _require_exact_keys(raw_process, PROCESS_KEYS, label="process")
    return {
        key: _require_int(
            raw_process,
            key,
            min_value=0,
            max_value=1_000_000,
            label="process",
        )
        for key in sorted(PROCESS_KEYS)
    }


def _normalize_cost(raw_cost: Any) -> dict[str, int | bool | None]:
    try:
        normalized: dict[str, int | bool | None] = normalize_cost_metadata(raw_cost)
        return normalized
    except CreativeCodeTelemetryContractError as exc:
        raise CreativeCodeTerminalOutcomeError(str(exc)) from exc


def normalize_terminal_observation(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the closed caller observation without granting it artifact status."""

    label = "CreativeCodeTerminalObservation"
    _require_exact_keys(payload, OBSERVATION_KEYS, label=label)
    terminal_state = payload.get("terminal_state")
    if terminal_state not in TERMINAL_STATES:
        raise CreativeCodeTerminalOutcomeError("terminal_evidence_unavailable")
    merge_sha = _optional_sha(payload.get("merge_sha"), label=f"{label}.merge_sha")
    reason_code = _optional_reason(payload.get("reason_code"), label=f"{label}.reason_code")
    if terminal_state == "merged":
        if merge_sha is None or reason_code is not None:
            raise CreativeCodeTerminalOutcomeError(
                "merged terminal evidence requires merge_sha and null reason_code."
            )
    if terminal_state == "closed_unmerged":
        if merge_sha is not None or reason_code is None:
            raise CreativeCodeTerminalOutcomeError(
                "closed_unmerged terminal evidence requires null merge_sha and one reason_code."
            )
    review, review_observation, governance_observation = _normalize_review(payload.get("review"))
    post_merge, post_merge_observation = _normalize_post_merge(
        payload.get("post_merge"),
        terminal_state=cast(str, terminal_state),
    )
    normalized = {
        "promotion_id": _require_string(payload, "promotion_id", PROMOTION_ID_RE, label=label),
        "repository": _require_repository(payload, label=label),
        "pull_request_number": _require_int(
            payload,
            "pull_request_number",
            min_value=1,
            max_value=999_999,
            label=label,
        ),
        "promoted_head_sha": _require_string(payload, "promoted_head_sha", SHA_RE, label=label),
        "closure_epoch": _require_int(
            payload,
            "closure_epoch",
            min_value=1,
            max_value=MAX_CLOSURE_EPOCH,
            label=label,
        ),
        "terminal_state": terminal_state,
        "merge_sha": merge_sha,
        "reason_code": reason_code,
        "review": review,
        "review_observation": review_observation,
        "governance_observation": governance_observation,
        "post_merge": post_merge,
        "post_merge_observation": post_merge_observation,
        "process": _normalize_process(payload.get("process")),
        "cost_metadata": _normalize_cost(payload.get("cost_metadata")),
        "sanitized": _require_const(payload, "sanitized", True, label=label),
    }
    try:
        reject_unsafe_telemetry_value(normalized, label=label)
    except CreativeCodeTelemetryContractError as exc:
        raise CreativeCodeTerminalOutcomeError(str(exc)) from exc
    return normalized


def _normalize_lineage(raw_lineage: Any) -> dict[str, Any]:
    if not isinstance(raw_lineage, dict):
        raise CreativeCodeTerminalOutcomeError("lineage must be a JSON object.")
    label = "lineage"
    _require_exact_keys(raw_lineage, LINEAGE_KEYS, label=label)
    normalized = {
        "promotion_id": _require_string(raw_lineage, "promotion_id", PROMOTION_ID_RE, label=label),
        "source_request_id": _require_string(raw_lineage, "source_request_id", ID_RE, label=label),
        "source_result_id": _require_string(raw_lineage, "source_result_id", ID_RE, label=label),
        "source_bundle_id": _require_string(raw_lineage, "source_bundle_id", ID_RE, label=label),
        "selected_variant_id": _require_string(
            raw_lineage, "selected_variant_id", ID_RE, label=label
        ),
        "receipt_id": _require_string(raw_lineage, "receipt_id", ID_RE, label=label),
        "plan_fingerprint": _require_string(
            raw_lineage, "plan_fingerprint", SHA256_RE, label=label
        ),
        "validation_fingerprint": _require_string(
            raw_lineage, "validation_fingerprint", SHA256_RE, label=label
        ),
        "approval_id": _require_string(raw_lineage, "approval_id", ID_RE, label=label),
        "patch_fingerprint": _require_string(
            raw_lineage, "patch_fingerprint", SHA256_RE, label=label
        ),
        "repository": _require_repository(raw_lineage, label=label),
        "pull_request_number": _require_int(
            raw_lineage,
            "pull_request_number",
            min_value=1,
            max_value=999_999,
            label=label,
        ),
        "base_sha": _require_string(raw_lineage, "base_sha", SHA_RE, label=label),
        "promoted_head_sha": _require_string(raw_lineage, "promoted_head_sha", SHA_RE, label=label),
    }
    try:
        reject_unsafe_telemetry_value(normalized, label=label)
    except CreativeCodeTelemetryContractError as exc:
        raise CreativeCodeTerminalOutcomeError(str(exc)) from exc
    return normalized


def terminal_outcome_id(
    *,
    repository: str,
    pull_request_number: int,
    promotion_id: str,
    promoted_head_sha: str,
) -> str:
    """Return the stable identity; terminal state and closure epoch are excluded."""

    if repository != CANONICAL_REPOSITORY:
        raise CreativeCodeTerminalOutcomeError(f"repository must equal {CANONICAL_REPOSITORY!r}.")
    identity: dict[str, Any] = {
        "repository": repository,
        "pull_request_number": pull_request_number,
        "promotion_id": promotion_id,
        "promoted_head_sha": promoted_head_sha,
    }
    outcome_id: str = build_asset_id(
        asset_type=ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint_payload(identity),
        upstream_ids=(
            repository,
            str(pull_request_number),
            promotion_id,
            promoted_head_sha,
        ),
    )
    return outcome_id


def _idempotency_payload(outcome: Mapping[str, Any]) -> dict[str, Any]:
    return {key: outcome[key] for key in sorted(OUTCOME_KEYS - {"idempotency_key"})}


def terminal_outcome_fingerprint(outcome: Mapping[str, Any]) -> str:
    """Fingerprint one fully validated terminal outcome."""

    normalized = validate_creative_code_terminal_outcome(outcome)
    fingerprint: str = fingerprint_payload(normalized)
    return fingerprint


def build_creative_code_terminal_outcome(
    *,
    promotion_plan: Mapping[str, Any],
    promotion_receipt: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one outcome from a validated, cross-bound PR-3 lineage."""

    try:
        plan = validate_creative_code_pr_promotion_plan(dict(promotion_plan))
        receipt = validate_creative_code_pr_promotion_receipt(dict(promotion_receipt))
    except CreativeCodePRPromotionContractError as exc:
        raise CreativeCodeTerminalOutcomeError("invalid_promotion_lineage") from exc
    if receipt["pull_request_state"] != "open":
        raise CreativeCodeTerminalOutcomeError(
            "promotion receipt must be terminal-observable open."
        )
    plan_fingerprint = promotion_plan_fingerprint(plan)
    comparisons = (
        (receipt["promotion_id"], plan["promotion_id"]),
        (receipt["plan_fingerprint"], plan_fingerprint),
        (receipt["source_result_id"], plan["source_result_id"]),
        (receipt["patch_fingerprint"], plan["patch_fingerprint"]),
        (receipt["repository"], plan["target_repository"]),
        (receipt["base_branch"], plan["target_base_branch"]),
        (receipt["head_branch"], plan["target_head_branch"]),
    )
    if any(left != right for left, right in comparisons):
        raise CreativeCodeTerminalOutcomeError("promotion_lineage_mismatch")
    observed = normalize_terminal_observation(observation)
    observation_bindings = (
        (observed["promotion_id"], receipt["promotion_id"]),
        (observed["repository"], receipt["repository"]),
        (observed["pull_request_number"], receipt["pull_request_number"]),
        (observed["promoted_head_sha"], receipt["commit_sha"]),
    )
    if any(left != right for left, right in observation_bindings):
        raise CreativeCodeTerminalOutcomeError("terminal_observation_lineage_mismatch")
    lineage = {
        "promotion_id": plan["promotion_id"],
        "source_request_id": plan["source_request_id"],
        "source_result_id": plan["source_result_id"],
        "source_bundle_id": plan["source_bundle_id"],
        "selected_variant_id": plan["selected_variant_id"],
        "receipt_id": receipt["receipt_id"],
        "plan_fingerprint": plan_fingerprint,
        "validation_fingerprint": receipt["validation_fingerprint"],
        "approval_id": receipt["approval_id"],
        "patch_fingerprint": plan["patch_fingerprint"],
        "repository": receipt["repository"],
        "pull_request_number": receipt["pull_request_number"],
        "base_sha": plan["base_commit_sha"],
        "promoted_head_sha": receipt["commit_sha"],
    }
    outcome: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "outcome_id": terminal_outcome_id(
            repository=receipt["repository"],
            pull_request_number=receipt["pull_request_number"],
            promotion_id=plan["promotion_id"],
            promoted_head_sha=receipt["commit_sha"],
        ),
        "idempotency_key": "pending",
        "lineage": lineage,
        "closure_epoch": observed["closure_epoch"],
        "terminal_state": observed["terminal_state"],
        "merge_sha": observed["merge_sha"],
        "reason_code": observed["reason_code"],
        "review_evidence": observed["review"],
        "review_observation": observed["review_observation"],
        "governance_observation": observed["governance_observation"],
        "post_merge_evidence": observed["post_merge"],
        "post_merge_observation": observed["post_merge_observation"],
        "process": observed["process"],
        "cost_metadata": observed["cost_metadata"],
        "sanitized": True,
    }
    outcome["idempotency_key"] = fingerprint_payload(_idempotency_payload(outcome))
    return validate_creative_code_terminal_outcome(outcome)


def validate_creative_code_terminal_outcome(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a terminal outcome and re-derive every observation token."""

    label = "CreativeCodeTerminalOutcomeV1"
    _require_exact_keys(payload, OUTCOME_KEYS, label=label)
    terminal_state = payload.get("terminal_state")
    if terminal_state not in TERMINAL_STATES:
        raise CreativeCodeTerminalOutcomeError(f"{label}.terminal_state is unsupported.")
    merge_sha = _optional_sha(payload.get("merge_sha"), label=f"{label}.merge_sha")
    reason_code = _optional_reason(payload.get("reason_code"), label=f"{label}.reason_code")
    if terminal_state == "merged":
        if merge_sha is None or reason_code is not None:
            raise CreativeCodeTerminalOutcomeError(
                "merged outcomes require merge_sha and null reason_code."
            )
    if terminal_state == "closed_unmerged":
        if merge_sha is not None or reason_code is None:
            raise CreativeCodeTerminalOutcomeError(
                "closed_unmerged outcomes require null merge_sha and one reason_code."
            )
    review, review_observation, governance_observation = _normalize_review(
        payload.get("review_evidence")
    )
    post_merge, post_merge_observation = _normalize_post_merge(
        payload.get("post_merge_evidence"),
        terminal_state=cast(str, terminal_state),
    )
    lineage = _normalize_lineage(payload.get("lineage"))
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", ARTIFACT_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "outcome_id": _require_string(payload, "outcome_id", ID_RE, label=label),
        "idempotency_key": _require_string(payload, "idempotency_key", SHA256_RE, label=label),
        "lineage": lineage,
        "closure_epoch": _require_int(
            payload,
            "closure_epoch",
            min_value=1,
            max_value=MAX_CLOSURE_EPOCH,
            label=label,
        ),
        "terminal_state": terminal_state,
        "merge_sha": merge_sha,
        "reason_code": reason_code,
        "review_evidence": review,
        "review_observation": payload.get("review_observation"),
        "governance_observation": payload.get("governance_observation"),
        "post_merge_evidence": post_merge,
        "post_merge_observation": payload.get("post_merge_observation"),
        "process": _normalize_process(payload.get("process")),
        "cost_metadata": _normalize_cost(payload.get("cost_metadata")),
        "sanitized": _require_const(payload, "sanitized", True, label=label),
    }
    if normalized["review_observation"] not in REVIEW_OBSERVATIONS:
        raise CreativeCodeTerminalOutcomeError("review_observation is unsupported.")
    if normalized["governance_observation"] not in GOVERNANCE_OBSERVATIONS:
        raise CreativeCodeTerminalOutcomeError("governance_observation is unsupported.")
    if normalized["post_merge_observation"] not in POST_MERGE_OBSERVATIONS:
        raise CreativeCodeTerminalOutcomeError("post_merge_observation is unsupported.")
    if normalized["review_observation"] != review_observation:
        raise CreativeCodeTerminalOutcomeError("review_observation does not match review evidence.")
    if normalized["governance_observation"] != governance_observation:
        raise CreativeCodeTerminalOutcomeError(
            "governance_observation does not match review evidence."
        )
    if normalized["post_merge_observation"] != post_merge_observation:
        raise CreativeCodeTerminalOutcomeError(
            "post_merge_observation does not match post-merge evidence."
        )
    expected_outcome_id = terminal_outcome_id(
        repository=lineage["repository"],
        pull_request_number=lineage["pull_request_number"],
        promotion_id=lineage["promotion_id"],
        promoted_head_sha=lineage["promoted_head_sha"],
    )
    if normalized["outcome_id"] != expected_outcome_id:
        raise CreativeCodeTerminalOutcomeError("outcome_id does not match terminal lineage.")
    expected_key = fingerprint_payload(_idempotency_payload(normalized))
    if normalized["idempotency_key"] != expected_key:
        raise CreativeCodeTerminalOutcomeError(
            "idempotency_key does not match terminal outcome content."
        )
    try:
        reject_unsafe_telemetry_value(normalized, label=label)
    except CreativeCodeTelemetryContractError as exc:
        raise CreativeCodeTerminalOutcomeError(str(exc)) from exc
    return normalized


def _normalize_projection_produced_at(produced_at: str) -> str:
    if not isinstance(produced_at, str) or len(produced_at) > MAX_EVIDENCE_PROJECTION_BYTES:
        raise CreativeCodeTerminalOutcomeError(
            "produced_at must be an explicit RFC3339 timestamp with a UTC offset."
        )
    matched = RFC3339_RE.fullmatch(produced_at)
    if matched is None:
        raise CreativeCodeTerminalOutcomeError(
            "produced_at must be an explicit RFC3339 timestamp with a UTC offset."
        )
    offset = matched.group("offset")
    if offset == "-00:00":
        raise CreativeCodeTerminalOutcomeError(
            "produced_at must include an explicit known UTC offset."
        )
    if matched.group("base").endswith(":60"):
        raise CreativeCodeTerminalOutcomeError("produced_at is invalid.")
    try:
        base = matched.group("base")
        canonical_base = base[:10] + "T" + base[11:]
        parsed = datetime.fromisoformat(
            canonical_base + ("+00:00" if offset in {"Z", "z"} else offset)
        )
    except (OverflowError, ValueError) as exc:
        raise CreativeCodeTerminalOutcomeError("produced_at is invalid.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CreativeCodeTerminalOutcomeError("produced_at must include a UTC offset.")
    try:
        normalized = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (OverflowError, ValueError) as exc:
        raise CreativeCodeTerminalOutcomeError("produced_at is invalid.") from exc
    canonical_fraction = (matched.group("fraction") or "").rstrip("0").removesuffix(".")
    return normalized.removesuffix("+00:00") + canonical_fraction + "Z"


def _terminal_projection_status(outcome: Mapping[str, Any]) -> str:
    if outcome["terminal_state"] == "closed_unmerged":
        return "deferred"
    if (
        outcome["review_observation"] == "no_actionables_observed"
        and outcome["governance_observation"] == "no_blockers_observed"
        and outcome["post_merge_observation"] == "complete_observed"
        and outcome["post_merge_evidence"]["current_main_ci"] == "success"
    ):
        return "valid"
    return "degraded"


def build_terminal_evidence_events(
    outcome: Mapping[str, Any],
    *,
    produced_at: str,
) -> list[EvidenceEvalEvent]:
    """Project one validated terminal outcome into a fixed observational bundle."""

    normalized = validate_creative_code_terminal_outcome(dict(outcome))
    normalized_produced_at = _normalize_projection_produced_at(produced_at)
    outcome_fingerprint = fingerprint_payload(normalized)
    bundle_fingerprint = fingerprint_payload(
        {
            "projection_policy_version": EVIDENCE_PROJECTION_POLICY_VERSION,
            "terminal_outcome_fingerprint": outcome_fingerprint,
        }
    )
    review = cast(dict[str, Any], normalized["review_evidence"])
    post_merge = cast(dict[str, Any], normalized["post_merge_evidence"])
    process = cast(dict[str, Any], normalized["process"])
    common_fingerprints = {
        "projection_bundle_fingerprint": bundle_fingerprint,
        "terminal_outcome_fingerprint": outcome_fingerprint,
    }
    payloads: tuple[tuple[str, dict[str, Any]], ...] = (
        (
            "item_metadata",
            {
                **common_fingerprints,
                "terminal_state": normalized["terminal_state"],
                "review_observation": normalized["review_observation"],
                "governance_observation": normalized["governance_observation"],
                "post_merge_observation": normalized["post_merge_observation"],
                "reason_code_present": normalized["reason_code"] is not None,
                "terminal_policy_version": normalized["policy_version"],
            },
        ),
        (
            "gate_metric",
            {
                **common_fingerprints,
                "sources_configured": review["sources_configured"],
                "sources_observed": review["sources_observed"],
                "findings_total": review["findings_total"],
                "fixed": review["fixed"],
                "not_a_bug": review["not_a_bug"],
                "deferred": review["deferred"],
                "unresolved_actionable": review["unresolved_actionable"],
                "review_cycles": process["review_cycles"],
                "repair_cycles": process["repair_cycles"],
                "validation_attempts": process["validation_attempts"],
                "post_merge_commands_configured": post_merge["commands_configured"],
                "post_merge_commands_executed": post_merge["commands_executed"],
                "post_merge_commands_passed": post_merge["commands_passed"],
            },
        ),
        (
            "gate_decision",
            {
                **common_fingerprints,
                "decision": normalized["terminal_state"],
                "review_observation": normalized["review_observation"],
                "governance_observation": normalized["governance_observation"],
                "post_merge_observation": normalized["post_merge_observation"],
                "current_main_ci": post_merge["current_main_ci"],
                "current_main_sha": post_merge["current_main_sha"],
                "validation_inventory_fingerprint": post_merge["validation_inventory_fingerprint"],
                "reason_code": normalized["reason_code"],
            },
        ),
    )
    upstream_ids = normalize_upstream_ids(
        (
            cast(str, normalized["outcome_id"]),
            cast(str, normalized["lineage"]["promotion_id"]),
            cast(str, normalized["lineage"]["receipt_id"]),
        )
    )
    validation_status = _terminal_projection_status(normalized)
    events: list[EvidenceEvalEvent] = []
    for event_type, metadata in payloads:
        event_fingerprint = fingerprint_payload(
            {
                "projection_bundle_fingerprint": bundle_fingerprint,
                "event_type": event_type,
                "metadata": metadata,
            }
        )
        idempotency_key = build_idempotency_key(
            asset_type=event_type,
            rail="control_plane",
            version=EVIDENCE_PROJECTION_PRODUCER_VERSION,
            policy_version=EVIDENCE_PROJECTION_POLICY_VERSION,
            fingerprint=event_fingerprint,
            upstream_ids=upstream_ids,
        )
        try:
            event = create_eval_event(
                event_type=cast(Any, event_type),
                rail="control_plane",
                source_artifact=EVIDENCE_PROJECTION_SOURCE_ARTIFACT,
                asset_refs=(),
                upstream_ids=upstream_ids,
                fingerprint=event_fingerprint,
                idempotency_key=idempotency_key,
                policy_version=EVIDENCE_PROJECTION_POLICY_VERSION,
                producer_name=EVIDENCE_PROJECTION_PRODUCER_NAME,
                producer_version=EVIDENCE_PROJECTION_PRODUCER_VERSION,
                produced_at=normalized_produced_at,
                validation_status=cast(Any, validation_status),
                metadata=dict(metadata),
            )
        except (TypeError, ValueError) as exc:
            raise CreativeCodeTerminalOutcomeError("terminal_evidence_projection_invalid") from exc
        events.append(event)
    return events


def _require_type_strict_equal(actual: Any, expected: Any, *, path: str) -> None:
    if type(actual) is not type(expected):
        raise CreativeCodeTerminalOutcomeError(f"evidence projection JSON type mismatch at {path}.")
    if isinstance(expected, dict):
        if list(actual) != list(expected):
            raise CreativeCodeTerminalOutcomeError(
                f"evidence projection object shape or key order mismatch at {path}."
            )
        for key in expected:
            _require_type_strict_equal(actual[key], expected[key], path=f"{path}.{key}")
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise CreativeCodeTerminalOutcomeError(
                f"evidence projection array length mismatch at {path}."
            )
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            _require_type_strict_equal(
                actual_item,
                expected_item,
                path=f"{path}[{index}]",
            )
        return
    if actual != expected:
        raise CreativeCodeTerminalOutcomeError(f"evidence projection value mismatch at {path}.")


def validate_terminal_evidence_projection(
    outcome: Mapping[str, Any],
    projection_bytes: bytes,
) -> list[EvidenceEvalEvent]:
    """Rebuild and exactly validate one serialized terminal projection bundle."""

    normalized = validate_creative_code_terminal_outcome(dict(outcome))
    decoded = _decode_terminal_evidence_projection(projection_bytes)
    produced_values: list[str] = []
    for event in decoded:
        produced_at = event.get("produced_at")
        if type(produced_at) is not str:
            raise CreativeCodeTerminalOutcomeError(
                "every evidence projection event must carry a string produced_at."
            )
        produced_values.append(produced_at)
    if len(set(produced_values)) != 1:
        raise CreativeCodeTerminalOutcomeError(
            "evidence projection events must share one produced_at."
        )
    expected_events = build_terminal_evidence_events(
        normalized,
        produced_at=produced_values[0],
    )
    expected_payload = [event.to_dict() for event in expected_events]
    _require_type_strict_equal(decoded, expected_payload, path="$.")
    expected_bytes = terminal_evidence_projection_bytes(expected_events)
    if projection_bytes != expected_bytes:
        raise CreativeCodeTerminalOutcomeError(
            "evidence projection bytes are not canonical or do not match the outcome."
        )
    return expected_events
