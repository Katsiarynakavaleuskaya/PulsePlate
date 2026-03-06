"""PRO web-session endpoints.

RU: Web-session endpoints для browser cookie auth поверх PRO/VIP tier.
EN: Web-session endpoints for browser cookie auth on top of PRO/VIP tier.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security, status
from fastapi.security import APIKeyCookie

from app.middleware.api_tiers import (
    SubscriptionTier,
    TierAuthContext,
    get_request_pro_auth_context,
    require_pro_tier,
)
from app.schemas.session import (
    SessionExchangeResponse,
    SessionLogoutResponse,
    SessionStatusResponse,
)
from app.security.web_session import (
    WEB_SESSION_COOKIE_NAME,
    clear_web_session_cookie,
    issue_web_session,
    require_web_session_ttl_seconds,
    set_web_session_cookie,
)

logger = logging.getLogger(__name__)

session_cookie_security = APIKeyCookie(
    name=WEB_SESSION_COOKIE_NAME,
    scheme_name="CookieSession",
    auto_error=False,
)

router = APIRouter(
    prefix="/api/v1/pro",
    tags=["pro", "session"],
)


def _get_cached_pro_context(request: Request) -> TierAuthContext:
    """Get PRO auth context produced by require_pro_tier dependency."""

    context = get_request_pro_auth_context(request)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing authentication context",
        )
    return context


def _to_exchange_response(payload: object) -> SessionExchangeResponse:
    """Typed conversion helper for Pydantic v2 discipline."""

    response_obj: SessionExchangeResponse
    response_obj = SessionExchangeResponse.model_validate(payload)
    return response_obj


def _to_status_response(payload: object) -> SessionStatusResponse:
    """Typed conversion helper for Pydantic v2 discipline."""

    response_obj: SessionStatusResponse
    response_obj = SessionStatusResponse.model_validate(payload)
    return response_obj


def _to_logout_response(payload: object) -> SessionLogoutResponse:
    """Typed conversion helper for Pydantic v2 discipline."""

    response_obj: SessionLogoutResponse
    response_obj = SessionLogoutResponse.model_validate(payload)
    return response_obj


def _issue_and_set_cookie(
    *,
    response: Response,
    context: TierAuthContext,
) -> SessionExchangeResponse:
    """Issue signed cookie and set hardened cookie attributes."""

    resolved_tier = context.tier
    if resolved_tier not in (SubscriptionTier.PRO, SubscriptionTier.VIP):
        logger.warning("Unexpected tier in session context: %s", resolved_tier.value)
        raise RuntimeError("Unexpected tier for web session exchange")

    ttl_seconds = require_web_session_ttl_seconds()
    issued = issue_web_session(
        api_key=context.api_key,
        tier=resolved_tier.value,
        ttl_seconds=ttl_seconds,
    )
    set_web_session_cookie(
        response=response,
        token=issued.token,
        ttl_seconds=ttl_seconds,
    )
    return _to_exchange_response(
        {
            "status": "ok",
            "tier": resolved_tier.value,
            "auth_source": context.source.value,
            "expires_at_epoch": issued.claims.expires_at_epoch,
            "ttl_seconds": ttl_seconds,
        }
    )


@router.post("/session/exchange", response_model=SessionExchangeResponse)
def exchange_session_cookie(
    request: Request,
    response: Response,
    _session_cookie: str | None = Security(session_cookie_security),
    _api_key: str = Depends(require_pro_tier),
) -> SessionExchangeResponse:
    """Exchange authenticated PRO/VIP session into hardened HttpOnly cookie."""

    context = _get_cached_pro_context(request)
    try:
        return _issue_and_set_cookie(response=response, context=context)
    except RuntimeError as exc:
        logger.warning("Session exchange failed due to security misconfiguration", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web session is unavailable",
        ) from exc


@router.get("/session", response_model=SessionStatusResponse)
def get_session_status(
    request: Request,
    _session_cookie: str | None = Security(session_cookie_security),
    _api_key: str = Depends(require_pro_tier),
) -> SessionStatusResponse:
    """Return current auth source and tier for PRO/VIP session."""

    context = _get_cached_pro_context(request)
    return _to_status_response(
        {
            "status": "ok",
            "authenticated": True,
            "tier": context.tier.value,
            "auth_source": context.source.value,
            "expires_at_epoch": context.session_expires_at_epoch,
        }
    )


@router.post("/session/refresh", response_model=SessionExchangeResponse)
def refresh_session_cookie(
    request: Request,
    response: Response,
    _session_cookie: str | None = Security(session_cookie_security),
    _api_key: str = Depends(require_pro_tier),
) -> SessionExchangeResponse:
    """Refresh session cookie for currently authenticated PRO/VIP principal."""

    context = _get_cached_pro_context(request)
    try:
        return _issue_and_set_cookie(response=response, context=context)
    except RuntimeError as exc:
        logger.warning("Session refresh failed due to security misconfiguration", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web session is unavailable",
        ) from exc


@router.post("/session/logout", response_model=SessionLogoutResponse)
def logout_session(
    response: Response,
    _session_cookie: str | None = Security(session_cookie_security),
    _api_key: str = Depends(require_pro_tier),
) -> SessionLogoutResponse:
    """Logout by clearing session cookie (idempotent)."""

    clear_web_session_cookie(response=response)
    return _to_logout_response({"status": "ok", "logged_out": True})
