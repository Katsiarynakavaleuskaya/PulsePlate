from __future__ import annotations

import pytest

from app.services import payments_activation
from settings import require_apple_shared_secret, validate_apple_receipt_verification_config


def test_require_apple_shared_secret_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="APPLE_SHARED_SECRET is required"):
        require_apple_shared_secret()


def test_apple_request_body_requires_shared_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_secret = "StrongAppleSharedSecretForTests123456789!"  # pragma: allowlist secret
    monkeypatch.setenv("APPLE_SHARED_SECRET", shared_secret)

    payload = payments_activation._apple_request_body("receipt-data-validated-12345")

    assert payload == {
        "receipt-data": "receipt-data-validated-12345",
        "password": shared_secret,
        "exclude-old-transactions": True,
    }


def test_validate_apple_receipt_verification_config_allows_test_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    validate_apple_receipt_verification_config()


def test_validate_apple_receipt_verification_config_requires_secret_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="APPLE_SHARED_SECRET is required"):
        validate_apple_receipt_verification_config()
