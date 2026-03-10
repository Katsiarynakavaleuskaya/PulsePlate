from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient
import pytest

from tests.payment_test_utils import json_response_payload as _json

pytestmark = pytest.mark.usefixtures("reset_payments_state")


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
            "currency": "BYN",
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
                "currency": "BYN",
            }
        )
    )
    activation, _ = payments_activation.activate_subscription(
        issuer=issuer,
        payload=activation_request,
    )
    return activation.activation_id


def _create_ios_activation_via_service(*, issuer: str) -> str:
    from app.schemas.payments import ActivateSubscriptionRequest
    from app.services import payments_activation

    activation, _ = payments_activation.activate_subscription(
        issuer=issuer,
        payload=ActivateSubscriptionRequest.model_validate(
            {
                "source": "ios_app_store",
                "plan": "pro_monthly",
                "client_event_id": "evt-ios-service-intent-1",
                "verification_ok": True,
                "verification_payload": {"receipt": "receipt-token-validated-99999"},
            }
        ),
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
    assert payload["intent_id"] == intent_id

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


def test_manual_reconcile_rejects_second_transition_after_verification(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="erip_qr")
    verified = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-erip-reconcile-final-1",
            "decision": "verified",
            "external_txn_id": "erip-final-ok-1",
        },
    )
    assert verified.status_code == 200, verified.text

    rejected = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-erip-reconcile-final-2",
            "decision": "rejected",
            "external_txn_id": "erip-final-no-1",
        },
    )
    assert rejected.status_code == 422
    payload = _json(rejected)
    assert payload["code"] == "invalid_reconcile_state"
    assert payload["detail"] == "manual_reconcile_transition_requires_pending_state"


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


def test_manual_reconcile_vip_key_can_manage_own_intent(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, vip_headers, source="swift_manual")

    reconcile = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=vip_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-vip-reconcile-1",
            "decision": "verified",
            "external_txn_id": "swift-vip-1",
        },
    )
    assert reconcile.status_code == 200, reconcile.text
    assert _json(reconcile)["status"] == "active"

    status_response = client.get(
        f"/api/v1/pro/payments/ru-by/reconcile/{intent_id}",
        headers=vip_headers,
    )
    assert status_response.status_code == 200, status_response.text
    assert _json(status_response)["external_txn_id"] == "swift-vip-1"


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


def test_manual_reconcile_status_missing_intent_returns_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/pro/payments/ru-by/reconcile/missing-intent",
        headers=pro_headers,
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


def test_manual_reconcile_rejects_ios_activation_via_service() -> None:
    from app.schemas.payments import ManualRailReconcileRequest
    from app.services import payments_activation

    issuer = payments_activation.issuer_from_api_key("test_pro_key")
    activation_id = _create_ios_activation_via_service(issuer=issuer)

    with pytest.raises(payments_activation.ActivationStateError, match="cannot be reconciled"):
        payments_activation.reconcile_activation(
            issuer=issuer,
            payload=ManualRailReconcileRequest.model_validate(
                {
                    "intent_id": activation_id,
                    "client_event_id": "evt-ios-reconcile-1",
                    "decision": "verified",
                }
            ),
        )


def test_manual_reconcile_rejects_ios_activation_via_api(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    from app.services import payments_activation

    activation_id = _create_ios_activation_via_service(
        issuer=payments_activation.issuer_from_api_key(pro_headers["X-API-Key"])
    )

    response = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": activation_id,
            "client_event_id": "evt-ios-api-reconcile-1",
            "decision": "verified",
        },
    )
    assert response.status_code == 422
    assert _json(response)["code"] == "invalid_reconcile_state"


def test_manual_status_rejects_ios_activation_via_api(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    from app.services import payments_activation

    activation_id = _create_ios_activation_via_service(
        issuer=payments_activation.issuer_from_api_key(pro_headers["X-API-Key"])
    )

    response = client.get(
        f"/api/v1/pro/payments/ru-by/reconcile/{activation_id}",
        headers=pro_headers,
    )
    assert response.status_code == 422
    payload = _json(response)
    assert payload["code"] == "invalid_reconcile_state"
    assert payload["detail"] == "manual_status_not_supported_for_ios"


def test_manual_reconcile_rejects_unsupported_state_via_service() -> None:
    from app.schemas.payments import ManualRailReconcileRequest
    from app.services import payments_activation

    issuer = payments_activation.issuer_from_api_key("test_pro_key")
    activation_id = _create_manual_intent_via_service(issuer=issuer, source="erip_qr")
    payments_activation._ACTIVATIONS[activation_id]["reconcile_status"] = "unsupported_state"

    with pytest.raises(
        payments_activation.ActivationStateError,
        match="manual reconcile transition requires pending state",
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


def test_manual_reconcile_rejects_unsupported_state_via_api(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    intent_id = _create_manual_intent(client, pro_headers, source="erip_qr")

    from app.services import payments_activation

    payments_activation._ACTIVATIONS[intent_id]["reconcile_status"] = "unsupported_state"

    response = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-unsupported-api-reconcile-1",
            "decision": "verified",
        },
    )
    assert response.status_code == 422
    assert _json(response)["code"] == "invalid_reconcile_state"
    assert _json(response)["detail"] == "manual_reconcile_transition_requires_pending_state"


def test_activation_state_detail_maps_manual_status_and_unknown_errors() -> None:
    from app.routers import billing
    from app.services import payments_activation

    manual_status_error = payments_activation.ActivationStateError(
        "manual reconciliation status is unavailable for ios_app_store"
    )
    assert (
        billing._activation_state_detail(manual_status_error)
        == "manual_status_not_supported_for_ios"
    )

    unknown_error = payments_activation.ActivationStateError("unexpected-payment-state")
    assert billing._activation_state_detail(unknown_error) == "invalid_reconcile_state"


def test_plan_to_tier_rejects_unknown_plan_value() -> None:
    from app.schemas.payments import SubscriptionPlan
    from app.services import payments_activation

    with pytest.raises(ValueError, match="unsupported subscription plan"):
        payments_activation._plan_to_tier(cast(SubscriptionPlan, "enterprise"))
