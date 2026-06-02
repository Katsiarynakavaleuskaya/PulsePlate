#!/usr/bin/env python3
"""Local-only Experiment Runner operator ledger and observability report."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, cast

OPERATOR_LEDGER_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(OPERATOR_LEDGER_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(OPERATOR_LEDGER_REPO_ROOT))

from scripts.orchestration.context_pack import REPO_ROOT
from scripts.orchestration.experiment_slack_bridge_audit import _atomic_publish_json
from scripts.orchestration.experiment_slack_bridge_config import (
    _normalized_absolute_path,
    _reject_symlinked_output_components,
)
from scripts.orchestration.experiment_slack_bridge_constants import SHA256_HEX_RE
from scripts.orchestration.experiment_slack_bridge_models import SlackSocketAuditError
from scripts.orchestration.experiment_slack_redaction import SLACK_IDENTIFIER_RE, safe_artifact_ref

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "operator-plane-2026-06-02-v1"
REDACTION_VERSION = "experiment-slack-redaction-v1"
DEFAULT_RETENTION_DAYS = 30
PROVIDER_TYPE = "experiment_runner_operator_plane"
DEFAULT_LEDGER_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "operator_ledger"
IDEMPOTENCY_KEY_ITERATIONS = 120_000
IDEMPOTENCY_KEY_NAMESPACE = b"pulseplate-operator-ledger-idempotency-v1"
PII_SHAPED_ARTIFACT_RE = re.compile(
    r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|" r"\b\+?\d[\d .()_-]{7,}\d\b)"
)
LOCAL_PATH_SEGMENT_RE = re.compile(
    r"(^|/)(Users|home|var|opt|tmp|private|Volumes|etc|usr|Library|System)(/|$)"
)
WINDOWS_DRIVE_SEGMENT_RE = re.compile(r"(^|/)[A-Za-z]:/")

ALLOWED_COMMAND_KINDS = frozenset(
    {"help", "kpp-status", "mvp-evidence", "status", "run-experiment", "oracle-review"}
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
DERIVED_EVENT_FIELDS = frozenset({"idempotency_key"})
EVENT_FIELDS = REQUIRED_EVENT_FIELDS | DERIVED_EVENT_FIELDS


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


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


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
        or PII_SHAPED_ARTIFACT_RE.search(normalized_ref)
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
    if SLACK_IDENTIFIER_RE.search(normalized):
        raise OperatorLedgerError("Experiment operator ledger task packet id is invalid.")
    return normalized


def _validate_retention_days(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise OperatorLedgerError("Experiment operator ledger retention is invalid.")
    if value <= 0 or value > 366:
        raise OperatorLedgerError("Experiment operator ledger retention is invalid.")
    return value


def _idempotency_key(payload: dict[str, Any]) -> str:
    stable = {
        key: payload[key]
        for key in (
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
    }
    return hashlib.pbkdf2_hmac(
        "sha256",
        _canonical_json_bytes(stable),
        IDEMPOTENCY_KEY_NAMESPACE,
        IDEMPOTENCY_KEY_ITERATIONS,
        dklen=16,
    ).hex()[:24]


def normalize_operator_ledger_event(payload: dict[str, Any]) -> OperatorLedgerRecord:
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
    for field in sorted(AUTHORITY_FIELDS):
        normalized[field] = _validate_false(payload[field], label=field)
    if normalized["status"] in {"dry_run", "dispatched", "observed"}:
        if normalized["failure_class"] != "none":
            raise OperatorLedgerError("Experiment operator ledger status/failure pair is invalid.")
    elif normalized["failure_class"] == "none":
        raise OperatorLedgerError("Experiment operator ledger status/failure pair is invalid.")
    if normalized["coauthor_required"] and normalized["coauthor_decision"] != "required":
        raise OperatorLedgerError("Experiment operator ledger coauthor decision is invalid.")
    normalized["idempotency_key"] = _idempotency_key(normalized)
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
    try:
        _reject_symlinked_output_components(
            candidate / "events" / "probe.json",
            artifact_dir=artifact_root,
            repo_root=repo_root,
        )
    except SlackSocketAuditError as exc:
        raise OperatorLedgerError(
            "Experiment operator ledger directory must stay under artifacts/orchestration/experiments."
        ) from exc
    return candidate


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
    event_dir = (
        _validate_ledger_dir(
            ledger_dir or default_ledger_dir(repo_root),
            repo_root=repo_root,
        )
        / "events"
    )
    try:
        candidate.relative_to(event_dir)
    except ValueError:
        pass
    else:
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
    return candidate


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
    event_dir.mkdir(parents=True, exist_ok=True)
    path = event_dir / f"{record.idempotency_key}.json"
    try:
        _atomic_publish_json(path, record.payload, exclusive=True)
    except FileExistsError as exc:
        raise OperatorLedgerError("Experiment operator ledger event already exists.") from exc
    except OSError as exc:
        raise OperatorLedgerError("Unable to write Experiment operator ledger event.") from exc
    return path


def _read_record(path: Path) -> OperatorLedgerRecord:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.") from exc
    if not isinstance(raw, dict):
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    _require_exact_keys(raw, allowed=EVENT_FIELDS)
    if DERIVED_EVENT_FIELDS - set(raw):
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    derived = raw.get("idempotency_key")
    if not isinstance(derived, str) or not derived:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    payload = dict(raw)
    payload.pop("idempotency_key")
    record = normalize_operator_ledger_event(payload)
    if derived != record.idempotency_key:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    if path.stem != record.idempotency_key:
        raise OperatorLedgerError("Existing Experiment operator ledger event is invalid.")
    return record


def load_operator_ledger_events(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
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
        paths = sorted(event_dir.glob("*.json"))
    except OSError as exc:
        raise OperatorLedgerError("Unable to inspect Experiment operator ledger events.") from exc
    symlinked_paths = [path for path in paths if path.is_symlink()]
    if symlinked_paths:
        raise OperatorLedgerError("Existing Experiment operator ledger event is symlinked.")
    records = [_read_record(path) for path in paths]
    return sorted(records, key=lambda record: (record.generated_at, record.idempotency_key))


def latest_operator_ledger_record(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
) -> OperatorLedgerRecord | None:
    """Return the latest local operator ledger record if one exists."""

    records = load_operator_ledger_events(ledger_dir=ledger_dir, repo_root=repo_root)
    return records[-1] if records else None


def _hash_prefix(value: Any) -> str:
    normalized = _validate_hash(value)
    if normalized == "none":
        return normalized
    return normalized[:16]


def latest_operator_ledger_summary(
    *,
    ledger_dir: Path | None = None,
    repo_root: Path | None = None,
) -> tuple[str, ...]:
    """Return Slack-safe summary lines for the latest local operator ledger event."""

    try:
        record = latest_operator_ledger_record(ledger_dir=ledger_dir, repo_root=repo_root)
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
) -> dict[str, Any]:
    """Build a redacted local observability report from operator ledger events."""

    records = load_operator_ledger_events(ledger_dir=ledger_dir, repo_root=repo_root)
    by_status = Counter(str(record.payload["status"]) for record in records)
    by_failure = Counter(str(record.payload["failure_class"]) for record in records)
    by_command = Counter(str(record.payload["command_kind"]) for record in records)
    by_dispatch_mode = Counter(str(record.payload["dispatch_mode"]) for record in records)
    latest = records[-1].payload if records else None
    return {
        "authority_boundary": {
            "claimed_merge_readiness": False,
            "created_pr": False,
            "product_runtime_changed": False,
            "resolved_review_threads": False,
        },
        "by_command_kind": dict(sorted(by_command.items())),
        "by_dispatch_mode": dict(sorted(by_dispatch_mode.items())),
        "by_failure_class": dict(sorted(by_failure.items())),
        "by_status": dict(sorted(by_status.items())),
        "event_count": len(records),
        "latest": (
            {
                "branch_hash": _hash_prefix(latest["branch_hash"]),
                "command_kind": latest["command_kind"],
                "failure_class": latest["failure_class"],
                "hypothesis_hash": _hash_prefix(latest["hypothesis_hash"]),
                "oracle_result_ref": latest["oracle_result_ref"],
                "status": latest["status"],
                "workflow_file": latest["workflow_file"],
                "workflow_ref": latest["workflow_ref"],
            }
            if latest
            else None
        ),
        "policy_version": POLICY_VERSION,
        "redaction_version": REDACTION_VERSION,
        "report_scope": "local_operator_plane_only",
        "schema_version": SCHEMA_VERSION,
    }


def render_operator_observability_markdown(report: dict[str, Any]) -> str:
    """Render a deterministic local-only Markdown report."""

    latest = report["latest"] or {}
    lines = [
        "# Experiment Runner Operator Ledger Report",
        "",
        "- Scope: local operator-plane evidence only",
        "- Authority: display-only; not PR, review-thread, merge-readiness, or product truth",
        f"- Policy version: `{report['policy_version']}`",
        f"- Event count: `{report['event_count']}`",
        "",
        "## Latest",
    ]
    if latest:
        for key in (
            "status",
            "failure_class",
            "command_kind",
            "workflow_file",
            "workflow_ref",
            "branch_hash",
            "hypothesis_hash",
            "oracle_result_ref",
        ):
            lines.append(f"- {key}: `{latest[key]}`")
    else:
        lines.append("- none")
    for section, key in (
        ("Status Counts", "by_status"),
        ("Failure Class Counts", "by_failure_class"),
        ("Command Counts", "by_command_kind"),
        ("Dispatch Mode Counts", "by_dispatch_mode"),
    ):
        lines.extend(["", f"## {section}"])
        counts = report[key]
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


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorLedgerError("Experiment operator ledger input is invalid.") from exc
    if not isinstance(payload, dict):
        raise OperatorLedgerError("Experiment operator ledger input is invalid.")
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-json", default=None, help="Sanitized operator ledger event JSON.")
    parser.add_argument(
        "--ledger-dir",
        default=None,
        help="Local ledger directory under artifacts/orchestration/experiments.",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Validate and record --event-json into the local operator ledger.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Render a local observability report from the operator ledger.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Summary output format.",
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
    try:
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
            rendered = json.dumps(payload, sort_keys=True) + "\n"
        elif args.summary:
            report = build_operator_observability_report(ledger_dir=ledger_dir)
            rendered = (
                json.dumps(report, indent=2, sort_keys=True) + "\n"
                if args.format == "json"
                else render_operator_observability_markdown(report)
            )
        else:
            rendered = (
                json.dumps(
                    {"policy_version": POLICY_VERSION, "status": "idle"},
                    sort_keys=True,
                )
                + "\n"
            )
        if args.output:
            output_path = _validate_output_path(
                Path(args.output),
                repo_root=REPO_ROOT,
                ledger_dir=ledger_dir,
            )
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding="utf-8")
            except OSError as exc:
                raise OperatorLedgerError(
                    "Unable to write Experiment operator ledger output."
                ) from exc
        else:
            print(rendered, end="")
    except OperatorLedgerError as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
