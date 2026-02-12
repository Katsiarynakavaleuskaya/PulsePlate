"""Tests for API tier validation middleware.

RU: Тесты для промежуточного ПО проверки уровней API.
EN: Tests for API tier validation middleware.
"""

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
    get_current_user,
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

    def test_vip_key_grants_vip_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP key grants VIP access in development."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert _validate_api_key_tier(TEST_KEY_VIP, SubscriptionTier.VIP) is True

    def test_vip_key_grants_pro_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP key also grants PRO access (VIP includes PRO)."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert _validate_api_key_tier(TEST_KEY_VIP, SubscriptionTier.PRO) is True

    def test_pro_key_grants_pro_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PRO key grants PRO access in development."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert _validate_api_key_tier(TEST_KEY_PRO, SubscriptionTier.PRO) is True

    def test_pro_key_denies_vip_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PRO key does NOT grant VIP access."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert _validate_api_key_tier(TEST_KEY_PRO, SubscriptionTier.VIP) is False

    def test_anonymous_allowed_in_dev(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test any key accepted when ALLOW_ANONYMOUS_API_KEYS=true in dev."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")
        assert _validate_api_key_tier("any_random_key", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("any_random_key", SubscriptionTier.VIP) is True

    def test_production_mode_without_db_uses_env_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test production mode falls back to env-based detection when DB is disabled."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
        monkeypatch.setenv("VIP_API_KEYS", "prod_key")  # pragma: allowlist secret
        assert _validate_api_key_tier("prod_key", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("prod_key", SubscriptionTier.VIP) is True

    def test_production_mode_without_db_resolves_pro_api_keys_csv(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test production env fallback resolves PRO_API_KEYS CSV with whitespace."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
        monkeypatch.setenv("PRO_API_KEYS", "  pro_key_a , pro_key_b  ")  # pragma: allowlist secret
        assert _validate_api_key_tier("pro_key_a", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("pro_key_b", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("pro_key_b", SubscriptionTier.VIP) is False

    def test_production_mode_blocks_test_keys_in_env_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test production env fallback does not accept hardcoded test keys."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
        assert _validate_api_key_tier(TEST_KEY_PRO, SubscriptionTier.PRO) is False
        assert _validate_api_key_tier(TEST_KEY_VIP, SubscriptionTier.VIP) is False

    def test_production_db_enabled_uses_db_lookup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test production mode with DB enabled validates access via DB tier."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.HIT, tier=SubscriptionTier.PRO),
        )
        assert _validate_api_key_tier("prodtoken", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("prodtoken", SubscriptionTier.VIP) is False

    def test_production_db_error_does_not_fallback_to_env_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB lookup error path denies access instead of env fallback."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("VIP_API_KEYS", "env_fallback_key")  # pragma: allowlist secret
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.ERROR),
        )
        assert _validate_api_key_tier("env_fallback_key", SubscriptionTier.VIP) is False
        assert _validate_api_key_tier("unknown_key", SubscriptionTier.PRO) is False

    def test_production_db_invalid_tier_does_not_fallback_to_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB lookup INVALID_TIER denies access (fail-closed), no env fallback."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("VIP_API_KEYS", "env_key")  # pragma: allowlist secret
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.INVALID_TIER),
        )
        assert _validate_api_key_tier("env_key", SubscriptionTier.VIP) is False

    def test_production_db_miss_falls_back_to_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test DB MISS allows env fallback (migration path)."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("PRO_API_KEYS", "miss_then_env_key")  # pragma: allowlist secret
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.MISS),
        )
        assert _validate_api_key_tier("miss_then_env_key", SubscriptionTier.PRO) is True
        assert _validate_api_key_tier("miss_then_env_key", SubscriptionTier.VIP) is False


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
        """Test _lookup_tier_from_db returns DBLookupResult with status ERROR on DB/session exceptions."""
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
        """Test _lookup_tier_from_db returns DBLookupResult with status MISS when no record is found."""
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
        """Test _lookup_tier_from_db returns DBLookupResult with status INVALID_TIER for unknown tier values."""
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
    """Test require_pro_tier dependency function (sync, runs in threadpool in FastAPI)."""

    def test_pro_key_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PRO key is accepted for PRO tier."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        result = require_pro_tier(x_api_key=TEST_KEY_PRO)
        assert result == TEST_KEY_PRO

    def test_vip_key_accepted_for_pro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP key is accepted for PRO tier (VIP includes PRO)."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        result = require_pro_tier(x_api_key=TEST_KEY_VIP)
        assert result == TEST_KEY_VIP

    def test_missing_key_raises_401(self) -> None:
        """Test missing API key raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            require_pro_tier(x_api_key=None)
        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    def test_invalid_key_raises_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid API key raises 403 Forbidden."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        with pytest.raises(HTTPException) as exc_info:
            require_pro_tier(x_api_key="invalid_key")
        assert exc_info.value.status_code == 403
        assert "does not have PRO tier access" in exc_info.value.detail


class TestRequireVIPTier:
    """Test require_vip_tier dependency function (sync, runs in threadpool in FastAPI)."""

    def test_vip_key_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP key is accepted for VIP tier."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        result = require_vip_tier(x_api_key=TEST_KEY_VIP)
        assert result == TEST_KEY_VIP

    def test_pro_key_rejected_for_vip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PRO key is rejected for VIP tier."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        with pytest.raises(HTTPException) as exc_info:
            require_vip_tier(x_api_key=TEST_KEY_PRO)
        assert exc_info.value.status_code == 403
        assert "does not have VIP tier access" in exc_info.value.detail

    def test_missing_key_raises_403(self) -> None:
        """Test missing API key raises 403 Forbidden (VIP = feature-gate)."""
        with pytest.raises(HTTPException) as exc_info:
            require_vip_tier(x_api_key=None)
        assert exc_info.value.status_code == 403
        assert "VIP access" in exc_info.value.detail or "API key required" in exc_info.value.detail

    def test_invalid_key_raises_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid API key raises 403 Forbidden."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        with pytest.raises(HTTPException) as exc_info:
            require_vip_tier(x_api_key="invalid_key")
        assert exc_info.value.status_code == 403
        assert "Upgrade to VIP" in exc_info.value.detail


class TestGetSubscriptionTier:
    """Test get_subscription_tier helper function."""

    def test_vip_key_returns_vip_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP key returns VIP tier."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert get_subscription_tier(TEST_KEY_VIP) == SubscriptionTier.VIP

    def test_pro_key_returns_pro_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PRO key returns PRO tier."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert get_subscription_tier(TEST_KEY_PRO) == SubscriptionTier.PRO

    def test_invalid_key_returns_free_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid key returns FREE tier."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        assert get_subscription_tier("invalid_key") == SubscriptionTier.FREE

    def test_production_db_disabled_uses_env_detection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test production mode with DB disabled uses env keys (not test keys)."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
        monkeypatch.setenv("VIP_API_KEYS", "vip_prod")  # pragma: allowlist secret
        monkeypatch.setenv(
            "PRO_API_KEYS", "  pro_prod_a , pro_prod_b  "
        )  # pragma: allowlist secret
        assert get_subscription_tier("vip_prod") == SubscriptionTier.VIP
        assert get_subscription_tier("pro_prod_a") == SubscriptionTier.PRO
        assert get_subscription_tier("pro_prod_b") == SubscriptionTier.PRO
        assert get_subscription_tier(TEST_KEY_VIP) == SubscriptionTier.FREE
        assert get_subscription_tier(TEST_KEY_PRO) == SubscriptionTier.FREE

    def test_production_db_enabled_uses_db_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_subscription_tier returns DB tier when available."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.HIT, tier=SubscriptionTier.VIP),
        )
        assert get_subscription_tier("db_key") == SubscriptionTier.VIP

    def test_production_db_enabled_falls_back_to_env_on_db_miss(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_subscription_tier falls back to env only when DB lookup misses."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("VIP_API_KEYS", "env_key")  # pragma: allowlist secret
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.MISS),
        )
        assert get_subscription_tier("env_key") == SubscriptionTier.VIP
        assert get_subscription_tier("unknown_key") == SubscriptionTier.FREE

    def test_production_db_error_returns_free_without_env_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DB errors are fail-closed for tier inference when DB mode is enabled."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("VIP_API_KEYS", "env_key")  # pragma: allowlist secret
        monkeypatch.setattr(
            api_tiers_mod,
            "_lookup_tier_from_db",
            lambda _: DBLookupResult(status=DBLookupStatus.ERROR),
        )
        assert get_subscription_tier("env_key") == SubscriptionTier.FREE


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_returns_derived_user(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_current_user returns CurrentUser with derived subject_id and api_key."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DEBUG", "true")
        user = await get_current_user(api_key=TEST_KEY_PRO)
        assert user.api_key == TEST_KEY_PRO
        assert user.user_id == derive_subject_id_from_api_key(TEST_KEY_PRO)


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

    def test_local_env_not_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test local environment is not production."""
        monkeypatch.setenv("APP_ENV", "local")
        from app.middleware.api_tiers import _is_production_environment

        is_prod, env = _is_production_environment()
        assert is_prod is False
        assert env == "local"

    def test_production_env_is_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test production environment is detected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        from app.middleware.api_tiers import _is_production_environment

        is_prod, env = _is_production_environment()
        assert is_prod is True
        assert env == "production"

    def test_staging_env_is_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test staging environment is treated as production."""
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("DEBUG", "false")
        from app.middleware.api_tiers import _is_production_environment

        is_prod, env = _is_production_environment()
        assert is_prod is True
        assert env == "staging"
