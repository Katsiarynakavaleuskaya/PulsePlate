from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from tests.payment_test_utils import json_response_payload as _json

pytestmark = pytest.mark.usefixtures("reset_payments_state")


def test_manual_billing_transport_key_rejects_invalid_key_when_subscription_db_mode_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import billing

    def _reject_transport_key(_: str) -> str:
        raise HTTPException(status_code=401, detail="transport key rejected")

    monkeypatch.setattr(billing, "_get_app_get_api_key", lambda: _reject_transport_key)
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")

    with pytest.raises(
        HTTPException, match="API key required for billing verification"
    ) as exc_info:
        billing._require_manual_billing_transport_key("pro-key")

    assert exc_info.value.status_code == 401


def test_manual_billing_transport_key_rejects_request_when_subscription_db_mode_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import billing

    def _reject_transport_key(_: str) -> str:
        raise HTTPException(status_code=401, detail="transport key rejected")

    monkeypatch.setattr(billing, "_get_app_get_api_key", lambda: _reject_transport_key)
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(
        HTTPException, match="API key required for billing verification"
    ) as exc_info:
        billing._require_manual_billing_transport_key("free-key")

    assert exc_info.value.status_code == 401


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
    assert payload["intent_id"] == payload["activation_id"]


def test_manual_intent_vip_headers_are_tier_compatible(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=vip_headers,
        json={
            "source": "swift_manual",
            "plan": "vip_monthly",
            "client_event_id": "evt-swift-intent-vip-1",
            "external_txn_id": "swift-intent-vip-1",
            "amount_minor": 2999,
            "currency": "rub",
            "verification_payload": {"comment": "invoice-vip-1"},
        },
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["payment_source"] == "swift_manual"
    assert payload["status"] == "pending_verification"
    assert payload["reconcile_status"] == "pending"
    assert payload["subscription_tier"] == "vip"
    assert payload["intent_id"] == payload["activation_id"]


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
            "currency": "BYN",
        },
    )
    assert response.status_code == 422


def test_manual_intent_openapi_contract_is_manual_only() -> None:
    from app.main import app as canonical_app

    components = canonical_app.openapi()["components"]["schemas"]
    manual_schema = components["ManualRailIntentRequest"]
    assert (
        manual_schema["properties"]["source"]["$ref"] == "#/components/schemas/ManualPaymentSource"
    )
    assert manual_schema["properties"]["currency"]["$ref"] == "#/components/schemas/RuByCurrency"


def test_payment_request_models_cover_normalization_error_branches() -> None:
    from app.schemas.payments import (
        ActivateSubscriptionRequest,
        AppleReceiptVerificationRequest,
        ManualRailIntentRequest,
        ManualRailReconcileRequest,
        RuByCurrency,
    )

    valid_apple = AppleReceiptVerificationRequest.model_validate(
        {
            "receipt_data": "receipt-token-validated-12345",
        }
    )
    assert valid_apple.receipt_data == "receipt-token-validated-12345"

    with pytest.raises(ValidationError):
        AppleReceiptVerificationRequest.model_validate(
            {
                "receipt_data": "        ",
            }
        )

    valid_manual_intent = ManualRailIntentRequest.model_validate(
        {
            "source": "erip_qr",
            "plan": "vip_monthly",
            "client_event_id": "evt-manual-validate-1",
            "amount_minor": 2000,
            "currency": "rub",
            "external_txn_id": None,
        }
    )
    assert valid_manual_intent.currency is RuByCurrency.rub
    assert valid_manual_intent.external_txn_id is None

    normalized_manual_intent = ManualRailIntentRequest.model_validate(
        {
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "  evt-manual-before-1  ",
            "amount_minor": 1500,
            "currency": " byn ",
        }
    )
    assert normalized_manual_intent.client_event_id == "evt-manual-before-1"
    assert normalized_manual_intent.currency is RuByCurrency.byn

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
            "external_txn_id": None,
        }
    )
    assert valid_reconcile.external_txn_id is None

    normalized_reconcile = ManualRailReconcileRequest.model_validate(
        {
            "intent_id": "  intent-validate-2  ",
            "client_event_id": "  evt-reconcile-validate-3  ",
            "decision": "verified",
        }
    )
    assert normalized_reconcile.intent_id == "intent-validate-2"
    assert normalized_reconcile.client_event_id == "evt-reconcile-validate-3"

    with pytest.raises(ValidationError):
        ManualRailReconcileRequest.model_validate(
            {
                "intent_id": "   ",
                "client_event_id": "evt-reconcile-validate-2",
                "decision": "verified",
            }
        )

    with pytest.raises(ValidationError):
        ActivateSubscriptionRequest.model_validate(
            {
                "source": "ios_app_store",
                "plan": "pro_monthly",
                "client_event_id": 123456,
            }
        )

    with pytest.raises(ValidationError):
        ActivateSubscriptionRequest.model_validate(
            {
                "source": "ios_app_store",
                "client_event_id": "evt-activation-missing-plan-1",
            }
        )

    with pytest.raises(ValidationError):
        ActivateSubscriptionRequest.model_validate(
            {
                "source": "ios_app_store",
                "plan": "pro_monthly",
                "client_event_id": "evt-activation-extra-1",
                "unexpected": "value",
            }
        )

    with pytest.raises(ValidationError):
        ActivateSubscriptionRequest.model_validate(
            {
                "source": "ios_app_store",
                "plan": "pro_monthly",
                "client_event_id": "evt-activation-typed-1",
                "external_txn_id": 42,
            }
        )

    with pytest.raises(ValidationError):
        AppleReceiptVerificationRequest.model_validate(
            {
                "receipt_data": 123456,
            }
        )

    with pytest.raises(ValidationError):
        AppleReceiptVerificationRequest.model_validate(
            {
                "receipt_data": "receipt-token-validated-typed-54321",
                "external_txn_id": 99,
            }
        )

    with pytest.raises(ValidationError):
        AppleReceiptVerificationRequest.model_validate(
            {
                "receipt_data": "receipt-token-validated-typed-77777",
                "reason_key": "unexpected",
            }
        )

    with pytest.raises(ValidationError):
        ManualRailIntentRequest.model_validate(
            {
                "source": "erip_qr",
                "plan": "pro_monthly",
                "client_event_id": "evt-manual-typed-1",
                "amount_minor": 1000,
                "currency": 840,
            }
        )

    with pytest.raises(ValidationError):
        ManualRailIntentRequest.model_validate(
            {
                "source": "swift_manual",
                "plan": "pro_monthly",
                "client_event_id": "evt-manual-typed-2",
                "amount_minor": 1000,
                "currency": "BYN",
                "external_txn_id": 7,
            }
        )

    with pytest.raises(ValidationError):
        ManualRailIntentRequest.model_validate(
            {
                "source": "erip_qr",
                "plan": "pro_monthly",
                "client_event_id": "evt-manual-currency-1",
                "amount_minor": 1000,
                "currency": "USD",
            }
        )

    with pytest.raises(ValidationError):
        ManualRailIntentRequest.model_validate(
            {
                "source": "erip_qr",
                "plan": "pro_monthly",
                "client_event_id": "evt-manual-extra-1",
                "amount_minor": 1000,
                "currency": "BYN",
                "unexpected": "value",
            }
        )

    with pytest.raises(ValidationError):
        ManualRailReconcileRequest.model_validate(
            {
                "intent_id": 1001,
                "client_event_id": "evt-reconcile-typed-1",
                "decision": "verified",
            }
        )

    with pytest.raises(ValidationError):
        ManualRailReconcileRequest.model_validate(
            {
                "intent_id": "intent-typed-2",
                "client_event_id": "evt-reconcile-typed-2",
                "decision": "verified",
                "external_txn_id": 17,
            }
        )

    with pytest.raises(ValidationError):
        ManualRailReconcileRequest.model_validate(
            {
                "intent_id": "intent-extra-1",
                "client_event_id": "evt-reconcile-extra-1",
                "decision": "verified",
                "extra_flag": True,
            }
        )


def test_manual_intent_idempotent_replay_returns_200(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    payload = {
        "source": "swift_manual",
        "plan": "vip_monthly",
        "client_event_id": "evt-manual-replay-1",
        "external_txn_id": "swift-replay-1",
        "amount_minor": 2999,
        "currency": "BYN",
    }
    first = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json=payload,
    )
    second = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json=payload,
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert _json(first) == _json(second)


def test_manual_intent_conflict_returns_409(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    first = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "plan": "vip_monthly",
            "client_event_id": "evt-manual-conflict-1",
            "amount_minor": 2999,
            "currency": "BYN",
            "external_txn_id": "erip-conflict-1",
        },
    )
    conflict = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "plan": "vip_monthly",
            "client_event_id": "evt-manual-conflict-1",
            "amount_minor": 3999,
            "currency": "BYN",
            "external_txn_id": "erip-conflict-2",
        },
    )
    assert first.status_code == 201, first.text
    assert conflict.status_code == 409, conflict.text
    assert _json(conflict)["code"] == "idempotency_conflict"
