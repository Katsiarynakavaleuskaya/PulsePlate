# -*- coding: utf-8 -*-
"""PRO restaurant partner contract endpoints.

RU: Contract-first endpoints для потока `menu -> partner`.
EN: Contract-first endpoints for `menu -> partner` flow.
"""

from __future__ import annotations

import threading
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.middleware.api_tiers import require_pro_tier
from app.schemas.restaurant_partner import (
    PartnerOrderConfirmRequest,
    PartnerOrderCreateRequest,
    PartnerOrderErrorResponse,
    PartnerHandoffShareIssueRequest,
    PartnerHandoffShareResponse,
    PartnerOrderPreviewRequest,
    PartnerOrderPreviewResponse,
    PartnerOrderResponse,
)
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return created


@router.get(
    "/orders/{order_id}",
    response_model=PartnerOrderResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Order not found",
            "model": PartnerOrderErrorResponse,
        }
    },
)
def get_partner_order(order_id: str) -> PartnerOrderResponse:
    order = restaurant_partner_orders.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post(
    "/orders/{order_id}/confirm",
    response_model=PartnerOrderResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Order not found",
            "model": PartnerOrderErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "client_event_id conflict",
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
) -> PartnerOrderResponse:
    try:
        confirmed, _ = restaurant_partner_orders.confirm_order(
            order_id=order_id,
            confirmed_by=payload.confirmed_by,
            client_event_id=payload.client_event_id,
            note=payload.note,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except restaurant_partner_orders.PartnerConsentRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except restaurant_partner_orders.ShareRevokedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except restaurant_partner_orders.ShareExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc


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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
