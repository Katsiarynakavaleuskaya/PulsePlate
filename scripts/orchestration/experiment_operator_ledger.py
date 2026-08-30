#!/usr/bin/env python3
"""Local-only Experiment Runner operator ledger and observability report."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, cast

OPERATOR_LEDGER_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(OPERATOR_LEDGER_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(OPERATOR_LEDGER_REPO_ROOT))

from scripts.orchestration.context_pack import REPO_ROOT
from scripts.orchestration.experiment_contract import validate_experiment_result
from scripts.orchestration.experiment_slack_bridge_config import (
    _normalized_absolute_path,
    _reject_symlinked_output_components,
)
from scripts.orchestration.experiment_slack_bridge_constants import SECRET_SHAPED_RE, SHA256_HEX_RE
from scripts.orchestration.experiment_slack_bridge_models import SlackSocketAuditError
from scripts.orchestration.experiment_slack_bridge_readiness import (
    manual_only_activation_readiness_report,
    render_activation_readiness_summary,
)
from scripts.orchestration.experiment_private_pilot_activation import (
    PrivatePilotActivationEvidenceError,
    absent_private_pilot_activation_summary,
    invalid_private_pilot_activation_summary,
    render_private_pilot_activation_summary,
    validate_private_pilot_activation_evidence,
)
from scripts.orchestration.experiment_slack_redaction import (
    LOCAL_PATH_RE,
    SLACK_IDENTIFIER_RE,
    safe_artifact_ref,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "operator-plane-2026-06-02-v1"
REDACTION_VERSION = "experiment-slack-redaction-v1"
DEFAULT_RETENTION_DAYS = 30
PROVIDER_TYPE = "experiment_runner_operator_plane"
DEFAULT_LEDGER_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "operator_ledger"
DEFAULT_OBSERVABILITY_REPORT_DIR = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "operator_observability"
)
DEFAULT_ACTIVATION_EVIDENCE_DIR = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "private_pilot_activation"
)
DEFAULT_ACTIVATION_EVIDENCE_STALE_AFTER_DAYS = 7
EXPERIMENT_RESULTS_REPO_PREFIX = "artifacts/orchestration/experiments/results/"
PRIVATE_PILOT_ACTIVATION_REPO_PREFIX = (
    "artifacts/orchestration/experiments/private_pilot_activation/"
)
IDEMPOTENCY_KEY_ITERATIONS = 120_000
IDEMPOTENCY_KEY_NAMESPACE = b"pulseplate-operator-ledger-idempotency-v1"
IDEMPOTENCY_KEY_CHECK_ITERATIONS = 1_000
IDEMPOTENCY_KEY_CHECK_NAMESPACE = b"pulseplate-operator-ledger-idempotency-check-v1"
CONTENT_HASH_NAMESPACE = b"pulseplate-operator-ledger-content-v1"
CONTENT_HASH_ITERATIONS = 1_000
IDEMPOTENCY_KEY_RE = re.compile(r"^[a-f0-9]{24}$")
EMAIL_SHAPED_ARTIFACT_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_SHAPED_ARTIFACT_RE = re.compile(r"\b\+?\d[\d .()_-]{7,}\d\b")
ARTIFACT_DATE_TOKEN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MIN_ALLOWED_ARTIFACT_DATE_YEAR = 2000
MAX_ALLOWED_ARTIFACT_DATE_YEAR = 2099
LOCAL_PATH_SEGMENT_RE = re.compile(
    r"(^|/)(Users|home|var|opt|tmp|private|Volumes|etc|usr|Library|System)(/|$)"
)
WINDOWS_DRIVE_SEGMENT_RE = re.compile(r"(^|/)[A-Za-z]:/")
GITHUB_APP_TOKEN_ARTIFACT_RE = re.compile(r"ghs_[A-Za-z0-9._-]{4,}", re.IGNORECASE)
PRIVATE_PILOT_ACTIVATION_INPUT_INVALID = "Private-pilot activation evidence input is invalid."

ALLOWED_COMMAND_KINDS = frozenset(
    {
        "help",
        "kpp-status",
        "mvp-evidence",
        "status",
        "run-experiment",
        "oracle-review",
        "rejected",
    }
)
ALLOWED_STATUS = frozenset({"dry_run", "dispatched", "failed", "rejected", "observed"})
ALLOWED_FAILURE_CLASSES = frozenset(
    {
        "none",
        "command_rejected",
        "dispatch_failed",
        "malformed_evidence",
        "missing_evidence",
        "operator_override",
        "oracle_violation",
        "rate_limited",
        "surface_breach",
    }
)
ALLOWED_DISPATCH_MODES = frozenset({"dry-run", "execute", "oracle-only", "manual-smoke"})
ALLOWED_WORKFLOW_FILES = frozenset({"experiment-runner-dispatch.yml", "none"})
ALLOWED_WORKFLOW_REFS = frozenset({"main", "none"})
ALLOWED_COAUTHOR_DECISIONS = frozenset(
    {"required", "not_required", "not_applicable", "pending_human_review"}
)
ALLOWED_REVIEW_OUTCOMES = frozenset(
    {"pending", "approved", "rejected", "deferred", "not_applicable"}
)
RESULT_METADATA_ABSENT = {
    "artifact_status": "absent",
    "artifact_ref": "none",
}
RESULT_METADATA_INVALID = {
    "artifact_status": "invalid",
    "artifact_ref": "none",
}
RESULT_METADATA_MISSING = {
    "artifact_status": "missing",
    "artifact_ref": "none",
}
SAFE_RESULT_METADATA_FIELDS = (
    "schema_version",
    "experiment_id_hash",
    "runner_mode",
    "status",
    "failure_class",
    "mutated_paths_count",
    "shared_tree_untouched",
    "promotion_ready",
    "contribution_kind",
    "coauthor_required",
)
CLI_OUTPUT_PATCH_OR_LOG_RE = re.compile(
    r"(diff\s+--git|^@@\s|^\+\+\+\s|^---\s|raw\s+patch|patch\s+text|"
    r"oracle\s+stdout|oracle\s+stderr|raw\s+stdout|raw\s+stderr|"
    r"stdout\s*:|stderr\s*:)",
    re.IGNORECASE | re.MULTILINE,
)
CLI_OUTPUT_LOCAL_PATH_RE = re.compile(
    r"("
    r"/(?:Users|home|var|opt|tmp|private|Volumes|etc|usr|Library|System)/"
    r"[^\s\"'`<>]*"
    r"|[A-Za-z]:\\[^\s\"'`<>]+"
    r"|\\\\[^\s\"'`<>]+"
    r")"
)

HASH_FIELDS = frozenset(
    {
        "branch_hash",
        "channel_hash",
        "event_hash",
        "hypothesis_hash",
        "oracle_result_hash",
        "slack_audit_hash",
        "team_hash",
        "user_hash",
    }
)
REQUIRED_HASH_FIELDS = frozenset({"channel_hash", "event_hash", "user_hash"})
ARTIFACT_REF_FIELDS = frozenset({"oracle_result_ref", "slack_audit_ref"})
AUTHORITY_FIELDS = frozenset(
    {
        "claimed_merge_readiness",
        "created_pr",
        "product_runtime_changed",
        "resolved_review_threads",
    }
)
REQUIRED_EVENT_FIELDS = frozenset(
    {
        "branch_hash",
        "channel_hash",
        "claimed_merge_readiness",
        "coauthor_decision",
        "coauthor_required",
        "command_kind",
        "created_pr",
        "dispatch_mode",
        "event_hash",
        "failure_class",
        "generated_at",
        "human_review_outcome",
        "hypothesis_hash",
        "oracle_result_hash",
        "oracle_result_ref",
        "policy_version",
        "product_runtime_changed",
        "provider_type",
        "redaction_version",
        "resolved_review_threads",
        "retention_days",
        "schema_version",
        "slack_audit_hash",
        "slack_audit_ref",
        "status",
        "task_packet_id",
        "team_hash",
        "user_hash",
        "workflow_file",
        "workflow_ref",
    }
)
DERIVED_EVENT_FIELDS = frozenset({"content_hash", "idempotency_key", "idempotency_key_check"})
LEGACY_DERIVED_EVENT_FIELDS = frozenset({"idempotency_key"})
EVENT_FIELDS = REQUIRED_EVENT_FIELDS | DERIVED_EVENT_FIELDS
LEGACY_EVENT_FIELDS = REQUIRED_EVENT_FIELDS | LEGACY_DERIVED_EVENT_FIELDS
IDEMPOTENCY_MATERIAL_FIELDS = (
    "branch_hash",
    "command_kind",
    "event_hash",
    "human_review_outcome",
    "hypothesis_hash",
    "oracle_result_hash",
    "slack_audit_hash",
    "status",
    "task_packet_id",
)
LEGACY_SHA256_IDEMPOTENCY_MATERIAL_FIELDS = (
    "branch_hash",
    "command_kind",
    "event_hash",
    "human_review_outcome",
    "hypothesis_hash",
    "oracle_result_hash",
    "slack_audit_hash",
    "status",
    "task_packet_id",
)


class OperatorLedgerError(RuntimeError):
    """Local operator ledger validation or artifact errors."""


@dataclass(frozen=True)
class OperatorLedgerRecord:
    """Strict normalized local operator ledger record."""

    payload: dict[str, Any]

    @property
    def idempotency_key(self) -> str:
        return str(self.payload["idempotency_key"])

    @property
    def generated_at(self) -> str:
        return str(self.payload["generated_at"])


def default_ledger_dir(repo_root: Path | None = None) -> Path:
    """Return the default local operator ledger directory."""

    effective_root = repo_root or REPO_ROOT
    return effective_root / "artifacts" / "orchestration" / "experiments" / "operator_ledger"


def default_observability_report_dir(repo_root: Path | None = None) -> Path:
    """Return the default local operator observability report directory."""

    effective_root = repo_root or REPO_ROOT
    return effective_root / "artifacts" / "orchestration" / "experiments" / "operator_observability"


def default_activation_evidence_dir(repo_root: Path | None = None) -> Path:
    """Return the default local private-pilot activation evidence directory."""

    effective_root = repo_root or REPO_ROOT
    return (
        effective_root / "artifacts" / "orchestration" / "experiments" / "private_pilot_activation"
    )


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_exact_keys(payload: dict[str, Any], *, allowed: frozenset[str]) -> None:
    missing = REQUIRED_EVENT_FIELDS - set(payload)
    extra = set(payload) - allowed
    if missing or extra:
        raise OperatorLedgerError("Experiment operator ledger event schema is invalid.")


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperatorLedgerError("Experiment operator ledger event timestamp is invalid.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OperatorLedgerError("Experiment operator ledger event timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise OperatorLedgerError("Experiment operator ledger event timestamp is invalid.")
    normalized = parsed.astimezone(timezone.utc)
    if normalized > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise OperatorLedgerError("Experiment operator ledger event timestamp is invalid.")
    return normalized.isoformat()


def _is_allowed_artifact_date_token(value: str) -> bool:
    if ARTIFACT_DATE_TOKEN_RE.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return MIN_ALLOWED_ARTIFACT_DATE_YEAR <= parsed.year <= MAX_ALLOWED_ARTIFACT_DATE_YEAR


def _contains_pii_shaped_artifact_ref(value: str) -> bool:
    if EMAIL_SHAPED_ARTIFACT_RE.search(value):
        return True
    for candidate in PHONE_SHAPED_ARTIFACT_RE.finditer(value):
        if not _is_allowed_artifact_date_token(candidate.group(0)):
            return True
    return False


def _validate_hash(value: Any) -> str:
    if value is None:
        return "none"
    if not isinstance(value, str):
        raise OperatorLedgerError("Experiment operator ledger hash field is invalid.")
    normalized = value.strip().lower()
    if normalized == "none":
        return normalized
    if SHA256_HEX_RE.fullmatch(normalized) is None:
        raise OperatorLedgerError("Experiment operator ledger hash field is invalid.")
    return normalized


def _validate_enum(value: Any, *, allowed: frozenset[str], label: str) -> str:
    if not isinstance(value, str):
        raise OperatorLedgerError(f"Experiment operator ledger {label} is invalid.")
    normalized = value.strip()
    if normalized not in allowed:
        raise OperatorLedgerError(f"Experiment operator ledger {label} is invalid.")
    return normalized


def _validate_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise OperatorLedgerError(f"Experiment operator ledger {label} is invalid.")
    return value


def _validate_false(value: Any, *, label: str) -> bool:
    normalized = _validate_bool(value, label=label)
    if normalized:
        raise OperatorLedgerError("Experiment operator ledger authority boundary is invalid.")
    return normalized


def _validate_artifact_ref(value: Any) -> str:
    if value is None:
        return "none"
    if not isinstance(value, str):
        raise OperatorLedgerError("Experiment operator ledger artifact reference is invalid.")
    normalized = value.strip()
    if normalized == "none":
        return normalized
    if SLACK_IDENTIFIER_RE.search(normalized):
        raise OperatorLedgerError("Experiment operator ledger artifact reference is invalid.")
    normalized_ref = normalized.replace("\\", "/")
    if (
        "//" in normalized_ref
        or _contains_pii_shaped_artifact_ref(normalized_ref)
        or GITHUB_APP_TOKEN_ARTIFACT_RE.search(normalized_ref)
        or LOCAL_PATH_SEGMENT_RE.search(normalized_ref)
        or WINDOWS_DRIVE_SEGMENT_RE.search(normalized_ref)
    ):
        raise OperatorLedgerError("Experiment operator ledger artifact reference is invalid.")
    safe = safe_artifact_ref(normalized)
    if safe in {"[redacted-ref]", "none"}:
        raise OperatorLedgerError("Experiment operator ledger artifact reference is invalid.")
    return cast(str, safe)


def _validate_task_packet_id(value: Any) -> str:
    if not isinstance(value, str):
        raise OperatorLedgerError("Experiment operator ledger task packet id is invalid.")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise OperatorLedgerError("Experiment operator ledger task packet id is invalid.")
    if not all(char.isalnum() or char in {"-", "_"} for char in normalized):
        raise OperatorLedgerError("Experiment operator ledger task packet id is invalid.")
    if (
        SLACK_IDENTIFIER_RE.search(normalized)
        or SECRET_SHAPED_RE.search(normalized)
        or SHA256_HEX_RE.fullmatch(normalized.lower())
    ):
        raise OperatorLedgerError("Experiment operator ledger task packet id is invalid.")
    return normalized


def _validate_retention_days(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise OperatorLedgerError("Experiment operator ledger retention is invalid.")
    if value <= 0 or value > 366:
        raise OperatorLedgerError("Experiment operator ledger retention is invalid.")
    return value


def _validate_stale_after_days(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise OperatorLedgerError("Private-pilot activation stale window is invalid.")
    if value <= 0 or value > 90:
        raise OperatorLedgerError("Private-pilot activation stale window is invalid.")
    return value


def _safe_cli_stdout_payload(rendered: str) -> str:
    """Return a CLI stdout payload only after final no-leak enforcement."""

    if (
        SECRET_SHAPED_RE.search(rendered)
        or GITHUB_APP_TOKEN_ARTIFACT_RE.search(rendered)
        or SLACK_IDENTIFIER_RE.search(rendered)
        or LOCAL_PATH_RE.search(rendered)
        or CLI_OUTPUT_LOCAL_PATH_RE.search(rendered)
        or CLI_OUTPUT_PATCH_OR_LOG_RE.search(rendered)
    ):
        raise OperatorLedgerError("Experiment operator ledger output contains unsafe content.")
    return rendered


def _idempotency_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in IDEMPOTENCY_MATERIAL_FIELDS}


def _legacy_sha256_idempotency_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in LEGACY_SHA256_IDEMPOTENCY_MATERIAL_FIELDS}


def _legacy_sha256_idempotency_key(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(_legacy_sha256_idempotency_material(payload))
    ).hexdigest()[:24]


def _idempotency_key(payload: dict[str, Any]) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        _canonical_json_bytes(_idempotency_material(payload)),
        IDEMPOTENCY_KEY_NAMESPACE,
        IDEMPOTENCY_KEY_ITERATIONS,
        dklen=16,
    ).hex()[:24]


def _idempotency_key_check(payload: dict[str, Any], idempotency_key: str) -> str:
    stable = _idempotency_material(payload)
    stable["idempotency_key"] = idempotency_key
    return hashlib.pbkdf2_hmac(
        "sha256",
        _canonical_json_bytes(stable),
        IDEMPOTENCY_KEY_CHECK_NAMESPACE,
        IDEMPOTENCY_KEY_CHECK_ITERATIONS,
        dklen=32,
    ).hex()


def _content_hash(payload: dict[str, Any]) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        _canonical_json_bytes(payload),
        CONTENT_HASH_NAMESPACE,
        CONTENT_HASH_ITERATIONS,
        dklen=32,
    ).hex()


def normalize_operator_ledger_event(
    payload: dict[str, Any],
    *,
    derive_idempotency_key: bool = True,
) -> OperatorLedgerRecord:
    """Validate and normalize one local operator ledger event."""

    if not isinstance(payload, dict):
        raise OperatorLedgerError("Experiment operator ledger event must be an object.")
    _require_exact_keys(payload, allowed=REQUIRED_EVENT_FIELDS)
    normalized: dict[str, Any] = {
        "schema_version": _validate_enum(
            payload["schema_version"],
            allowed=frozenset({SCHEMA_VERSION}),
            label="schema_version",
        ),
        "generated_at": _validate_timestamp(payload["generated_at"]),
        "policy_version": _validate_enum(
            payload["policy_version"],
            allowed=frozenset({POLICY_VERSION}),
            label="policy_version",
        ),
        "provider_type": _validate_enum(
            payload["provider_type"],
            allowed=frozenset({PROVIDER_TYPE}),
            label="provider_type",
        ),
        "task_packet_id": _validate_task_packet_id(payload["task_packet_id"]),
        "command_kind": _validate_enum(
            payload["command_kind"],
            allowed=ALLOWED_COMMAND_KINDS,
            label="command_kind",
        ),
        "status": _validate_enum(payload["status"], allowed=ALLOWED_STATUS, label="status"),
        "failure_class": _validate_enum(
            payload["failure_class"],
            allowed=ALLOWED_FAILURE_CLASSES,
            label="failure_class",
        ),
        "dispatch_mode": _validate_enum(
            payload["dispatch_mode"],
            allowed=ALLOWED_DISPATCH_MODES,
            label="dispatch_mode",
        ),
        "workflow_file": _validate_enum(
            payload["workflow_file"],
            allowed=ALLOWED_WORKFLOW_FILES,
            label="workflow_file",
        ),
        "workflow_ref": _validate_enum(
            payload["workflow_ref"],
            allowed=ALLOWED_WORKFLOW_REFS,
            label="workflow_ref",
        ),
        "oracle_result_ref": _validate_artifact_ref(payload["oracle_result_ref"]),
        "slack_audit_ref": _validate_artifact_ref(payload["slack_audit_ref"]),
        "coauthor_required": _validate_bool(
            payload["coauthor_required"],
            label="coauthor_required",
        ),
        "coauthor_decision": _validate_enum(
            payload["coauthor_decision"],
            allowed=ALLOWED_COAUTHOR_DECISIONS,
            label="coauthor_decision",
        ),
        "human_review_outcome": _validate_enum(
            payload["human_review_outcome"],
            allowed=ALLOWED_REVIEW_OUTCOMES,
            label="human_review_outcome",
        ),
        "redaction_version": _validate_enum(
            payload["redaction_version"],
            allowed=frozenset({REDACTION_VERSION}),
            label="redaction_version",
        ),
        "retention_days": _validate_retention_days(payload["retention_days"]),
    }
    for field in sorted(HASH_FIELDS):
        normalized[field] = _validate_hash(payload[field])
        if field in REQUIRED_HASH_FIELDS and normalized[field] == "none":
            raise OperatorLedgerError("Experiment operator ledger hash field is invalid.")
    for field in sorted(AUTHORITY_FIELDS):
        normalized[field] = _validate_false(payload[field], label=field)
    if (normalized["workflow_file"] == "none") != (normalized["workflow_ref"] == "none"):
        raise OperatorLedgerError("Experiment operator ledger workflow target is invalid.")
    if normalized["status"] in {"dry_run", "dispatched", "observed"}:
        if normalized["failure_class"] != "none":
            raise OperatorLedgerError("Experiment operator ledger status/failure pair is invalid.")
    elif normalized["failure_class"] == "none":
        raise OperatorLedgerError("Experiment operator ledger status/failure pair is invalid.")
    if normalized["status"] == "dispatched" and (
        normalized["command_kind"] != "run-experiment" or normalized["dispatch_mode"] != "execute"
    ):
        raise OperatorLedgerError("Experiment operator ledger dispatch status is invalid.")
    if normalized["coauthor_required"] and normalized["coauthor_decision"] != "required":
        raise OperatorLedgerError("Experiment operator ledger coauthor decision is invalid.")
    if not normalized["coauthor_required"] and normalized["coauthor_decision"] == "required":
        raise OperatorLedgerError("Experiment operator ledger coauthor decision is invalid.")
    if derive_idempotency_key:
        idempotency_key = _idempotency_key(normalized)
        normalized["content_hash"] = _content_hash(normalized)
        normalized["idempotency_key"] = idempotency_key
        normalized["idempotency_key_check"] = _idempotency_key_check(
            normalized,
            idempotency_key,
        )
    return OperatorLedgerRecord(payload=normalized)


def _artifact_root(repo_root: Path) -> Path:
    return cast(
        Path,
        _normalized_absolute_path(repo_root / "artifacts" / "orchestration" / "experiments"),
    )


def _validate_ledger_dir(ledger_dir: Path, *, repo_root: Path) -> Path:
    artifact_root = _artifact_root(repo_root)
    candidate = ledger_dir.expanduser()
    if not candidate.is_absolute():
        candidate = _normalized_absolute_path(repo_root / candidate)
    else:
        candidate = _normalized_absolute_path(candidate)
    try:
        candidate.relative_to(artifact_root)
    except ValueError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger directory must stay under artifacts/orchestration/experiments."
        ) from exc
    relative_parts = candidate.relative_to(artifact_root).parts
    if "events" in relative_parts:
        raise OperatorLedgerError(
            "Experiment operator ledger directory must not target the reserved event store."
        )
    try:
        _reject_symlinked_output_components(
            candidate / "events" / "probe.json",
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
        _reject_symlinked_output_components(
            candidate / "tmp" / "probe.json",
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
    except SlackSocketAuditError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger directory must stay under artifacts/orchestration/experiments."
        ) from exc
    validated: Path = candidate
    return validated


def _validate_activation_evidence_dir(evidence_dir: Path, *, repo_root: Path) -> Path:
    artifact_root = _artifact_root(repo_root)
    candidate = evidence_dir.expanduser()
    if not candidate.is_absolute():
        candidate = _normalized_absolute_path(repo_root / candidate)
    else:
        candidate = _normalized_absolute_path(candidate)
    try:
        candidate.relative_to(artifact_root)
    except ValueError as exc:
        raise OperatorLedgerError(
            "Experiment private-pilot activation evidence directory must stay under "
            "artifacts/orchestration/experiments."
        ) from exc
    relative_parts = candidate.relative_to(artifact_root).parts
    if "events" in relative_parts or "tmp" in relative_parts:
        raise OperatorLedgerError(
            "Experiment private-pilot activation evidence directory is invalid."
        )
    try:
        _reject_symlinked_output_components(
            candidate / "probe.json",
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
        _reject_symlinked_output_components(
            candidate / "tmp" / "probe.json",
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
    except SlackSocketAuditError as exc:
        raise OperatorLedgerError(
            "Experiment private-pilot activation evidence directory must stay under "
            "artifacts/orchestration/experiments."
        ) from exc
    validated: Path = candidate
    return validated


def _validate_output_path(
    output_path: Path,
    *,
    repo_root: Path,
    ledger_dir: Path | None = None,
) -> Path:
    artifact_root = _artifact_root(repo_root)
    candidate = output_path.expanduser()
    if not candidate.is_absolute():
        candidate = _normalized_absolute_path(repo_root / candidate)
    else:
        candidate = _normalized_absolute_path(candidate)
    try:
        candidate.relative_to(artifact_root)
    except ValueError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger output must stay under artifacts/orchestration/experiments."
        ) from exc
    _validate_ledger_dir(
        ledger_dir or default_ledger_dir(repo_root),
        repo_root=repo_root,
    )
    relative_parts = candidate.relative_to(artifact_root).parts
    if "events" in relative_parts:
        raise OperatorLedgerError(
            "Experiment operator ledger output must not target the reserved event store."
        )
    try:
        _reject_symlinked_output_components(
            candidate,
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
    except SlackSocketAuditError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger output must stay under artifacts/orchestration/experiments."
        ) from exc
    validated: Path = candidate
    return validated


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _preflight_output_write(path: Path) -> None:
    if path.exists() and not path.is_file():
        raise OSError("Experiment operator ledger output target is invalid.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.preflight.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            temp_file.write("")
            temp_file.flush()
            os.fsync(temp_file.fileno())
    finally:
        if temp_path is not None:
            _unlink_if_exists(temp_path)


def _preflight_ledger_event_store(target_dir: Path) -> None:
    if target_dir.exists() and not target_dir.is_dir():
        raise OSError("Existing Experiment operator ledger directory is invalid.")
    event_dir = target_dir / "events"
    if event_dir.exists() and not event_dir.is_dir():
        raise OSError("Existing Experiment operator ledger event directory is invalid.")
    tmp_dir = target_dir / "tmp"
    if tmp_dir.exists() and not tmp_dir.is_dir():
        raise OSError("Existing Experiment operator ledger tmp directory is invalid.")
    event_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=".operator-ledger-preflight.",
        suffix=".tmp",
        dir=tmp_dir,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            temp_file.write("")
            temp_file.flush()
            os.fsync(temp_file.fileno())
    finally:
        if temp_path is not None:
            _unlink_if_exists(temp_path)


def preflight_slack_bridge_operator_ledger_event(
    *,
    task_packet_id: str | None,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
) -> str:
    """Validate local ledger context before a Slack bridge event can dispatch."""

    effective_root = repo_root or REPO_ROOT
    normalized_packet_id = _validate_task_packet_id(task_packet_id)
    target_dir = _validate_ledger_dir(
        ledger_dir or default_ledger_dir(effective_root),
        repo_root=effective_root,
    )
    try:
        _preflight_ledger_event_store(target_dir)
        load_operator_ledger_events(
            ledger_dir=target_dir,
            repo_root=effective_root,
        )
    except OSError as exc:
        raise OperatorLedgerError("Unable to write Experiment operator ledger event.") from exc
    return normalized_packet_id


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger audit evidence is unavailable."
        ) from exc


def _safe_artifact_ref_from_path(path: Path, *, repo_root: Path) -> str:
    artifact_root = _artifact_root(repo_root)
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = _normalized_absolute_path(repo_root / candidate)
    else:
        candidate = _normalized_absolute_path(candidate)
    try:
        candidate.relative_to(artifact_root)
        repo_relative = candidate.relative_to(_normalized_absolute_path(repo_root)).as_posix()
    except ValueError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger audit evidence must stay under artifacts."
        ) from exc
    return _validate_artifact_ref(repo_relative)


def write_slack_bridge_operator_ledger_event(
    *,
    task_packet_id: str | None,
    command_kind: str,
    status: str,
    dispatch_mode: str,
    workflow_file: str,
    workflow_ref: str,
    event_hash: str,
    channel_hash: str,
    user_hash: str,
    team_hash: str | None,
    branch_hash: str | None,
    hypothesis_hash: str | None,
    slack_audit_path: Path,
    failure_class: str | None = None,
    human_review_outcome: str = "pending",
    retention_days: int = DEFAULT_RETENTION_DAYS,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Write a strict local operator-ledger record for one Slack bridge decision."""

    effective_root = repo_root or REPO_ROOT
    normalized_packet_id = preflight_slack_bridge_operator_ledger_event(
        task_packet_id=task_packet_id,
        ledger_dir=ledger_dir,
        repo_root=effective_root,
    )
    workflow_enabled = command_kind == "run-experiment"
    payload = {
        "branch_hash": branch_hash if workflow_enabled else "none",
        "channel_hash": channel_hash,
        "claimed_merge_readiness": False,
        "coauthor_decision": "not_required",
        "coauthor_required": False,
        "command_kind": command_kind,
        "created_pr": False,
        "dispatch_mode": dispatch_mode,
        "event_hash": event_hash,
        "failure_class": failure_class or "none",
        "generated_at": _utcnow_iso(),
        "human_review_outcome": human_review_outcome,
        "hypothesis_hash": hypothesis_hash if workflow_enabled else "none",
        "oracle_result_hash": "none",
        "oracle_result_ref": "none",
        "policy_version": POLICY_VERSION,
        "product_runtime_changed": False,
        "provider_type": PROVIDER_TYPE,
        "redaction_version": REDACTION_VERSION,
        "resolved_review_threads": False,
        "retention_days": retention_days,
        "schema_version": SCHEMA_VERSION,
        "slack_audit_hash": _sha256_file(slack_audit_path),
        "slack_audit_ref": _safe_artifact_ref_from_path(
            slack_audit_path,
            repo_root=effective_root,
        ),
        "status": status,
        "task_packet_id": normalized_packet_id,
        "team_hash": team_hash,
        "user_hash": user_hash,
        "workflow_file": workflow_file if workflow_enabled else "none",
        "workflow_ref": workflow_ref if workflow_enabled else "none",
    }
    return write_operator_ledger_event(
        payload,
        ledger_dir=ledger_dir,
        repo_root=effective_root,
    )


def _write_operator_event_json(path: Path, payload: dict[str, Any], *, temp_dir: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=temp_dir,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            temp_file.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.link(temp_path, path)
    finally:
        if temp_path is not None:
            _unlink_if_exists(temp_path)


def write_operator_ledger_event(
    payload: dict[str, Any],
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Write one normalized event to the local operator ledger without overwrite."""

    effective_root = repo_root or REPO_ROOT
    record = normalize_operator_ledger_event(payload)
    target_dir = _validate_ledger_dir(
        ledger_dir or default_ledger_dir(effective_root),
        repo_root=effective_root,
    )
    if target_dir.exists() and not target_dir.is_dir():
        raise OperatorLedgerError("Existing Experiment operator ledger directory is invalid.")
    event_dir = target_dir / "events"
    if event_dir.exists() and not event_dir.is_dir():
        raise OperatorLedgerError("Existing Experiment operator ledger event directory is invalid.")
    try:
        event_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OperatorLedgerError("Unable to write Experiment operator ledger event.") from exc
    path = event_dir / f"{record.idempotency_key}.json"
    try:
        _write_operator_event_json(path, record.payload, temp_dir=target_dir / "tmp")
    except FileExistsError as exc:
        raise OperatorLedgerError("Experiment operator ledger event already exists.") from exc
    except OSError as exc:
        raise OperatorLedgerError("Unable to write Experiment operator ledger event.") from exc
    return path


def _read_private_pilot_activation_evidence(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.") from exc
    if not isinstance(raw, dict):
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.")
    try:
        normalized = cast(
            dict[str, Any],
            validate_private_pilot_activation_evidence(raw),
        )
    except PrivatePilotActivationEvidenceError as exc:
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.") from exc
    if path.stem != normalized["evidence_id"]:
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.")
    return normalized


def write_private_pilot_activation_evidence(
    payload: dict[str, Any],
    *,
    evidence_dir: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Validate and import one redacted private-pilot activation evidence artifact."""

    effective_root = repo_root or REPO_ROOT
    try:
        normalized = validate_private_pilot_activation_evidence(payload)
    except PrivatePilotActivationEvidenceError as exc:
        raise OperatorLedgerError("Private-pilot activation evidence input is invalid.") from exc
    target_dir = _validate_activation_evidence_dir(
        evidence_dir or default_activation_evidence_dir(effective_root),
        repo_root=effective_root,
    )
    if target_dir.exists() and not target_dir.is_dir():
        raise OperatorLedgerError(
            "Existing private-pilot activation evidence directory is invalid."
        )
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OperatorLedgerError("Unable to write private-pilot activation evidence.") from exc
    path = target_dir / f"{normalized['evidence_id']}.json"
    if path.exists():
        existing = _read_private_pilot_activation_evidence(path)
        if existing == normalized:
            return path
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.")
    try:
        _write_operator_event_json(path, normalized, temp_dir=target_dir / "tmp")
    except OSError as exc:
        raise OperatorLedgerError("Unable to write private-pilot activation evidence.") from exc
    return path


def load_private_pilot_activation_evidence(
    *,
    evidence_dir: Path | None = None,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Load local private-pilot activation evidence, failing closed on malformed artifacts."""

    effective_root = repo_root or REPO_ROOT
    target_dir = _validate_activation_evidence_dir(
        evidence_dir or default_activation_evidence_dir(effective_root),
        repo_root=effective_root,
    )
    if not target_dir.exists():
        return []
    if not target_dir.is_dir():
        raise OperatorLedgerError(
            "Existing private-pilot activation evidence directory is invalid."
        )
    tmp_dir = target_dir / "tmp"
    if tmp_dir.exists() and (not tmp_dir.is_dir() or tmp_dir.is_symlink()):
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.")
    try:
        entries = sorted(target_dir.iterdir())
    except OSError as exc:
        raise OperatorLedgerError("Unable to inspect private-pilot activation evidence.") from exc
    evidence_paths = [path for path in entries if path.name != "tmp"]
    unexpected = [path for path in evidence_paths if path.suffix != ".json" or not path.is_file()]
    if unexpected:
        raise OperatorLedgerError("Existing private-pilot activation evidence is invalid.")
    records = [_read_private_pilot_activation_evidence(path) for path in evidence_paths]
    return sorted(records, key=lambda record: (record["generated_at"], record["evidence_id"]))


def latest_private_pilot_activation_evidence(
    *,
    evidence_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    """Return latest validated private-pilot activation evidence if present."""

    records = load_private_pilot_activation_evidence(
        evidence_dir=evidence_dir,
        repo_root=repo_root,
    )
    return records[-1] if records else None


def validate_private_pilot_activation_evidence_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate downloaded redacted activation evidence without importing it."""

    try:
        return cast(dict[str, Any], validate_private_pilot_activation_evidence(payload))
    except PrivatePilotActivationEvidenceError as exc:
        raise OperatorLedgerError("Private-pilot activation evidence input is invalid.") from exc


def _activation_generated_at(record: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(str(record["generated_at"])).astimezone(timezone.utc)


def _activation_evidence_age_class(
    latest: dict[str, Any] | None,
    *,
    invalid: bool,
    now: datetime,
    stale_after_days: int,
) -> str:
    if invalid:
        return "invalid_local_artifact"
    if latest is None:
        return "absent"
    generated_at = _activation_generated_at(latest)
    return "stale" if generated_at + timedelta(days=stale_after_days) < now else "fresh"


def _activation_blocker_label(record: dict[str, Any]) -> str:
    state = str(record["activation_state"])
    if state == "blocked_by_missing_secret":
        return "missing_secret"
    if state == "blocked_by_allowlist":
        return "allowlist"
    if state in {"blocked_by_invalid_config", "invalid_local_artifact"}:
        return "invalid_config"
    if state == "smoke_failed_safely":
        return "failed_smoke"
    if state == "smoke_recorded":
        return "recorded_smoke"
    return "none"


def _activation_blocker_trend(records: list[dict[str, Any]], *, invalid: bool) -> str:
    if invalid:
        return "invalid_local_artifact"
    if not records:
        return "none"
    labels = [_activation_blocker_label(record) for record in records]
    latest_label = labels[-1]
    if latest_label in {"recorded_smoke", "failed_smoke", "none"}:
        return latest_label
    historical_blockers = {
        label
        for label in labels
        if label in {"missing_secret", "allowlist", "invalid_config", "failed_smoke"}
    }
    return "mixed_blockers" if len(historical_blockers) > 1 else latest_label


def _private_pilot_manual_smoke_operations_projection(
    records: list[dict[str, Any]],
    *,
    invalid: bool,
    now: datetime,
    stale_after_days: int,
) -> dict[str, Any]:
    latest = records[-1] if records else None
    evidence_age_class = _activation_evidence_age_class(
        latest,
        invalid=invalid,
        now=now,
        stale_after_days=stale_after_days,
    )
    blocker_trend = _activation_blocker_trend(records, invalid=invalid)
    if invalid:
        return {
            "activation_evidence_count": 0,
            "blocker_trend": blocker_trend,
            "evidence_age_class": evidence_age_class,
            "import_status": "invalid_local_artifact",
            "latest_activation_state": "invalid_local_artifact",
            "latest_smoke_class": "invalid_local_artifact",
            "next_operator_action": "inspect_sanitized_failure",
            "stale_after_days": stale_after_days,
        }
    if latest is None:
        return {
            "activation_evidence_count": 0,
            "blocker_trend": "none",
            "evidence_age_class": "absent",
            "import_status": "absent",
            "latest_activation_state": "manual_only",
            "latest_smoke_class": "none",
            "next_operator_action": "run_manual_live_smoke",
            "stale_after_days": stale_after_days,
        }
    return {
        "activation_evidence_count": len(records),
        "blocker_trend": blocker_trend,
        "evidence_age_class": evidence_age_class,
        "import_status": "valid",
        "latest_activation_state": latest["activation_state"],
        "latest_smoke_class": latest["last_smoke"],
        "next_operator_action": latest["next_operator_action"],
        "stale_after_days": stale_after_days,
    }


def _private_pilot_manual_smoke_summary(
    projection: dict[str, Any],
) -> tuple[str, ...]:
    return (
        f"private_pilot_evidence_age_class={projection['evidence_age_class']}",
        f"private_pilot_blocker_trend={projection['blocker_trend']}",
        f"private_pilot_import_status={projection['import_status']}",
    )


def latest_private_pilot_activation_summary(
    *,
    evidence_dir: Path | None = None,
    repo_root: Path | None = None,
    now: datetime | None = None,
    stale_after_days: int = DEFAULT_ACTIVATION_EVIDENCE_STALE_AFTER_DAYS,
) -> tuple[str, ...]:
    """Return latest private-pilot activation summary, sanitized on local failures."""

    effective_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    normalized_stale_days = _validate_stale_after_days(stale_after_days)
    try:
        records = load_private_pilot_activation_evidence(
            evidence_dir=evidence_dir,
            repo_root=repo_root,
        )
    except OperatorLedgerError:
        projection = _private_pilot_manual_smoke_operations_projection(
            [],
            invalid=True,
            now=effective_now,
            stale_after_days=normalized_stale_days,
        )
        return cast(
            tuple[str, ...],
            (
                *invalid_private_pilot_activation_summary(),
                *_private_pilot_manual_smoke_summary(projection),
            ),
        )
    projection = _private_pilot_manual_smoke_operations_projection(
        records,
        invalid=False,
        now=effective_now,
        stale_after_days=normalized_stale_days,
    )
    return cast(
        tuple[str, ...],
        (
            *render_private_pilot_activation_summary(records[-1] if records else None),
            *_private_pilot_manual_smoke_summary(projection),
        ),
    )


def _private_pilot_activation_projection(
    latest: dict[str, Any] | None,
    *,
    evidence_dir: Path | None,
    invalid: bool,
    repo_root: Path,
    manual_smoke_operations: dict[str, Any],
) -> dict[str, Any]:
    if invalid:
        return {
            "activation_state": "invalid_local_artifact",
            "artifact_ref": "none",
            "artifact_status": "invalid",
            "dispatch_outcome_class": "invalid_local_artifact",
            "evidence_graph_admission_status": "contract_only_not_runtime",
            "evidence_id": "none",
            "last_smoke": "invalid_local_artifact",
            "manual_smoke_operations": manual_smoke_operations,
            "next_operator_action": "inspect_sanitized_failure",
            "summary": (
                *invalid_private_pilot_activation_summary(),
                *_private_pilot_manual_smoke_summary(manual_smoke_operations),
            ),
        }
    if latest is None:
        return {
            "activation_state": "manual_only",
            "artifact_ref": "none",
            "artifact_status": "absent",
            "dispatch_outcome_class": "not_run",
            "evidence_graph_admission_status": "contract_only_not_runtime",
            "evidence_id": "none",
            "last_smoke": "none",
            "manual_smoke_operations": manual_smoke_operations,
            "next_operator_action": "run_manual_live_smoke",
            "summary": (
                *absent_private_pilot_activation_summary(),
                *_private_pilot_manual_smoke_summary(manual_smoke_operations),
            ),
        }
    target_dir = _validate_activation_evidence_dir(
        evidence_dir or default_activation_evidence_dir(repo_root),
        repo_root=repo_root,
    )
    artifact_path = target_dir / f"{latest['evidence_id']}.json"
    return {
        "activation_state": latest["activation_state"],
        "artifact_ref": _safe_artifact_ref_from_path(artifact_path, repo_root=repo_root),
        "artifact_status": "valid",
        "dispatch_outcome_class": latest["dispatch_outcome_class"],
        "evidence_graph_admission_status": latest["evidence_graph_admission_status"],
        "evidence_id": latest["evidence_id"],
        "last_smoke": latest["last_smoke"],
        "manual_smoke_operations": manual_smoke_operations,
        "next_operator_action": latest["next_operator_action"],
        "summary": (
            *render_private_pilot_activation_summary(latest),
            *_private_pilot_manual_smoke_summary(manual_smoke_operations),
        ),
    }


def _read_record(path: Path) -> OperatorLedgerRecord:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.") from exc
    if not isinstance(raw, dict):
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    derived = raw.get("idempotency_key")
    if not isinstance(derived, str) or not IDEMPOTENCY_KEY_RE.fullmatch(derived):
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    if path.stem != derived:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    if set(raw) == LEGACY_EVENT_FIELDS:
        return _read_legacy_sha256_record(raw, derived)
    _require_exact_keys(raw, allowed=EVENT_FIELDS)
    if DERIVED_EVENT_FIELDS - set(raw):
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    content_hash = raw.get("content_hash")
    if not isinstance(content_hash, str) or SHA256_HEX_RE.fullmatch(content_hash) is None:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    idempotency_key_check = raw.get("idempotency_key_check")
    if (
        not isinstance(idempotency_key_check, str)
        or SHA256_HEX_RE.fullmatch(idempotency_key_check) is None
    ):
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    payload = dict(raw)
    for field in DERIVED_EVENT_FIELDS:
        payload.pop(field)
    record = normalize_operator_ledger_event(payload, derive_idempotency_key=False)
    if _content_hash(record.payload) != content_hash:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    if _idempotency_key_check(record.payload, derived) != idempotency_key_check:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    record.payload["content_hash"] = content_hash
    record.payload["idempotency_key"] = derived
    record.payload["idempotency_key_check"] = idempotency_key_check
    return record


def _read_legacy_sha256_record(raw: dict[str, Any], derived: str) -> OperatorLedgerRecord:
    payload = dict(raw)
    payload.pop("idempotency_key")
    record = normalize_operator_ledger_event(payload, derive_idempotency_key=False)
    if _legacy_sha256_idempotency_key(record.payload) != derived:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    record.payload["content_hash"] = _content_hash(record.payload)
    record.payload["idempotency_key"] = derived
    record.payload["idempotency_key_check"] = _idempotency_key_check(record.payload, derived)
    return record


def _record_is_retained(record: OperatorLedgerRecord, *, now: datetime) -> bool:
    generated_at = datetime.fromisoformat(str(record.payload["generated_at"])).astimezone(
        timezone.utc
    )
    retention_days = int(record.payload["retention_days"])
    return generated_at + timedelta(days=retention_days) >= now


def load_operator_ledger_events(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> list[OperatorLedgerRecord]:
    """Load local operator ledger events, failing closed on malformed records."""

    effective_root = repo_root or REPO_ROOT
    target_dir = _validate_ledger_dir(
        ledger_dir or default_ledger_dir(effective_root),
        repo_root=effective_root,
    )
    if target_dir.exists() and not target_dir.is_dir():
        raise OperatorLedgerError("Existing Experiment operator ledger directory is invalid.")
    event_dir = target_dir / "events"
    if not event_dir.exists():
        return []
    if not event_dir.is_dir():
        raise OperatorLedgerError("Existing Experiment operator ledger event directory is invalid.")
    try:
        entries = sorted(event_dir.iterdir())
    except OSError as exc:
        raise OperatorLedgerError("Unable to inspect Experiment operator ledger events.") from exc
    unexpected_paths = [path for path in entries if path.suffix != ".json" or not path.is_file()]
    if unexpected_paths:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    paths = entries
    symlinked_paths = [path for path in paths if path.is_symlink()]
    if symlinked_paths:
        raise OperatorLedgerError("Existing Experiment operator ledger event is symlinked.")
    records = [_read_record(path) for path in paths]
    effective_now = (
        (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    )
    retained_records = [
        record for record in records if _record_is_retained(record, now=effective_now)
    ]
    return sorted(
        retained_records, key=lambda record: (record.generated_at, record.idempotency_key)
    )


def latest_operator_ledger_record(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
    exclude_event_hash: str | None = None,
) -> OperatorLedgerRecord | None:
    """Return the latest local operator ledger record if one exists."""

    records = load_operator_ledger_events(ledger_dir=ledger_dir, repo_root=repo_root)
    if exclude_event_hash is not None:
        normalized_excluded = _validate_hash(exclude_event_hash)
        records = [
            record for record in records if record.payload["event_hash"] != normalized_excluded
        ]
    return records[-1] if records else None


def _hash_prefix(value: Any) -> str:
    normalized = _validate_hash(value)
    if normalized == "none":
        return normalized
    return normalized[:16]


def _value_hash_prefix(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def _result_metadata(artifact_status: str, artifact_ref: str, **values: Any) -> dict[str, Any]:
    metadata = {"artifact_status": artifact_status, "artifact_ref": artifact_ref}
    metadata.update(values)
    return metadata


def _validate_result_artifact_path(artifact_ref: str, *, repo_root: Path) -> Path:
    if not artifact_ref.startswith(EXPERIMENT_RESULTS_REPO_PREFIX):
        raise OperatorLedgerError("Experiment result artifact reference is invalid.")
    artifact_root = _artifact_root(repo_root)
    results_root = cast(
        Path,
        _normalized_absolute_path(repo_root / EXPERIMENT_RESULTS_REPO_PREFIX),
    )
    candidate = cast(Path, _normalized_absolute_path(repo_root / artifact_ref))
    try:
        candidate.relative_to(results_root)
        candidate.relative_to(artifact_root)
    except ValueError as exc:
        raise OperatorLedgerError("Experiment result artifact reference is invalid.") from exc
    try:
        _reject_symlinked_output_components(
            candidate,
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
    except SlackSocketAuditError as exc:
        raise OperatorLedgerError("Experiment result artifact reference is invalid.") from exc
    if candidate.exists() and (not candidate.is_file() or candidate.is_symlink()):
        raise OperatorLedgerError("Experiment result artifact reference is invalid.")
    return candidate


def _safe_result_metadata_from_ref(
    artifact_ref: Any,
    *,
    repo_root: Path,
    expected_result_hash: Any = "none",
) -> dict[str, Any]:
    try:
        normalized_ref = _validate_artifact_ref(artifact_ref)
        normalized_expected_hash = _validate_hash(expected_result_hash)
    except OperatorLedgerError:
        return dict(RESULT_METADATA_INVALID)
    if normalized_ref == "none":
        return dict(RESULT_METADATA_ABSENT)
    try:
        result_path = _validate_result_artifact_path(normalized_ref, repo_root=repo_root)
    except OperatorLedgerError:
        return _result_metadata("invalid", normalized_ref)
    if not result_path.exists():
        return _result_metadata("missing", normalized_ref)
    try:
        if (
            normalized_expected_hash == "none"
            or _sha256_file(result_path) != normalized_expected_hash
        ):
            return _result_metadata("invalid", normalized_ref)
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Experiment result must be a JSON object.")
        result = validate_experiment_result(raw)
    except (
        OSError,
        OperatorLedgerError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
    ):
        return _result_metadata("invalid", normalized_ref)
    metadata = {
        "schema_version": result["schema_version"],
        "experiment_id_hash": _value_hash_prefix(result["experiment_id"]),
        "runner_mode": result["runner_mode"],
        "status": result["status"],
        "failure_class": result["failure_class"] or "none",
        "mutated_paths_count": len(result["mutated_paths"]),
        "shared_tree_untouched": result["shared_tree_untouched"],
        "promotion_ready": result["promotion_ready"],
        "contribution_kind": result["contribution_kind"],
        "coauthor_required": result["coauthor_required"],
    }
    return _result_metadata("valid", normalized_ref, **metadata)


def latest_operator_ledger_summary(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
    exclude_event_hash: str | None = None,
) -> tuple[str, ...]:
    """Return Slack-safe summary lines for the latest local operator ledger event."""

    try:
        record = latest_operator_ledger_record(
            ledger_dir=ledger_dir,
            repo_root=repo_root,
            exclude_event_hash=exclude_event_hash,
        )
    except OperatorLedgerError:
        return (
            "operator_ledger_status=invalid_local_artifact",
            "operator_ledger_scope=local_only",
            "operator_ledger_authority=display_only",
        )
    if record is None:
        return (
            "operator_ledger_status=absent",
            "operator_ledger_scope=local_only",
            "operator_ledger_authority=display_only",
        )
    payload = record.payload
    return (
        f"operator_ledger_status={payload['status']}",
        f"operator_ledger_failure_class={payload['failure_class']}",
        f"operator_ledger_command_kind={payload['command_kind']}",
        f"operator_ledger_dispatch_mode={payload['dispatch_mode']}",
        f"operator_ledger_workflow_file={payload['workflow_file']}",
        f"operator_ledger_workflow_ref={payload['workflow_ref']}",
        f"operator_ledger_branch_hash={_hash_prefix(payload['branch_hash'])}",
        f"operator_ledger_hypothesis_hash={_hash_prefix(payload['hypothesis_hash'])}",
        f"operator_ledger_oracle_ref={payload['oracle_result_ref']}",
        "operator_ledger_scope=local_only",
        "operator_ledger_authority=display_only",
    )


def build_operator_observability_report(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
    activation_readiness: dict[str, Any] | None = None,
    activation_evidence_dir: Path | None = None,
    now: datetime | None = None,
    activation_evidence_stale_after_days: int = DEFAULT_ACTIVATION_EVIDENCE_STALE_AFTER_DAYS,
) -> dict[str, Any]:
    """Build a redacted local observability report from operator ledger events."""

    effective_root = repo_root or REPO_ROOT
    effective_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    normalized_stale_days = _validate_stale_after_days(activation_evidence_stale_after_days)
    records = load_operator_ledger_events(ledger_dir=ledger_dir, repo_root=effective_root)
    activation_evidence_records: list[dict[str, Any]] = []
    activation_evidence_invalid = False
    try:
        activation_evidence_records = load_private_pilot_activation_evidence(
            evidence_dir=activation_evidence_dir,
            repo_root=effective_root,
        )
    except OperatorLedgerError:
        activation_evidence_invalid = True
    by_status = Counter(str(record.payload["status"]) for record in records)
    by_failure = Counter(str(record.payload["failure_class"]) for record in records)
    by_command = Counter(str(record.payload["command_kind"]) for record in records)
    by_dispatch_mode = Counter(str(record.payload["dispatch_mode"]) for record in records)
    by_activation_state = Counter(
        str(record["activation_state"]) for record in activation_evidence_records
    )
    if activation_evidence_invalid:
        by_activation_state["invalid_local_artifact"] += 1
    result_artifacts = [
        _safe_result_metadata_from_ref(
            record.payload["oracle_result_ref"],
            repo_root=effective_root,
            expected_result_hash=record.payload["oracle_result_hash"],
        )
        for record in records
    ]
    by_result_artifact_status = Counter(
        str(metadata["artifact_status"]) for metadata in result_artifacts
    )
    source_counts = {
        "private_pilot_activation_evidence": len(activation_evidence_records),
        "operator_ledger_events": len(records),
        "result_artifact_refs": sum(
            1 for metadata in result_artifacts if metadata.get("artifact_status") != "absent"
        ),
    }
    malformed_artifact_counts = {
        "invalid_private_pilot_activation_evidence": 1 if activation_evidence_invalid else 0,
        "invalid_result_artifacts": by_result_artifact_status.get("invalid", 0),
        "missing_result_artifacts": by_result_artifact_status.get("missing", 0),
    }
    latest = records[-1].payload if records else None
    latest_result_metadata = result_artifacts[-1] if result_artifacts else None
    latest_activation = activation_evidence_records[-1] if activation_evidence_records else None
    manual_smoke_operations = _private_pilot_manual_smoke_operations_projection(
        activation_evidence_records,
        invalid=activation_evidence_invalid,
        now=effective_now,
        stale_after_days=normalized_stale_days,
    )
    latest_activation_projection = _private_pilot_activation_projection(
        latest_activation,
        evidence_dir=activation_evidence_dir,
        invalid=activation_evidence_invalid,
        repo_root=effective_root,
        manual_smoke_operations=manual_smoke_operations,
    )
    redaction_value_stored = False
    return {
        "authority_boundary": {
            "claimed_merge_readiness": False,
            "created_pr": False,
            "product_runtime_changed": False,
            "resolved_review_threads": False,
        },
        "activation_readiness": activation_readiness or manual_only_activation_readiness_report(),
        "by_command_kind": dict(sorted(by_command.items())),
        "by_dispatch_mode": dict(sorted(by_dispatch_mode.items())),
        "by_failure_class": dict(sorted(by_failure.items())),
        "by_private_pilot_activation_state": dict(sorted(by_activation_state.items())),
        "by_result_artifact_status": dict(sorted(by_result_artifact_status.items())),
        "by_status": dict(sorted(by_status.items())),
        "evidence_graph_admission_status": "contract_only_not_runtime",
        "event_count": len(records),
        "latest": (
            {
                "branch_hash": _hash_prefix(latest["branch_hash"]),
                "command_kind": latest["command_kind"],
                "coauthor_decision": latest["coauthor_decision"],
                "coauthor_required": latest["coauthor_required"],
                "dispatch_mode": latest["dispatch_mode"],
                "failure_class": latest["failure_class"],
                "human_review_outcome": latest["human_review_outcome"],
                "hypothesis_hash": _hash_prefix(latest["hypothesis_hash"]),
                "oracle_result_ref": latest["oracle_result_ref"],
                "result_metadata": latest_result_metadata,
                "status": latest["status"],
                "workflow_file": latest["workflow_file"],
                "workflow_ref": latest["workflow_ref"],
            }
            if latest
            else None
        ),
        "malformed_artifact_counts": malformed_artifact_counts,
        "policy_version": POLICY_VERSION,
        "private_pilot_activation_evidence": latest_activation_projection,
        "private_pilot_activation_summary": list(latest_activation_projection["summary"]),
        "private_pilot_manual_smoke_operations": manual_smoke_operations,
        "redaction_version": REDACTION_VERSION,
        "redaction_summary": {
            "approval_digests_stored": False,
            "health_data_stored": False,
            "local_paths_stored": False,
            "patch_text_stored": False,
            "provider_logs_stored": False,
            "raw_branch_refs_stored": False,
            "raw_hypotheses_stored": False,
            "raw_slack_text_stored": False,
            "slack_ids_stored": False,
            "token_prefixes_stored": redaction_value_stored,
        },
        "report_scope": "local_operator_plane_only",
        "result_artifacts": result_artifacts,
        "schema_version": SCHEMA_VERSION,
        "source_counts": source_counts,
    }


def render_operator_observability_markdown(report: dict[str, Any]) -> str:
    """Render a deterministic local-only Markdown report."""

    latest = report["latest"] or {}
    activation_readiness = report.get("activation_readiness") or (
        manual_only_activation_readiness_report()
    )
    lines = [
        "# Experiment Runner Operator Ledger Report",
        "",
        "- Scope: local operator-plane evidence only",
        "- Authority: display-only; not PR, review-thread, merge-readiness, or product truth",
        f"- Policy version: `{report['policy_version']}`",
        f"- Evidence graph admission: `{report['evidence_graph_admission_status']}`",
        f"- Event count: `{report['event_count']}`",
        "",
        "## Latest",
    ]
    if latest:
        for key in (
            "status",
            "failure_class",
            "command_kind",
            "dispatch_mode",
            "coauthor_decision",
            "coauthor_required",
            "human_review_outcome",
            "workflow_file",
            "workflow_ref",
            "branch_hash",
            "hypothesis_hash",
            "oracle_result_ref",
        ):
            lines.append(f"- {key}: `{latest[key]}`")
        result_metadata = latest.get("result_metadata") or {}
        lines.extend(["", "## Latest Result Metadata"])
        for key in (
            "artifact_status",
            *SAFE_RESULT_METADATA_FIELDS,
        ):
            if key in result_metadata:
                lines.append(f"- {key}: `{result_metadata[key]}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Activation Readiness"])
    for summary_item in render_activation_readiness_summary(activation_readiness):
        key, value = summary_item.split("=", 1)
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Private Pilot Activation Evidence"])
    private_pilot_summary = report.get("private_pilot_activation_summary") or (
        absent_private_pilot_activation_summary()
    )
    for summary_item in private_pilot_summary:
        key, value = summary_item.split("=", 1)
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Private Pilot Manual Smoke Operations"])
    manual_smoke_operations = report.get("private_pilot_manual_smoke_operations", {})
    if isinstance(manual_smoke_operations, dict) and manual_smoke_operations:
        for key, value in sorted(manual_smoke_operations.items()):
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")
    for section, key in (
        ("Status Counts", "by_status"),
        ("Failure Class Counts", "by_failure_class"),
        ("Command Counts", "by_command_kind"),
        ("Dispatch Mode Counts", "by_dispatch_mode"),
        ("Private Pilot Activation State Counts", "by_private_pilot_activation_state"),
        ("Result Artifact Counts", "by_result_artifact_status"),
        ("Source Counts", "source_counts"),
        ("Malformed Artifact Counts", "malformed_artifact_counts"),
        ("Redaction Summary", "redaction_summary"),
    ):
        lines.extend(["", f"## {section}"])
        counts = report.get(key, {})
        if counts:
            for name, count in counts.items():
                lines.append(f"- `{name}`: `{count}`")
        else:
            lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundary",
            "- created_pr: `false`",
            "- resolved_review_threads: `false`",
            "- claimed_merge_readiness: `false`",
            "- product_runtime_changed: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def _html_cell(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _render_html_table(rows: list[tuple[str, Any]]) -> str:
    if not rows:
        return "<p>none</p>"
    rendered_rows = [
        f'<tr><th scope="row">{_html_cell(name)}</th><td>{_html_cell(value)}</td></tr>'
        for name, value in rows
    ]
    return "<table><tbody>" + "".join(rendered_rows) + "</tbody></table>"


def render_operator_observability_html(report: dict[str, Any]) -> str:
    """Render a deterministic escaped local-only HTML report."""

    latest = report["latest"] or {}
    latest_result = latest.get("result_metadata") if latest else None
    activation_readiness = report.get("activation_readiness") or (
        manual_only_activation_readiness_report()
    )
    sections: list[str] = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Experiment Runner Operator Ledger Report</title>",
        "</head>",
        "<body>",
        "<h1>Experiment Runner Operator Ledger Report</h1>",
        "<p>Scope: local operator-plane evidence only.</p>",
        (
            "<p>Authority: display-only; not PR, review-thread, merge-readiness, "
            "or product truth.</p>"
        ),
        _render_html_table(
            [
                ("policy_version", report["policy_version"]),
                ("redaction_version", report["redaction_version"]),
                (
                    "evidence_graph_admission_status",
                    report.get(
                        "evidence_graph_admission_status",
                        "contract_only_not_runtime",
                    ),
                ),
                ("event_count", report["event_count"]),
            ]
        ),
        "<h2>Latest</h2>",
    ]
    if latest:
        sections.append(
            _render_html_table(
                [
                    (key, latest[key])
                    for key in (
                        "status",
                        "failure_class",
                        "command_kind",
                        "dispatch_mode",
                        "coauthor_decision",
                        "coauthor_required",
                        "human_review_outcome",
                        "workflow_file",
                        "workflow_ref",
                        "branch_hash",
                        "hypothesis_hash",
                        "oracle_result_ref",
                    )
                ]
            )
        )
        sections.append("<h2>Latest Result Metadata</h2>")
        if isinstance(latest_result, dict):
            sections.append(
                _render_html_table(
                    [
                        (key, latest_result[key])
                        for key in (
                            "artifact_status",
                            *SAFE_RESULT_METADATA_FIELDS,
                        )
                        if key in latest_result
                    ]
                )
            )
        else:
            sections.append("<p>none</p>")
    else:
        sections.append("<p>none</p>")
    sections.extend(
        [
            "<h2>Activation Readiness</h2>",
            _render_html_table(
                [
                    tuple(summary_item.split("=", 1))
                    for summary_item in render_activation_readiness_summary(activation_readiness)
                ]
            ),
            "<h2>Private Pilot Activation Evidence</h2>",
            _render_html_table(
                [
                    tuple(summary_item.split("=", 1))
                    for summary_item in (
                        report.get("private_pilot_activation_summary")
                        or absent_private_pilot_activation_summary()
                    )
                ]
            ),
            "<h2>Private Pilot Manual Smoke Operations</h2>",
            _render_html_table(
                sorted((report.get("private_pilot_manual_smoke_operations") or {}).items())
            ),
        ]
    )
    for title, key in (
        ("Status Counts", "by_status"),
        ("Failure Class Counts", "by_failure_class"),
        ("Command Counts", "by_command_kind"),
        ("Dispatch Mode Counts", "by_dispatch_mode"),
        ("Private Pilot Activation State Counts", "by_private_pilot_activation_state"),
        ("Result Artifact Counts", "by_result_artifact_status"),
        ("Source Counts", "source_counts"),
        ("Malformed Artifact Counts", "malformed_artifact_counts"),
        ("Redaction Summary", "redaction_summary"),
    ):
        sections.append(f"<h2>{_html_cell(title)}</h2>")
        values = report.get(key, {})
        sections.append(_render_html_table(sorted(values.items())))
    sections.extend(
        [
            "<h2>Boundary</h2>",
            _render_html_table(sorted(report["authority_boundary"].items())),
            "</body>",
            "</html>",
            "",
        ]
    )
    return "\n".join(sections)


def _report_set_output_paths(
    report_dir: Path | None,
    *,
    repo_root: Path,
    ledger_dir: Path | None = None,
) -> dict[str, Path]:
    target_dir = report_dir or default_observability_report_dir(repo_root)
    return {
        "json": _validate_output_path(
            target_dir / "operator_observability_report.json",
            repo_root=repo_root,
            ledger_dir=ledger_dir,
        ),
        "markdown": _validate_output_path(
            target_dir / "operator_observability_report.md",
            repo_root=repo_root,
            ledger_dir=ledger_dir,
        ),
        "html": _validate_output_path(
            target_dir / "operator_observability_report.html",
            repo_root=repo_root,
            ledger_dir=ledger_dir,
        ),
    }


def write_operator_observability_report_set(
    report: dict[str, Any],
    *,
    report_dir: Path | None = None,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, str]:
    """Write JSON, Markdown, and HTML observability reports under local artifacts."""

    effective_root = repo_root or REPO_ROOT
    paths = _report_set_output_paths(
        report_dir,
        repo_root=effective_root,
        ledger_dir=ledger_dir,
    )
    safe_refs = {
        kind: _safe_artifact_ref_from_path(path, repo_root=effective_root)
        for kind, path in paths.items()
    }
    rendered = {
        "json": json.dumps(report, indent=2, sort_keys=True) + "\n",
        "markdown": render_operator_observability_markdown(report),
        "html": render_operator_observability_html(report),
    }
    for content in rendered.values():
        _safe_cli_stdout_payload(content)
    for path in paths.values():
        try:
            _preflight_output_write(path)
        except OSError as exc:
            raise OperatorLedgerError("Unable to write Experiment operator ledger output.") from exc
    for kind, path in paths.items():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered[kind], encoding="utf-8")
        except OSError as exc:
            raise OperatorLedgerError("Unable to write Experiment operator ledger output.") from exc
    return safe_refs


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorLedgerError("Experiment operator ledger input is invalid.") from exc
    if not isinstance(payload, dict):
        raise OperatorLedgerError("Experiment operator ledger input is invalid.")
    return payload


def _read_activation_evidence_json_object(path: Path) -> dict[str, Any]:
    candidate = path.expanduser()
    if candidate.is_symlink() or not candidate.is_file():
        raise OperatorLedgerError("Private-pilot activation evidence input is invalid.")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorLedgerError(PRIVATE_PILOT_ACTIVATION_INPUT_INVALID) from exc
    if not isinstance(payload, dict):
        raise OperatorLedgerError(PRIVATE_PILOT_ACTIVATION_INPUT_INVALID)
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-json", default=None, help="Sanitized operator ledger event JSON.")
    parser.add_argument(
        "--activation-evidence-json",
        default=None,
        help="Redacted private-pilot activation evidence JSON.",
    )
    parser.add_argument(
        "--ledger-dir",
        default=None,
        help="Local ledger directory under artifacts/orchestration/experiments.",
    )
    parser.add_argument(
        "--activation-evidence-dir",
        default=None,
        help=(
            "Local private-pilot activation evidence directory under "
            "artifacts/orchestration/experiments."
        ),
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Validate and record --event-json into the local operator ledger.",
    )
    parser.add_argument(
        "--record-activation-evidence",
        action="store_true",
        help=(
            "Validate and import --activation-evidence-json into the local "
            "private-pilot activation evidence store."
        ),
    )
    parser.add_argument(
        "--validate-activation-evidence",
        action="store_true",
        help=(
            "Validate --activation-evidence-json as downloaded redacted "
            "private-pilot activation evidence without importing it."
        ),
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Render a local observability report from the operator ledger.",
    )
    parser.add_argument(
        "--write-report-set",
        action="store_true",
        help=(
            "Write JSON, Markdown, and HTML reports under "
            "artifacts/orchestration/experiments/operator_observability/."
        ),
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help=(
            "Optional report-set directory under artifacts/orchestration/experiments. "
            "Defaults to operator_observability/."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("html", "json", "markdown"),
        default="json",
        help="Summary output format.",
    )
    parser.add_argument(
        "--activation-evidence-stale-after-days",
        type=int,
        default=DEFAULT_ACTIVATION_EVIDENCE_STALE_AFTER_DAYS,
        help=(
            "Local report/status stale classification window for private-pilot "
            "activation evidence."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path under artifacts/orchestration/experiments.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ledger_dir = Path(args.ledger_dir) if args.ledger_dir else None
    activation_evidence_dir = (
        Path(args.activation_evidence_dir) if args.activation_evidence_dir else None
    )
    report_dir = Path(args.report_dir) if args.report_dir else None
    try:
        stale_after_days = _validate_stale_after_days(args.activation_evidence_stale_after_days)
        if args.record and args.record_activation_evidence:
            raise OperatorLedgerError(
                "Experiment operator ledger cannot record multiple evidence types."
            )
        if args.validate_activation_evidence and (
            args.record
            or args.record_activation_evidence
            or args.summary
            or args.write_report_set
            or args.output
        ):
            raise OperatorLedgerError(
                "Private-pilot activation evidence validation cannot combine with other modes."
            )
        if args.write_report_set and (args.record or args.record_activation_evidence):
            raise OperatorLedgerError(
                "Experiment operator ledger report set cannot record evidence."
            )
        if args.write_report_set and args.summary:
            raise OperatorLedgerError(
                "Experiment operator ledger report set cannot combine with summary."
            )
        if args.write_report_set and args.output:
            raise OperatorLedgerError(
                "Experiment operator ledger report set uses deterministic outputs."
            )
        output_path = (
            _validate_output_path(
                Path(args.output),
                repo_root=REPO_ROOT,
                ledger_dir=ledger_dir,
            )
            if args.output
            else None
        )
        if args.summary and output_path is None:
            raise OperatorLedgerError(
                "Experiment operator ledger summary output requires --output."
            )
        if output_path:
            try:
                _preflight_output_write(output_path)
            except OSError as exc:
                raise OperatorLedgerError(
                    "Unable to write Experiment operator ledger output."
                ) from exc
        rendered: str | None = None
        stdout_payload: str | None = None
        if args.record:
            if args.event_json is None:
                raise OperatorLedgerError("Experiment operator ledger input is invalid.")
            path = write_operator_ledger_event(
                _read_json_object(Path(args.event_json).expanduser()),
                ledger_dir=ledger_dir,
            )
            payload = {
                "idempotency_key": path.stem,
                "status": "recorded",
            }
            stdout_payload = json.dumps(payload, sort_keys=True) + "\n"
        elif args.validate_activation_evidence:
            if args.activation_evidence_json is None:
                raise OperatorLedgerError(PRIVATE_PILOT_ACTIVATION_INPUT_INVALID)
            evidence = validate_private_pilot_activation_evidence_payload(
                _read_activation_evidence_json_object(
                    Path(args.activation_evidence_json).expanduser()
                )
            )
            payload = {
                "activation_state": evidence["activation_state"],
                "authority": "display_only",
                "dispatch_outcome_class": evidence["dispatch_outcome_class"],
                "evidence_graph_admission_status": evidence["evidence_graph_admission_status"],
                "import_status": "validation_only_not_imported",
                "last_smoke": evidence["last_smoke"],
                "next_operator_action": evidence["next_operator_action"],
                "status": "validated",
            }
            stdout_payload = json.dumps(payload, sort_keys=True) + "\n"
        elif args.record_activation_evidence:
            if args.activation_evidence_json is None:
                raise OperatorLedgerError(PRIVATE_PILOT_ACTIVATION_INPUT_INVALID)
            evidence = validate_private_pilot_activation_evidence_payload(
                _read_activation_evidence_json_object(
                    Path(args.activation_evidence_json).expanduser()
                )
            )
            target_dir = _validate_activation_evidence_dir(
                activation_evidence_dir or default_activation_evidence_dir(REPO_ROOT),
                repo_root=REPO_ROOT,
            )
            target_path = target_dir / f"{evidence['evidence_id']}.json"
            existed_before = target_path.exists()
            path = write_private_pilot_activation_evidence(
                evidence,
                evidence_dir=activation_evidence_dir,
            )
            payload = {
                "artifact_ref": _safe_artifact_ref_from_path(path, repo_root=REPO_ROOT),
                "evidence_id": path.stem,
                "import_status": "duplicate" if existed_before else "imported",
                "status": "validated",
                "store_path_class": "local_private_pilot_activation_store",
            }
            stdout_payload = json.dumps(payload, sort_keys=True) + "\n"
        elif args.write_report_set:
            report = build_operator_observability_report(
                ledger_dir=ledger_dir,
                activation_evidence_dir=activation_evidence_dir,
                activation_evidence_stale_after_days=stale_after_days,
            )
            stdout_payload = (
                json.dumps(
                    {
                        "outputs": write_operator_observability_report_set(
                            report,
                            report_dir=report_dir,
                            ledger_dir=ledger_dir,
                        ),
                        "status": "written",
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        elif args.summary:
            report = build_operator_observability_report(
                ledger_dir=ledger_dir,
                activation_evidence_dir=activation_evidence_dir,
                activation_evidence_stale_after_days=stale_after_days,
            )
            if args.format == "json":
                rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
            elif args.format == "html":
                rendered = render_operator_observability_html(report)
            else:
                rendered = render_operator_observability_markdown(report)
        else:
            stdout_payload = (
                json.dumps(
                    {"policy_version": POLICY_VERSION, "status": "idle"},
                    sort_keys=True,
                )
                + "\n"
            )
        if output_path:
            if rendered is None:
                rendered = stdout_payload
            if rendered is None:
                raise OperatorLedgerError("Experiment operator ledger output is invalid.")
            try:
                _safe_cli_stdout_payload(rendered)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding="utf-8")
            except OSError as exc:
                raise OperatorLedgerError(
                    "Unable to write Experiment operator ledger output."
                ) from exc
        else:
            if stdout_payload is None:
                raise OperatorLedgerError("Experiment operator ledger output is invalid.")
            sys.stdout.write(_safe_cli_stdout_payload(stdout_payload))
    except OperatorLedgerError as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
