from __future__ import annotations

from collections.abc import Callable
from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app import get_api_key as _APP_GET_API_KEY
from tests.payment_test_utils import json_response_payload as _json

pytestmark = pytest.mark.usefixtures("reset_payments_state")

DependencyOverride = tuple[FastAPI, Callable[..., object], Callable[..., object]]


def _is_app_get_api_key_dependency(dependency: Callable[..., object]) -> bool:
    """Return True for current or stale app-level API key dependency callables."""
    if getattr(dependency, "__name__", None) == "get_api_key":
        return True

    return dependency is _APP_GET_API_KEY


def _iter_app_override_targets(app: FastAPI) -> list[FastAPI]:
    """Return app instances that may carry app-level auth dependency overrides."""
    targets = [app]
    canonical_app: FastAPI | None
    try:
        from app.main import app as canonical_app
    except ImportError:
        canonical_app = None

    if isinstance(canonical_app, FastAPI):
        targets.append(canonical_app)

    unique_targets: list[FastAPI] = []
    seen_ids: set[int] = set()
    for target in targets:
        target_id = id(target)
        if target_id not in seen_ids:
            unique_targets.append(target)
            seen_ids.add(target_id)
    return unique_targets


def _pop_app_get_api_key_overrides(app: FastAPI) -> list[DependencyOverride]:
    """Remove all app-level get_api_key overrides, including stale reload keys."""
    removed: list[DependencyOverride] = []
    for app_target in _iter_app_override_targets(app):
        for dependency in list(app_target.dependency_overrides):
            if _is_app_get_api_key_dependency(dependency):
                removed.append(
                    (app_target, dependency, app_target.dependency_overrides.pop(dependency))
                )
    return removed


def _restore_dependency_overrides(
    overrides: list[DependencyOverride],
) -> None:
    """Restore dependency overrides removed for an isolated auth test."""
    for app_target, dependency, override in overrides:
        app_target.dependency_overrides[dependency] = override


def test_pop_app_get_api_key_overrides_removes_stale_reload_key(app: FastAPI) -> None:
    def get_api_key() -> str:
        return "stale"

    def _override() -> str:
        return "override"

    get_api_key.__module__ = "reloaded_legacy_app"
    app.dependency_overrides[get_api_key] = _override

    removed = _pop_app_get_api_key_overrides(app)

    assert (app, get_api_key, _override) in removed
    assert get_api_key not in app.dependency_overrides
    _restore_dependency_overrides(removed)
    assert app.dependency_overrides[get_api_key] is _override


def test_pop_app_get_api_key_overrides_scans_canonical_app() -> None:
    other_app = FastAPI()
    from app.main import app as canonical_app

    def _override() -> str:
        return "override"

    sentinel = object()
    original_override = canonical_app.dependency_overrides.get(_APP_GET_API_KEY, sentinel)
    canonical_app.dependency_overrides[_APP_GET_API_KEY] = _override

    try:
        removed = _pop_app_get_api_key_overrides(other_app)

        try:
            assert (canonical_app, _APP_GET_API_KEY, _override) in removed
            assert _APP_GET_API_KEY not in canonical_app.dependency_overrides
        finally:
            _restore_dependency_overrides(removed)
        assert canonical_app.dependency_overrides[_APP_GET_API_KEY] is _override
    finally:
        if original_override is sentinel:
            canonical_app.dependency_overrides.pop(_APP_GET_API_KEY, None)
        else:
            canonical_app.dependency_overrides[_APP_GET_API_KEY] = cast(
                Callable[..., object], original_override
            )


def test_manual_intent_rejects_invalid_transport_key_behaviorally(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers={"X-API-Key": "bad-key"},
        json={
            "source": "erip_qr",
            "plan": "pro_monthly",
            "client_event_id": "evt-invalid-transport-key",
            "external_txn_id": "invalid-transport-key",
            "amount_minor": 1999,
            "currency": "BYN",
        },
    )

    assert response.status_code == 401, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "API key required for billing verification"


def test_manual_intent_rejects_env_configured_pro_key_without_app_validator_override(
    app: FastAPI,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_overrides = _pop_app_get_api_key_overrides(app)
    try:
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
        monkeypatch.setenv("PRO_API_KEYS", pro_headers["X-API-Key"])

        with TestClient(app) as isolated_client:
            response = isolated_client.post(
                "/api/v1/pro/payments/ru-by/manual-intent",
                headers=pro_headers,
                json={
                    "source": "erip_qr",
                    "plan": "pro_monthly",
                    "client_event_id": "evt-pre-entitlement-db-mode",
                    "external_txn_id": "pre-entitlement-db-mode",
                    "amount_minor": 1999,
                    "currency": "BYN",
                },
            )
            session_response = isolated_client.get("/api/v1/pro/session", headers=pro_headers)
    finally:
        _restore_dependency_overrides(original_overrides)

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "API key required for billing verification"
    assert session_response.status_code == 403


def test_manual_intent_rejects_transport_key_when_configured_app_validator_rejects(
    app: FastAPI,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import billing

    def _reject_app_api_key(_: str) -> str:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    original_overrides = _pop_app_get_api_key_overrides(app)

    try:
        monkeypatch.setattr(billing, "validate_app_api_key", _reject_app_api_key)

        with TestClient(app) as isolated_client:
            response = isolated_client.post(
                "/api/v1/pro/payments/ru-by/manual-intent",
                headers=pro_headers,
                json={
                    "source": "swift_manual",
                    "plan": "pro_monthly",
                    "client_event_id": "evt-missing-app-validator",
                    "external_txn_id": "missing-app-validator",
                    "amount_minor": 1999,
                    "currency": "RUB",
                },
            )
    finally:
        _restore_dependency_overrides(original_overrides)

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "API key required for billing verification"


def test_manual_billing_validator_fails_closed_when_app_validator_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import billing

    monkeypatch.setenv("API_KEY", "test_key")

    validator = billing._get_effective_manual_billing_key_validator()

    assert validator("test_key") == "test_key"
    with pytest.raises(HTTPException) as exc_info:
        validator("env-configured-pro-key")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid API Key"


def test_manual_intent_uses_configured_api_key_not_app_dependency_override(
    app: FastAPI,
    manual_billing_headers: dict[str, str],
    pro_headers: dict[str, str],
) -> None:
    def _override(api_key: str = "") -> str:
        return api_key

    original_overrides = _pop_app_get_api_key_overrides(app)
    for app_target in _iter_app_override_targets(app):
        app_target.dependency_overrides[_APP_GET_API_KEY] = _override

    try:
        with TestClient(app) as isolated_client:
            rejected = isolated_client.post(
                "/api/v1/pro/payments/ru-by/manual-intent",
                headers=pro_headers,
                json={
                    "source": "erip_qr",
                    "plan": "pro_monthly",
                    "client_event_id": "evt-dependency-override-rejected",
                    "external_txn_id": "dependency-override-rejected",
                    "amount_minor": 1999,
                    "currency": "BYN",
                },
            )
            accepted = isolated_client.post(
                "/api/v1/pro/payments/ru-by/manual-intent",
                headers=manual_billing_headers,
                json={
                    "source": "erip_qr",
                    "plan": "pro_monthly",
                    "client_event_id": "evt-configured-api-key-accepted",
                    "external_txn_id": "configured-api-key-accepted",
                    "amount_minor": 1999,
                    "currency": "BYN",
                },
            )
    finally:
        for app_target in _iter_app_override_targets(app):
            app_target.dependency_overrides.pop(_APP_GET_API_KEY, None)
        _restore_dependency_overrides(original_overrides)

    assert rejected.status_code == 401, rejected.text
    assert rejected.json()["detail"] == "API key required for billing verification"
    assert accepted.status_code == 201, accepted.text


def test_manual_intent_happy_path(
    client: TestClient,
    manual_billing_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=manual_billing_headers,
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


def test_manual_intent_supports_vip_plan_with_app_transport_key(
    client: TestClient,
    manual_billing_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=manual_billing_headers,
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
    manual_billing_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=manual_billing_headers,
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
    manual_billing_headers: dict[str, str],
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
        headers=manual_billing_headers,
        json=payload,
    )
    second = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=manual_billing_headers,
        json=payload,
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert _json(first) == _json(second)


def test_manual_intent_conflict_returns_409(
    client: TestClient,
    manual_billing_headers: dict[str, str],
) -> None:
    first = client.post(
        "/api/v1/pro/payments/ru-by/manual-intent",
        headers=manual_billing_headers,
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
        headers=manual_billing_headers,
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
