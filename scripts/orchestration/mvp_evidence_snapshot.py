"""Durable sanitized MVP evidence snapshot for Slack operator surface.

RU: MVP evidence snapshot — aggregate-only, allowlist-first, no PII.
EN: MVP evidence snapshot is aggregate-only, allowlist-first, with no PII.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

SnapshotPolicyVersion = Literal["2026-05-30-v1"]

DEFAULT_SNAPSHOT_POLICY_VERSION: SnapshotPolicyVersion = "2026-05-30-v1"
DEFAULT_RETENTION_DAYS = 30
DEFAULT_PRODUCER_NAME = "mvp-evidence-snapshot"
DEFAULT_PRODUCER_VERSION = "1.0.0"

# Event name contract copied from frontend/src/lib/mvpObservability.ts.
# Any drift must be caught by test_mvp_evidence_event_contract_matches_frontend_source.
ALLOWED_EVENT_NAMES: tuple[str, ...] = (
    "guided_planning_viewed",
    "planning_intent_selected",
    "planning_time_selected",
    "planning_preview_seen",
    "tier_value_viewed",
    "primary_planning_cta_clicked",
    "wellness_boundary_viewed",
    "planning_save_prompt_viewed",
    "planning_auth_prompt_viewed",
    "planning_progress_state_viewed",
    "planning_save_clicked",
    "planning_continue_clicked",
)

# Allowlist of payload keys permitted in snapshot after sanitization.
ALLOWED_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "surface",
        "componentId",
        "routePath",
        "optionId",
        "tierLabel",
        "authState",
    }
)

# Defense-in-depth denylist. Keys containing any fragment are dropped.
_DENYLIST_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "access_token",
    "health_payload",
    "medical_record",
    "password",
    "prompt_text",
    "raw_prompt",
    "raw_response",
    "refresh_token",
    "response_text",
    "secret",
    "user_health",
    "user_payload",
    "email",
    "name",
    "weight",
    "height",
    "bmi",
    "healthcondition",
    "freetext",
    "nutritiontargets",
    "devicefingerprint",
    "cookieid",
    "trackingid",
    "sessiontoken",
    "sessionid",
    "phone",
    "address",
    "dob",
    "ssn",
    "gender",
    "diagnosis",
    "medication",
    "payment",
    "card",
    "ipaddress",
    "latitude",
    "longitude",
    "photo",
    "passwordhash",
    "token",
    "jwt",
)

_VALID_ROUTE_PATHS: frozenset[str] = frozenset({"/app", "/setup", "/plate", "/progress", "/pro"})
_VALID_AUTH_STATES: frozenset[str] = frozenset({"authenticated", "unauthenticated", "unknown"})
_SUPPORTED_POLICY_VERSIONS: frozenset[SnapshotPolicyVersion] = frozenset({"2026-05-30-v1"})

_SNAPSHOT_FILENAME_RE = re.compile(
    r"^mvp_evidence_snapshot_(?P<produced_at>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}(?:\.[0-9]+)?\+[0-9]{2}-[0-9]{2})_(?P<idempotency_key>[a-f0-9]{24})\.json$"
)


def _repo_root() -> Path:
    return Path(__file__).parent.parent.parent.resolve()


def _snapshot_dir() -> Path:
    return _repo_root() / "artifacts" / "orchestration" / "mvp_evidence_snapshots"


def _reject_symlinked_path(candidate: Path, *, anchor: Path) -> None:
    """Fail closed if candidate or any ancestor under anchor is a symlink."""
    resolved_anchor = anchor.resolve()
    # Check for symlinks before resolving
    for part in [candidate, *candidate.parents]:
        if part == resolved_anchor or part == anchor:
            break
        if part.is_symlink():
            raise ValueError(f"Snapshot path must not traverse a symlink: {part}")
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_anchor)
    except ValueError as exc:
        raise ValueError(f"Snapshot path must stay under {resolved_anchor}.") from exc


@dataclass(frozen=True)
class MvpEvidenceSnapshotLine:
    """Single immutable snapshot line with idempotency and fingerprint."""

    idempotency_key: str
    fingerprint: str
    produced_at: str
    producer_name: str
    producer_version: str
    policy_version: SnapshotPolicyVersion
    event_aggregates: dict[str, int]
    route_buckets: tuple[str, ...]
    auth_state_buckets: tuple[str, ...]
    coverage_flags: tuple[str, ...]


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint_payload(payload: Any) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"sha256:{digest}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Allowlist-first sanitization with denylist defense-in-depth."""
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        # Allowlist first
        if key not in ALLOWED_PAYLOAD_KEYS:
            continue
        # Denylist defense-in-depth
        lowered = key.lower()
        if any(fragment in lowered for fragment in _DENYLIST_KEY_FRAGMENTS):
            continue
        sanitized[key] = value
    return sanitized


def build_snapshot_line(
    events: list[dict[str, Any]],
    expected_event_names: tuple[str, ...] = ALLOWED_EVENT_NAMES,
    *,
    producer_name: str = DEFAULT_PRODUCER_NAME,
    producer_version: str = DEFAULT_PRODUCER_VERSION,
    policy_version: SnapshotPolicyVersion = DEFAULT_SNAPSHOT_POLICY_VERSION,
) -> MvpEvidenceSnapshotLine:
    """Build a deterministic snapshot line from sanitized events.

    Raises ValueError on invalid input.
    """
    event_aggregates: dict[str, int] = {name: 0 for name in expected_event_names}
    route_buckets: set[str] = set()
    auth_state_buckets: set[str] = set()

    for event in events:
        if not isinstance(event, dict):
            continue
        name = event.get("name")
        if name not in expected_event_names:
            continue
        event_aggregates[name] = event_aggregates.get(name, 0) + 1
        payload = _sanitize_payload(
            event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        )
        route_path = payload.get("routePath")
        if isinstance(route_path, str) and route_path in _VALID_ROUTE_PATHS:
            route_buckets.add(route_path)
        auth_state = payload.get("authState")
        if isinstance(auth_state, str) and auth_state in _VALID_AUTH_STATES:
            auth_state_buckets.add(auth_state)

    coverage_flags = tuple(
        f"{name}=present" if event_aggregates[name] > 0 else f"{name}=absent"
        for name in expected_event_names
    )

    produced_at = _now_iso()
    identity_payload = {
        "event_aggregates": event_aggregates,
        "route_buckets": sorted(route_buckets),
        "auth_state_buckets": sorted(auth_state_buckets),
        "coverage_flags": list(coverage_flags),
        "policy_version": policy_version,
        "producer_name": producer_name,
        "producer_version": producer_version,
        "produced_at": produced_at,
    }
    fingerprint = _fingerprint_payload(identity_payload)
    idempotency_key = hashlib.sha256(
        _canonical_json_bytes(
            {
                "producer_name": producer_name,
                "producer_version": producer_version,
                "produced_at": produced_at,
            }
        )
    ).hexdigest()[:24]

    return MvpEvidenceSnapshotLine(
        idempotency_key=idempotency_key,
        fingerprint=fingerprint,
        produced_at=produced_at,
        producer_name=producer_name,
        producer_version=producer_version,
        policy_version=policy_version,
        event_aggregates=event_aggregates,
        route_buckets=tuple(sorted(route_buckets)),
        auth_state_buckets=tuple(sorted(auth_state_buckets)),
        coverage_flags=coverage_flags,
    )


def _snapshot_line_to_dict(line: MvpEvidenceSnapshotLine) -> dict[str, Any]:
    return {
        "idempotency_key": line.idempotency_key,
        "fingerprint": line.fingerprint,
        "produced_at": line.produced_at,
        "producer_name": line.producer_name,
        "producer_version": line.producer_version,
        "policy_version": line.policy_version,
        "event_aggregates": line.event_aggregates,
        "route_buckets": list(line.route_buckets),
        "auth_state_buckets": list(line.auth_state_buckets),
        "coverage_flags": list(line.coverage_flags),
    }


def _snapshot_filename(line: MvpEvidenceSnapshotLine) -> str:
    safe_produced_at = line.produced_at.replace(":", "-")
    return f"mvp_evidence_snapshot_{safe_produced_at}_{line.idempotency_key}.json"


def write_snapshot_line(
    line: MvpEvidenceSnapshotLine,
    base_dir: Path | None = None,
) -> Path:
    """Atomic write of a single snapshot line as its own JSON file.

    Returns the written file path.
    Raises ValueError on path traversal or symlink injection.
    """
    raw_dir = base_dir or _snapshot_dir()
    anchor = (_repo_root() / "artifacts" / "orchestration").resolve()
    _reject_symlinked_path(raw_dir, anchor=anchor)
    target_dir = raw_dir.resolve()

    target_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = target_dir / _snapshot_filename(line)
    record = _canonical_json_bytes(_snapshot_line_to_dict(line))
    temp_file = snapshot_file.with_suffix(f".tmp.{os.getpid()}")
    try:
        with open(temp_file, "wb") as f:
            f.write(record)
            f.flush()
            os.fsync(f.fileno())
        temp_file.replace(snapshot_file)
    finally:
        if temp_file.exists():
            temp_file.unlink()
    return snapshot_file


def read_latest_snapshot_line(
    base_dir: Path | None = None,
) -> MvpEvidenceSnapshotLine | None:
    """Read the most recent snapshot line from the snapshot directory.

    Returns None if no snapshots exist or the latest file is corrupt.
    Raises ValueError on path traversal or symlink injection.
    """
    raw_dir = base_dir or _snapshot_dir()
    anchor = (_repo_root() / "artifacts" / "orchestration").resolve()
    _reject_symlinked_path(raw_dir, anchor=anchor)
    target_dir = raw_dir.resolve()

    if not target_dir.exists():
        return None

    snapshot_files: list[Path] = []
    for entry in target_dir.iterdir():
        if not entry.is_file():
            continue
        match = _SNAPSHOT_FILENAME_RE.match(entry.name)
        if match:
            snapshot_files.append(entry)

    if not snapshot_files:
        return None

    def _safe_mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0

    # Sort by mtime descending; tie-break by filename for determinism.
    snapshot_files.sort(key=lambda p: (_safe_mtime(p), p.name), reverse=True)
    latest = snapshot_files[0]
    _reject_symlinked_path(latest, anchor=anchor)

    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Policy version validation (fail closed on unknown versions)
        if data.get("policy_version") not in _SUPPORTED_POLICY_VERSIONS:
            return None
        # Runtime type validation
        if not (
            isinstance(data.get("event_aggregates"), dict)
            and isinstance(data.get("route_buckets"), list)
            and isinstance(data.get("auth_state_buckets"), list)
            and isinstance(data.get("coverage_flags"), list)
            and all(isinstance(v, int) for v in data["event_aggregates"].values())
            and all(isinstance(s, str) for s in data["route_buckets"])
            and all(isinstance(s, str) for s in data["auth_state_buckets"])
            and all(isinstance(s, str) for s in data["coverage_flags"])
        ):
            return None
        # Fingerprint verification
        recomputed_payload = {
            "event_aggregates": dict(data["event_aggregates"]),
            "route_buckets": sorted(data["route_buckets"]),
            "auth_state_buckets": sorted(data["auth_state_buckets"]),
            "coverage_flags": list(data["coverage_flags"]),
            "policy_version": data["policy_version"],
            "producer_name": data["producer_name"],
            "producer_version": data["producer_version"],
            "produced_at": data["produced_at"],
        }
        if data["fingerprint"] != _fingerprint_payload(recomputed_payload):
            return None
        return MvpEvidenceSnapshotLine(
            idempotency_key=data["idempotency_key"],
            fingerprint=data["fingerprint"],
            produced_at=data["produced_at"],
            producer_name=data["producer_name"],
            producer_version=data["producer_version"],
            policy_version=data["policy_version"],
            event_aggregates=dict(data["event_aggregates"]),
            route_buckets=tuple(data["route_buckets"]),
            auth_state_buckets=tuple(data["auth_state_buckets"]),
            coverage_flags=tuple(data["coverage_flags"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError, UnicodeDecodeError, OSError):
        return None


def cleanup_expired_snapshots(
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Delete snapshot files older than retention_days.

    Raises ValueError if retention_days is not positive.
    Returns a summary dict without exposing local paths.
    """
    if retention_days <= 0:
        raise ValueError("retention_days must be positive")
    raw_dir = base_dir or _snapshot_dir()
    anchor = (_repo_root() / "artifacts" / "orchestration").resolve()
    _reject_symlinked_path(raw_dir, anchor=anchor)
    target_dir = raw_dir.resolve()

    if not target_dir.exists():
        return {
            "deleted_count": 0,
            "expired_count": 0,
            "retention_days": retention_days,
            "status": "pass",
        }

    threshold = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    expired_count = 0
    deleted_count = 0
    for entry in target_dir.iterdir():
        if not entry.is_file():
            continue
        # Clean up stale temp files
        if entry.suffix == ".tmp":
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime < threshold:
                expired_count += 1
                try:
                    entry.unlink()
                    deleted_count += 1
                except OSError:
                    pass
            continue
        match = _SNAPSHOT_FILENAME_RE.match(entry.name)
        if not match:
            continue
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        if mtime < threshold:
            expired_count += 1
            try:
                entry.unlink()
                deleted_count += 1
            except OSError:
                pass

    return {
        "deleted_count": deleted_count,
        "expired_count": expired_count,
        "retention_days": retention_days,
        "status": "pass",
    }
