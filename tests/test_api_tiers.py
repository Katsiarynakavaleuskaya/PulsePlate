"""Tests for API tier validation middleware.

RU: Тесты для промежуточного ПО проверки уровней API.
EN: Tests for API tier validation middleware.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.middleware.api_tiers import (
    SubscriptionTier,
    TEST_KEY_PRO,
    TEST_KEY_VIP,
    _validate_api_key_tier,
    get_subscription_tier,
    require_pro_tier,
    require_vip_tier,
)


class TestSubscriptionTier:
    """Test SubscriptionTier enum."""

    def test_tier_values(self) -> None:
        """Test tier enum has correct values."""
        assert SubscriptionTier.FREE == "FREE"
        assert SubscriptionTier.PRO == "PRO"
        assert SubscriptionTier.VIP == "VIP"


class TestValidateAPIKeyTier:
    """Test _validate_api_key_tier function."""

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_vip_key_grants_vip_access(self) -> None:
        """Test VIP key grants VIP access in development."""
        assert _validate_api_key_tier(TEST_KEY_VIP, SubscriptionTier.VIP) is True

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_vip_key_grants_pro_access(self) -> None:
        """Test VIP key also grants PRO access (VIP includes PRO)."""
        assert _validate_api_key_tier(TEST_KEY_VIP, SubscriptionTier.PRO) is True

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_pro_key_grants_pro_access(self) -> None:
        """Test PRO key grants PRO access in development."""
        assert _validate_api_key_tier(TEST_KEY_PRO, SubscriptionTier.PRO) is True

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_pro_key_denies_vip_access(self) -> None:
        """Test PRO key does NOT grant VIP access."""
        assert _validate_api_key_tier(TEST_KEY_PRO, SubscriptionTier.VIP) is False

    @patch.dict(
        os.environ, {"APP_ENV": "local", "DEBUG": "true", "ALLOW_ANONYMOUS_API_KEYS": "true"}
    )
    def test_anonymous_allowed_in_dev(self) -> None:
        """Test any key accepted when ALLOW_ANONYMOUS_API_KEYS=true in dev."""
        assert _validate_api_key_tier("any_random_key", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("any_random_key", SubscriptionTier.VIP) is True

    @patch.dict(
        os.environ, {"APP_ENV": "production", "DEBUG": "false", "SUBSCRIPTION_DB_ENABLED": "false"}
    )
    def test_production_mode_raises_not_implemented(self) -> None:
        """Test production mode raises NotImplementedError when DB not enabled."""
        with pytest.raises(NotImplementedError, match="API key validation not implemented"):
            _validate_api_key_tier(TEST_KEY_VIP, SubscriptionTier.VIP)
        with pytest.raises(NotImplementedError, match="API key validation not implemented"):
            _validate_api_key_tier(TEST_KEY_PRO, SubscriptionTier.PRO)

    @patch.dict(
        os.environ,
        {"APP_ENV": "production", "DEBUG": "false", "SUBSCRIPTION_DB_ENABLED": "true"},
    )
    def test_production_db_enabled_raises_lookup_not_implemented(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test production mode with DB enabled reaches the lookup placeholder path."""
        caplog.set_level("ERROR")
        with pytest.raises(
            NotImplementedError, match="Subscription database lookup not implemented"
        ):
            _validate_api_key_tier("prod_key", SubscriptionTier.PRO)
        assert "Subscription database lookup not implemented" in caplog.text


class TestRequireProTier:
    """Test require_pro_tier dependency function."""

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    @pytest.mark.asyncio
    async def test_pro_key_accepted(self) -> None:
        """Test PRO key is accepted for PRO tier."""
        result = await require_pro_tier(x_api_key=TEST_KEY_PRO)
        assert result == TEST_KEY_PRO

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    @pytest.mark.asyncio
    async def test_vip_key_accepted_for_pro(self) -> None:
        """Test VIP key is accepted for PRO tier (VIP includes PRO)."""
        result = await require_pro_tier(x_api_key=TEST_KEY_VIP)
        assert result == TEST_KEY_VIP

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self) -> None:
        """Test missing API key raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            await require_pro_tier(x_api_key=None)
        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    @pytest.mark.asyncio
    async def test_invalid_key_raises_403(self) -> None:
        """Test invalid API key raises 403 Forbidden."""
        with pytest.raises(HTTPException) as exc_info:
            await require_pro_tier(x_api_key="invalid_key")
        assert exc_info.value.status_code == 403
        assert "does not have PRO tier access" in exc_info.value.detail


class TestRequireVIPTier:
    """Test require_vip_tier dependency function."""

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    @pytest.mark.asyncio
    async def test_vip_key_accepted(self) -> None:
        """Test VIP key is accepted for VIP tier."""
        result = await require_vip_tier(x_api_key=TEST_KEY_VIP)
        assert result == TEST_KEY_VIP

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    @pytest.mark.asyncio
    async def test_pro_key_rejected_for_vip(self) -> None:
        """Test PRO key is rejected for VIP tier."""
        with pytest.raises(HTTPException) as exc_info:
            await require_vip_tier(x_api_key=TEST_KEY_PRO)
        assert exc_info.value.status_code == 403
        assert "does not have VIP tier access" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self) -> None:
        """Test missing API key raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            await require_vip_tier(x_api_key=None)
        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    @pytest.mark.asyncio
    async def test_invalid_key_raises_403(self) -> None:
        """Test invalid API key raises 403 Forbidden."""
        with pytest.raises(HTTPException) as exc_info:
            await require_vip_tier(x_api_key="invalid_key")
        assert exc_info.value.status_code == 403
        assert "Upgrade to VIP" in exc_info.value.detail


class TestGetSubscriptionTier:
    """Test get_subscription_tier helper function."""

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_vip_key_returns_vip_tier(self) -> None:
        """Test VIP key returns VIP tier."""
        assert get_subscription_tier(TEST_KEY_VIP) == SubscriptionTier.VIP

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_pro_key_returns_pro_tier(self) -> None:
        """Test PRO key returns PRO tier."""
        assert get_subscription_tier(TEST_KEY_PRO) == SubscriptionTier.PRO

    @patch.dict(os.environ, {"APP_ENV": "local", "DEBUG": "true"})
    def test_invalid_key_returns_free_tier(self) -> None:
        """Test invalid key returns FREE tier."""
        assert get_subscription_tier("invalid_key") == SubscriptionTier.FREE

    @patch.dict(
        os.environ, {"APP_ENV": "production", "DEBUG": "false", "SUBSCRIPTION_DB_ENABLED": "false"}
    )
    def test_production_raises_not_implemented(self) -> None:
        """Test production mode raises NotImplementedError when DB not enabled."""
        # Database not implemented yet, should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            get_subscription_tier(TEST_KEY_VIP)
        with pytest.raises(NotImplementedError):
            get_subscription_tier(TEST_KEY_PRO)


class TestEnvironmentConfiguration:
    """Test environment configuration handling."""

    @patch.dict(os.environ, {"APP_ENV": "local"})
    def test_local_env_not_production(self) -> None:
        """Test local environment is not production."""
        from app.middleware.api_tiers import _is_production_environment

        is_prod, env = _is_production_environment()
        assert is_prod is False
        assert env == "local"

    @patch.dict(os.environ, {"APP_ENV": "production", "DEBUG": "false"})
    def test_production_env_is_production(self) -> None:
        """Test production environment is detected."""
        from app.middleware.api_tiers import _is_production_environment

        is_prod, env = _is_production_environment()
        assert is_prod is True
        assert env == "production"

    @patch.dict(os.environ, {"APP_ENV": "staging", "DEBUG": "false"})
    def test_staging_env_is_production(self) -> None:
        """Test staging environment is treated as production."""
        from app.middleware.api_tiers import _is_production_environment

        is_prod, env = _is_production_environment()
        assert is_prod is True
        assert env == "staging"
