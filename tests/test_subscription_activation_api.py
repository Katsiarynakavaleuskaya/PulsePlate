from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.http_error_details import (
    ACTIVATION_ACCESS_FORBIDDEN_DETAIL,
    DETERMINISTIC_ACTIVATION_CONFLICT_DETAIL,
    TRANSPORT_AUTH_REQUIRED_DETAIL,
)
from app.models import Subscription, SubscriptionActivationAudit
from app.schemas.payments import (
    ActivateSubscriptionRequest,
    IOSAppStoreActivationPayload,
    IOSVerifiedActivationResult,
    ManualActivationPayload,
    PaymentSource,
    ReconcileStatus,
    SubscriptionActivationResponse,
    SubscriptionStatus,
    SubscriptionTier,
)
from app.services import payments_activation
from core import db as core_db


@pytest.fixture(autouse=True)
def _reset_payments_state() -> None:
    from app.services import payments_activation

    payments_activation.reset_state()


def _apple_response_for_receipt(receipt_data: str) -> dict[str, Any]:
    """Map test receipt_data to Apple verify response for server-side reverification."""
    # Far-future active expiries keep fixtures deterministic and avoid time-based drift.
    far_future_2099_04_ms = "4078684800000"
    far_future_2099_05_ms = "4081276800000"
    expired_2024_02_ms = "1706745600000"
    base = {
        "status": 0,
        "latest_receipt_info": [
            {
                "product_id": "com.pulseplate.premium.monthly",
                "expires_date_ms": far_future_2099_04_ms,
                "transaction_id": "txn-001",
                "original_transaction_id": "original-txn-001",
            }
        ],
    }
    mapping: dict[str, dict[str, Any]] = {
        "base64_receipt_blob_renewal_1": {
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": far_future_2099_04_ms,
                    "transaction_id": "txn-renewal-1",
                    "original_transaction_id": "txn-renewal-1",
                }
            ],
        },
        "base64_receipt_blob_renewal_2": {
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": far_future_2099_05_ms,
                    "transaction_id": "txn-renewal-2",
                    "original_transaction_id": "txn-renewal-2",
                }
            ],
        },
        "base64_receipt_blob_expired": {
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": expired_2024_02_ms,
                    "transaction_id": "txn-expired-1",
                    "original_transaction_id": "txn-expired-1",
                }
            ],
        },
        "base64_receipt_blob_pro_route": {
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": far_future_2099_04_ms,
                    "transaction_id": "txn-pro-route-1",
                    "original_transaction_id": "txn-pro-route-1",
                }
            ],
        },
        "base64_receipt_blob_vip_route": {
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.vip.monthly",
                    "expires_date_ms": far_future_2099_05_ms,
                    "transaction_id": "txn-vip-route-1",
                    "original_transaction_id": "txn-vip-route-1",
                }
            ],
        },
        "base64_receipt_blob_forged": {"status": 21002},
        "base64_receipt_blob_get": {
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": far_future_2099_04_ms,
                    "transaction_id": "txn-get-1",
                    "original_transaction_id": "original-txn-get-1",
                }
            ],
        },
    }
    return mapping.get(receipt_data, base)


@pytest.fixture(autouse=True)
def _mock_apple_verify_for_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Apple verify so activation tests can run without real Apple API.

    Server-side reverification requires valid Apple response. This fixture
    returns deterministic responses for known test receipt_data values.
    """
    from app.services import payments_activation

    async def _fake_call(url: str, receipt_data: str) -> dict[str, Any]:
        del url
        return _apple_response_for_receipt(receipt_data)

    monkeypatch.setattr(
        payments_activation,
        "_call_apple_verify_endpoint",
        _fake_call,
    )


@pytest.fixture
def _db_backed_paid_authz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force production-like DB-backed authz for canonical paid-route checks."""

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("PRO_API_KEYS", "test_pro_key")  # pragma: allowlist secret
    monkeypatch.setenv("VIP_API_KEYS", "test_vip_key")  # pragma: allowlist secret


def _json(response: Any) -> dict[str, Any]:
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    payload: dict[str, Any] = response.json()
    return payload


def _ios_payload(
    *,
    transaction_id: str = "txn-001",
    product_id: str = "com.pulseplate.premium.monthly",
    tier: str = "pro",
    status: str = "active",
    expires_at: str | None = "2026-04-01T00:00:00Z",
    receipt_data: str | None = "base64_receipt_blob",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "ios_app_store",
        "payload": {
            "verification_result": {
                "transaction_id": transaction_id,
                "original_transaction_id": "original-txn-001",
                "product_id": product_id,
                "subscription_tier": tier,
                "status": status,
                "platform": "ios",
            }
        },
    }
    if expires_at is not None:
        payload["payload"]["verification_result"]["expires_at"] = expires_at
    if receipt_data is not None:
        payload["payload"]["receipt_data"] = receipt_data
    return payload


def _relative_iso(*, days: int) -> str:
    """Return a deterministic ISO timestamp relative to now for entitlement tests."""

    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def _manual_payload(
    *,
    source: str,
    source_reference: str,
    submitted_amount: str = "9.99",
    submitted_currency: str = "BYN",
) -> dict[str, Any]:
    return {
        "source": source,
        "payload": {
            "source_reference": source_reference,
            "submitted_amount": submitted_amount,
            "submitted_currency": submitted_currency,
        },
    }


def _load_counts() -> tuple[int, int]:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        subscription_count = len(session.execute(select(Subscription)).scalars().all())
        audit_count = len(session.execute(select(SubscriptionActivationAudit)).scalars().all())
        return subscription_count, audit_count
    finally:
        session.close()


def _load_subscription_for_user_source(user_id: int, source: str) -> Subscription:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.source == source,
        )
        subscription = session.execute(statement).scalar_one()
        session.expunge(subscription)
        return subscription
    finally:
        session.close()


def _load_audit(activation_id: str) -> SubscriptionActivationAudit:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        audit = session.get(SubscriptionActivationAudit, activation_id)
        assert audit is not None
        session.expunge(audit)
        return audit
    finally:
        session.close()


def _set_subscription_status_for_user_source(
    *,
    user_id: int,
    source: str,
    status: str,
    expires_at: datetime | None = None,
) -> None:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.source == source,
        )
        subscription = session.execute(statement).scalar_one()
        subscription.status = status
        subscription.expires_at = expires_at
        session.commit()
    finally:
        session.close()


def _premium_week_payload() -> dict[str, Any]:
    return {
        "targets": {
            "kcal": 2000,
            "macros": {
                "protein_g": 110.0,
                "fat_g": 70.0,
                "carbs_g": 220.0,
                "fiber_g": 30.0,
            },
            "micro": {"vitamin_c_mg": 90.0, "iron_mg": 14.0},
            "water_ml": 0,
            "activity_week": {
                "moderate_aerobic_min": 150,
                "vigorous_aerobic_min": 75,
                "strength_sessions": 2,
                "steps_daily": 8000,
            },
        },
        "diet_flags": [],
        "lang": "en",
    }


def _vip_weekly_plan_payload() -> dict[str, Any]:
    return {
        "weight": 70.0,
        "height": 170.0,
        "age": 30,
        "gender": "female",
        "activity_level": "moderate",
        "dietary_preferences": ["vegetarian"],
        "target_calories": 1800,
    }


def test_activate_subscription_ios_empty_receipt_data_returns_403(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """iOS activation with empty receipt_data raises ActivationReverifyRejectedError (line 1198)."""
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(receipt_data=""),
    )
    assert response.status_code == 403, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "activation_reverify_rejected"


@pytest.mark.asyncio
async def test_activate_subscription_async_delegates_to_sync_for_non_ios_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """activate_subscription_async delegates to sync activate_subscription for non-iOS (line 1193)."""
    expected = SubscriptionActivationResponse(
        activation_id="delegated-activation-1",
        source=PaymentSource.erip_qr,
        tier=SubscriptionTier.pro,
        status=SubscriptionStatus.active,
        platform="ios",
    )

    def _fake_activate(
        *,
        payload: ActivateSubscriptionRequest,
        user_id: int,
    ) -> SubscriptionActivationResponse:
        assert payload.source == PaymentSource.erip_qr
        assert user_id == 42
        return expected

    monkeypatch.setattr(
        payments_activation,
        "activate_subscription",
        _fake_activate,
    )

    payload = ActivateSubscriptionRequest.model_validate(
        _manual_payload(source="erip_qr", source_reference="ERIP-QR-99999"),
    )
    result = await payments_activation.activate_subscription_async(
        payload=payload,
        user_id=42,
    )
    assert result == expected
    assert result.activation_id == "delegated-activation-1"


def test_activate_subscription_requires_transport_auth(client: TestClient) -> None:
    response = client.post("/api/v1/pro/payments/activate", json=_ios_payload())
    assert response.status_code == 401, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "activation_transport_unauthorized"
    assert payload["detail"] == TRANSPORT_AUTH_REQUIRED_DETAIL
    assert "X-API-Key" not in payload["detail"]


def test_activate_subscription_blank_transport_header_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers={"X-API-Key": "   "},
        json=_ios_payload(),
    )
    assert response.status_code == 401, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "activation_transport_unauthorized"
    assert payload["detail"] == TRANSPORT_AUTH_REQUIRED_DETAIL
    assert "blank" not in payload["detail"].lower()


def test_ios_verified_happy_path_persists_subscription(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(),
    )
    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["source"] == "ios_app_store"
    assert payload["tier"] == "pro"
    assert payload["status"] == "active"
    assert payload["platform"] == "ios"
    assert payload["product_id"] == "com.pulseplate.premium.monthly"
    assert payload["expires_at"].startswith("2099-04-01T00:00:00")
    assert payload["activated_at"] is not None

    subscription_count, audit_count = _load_counts()
    assert subscription_count == 1
    assert audit_count == 1

    audit = _load_audit(payload["activation_id"])
    assert audit.provider_receipt_hash is not None
    assert audit.provider_receipt_hash != "base64_receipt_blob"


def test_ios_replay_is_idempotent_and_creates_no_duplicates(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    body = _ios_payload(transaction_id="txn-replay-1")
    first = client.post("/api/v1/pro/payments/activate", headers=pro_headers, json=body)
    second = client.post("/api/v1/pro/payments/activate", headers=pro_headers, json=body)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert _json(first) == _json(second)

    subscription_count, audit_count = _load_counts()
    assert subscription_count == 1
    assert audit_count == 1


def test_ios_renewal_updates_existing_subscription_row(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    first = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-renewal-1",
            expires_at="2026-04-01T00:00:00Z",
            receipt_data="base64_receipt_blob_renewal_1",
        ),
    )
    second = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-renewal-2",
            expires_at="2026-05-01T00:00:00Z",
            receipt_data="base64_receipt_blob_renewal_2",
        ),
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    user_id = _json(second)["user_id"]
    subscription = _load_subscription_for_user_source(user_id, "ios_app_store")
    assert subscription.source_reference == "txn-renewal-2"
    assert subscription.expires_at is not None
    assert subscription.expires_at.isoformat().startswith("2099-05-01T00:00:00")

    subscription_count, audit_count = _load_counts()
    assert subscription_count == 1
    assert audit_count == 2


def test_ios_expired_evidence_is_rejected_fail_closed(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-expired-1",
            status="expired",
            expires_at="2026-03-01T00:00:00Z",
            receipt_data="base64_receipt_blob_expired",
        ),
    )
    assert response.status_code == 403, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "activation_reverify_rejected"


def test_ios_activation_rejects_oversized_receipt_data(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Oversized receipt_data must return 422 (DoS protection)."""
    oversized = "x" * (512_001)
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(receipt_data=oversized),
    )
    assert response.status_code == 422, response.text


def test_ios_forged_verification_result_rejected_activation_reverify(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    """Activation cannot persist paid state from client-supplied forged verification_result.

    Client sends forged verification_result (pro, active) with invalid receipt_data.
    Server reverifies receipt, gets invalid Apple response, rejects activation.
    No subscription must be persisted.
    """
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-forged-1",
            tier="pro",
            status="active",
            expires_at="2026-06-01T00:00:00Z",
            receipt_data="base64_receipt_blob_forged",
        ),
    )
    assert response.status_code == 403, response.text
    payload = _json(response)
    assert payload.get("code") == "activation_reverify_rejected"

    subscription_count, audit_count = _load_counts()
    assert subscription_count == 0
    assert audit_count == 0


def test_free_user_denied_on_canonical_pro_route(
    client: TestClient,
    pro_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    response = client.get("/api/v1/pro/session", headers=pro_headers)
    assert response.status_code == 403, response.text


def test_free_user_denied_on_canonical_vip_route(
    client: TestClient,
    vip_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    response = client.get("/api/v1/vip/health", headers=vip_headers)
    assert response.status_code == 403, response.text


def test_active_pro_allows_pro_but_not_vip(
    client: TestClient,
    pro_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    activation = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-pro-route-1",
            tier="pro",
            status="active",
            expires_at=_relative_iso(days=30),
            receipt_data="base64_receipt_blob_pro_route",
        ),
    )
    assert activation.status_code == 200, activation.text

    pro_response = client.get("/api/v1/pro/session", headers=pro_headers)
    assert pro_response.status_code == 200, pro_response.text
    assert _json(pro_response)["tier"] == "PRO"

    vip_response = client.get("/api/v1/vip/health", headers=pro_headers)
    assert vip_response.status_code == 403, vip_response.text


def test_active_vip_allows_vip_and_pro(
    client: TestClient,
    vip_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    activation = client.post(
        "/api/v1/pro/payments/activate",
        headers=vip_headers,
        json=_ios_payload(
            transaction_id="txn-vip-route-1",
            tier="vip",
            status="active",
            expires_at=_relative_iso(days=45),
            receipt_data="base64_receipt_blob_vip_route",
        ),
    )
    assert activation.status_code == 200, activation.text

    pro_response = client.get("/api/v1/pro/session", headers=vip_headers)
    assert pro_response.status_code == 200, pro_response.text
    assert _json(pro_response)["tier"] == "VIP"

    vip_response = client.get("/api/v1/vip/health", headers=vip_headers)
    assert vip_response.status_code == 200, vip_response.text


def test_expired_entitlement_denied_everywhere(
    client: TestClient,
    vip_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    activation = client.post(
        "/api/v1/pro/payments/activate",
        headers=vip_headers,
        json=_ios_payload(
            transaction_id="txn-expired-1",
            tier="vip",
            status="expired",
            expires_at=_relative_iso(days=-10),
            receipt_data="base64_receipt_blob_expired",
        ),
    )
    assert activation.status_code == 403, activation.text

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 403


def test_cancelled_entitlement_denied_everywhere(
    client: TestClient,
    vip_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    activation = client.post(
        "/api/v1/pro/payments/activate",
        headers=vip_headers,
        json=_ios_payload(
            transaction_id="txn-cancelled-route-1",
            tier="vip",
            status="active",
            expires_at=_relative_iso(days=60),
        ),
    )
    assert activation.status_code == 200, activation.text
    user_id = _json(activation)["user_id"]

    _set_subscription_status_for_user_source(
        user_id=user_id,
        source="ios_app_store",
        status="cancelled",
    )

    assert client.get("/api/v1/pro/session", headers=vip_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=vip_headers).status_code == 403


def test_pending_manual_review_does_not_unlock_paid_routes(
    client: TestClient,
    pro_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    activation = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_manual_payload(
            source="swift_manual",
            source_reference="swift-manual-route-1",
        ),
    )
    assert activation.status_code == 200, activation.text
    user_id = _json(activation)["user_id"]

    subscription = _load_subscription_for_user_source(user_id, "swift_manual")
    assert subscription.status == "pending_manual_review"

    assert client.get("/api/v1/pro/session", headers=pro_headers).status_code == 403
    assert client.get("/api/v1/vip/health", headers=pro_headers).status_code == 403


def test_pre_entitlement_billing_route_stays_accessible(
    client: TestClient,
    pro_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-pre-entitlement-1",
            tier="pro",
            status="active",
            expires_at=_relative_iso(days=35),
        ),
    )
    assert response.status_code == 200, response.text
    assert _json(response)["status"] == "active"


def test_deprecated_premium_alias_does_not_bypass_canonical_pro_authz(
    client: TestClient,
    pro_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    response = client.post(
        "/api/v1/premium/plan/week-flexible",
        headers=pro_headers,
        json=_premium_week_payload(),
    )
    assert response.status_code == 403, response.text


def test_deprecated_vip_alias_does_not_bypass_backend_entitlement_truth(
    client: TestClient,
    vip_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    response = client.post(
        "/api/v1/vip/weekly-plan",
        headers=vip_headers,
        json=_vip_weekly_plan_payload(),
    )
    assert response.status_code == 403, response.text


def test_active_row_with_past_expiry_denies_paid_routes(
    client: TestClient,
    pro_headers: dict[str, str],
    _db_backed_paid_authz: None,
) -> None:
    activation = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-expiry-check-1",
            tier="pro",
            status="active",
            expires_at=_relative_iso(days=60),
        ),
    )
    assert activation.status_code == 200, activation.text
    user_id = _json(activation)["user_id"]

    _set_subscription_status_for_user_source(
        user_id=user_id,
        source="ios_app_store",
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    assert client.get("/api/v1/pro/session", headers=pro_headers).status_code == 403


def test_activate_subscription_unsupported_source_returns_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json={"source": "unknown_source", "payload": {}},
    )
    assert response.status_code == 422, response.text
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("source", ["erip_qr", "swift_manual"])
def test_manual_sources_create_pending_manual_review(
    client: TestClient,
    pro_headers: dict[str, str],
    source: str,
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_manual_payload(source=source, source_reference=f"{source}-reference-1"),
    )
    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["source"] == source
    assert payload["tier"] == "pro"
    assert payload["status"] == "pending_manual_review"
    assert payload["platform"] == "web"
    assert payload["activated_at"] is None


def test_manual_replay_is_stable_after_payload_normalization(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    first = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_manual_payload(source="erip_qr", source_reference="ERIP-QR-12345"),
    )
    second = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json={
            "source": "erip_qr",
            "payload": {
                "source_reference": "  ERIP-QR-12345  ",
                "submitted_amount": " 9.99 ",
                "submitted_currency": " byn ",
            },
        },
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert _json(first)["activation_id"] == _json(second)["activation_id"]


def test_manual_source_conflict_returns_409(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    first = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_manual_payload(source="erip_qr", source_reference="ERIP-QR-12345"),
    )
    conflict = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_manual_payload(
            source="erip_qr",
            source_reference="ERIP-QR-12345",
            submitted_amount="12.99",
        ),
    )
    assert first.status_code == 200, first.text
    assert conflict.status_code == 409, conflict.text
    payload = _json(conflict)
    assert payload["status"] == "error"
    assert payload["code"] == "idempotency_conflict"
    assert payload["detail"] == DETERMINISTIC_ACTIVATION_CONFLICT_DETAIL
    assert "deterministic activation key conflict" not in payload["detail"]


def test_activate_subscription_malformed_body_returns_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json={"source": "erip_qr", "payload": {}},
    )
    assert response.status_code == 422, response.text
    assert response.headers["content-type"].startswith("application/json")


def test_activate_subscription_legacy_body_is_rejected_on_runtime_route(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json={
            "source": "ios_app_store",
            "plan": "pro_monthly",
            "client_event_id": "evt-legacy-runtime-1",
            "verification_ok": True,
        },
    )
    assert response.status_code == 422, response.text
    payload = _json(response)
    assert payload["detail"] == "canonical activation payload is required on this route"


def test_get_activation_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(transaction_id="txn-get-1", receipt_data="base64_receipt_blob_get"),
    )
    assert created.status_code == 200, created.text
    activation_id = _json(created)["activation_id"]

    fetched = client.get(
        f"/api/v1/pro/payments/activations/{activation_id}",
        headers=pro_headers,
    )
    assert fetched.status_code == 200, fetched.text
    payload = _json(fetched)
    assert payload["activation_id"] == activation_id
    assert payload["source_reference"] == "txn-get-1"


def test_get_activation_wrong_user_returns_403(
    client: TestClient,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(transaction_id="txn-forbidden-1"),
    )
    assert created.status_code == 200, created.text
    activation_id = _json(created)["activation_id"]

    response = client.get(
        f"/api/v1/pro/payments/activations/{activation_id}",
        headers=vip_headers,
    )
    assert response.status_code == 403, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "forbidden"
    assert payload["detail"] == ACTIVATION_ACCESS_FORBIDDEN_DETAIL
    assert "activation access forbidden" not in payload["detail"]


def test_get_activation_missing_transport_protection_returns_401(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(transaction_id="txn-missing-auth-1"),
    )
    assert created.status_code == 200, created.text
    activation_id = _json(created)["activation_id"]

    response = client.get(f"/api/v1/pro/payments/activations/{activation_id}")
    assert response.status_code == 401, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "activation_transport_unauthorized"
    assert payload["detail"] == TRANSPORT_AUTH_REQUIRED_DETAIL
    assert "unauthorized" not in payload["detail"].lower()
    assert "x-api-key" not in payload["detail"].lower()
    assert "internal" not in payload["detail"].lower()


def test_get_activation_not_found_returns_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/pro/payments/activations/missing-activation",
        headers=pro_headers,
    )
    assert response.status_code == 404, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "not_found"


def test_ios_verified_result_normalizes_optional_fields_and_timezone() -> None:
    result = IOSVerifiedActivationResult.model_validate(
        {
            "transaction_id": " txn-optional ",
            "original_transaction_id": None,
            "product_id": " product-id ",
            "subscription_tier": "pro",
            "status": "active",
            "expires_at": datetime(2026, 4, 1, 0, 0, 0),
            "platform": "ios",
        }
    )

    assert result.transaction_id == "txn-optional"
    assert result.original_transaction_id is None
    assert result.product_id == "product-id"
    assert result.expires_at == datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_ios_verified_result_rejects_non_ios_platform() -> None:
    with pytest.raises(ValueError, match="ios verification result must use ios platform"):
        IOSVerifiedActivationResult.model_validate(
            {
                "transaction_id": "txn-001",
                "product_id": "product-id",
                "subscription_tier": "pro",
                "status": "active",
                "expires_at": "2026-04-01T00:00:00Z",
                "platform": "web",
            }
        )


def test_ios_verified_result_requires_expires_at_for_active_status() -> None:
    with pytest.raises(ValueError, match="expires_at is required"):
        IOSVerifiedActivationResult.model_validate(
            {
                "transaction_id": "txn-001",
                "product_id": "product-id",
                "subscription_tier": "pro",
                "status": "active",
                "platform": "ios",
            }
        )


def test_ios_verified_result_allows_missing_expires_at_for_rejected_status() -> None:
    result = IOSVerifiedActivationResult.model_validate(
        {
            "transaction_id": "txn-rejected-1",
            "product_id": "product-id",
            "subscription_tier": "pro",
            "status": "rejected",
            "platform": "ios",
        }
    )

    assert result.expires_at is None


def test_ios_payload_validator_passthrough_branches() -> None:
    assert IOSAppStoreActivationPayload._normalize_receipt_data(None) is None
    assert IOSAppStoreActivationPayload._normalize_receipt_data(123) == 123


def test_manual_payload_allows_missing_optional_amount_and_currency() -> None:
    payload = ManualActivationPayload.model_validate(
        {
            "source_reference": "ERIP-QR-12345",
            "submitted_amount": None,
            "submitted_currency": None,
        }
    )

    assert payload.submitted_amount is None
    assert payload.submitted_currency is None


def test_activate_subscription_request_normalizes_canonical_payload_for_stable_hashing() -> None:
    request = ActivateSubscriptionRequest.model_validate(
        {
            "source": "erip_qr",
            "payload": {
                "source_reference": "  ERIP-QR-12345  ",
                "submitted_amount": " 9.99 ",
                "submitted_currency": " byn ",
            },
        }
    )

    assert isinstance(request.payload, ManualActivationPayload)
    assert request.model_dump(mode="json", exclude_none=True)["payload"] == {
        "source_reference": "ERIP-QR-12345",
        "submitted_amount": "9.99",
        "submitted_currency": "BYN",
    }


def test_activate_subscription_request_legacy_requires_client_event_id() -> None:
    with pytest.raises(ValueError, match="client_event_id is required when payload is omitted"):
        ActivateSubscriptionRequest.model_validate(
            {
                "source": "ios_app_store",
                "plan": "pro_monthly",
            }
        )


def test_legacy_request_accessors_reject_payload_lookup() -> None:
    request = ActivateSubscriptionRequest.model_validate(
        {
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "evt-legacy-accessor-1",
        }
    )

    with pytest.raises(ValueError, match="ios activation payload is unavailable"):
        request.get_ios_payload()
    with pytest.raises(ValueError, match="manual activation payload is unavailable"):
        request.get_manual_payload()


def test_get_ios_payload_validates_constructed_dict_payload() -> None:
    request = ActivateSubscriptionRequest.model_construct(
        source=PaymentSource.ios_app_store,
        payload={
            "verification_result": {
                "transaction_id": "txn-constructed-ios-1",
                "original_transaction_id": "txn-constructed-ios-1",
                "product_id": "com.pulseplate.premium.monthly",
                "subscription_tier": "pro",
                "status": "active",
                "expires_at": "2099-04-01T00:00:00Z",
                "platform": "ios",
            },
            "receipt_data": "receipt-data-constructed-ios-12345",
        },
        plan=None,
        client_event_id=None,
        external_txn_id=None,
        verification_ok=None,
        verification_payload={},
    )

    payload = request.get_ios_payload()
    assert payload.verification_result.transaction_id == "txn-constructed-ios-1"
    assert payload.receipt_data == "receipt-data-constructed-ios-12345"


def test_get_manual_payload_validates_constructed_dict_payload() -> None:
    request = ActivateSubscriptionRequest.model_construct(
        source=PaymentSource.erip_qr,
        payload={
            "source_reference": "ERIP-CONSTRUCTED-1",
            "submitted_amount": "19.99",
            "submitted_currency": "BYN",
        },
        plan=None,
        client_event_id=None,
        external_txn_id=None,
        verification_ok=None,
        verification_payload={},
    )

    payload = request.get_manual_payload()
    assert payload.source_reference == "ERIP-CONSTRUCTED-1"
    assert payload.submitted_currency == "BYN"


def test_subscription_activation_response_fills_compatibility_fields() -> None:
    response = SubscriptionActivationResponse.model_validate(
        {
            "activation_id": "activation-1",
            "source": "ios_app_store",
            "tier": "pro",
            "status": "active",
            "platform": "ios",
        }
    )

    assert response.intent_id == "activation-1"
    assert response.audit_id == "activation-1"
    assert response.payment_source == PaymentSource.ios_app_store
    assert response.subscription_tier is not None
    assert response.subscription_tier.value == "pro"


def test_subscription_activation_response_fills_canonical_fields_from_legacy_values() -> None:
    response = SubscriptionActivationResponse.model_validate(
        {
            "activation_id": "activation-2",
            "payment_source": "swift_manual",
            "subscription_tier": "vip",
            "status": "pending_verification",
            "platform": "web",
        }
    )

    assert response.source == PaymentSource.swift_manual
    assert response.tier == SubscriptionTier.vip


def test_internal_helper_handles_none_receipt_and_none_amount() -> None:
    assert payments_activation._hash_receipt(None) is None
    assert payments_activation._amount_to_minor_units(None) is None


def test_internal_helper_rejects_invalid_amount() -> None:
    with pytest.raises(ValueError, match="submitted_amount must be a valid decimal string"):
        payments_activation._amount_to_minor_units("not-a-number")


def test_internal_helper_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="submitted_amount must be non-negative"):
        payments_activation._amount_to_minor_units("-1.00")


def test_internal_reconcile_status_helper_covers_all_paths() -> None:
    assert (
        payments_activation._reconcile_status_from_subscription_status(
            status=SubscriptionStatus.pending_manual_review
        )
        == ReconcileStatus.pending
    )
    assert (
        payments_activation._reconcile_status_from_subscription_status(
            status=SubscriptionStatus.rejected
        )
        == ReconcileStatus.rejected
    )
    assert (
        payments_activation._reconcile_status_from_subscription_status(
            status=SubscriptionStatus.expired
        )
        == ReconcileStatus.verified
    )
    assert (
        payments_activation._reconcile_status_from_subscription_status(
            status=SubscriptionStatus.cancelled
        )
        == ReconcileStatus.not_required
    )


def test_internal_optional_parsers_fail_closed() -> None:
    assert payments_activation._parse_optional_plan(123) is None
    assert payments_activation._parse_optional_plan("enterprise") is None
    assert payments_activation._parse_optional_subscription_tier_value(123) is None
    assert payments_activation._parse_optional_subscription_tier_value("gold") is None
    assert (
        payments_activation._response_tier_value(
            tier=SubscriptionTier.free,
            evidence_summary={},
        )
        is None
    )


def test_internal_resolve_user_id_fail_closed() -> None:
    with pytest.raises(ValueError, match="user_id or issuer is required"):
        payments_activation._resolve_user_id(user_id=None, issuer=None)
    with pytest.raises(ValueError, match="issuer is invalid"):
        payments_activation._resolve_user_id(user_id=None, issuer="api_key:abc")
    with pytest.raises(ValueError, match="issuer is invalid"):
        payments_activation._resolve_user_id(user_id=None, issuer="subject:not-a-number")


def test_internal_legacy_status_and_reconcile_status_parsers() -> None:
    assert payments_activation._resolve_legacy_status(
        source=PaymentSource.ios_app_store,
        verification_ok=False,
    ) == (SubscriptionStatus.rejected, ReconcileStatus.rejected)
    assert payments_activation._resolve_legacy_status(
        source=PaymentSource.erip_qr,
        verification_ok=None,
    ) == (SubscriptionStatus.pending_verification, ReconcileStatus.pending)
    assert payments_activation._parse_optional_reconcile_status(123) is None
    assert payments_activation._parse_optional_reconcile_status("unsupported") is None


def test_internal_normalize_legacy_activation_rejects_missing_fields() -> None:
    request = ActivateSubscriptionRequest.model_construct(
        source=PaymentSource.ios_app_store,
        payload=None,
        plan=None,
        client_event_id=None,
        external_txn_id=None,
        verification_ok=None,
        verification_payload={},
    )

    with pytest.raises(ValueError, match="legacy activation requires plan and client_event_id"):
        payments_activation._normalize_legacy_activation(payload=request)


def test_internal_coerce_datetime_covers_fail_closed_paths() -> None:
    naive = datetime(2026, 4, 1, 0, 0, 0)
    aware = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)

    assert payments_activation._coerce_datetime(None) is None
    assert payments_activation._coerce_datetime(naive) == naive.replace(tzinfo=timezone.utc)
    assert payments_activation._coerce_datetime(aware) == aware
    assert payments_activation._coerce_datetime("  ") is None
    assert payments_activation._coerce_datetime("not-a-date") is None


def test_issuer_from_api_key_rejects_blank_key() -> None:
    with pytest.raises(ValueError, match="api_key is required"):
        payments_activation.issuer_from_api_key("   ")


def test_activate_subscription_rolls_back_on_sqlalchemy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingSession:
        def __init__(self) -> None:
            self.rolled_back = False

        def add(self, _obj: object) -> None:
            return None

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            raise SQLAlchemyError("boom")

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            return None

    session = FailingSession()
    monkeypatch.setattr(
        payments_activation,
        "get_session_factory",
        lambda: (lambda: session),
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_user_key",
        lambda **_: None,
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_subscription_for_user_source",
        lambda **_: None,
    )

    with pytest.raises(SQLAlchemyError, match="boom"):
        payments_activation.activate_subscription(
            user_id=1,
            payload=payments_activation.ActivateSubscriptionRequest.model_validate(_ios_payload()),
        )

    assert session.rolled_back is True


def test_activate_subscription_replays_after_integrity_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = payments_activation.ActivateSubscriptionRequest.model_validate(_ios_payload())
    normalized = payments_activation._normalize_activation(payload=request)
    replay_audit = type(
        "Audit",
        (),
        {
            "id": "activation-replay-1",
            "user_id": 1,
            "source": "ios_app_store",
            "subscription_id": "sub-1",
            "payload_hash": normalized.payload_hash,
            "tier": "pro",
            "status": "active",
            "platform": "ios",
            "provider_receipt_hash": "receipt-hash",
            "source_reference": "txn-race-1",
            "product_id": "com.pulseplate.premium.monthly",
            "expires_at": datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
            "activated_at": datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc),
            "submitted_amount_minor": None,
            "submitted_currency": None,
            "evidence_summary": {"reconcile_status": "verified"},
            "created_at": datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc),
        },
    )()

    class IntegrityRaceSession:
        def __init__(self) -> None:
            self.rollback_count = 0
            self.commit_count = 0

        def add(self, _obj: object) -> None:
            return None

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            self.commit_count += 1
            raise IntegrityError("insert", {}, Exception("duplicate"))

        def rollback(self) -> None:
            self.rollback_count += 1

        def close(self) -> None:
            return None

    session = IntegrityRaceSession()

    monkeypatch.setattr(
        payments_activation,
        "get_session_factory",
        lambda: (lambda: session),
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_user_key",
        lambda **kwargs: (
            None
            if kwargs["idempotency_key"] == normalized.idempotency_key and session.commit_count == 0
            else replay_audit
        ),
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_subscription_for_user_source",
        lambda **_: None,
    )

    response = payments_activation.activate_subscription(
        user_id=1,
        payload=request,
    )

    assert isinstance(response, SubscriptionActivationResponse)
    assert response.activation_id == "activation-replay-1"
    assert session.rollback_count == 1


def test_get_reconcile_activation_status_returns_none_when_subscription_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummySession:
        def close(self) -> None:
            return None

    audit = type(
        "Audit",
        (),
        {
            "id": "activation-1",
            "user_id": 1,
            "source": "erip_qr",
            "subscription_id": "sub-1",
        },
    )()

    monkeypatch.setattr(
        payments_activation, "get_session_factory", lambda: (lambda: DummySession())
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_id",
        lambda **_: audit,
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_subscription_by_id",
        lambda **_: None,
    )

    result = payments_activation.get_reconcile_activation_status("activation-1", user_id=1)
    assert result is None


def test_reconcile_activation_raises_not_found_when_subscription_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummySession:
        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    audit = type(
        "Audit",
        (),
        {
            "id": "activation-1",
            "user_id": 1,
            "source": "erip_qr",
            "subscription_id": "sub-1",
        },
    )()

    monkeypatch.setattr(
        payments_activation, "get_session_factory", lambda: (lambda: DummySession())
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_id",
        lambda **_: audit,
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_user_key",
        lambda **_: None,
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_subscription_by_id",
        lambda **_: None,
    )

    with pytest.raises(payments_activation.ActivationNotFoundError, match="activation not found"):
        payments_activation.reconcile_activation(
            user_id=1,
            payload=payments_activation.ManualRailReconcileRequest.model_validate(
                {
                    "intent_id": "activation-1",
                    "client_event_id": "evt-reconcile-missing-sub-1",
                    "decision": "verified",
                }
            ),
        )


def test_reconcile_activation_rejects_non_pending_subscription_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummySession:
        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    audit = type(
        "Audit",
        (),
        {
            "id": "activation-1",
            "user_id": 1,
            "source": "erip_qr",
            "subscription_id": "sub-1",
        },
    )()
    subscription = type("Subscription", (), {"status": "active"})()

    monkeypatch.setattr(
        payments_activation, "get_session_factory", lambda: (lambda: DummySession())
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_id",
        lambda **_: audit,
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_audit_by_user_key",
        lambda **_: None,
    )
    monkeypatch.setattr(
        payments_activation.subscriptions_store,
        "get_subscription_by_id",
        lambda **_: subscription,
    )

    with pytest.raises(
        payments_activation.ActivationStateError,
        match="manual reconcile transition requires pending state",
    ):
        payments_activation.reconcile_activation(
            user_id=1,
            payload=payments_activation.ManualRailReconcileRequest.model_validate(
                {
                    "intent_id": "activation-1",
                    "client_event_id": "evt-reconcile-active-sub-1",
                    "decision": "verified",
                }
            ),
        )


def test_reset_state_rolls_back_on_sqlalchemy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingSession:
        def __init__(self) -> None:
            self.rolled_back = False

        def execute(self, _statement: object) -> None:
            raise SQLAlchemyError("cleanup failed")

        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            return None

    session = FailingSession()
    monkeypatch.setattr(
        payments_activation,
        "get_session_factory",
        lambda: (lambda: session),
    )

    payments_activation.reset_state()

    assert session.rolled_back is True


def test_subscription_activation_migration_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "billing-activation.sqlite3"
    database_url = f"sqlite:///{db_path}"
    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini = repo_root / "alembic.ini"
    temp_alembic_ini = tmp_path / "alembic.ini"
    temp_alembic_ini.write_text(
        alembic_ini.read_text(encoding="utf-8").replace(
            "script_location = alembic",
            f"script_location = {repo_root / 'alembic'}",
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    core_db.reset_db_for_tests()

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "config_path, repo_root = sys.argv[1], sys.argv[2]; "
                "from alembic.config import main; "
                "sys.path.append(repo_root); "
                'main(argv=["-c", config_path, "upgrade", "head"], prog="alembic")'
            ),
            str(temp_alembic_ini),
            str(repo_root),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert completed.returncode == 0, completed.stderr

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
    finally:
        engine.dispose()
        core_db.reset_db_for_tests()

    assert "subscriptions" in tables
    assert "subscription_activation_audit" in tables
