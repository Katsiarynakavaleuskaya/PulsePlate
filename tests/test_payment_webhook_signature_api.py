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
    assert payments_activation.validate_webhook_signature("   ", payload, sig) is False


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
