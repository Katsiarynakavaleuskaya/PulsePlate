from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from app.schemas.payments import AppleVerificationEnvironment, AppleVerificationState
from app.services import payments_activation


class _FakeResponse:
    def __init__(self, payload: object, *, raise_http_error: bool = False) -> None:
        self._payload = payload
        self._raise_http_error = raise_http_error

    def raise_for_status(self) -> None:
        if self._raise_http_error:
            request = httpx.Request("POST", payments_activation.APPLE_VERIFY_PRODUCTION_URL)
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def json(self) -> object:
        return self._payload


class _FakeAsyncClient:
    def __init__(
        self,
        *,
        response: _FakeResponse | None = None,
        raised_exc: Exception | None = None,
        **kwargs: object,
    ) -> None:
        self.timeout = kwargs.get("timeout")
        self.response = response
        self.raised_exc = raised_exc
        self.captured_payload: dict[str, object] | None = None

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> bool:
        return False

    async def post(self, url: str, json: dict[str, object]) -> _FakeResponse:
        del url
        self.captured_payload = json
        if self.raised_exc is not None:
            raise self.raised_exc
        assert self.response is not None
        return self.response


def _install_fake_async_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: _FakeResponse | None = None,
    raised_exc: Exception | None = None,
) -> _FakeAsyncClient:
    fake_client = _FakeAsyncClient(
        response=response,
        raised_exc=raised_exc,
        timeout=payments_activation.APPLE_VERIFY_TIMEOUT_SECONDS,
    )

    def _factory(*args: object, **kwargs: object) -> _FakeAsyncClient:
        del args, kwargs
        return fake_client

    monkeypatch.setattr(payments_activation.httpx, "AsyncClient", _factory)
    return fake_client


def test_coerce_apple_status_covers_supported_inputs() -> None:
    assert payments_activation._coerce_apple_status(True) is None
    assert payments_activation._coerce_apple_status(21007) == 21007
    assert payments_activation._coerce_apple_status(" 21006 ") == 21006
    assert payments_activation._coerce_apple_status("bad-status") is None
    assert payments_activation._coerce_apple_status("") is None


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (
            datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        ),
        (datetime(2026, 4, 1, 12, 0), datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)),
        (4102444800000, datetime.fromtimestamp(4102444800000 / 1000.0, tz=timezone.utc)),
        ("4102444800000", datetime.fromtimestamp(4102444800000 / 1000.0, tz=timezone.utc)),
        ("2026-04-01T00:00:00Z", datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)),
        ("2026-04-01T00:00:00", datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)),
        ("2026-04-01 00:00:00 Etc/GMT", datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)),
    ],
)
def test_parse_apple_datetime_accepts_supported_formats(
    raw_value: object,
    expected: datetime,
) -> None:
    assert payments_activation._parse_apple_datetime(raw_value) == expected


def test_parse_apple_datetime_rejects_invalid_inputs() -> None:
    assert payments_activation._parse_apple_datetime(None) is None
    assert payments_activation._parse_apple_datetime("   ") is None
    assert payments_activation._parse_apple_datetime("not-a-date") is None
    assert payments_activation._parse_apple_datetime([]) is None


@pytest.mark.parametrize("raw_value", [10**30, str(10**30)])
def test_parse_apple_datetime_rejects_out_of_range_epoch_values(raw_value: object) -> None:
    assert payments_activation._parse_apple_datetime(raw_value) is None


def test_receipt_entries_falls_back_to_receipt_in_app() -> None:
    entries = payments_activation._receipt_entries(
        {
            "receipt": {
                "in_app": [
                    {"product_id": "com.pulseplate.premium.monthly"},
                    "skip-me",
                ]
            }
        }
    )

    assert entries == [{"product_id": "com.pulseplate.premium.monthly"}]


def test_activation_payload_for_product_covers_none_pro_vip_and_unknown() -> None:
    assert payments_activation._activation_payload_for_product(None) is None
    pro_payload = payments_activation._activation_payload_for_product(
        "com.pulseplate.premium.monthly"
    )
    vip_payload = payments_activation._activation_payload_for_product("com.pulseplate.vip.monthly")
    assert pro_payload is not None
    assert pro_payload.tier.value == "pro"
    assert pro_payload.platform == "ios"
    assert vip_payload is not None
    assert vip_payload.tier.value == "vip"
    assert vip_payload.platform == "ios"
    assert (
        payments_activation._activation_payload_for_product("com.pulseplate.unknown.monthly")
        is None
    )


@pytest.mark.asyncio
async def test_call_apple_verify_endpoint_returns_payload_and_uses_required_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    fake_client = _install_fake_async_client(
        monkeypatch,
        response=_FakeResponse({"status": 0}),
    )

    payload = await payments_activation._call_apple_verify_endpoint(
        payments_activation.APPLE_VERIFY_PRODUCTION_URL,
        "receipt-data-validated-12345",
    )

    assert payload == {"status": 0}
    assert fake_client.captured_payload == {
        "receipt-data": "receipt-data-validated-12345",
        "password": "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
        "exclude-old-transactions": True,
    }


@pytest.mark.asyncio
async def test_call_apple_verify_endpoint_raises_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_fake_async_client(
        monkeypatch,
        raised_exc=httpx.ReadTimeout("timeout"),
    )

    with pytest.raises(payments_activation.AppleVerifyTimeoutError):
        await payments_activation._call_apple_verify_endpoint(
            payments_activation.APPLE_VERIFY_PRODUCTION_URL,
            "receipt-data-validated-12345",
        )


@pytest.mark.asyncio
async def test_call_apple_verify_endpoint_raises_transport_for_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_fake_async_client(
        monkeypatch,
        response=_FakeResponse({"status": 0}, raise_http_error=True),
    )

    with pytest.raises(payments_activation.AppleVerifyTransportError):
        await payments_activation._call_apple_verify_endpoint(
            payments_activation.APPLE_VERIFY_PRODUCTION_URL,
            "receipt-data-validated-12345",
        )


@pytest.mark.asyncio
async def test_call_apple_verify_endpoint_raises_transport_when_secret_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)
    fake_client = _install_fake_async_client(
        monkeypatch,
        response=_FakeResponse({"status": 0}),
    )

    with pytest.raises(payments_activation.AppleVerifyTransportError):
        await payments_activation._call_apple_verify_endpoint(
            payments_activation.APPLE_VERIFY_PRODUCTION_URL,
            "receipt-data-validated-12345",
        )

    assert fake_client.captured_payload is None


@pytest.mark.asyncio
async def test_call_apple_verify_endpoint_rejects_non_dict_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET",
        "StrongAppleSharedSecretForTests123456789!",  # pragma: allowlist secret
    )
    _install_fake_async_client(
        monkeypatch,
        response=_FakeResponse(["not-a-dict"]),
    )

    with pytest.raises(payments_activation.AppleVerifyTransportError):
        await payments_activation._call_apple_verify_endpoint(
            payments_activation.APPLE_VERIFY_PRODUCTION_URL,
            "receipt-data-validated-12345",
        )


def test_normalize_apple_verification_handles_provider_expired_status() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": payments_activation.APPLE_EXPIRED_RECEIPT_STATUS,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": "946684800000",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is False
    assert response.verification_state is AppleVerificationState.expired
    assert response.error is not None
    assert response.error.code == "APPLE_RECEIPT_EXPIRED"


def test_normalize_apple_verification_rejects_missing_receipt_entries() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={"status": 0},
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is False
    assert response.verification_state is AppleVerificationState.invalid
    assert response.error is not None
    assert response.error.code == "APPLE_RECEIPT_INVALID"


def test_normalize_apple_verification_rejects_unknown_product() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.enterprise.monthly",
                    "expires_date_ms": "4102444800000",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is False
    assert response.verification_state is AppleVerificationState.invalid
    assert response.error is not None
    assert response.error.code == "APPLE_RECEIPT_INVALID"


def test_normalize_apple_verification_keeps_renewal_active_without_restore_signal() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": "4102444800000",
                    "transaction_id": "txn-renewal-2",
                    "original_transaction_id": "txn-original-1",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is True
    assert response.verification_state is AppleVerificationState.active


def test_normalize_apple_verification_uses_restored_only_for_explicit_signal() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": 0,
            "restore_detected": True,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": "4102444800000",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is True
    assert response.verification_state is AppleVerificationState.restored


def test_normalize_apple_verification_accepts_restored_marker_alias() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": 0,
            "restored": True,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": "4102444800000",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is True
    assert response.verification_state is AppleVerificationState.restored


@pytest.mark.parametrize("marker", ["restore_detected", "restored"])
def test_has_reliable_restore_signal_accepts_entry_markers(marker: str) -> None:
    assert payments_activation._has_reliable_restore_signal({}, {marker: True}) is True


def test_normalize_apple_verification_rejects_cancelled_receipt() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date_ms": "4102444800000",
                    "cancellation_date": "2026-03-08T00:00:00Z",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is False
    assert response.verification_state is AppleVerificationState.invalid
    assert response.error is not None
    assert response.error.code == "APPLE_RECEIPT_INVALID"
    assert response.expires_at == datetime.fromtimestamp(4102444800000 / 1000.0, tz=timezone.utc)


def test_normalize_apple_verification_rejects_unparseable_expiry_field() -> None:
    response = payments_activation._normalize_apple_verification(
        payload={
            "status": 0,
            "latest_receipt_info": [
                {
                    "product_id": "com.pulseplate.premium.monthly",
                    "expires_date": "definitely-not-a-supported-apple-date",
                }
            ],
        },
        environment=AppleVerificationEnvironment.production,
    )

    assert response.verified is False
    assert response.verification_state is AppleVerificationState.invalid
    assert response.error is not None
    assert response.error.code == "APPLE_RECEIPT_INVALID"
    assert response.expires_at is None
