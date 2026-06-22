"""Stateless web session cookie helpers (PBKDF2-HMAC signature, fail-closed).

RU: Stateless web session cookie для PRO/VIP web-потока.
EN: Stateless web session cookie for PRO/VIP web flow.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Response

from app.security.server_salt import require_server_salt
from settings import is_production_like_env, is_raw_explicit_developer_env

WEB_SESSION_COOKIE_NAME = "pp_web_session"
WEB_SESSION_TTL_ENV = "WEB_SESSION_TTL_SECONDS"
DEFAULT_WEB_SESSION_TTL_SECONDS = 60 * 60 * 12  # 12h
_COOKIE_PATH = "/"
_COOKIE_SAMESITE: Literal["lax"] = "lax"
_SESSION_SIGNATURE_ITERATIONS = 20_000
# RU/EN: Допуск рассинхрона часов для `iat` (not-before), секунды.
_SESSION_IAT_CLOCK_SKEW_SECONDS = 120
_SESSION_ENCRYPTION_CONTEXT = b"web_session_v1::api_key"

logger = logging.getLogger(__name__)


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


def _sign_payload(*, payload_b64: str, secret: str | None = None) -> str:
    """Return deterministic PBKDF2-HMAC signature for payload string."""

    key = _derive_session_hmac_key(secret)
    return hashlib.pbkdf2_hmac(
        "sha256",
        payload_b64.encode("ascii"),
        key,
        _SESSION_SIGNATURE_ITERATIONS,
        dklen=32,
    ).hex()


@functools.lru_cache(maxsize=32)
def _fernet_key_b64_from_hmac_key(hmac_key: bytes) -> bytes:
    """Derive Fernet key material; PBKDF2 password is secret key, salt is public context.

    RU: Пароль PBKDF2 — секретный HMAC-ключ; соль — публичный контекст (стандартная семантика).
    EN: PBKDF2 password is the secret HMAC key; salt is the public context label.
    """

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        hmac_key,
        _SESSION_ENCRYPTION_CONTEXT,
        _SESSION_SIGNATURE_ITERATIONS,
        dklen=32,
    )
    return base64.urlsafe_b64encode(derived)


def _derive_session_encryption_key(secret: str | None = None) -> bytes:
    """Derive deterministic Fernet key for encrypted claim fields."""

    return _fernet_key_b64_from_hmac_key(_derive_session_hmac_key(secret))


def _encrypt_api_key(api_key: str, *, secret: str | None = None) -> str:
    """Encrypt API key so cookie payload does not expose raw credential."""

    cipher = Fernet(_derive_session_encryption_key(secret))
    encrypted: bytes = cipher.encrypt(api_key.encode("utf-8"))
    return encrypted.decode("ascii")


def _decrypt_api_key(encrypted_api_key: str, *, secret: str | None = None) -> str | None:
    """Decrypt API key claim from token payload, fail-closed."""

    try:
        cipher = Fernet(_derive_session_encryption_key(secret))
        decrypted = cipher.decrypt(encrypted_api_key.encode("ascii"))
    except (ValueError, InvalidToken):
        return None
    try:
        normalized = decrypted.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None
    return normalized if normalized else None


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
        "enc_api_key": _encrypt_api_key(claims.api_key, secret=secret),
        "tier": claims.tier,
        "iat": claims.issued_at_epoch,
        "exp": claims.expires_at_epoch,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = _sign_payload(payload_b64=payload_b64, secret=secret)

    return IssuedWebSession(token=f"{payload_b64}.{signature}", claims=claims)


def verify_web_session(
    token: str,
    *,
    now: datetime | None = None,
    secret: str | None = None,
) -> WebSessionClaims | None:
    """Verify signed token and return claims, else None (fail-closed).

    Misconfigured crypto env (e.g. missing SERVER_SALT when secret is omitted) returns None
    after a warning log; does not raise — callers may treat this like any other invalid token.
    """

    raw = token.strip()
    if not raw:
        return None

    parts = raw.split(".")
    if len(parts) != 2:
        return None

    payload_b64, signature = parts
    if not payload_b64 or not signature:
        return None

    try:
        expected_sig = _sign_payload(payload_b64=payload_b64, secret=secret)
    except RuntimeError:
        logger.warning(
            "web_session: payload signing unavailable (check SERVER_SALT / explicit secret)",
            exc_info=True,
        )
        return None
    if not hmac.compare_digest(expected_sig, signature):
        return None

    try:
        payload_obj = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if not isinstance(payload_obj, dict):
        return None

    legacy_plain_api_key = payload_obj.get("api_key")
    tier = payload_obj.get("tier")
    issued_at = payload_obj.get("iat")
    expires_at = payload_obj.get("exp")
    version = payload_obj.get("v")

    if not isinstance(tier, str):
        return None
    # RU: bool — подкласс int; отвергаем явным сравнением типа.
    # EN: bool subclasses int; reject with exact-type checks (JWT claim hygiene).
    if type(issued_at) is not int or type(expires_at) is not int:
        return None
    if version != 1:
        return None

    # If encrypted claim key is present on the wire (even null/empty), never fall back to legacy
    # plaintext — prevents downgrade when both fields appear.
    enc_api_key_present = "enc_api_key" in payload_obj  # pragma: allowlist secret
    encrypted_api_key = payload_obj.get("enc_api_key")

    resolved_api_key: str | None = None
    if enc_api_key_present:
        if not isinstance(encrypted_api_key, str) or not encrypted_api_key.strip():
            return None
        resolved_api_key = _decrypt_api_key(encrypted_api_key.strip(), secret=secret)
        if resolved_api_key is None:
            return None
    elif isinstance(legacy_plain_api_key, str) and legacy_plain_api_key.strip():
        # RU: Совместимость со старыми cookie до выката шифрования (plaintext api_key).
        # EN: Backward compatibility for pre-encryption cookies (plaintext api_key claim).
        resolved_api_key = legacy_plain_api_key.strip()
    else:
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
    # Reject if iat is in the future vs verifier clock (beyond allowed skew).
    if issued_at > now_epoch + _SESSION_IAT_CLOCK_SKEW_SECONDS:
        return None

    return WebSessionClaims(
        api_key=resolved_api_key,
        tier=normalized_tier,
        issued_at_epoch=issued_at,
        expires_at_epoch=expires_at,
    )


def _is_secure_cookie_environment() -> bool:
    """Return Secure-cookie mode (fail-closed by default)."""

    if is_production_like_env():
        return True
    return not is_raw_explicit_developer_env()


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
