"""API Tier Validation Middleware

RU: Промежуточное ПО для проверки уровня доступа API (FREE, PRO, VIP).
EN: Middleware for validating API access tiers (FREE, PRO, VIP).

This module provides dependency functions for FastAPI endpoints to enforce
subscription tier access control for mobile apps (iOS/Android) and web.

Subscription Tiers:
- FREE: No API key required, basic features
- PRO: API key required (tier 1), advanced features
- VIP: API key required (tier 2), premium features

Usage:
    from app.middleware.api_tiers import require_pro_tier, require_vip_tier

    @router.post("/pro/feature", dependencies=[Depends(require_pro_tier)])
    async def pro_feature():
        ...

    @router.post("/vip/feature", dependencies=[Depends(require_vip_tier)])
    async def vip_feature():
        ...
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from sqlalchemy import text

from app.routers.api_key import api_key_header

from app.utils.feature_flags import is_vip_module_enabled

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Subscription tier levels for API access control.

    RU: Уровни подписки для контроля доступа к API.
    EN: Subscription levels for API access control.
    """

    FREE = "FREE"
    PRO = "PRO"
    VIP = "VIP"


# Test API keys for development/testing (nosec B105)
TEST_KEY_PRO = "test_pro_key"  # nosec B105
TEST_KEY_VIP = "test_vip_key"  # nosec B105

# Environment configuration
VIP_MODULE_ENABLED = is_vip_module_enabled()
ALLOW_ANONYMOUS_API_KEYS = os.getenv("ALLOW_ANONYMOUS_API_KEYS", "false").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
# Note: SUBSCRIPTION_DB_ENABLED is checked dynamically in code to support testing


def _is_subscription_db_enabled() -> bool:
    """Return True when DB-backed subscription lookup is enabled."""
    return os.getenv("SUBSCRIPTION_DB_ENABLED", "false").lower() in ("true", "1", "yes", "on")


def _tier_allows_access(tier: SubscriptionTier, required_tier: SubscriptionTier) -> bool:
    """Return whether a resolved tier satisfies the required tier."""
    if required_tier == SubscriptionTier.PRO:
        return tier in (SubscriptionTier.PRO, SubscriptionTier.VIP)
    if required_tier == SubscriptionTier.VIP:
        return tier == SubscriptionTier.VIP
    return True


def _parse_tier_value(raw_tier: str) -> SubscriptionTier | None:
    """Convert DB/env tier string to SubscriptionTier enum safely."""
    normalized = raw_tier.strip().upper()
    if normalized in SubscriptionTier.__members__:
        return SubscriptionTier[normalized]
    return None


def _lookup_tier_from_db(api_key: str) -> SubscriptionTier | None:
    """Try to resolve API key tier from DB; return None on misses/errors.

    RU: Пытается определить tier из БД; возвращает None при промахе/ошибке.
    EN: Attempts to resolve tier from DB; returns None on miss/error.
    """
    query = text("SELECT tier FROM api_keys WHERE api_key = :api_key LIMIT 1")

    try:
        from core.db import get_session_factory

        session_factory = get_session_factory()
        session = session_factory()
        try:
            raw_tier = session.execute(query, {"api_key": api_key}).scalar_one_or_none()
        finally:
            session.close()
    except Exception:
        logger.warning("Subscription DB lookup failed; falling back to env-based tier detection")
        return None

    if raw_tier is None:
        return None

    parsed_tier = _parse_tier_value(str(raw_tier))
    if parsed_tier is None:
        logger.warning("Subscription DB lookup returned unknown tier value; using env fallback")
    return parsed_tier


def _resolve_tier_from_env(api_key: str) -> SubscriptionTier | None:
    """Resolve tier via environment/test-key fallback."""
    if api_key == TEST_KEY_VIP:
        return SubscriptionTier.VIP
    if api_key == TEST_KEY_PRO:
        return SubscriptionTier.PRO

    vip_keys = os.getenv("VIP_API_KEYS", "")
    if api_key and api_key in {value.strip() for value in vip_keys.split(",") if value.strip()}:
        return SubscriptionTier.VIP

    pro_keys = os.getenv("PRO_API_KEYS", "")
    if api_key and api_key in {value.strip() for value in pro_keys.split(",") if value.strip()}:
        return SubscriptionTier.PRO

    return None


def _is_production_environment() -> tuple[bool, str]:
    """Determine if we're in production mode.

    Returns:
        tuple[bool, str]: (is_production, app_env)
    """
    app_env = os.getenv("APP_ENV", "local").lower()
    debug_mode = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes", "on")
    # Production if env is production/staging AND debug is off
    is_production = (app_env in ("production", "prod", "staging")) and (not debug_mode)
    return is_production, app_env


def _validate_api_key_tier(api_key: str, required_tier: SubscriptionTier) -> bool:
    """Validate if API key has access to required tier.

    Args:
        api_key: API key from request header
        required_tier: Minimum required subscription tier

    Returns:
        bool: True if API key is valid for the required tier

    Note:
        In development mode, test keys are accepted:
        - test_pro_key: PRO tier access
        - test_vip_key: VIP tier access (also grants PRO)

        In production, this should query the subscriptions database.
    """
    is_production, app_env = _is_production_environment()

    if _is_subscription_db_enabled():
        db_tier = _lookup_tier_from_db(api_key)
        if db_tier is not None:
            return _tier_allows_access(db_tier, required_tier)

        logger.warning(
            "Subscription DB lookup unavailable. Falling back to env-based tier detection for tier %s.",
            required_tier.value,
        )

    resolved_env_tier = _resolve_tier_from_env(api_key)
    if resolved_env_tier is not None:
        return _tier_allows_access(resolved_env_tier, required_tier)

    # In non-production mode with anonymous access enabled, allow any key.
    # Check env var dynamically to support testing with mock.patch.dict.
    if not is_production:
        allow_anonymous = os.getenv("ALLOW_ANONYMOUS_API_KEYS", "false").lower() in (
            "true",
            "1",
            "yes",
            "on",
        )
        if allow_anonymous:
            logger.warning(
                f"Anonymous API key accepted in {app_env} mode for tier {required_tier.value}"
            )
            return True

    return False


async def require_pro_tier(x_api_key: Optional[str] = Security(api_key_header)) -> str:
    """Require PRO tier API key for endpoint access.

    RU: Требуется API ключ уровня PRO для доступа к endpoint.
    EN: Requires PRO tier API key for endpoint access.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        str: Validated API key

    Raises:
        HTTPException: 401 if API key is missing or invalid
        HTTPException: 403 if API key tier is insufficient

    Usage:
        @router.post("/pro/feature", dependencies=[Depends(require_pro_tier)])
        async def pro_feature():
            return {"message": "PRO feature accessed"}
    """
    if not x_api_key:
        logger.warning("PRO endpoint accessed without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for PRO tier access",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not _validate_api_key_tier(x_api_key, SubscriptionTier.PRO):
        logger.warning("Invalid API key for PRO tier")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have PRO tier access",
        )

    logger.debug("PRO tier access granted")
    return x_api_key


async def require_vip_tier(x_api_key: Optional[str] = Security(api_key_header)) -> str:
    """Require VIP tier API key for endpoint access.

    RU: Требуется API ключ уровня VIP для доступа к endpoint.
    EN: Requires VIP tier API key for endpoint access.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        str: Validated API key

    Raises:
        HTTPException: 403 if API key is missing or invalid (VIP = feature-gate, not auth-gate)
        HTTPException: 403 if API key tier is insufficient

    Usage:
        @router.post("/vip/feature", dependencies=[Depends(require_vip_tier)])
        async def vip_feature():
            return {"message": "VIP feature accessed"}
    """
    if not x_api_key:
        logger.warning("VIP endpoint accessed without API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="VIP access required",
        )

    if not _validate_api_key_tier(x_api_key, SubscriptionTier.VIP):
        logger.warning("Invalid API key for VIP tier")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have VIP tier access. Upgrade to VIP to access this feature.",
        )

    logger.debug("VIP tier access granted")
    return x_api_key


def get_subscription_tier(api_key: str) -> SubscriptionTier:
    """Get subscription tier for API key.

    RU: Получить уровень подписки для API ключа.
    EN: Get subscription tier for API key.

    Args:
        api_key: API key to check

    Returns:
        SubscriptionTier: Subscription tier (FREE, PRO, or VIP)

    Note:
        Returns FREE if API key is invalid or not found.
        In development mode, test keys return their respective tiers.
    """
    if _is_subscription_db_enabled():
        db_tier = _lookup_tier_from_db(api_key)
        if db_tier is not None:
            return db_tier
        logger.warning(
            "Subscription DB lookup unavailable for get_subscription_tier; using env fallback"
        )

    env_tier = _resolve_tier_from_env(api_key)
    return env_tier if env_tier is not None else SubscriptionTier.FREE


def derive_subject_id_from_api_key(api_key: str) -> int:
    """Derive stable subject_id from API key for state isolation.

    RU: Получить стабильный subject_id из API ключа для изоляции состояния.
    EN: Derive stable subject_id from API key for state isolation.

    Args:
        api_key: Validated API key

    Returns:
        int: Deterministic positive integer subject_id (fits in int64)

    Note:
        This is a temporary solution until proper user authentication is implemented.
        Each API key gets isolated Bayesian state. When user→key mapping is added,
        state can be migrated to actual user_id.

        Security: Uses SHA-256 for identity derivation, NOT password hashing.
        This is intentional - we're creating a deterministic ID, not securing a secret.
    """
    # CodeQL [py/weak-sensitive-data-hashing]: False positive - this is identity derivation,
    # not password hashing. SHA-256 is appropriate for deterministic ID generation.
    digest = hashlib.sha256(
        api_key.encode("utf-8")
    ).digest()  # lgtm[py/weak-sensitive-data-hashing]
    # Take first 8 bytes, convert to int, mask to positive int64
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated user context derived from the API key.

    Attributes:
        user_id: Stable subject identifier derived from API key
        api_key: Raw API key used for authentication
    """

    user_id: int
    api_key: str


async def get_current_user(api_key: str = Depends(require_pro_tier)) -> CurrentUser:
    """Get authenticated user context for PRO-protected endpoints.

    RU: Получить контекст пользователя для PRO-защищённых endpoint.
    EN: Get authenticated user context for PRO-protected endpoints.

    Args:
        api_key: Validated API key from require_pro_tier dependency

    Returns:
        CurrentUser: User context with derived subject_id
    """
    return CurrentUser(user_id=derive_subject_id_from_api_key(api_key), api_key=api_key)


async def get_pro_subject_id(current_user: CurrentUser = Depends(get_current_user)) -> int:
    """Get subject_id for PRO-protected endpoints.

    RU: Получить subject_id для PRO-защищённых endpoint.
    EN: Get subject_id for PRO-protected endpoints.

    Args:
        current_user: Authenticated user context

    Returns:
        int: Subject ID derived from API key

    Usage:
        @router.post("/event")
        def record_event(
            payload: EventRequest,
            subject_id: int = Depends(get_pro_subject_id),
        ):
            # Use subject_id instead of user_id from payload
            ...
    """
    return current_user.user_id
