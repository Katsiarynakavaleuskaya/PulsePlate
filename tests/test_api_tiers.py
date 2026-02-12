"""Tests for API tier validation middleware.

RU: Тесты для промежуточного ПО проверки уровней API.
EN: Tests for API tier validation middleware.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import app.middleware.api_tiers as api_tiers_mod
from app.middleware.api_tiers import (
    DBLookupResult,
    DBLookupStatus,
    CurrentUser,
    SubscriptionTier,
    TEST_KEY_PRO,
    TEST_KEY_VIP,
    _validate_api_key_tier,
    derive_subject_id_from_api_key,
    get_pro_subject_id,
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
        os.environ,
        {
            "APP_ENV": "production",
            "DEBUG": "false",
            "SUBSCRIPTION_DB_ENABLED": "false",
            "VIP_API_KEYS": "prod_key",  # pragma: allowlist secret
        },
        clear=False,
    )
    def test_production_mode_without_db_uses_env_fallback(self) -> None:
        """Test production mode falls back to env-based detection when DB is disabled."""
        assert _validate_api_key_tier("prod_key", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("prod_key", SubscriptionTier.VIP) is True

    @patch.dict(
        os.environ,
        {"APP_ENV": "production", "DEBUG": "false", "SUBSCRIPTION_DB_ENABLED": "true"},
    )
    def test_production_db_enabled_uses_db_lookup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test production mode with DB enabled validates access via DB tier."""
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.HIT, tier=SubscriptionTier.PRO),
        )
        assert _validate_api_key_tier("prodtoken", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("prodtoken", SubscriptionTier.VIP) is False

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "DEBUG": "false",
            "SUBSCRIPTION_DB_ENABLED": "true",
            "VIP_API_KEYS": "env_fallback_key",  # pragma: allowlist secret
        },
        clear=False,
    )
    def test_production_db_error_does_not_fallback_to_env_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB lookup error path denies access instead of env fallback."""
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.ERROR),
        )
        assert _validate_api_key_tier("env_fallback_key", SubscriptionTier.VIP) is False
        assert _validate_api_key_tier("unknown_key", SubscriptionTier.PRO) is False


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    def __init__(self, value: object) -> None:
        self._value = value
        self.closed = False

    def execute(self, _query: object, _params: dict[str, str]) -> _FakeResult:
        return _FakeResult(self._value)

    def close(self) -> None:
        self.closed = True


class TestDBLookupHelpers:
    """Test low-level DB tier lookup helpers."""

    def test_tier_allows_access_helper(self) -> None:
        """Test tier inclusion matrix helper."""
        assert api_tiers_mod._tier_allows_access(SubscriptionTier.VIP, SubscriptionTier.PRO) is True
        assert (
            api_tiers_mod._tier_allows_access(SubscriptionTier.PRO, SubscriptionTier.VIP) is False
        )
        assert (
            api_tiers_mod._tier_allows_access(SubscriptionTier.FREE, SubscriptionTier.FREE) is True
        )

    def test_parse_tier_value(self) -> None:
        """Test tier parsing from raw values."""
        assert api_tiers_mod._parse_tier_value(" vip ") == SubscriptionTier.VIP
        assert api_tiers_mod._parse_tier_value("PRO") == SubscriptionTier.PRO
        assert api_tiers_mod._parse_tier_value("unknown") is None

    def test_lookup_tier_from_db_handles_db_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB lookup returns None on DB/session exceptions."""
        import core.db as core_db

        def _boom() -> object:
            raise RuntimeError("db down")

        monkeypatch.setattr(core_db, "get_session_factory", _boom)
        result = api_tiers_mod._lookup_tier_from_db("key")
        assert result.status == DBLookupStatus.ERROR
        assert result.tier is None

    def test_lookup_tier_from_db_handles_missing_record(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB lookup returns None when no record is found."""
        import core.db as core_db

        session = _FakeSession(None)
        monkeypatch.setattr(core_db, "get_session_factory", lambda: lambda: session)
        result = api_tiers_mod._lookup_tier_from_db("key")
        assert result.status == DBLookupStatus.MISS
        assert result.tier is None
        assert session.closed is True

    def test_lookup_tier_from_db_handles_unknown_tier_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB lookup returns None for unknown tier string values."""
        import core.db as core_db

        session = _FakeSession("not_a_tier")
        monkeypatch.setattr(core_db, "get_session_factory", lambda: lambda: session)
        result = api_tiers_mod._lookup_tier_from_db("key")
        assert result.status == DBLookupStatus.INVALID_TIER
        assert result.tier is None
        assert session.closed is True

    def test_lookup_tier_from_db_returns_parsed_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test DB lookup returns parsed tier for valid DB value."""
        import core.db as core_db

        session = _FakeSession("VIP")
        monkeypatch.setattr(core_db, "get_session_factory", lambda: lambda: session)
        result = api_tiers_mod._lookup_tier_from_db("key")
        assert result.status == DBLookupStatus.HIT
        assert result.tier == SubscriptionTier.VIP
        assert session.closed is True


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
    async def test_missing_key_raises_403(self) -> None:
        """Test missing API key raises 403 Forbidden (VIP = feature-gate)."""
        with pytest.raises(HTTPException) as exc_info:
            await require_vip_tier(x_api_key=None)
        assert exc_info.value.status_code == 403
        assert "VIP access" in exc_info.value.detail or "API key required" in exc_info.value.detail

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
        os.environ,
        {"APP_ENV": "production", "DEBUG": "false", "SUBSCRIPTION_DB_ENABLED": "false"},
        clear=False,
    )
    def test_production_db_disabled_uses_env_detection(self) -> None:
        """Test production mode with DB disabled uses env/test-key detection."""
        assert get_subscription_tier(TEST_KEY_VIP) == SubscriptionTier.VIP
        assert get_subscription_tier(TEST_KEY_PRO) == SubscriptionTier.PRO

    @patch.dict(
        os.environ,
        {"APP_ENV": "production", "DEBUG": "false", "SUBSCRIPTION_DB_ENABLED": "true"},
    )
    def test_production_db_enabled_uses_db_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_subscription_tier returns DB tier when available."""
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.HIT, tier=SubscriptionTier.VIP),
        )
        assert get_subscription_tier("db_key") == SubscriptionTier.VIP

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "DEBUG": "false",
            "SUBSCRIPTION_DB_ENABLED": "true",
            "VIP_API_KEYS": "env_key",  # pragma: allowlist secret
        },
        clear=False,
    )
    def test_production_db_enabled_falls_back_to_env_on_db_miss(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_subscription_tier falls back to env only when DB lookup misses."""
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.MISS),
        )
        assert get_subscription_tier("env_key") == SubscriptionTier.VIP
        assert get_subscription_tier("unknown_key") == SubscriptionTier.FREE

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "DEBUG": "false",
            "SUBSCRIPTION_DB_ENABLED": "true",
            "VIP_API_KEYS": "env_key",  # pragma: allowlist secret
        },
        clear=False,
    )
    def test_production_db_error_returns_free_without_env_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB errors are fail-closed for tier inference when DB mode is enabled."""
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.ERROR),
        )
        assert get_subscription_tier("env_key") == SubscriptionTier.FREE


class TestGetProSubjectId:
    """Test get_pro_subject_id helper."""

    @pytest.mark.asyncio
    async def test_get_pro_subject_id_returns_current_user_id(self) -> None:
        """Test helper returns subject ID from current user."""
        current_user = CurrentUser(user_id=123, api_key="test_key")
        assert await get_pro_subject_id(current_user=current_user) == 123


class TestDeriveSubjectIdFromApiKey:
    """Tests for derive_subject_id_from_api_key."""

    def test_same_key_is_deterministic(self) -> None:
        """Test same key produces stable subject IDs."""
        key = "deterministic-key"
        assert derive_subject_id_from_api_key(key) == derive_subject_id_from_api_key(key)

    def test_different_keys_are_unique(self) -> None:
        """Test different keys produce different subject IDs."""
        first = derive_subject_id_from_api_key("key-one")
        second = derive_subject_id_from_api_key("key-two")
        assert first != second

    def test_subject_id_within_positive_int64(self) -> None:
        """Test subject ID is positive int64 within allowed range."""
        subject_id = derive_subject_id_from_api_key("range-check")
        assert 1 <= subject_id <= 0x7FFF_FFFF_FFFF_FFFF


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
