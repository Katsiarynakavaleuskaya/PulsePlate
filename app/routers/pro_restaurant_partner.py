# -*- coding: utf-8 -*-
"""PRO restaurant partner contract endpoints.

RU: Contract-first endpoints для потока `menu -> partner`.
EN: Contract-first endpoints for `menu -> partner` flow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.middleware.api_tiers import require_pro_tier
from app.schemas.restaurant_partner import (
    PartnerOrderConfirmRequest,
    PartnerOrderCreateRequest,
    PartnerOrderErrorResponse,
    PartnerOrderPreviewRequest,
    PartnerOrderPreviewResponse,
    PartnerOrderResponse,
)
from app.services import restaurant_partner_orders

router = APIRouter(
    prefix="/api/v1/pro/restaurants/partner",
    tags=["pro", "restaurants"],
    dependencies=[Depends(require_pro_tier)],
)


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
) -> PartnerOrderResponse:
    try:
        created, is_new = restaurant_partner_orders.create_order(
            draft=payload.draft,
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
