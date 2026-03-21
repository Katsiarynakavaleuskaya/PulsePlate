# -*- coding: utf-8 -*-
"""Billing activation endpoints for persisted subscription state.

RU: Runtime endpoints для activation + persisted subscription state.
EN: Runtime endpoints for activation + persisted subscription state.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, Security, status
from fastapi.responses import JSONResponse

from app.http_error_details import (
    ACTIVATION_ACCESS_FORBIDDEN_DETAIL,
    DETERMINISTIC_ACTIVATION_CONFLICT_DETAIL,
    TRANSPORT_AUTH_REQUIRED_DETAIL,
)
from app.schemas.payments import PaymentSource
from app.middleware.api_tiers import CurrentUser, derive_subject_id_from_api_key
from app.routers.api_key import api_key_header
from app.schemas.payments import (
    ActivateSubscriptionRequest,
    PaymentErrorResponse,
    SubscriptionActivationResponse,
)
from app.services import payments_activation


class ActivationTransportUnauthorizedError(PermissionError):
    """Raised when transport auth is missing or blank."""


router = APIRouter(
    prefix="/api/v1/pro/payments",
    tags=["pro", "payments"],
)


def _payment_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    detail: str,
) -> JSONResponse:
    """Return deterministic JSON error envelope."""

    error = PaymentErrorResponse(
        code=code,
        message=message,
        detail=detail,
    )
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(mode="json"),
    )


def _resolve_activation_user(x_api_key: str | None) -> CurrentUser:
    """Resolve pre-entitlement transport identity from non-empty API key."""

    if x_api_key is None:
        raise ActivationTransportUnauthorizedError("X-API-Key header is required")

    normalized_api_key = x_api_key.strip()
    if not normalized_api_key:
        raise ActivationTransportUnauthorizedError("X-API-Key header must not be blank")

    return CurrentUser(
        user_id=derive_subject_id_from_api_key(normalized_api_key),
        api_key=normalized_api_key,
    )


@router.post(
    "/activate",
    response_model=SubscriptionActivationResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid transport protection",
            "model": PaymentErrorResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "iOS activation requires receipt_data or Apple verification failed",
            "model": PaymentErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Canonical activation payload is required on this route",
            "model": PaymentErrorResponse,
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Apple receipt verification upstream error",
            "model": PaymentErrorResponse,
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "description": "Apple receipt verification timed out",
            "model": PaymentErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "Deterministic activation conflict",
            "model": PaymentErrorResponse,
        },
    },
)
async def activate_subscription(
    payload: ActivateSubscriptionRequest,
    response: Response,
    x_api_key: str | None = Security(api_key_header),
) -> SubscriptionActivationResponse | JSONResponse:
    """Create or replay a deterministic subscription activation event."""

    try:
        current_user = _resolve_activation_user(x_api_key)
        if not payload.uses_canonical_payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="canonical activation payload is required on this route",
            )
        if payload.source is PaymentSource.ios_app_store:
            activation = await payments_activation.activate_subscription_async(
                user_id=current_user.user_id,
                payload=payload,
            )
        else:
            activation = payments_activation.activate_subscription(
                user_id=current_user.user_id,
                payload=payload,
            )
    except ActivationTransportUnauthorizedError:
        return _payment_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="activation_transport_unauthorized",
            message="Transport protection required",
            detail=TRANSPORT_AUTH_REQUIRED_DETAIL,
        )
    except payments_activation.IdempotencyConflictError:
        return _payment_error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            message="Deterministic activation conflict",
            detail=DETERMINISTIC_ACTIVATION_CONFLICT_DETAIL,
        )
    except payments_activation.ActivationReverifyRejectedError as exc:
        return _payment_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code=getattr(exc, "error_code", "activation_reverify_rejected"),
            message=exc.error_message or "Activation reverification rejected",
            detail=str(exc),
        )
    except payments_activation.AppleVerifyTransportError as exc:
        return _payment_error_response(
            status_code=exc.status_code,
            code=exc.error_code,
            message=exc.error_message,
            detail=str(exc) or exc.error_message,
        )

    response.status_code = status.HTTP_200_OK
    return activation


@router.get(
    "/activations/{activation_id}",
    response_model=SubscriptionActivationResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid transport protection",
            "model": PaymentErrorResponse,
        },
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
    x_api_key: str | None = Security(api_key_header),
) -> SubscriptionActivationResponse | JSONResponse:
    """Get current persisted entitlement view for an activation lineage."""

    try:
        current_user = _resolve_activation_user(x_api_key)
        activation = payments_activation.get_activation(
            activation_id,
            user_id=current_user.user_id,
        )
    except ActivationTransportUnauthorizedError:
        return _payment_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="activation_transport_unauthorized",
            message="Transport protection required",
            detail=TRANSPORT_AUTH_REQUIRED_DETAIL,
        )
    except payments_activation.ActivationAccessForbiddenError:
        return _payment_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
            message="Activation access forbidden",
            detail=ACTIVATION_ACCESS_FORBIDDEN_DETAIL,
        )

    if activation is None:
        return _payment_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message="Activation not found",
            detail=activation_id,
        )

    return activation
