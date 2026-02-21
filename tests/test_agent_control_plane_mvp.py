"""Deterministic tests for Agent Control Plane MVP security primitives."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.security import agent_control_plane as cp


def test_parse_allowlist_supports_commas_and_newlines() -> None:
    raw = "tool.exec:https://api.example.com,\nagent.plan:internal://planner, malformed"
    parsed = cp.parse_allowlist(raw)
    assert ("tool.exec", "https://api.example.com") in parsed
    assert ("agent.plan", "internal://planner") in parsed
    assert len(parsed) == 2


def test_parse_allowlist_skips_empty_action_or_target() -> None:
    raw = ":https://api.example.com,tool.exec:,tool.exec:https://api.example.com"
    assert cp.parse_allowlist(raw) == {("tool.exec", "https://api.example.com")}


def test_load_allowlist_from_env_parses_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cp.ALLOWLIST_ENV, "tool.exec:https://api.example.com")
    assert cp.load_allowlist_from_env() == {("tool.exec", "https://api.example.com")}


def test_to_utc_treats_naive_datetime_as_utc() -> None:
    normalized = cp._to_utc(datetime(2026, 2, 21, 12, 34, 56))
    assert normalized.tzinfo == timezone.utc
    assert normalized.isoformat() == "2026-02-21T12:34:56+00:00"


def test_evaluate_policy_is_deny_by_default() -> None:
    decision = cp.evaluate_policy(
        "tool.exec",
        "https://not-allowlisted.example.com",
        allowlist={("tool.exec", "https://api.example.com")},
    )
    assert decision.allowed is False
    assert decision.reason == "deny_by_default"


def test_evaluate_policy_rejects_invalid_action_or_target() -> None:
    decision = cp.evaluate_policy(" ", "  ")
    assert decision.allowed is False
    assert decision.reason == "invalid_action_or_target"


def test_require_policy_allow_returns_allowed_decision() -> None:
    decision = cp.require_policy_allow(
        "tool.exec",
        "https://api.example.com",
        allowlist={("tool.exec", "https://api.example.com")},
    )
    assert decision.allowed is True
    assert decision.reason == "allowlist_match"


def test_require_policy_allow_raises_for_denied() -> None:
    with pytest.raises(PermissionError, match="Policy denied"):
        cp.require_policy_allow(
            "tool.exec",
            "https://denied.example.com",
            allowlist={("tool.exec", "https://api.example.com")},
        )


def test_require_audit_secret_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(cp.AUDIT_SIGNING_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=cp.AUDIT_SIGNING_KEY_ENV):
        cp.require_audit_secret()


def test_sign_and_verify_audit_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cp.AUDIT_SIGNING_KEY_ENV, "audit-key")
    decision = cp.PolicyDecision(
        action="tool.exec",
        target="https://api.example.com",
        allowed=True,
        reason="allowlist_match",
    )
    ts = datetime(2026, 2, 21, 12, 0, tzinfo=timezone.utc)
    envelope = cp.sign_audit_envelope(
        decision,
        metadata={"path": "/api/v1/insight", "method": "POST"},
        timestamp=ts,
    )

    assert envelope.action == "tool.exec"
    assert envelope.allowed is True
    assert envelope.timestamp_utc == "2026-02-21T12:00:00+00:00"
    assert cp.verify_audit_envelope(envelope) is True


def test_verify_audit_envelope_fails_on_tamper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cp.AUDIT_SIGNING_KEY_ENV, "audit-key")
    decision = cp.PolicyDecision(
        action="tool.exec",
        target="https://api.example.com",
        allowed=True,
        reason="allowlist_match",
    )
    envelope = cp.sign_audit_envelope(decision)
    tampered = replace(envelope, target="https://tampered.example.com")
    assert cp.verify_audit_envelope(tampered) is False


def test_require_scoped_token_ttl_seconds_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(cp.SCOPED_TTL_ENV, raising=False)
    assert cp.require_scoped_token_ttl_seconds() == cp.DEFAULT_SCOPED_TOKEN_TTL_SECONDS


def test_require_scoped_token_ttl_seconds_raises_on_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(cp.SCOPED_TTL_ENV, "0")
    with pytest.raises(RuntimeError, match=cp.SCOPED_TTL_ENV):
        cp.require_scoped_token_ttl_seconds()


def test_require_scoped_token_ttl_seconds_raises_on_non_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(cp.SCOPED_TTL_ENV, "not-an-int")
    with pytest.raises(RuntimeError, match=cp.SCOPED_TTL_ENV):
        cp.require_scoped_token_ttl_seconds()


def test_require_scoped_token_ttl_seconds_accepts_positive_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(cp.SCOPED_TTL_ENV, "120")
    assert cp.require_scoped_token_ttl_seconds() == 120


def test_require_secrets_hmac_key_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cp.BROKER_HMAC_KEY_ENV, "broker-key")
    assert cp.require_secrets_hmac_key() == "broker-key"


def test_issue_scoped_token_requires_hmac_key_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(cp.BROKER_HMAC_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=cp.BROKER_HMAC_KEY_ENV):
        cp.issue_scoped_token("agent.exec")


def test_issue_scoped_token_is_deterministic_with_fixed_inputs() -> None:
    now = datetime(2026, 2, 21, 15, 30, tzinfo=timezone.utc)
    first = cp.issue_scoped_token(
        "agent.exec",
        ttl_seconds=60,
        now=now,
        hmac_key="broker-key",
    )
    second = cp.issue_scoped_token(
        "agent.exec",
        ttl_seconds=60,
        now=now,
        hmac_key="broker-key",
    )
    assert first == second
    assert first.expires_at_utc == "2026-02-21T15:31:00+00:00"


def test_issue_scoped_token_rejects_empty_scope() -> None:
    with pytest.raises(ValueError, match="scope must be non-empty"):
        cp.issue_scoped_token(" ", hmac_key="broker-key")


def test_issue_scoped_token_rejects_non_positive_ttl() -> None:
    with pytest.raises(ValueError, match="ttl_seconds must be >= 1"):
        cp.issue_scoped_token("agent.exec", ttl_seconds=0, hmac_key="broker-key")


def test_issue_scoped_token_rejects_empty_string_hmac_key() -> None:
    """Fail-closed: explicitly passing empty-string hmac_key must raise."""
    with pytest.raises(RuntimeError, match="non-empty"):
        cp.issue_scoped_token("agent.exec", ttl_seconds=60, hmac_key="")


def test_sign_audit_envelope_rejects_empty_string_secret() -> None:
    """Fail-closed: explicitly passing empty-string secret must raise."""
    decision = cp.PolicyDecision(action="agent.exec", target="*", allowed=True, reason="test")
    with pytest.raises(RuntimeError, match="non-empty"):
        cp.sign_audit_envelope(decision, secret="")


def test_verify_audit_envelope_rejects_empty_string_secret() -> None:
    """Fail-closed: explicitly passing empty-string secret must raise."""
    decision = cp.PolicyDecision(action="agent.exec", target="*", allowed=True, reason="test")
    envelope = cp.sign_audit_envelope(decision, secret="test-secret")
    with pytest.raises(RuntimeError, match="non-empty"):
        cp.verify_audit_envelope(envelope, secret="")
