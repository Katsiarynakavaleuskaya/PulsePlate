"""Hidden internal paywall analytics router.

RU: First-party hidden ingestion surface для paywall exposure instrumentation.
EN: First-party hidden ingestion surface for paywall exposure instrumentation.
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.middleware.api_tiers import (
    TierAuthContext,
    derive_subject_id_from_api_key,
    resolve_pro_auth_context,
)
from app.schemas.paywall_analytics import (
    PaywallExposureAckResponse,
    PaywallExposureEventName,
    PaywallExposureEventRequest,
)
from app.security.web_session import WEB_SESSION_COOKIE_NAME

if TYPE_CHECKING:
    from app.services.paywall_exposure_ledger import PaywallExposureAuthContext

router = APIRouter(prefix="/api/v1/internal/paywall", include_in_schema=False)
_PAYWALL_ALLOWED_ORIGINS_ENV = "PAYWALL_ANALYTICS_ALLOWED_ORIGINS"
_FALLBACK_ALLOWED_ORIGINS_ENV = "WORKER_ALLOWED_ORIGINS"
_LOCAL_ENV_NAMES = {"local", "dev", "development", "test"}


def _resolve_optional_auth_context(
    *,
    request: Request,
    x_api_key: str | None,
) -> TierAuthContext | None:
    """Best-effort auth resolution without turning analytics into a hard auth surface."""

    has_cookie = bool(request.cookies.get(WEB_SESSION_COOKIE_NAME, ""))
    has_header = bool(x_api_key and x_api_key.strip())
    if not has_cookie and not has_header:
        return None

    try:
        return resolve_pro_auth_context(x_api_key=x_api_key, request=request)
    except HTTPException:
        return None


def _to_ledger_auth_context(context: TierAuthContext | None) -> "PaywallExposureAuthContext":
    """Translate request auth context into ledger-safe fields."""

    from app.services.paywall_exposure_ledger import PaywallExposureAuthContext

    if context is None:
        return PaywallExposureAuthContext()

    tier_snapshot = context.tier.value.upper()
    auth_source = context.source.value
    subject_id = derive_subject_id_from_api_key(context.api_key)
    return PaywallExposureAuthContext(
        subject_id=subject_id,
        auth_source=auth_source,
        tier_snapshot=tier_snapshot,
    )


def _normalized_origin(value: str | None) -> str | None:
    """Normalize Origin/Referer to ``scheme://netloc`` for exact allowlisting."""

    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _configured_allowed_origins() -> set[str]:
    """Resolve exact trusted origins from paywall-specific or worker fallback env."""

    raw = (
        os.getenv(_PAYWALL_ALLOWED_ORIGINS_ENV) or os.getenv(_FALLBACK_ALLOWED_ORIGINS_ENV) or ""
    ).strip()
    return {
        normalized
        for normalized in (_normalized_origin(item) for item in raw.split(","))
        if normalized is not None
    }


def _is_local_or_test_environment() -> bool:
    """Allow local/test fallback to the request host when no explicit allowlist exists."""

    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    runtime_env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    return app_env in _LOCAL_ENV_NAMES or runtime_env in _LOCAL_ENV_NAMES


def _trusted_browser_origin(request: Request) -> str | None:
    """Return a trusted first-party origin or ``None`` when provenance is missing."""

    allowed_origins = _configured_allowed_origins()
    request_origin = _normalized_origin(request.headers.get("Origin"))
    referer_origin = _normalized_origin(request.headers.get("Referer"))

    candidates = tuple(
        candidate for candidate in (request_origin, referer_origin) if candidate is not None
    )
    if allowed_origins:
        for candidate in candidates:
            if candidate in allowed_origins:
                return candidate
        return None

    if not _is_local_or_test_environment():
        return None

    expected_origin = _normalized_origin(str(request.base_url))
    if expected_origin is None:
        return None
    for candidate in candidates:
        if candidate == expected_origin:
            return candidate
    return None


@router.post(
    "/events",
    include_in_schema=False,
    response_model=PaywallExposureAckResponse,
)
def ingest_paywall_event(
    request_body: PaywallExposureEventRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> PaywallExposureAckResponse:
    """Persist paywall exposure events behind a hidden first-party route."""

    context = _resolve_optional_auth_context(request=request, x_api_key=x_api_key)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated session required.",
        )

    from app.services.paywall_exposure_ledger import (
        PaywallExposureRecordInput,
        record_paywall_exposure_event,
    )

    record = PaywallExposureRecordInput(
        client_event_id=request_body.client_event_id,
        exposure_id=request_body.exposure_id,
        event_name=PaywallExposureEventName(request_body.event_name.value),
        source_surface=request_body.source_surface,
        trigger_reason=request_body.trigger_reason,
        via=request_body.via,
        metadata=request_body.metadata,
    )
    record_paywall_exposure_event(
        record=record,
        auth_context=_to_ledger_auth_context(context),
    )
    return PaywallExposureAckResponse()
