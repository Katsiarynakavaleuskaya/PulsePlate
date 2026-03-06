from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest


@pytest.fixture(autouse=True)
def _reset_payments_state() -> None:
    from app.services import payments_activation

    payments_activation.reset_state()


def _json(response: Any) -> dict[str, Any]:
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    payload: dict[str, Any] = response.json()
    return payload


def _create_manual_intent(client: TestClient, headers: dict[str, str], *, source: str) -> str:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=headers,
        json={
            "source": source,
            "plan": "vip_monthly",
            "client_event_id": f"evt-{source}-intent-1",
            "external_txn_id": f"{source}-intent-1",
            "amount_minor": 2999,
            "currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    return _json(response)["activation_id"]


def _create_manual_intent_via_service(*, issuer: str, source: str) -> str:
    from app.schemas.payments import ManualRailIntentRequest
    from app.services import payments_activation

    activation_request = payments_activation.build_manual_intent_request(
        payload=ManualRailIntentRequest.model_validate(
            {
                "source": source,
                "plan": "vip_monthly",
                "client_event_id": f"evt-{source}-service-intent-1",
                "external_txn_id": f"{source}-service-intent-1",
                "amount_minor": 2999,
                "currency": "USD",
            }
        )
    )
    activation, _ = payments_activation.activate_subscription(
        issuer=issuer,
        payload=activation_request,
    )
    return activation.activation_id


def test_manual_reconcile_verified_flow(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="swift_manual")

    reconcile = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-swift-reconcile-1",
            "decision": "verified",
            "external_txn_id": "swift-settled-1",
        },
    )
    assert reconcile.status_code == 200, reconcile.text
    payload = _json(reconcile)
    assert payload["status"] == "active"
    assert payload["reconcile_status"] == "verified"
    assert payload["subscription_tier"] == "vip"
    assert payload["external_txn_id"] == "swift-settled-1"

    status_response = client.get(
        f"/api/v1/pro/payments/ru-by/reconcile/{intent_id}",
        headers=pro_headers,
    )
    assert status_response.status_code == 200, status_response.text
    assert _json(status_response)["status"] == "active"


def test_manual_reconcile_is_idempotent(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="erip_qr")
    payload = {
        "intent_id": intent_id,
        "client_event_id": "evt-erip-reconcile-1",
        "decision": "rejected",
        "external_txn_id": "erip-final-1",
    }
    first = client.post("/api/v1/pro/payments/ru-by/reconcile", headers=pro_headers, json=payload)
    second = client.post("/api/v1/pro/payments/ru-by/reconcile", headers=pro_headers, json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert _json(first) == _json(second)


def test_manual_reconcile_conflict_returns_409(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="erip_qr")
    first = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-erip-reconcile-2",
            "decision": "verified",
            "external_txn_id": "erip-settled-2",
        },
    )
    conflict = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-erip-reconcile-2",
            "decision": "rejected",
            "external_txn_id": "erip-other-2",
        },
    )
    assert first.status_code == 200, first.text
    assert conflict.status_code == 409, conflict.text
    payload = _json(conflict)
    assert payload["code"] == "idempotency_conflict"


def test_manual_reconcile_forbidden_for_other_issuer(
    client: TestClient,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="swift_manual")
    response = client.get(
        f"/api/v1/pro/payments/ru-by/reconcile/{intent_id}",
        headers=vip_headers,
    )
    assert response.status_code == 403
    assert _json(response)["code"] == "forbidden"


def test_manual_reconcile_missing_intent_returns_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": "missing-intent",
            "client_event_id": "evt-missing-1",
            "decision": "verified",
        },
    )
    assert response.status_code == 404
    assert _json(response)["code"] == "not_found"


def test_manual_reconcile_forbidden_for_other_issuer_on_post(
    client: TestClient,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="erip_qr")
    response = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=vip_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-foreign-reconcile-1",
            "decision": "verified",
        },
    )
    assert response.status_code == 403
    assert _json(response)["code"] == "forbidden"


def test_manual_reconcile_rejects_ios_activation_via_service() -> None:
    from app.schemas.payments import (
        AppleReceiptVerificationRequest,
        ManualRailReconcileRequest,
    )
    from app.services import payments_activation

    issuer = payments_activation.issuer_from_api_key("test_pro_key")
    activation_request = payments_activation.build_ios_activation_request(
        payload=AppleReceiptVerificationRequest.model_validate(
            {
                "plan": "pro_monthly",
                "client_event_id": "evt-ios-service-1",
                "receipt": "receipt-token-validated-99999",
            }
        )
    )
    activation, _ = payments_activation.activate_subscription(
        issuer=issuer,
        payload=activation_request,
    )

    with pytest.raises(payments_activation.ActivationStateError, match="cannot be reconciled"):
        payments_activation.reconcile_activation(
            issuer=issuer,
            payload=ManualRailReconcileRequest.model_validate(
                {
                    "intent_id": activation.activation_id,
                    "client_event_id": "evt-ios-reconcile-1",
                    "decision": "verified",
                }
            ),
        )


def test_manual_reconcile_rejects_unsupported_state_via_service() -> None:
    from app.schemas.payments import ManualRailReconcileRequest
    from app.services import payments_activation

    issuer = payments_activation.issuer_from_api_key("test_pro_key")
    activation_id = _create_manual_intent_via_service(issuer=issuer, source="erip_qr")
    payments_activation._ACTIVATIONS[activation_id]["reconcile_status"] = "unsupported_state"

    with pytest.raises(
        payments_activation.ActivationStateError, match="unsupported reconcile state"
    ):
        payments_activation.reconcile_activation(
            issuer=issuer,
            payload=ManualRailReconcileRequest.model_validate(
                {
                    "intent_id": activation_id,
                    "client_event_id": "evt-unsupported-reconcile-1",
                    "decision": "verified",
                }
            ),
        )
