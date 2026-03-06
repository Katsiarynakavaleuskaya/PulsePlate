from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest


@pytest.fixture(autouse=True)
def _reset_payments_state() -> None:
    from app.services import payments_activation

    payments_activation.reset_state()


def _json(response: Any) -> dict[str, Any]:
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    payload: dict[str, Any] = response.json()
    return payload


def test_apple_verify_receipt_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/apple/verify-receipt",
        headers=pro_headers,
        json={
            "plan": "vip_monthly",
            "client_event_id": "evt-ios-billing-1",
            "receipt": "receipt-token-validated-12345",
            "external_txn_id": "ios-txn-1",
        },
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["payment_source"] == "ios_app_store"
    assert payload["plan"] == "vip_monthly"
    assert payload["subscription_tier"] == "vip"
    assert payload["status"] == "active"
    assert payload["reconcile_status"] == "verified"
    assert payload["audit_id"] == payload["activation_id"]


def test_apple_verify_receipt_short_receipt_rejects(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/apple/verify-receipt",
        headers=pro_headers,
        json={
            "plan": "pro_monthly",
            "client_event_id": "evt-ios-billing-2",
            "receipt": "shortbad",
        },
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["status"] == "rejected"
    assert payload["reconcile_status"] == "rejected"
    assert payload["subscription_tier"] == "pro"


def test_apple_verify_receipt_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/api/v1/pro/payments/apple/verify-receipt",
        json={
            "plan": "pro_monthly",
            "client_event_id": "evt-ios-billing-3",
            "receipt": "receipt-token-validated-12345",
        },
    )
    assert response.status_code == 401


def test_manual_intent_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "evt-erip-intent-1",
            "external_txn_id": "erip-intent-1",
            "amount_minor": 1999,
            "currency": "byn",
            "verification_payload": {"comment": "invoice-1"},
        },
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["payment_source"] == "erip_qr"
    assert payload["status"] == "pending_verification"
    assert payload["reconcile_status"] == "pending"
    assert payload["subscription_tier"] == "pro"


def test_manual_intent_rejects_ios_source(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "ios_app_store",
            "plan": "pro_monthly",
            "client_event_id": "evt-manual-invalid-1",
            "amount_minor": 999,
            "currency": "USD",
        },
    )
    assert response.status_code == 422


def test_payment_request_models_cover_normalization_error_branches() -> None:
    from app.schemas.payments import (
        AppleReceiptVerificationRequest,
        ManualRailIntentRequest,
        ManualRailReconcileRequest,
    )

    valid_apple = AppleReceiptVerificationRequest.model_validate(
        {
            "plan": "pro_monthly",
            "client_event_id": "evt-apple-validate-1",
            "receipt": "receipt-token-validated-12345",
        }
    )
    assert valid_apple.external_txn_id is None

    with pytest.raises(ValidationError):
        AppleReceiptVerificationRequest.model_validate(
            {
                "plan": "pro_monthly",
                "client_event_id": "evt-apple-validate-2",
                "receipt": "        ",
            }
        )

    valid_manual_intent = ManualRailIntentRequest.model_validate(
        {
            "source": "erip_qr",
            "plan": "vip_monthly",
            "client_event_id": "evt-manual-validate-1",
            "amount_minor": 2000,
            "currency": "usd",
        }
    )
    assert valid_manual_intent.currency == "USD"
    assert valid_manual_intent.external_txn_id is None

    with pytest.raises(ValidationError):
        ManualRailIntentRequest.model_validate(
            {
                "source": "swift_manual",
                "plan": "pro_monthly",
                "client_event_id": "evt-manual-validate-2",
                "amount_minor": 1000,
                "currency": "   ",
            }
        )

    valid_reconcile = ManualRailReconcileRequest.model_validate(
        {
            "intent_id": "intent-validate-1",
            "client_event_id": "evt-reconcile-validate-1",
            "decision": "verified",
        }
    )
    assert valid_reconcile.external_txn_id is None

    with pytest.raises(ValidationError):
        ManualRailReconcileRequest.model_validate(
            {
                "intent_id": "   ",
                "client_event_id": "evt-reconcile-validate-2",
                "decision": "verified",
            }
        )
