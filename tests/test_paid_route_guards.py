from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP, derive_subject_id_from_api_key
from app.models import Subscription
from app.schemas.payments import SubscriptionStatus
from app.services import payments_activation
from core import db as core_db
from core.billing_policy import LEGACY_MANUAL_COMPAT_CUTOFF


def _apple_response_for_receipt(receipt_data: str) -> dict[str, Any]:
    """Map test receipt_data to Apple verify response for server-side reverification.

    Uses allowlisted product IDs: com.pulseplate.premium.monthly (pro),
    com.pulseplate.vip.monthly (vip).
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    expires_future_ms = str(now_ms + 30 * 24 * 3600 * 1000)
    expires_past_ms = "1706745600000"  # 2024-02-01 UTC
    pro_active = {
        "status": 0,
        "latest_receipt_info": [
            {
                "product_id": "com.pulseplate.premium.monthly",
                "expires_date_ms": expires_future_ms,
                "transaction_id": "txn-pro",
                "original_transaction_id": "orig-txn-pro",
            }
        ],
    }
    vip_active = {
        "status": 0,
        "latest_receipt_info": [
            {
                "product_id": "com.pulseplate.vip.monthly",
                "expires_date_ms": expires_future_ms,
                "transaction_id": "txn-vip",
                "original_transaction_id": "orig-txn-vip",
            }
        ],
    }
    vip_expired = {
        "status": 0,
        "latest_receipt_info": [
            {
                "product_id": "com.pulseplate.vip.monthly",
                "expires_date_ms": expires_past_ms,
                "transaction_id": "txn-expired",
                "original_transaction_id": "orig-txn-expired",
            }
        ],
    }
    mapping: dict[str, dict[str, Any]] = {
        "receipt-txn-pro-active": pro_active,
        "receipt-txn-vip-active": vip_active,
        "receipt-txn-expired": vip_expired,
        "receipt-txn-cancelled": vip_active,
        "receipt-txn-carveout": pro_active,
        "receipt-txn-alias-pro": pro_active,
    }
    return mapping.get(receipt_data, pro_active)


@pytest.fixture(autouse=True)
def _mock_apple_verify_for_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Apple verify so activation tests can run without real Apple API."""

    async def _fake_call(url: str, receipt_data: str) -> dict[str, Any]:
        del url
        return _apple_response_for_receipt(receipt_data)

    monkeypatch.setattr(
        payments_activation,
        "_call_apple_verify_endpoint",
        _fake_call,
    )


@pytest.fixture(autouse=True)
def _db_backed_paid_authz(
    monkeypatch: pytest.MonkeyPatch,
    configure_sqlite_database: object,
) -> None:
    """Force canonical paid routes onto persisted backend entitlement truth."""

    payments_activation.reset_state()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("PRO_API_KEYS", TEST_KEY_PRO)  # pragma: allowlist secret
    monkeypatch.setenv("VIP_API_KEYS", TEST_KEY_VIP)  # pragma: allowlist secret


def _json(response: Any) -> dict[str, Any]:
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    payload: dict[str, Any] = response.json()
    return payload


def _ios_payload(*, tier: str, status: str, transaction_id: str) -> dict[str, Any]:
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    )
    if status == "expired":
        expires_at = (
            (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
        )
    return {
        "source": "ios_app_store",
        "payload": {
            "verification_result": {
                "transaction_id": transaction_id,
                "original_transaction_id": f"orig-{transaction_id}",
                "product_id": f"com.pulseplate.{tier}.monthly",
                "subscription_tier": tier,
                "status": status,
                "expires_at": expires_at,
                "platform": "ios",
            },
            "receipt_data": f"receipt-{transaction_id}",
        },
    }


def _manual_payload(*, source: str, source_reference: str) -> dict[str, Any]:
    return {
        "source": source,
        "payload": {
            "source_reference": source_reference,
            "submitted_amount": "9.99",
            "submitted_currency": "BYN",
        },
    }


def _load_subscription(*, api_key: str, source: str) -> Subscription:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        statement = select(Subscription).where(
            Subscription.user_id == derive_subject_id_from_api_key(api_key),
            Subscription.source == source,
        )
        subscription = session.execute(statement).scalar_one()
        session.expunge(subscription)
        return subscription
    finally:
        session.close()


def _set_subscription_status(*, api_key: str, source: str, status: str) -> None:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        statement = select(Subscription).where(
            Subscription.user_id == derive_subject_id_from_api_key(api_key),
            Subscription.source == source,
        )
        subscription = session.execute(statement).scalar_one()
        subscription.status = status
        session.commit()
    finally:
        session.close()


def _persist_subscription(
    *,
    api_key: str,
    source: str,
    tier: str,
    status: str,
    expires_at: datetime | None,
    activated_at: datetime | None | object = ...,
    created_at: datetime | None = None,
) -> None:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    persisted_activated_at = (
        (datetime.now(timezone.utc) if status == "active" else None)
        if activated_at is ...
        else activated_at
    )
    try:
        session.add(
            Subscription(
                id=str(uuid4()),
                user_id=derive_subject_id_from_api_key(api_key),
                source=source,
                tier=tier,
                status=status,
                platform="web",
                source_reference=f"{source}:{api_key}",
                product_id=f"com.pulseplate.{tier}.monthly",
                expires_at=expires_at,
                activated_at=persisted_activated_at,
                created_at=created_at or datetime.now(timezone.utc),
                updated_at=created_at or datetime.now(timezone.utc),
            )
        )
        session.commit()
    finally:
        session.close()


def test_pro_header_without_persisted_entitlement_is_denied(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Client-declared PRO key must not unlock canonical PRO routes without backend truth."""

    response = client.get("/api/v1/pro/session", headers=pro_headers)
    assert response.status_code == 403, response.text


def test_vip_header_without_persisted_entitlement_is_denied(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Client-declared VIP key must not unlock canonical VIP routes without backend truth."""

    response = client.get("/api/v1/vip/health", headers=vip_headers)
    assert response.status_code == 403, response.text


def test_activation_unlocks_pro_route_but_not_vip(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Active PRO entitlement must unlock canonical PRO and still deny canonical VIP."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(tier="pro", status="active", transaction_id="txn-pro-active"),
    )
    assert activate.status_code == 200, activate.text

    pro_response = client.get("/api/v1/pro/session", headers=pro_headers)
    assert pro_response.status_code == 200, pro_response.text
    assert _json(pro_response)["tier"] == "PRO"

    vip_response = client.get("/api/v1/vip/health", headers=pro_headers)
    assert vip_response.status_code == 403, vip_response.text


def test_activation_unlocks_vip_and_pro_routes(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Active VIP entitlement must unlock canonical VIP and inherited PRO surfaces."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=vip_headers,
        json=_ios_payload(tier="vip", status="active", transaction_id="txn-vip-active"),
    )
    assert activate.status_code == 200, activate.text

    pro_response = client.get("/api/v1/pro/session", headers=vip_headers)
    assert pro_response.status_code == 200, pro_response.text
    assert _json(pro_response)["tier"] == "VIP"

    vip_response = client.get("/api/v1/vip/health", headers=vip_headers)
    assert vip_response.status_code == 200, vip_response.text
    assert _json(vip_response)["status"] == "success"


def test_expired_entitlement_does_not_unlock_paid_routes(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Expired persisted entitlements must deny both canonical paid surfaces."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=vip_headers,
        json=_ios_payload(tier="vip", status="expired", transaction_id="txn-expired"),
    )
    assert activate.status_code == 403, activate.text

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 403


def test_pending_manual_review_does_not_unlock_paid_routes(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Manual-rail pending review must not unlock canonical paid routes."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_manual_payload(source="erip_qr", source_reference="erip-order-001"),
    )
    assert activate.status_code == 200, activate.text

    payload = _json(activate)
    assert payload["status"] == "pending_manual_review"

    assert client.get("/api/v1/pro/session", headers=pro_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=pro_headers).status_code == 403


def test_manual_ru_by_entry_routes_remain_callable_before_entitlement(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Manual RU/BY entry routes stay transport-auth accessible before entitlement exists."""

    create_intent = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "evt-transport-auth-1",
            "external_txn_id": "erip-transport-auth-1",
            "amount_minor": 1999,
            "currency": "BYN",
        },
    )
    assert create_intent.status_code == 201, create_intent.text
    intent_id = _json(create_intent)["intent_id"]

    status_response = client.get(
        f"/api/v1/pro/payments/ru-by/reconcile/{intent_id}",
        headers=pro_headers,
    )
    assert status_response.status_code == 200, status_response.text
    assert _json(status_response)["reconcile_status"] == "pending"

    assert client.get("/api/v1/pro/session", headers=pro_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=pro_headers).status_code == 403


def test_verified_manual_vip_unlocks_pro_and_vip_routes(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Verified bounded manual VIP entitlement must unlock both paid surfaces."""

    create_intent = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=vip_headers,
        json={
            "source": "swift_manual",
            "plan": "vip_monthly",
            "client_event_id": "evt-manual-vip-intent-1",
            "external_txn_id": "swift-manual-vip-1",
            "amount_minor": 2999,
            "currency": "BYN",
        },
    )
    assert create_intent.status_code == 201, create_intent.text
    intent_id = _json(create_intent)["intent_id"]

    reconcile = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=vip_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-manual-vip-reconcile-1",
            "decision": "verified",
            "external_txn_id": "swift-manual-vip-settled-1",
        },
    )
    assert reconcile.status_code == 200, reconcile.text
    reconcile_payload = _json(reconcile)
    assert reconcile_payload["status"] == "active"
    assert reconcile_payload["subscription_tier"] == "vip"
    assert reconcile_payload["expires_at"] is not None

    subscription = _load_subscription(api_key=TEST_KEY_VIP, source="swift_manual")
    assert subscription.status == SubscriptionStatus.active.value
    assert subscription.expires_at is not None

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 200
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 200


def test_verified_manual_pro_unlocks_only_pro_route(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Verified manual PRO entitlement must not unlock VIP-only routes."""

    create_intent = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "evt-manual-pro-intent-1",
            "external_txn_id": "erip-manual-pro-1",
            "amount_minor": 1999,
            "currency": "BYN",
        },
    )
    assert create_intent.status_code == 201, create_intent.text
    intent_id = _json(create_intent)["intent_id"]

    reconcile = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-manual-pro-reconcile-1",
            "decision": "verified",
            "external_txn_id": "erip-manual-pro-settled-1",
        },
    )
    assert reconcile.status_code == 200, reconcile.text
    reconcile_payload = _json(reconcile)
    assert reconcile_payload["subscription_tier"] == "pro"
    assert reconcile_payload["expires_at"] is not None

    assert client.get("/api/v1/pro/session", headers=pro_headers).status_code == 200
    assert client.get("/api/v1/vip/health", headers=pro_headers).status_code == 403


def test_rejected_manual_reconcile_keeps_paid_routes_denied(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Rejected manual reconciliation must not unlock canonical paid routes."""

    create_intent = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "evt-manual-rejected-intent-1",
            "external_txn_id": "erip-manual-rejected-1",
            "amount_minor": 1999,
            "currency": "BYN",
        },
    )
    assert create_intent.status_code == 201, create_intent.text
    intent_id = _json(create_intent)["intent_id"]

    reconcile = client.post(
        "/api/v1/pro/payments/ru-by/reconcile",
        headers=pro_headers,
        json={
            "intent_id": intent_id,
            "client_event_id": "evt-manual-rejected-reconcile-1",
            "decision": "rejected",
            "external_txn_id": "erip-manual-rejected-final-1",
        },
    )
    assert reconcile.status_code == 200, reconcile.text
    reconcile_payload = _json(reconcile)
    assert reconcile_payload["status"] == "rejected"
    assert reconcile_payload["expires_at"] is None

    assert client.get("/api/v1/pro/session", headers=pro_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=pro_headers).status_code == 403


def test_active_paid_manual_row_without_expiry_fails_closed(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Broken manual paid rows without expiry must fail closed."""

    _persist_subscription(
        api_key=TEST_KEY_VIP,
        source="swift_manual",
        tier="vip",
        status="active",
        expires_at=None,
        activated_at=None,
    )

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 403


def test_legacy_manual_row_without_expiry_uses_compat_activation_window(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Legacy manual paid rows should retain bounded access from activated_at."""

    _persist_subscription(
        api_key=TEST_KEY_VIP,
        source="swift_manual",
        tier="vip",
        status="active",
        expires_at=None,
        created_at=LEGACY_MANUAL_COMPAT_CUTOFF - timedelta(days=1),
    )

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 200
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 200


def test_post_cutoff_manual_row_without_expiry_fails_closed(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Post-rollout malformed manual rows must not receive compat authz access."""

    _persist_subscription(
        api_key=TEST_KEY_VIP,
        source="swift_manual",
        tier="vip",
        status="active",
        expires_at=None,
        activated_at=LEGACY_MANUAL_COMPAT_CUTOFF + timedelta(hours=1),
        created_at=LEGACY_MANUAL_COMPAT_CUTOFF + timedelta(hours=1),
    )

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 403


def test_cancelled_entitlement_does_not_unlock_paid_routes(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Cancelled persisted subscriptions must deny canonical PRO and VIP routes."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=vip_headers,
        json=_ios_payload(tier="vip", status="active", transaction_id="txn-cancelled"),
    )
    assert activate.status_code == 200, activate.text

    subscription = _load_subscription(api_key=TEST_KEY_VIP, source="ios_app_store")
    assert subscription.status == SubscriptionStatus.active.value
    _set_subscription_status(
        api_key=TEST_KEY_VIP,
        source="ios_app_store",
        status=SubscriptionStatus.cancelled.value,
    )

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 403


def test_billing_entry_route_stays_outside_paid_entitlement_gate(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Activation route must remain callable before any paid entitlement exists."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(tier="pro", status="active", transaction_id="txn-carveout"),
    )
    assert activate.status_code == 200, activate.text
    assert _json(activate)["status"] == "active"


def test_deprecated_pro_alias_does_not_bypass_missing_entitlement(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Deprecated PRO alias must not bypass canonical paid authz outcome."""

    response = client.post("/api/v1/premium/plan/week-flexible", headers=pro_headers, json={})
    assert response.status_code == 403, response.text


def test_deprecated_vip_alias_does_not_bypass_pro_only_entitlement(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """VIP alias must still deny a user who only has active PRO entitlement."""

    activate = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(tier="pro", status="active", transaction_id="txn-alias-pro"),
    )
    assert activate.status_code == 200, activate.text

    response = client.post("/api/v1/vip/weekly-plan", headers=pro_headers, json={})
    assert response.status_code == 403, response.text
