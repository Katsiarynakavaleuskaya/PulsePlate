from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

import app.middleware.api_tiers as api_tiers_mod
from app.middleware.api_tiers import (
    DBLookupStatus,
    SubscriptionTier,
    TEST_KEY_PRO,
    TEST_KEY_VIP,
    derive_subject_id_from_api_key,
    get_subscription_tier,
)
from app.models import Subscription
from app.services import payments_activation
from core import db as core_db


@pytest.fixture(autouse=True)
def _reset_subscription_state(configure_sqlite_database: object) -> None:
    """Reset persisted billing state between tests."""

    payments_activation.reset_state()


def _persist_subscription(
    *,
    api_key: str,
    source: str,
    tier: str,
    status: str,
    expires_at: datetime | None = None,
) -> None:
    """Insert a persisted subscription row for DB-backed authz tests."""

    session_factory = core_db.get_session_factory()
    session = session_factory()
    now = datetime.now(timezone.utc)
    try:
        session.add(
            Subscription(
                id=str(uuid4()),
                user_id=derive_subject_id_from_api_key(api_key),
                source=source,
                tier=tier,
                status=status,
                platform="ios",
                source_reference=f"{source}:{api_key}",
                product_id=f"com.pulseplate.{tier}.monthly",
                expires_at=expires_at,
                activated_at=now if status == "active" else None,
            )
        )
        session.commit()
    finally:
        session.close()


def test_lookup_tier_from_db_returns_highest_active_entitlement() -> None:
    """VIP must win when multiple active persisted subscriptions exist."""

    future = datetime.now(timezone.utc) + timedelta(days=14)
    _persist_subscription(
        api_key=TEST_KEY_VIP,
        source="ios_app_store",
        tier="pro",
        status="active",
        expires_at=future,
    )
    _persist_subscription(
        api_key=TEST_KEY_VIP,
        source="swift_manual",
        tier="vip",
        status="active",
        expires_at=future,
    )

    result = api_tiers_mod._lookup_tier_from_db(TEST_KEY_VIP)
    assert result.status == DBLookupStatus.HIT
    assert result.tier == SubscriptionTier.VIP


def test_lookup_tier_from_db_returns_free_for_non_active_entitlements() -> None:
    """Persisted non-active rows must authoritatively deny paid access."""

    past = datetime.now(timezone.utc) - timedelta(days=1)
    _persist_subscription(
        api_key=TEST_KEY_PRO,
        source="ios_app_store",
        tier="pro",
        status="expired",
        expires_at=past,
    )
    _persist_subscription(
        api_key=TEST_KEY_PRO,
        source="erip_qr",
        tier="vip",
        status="pending_manual_review",
    )

    result = api_tiers_mod._lookup_tier_from_db(TEST_KEY_PRO)
    assert result.status == DBLookupStatus.HIT
    assert result.tier == SubscriptionTier.FREE


def test_lookup_tier_from_db_parses_free_tier_and_normalizes_aware_expiry() -> None:
    """Aware datetimes must normalize to UTC and a persisted free tier must stay free."""

    future = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3))) + timedelta(days=2)
    _persist_subscription(
        api_key="free-tier-user",  # pragma: allowlist secret
        source="ios_app_store",
        tier="free",
        status="active",
        expires_at=future,
    )

    result = api_tiers_mod._lookup_tier_from_db("free-tier-user")
    assert result.status == DBLookupStatus.HIT
    assert result.tier == SubscriptionTier.FREE


def test_lookup_tier_from_db_ignores_active_rows_that_are_already_expired() -> None:
    """An active row with past expiry must not unlock paid access."""

    past = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5))) - timedelta(days=2)
    _persist_subscription(
        api_key="expired-active-user",  # pragma: allowlist secret
        source="ios_app_store",
        tier="vip",
        status="active",
        expires_at=past,
    )

    result = api_tiers_mod._lookup_tier_from_db("expired-active-user")
    assert result.status == DBLookupStatus.HIT
    assert result.tier == SubscriptionTier.FREE


def test_lookup_tier_from_db_returns_invalid_tier_for_malformed_rows() -> None:
    """Malformed persisted tier/state rows must fail closed."""

    _persist_subscription(
        api_key="malformed-subscription-key",  # pragma: allowlist secret
        source="ios_app_store",
        tier="enterprise",
        status="active",
    )

    result = api_tiers_mod._lookup_tier_from_db("malformed-subscription-key")
    assert result.status == DBLookupStatus.INVALID_TIER
    assert result.tier is None


def test_lookup_tier_from_db_returns_invalid_tier_for_malformed_status() -> None:
    """Malformed persisted status rows must fail closed."""

    _persist_subscription(
        api_key="malformed-status-key",  # pragma: allowlist secret
        source="ios_app_store",
        tier="pro",
        status="waiting_for_review",
    )

    result = api_tiers_mod._lookup_tier_from_db("malformed-status-key")
    assert result.status == DBLookupStatus.INVALID_TIER
    assert result.tier is None


def test_lookup_tier_from_db_fails_closed_for_mixed_valid_and_malformed_rows() -> None:
    """Mixed persisted rows must deny paid access when any row is malformed."""

    future = datetime.now(timezone.utc) + timedelta(days=14)
    _persist_subscription(
        api_key="mixed-malformed-key",  # pragma: allowlist secret
        source="ios_app_store",
        tier="vip",
        status="active",
        expires_at=future,
    )
    _persist_subscription(
        api_key="mixed-malformed-key",  # pragma: allowlist secret
        source="swift_manual",
        tier="enterprise",
        status="active",
        expires_at=future,
    )

    result = api_tiers_mod._lookup_tier_from_db("mixed-malformed-key")
    assert result.status == DBLookupStatus.INVALID_TIER
    assert result.tier is None


def test_get_subscription_tier_is_fail_closed_on_db_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DB-backed tier resolution must not fall back to env/test keys on MISS."""

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
    monkeypatch.setenv("PRO_API_KEYS", TEST_KEY_PRO)  # pragma: allowlist secret
    monkeypatch.setenv("VIP_API_KEYS", TEST_KEY_VIP)  # pragma: allowlist secret

    assert get_subscription_tier(TEST_KEY_PRO) == SubscriptionTier.FREE
    assert get_subscription_tier(TEST_KEY_VIP) == SubscriptionTier.FREE
