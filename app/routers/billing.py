# -*- coding: utf-8 -*-
"""Canonical billing endpoints for RU/BY + iOS payment baseline.

RU: Канонические billing endpoints для RU/BY + iOS baseline.
EN: Canonical billing endpoints for RU/BY + iOS baseline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI

from app.middleware.api_tiers import require_pro_tier
from app.schemas.payments import (
    AppleReceiptVerificationRequest,
    ManualRailIntentRequest,
    ManualRailReconcileRequest,
    PaymentErrorResponse,
    SubscriptionActivationResponse,
)
from app.services import payments_activation

router = APIRouter(prefix="/api/v1/pro/payments", tags=["pro", "payments"])

__all__ = ["register_billing_routes", "router"]


def register_billing_routes(app: "FastAPI") -> APIRouter:
    """Register canonical billing routes idempotently on the provided app."""
    has_apple_verify = any(
        getattr(route, "path", None) == "/api/v1/pro/payments/apple/verify-receipt"
        and "POST" in (getattr(route, "methods", None) or set())
        for route in getattr(app, "routes", None) or []
    )
    if not has_apple_verify:
        app.include_router(router)
    return router


def _issuer_from_api_key(api_key: str) -> str:
    """Return deterministic opaque issuer marker from API key."""
    return payments_activation.issuer_from_api_key(api_key)


@router.post(
    "/apple/verify-receipt",
    response_model=SubscriptionActivationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "Idempotent replay",
            "model": SubscriptionActivationResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "client_event_id conflict",
            "model": PaymentErrorResponse,
        },
    },
)
def verify_apple_receipt(
    payload: AppleReceiptVerificationRequest,
    x_api_key: str = Depends(require_pro_tier),
) -> SubscriptionActivationResponse | JSONResponse:
    """Create or replay iOS receipt activation using deterministic baseline verification."""
    activation_request = payments_activation.build_ios_activation_request(payload=payload)
    try:
        activation, is_new = payments_activation.activate_subscription(
            issuer=_issuer_from_api_key(x_api_key),
            payload=activation_request,
        )
    except payments_activation.IdempotencyConflictError as exc:
        error = PaymentErrorResponse(
            code="idempotency_conflict",
            message="client_event_id conflict",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error.model_dump(mode="json"),
        )
    if is_new:
        return activation
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=activation.model_dump(mode="json"),
    )


@router.post(
    "/ru-by/manual-intent",
    response_model=SubscriptionActivationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "Idempotent replay",
            "model": SubscriptionActivationResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "client_event_id conflict",
            "model": PaymentErrorResponse,
        },
    },
)
def create_manual_payment_intent(
    payload: ManualRailIntentRequest,
    x_api_key: str = Depends(require_pro_tier),
) -> SubscriptionActivationResponse | JSONResponse:
    """Create manual RU/BY payment intent with pending reconciliation lifecycle."""
    activation_request = payments_activation.build_manual_intent_request(payload=payload)
    try:
        activation, is_new = payments_activation.activate_subscription(
            issuer=_issuer_from_api_key(x_api_key),
            payload=activation_request,
        )
    except payments_activation.IdempotencyConflictError as exc:
        error = PaymentErrorResponse(
            code="idempotency_conflict",
            message="client_event_id conflict",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error.model_dump(mode="json"),
        )
    if is_new:
        return activation
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=activation.model_dump(mode="json"),
    )


@router.post(
    "/ru-by/reconcile",
    response_model=SubscriptionActivationResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Activation access forbidden",
            "model": PaymentErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Activation not found",
            "model": PaymentErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "client_event_id conflict",
            "model": PaymentErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Reconcile state invalid",
            "model": PaymentErrorResponse,
        },
    },
)
def reconcile_manual_payment_intent(
    payload: ManualRailReconcileRequest,
    x_api_key: str = Depends(require_pro_tier),
) -> SubscriptionActivationResponse | JSONResponse:
    """Apply reconciliation decision to pending manual payment intent."""
    try:
        return payments_activation.reconcile_activation(
            issuer=_issuer_from_api_key(x_api_key),
            payload=payload,
        )
    except payments_activation.ActivationAccessForbiddenError as exc:
        error = PaymentErrorResponse(
            code="forbidden",
            message="Activation access forbidden",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error.model_dump(mode="json"),
        )
    except KeyError as exc:
        error = PaymentErrorResponse(
            code="not_found",
            message="Activation not found",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error.model_dump(mode="json"),
        )
    except payments_activation.IdempotencyConflictError as exc:
        error = PaymentErrorResponse(
            code="idempotency_conflict",
            message="client_event_id conflict",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error.model_dump(mode="json"),
        )
    except payments_activation.ActivationStateError as exc:
        error = PaymentErrorResponse(
            code="invalid_reconcile_state",
            message="Reconcile state invalid",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error.model_dump(mode="json"),
        )


@router.get(
    "/ru-by/reconcile/{intent_id}",
    response_model=SubscriptionActivationResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Activation access forbidden",
            "model": PaymentErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Activation not found",
            "model": PaymentErrorResponse,
        },
    },
)
def get_manual_payment_intent_status(
    intent_id: str,
    x_api_key: str = Depends(require_pro_tier),
) -> SubscriptionActivationResponse | JSONResponse:
    """Fetch current status of manual payment reconciliation intent."""
    issuer = _issuer_from_api_key(x_api_key)
    try:
        activation = payments_activation.get_activation(intent_id, issuer=issuer)
    except payments_activation.ActivationAccessForbiddenError as exc:
        error = PaymentErrorResponse(
            code="forbidden",
            message="Activation access forbidden",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error.model_dump(mode="json"),
        )
    if activation is None:
        error = PaymentErrorResponse(
            code="not_found",
            message="Activation not found",
            detail=intent_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error.model_dump(mode="json"),
        )
    return activation
