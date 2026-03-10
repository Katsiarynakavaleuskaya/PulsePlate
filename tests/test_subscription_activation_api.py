from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.models import Subscription, SubscriptionActivationAudit
from app.schemas.payments import IOSVerifiedActivationResult, ManualActivationPayload
from app.services import payments_activation
from core import db as core_db


@pytest.fixture(autouse=True)
def _reset_payments_state() -> None:
    from app.services import payments_activation

    payments_activation.reset_state()


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


def test_activate_subscription_requires_transport_auth(client: TestClient) -> None:
    response = client.post("/api/v1/pro/payments/activate", json=_ios_payload())
    assert response.status_code == 401, response.text
    payload = _json(response)
    assert payload["status"] == "error"
    assert payload["code"] == "activation_transport_unauthorized"


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
    assert payload["expires_at"].startswith("2026-04-01T00:00:00")
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
        ),
    )
    second = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(
            transaction_id="txn-renewal-2",
            expires_at="2026-05-01T00:00:00Z",
        ),
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    user_id = _json(second)["user_id"]
    subscription = _load_subscription_for_user_source(user_id, "ios_app_store")
    assert subscription.source_reference == "txn-renewal-2"
    assert subscription.expires_at is not None
    assert subscription.expires_at.isoformat().startswith("2026-05-01T00:00:00")

    subscription_count, audit_count = _load_counts()
    assert subscription_count == 1
    assert audit_count == 2


def test_ios_expired_evidence_is_persisted_as_expired(
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
        ),
    )
    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["status"] == "expired"
    assert payload["activated_at"] is None


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


def test_get_activation_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/payments/activate",
        headers=pro_headers,
        json=_ios_payload(transaction_id="txn-get-1"),
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


def test_internal_helper_handles_none_receipt_and_none_amount() -> None:
    assert payments_activation._hash_receipt(None) is None
    assert payments_activation._amount_to_minor_units(None) is None


def test_internal_helper_rejects_invalid_amount() -> None:
    with pytest.raises(ValueError, match="submitted_amount must be a valid decimal string"):
        payments_activation._amount_to_minor_units("not-a-number")


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
    alembic_bin = shutil.which("alembic")
    assert alembic_bin is not None
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
    completed = subprocess.run(
        [alembic_bin, "-c", str(temp_alembic_ini), "upgrade", "head"],
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
