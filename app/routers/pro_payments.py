# -*- coding: utf-8 -*-
"""PRO payments baseline endpoints (contract-first, additive, non-breaking).

RU: Базовые PRO endpoints для активации подписки (контракт-first, без breaking changes).
EN: Baseline PRO endpoints for subscription activation (contract-first, non-breaking).
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from app.middleware.api_tiers import require_pro_tier
from app.schemas.payments import (
    ActivateSubscriptionRequest,
    PaymentErrorResponse,
    SubscriptionActivationResponse,
)
from app.services import payments_activation

router = APIRouter(
    prefix="/api/v1/pro/payments",
    tags=["pro", "payments"],
)


def _issuer_from_api_key(api_key: str) -> str:
    """Return deterministic opaque issuer marker from API key."""
    if not api_key:
        return "api_key:anonymous"
    digest = hashlib.sha3_256(api_key.encode("utf-8")).hexdigest()
    return f"api_key:{digest}"


@router.post(
    "/activate",
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
def activate_subscription(
    payload: ActivateSubscriptionRequest,
    response: Response,
    x_api_key: str = Depends(require_pro_tier),
) -> SubscriptionActivationResponse | JSONResponse:
    """Create activation or return idempotent replay."""
    try:
        activation, is_new = payments_activation.activate_subscription(
            issuer=_issuer_from_api_key(x_api_key),
            payload=payload,
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
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return activation


@router.get(
    "/activations/{activation_id}",
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
def get_subscription_activation(
    activation_id: str,
    x_api_key: str = Depends(require_pro_tier),
) -> SubscriptionActivationResponse | JSONResponse:
    """Get activation status by ID."""
    issuer = _issuer_from_api_key(x_api_key)
    try:
        activation = payments_activation.get_activation(activation_id, issuer=issuer)
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
            detail=activation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error.model_dump(mode="json"),
        )
    return activation
