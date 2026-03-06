"""Stateless web session cookie helpers (HMAC-BLAKE2s, fail-closed).

RU: Stateless web session cookie для PRO/VIP web-потока.
EN: Stateless web session cookie for PRO/VIP web flow.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import Response

from app.security.server_salt import require_server_salt

WEB_SESSION_COOKIE_NAME = "pp_web_session"
WEB_SESSION_TTL_ENV = "WEB_SESSION_TTL_SECONDS"
DEFAULT_WEB_SESSION_TTL_SECONDS = 60 * 60 * 12  # 12h
_COOKIE_PATH = "/"
_COOKIE_SAMESITE: Literal["lax"] = "lax"


@dataclass(frozen=True)
class WebSessionClaims:
    """Validated web session claims payload."""

    api_key: str
    tier: str
    issued_at_epoch: int
    expires_at_epoch: int


@dataclass(frozen=True)
class IssuedWebSession:
    """Issued web session token with normalized claims."""

    token: str
    claims: WebSessionClaims


def require_web_session_ttl_seconds() -> int:
    """Return session TTL from env with strict validation."""

    raw = (os.getenv(WEB_SESSION_TTL_ENV) or "").strip()
    if raw == "":
        return DEFAULT_WEB_SESSION_TTL_SECONDS
    try:
        ttl = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{WEB_SESSION_TTL_ENV} must be an integer >= 1.") from exc
    if ttl < 1:
        raise RuntimeError(f"{WEB_SESSION_TTL_ENV} must be an integer >= 1.")
    return ttl


def _derive_session_hmac_key(secret: str | None = None) -> bytes:
    """Derive scoped HMAC key from explicit secret or SERVER_SALT."""

    if secret is not None:
        normalized = secret.strip()
        if not normalized:
            raise RuntimeError("Explicit web-session secret must be non-empty (fail-closed).")
        return normalized.encode("utf-8")

    server_salt = require_server_salt()
    scoped_key = f"web_session_v1::{server_salt}"
    return hashlib.blake2s(scoped_key.encode("utf-8")).digest()


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes into URL-safe base64 without padding."""

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(encoded: str) -> bytes:
    """Decode URL-safe base64 with optional stripped padding."""

    pad_len = (-len(encoded)) % 4
    return base64.urlsafe_b64decode(encoded + ("=" * pad_len))


def _normalized_tier(raw_tier: str) -> str:
    """Normalize and validate tier claim."""

    tier = raw_tier.strip().upper()
    if tier not in {"PRO", "VIP"}:
        raise ValueError("web session tier must be PRO or VIP")
    return tier


def issue_web_session(
    *,
    api_key: str,
    tier: str,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
    secret: str | None = None,
) -> IssuedWebSession:
    """Issue signed stateless web session token."""

    normalized_key = api_key.strip()
    if not normalized_key:
        raise ValueError("api_key must be non-empty")

    normalized_tier = _normalized_tier(tier)
    ttl = ttl_seconds if ttl_seconds is not None else require_web_session_ttl_seconds()
    if ttl < 1:
        raise ValueError("ttl_seconds must be >= 1")

    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued_at = int(now_dt.timestamp())
    expires_at = issued_at + ttl
    claims = WebSessionClaims(
        api_key=normalized_key,
        tier=normalized_tier,
        issued_at_epoch=issued_at,
        expires_at_epoch=expires_at,
    )

    payload = {
        "api_key": claims.api_key,
        "tier": claims.tier,
        "iat": claims.issued_at_epoch,
        "exp": claims.expires_at_epoch,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = hmac.new(
        _derive_session_hmac_key(secret),
        payload_b64.encode("ascii"),
        hashlib.blake2s,
    ).hexdigest()

    return IssuedWebSession(token=f"{payload_b64}.{signature}", claims=claims)


def verify_web_session(
    token: str,
    *,
    now: datetime | None = None,
    secret: str | None = None,
) -> WebSessionClaims | None:
    """Verify signed token and return claims, else None (fail-closed)."""

    raw = token.strip()
    if not raw:
        return None

    parts = raw.split(".")
    if len(parts) != 2:
        return None

    payload_b64, signature = parts
    if not payload_b64 or not signature:
        return None

    expected_sig = hmac.new(
        _derive_session_hmac_key(secret),
        payload_b64.encode("ascii"),
        hashlib.blake2s,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, signature):
        return None

    try:
        payload_obj = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if not isinstance(payload_obj, dict):
        return None

    api_key = payload_obj.get("api_key")
    tier = payload_obj.get("tier")
    issued_at = payload_obj.get("iat")
    expires_at = payload_obj.get("exp")
    version = payload_obj.get("v")

    if not isinstance(api_key, str) or not api_key.strip():
        return None
    if not isinstance(tier, str):
        return None
    if not isinstance(issued_at, int) or not isinstance(expires_at, int):
        return None
    if version != 1:
        return None

    try:
        normalized_tier = _normalized_tier(tier)
    except ValueError:
        return None

    if issued_at < 0 or expires_at <= issued_at:
        return None

    now_epoch = int((now or datetime.now(timezone.utc)).astimezone(timezone.utc).timestamp())
    if now_epoch >= expires_at:
        return None

    return WebSessionClaims(
        api_key=api_key.strip(),
        tier=normalized_tier,
        issued_at_epoch=issued_at,
        expires_at_epoch=expires_at,
    )


def _is_secure_cookie_environment() -> bool:
    """Return Secure-cookie mode (fail-closed by default)."""

    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    return app_env not in {"local", "dev", "development", "test"}


def set_web_session_cookie(
    *,
    response: Response,
    token: str,
    ttl_seconds: int | None = None,
) -> None:
    """Set hardened session cookie."""

    ttl = ttl_seconds if ttl_seconds is not None else require_web_session_ttl_seconds()
    response.set_cookie(
        key=WEB_SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl,
        httponly=True,
        samesite=_COOKIE_SAMESITE,
        secure=_is_secure_cookie_environment(),
        path=_COOKIE_PATH,
    )


def clear_web_session_cookie(*, response: Response) -> None:
    """Clear hardened session cookie."""

    response.delete_cookie(
        key=WEB_SESSION_COOKIE_NAME,
        path=_COOKIE_PATH,
        httponly=True,
        samesite=_COOKIE_SAMESITE,
        secure=_is_secure_cookie_environment(),
    )
