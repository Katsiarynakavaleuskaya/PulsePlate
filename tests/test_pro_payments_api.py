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


def _activation_payload(
    *,
    source: str = "ios_app_store",
    client_event_id: str = "evt-activation-001",
    verification_ok: bool | None = True,
    external_txn_id: str | None = "txn-001",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": source,
        "client_event_id": client_event_id,
        "verification_payload": {"raw": "opaque"},
    }
    if verification_ok is not None:
        payload["verification_ok"] = verification_ok
    if external_txn_id is not None:
        payload["external_txn_id"] = external_txn_id
    return payload


def test_activate_subscription_requires_pro_tier(client: TestClient) -> None:
    response = client.post("/api/v1/pro/payments/activate", json=_activation_payload())
    assert response.status_code in {401, 403}


def test_activate_subscription_ios_verified_returns_201(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(source="ios_app_store", verification_ok=True),
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["payment_source"] == "ios_app_store"
    assert payload["status"] == "active"
    assert payload["reconcile_status"] == "verified"
    assert payload["verified_at"] is not None


def test_activate_subscription_ios_rejected_returns_201(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(
            source="ios_app_store",
            client_event_id="evt-ios-rejected-1",
            verification_ok=False,
        ),
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["status"] == "rejected"
    assert payload["reconcile_status"] == "rejected"
    assert payload["verified_at"] is not None


def test_activate_subscription_ios_without_verification_is_pending(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(
            source="ios_app_store",
            client_event_id="evt-ios-pending-1",
            verification_ok=None,
            external_txn_id=None,
        ),
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["status"] == "pending_verification"
    assert payload["reconcile_status"] == "pending"
    assert payload["external_txn_id"] is None
    assert payload["verified_at"] is None


def test_activate_subscription_defaults_verification_payload_when_omitted(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json={
            "source": "ios_app_store",
            "client_event_id": "evt-ios-no-payload-1",
            "verification_ok": True,
            "external_txn_id": "txn-no-payload-1",
        },
    )
    assert response.status_code == 201, response.text
    payload = _json(response)
    assert payload["status"] == "active"
    assert payload["reconcile_status"] == "verified"


def test_activate_subscription_manual_rails_start_pending(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    for source in ("erip_qr", "swift_manual"):
        response = client.post(
            "/api/v1/pro/payments/activate",
            headers=pro_headers,
            json=_activation_payload(
                source=source,
                client_event_id=f"evt-{source}",
                verification_ok=None,
                external_txn_id=f"ext-{source}",
            ),
        )
        assert response.status_code == 201, response.text
        payload = _json(response)
        assert payload["payment_source"] == source
        assert payload["status"] == "pending_verification"
        assert payload["reconcile_status"] == "pending"
        assert payload["verified_at"] is None


def test_activate_subscription_idempotent_replay_returns_200(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    body = _activation_payload(
        source="ios_app_store",
        client_event_id="evt-replay-1",
        verification_ok=True,
        external_txn_id="txn-replay",
    )
    first = client.post("/api/v1/pro/payments/activate", headers=pro_headers, json=body)
    second = client.post("/api/v1/pro/payments/activate", headers=pro_headers, json=body)
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    first_payload = _json(first)
    second_payload = _json(second)
    assert first_payload["activation_id"] == second_payload["activation_id"]
    assert first_payload == second_payload


def test_activate_subscription_idempotency_conflict_returns_409(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    first = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(
            source="ios_app_store",
            client_event_id="evt-conflict-1",
            verification_ok=True,
            external_txn_id="txn-conflict-1",
        ),
    )
    conflict = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(
            source="ios_app_store",
            client_event_id="evt-conflict-1",
            verification_ok=False,
            external_txn_id="txn-conflict-2",
        ),
    )
    assert first.status_code == 201, first.text
    assert conflict.status_code == 409, conflict.text
    conflict_payload = _json(conflict)
    assert conflict_payload["status"] == "error"
    assert conflict_payload["code"] == "idempotency_conflict"
    assert "client_event_id conflict" in conflict_payload["detail"]


def test_activate_subscription_invalid_source_returns_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(source="unknown_source"),
    )
    assert response.status_code == 422


def test_activate_subscription_blank_client_event_id_returns_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(client_event_id="   "),
    )
    assert response.status_code == 422


def test_issuer_helper_supports_empty_api_key() -> None:
    from app.routers.pro_payments import _issuer_from_api_key

    assert _issuer_from_api_key("") == "api_key:anonymous"


def test_issuer_helper_returns_stable_marker_for_same_api_key() -> None:
    from app.routers.pro_payments import _issuer_from_api_key

    first = _issuer_from_api_key("pro-key-issuer-stable")
    second = _issuer_from_api_key("pro-key-issuer-stable")
    assert first == second


def test_issuer_helper_returns_distinct_markers_for_different_api_keys() -> None:
    from app.routers.pro_payments import _issuer_from_api_key

    first = _issuer_from_api_key("pro-key-issuer-a")
    second = _issuer_from_api_key("pro-key-issuer-b")
    assert first != second


def test_get_activation_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(client_event_id="evt-get-1"),
    )
    assert created.status_code == 201, created.text
    activation_id = _json(created)["activation_id"]

    fetched = client.get(
        f"/api/v1/pro/payments/activations/{activation_id}",
        headers=pro_headers,
    )
    assert fetched.status_code == 200, fetched.text
    fetched_payload = _json(fetched)
    assert fetched_payload["activation_id"] == activation_id
    assert fetched_payload["payment_source"] == "ios_app_store"


def test_get_activation_forbidden_for_other_issuer(
    client: TestClient,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_activation_payload(client_event_id="evt-forbidden-1"),
    )
    assert created.status_code == 201, created.text
    activation_id = _json(created)["activation_id"]

    fetched = client.get(
        f"/api/v1/pro/payments/activations/{activation_id}",
        headers=vip_headers,
    )
    assert fetched.status_code == 403
    payload = _json(fetched)
    assert payload["status"] == "error"
    assert payload["code"] == "forbidden"


def test_get_activation_not_found_returns_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/pro/payments/activations/missing-activation",
        headers=pro_headers,
    )
    assert response.status_code == 404
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "not_found"


def test_payments_activation_reset_state_clears_process_local_records() -> None:
    from app.schemas.payments import ActivateSubscriptionRequest
    from app.services import payments_activation

    payload = ActivateSubscriptionRequest.model_validate(_activation_payload())
    activation, created = payments_activation.activate_subscription(
        issuer="api_key:test-process-local",
        payload=payload,
    )

    assert created is True
    assert (
        payments_activation.get_activation(
            activation.activation_id,
            issuer="api_key:test-process-local",
        )
        is not None
    )

    payments_activation.reset_state()

    assert (
        payments_activation.get_activation(
            activation.activation_id,
            issuer="api_key:test-process-local",
        )
        is None
    )
