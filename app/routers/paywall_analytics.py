"""Hidden internal paywall analytics router.

RU: First-party hidden ingestion surface для paywall exposure instrumentation.
EN: First-party hidden ingestion surface for paywall exposure instrumentation.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, Request

from app.middleware.api_tiers import (
    TierAuthContext,
    derive_subject_id_from_api_key,
    resolve_pro_auth_context,
)
from app.schemas.paywall_analytics import (
    PaywallExposureAckResponse,
    PaywallExposureEventRequest,
)
from app.services.paywall_exposure_ledger import (
    PaywallExposureAuthContext,
    PaywallExposureRecordInput,
    record_paywall_exposure_event,
)
from app.security.web_session import WEB_SESSION_COOKIE_NAME

router = APIRouter(prefix="/api/v1/internal/paywall", include_in_schema=False)


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
    except Exception:
        return None


def _to_ledger_auth_context(context: TierAuthContext | None) -> PaywallExposureAuthContext:
    """Translate request auth context into ledger-safe fields."""

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
    record = PaywallExposureRecordInput(
        client_event_id=request_body.client_event_id,
        exposure_id=request_body.exposure_id,
        event_name=request_body.event_name,
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
