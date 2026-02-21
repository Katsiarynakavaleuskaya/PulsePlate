"""Agent Control Plane MVP primitives.

RU: Базовые примитивы Agent Control Plane (MVP):
- deny-by-default policy gate
- signed audit envelope
- short-lived scoped token issuing

EN: Agent Control Plane MVP primitives:
- deny-by-default policy gate
- signed audit envelope
- short-lived scoped token issuing
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

ALLOWLIST_ENV = "AGENT_CONTROL_ALLOWLIST"
AUDIT_SIGNING_KEY_ENV = "AGENT_CONTROL_AUDIT_SIGNING_KEY"
BROKER_HMAC_KEY_ENV = "AGENT_CONTROL_BROKER_HMAC_KEY"
SCOPED_TTL_ENV = "AGENT_CONTROL_SCOPED_TTL_SECONDS"

DEFAULT_SCOPED_TOKEN_TTL_SECONDS = 300


@dataclass(frozen=True)
class PolicyDecision:
    """Policy gate decision for a privileged action."""

    action: str
    target: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class SignedAuditEnvelope:
    """Signed audit payload for policy decisions."""

    action: str
    target: str
    allowed: bool
    reason: str
    metadata_hash: str
    timestamp_utc: str
    signature: str


@dataclass(frozen=True)
class IssuedScopedToken:
    """Short-lived scoped token issued by SecretsBoundary helper."""

    scope: str
    token: str
    issued_at_utc: str
    expires_at_utc: str


def _to_utc(value: datetime) -> datetime:
    """Normalize datetime to UTC.

    RU: Наивные datetime трактуем как UTC.
    EN: Naive datetimes are treated as UTC.
    """

    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601_utc(value: datetime) -> str:
    """Return deterministic ISO8601 UTC timestamp."""

    return _to_utc(value).isoformat()


def parse_allowlist(raw: str) -> set[tuple[str, str]]:
    """Parse allowlist from env value.

    Supported formats:
    - `action:target,action:target`
    - newline-separated `action:target`
    """

    pairs: set[tuple[str, str]] = set()
    compact = raw.replace("\n", ",")
    for entry in compact.split(","):
        candidate = entry.strip()
        if not candidate or ":" not in candidate:
            continue
        action, target = candidate.split(":", 1)
        action = action.strip()
        target = target.strip()
        if not action or not target:
            continue
        pairs.add((action, target))
    return pairs


def load_allowlist_from_env() -> set[tuple[str, str]]:
    """Load allowlist pairs from AGENT_CONTROL_ALLOWLIST env var."""

    raw = (os.getenv(ALLOWLIST_ENV) or "").strip()
    return parse_allowlist(raw)


def evaluate_policy(
    action: str,
    target: str,
    *,
    allowlist: set[tuple[str, str]] | None = None,
) -> PolicyDecision:
    """Evaluate deny-by-default policy.

    RU: Неизвестные пары action/target запрещаются по умолчанию.
    EN: Unknown action/target pairs are denied by default.
    """

    normalized_action = action.strip()
    normalized_target = target.strip()
    if not normalized_action or not normalized_target:
        return PolicyDecision(
            action=normalized_action,
            target=normalized_target,
            allowed=False,
            reason="invalid_action_or_target",
        )

    active_allowlist = allowlist if allowlist is not None else load_allowlist_from_env()
    if (normalized_action, normalized_target) in active_allowlist:
        return PolicyDecision(
            action=normalized_action,
            target=normalized_target,
            allowed=True,
            reason="allowlist_match",
        )
    return PolicyDecision(
        action=normalized_action,
        target=normalized_target,
        allowed=False,
        reason="deny_by_default",
    )


def require_policy_allow(
    action: str,
    target: str,
    *,
    allowlist: set[tuple[str, str]] | None = None,
) -> PolicyDecision:
    """Return allowed policy decision or raise PermissionError (fail-closed)."""

    decision = evaluate_policy(action, target, allowlist=allowlist)
    if not decision.allowed:
        raise PermissionError(
            f"Policy denied action={decision.action!r} target={decision.target!r}: {decision.reason}"
        )
    return decision


def require_audit_secret() -> str:
    """Return audit signing secret or raise (fail-closed)."""

    secret = (os.getenv(AUDIT_SIGNING_KEY_ENV) or "").strip()
    if not secret:
        raise RuntimeError(
            f"{AUDIT_SIGNING_KEY_ENV} is required for signed audit envelopes (fail-closed)."
        )
    return secret


def require_secrets_hmac_key() -> str:
    """Return secrets-boundary HMAC key or raise (fail-closed)."""

    key = (os.getenv(BROKER_HMAC_KEY_ENV) or "").strip()
    if not key:
        raise RuntimeError(
            f"{BROKER_HMAC_KEY_ENV} is required for scoped token issuing (fail-closed)."
        )
    return key


def require_scoped_token_ttl_seconds() -> int:
    """Return scoped token TTL from env with strict validation."""

    raw = (os.getenv(SCOPED_TTL_ENV) or "").strip()
    if raw == "":
        return DEFAULT_SCOPED_TOKEN_TTL_SECONDS

    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{SCOPED_TTL_ENV} must be an integer >= 1.") from exc
    if value < 1:
        raise RuntimeError(f"{SCOPED_TTL_ENV} must be an integer >= 1.")
    return value


def _metadata_hash(metadata: Mapping[str, Any] | None) -> str:
    """Return deterministic hash for metadata payload."""

    payload = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sign_audit_envelope(
    decision: PolicyDecision,
    *,
    metadata: Mapping[str, Any] | None = None,
    timestamp: datetime | None = None,
    secret: str | None = None,
) -> SignedAuditEnvelope:
    """Sign policy decision and return audit envelope.

    RU: Подписывает решение policy gate для tamper-evident аудита.
    EN: Signs policy decision for tamper-evident audit trail.
    """

    # Fail-closed: reject both None and empty-string secrets
    if secret is not None:
        signing_secret = secret.strip()
        if not signing_secret:
            raise RuntimeError("Explicit secret must be non-empty (fail-closed).")
    else:
        signing_secret = require_audit_secret()
    issued_at = _iso8601_utc(timestamp or datetime.now(timezone.utc))
    meta_hash = _metadata_hash(metadata)
    payload = (
        f"{decision.action}|{decision.target}|{int(decision.allowed)}|"
        f"{decision.reason}|{meta_hash}|{issued_at}"
    )
    signature = hmac.new(
        signing_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return SignedAuditEnvelope(
        action=decision.action,
        target=decision.target,
        allowed=decision.allowed,
        reason=decision.reason,
        metadata_hash=meta_hash,
        timestamp_utc=issued_at,
        signature=signature,
    )


def verify_audit_envelope(envelope: SignedAuditEnvelope, *, secret: str | None = None) -> bool:
    """Verify signed audit envelope integrity."""

    # Fail-closed: reject both None and empty-string secrets
    if secret is not None:
        signing_secret = secret.strip()
        if not signing_secret:
            raise RuntimeError("Explicit secret must be non-empty (fail-closed).")
    else:
        signing_secret = require_audit_secret()
    payload = (
        f"{envelope.action}|{envelope.target}|{int(envelope.allowed)}|"
        f"{envelope.reason}|{envelope.metadata_hash}|{envelope.timestamp_utc}"
    )
    expected_signature = hmac.new(
        signing_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, envelope.signature)


def issue_scoped_token(
    scope: str,
    *,
    ttl_seconds: int | None = None,
    now: datetime | None = None,
    hmac_key: str | None = None,
) -> IssuedScopedToken:
    """Issue short-lived scoped token.

    RU: Выдаёт короткоживущий токен для scoped-action, без хранения plaintext секретов.
    EN: Issues short-lived scoped token without plaintext secret persistence.
    """

    normalized_scope = scope.strip()
    if not normalized_scope:
        raise ValueError("scope must be non-empty")

    token_ttl = ttl_seconds if ttl_seconds is not None else require_scoped_token_ttl_seconds()
    if token_ttl < 1:
        raise ValueError("ttl_seconds must be >= 1")

    # Fail-closed: reject both None and empty-string keys
    if hmac_key is not None:
        key = hmac_key.strip()
        if not key:
            raise RuntimeError("Explicit hmac_key must be non-empty (fail-closed).")
    else:
        key = require_secrets_hmac_key()
    issued_at_dt = _to_utc(now or datetime.now(timezone.utc))
    expires_at_dt = issued_at_dt + timedelta(seconds=token_ttl)
    issued_at = _iso8601_utc(issued_at_dt)
    expires_at = _iso8601_utc(expires_at_dt)

    payload = f"{normalized_scope}|{issued_at}|{expires_at}"
    token = hmac.new(
        key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return IssuedScopedToken(
        scope=normalized_scope,
        token=token,
        issued_at_utc=issued_at,
        expires_at_utc=expires_at,
    )
