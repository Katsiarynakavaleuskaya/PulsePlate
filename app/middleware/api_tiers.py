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
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status

from app.routers.api_key import api_key_header
from app.schemas.payments import (
    SubscriptionStatus as PersistedSubscriptionStatus,
    SubscriptionTier as PersistedSubscriptionTier,
)
from app.security.web_session import WEB_SESSION_COOKIE_NAME, verify_web_session
from app.services import subscriptions as subscriptions_store

from app.utils.feature_flags import is_vip_module_enabled
from settings import (
    get_runtime_env_name,
    is_explicit_developer_env,
    is_production_like_env,
    is_truthy_env_var,
)

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Subscription tier levels for API access control.

    RU: Уровни подписки для контроля доступа к API.
    EN: Subscription levels for API access control.
    """

    FREE = "FREE"
    PRO = "PRO"
    VIP = "VIP"


class DBLookupStatus(str, Enum):
    """Outcome of DB-backed API key tier lookup."""

    HIT = "HIT"
    MISS = "MISS"
    ERROR = "ERROR"
    INVALID_TIER = "INVALID_TIER"


@dataclass(frozen=True)
class DBLookupResult:
    """Structured DB lookup result to avoid ambiguous None semantics."""

    status: DBLookupStatus
    tier: SubscriptionTier | None = None


class AuthSource(str, Enum):
    """Authentication source used for tier resolution."""

    HEADER = "header"
    COOKIE = "cookie"


@dataclass(frozen=True)
class TierAuthContext:
    """Resolved authentication context (header or cookie)."""

    api_key: str
    tier: SubscriptionTier
    source: AuthSource
    session_expires_at_epoch: int | None = None


# Test API keys for deterministic test/development tier checks.
TEST_KEY_PRO = "test_pro_key"  # nosec B105: deterministic non-production test key (remove-by: 2026-09-30, ref: PR-995)
TEST_KEY_VIP = "test_vip_key"  # nosec B105: deterministic non-production test key (remove-by: 2026-09-30, ref: PR-995)

# Environment configuration
VIP_MODULE_ENABLED = is_vip_module_enabled()
# Note: SUBSCRIPTION_DB_ENABLED and ALLOW_ANONYMOUS_API_KEYS are checked dynamically in code
# to support testing and avoid import-time config freeze.


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


def _parse_persisted_subscription_tier(raw_tier: str) -> SubscriptionTier | None:
    """Convert persisted billing tier string into authz tier enum."""

    normalized = raw_tier.strip().lower()
    try:
        persisted_tier = PersistedSubscriptionTier(normalized)
    except ValueError:
        return None

    return {
        PersistedSubscriptionTier.free: SubscriptionTier.FREE,
        PersistedSubscriptionTier.pro: SubscriptionTier.PRO,
        PersistedSubscriptionTier.vip: SubscriptionTier.VIP,
    }[persisted_tier]


def _parse_persisted_subscription_status(
    raw_status: str,
) -> PersistedSubscriptionStatus | None:
    """Convert persisted billing status string into canonical status enum."""

    normalized = raw_status.strip().lower()
    try:
        return PersistedSubscriptionStatus(normalized)
    except ValueError:
        return None


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    """Normalize naive/aware datetimes to UTC for deterministic expiry checks."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _tier_rank(tier: SubscriptionTier) -> int:
    """Return deterministic rank for effective paid-tier resolution."""

    return {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.PRO: 1,
        SubscriptionTier.VIP: 2,
    }[tier]


def _lookup_tier_from_db(api_key: str) -> DBLookupResult:
    """Try to resolve API key tier from persisted subscriptions with explicit outcome.

    RU: Пытается определить entitlement из persisted subscriptions и возвращает статус lookup.
    EN: Attempts to resolve entitlement from persisted subscriptions and returns structured status.
    """
    try:
        from core.db import get_session_factory

        user_id = derive_subject_id_from_api_key(api_key)
        session_factory = get_session_factory()
        session = session_factory()
        try:
            subscriptions = subscriptions_store.list_subscriptions_for_user(
                session=session,
                user_id=user_id,
            )
        finally:
            session.close()
    except Exception:
        logger.warning(
            "Subscription DB lookup failed; denying env fallback for safety",
            exc_info=True,
            extra={"component": "api_tiers", "db_lookup_status": DBLookupStatus.ERROR.value},
        )
        return DBLookupResult(status=DBLookupStatus.ERROR)

    if not subscriptions:
        return DBLookupResult(status=DBLookupStatus.MISS)

    now = datetime.now(timezone.utc)
    saw_valid_state = False
    saw_invalid_state = False
    effective_tier = SubscriptionTier.FREE

    for subscription in subscriptions:
        parsed_tier = _parse_persisted_subscription_tier(subscription.tier)
        parsed_status = _parse_persisted_subscription_status(subscription.status)
        if parsed_tier is None or parsed_status is None:
            saw_invalid_state = True
            continue

        saw_valid_state = True
        if parsed_status is not PersistedSubscriptionStatus.active:
            continue

        expires_at = _normalize_utc_datetime(subscription.expires_at)
        if expires_at is not None and expires_at <= now:
            continue

        if _tier_rank(parsed_tier) > _tier_rank(effective_tier):
            effective_tier = parsed_tier

    if saw_valid_state:
        return DBLookupResult(status=DBLookupStatus.HIT, tier=effective_tier)

    if saw_invalid_state:
        logger.warning(
            "Subscription DB lookup returned invalid persisted entitlement state; denying access",
            extra={"component": "api_tiers", "db_lookup_status": DBLookupStatus.INVALID_TIER.value},
        )
        return DBLookupResult(status=DBLookupStatus.INVALID_TIER)

    # RU: Защитный хвост для типизатора; неожиданный непустой, но нейтральный набор трактуем как MISS.
    # EN: Defensive tail for the type checker; treat any unexpected neutral non-empty set as MISS.
    return DBLookupResult(status=DBLookupStatus.MISS)


def _resolve_tier_from_env(
    api_key: str, *, allow_test_keys: bool = True
) -> SubscriptionTier | None:
    """Resolve tier via environment fallback.

    Test keys are accepted only when allow_test_keys=True.
    """
    if allow_test_keys and api_key == TEST_KEY_VIP:
        return SubscriptionTier.VIP
    if allow_test_keys and api_key == TEST_KEY_PRO:
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
    app_env = get_runtime_env_name()
    return is_production_like_env(), app_env


def _resolve_authorized_api_key_tier(
    api_key: str,
    *,
    required_tier: SubscriptionTier,
) -> SubscriptionTier | None:
    """Resolve authorized tier in a single pass, else None."""

    is_production, app_env = _is_production_environment()
    in_developer_env = is_explicit_developer_env()
    allow_developer_api_keys = in_developer_env and is_truthy_env_var("ALLOW_DEV_API_KEY", "true")

    if _is_subscription_db_enabled():
        db_lookup = _lookup_tier_from_db(api_key)
        if db_lookup.status == DBLookupStatus.HIT and db_lookup.tier is not None:
            if _tier_allows_access(db_lookup.tier, required_tier):
                return db_lookup.tier
            return None
        return None

    resolved_env_tier = _resolve_tier_from_env(
        api_key,
        allow_test_keys=allow_developer_api_keys,
    )
    if resolved_env_tier is not None:
        if _tier_allows_access(resolved_env_tier, required_tier):
            return resolved_env_tier
        return None

    # In non-production mode with anonymous access enabled, allow any key.
    if in_developer_env and not is_production:
        allow_anonymous = is_truthy_env_var("ALLOW_ANONYMOUS_API_KEYS", "false")
        if allow_anonymous:
            logger.warning(
                "Anonymous API key accepted in %s mode for tier %s",
                app_env,
                required_tier.value,
            )
            return required_tier

    return None


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
    return _resolve_authorized_api_key_tier(api_key, required_tier=required_tier) is not None


def _request_dependency(request: Request) -> Request:
    """FastAPI helper to inject Request while preserving direct-call compatibility."""

    return request


def _as_request(request: object | None) -> Request | None:
    """Return Request instance or None for direct function invocations."""

    return request if isinstance(request, Request) else None


def _resolve_cookie_auth_context(
    *,
    request: Request | None,
    required_tier: SubscriptionTier,
) -> TierAuthContext | None:
    """Resolve cookie-backed auth context or None."""

    if request is None:
        return None

    raw_cookie = request.cookies.get(WEB_SESSION_COOKIE_NAME, "")
    if not raw_cookie:
        return None

    try:
        claims = verify_web_session(raw_cookie)
    except RuntimeError:
        logger.warning(
            "Session cookie verification failed due to server configuration", exc_info=True
        )
        return None
    if claims is None:
        return None

    resolved_tier = _resolve_authorized_api_key_tier(
        claims.api_key,
        required_tier=required_tier,
    )
    if resolved_tier is None:
        return None

    return TierAuthContext(
        api_key=claims.api_key,
        tier=resolved_tier,
        source=AuthSource.COOKIE,
        session_expires_at_epoch=claims.expires_at_epoch,
    )


def resolve_pro_auth_context(
    *,
    x_api_key: Optional[str] = Security(api_key_header),
    request: Request = Depends(_request_dependency),
) -> TierAuthContext:
    """Resolve PRO auth using header-first precedence, then cookie fallback."""

    request_obj = _as_request(request)
    if x_api_key is not None:
        normalized_api_key = x_api_key.strip()
        if not normalized_api_key:
            logger.warning("Empty X-API-Key header is not allowed for PRO tier")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have PRO tier access",
            )
        resolved_tier = _resolve_authorized_api_key_tier(
            normalized_api_key,
            required_tier=SubscriptionTier.PRO,
        )
        if resolved_tier is None:
            logger.warning("Invalid API key for PRO tier")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have PRO tier access",
            )
        return TierAuthContext(
            api_key=normalized_api_key,
            tier=resolved_tier,
            source=AuthSource.HEADER,
        )

    cookie_context = _resolve_cookie_auth_context(
        request=request_obj,
        required_tier=SubscriptionTier.PRO,
    )
    if cookie_context is not None:
        return cookie_context

    logger.warning("PRO endpoint accessed without API key and without valid session cookie")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key required for PRO tier access",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def resolve_vip_auth_context(
    *,
    x_api_key: Optional[str] = Security(api_key_header),
    request: Request = Depends(_request_dependency),
) -> TierAuthContext:
    """Resolve VIP auth using header-first precedence, then cookie fallback."""

    request_obj = _as_request(request)
    if x_api_key is not None:
        normalized_api_key = x_api_key.strip()
        if not normalized_api_key:
            logger.warning("Empty X-API-Key header is not allowed for VIP tier")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have VIP tier access. Upgrade to VIP to access this feature.",
            )
        resolved_tier = _resolve_authorized_api_key_tier(
            normalized_api_key,
            required_tier=SubscriptionTier.VIP,
        )
        if resolved_tier is None:
            logger.warning("Invalid API key for VIP tier")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have VIP tier access. Upgrade to VIP to access this feature.",
            )
        return TierAuthContext(
            api_key=normalized_api_key,
            tier=resolved_tier,
            source=AuthSource.HEADER,
        )

    cookie_context = _resolve_cookie_auth_context(
        request=request_obj,
        required_tier=SubscriptionTier.VIP,
    )
    if cookie_context is not None:
        return cookie_context

    logger.warning("VIP endpoint accessed without API key and without valid session cookie")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="VIP access required",
    )


def get_request_pro_auth_context(request: Request) -> TierAuthContext | None:
    """Return cached PRO auth context stored by require_pro_tier dependency."""

    cached = getattr(request.state, "pro_auth_context", None)
    if isinstance(cached, TierAuthContext):
        return cached
    return None


def require_pro_tier(
    x_api_key: Optional[str] = Security(api_key_header),
    request: Request = Depends(_request_dependency),
) -> str:
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
    context = resolve_pro_auth_context(
        x_api_key=x_api_key,
        request=request,
    )
    request_obj = _as_request(request)
    if request_obj is not None:
        request_obj.state.pro_auth_context = context
    logger.debug("PRO tier access granted via %s", context.source.value)
    return context.api_key


def require_vip_tier(
    x_api_key: Optional[str] = Security(api_key_header),
    request: Request = Depends(_request_dependency),
) -> str:
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
    context = resolve_vip_auth_context(
        x_api_key=x_api_key,
        request=request,
    )
    request_obj = _as_request(request)
    if request_obj is not None:
        request_obj.state.vip_auth_context = context
    logger.debug("VIP tier access granted via %s", context.source.value)
    return context.api_key


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
    allow_developer_api_keys = is_explicit_developer_env() and is_truthy_env_var(
        "ALLOW_DEV_API_KEY", "true"
    )

    if _is_subscription_db_enabled():
        db_lookup = _lookup_tier_from_db(api_key)
        if db_lookup.status == DBLookupStatus.HIT and db_lookup.tier is not None:
            return db_lookup.tier
        return SubscriptionTier.FREE

    env_tier = _resolve_tier_from_env(
        api_key,
        allow_test_keys=allow_developer_api_keys and not is_production,
    )
    return env_tier if env_tier is not None else SubscriptionTier.FREE


def derive_subject_id_from_api_key(api_key: str) -> int:
    """Derive stable subject_id from API key for state isolation.

    RU: Получить стабильный subject_id из API ключа для изоляции состояния.
    EN: Derive stable subject_id from API key for state isolation.

    Args:
        api_key: Validated API key

    Returns:
        int: Deterministic positive integer subject_id (fits in PostgreSQL bigint)

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
    # Use a positive signed bigint-compatible range to minimize collision risk.
    # RU: Используем диапазон signed bigint, чтобы не сжимать principal до int4
    # и не повышать риск коллизий между tenant/user subject_id.
    return (int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF) or 1


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
