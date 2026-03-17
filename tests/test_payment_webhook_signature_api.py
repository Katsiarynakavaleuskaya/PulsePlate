# -*- coding: utf-8 -*-
"""Contract tests for payment webhook signature validation.

RU: Контрактные тесты для валидации подписи webhook перед state transition.
EN: Contract tests for webhook signature validation before state transition.

Contract: Any webhook/event handler must validate signature before state transition
(evidence: docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:84).

This file documents the B1 baseline contract for future webhook handlers.
Full behavioral verification of provider webhooks (Apple, Stripe, etc.) is deferred to B2.
"""

from __future__ import annotations

import hmac
import hashlib

import pytest

from app.http_error_details import BILLING_SIGNATURE_INVALID
from app.schemas.payments import PaymentErrorResponse
from app.services import payments_activation


def test_validate_webhook_signature_rejects_empty_signature() -> None:
    """Invalid signature (empty) must be rejected before state transition."""
    secret = "test-webhook-secret"  # pragma: allowlist secret
    payload = b'{"event":"payment.completed","id":"evt-1"}'
    assert payments_activation.validate_webhook_signature(secret, payload, "") is False
    assert payments_activation.validate_webhook_signature(secret, payload, "   ") is False


def test_validate_webhook_signature_rejects_empty_secret() -> None:
    """Empty secret must fail closed."""
    payload = b'{"event":"payment.completed"}'
    sig = hmac.new(b"any-secret", payload, hashlib.sha256).hexdigest()  # pragma: allowlist secret
    assert payments_activation.validate_webhook_signature("", payload, sig) is False


def _signature(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def test_validate_webhook_signature_accepts_valid_uppercase_hex() -> None:
    """Uppercase hex signature must be accepted (case-insensitive at hex layer)."""
    secret = "topsecret"  # pragma: allowlist secret
    payload = b'{"event":"paid"}'
    signature = _signature(secret, payload).upper()
    assert payments_activation.validate_webhook_signature(secret, payload, signature) is True


def test_validate_webhook_signature_rejects_signature_with_whitespace() -> None:
    """Signature with leading/trailing whitespace must be rejected."""
    secret = "topsecret"  # pragma: allowlist secret
    payload = b'{"event":"paid"}'
    signature = f" {_signature(secret, payload)} "
    assert payments_activation.validate_webhook_signature(secret, payload, signature) is False


def test_validate_webhook_signature_rejects_non_ascii_signature() -> None:
    """Non-ASCII signature must fail closed, not raise."""
    secret = "topsecret"  # pragma: allowlist secret
    payload = b'{"event":"paid"}'
    assert payments_activation.validate_webhook_signature(secret, payload, "неascii") is False


def test_validate_webhook_signature_rejects_non_hex_signature() -> None:
    """Invalid hex characters in signature must fail closed."""
    secret = "topsecret"  # pragma: allowlist secret
    payload = b'{"event":"paid"}'
    assert payments_activation.validate_webhook_signature(secret, payload, "z" * 64) is False


def test_validate_webhook_signature_uses_raw_body_bytes_exactly() -> None:
    """Signature must be over exact raw HTTP body bytes, not re-serialized JSON."""
    secret = "topsecret"  # pragma: allowlist secret
    raw_body = b'{"b":2,"a":1}'
    reserialized_body = b'{"a":1,"b":2}'
    signature = _signature(secret, raw_body)
    assert payments_activation.validate_webhook_signature(secret, raw_body, signature) is True
    assert (
        payments_activation.validate_webhook_signature(secret, reserialized_body, signature)
        is False
    )


def test_validate_webhook_signature_rejects_invalid_signature() -> None:
    """Wrong or tampered signature must be rejected."""
    secret = "test-webhook-secret"  # pragma: allowlist secret
    payload = b'{"event":"payment.completed","id":"evt-1"}'
    wrong_sig = "a" * 64  # valid hex length but wrong value
    assert payments_activation.validate_webhook_signature(secret, payload, wrong_sig) is False


def test_validate_webhook_signature_accepts_valid_signature() -> None:
    """Valid HMAC-SHA256 signature must be accepted."""
    secret = "test-webhook-secret"  # pragma: allowlist secret
    payload = b'{"event":"payment.completed","id":"evt-1"}'
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    assert payments_activation.validate_webhook_signature(secret, payload, expected) is True


def test_validate_webhook_signature_payload_sensitive() -> None:
    """Signature must be payload-specific; tampered payload must fail."""
    secret = "test-webhook-secret"  # pragma: allowlist secret
    payload = b'{"event":"payment.completed"}'
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    tampered = b'{"event":"payment.completed","tampered":true}'
    assert payments_activation.validate_webhook_signature(secret, tampered, sig) is False


def test_payment_error_response_supports_billing_signature_invalid() -> None:
    """PaymentErrorResponse contract must support BILLING_SIGNATURE_INVALID code."""
    err = PaymentErrorResponse(
        code=BILLING_SIGNATURE_INVALID,
        message="Webhook signature validation failed",
        detail="Invalid or missing signature",
    )
    assert err.code == "BILLING_SIGNATURE_INVALID"
    assert err.status == "error"
    dumped = err.model_dump(mode="json")
    assert dumped["code"] == "BILLING_SIGNATURE_INVALID"
