"""Unit tests for web session cookie security helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi import Response

from app.security import web_session

TEST_PRO_KEY = "test_pro_key"  # pragma: allowlist secret
# Must satisfy core/server_salt.py strength rules (length + character classes).
TEST_SERVER_SALT = "StrongSessionSaltForTests123456789!"  # pragma: allowlist secret


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(encoded: str) -> bytes:
    pad_len = (-len(encoded)) % 4
    return base64.urlsafe_b64decode(encoded + ("=" * pad_len))


def _derived_key(server_salt: str) -> bytes:
    return hashlib.blake2s(f"web_session_v1::{server_salt}".encode("utf-8")).digest()


def _sign_payload(payload_b64: str, *, server_salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        payload_b64.encode("ascii"),
        _derived_key(server_salt),
        web_session._SESSION_SIGNATURE_ITERATIONS,
        dklen=32,
    ).hex()


def test_require_web_session_ttl_seconds_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset TTL should use safe default."""

    monkeypatch.delenv(web_session.WEB_SESSION_TTL_ENV, raising=False)
    assert (
        web_session.require_web_session_ttl_seconds() == web_session.DEFAULT_WEB_SESSION_TTL_SECONDS
    )


def test_require_web_session_ttl_seconds_valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """TTL env should be parsed when valid."""

    monkeypatch.setenv(web_session.WEB_SESSION_TTL_ENV, "123")
    assert web_session.require_web_session_ttl_seconds() == 123


def test_require_web_session_ttl_seconds_rejects_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid TTL env should fail closed."""

    monkeypatch.setenv(web_session.WEB_SESSION_TTL_ENV, "abc")
    with pytest.raises(RuntimeError):
        web_session.require_web_session_ttl_seconds()

    monkeypatch.setenv(web_session.WEB_SESSION_TTL_ENV, "0")
    with pytest.raises(RuntimeError):
        web_session.require_web_session_ttl_seconds()


def test_issue_and_verify_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Issued token should verify and keep core claims."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    issued = web_session.issue_web_session(
        api_key=TEST_PRO_KEY,
        tier="PRO",
        now=now,
        ttl_seconds=120,
    )
    claims = web_session.verify_web_session(issued.token, now=now + timedelta(seconds=60))

    assert claims is not None
    assert claims.api_key == TEST_PRO_KEY
    assert claims.tier == "PRO"
    assert claims.issued_at_epoch == int(now.timestamp())
    assert claims.expires_at_epoch == int((now + timedelta(seconds=120)).timestamp())


def test_verify_legacy_plaintext_api_key_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-encryption cookies with plaintext api_key must verify until TTL expires."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = issued_at + 300
    payload = {
        "api_key": TEST_PRO_KEY,
        "tier": "PRO",
        "iat": issued_at,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    token = f"{payload_b64}.{sig}"

    claims = web_session.verify_web_session(token, now=now + timedelta(seconds=10))
    assert claims is not None
    assert claims.api_key == TEST_PRO_KEY
    assert claims.tier == "PRO"


def test_verify_prefers_encrypted_claim_when_both_enc_and_legacy_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If both enc_api_key and legacy api_key exist, decrypted enc wins (no downgrade)."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 2, tzinfo=timezone.utc)
    issued = web_session.issue_web_session(
        api_key=TEST_PRO_KEY,
        tier="PRO",
        now=now,
        ttl_seconds=400,
    )
    payload_b64, sig = issued.token.split(".", 1)
    payload_obj = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    payload_obj["api_key"] = "attacker_override_value"  # pragma: allowlist secret
    payload_bytes = json.dumps(
        payload_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    tampered_b64 = _b64url_encode(payload_bytes)
    tampered_sig = _sign_payload(tampered_b64, server_salt=TEST_SERVER_SALT)
    claims = web_session.verify_web_session(
        f"{tampered_b64}.{tampered_sig}",
        now=now + timedelta(seconds=10),
    )
    assert claims is not None
    assert claims.api_key == TEST_PRO_KEY


def test_verify_rejects_invalid_enc_without_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid enc_api_key must fail closed even if legacy api_key is present."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 3, tzinfo=timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = issued_at + 200
    payload = {
        "enc_api_key": "not-valid-fernet-ciphertext",  # pragma: allowlist secret
        "api_key": TEST_PRO_KEY,
        "tier": "PRO",
        "iat": issued_at,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_rejects_empty_enc_api_key_without_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty enc_api_key claim must not fall back to legacy plaintext api_key."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 4, tzinfo=timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = issued_at + 200
    payload = {
        "enc_api_key": "",
        "api_key": TEST_PRO_KEY,
        "tier": "PRO",
        "iat": issued_at,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_rejects_future_iat_beyond_skew(monkeypatch: pytest.MonkeyPatch) -> None:
    """Token with iat far in the future must fail closed (not-before)."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    now_epoch = int(now.timestamp())
    issued_at = now_epoch + 500
    expires_at = issued_at + 400
    payload = {
        "api_key": TEST_PRO_KEY,
        "tier": "PRO",
        "iat": issued_at,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_returns_none_when_server_salt_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing SERVER_SALT during verify must return None, not raise."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    issued = web_session.issue_web_session(
        api_key=TEST_PRO_KEY,
        tier="PRO",
        now=now,
        ttl_seconds=120,
    )
    monkeypatch.delenv("SERVER_SALT", raising=False)
    assert web_session.verify_web_session(issued.token, now=now + timedelta(seconds=10)) is None


def test_token_payload_does_not_expose_raw_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Token payload must not include plaintext API key claim."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    issued = web_session.issue_web_session(api_key=TEST_PRO_KEY, tier="PRO", ttl_seconds=120)
    payload_b64, _sig = issued.token.split(".", 1)
    payload_obj = json.loads(_b64url_decode(payload_b64).decode("utf-8"))

    assert "api_key" not in payload_obj
    assert payload_obj["enc_api_key"] != TEST_PRO_KEY


def test_issue_rejects_invalid_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Issue path must fail closed for malformed inputs."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)

    with pytest.raises(ValueError):
        web_session.issue_web_session(api_key="", tier="PRO")
    with pytest.raises(ValueError):
        web_session.issue_web_session(api_key="k", tier="FREE")
    with pytest.raises(ValueError):
        web_session.issue_web_session(api_key="k", tier="PRO", ttl_seconds=0)


def test_issue_rejects_empty_explicit_secret() -> None:
    """Explicit empty secret is forbidden."""

    with pytest.raises(RuntimeError):
        web_session.issue_web_session(api_key="k", tier="PRO", secret="   ")


def test_issue_and_verify_with_explicit_secret() -> None:
    """Explicit secret path should work without relying on SERVER_SALT env."""

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = web_session.issue_web_session(
        api_key=TEST_PRO_KEY,
        tier="PRO",
        now=now,
        ttl_seconds=120,
        secret="explicit-session-secret",  # pragma: allowlist secret
    )
    claims = web_session.verify_web_session(
        issued.token,
        now=now + timedelta(seconds=30),
        secret="explicit-session-secret",  # pragma: allowlist secret
    )
    assert claims is not None
    assert claims.api_key == TEST_PRO_KEY
    assert claims.tier == "PRO"


def test_verify_rejects_malformed_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed token formats should return None."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    assert web_session.verify_web_session("") is None
    assert web_session.verify_web_session("abc") is None
    assert web_session.verify_web_session("a.b.c") is None
    assert web_session.verify_web_session("a.") is None
    assert web_session.verify_web_session(".b") is None


def test_verify_logs_when_signing_unavailable_without_server_salt(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Missing SERVER_SALT during signature verify must log a warning (operator signal)."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    issued = web_session.issue_web_session(api_key=TEST_PRO_KEY, tier="PRO", ttl_seconds=120)
    monkeypatch.delenv("SERVER_SALT", raising=False)
    with caplog.at_level(logging.WARNING, logger="app.security.web_session"):
        assert web_session.verify_web_session(issued.token) is None
    assert any("payload signing unavailable" in r.message for r in caplog.records)


def test_verify_rejects_invalid_base64_payload_with_valid_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signed token with undecodable payload must fail closed."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    payload = "@@@"
    sig = _sign_payload(payload, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload}.{sig}") is None


def test_verify_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tampered signature must fail verification."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    issued = web_session.issue_web_session(api_key="k", tier="PRO", ttl_seconds=100)
    payload, _sig = issued.token.split(".", 1)
    assert web_session.verify_web_session(f"{payload}.deadbeef") is None


def test_verify_rejects_wrong_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported version must be rejected."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    issued = web_session.issue_web_session(api_key="k", tier="PRO", ttl_seconds=100)
    payload, _sig = issued.token.split(".", 1)
    payload_raw = _b64url_decode(payload)
    tampered = payload_raw.replace(b'"v":1', b'"v":2')
    tampered_payload = _b64url_encode(tampered)
    tampered_sig = _sign_payload(
        tampered_payload,
        server_salt=TEST_SERVER_SALT,
    )
    bad_token = f"{tampered_payload}.{tampered_sig}"
    assert web_session.verify_web_session(bad_token) is None


def test_verify_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired token should be rejected deterministically."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = web_session.issue_web_session(
        api_key="k",
        tier="PRO",
        now=now,
        ttl_seconds=10,
    )
    assert web_session.verify_web_session(issued.token, now=now + timedelta(seconds=11)) is None


def test_verify_rejects_payload_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verification should reject non-object payload and invalid claims."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now_epoch = int(datetime.now(tz=timezone.utc).timestamp())
    expires_epoch = now_epoch + 100

    bad_payloads = [
        b"[]",
        b'{"enc_api_key":"","tier":"PRO","iat":1,"exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":"UNKNOWN","iat":1,"exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":123,"iat":1,"exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":"PRO","iat":"1","exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":"PRO","iat":1,"exp":"2","v":1}',
        b'{"enc_api_key":"k","tier":"PRO","iat":-1,"exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":"PRO","iat":2,"exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":"PRO","iat":true,"exp":2,"v":1}',
        b'{"enc_api_key":"k","tier":"PRO","iat":1,"exp":false,"v":1}',
        (
            f'{{"enc_api_key":"k","tier":"PRO","iat":{now_epoch},"exp":{expires_epoch},"v":"1"}}'.encode(
                "utf-8"
            )
        ),
    ]
    for payload_raw in bad_payloads:
        payload = _b64url_encode(payload_raw)
        sig = _sign_payload(payload, server_salt=TEST_SERVER_SALT)
        assert web_session.verify_web_session(f"{payload}.{sig}") is None


def test_cookie_helpers_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local mode should set hardened cookie without Secure flag."""

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv(web_session.WEB_SESSION_TTL_ENV, "90")
    response = Response()

    web_session.set_web_session_cookie(response=response, token="abc")
    header = response.headers.get("set-cookie", "")
    assert f"{web_session.WEB_SESSION_COOKIE_NAME}=abc" in header
    assert "HttpOnly" in header
    assert "Path=/" in header
    assert "samesite=lax" in header.lower()
    assert "max-age=90" in header.lower()
    assert "secure" not in header.lower()


def test_cookie_helpers_prod_and_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prod mode should set Secure and clear should expire cookie."""

    monkeypatch.setenv("APP_ENV", "production")
    response = Response()

    web_session.set_web_session_cookie(response=response, token="abc", ttl_seconds=30)
    set_headers = [
        value.decode("latin-1").lower()
        for key, value in response.raw_headers
        if key.lower() == b"set-cookie"
    ]
    assert any("secure" in header for header in set_headers)
    assert any("max-age=30" in header for header in set_headers)

    web_session.clear_web_session_cookie(response=response)
    clear_headers = [
        value.decode("latin-1").lower()
        for key, value in response.raw_headers
        if key.lower() == b"set-cookie"
    ]
    assert any(f"{web_session.WEB_SESSION_COOKIE_NAME}=" in header for header in clear_headers)
    assert any("max-age=0" in header for header in clear_headers)


def test_decrypt_api_key_returns_none_on_fernet_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ValueError from Fernet.decrypt must map to None (fail-closed)."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    with patch.object(Fernet, "decrypt", side_effect=ValueError("invalid token")):
        assert web_session._decrypt_api_key("not-used", secret=None) is None


def test_decrypt_api_key_returns_none_on_non_utf8_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decrypted bytes that are not valid UTF-8 must return None."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    with patch.object(Fernet, "decrypt", return_value=b"\xff\xfe"):
        assert web_session._decrypt_api_key("not-used", secret=None) is None


def test_verify_rejects_enc_api_key_json_null(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON null enc_api_key must fail closed (enc key present but unusable)."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 10, tzinfo=timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = issued_at + 300
    payload = {
        "enc_api_key": None,
        "tier": "PRO",
        "iat": issued_at,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_rejects_when_no_api_or_enc_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """Payload without api_key or enc_api_key must be rejected."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 11, tzinfo=timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = issued_at + 300
    payload = {
        "tier": "PRO",
        "iat": issued_at,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_rejects_negative_issued_at(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative iat must fail validation."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 12, tzinfo=timezone.utc)
    expires_at = int(now.timestamp()) + 400
    payload = {
        "api_key": TEST_PRO_KEY,
        "tier": "PRO",
        "iat": -5,
        "exp": expires_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_rejects_expires_not_after_issued(monkeypatch: pytest.MonkeyPatch) -> None:
    """exp must be strictly greater than iat."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)
    issued_at = int(now.timestamp())
    payload = {
        "api_key": TEST_PRO_KEY,
        "tier": "PRO",
        "iat": issued_at,
        "exp": issued_at,
        "v": 1,
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = _sign_payload(payload_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{payload_b64}.{sig}", now=now) is None


def test_verify_rejects_invalid_tier_on_encrypted_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tampered tier after signature recompute must fail tier normalization."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 14, tzinfo=timezone.utc)
    issued = web_session.issue_web_session(
        api_key=TEST_PRO_KEY,
        tier="PRO",
        now=now,
        ttl_seconds=400,
    )
    payload_b64, _sig = issued.token.split(".", 1)
    obj = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    obj["tier"] = "INVALID"
    payload_bytes = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    tampered_b64 = _b64url_encode(payload_bytes)
    tampered_sig = _sign_payload(tampered_b64, server_salt=TEST_SERVER_SALT)
    assert (
        web_session.verify_web_session(
            f"{tampered_b64}.{tampered_sig}",
            now=now + timedelta(seconds=10),
        )
        is None
    )


def test_verify_rejects_future_iat_encrypted_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Encrypted payload with iat beyond clock skew must fail (not-before)."""

    monkeypatch.setenv("SERVER_SALT", TEST_SERVER_SALT)
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    now_epoch = int(now.timestamp())
    issued = web_session.issue_web_session(
        api_key=TEST_PRO_KEY,
        tier="PRO",
        now=now,
        ttl_seconds=800,
    )
    payload_b64, _sig = issued.token.split(".", 1)
    obj = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    obj["iat"] = now_epoch + 500
    obj["exp"] = obj["iat"] + 400
    payload_bytes = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    tampered_b64 = _b64url_encode(payload_bytes)
    tampered_sig = _sign_payload(tampered_b64, server_salt=TEST_SERVER_SALT)
    assert web_session.verify_web_session(f"{tampered_b64}.{tampered_sig}", now=now) is None
