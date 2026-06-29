"""Guard manual billing transport auth away from legacy tier-key fallbacks."""

from __future__ import annotations

from fastapi import HTTPException
import pytest

from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP
from app.routers import billing
from app.routers.api_key import validate_app_api_key


def test_manual_billing_transport_uses_canonical_app_api_key_validator() -> None:
    assert billing._get_effective_manual_billing_key_validator() is validate_app_api_key


@pytest.mark.parametrize("tier_key", [TEST_KEY_PRO, TEST_KEY_VIP])
def test_manual_billing_transport_rejects_tier_keys_under_strict_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tier_key: str,
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    validator = billing._get_effective_manual_billing_key_validator()

    assert validator("test_key") == "test_key"
    with pytest.raises(HTTPException) as exc_info:
        validator(tier_key)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid API Key"
