from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest

from app.schemas.payments import AppleReceiptVerificationRequest
from tests.payment_test_utils import json_response_payload as _json

pytestmark = pytest.mark.usefixtures("reset_payments_state")


def _billing_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    accepted_key = "billing-verify-test-key"
    monkeypatch.setenv("API_KEY", accepted_key)
    return {"X-API-Key": accepted_key}


def _request_payload(receipt_data: str = "receipt-data-validated-12345") -> dict[str, str]:
    return {"receipt_data": receipt_data}


def _apple_receipt_entry(
    *,
    product_id: str = "com.pulseplate.premium.monthly",
    expires_date_ms: str = "4102444800000",
    transaction_id: str = "txn-1",
    original_transaction_id: str = "txn-1",
) -> dict[str, str]:
    return {
        "product_id": product_id,
        "expires_date_ms": expires_date_ms,
        "transaction_id": transaction_id,
        "original_transaction_id": original_transaction_id,
    }


def _install_apple_stub(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[dict[str, Any] | Exception],
) -> list[tuple[str, str]]:
    from app.services import payments_activation

    calls: list[tuple[str, str]] = []

    async def _fake(url: str, receipt_data: str) -> dict[str, Any]:
        calls.append((url, receipt_data))
        index = min(len(calls) - 1, len(responses) - 1)
        response = responses[index]
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(payments_activation, "_call_apple_verify_endpoint", _fake)
    return calls


def test_apple_verify_receipt_requires_valid_transport_api_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    calls = _install_apple_stub(
        monkeypatch,
        [
            {
                "status": 0,
                "latest_receipt_info": [_apple_receipt_entry()],
            }
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["provider"] == "apple"
    assert payload["verified"] is True
    assert payload["verification_state"] == "active"
    assert payload["environment"] == "production"
    assert payload["product_id"] == "com.pulseplate.premium.monthly"
    assert payload["activation_payload"] == {"tier": "pro", "platform": "ios"}
    assert payload["error"] is None
    assert calls == [("https://buy.itunes.apple.com/verifyReceipt", "receipt-data-validated-12345")]

    from app.services import payments_activation

    assert payments_activation._ACTIVATIONS == {}


def test_apple_verify_receipt_retries_sandbox_when_needed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    calls = _install_apple_stub(
        monkeypatch,
        [
            {"status": 21007},
            {
                "status": 0,
                "latest_receipt_info": [_apple_receipt_entry()],
            },
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload("sandbox-receipt-data-12345"),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["verified"] is True
    assert payload["environment"] == "sandbox"
    assert calls == [
        ("https://buy.itunes.apple.com/verifyReceipt", "sandbox-receipt-data-12345"),
        ("https://sandbox.itunes.apple.com/verifyReceipt", "sandbox-receipt-data-12345"),
    ]


def test_apple_verify_receipt_returns_invalid_business_envelope(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [
            {"status": 21010},
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["verified"] is False
    assert payload["verification_state"] == "invalid"
    assert payload["activation_payload"] is None
    assert payload["error"] == {
        "code": "APPLE_RECEIPT_INVALID",
        "message": "Receipt verification failed",
    }


def test_apple_verify_receipt_returns_expired_business_envelope(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [
            {
                "status": 0,
                "latest_receipt_info": [
                    _apple_receipt_entry(expires_date_ms="946684800000"),
                ],
            }
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["verified"] is False
    assert payload["verification_state"] == "expired"
    assert payload["error"] == {
        "code": "APPLE_RECEIPT_EXPIRED",
        "message": "Apple receipt is expired",
    }


def test_apple_verify_receipt_keeps_normal_renewal_active(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [
            {
                "status": 0,
                "latest_receipt_info": [
                    _apple_receipt_entry(
                        transaction_id="txn-restored-2",
                        original_transaction_id="txn-original-1",
                    ),
                ],
            }
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["verified"] is True
    assert payload["verification_state"] == "active"
    assert payload["activation_payload"] == {"tier": "pro", "platform": "ios"}


def test_apple_verify_receipt_uses_restored_state_only_for_explicit_signal(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [
            {
                "status": 0,
                "restore_detected": True,
                "latest_receipt_info": [
                    _apple_receipt_entry(),
                ],
            }
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["verified"] is True
    assert payload["verification_state"] == "restored"


def test_apple_verify_receipt_timeout_returns_504(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import payments_activation

    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [payments_activation.AppleVerifyTimeoutError()],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 504, response.text
    payload = _json(response)
    assert payload["verified"] is False
    assert payload["error"] == {
        "code": "APPLE_VERIFY_TIMEOUT",
        "message": "Apple receipt verification timed out",
    }


def test_apple_verify_receipt_upstream_error_returns_502(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import payments_activation

    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [payments_activation.AppleVerifyTransportError()],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 502, response.text
    payload = _json(response)
    assert payload["verified"] is False
    assert payload["error"] == {
        "code": "APPLE_UPSTREAM_ERROR",
        "message": "Apple receipt verification failed",
    }


def test_apple_verify_receipt_repeated_calls_are_stateless_replays(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    calls = _install_apple_stub(
        monkeypatch,
        [
            {
                "status": 0,
                "latest_receipt_info": [_apple_receipt_entry()],
            }
        ],
    )

    first = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )
    second = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert _json(first) == _json(second)
    assert calls == [
        ("https://buy.itunes.apple.com/verifyReceipt", "receipt-data-validated-12345"),
        ("https://buy.itunes.apple.com/verifyReceipt", "receipt-data-validated-12345"),
    ]


def test_apple_verify_receipt_requires_nonblank_api_key(client: TestClient) -> None:
    missing = client.post(
        "/api/v1/billing/apple/verify-receipt",
        json=_request_payload(),
    )
    blank = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers={"X-API-Key": "   "},
        json=_request_payload(),
    )

    assert missing.status_code == 401
    assert blank.status_code == 401


def test_apple_verify_receipt_rejects_malformed_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json={"receipt_data": "   "},
    )

    assert response.status_code == 422


def test_apple_verify_receipt_rejects_invalid_api_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "billing-verify-test-key")
    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers={"X-API-Key": "bad"},
        json=_request_payload(),
    )

    assert response.status_code == 401


def test_apple_verify_receipt_rejects_cancelled_receipt(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_apple_stub(
        monkeypatch,
        [
            {
                "status": 0,
                "latest_receipt_info": [
                    {
                        **_apple_receipt_entry(),
                        "cancellation_date": "2026-03-08T00:00:00Z",
                    }
                ],
            }
        ],
    )

    response = client.post(
        "/api/v1/billing/apple/verify-receipt",
        headers=_billing_headers(monkeypatch),
        json=_request_payload(),
    )

    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["verified"] is False
    assert payload["verification_state"] == "invalid"
    assert payload["activation_payload"] is None


def test_require_billing_transport_key_returns_500_when_validator_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app as app_module
    from app.routers import billing
    from fastapi import HTTPException

    monkeypatch.setattr(app_module, "get_api_key", None, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        billing._require_billing_transport_key("billing-verify-test-key")

    assert exc_info.value.status_code == 500


def test_require_billing_transport_key_returns_500_on_unexpected_validator_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app as app_module
    from app.routers import billing
    from fastapi import HTTPException

    def _boom(_: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "get_api_key", _boom, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        billing._require_billing_transport_key("billing-verify-test-key")

    assert exc_info.value.status_code == 500


def test_require_billing_transport_key_returns_500_on_non_string_validator_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app as app_module
    from app.routers import billing
    from fastapi import HTTPException

    monkeypatch.setattr(app_module, "get_api_key", lambda _: object(), raising=False)

    with pytest.raises(HTTPException) as exc_info:
        billing._require_billing_transport_key("billing-verify-test-key")

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_verify_apple_receipt_response_wraps_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import billing
    from app.services import payments_activation
    from fastapi.responses import JSONResponse

    async def _raise_transport(_: str) -> AppleReceiptVerificationRequest:
        raise payments_activation.AppleVerifyTransportError()

    monkeypatch.setattr(payments_activation, "verify_apple_receipt", _raise_transport)
    response = await billing._verify_apple_receipt_response(
        AppleReceiptVerificationRequest(receipt_data="receipt-data-validated-12345")
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 502
