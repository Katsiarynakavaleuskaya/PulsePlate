# -*- coding: utf-8 -*-
"""PRO restaurant partner contract endpoints.

RU: Contract-first endpoints для потока `menu -> partner`.
EN: Contract-first endpoints for `menu -> partner` flow.
"""

from __future__ import annotations

import threading
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.http_error_details import (
    CONFIRM_ORDER_CONFLICT_DETAIL,
    CREATE_ORDER_CONFLICT_DETAIL,
    INVALID_HANDOFF_PAYLOAD_DETAIL,
    INVALID_ORDER_TRANSITION_DETAIL,
    INVALID_WEEKLY_PLAN_ADAPTER_PAYLOAD_DETAIL,
    ORDER_ACCESS_FORBIDDEN_DETAIL,
    ORDER_GONE_DETAIL,
    PARTNER_CONSENT_REQUIRED_DETAIL,
    SHARE_ACCESS_FORBIDDEN_DETAIL,
    SHARE_EXPIRED_DETAIL,
    SHARE_REVOKED_DETAIL,
)
from app.middleware.api_tiers import require_pro_tier
from app.security.rate_limit import RATE_LIMIT_429_RESPONSES, RATE_LIMIT_EXPORTS, limit_if_available
from app.schemas.restaurant_partner import (
    PartnerOrderConfirmRequest,
    PartnerOrderCreateRequest,
    PartnerOrderErrorResponse,
    PartnerHandoffShareIssueRequest,
    PartnerHandoffShareResponse,
    PartnerOrderWeeklyAdapterRequest,
    PartnerOrderPreviewRequest,
    PartnerOrderPreviewResponse,
    PartnerOrderResponse,
)
from app.services import restaurant_partner_export_adapter
from app.services import restaurant_partner_orders

_ISSUER_LOCK = threading.Lock()
_ISSUER_BY_API_KEY: dict[str, str] = {}

router = APIRouter(
    prefix="/api/v1/pro/restaurants/partner",
    tags=["pro", "restaurants"],
    dependencies=[Depends(require_pro_tier)],
)


def _issuer_from_api_key(api_key: str) -> str:
    """Build process-stable opaque issuer marker from authenticated API key."""
    if not api_key:
        return "api_key:anonymous"
    with _ISSUER_LOCK:
        marker = _ISSUER_BY_API_KEY.get(api_key)
        if marker is None:
            marker = f"api_key:{uuid4().hex[:12]}"
            _ISSUER_BY_API_KEY[api_key] = marker
    return marker


@router.post(
    "/orders/preview",
    response_model=PartnerOrderPreviewResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid order draft",
            "model": PartnerOrderErrorResponse,
        }
    },
)
def preview_partner_order(payload: PartnerOrderPreviewRequest) -> PartnerOrderPreviewResponse:
    preview: PartnerOrderPreviewResponse = restaurant_partner_orders.preview_order(payload.draft)
    return preview


@router.post(
    "/orders/adapt/preview",
    response_model=PartnerOrderPreviewResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid weekly plan adapter payload",
            "model": PartnerOrderErrorResponse,
        },
        **RATE_LIMIT_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_EXPORTS)
def preview_partner_order_from_weekly_plan(
    request: Request,
    payload: PartnerOrderWeeklyAdapterRequest,
) -> PartnerOrderPreviewResponse:
    del request
    try:
        draft = restaurant_partner_export_adapter.build_order_draft_from_weekly_plan(
            week_plan=payload.week_plan,
            restaurant_id=payload.restaurant_id,
            currency=payload.currency,
            fulfillment=payload.fulfillment,
            service_fee_minor=payload.service_fee_minor,
            delivery_fee_minor=payload.delivery_fee_minor,
            customer_note=payload.customer_note,
            dietary_tags=payload.dietary_tags,
            allergens=payload.allergens,
            consent=payload.consent,
            attribution_source=payload.attribution_source,
            unit_price_minor_default=payload.unit_price_minor_default,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=INVALID_WEEKLY_PLAN_ADAPTER_PAYLOAD_DETAIL,
        ) from exc
    return restaurant_partner_orders.preview_order(draft)


@router.post(
    "/orders",
    response_model=PartnerOrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "Idempotent replay",
            "model": PartnerOrderResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "client_event_id conflict",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid order draft",
            "model": PartnerOrderErrorResponse,
        },
    },
)
def create_partner_order(
    payload: PartnerOrderCreateRequest,
    response: Response,
    x_api_key: str = Depends(require_pro_tier),
) -> PartnerOrderResponse:
    try:
        created, is_new = restaurant_partner_orders.create_order(
            draft=payload.draft,
            issuer=_issuer_from_api_key(x_api_key),
            client_event_id=payload.client_event_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CREATE_ORDER_CONFLICT_DETAIL,
        ) from exc
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return created


@router.get(
    "/orders/{order_id}",
    response_model=PartnerOrderResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Order access forbidden",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Order not found",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_410_GONE: {
            "description": "Order gone",
            "model": PartnerOrderErrorResponse,
        },
    },
)
def get_partner_order(
    order_id: str,
    x_api_key: str = Depends(require_pro_tier),
) -> PartnerOrderResponse:
    issuer = _issuer_from_api_key(x_api_key)
    try:
        order = restaurant_partner_orders.get_order(order_id, issuer=issuer)
    except restaurant_partner_orders.OrderAccessForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ORDER_ACCESS_FORBIDDEN_DETAIL,
        ) from exc
    except restaurant_partner_orders.OrderGoneError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=ORDER_GONE_DETAIL,
        ) from exc
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post(
    "/orders/{order_id}/confirm",
    response_model=PartnerOrderResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Order access forbidden",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Order not found",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "client_event_id conflict",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_410_GONE: {
            "description": "Order gone",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid transition",
            "model": PartnerOrderErrorResponse,
        },
    },
)
def confirm_partner_order(
    order_id: str,
    payload: PartnerOrderConfirmRequest,
    x_api_key: str = Depends(require_pro_tier),
) -> PartnerOrderResponse:
    issuer = _issuer_from_api_key(x_api_key)
    try:
        confirmed, _ = restaurant_partner_orders.confirm_order(
            order_id=order_id,
            issuer=issuer,
            confirmed_by=payload.confirmed_by,
            client_event_id=payload.client_event_id,
            note=payload.note,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        ) from exc
    except restaurant_partner_orders.OrderAccessForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ORDER_ACCESS_FORBIDDEN_DETAIL,
        ) from exc
    except restaurant_partner_orders.OrderGoneError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=ORDER_GONE_DETAIL,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CONFIRM_ORDER_CONFLICT_DETAIL,
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=INVALID_ORDER_TRANSITION_DETAIL,
        ) from exc
    return confirmed


@router.post(
    "/orders/{order_id}/handoff/shares",
    response_model=PartnerHandoffShareResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Partner consent required",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Order not found",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid handoff payload",
            "content": {
                "application/json": {
                    "schema": {
                        "oneOf": [
                            {"$ref": "#/components/schemas/PartnerOrderErrorResponse"},
                            {"$ref": "#/components/schemas/HTTPValidationError"},
                        ]
                    }
                }
            },
        },
    },
)
def issue_handoff_share(
    order_id: str,
    payload: PartnerHandoffShareIssueRequest,
    x_api_key: str = Depends(require_pro_tier),
) -> PartnerHandoffShareResponse:
    try:
        issued = restaurant_partner_orders.issue_handoff_share(
            order_id=order_id,
            issuer=_issuer_from_api_key(x_api_key),
            partner_id=payload.partner_id,
            expires_in_minutes=payload.expires_in_minutes,
        )
    except restaurant_partner_orders.OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        ) from exc
    except restaurant_partner_orders.ShareAccessForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SHARE_ACCESS_FORBIDDEN_DETAIL,
        ) from exc
    except restaurant_partner_orders.PartnerConsentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PARTNER_CONSENT_REQUIRED_DETAIL,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=INVALID_HANDOFF_PAYLOAD_DETAIL,
        ) from exc
    return issued


@router.get(
    "/handoff/shares/{share_id}/status",
    response_model=PartnerHandoffShareResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Share revoked or access forbidden",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Share not found",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_410_GONE: {
            "description": "Share expired",
            "model": PartnerOrderErrorResponse,
        },
    },
)
def get_handoff_share_status(
    share_id: str,
    x_api_key: str = Depends(require_pro_tier),
) -> PartnerHandoffShareResponse:
    try:
        return restaurant_partner_orders.get_handoff_share_status(
            share_id,
            requester_issuer=_issuer_from_api_key(x_api_key),
        )
    except restaurant_partner_orders.ShareNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        ) from exc
    except restaurant_partner_orders.ShareAccessForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SHARE_ACCESS_FORBIDDEN_DETAIL,
        ) from exc
    except restaurant_partner_orders.ShareRevokedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SHARE_REVOKED_DETAIL,
        ) from exc
    except restaurant_partner_orders.ShareExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=SHARE_EXPIRED_DETAIL,
        ) from exc


@router.post(
    "/handoff/shares/{share_id}/revoke",
    response_model=PartnerHandoffShareResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Share access forbidden",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Share not found",
            "model": PartnerOrderErrorResponse,
        },
    },
)
def revoke_handoff_share(
    share_id: str,
    x_api_key: str = Depends(require_pro_tier),
) -> PartnerHandoffShareResponse:
    try:
        return restaurant_partner_orders.revoke_handoff_share(
            share_id,
            requester_issuer=_issuer_from_api_key(x_api_key),
        )
    except restaurant_partner_orders.ShareNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        ) from exc
    except restaurant_partner_orders.ShareAccessForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SHARE_ACCESS_FORBIDDEN_DETAIL,
        ) from exc
