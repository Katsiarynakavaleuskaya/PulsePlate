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

import logging
import os
from enum import Enum
from typing import Optional

from fastapi import Header, HTTPException, status

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
VIP_MODULE_ENABLED = os.getenv("VIP_MODULE_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
ALLOW_ANONYMOUS_API_KEYS = os.getenv("ALLOW_ANONYMOUS_API_KEYS", "false").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
# Note: SUBSCRIPTION_DB_ENABLED is checked dynamically in code to support testing


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

    # Development mode: Accept test keys
    if not is_production:
        if api_key == TEST_KEY_VIP:
            # VIP key grants access to both PRO and VIP
            return True
        if api_key == TEST_KEY_PRO and required_tier == SubscriptionTier.PRO:
            # PRO key grants access only to PRO
            return True

        # In dev mode with anonymous access enabled, allow any key
        # Check env var dynamically to support testing with mock.patch.dict
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

        # Invalid key in dev mode: reject
        return False

    # Production mode: Query database
    # Fail-fast if database not configured
    # Check env var dynamically to support testing with mock.patch.dict
    subscription_db_enabled = os.getenv("SUBSCRIPTION_DB_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    if not subscription_db_enabled:
        logger.critical(
            "Production mode requires SUBSCRIPTION_DB_ENABLED=true. "
            "Set environment variable and implement subscription database lookup."
        )
        raise NotImplementedError(
            "API key validation not implemented for production. "
            "Set SUBSCRIPTION_DB_ENABLED=true and implement get_subscription_by_api_key() function."
        )

    # TODO: Implement database lookup for production when SUBSCRIPTION_DB_ENABLED=true
    # from app.services.subscriptions import get_subscription_by_api_key
    # subscription = get_subscription_by_api_key(api_key)
    # if not subscription or subscription.is_expired():
    #     return False
    # if required_tier == SubscriptionTier.VIP:
    #     return subscription.tier == SubscriptionTier.VIP
    # elif required_tier == SubscriptionTier.PRO:
    #     return subscription.tier in [SubscriptionTier.PRO, SubscriptionTier.VIP]
    # return True

    # This code path should never be reached after DB implementation
    logger.error(f"Subscription database lookup not implemented. Tier: {required_tier.value}")
    raise NotImplementedError(
        "Subscription database lookup not implemented. "
        "Implement get_subscription_by_api_key() in app/services/subscriptions.py"
    )


async def require_pro_tier(x_api_key: Optional[str] = Header(None)) -> str:
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


async def require_vip_tier(x_api_key: Optional[str] = Header(None)) -> str:
    """Require VIP tier API key for endpoint access.

    RU: Требуется API ключ уровня VIP для доступа к endpoint.
    EN: Requires VIP tier API key for endpoint access.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        str: Validated API key

    Raises:
        HTTPException: 401 if API key is missing or invalid
        HTTPException: 403 if API key tier is insufficient

    Usage:
        @router.post("/vip/feature", dependencies=[Depends(require_vip_tier)])
        async def vip_feature():
            return {"message": "VIP feature accessed"}
    """
    if not x_api_key:
        logger.warning("VIP endpoint accessed without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for VIP tier access",
            headers={"WWW-Authenticate": "ApiKey"},
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
    is_production, _ = _is_production_environment()

    # Development mode: Check test keys
    if not is_production:
        if api_key == TEST_KEY_VIP:
            return SubscriptionTier.VIP
        if api_key == TEST_KEY_PRO:
            return SubscriptionTier.PRO

    # Production mode: Query database
    # Fail-fast if database not configured
    # Check env var dynamically to support testing with mock.patch.dict
    subscription_db_enabled = os.getenv("SUBSCRIPTION_DB_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    if is_production and not subscription_db_enabled:
        raise NotImplementedError(
            "Subscription database not implemented. "
            "Set SUBSCRIPTION_DB_ENABLED=true and implement get_subscription_by_api_key()."
        )

    # TODO: Implement database lookup
    # from app.services.subscriptions import get_subscription_by_api_key
    # subscription = get_subscription_by_api_key(api_key)
    # return subscription.tier if subscription else SubscriptionTier.FREE

    return SubscriptionTier.FREE
