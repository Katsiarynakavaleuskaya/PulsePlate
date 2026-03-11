"""Unit tests for web session cookie security helpers."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Response

from app.security import web_session

TEST_PRO_KEY = "test_pro_key"  # pragma: allowlist secret


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

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
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


def test_issue_rejects_invalid_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Issue path must fail closed for malformed inputs."""

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")

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

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
    assert web_session.verify_web_session("") is None
    assert web_session.verify_web_session("abc") is None
    assert web_session.verify_web_session("a.b.c") is None
    assert web_session.verify_web_session("a.") is None
    assert web_session.verify_web_session(".b") is None


def test_verify_rejects_invalid_base64_payload_with_valid_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signed token with undecodable payload must fail closed."""

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
    payload = "@@@"
    sig = _sign_payload(payload, server_salt="StrongSessionSaltForTests123456789!")
    assert web_session.verify_web_session(f"{payload}.{sig}") is None


def test_verify_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tampered signature must fail verification."""

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
    issued = web_session.issue_web_session(api_key="k", tier="PRO", ttl_seconds=100)
    payload, _sig = issued.token.split(".", 1)
    assert web_session.verify_web_session(f"{payload}.deadbeef") is None


def test_verify_rejects_wrong_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported version must be rejected."""

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
    issued = web_session.issue_web_session(api_key="k", tier="PRO", ttl_seconds=100)
    payload, _sig = issued.token.split(".", 1)
    payload_raw = _b64url_decode(payload)
    tampered = payload_raw.replace(b'"v":1', b'"v":2')
    tampered_payload = _b64url_encode(tampered)
    tampered_sig = _sign_payload(
        tampered_payload,
        server_salt="StrongSessionSaltForTests123456789!",
    )
    bad_token = f"{tampered_payload}.{tampered_sig}"
    assert web_session.verify_web_session(bad_token) is None


def test_verify_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired token should be rejected deterministically."""

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
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

    monkeypatch.setenv("SERVER_SALT", "StrongSessionSaltForTests123456789!")
    now_epoch = int(datetime.now(tz=timezone.utc).timestamp())
    expires_epoch = now_epoch + 100

    bad_payloads = [
        b"[]",
        b'{"api_key":"","tier":"PRO","iat":1,"exp":2,"v":1}',
        b'{"api_key":"k","tier":"UNKNOWN","iat":1,"exp":2,"v":1}',
        b'{"api_key":"k","tier":123,"iat":1,"exp":2,"v":1}',
        b'{"api_key":"k","tier":"PRO","iat":"1","exp":2,"v":1}',
        b'{"api_key":"k","tier":"PRO","iat":1,"exp":"2","v":1}',
        b'{"api_key":"k","tier":"PRO","iat":-1,"exp":2,"v":1}',
        b'{"api_key":"k","tier":"PRO","iat":2,"exp":2,"v":1}',
        (
            f'{{"api_key":"k","tier":"PRO","iat":{now_epoch},"exp":{expires_epoch},"v":"1"}}'.encode(
                "utf-8"
            )
        ),
    ]
    for payload_raw in bad_payloads:
        payload = _b64url_encode(payload_raw)
        sig = _sign_payload(payload, server_salt="StrongSessionSaltForTests123456789!")
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
