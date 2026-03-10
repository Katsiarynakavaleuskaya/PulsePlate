# -*- coding: utf-8 -*-
"""Canonical billing endpoints for RU/BY + iOS payment baseline.

RU: Канонические billing endpoints для RU/BY + iOS baseline.
EN: Canonical billing endpoints for RU/BY + iOS baseline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI

from app.middleware.api_tiers import require_pro_tier
from app.routers.api_key import api_key_header
from app.schemas.payments import (
    AppleProviderError,
    AppleReceiptVerificationRequest,
    AppleReceiptVerificationResponse,
    AppleVerificationState,
    ManualRailIntentRequest,
    ManualRailReconcileRequest,
    PaymentErrorResponse,
    SubscriptionActivationResponse,
)
from app.services import payments_activation

billing_router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
router = APIRouter(prefix="/api/v1/pro/payments", tags=["pro", "payments"])

__all__ = ["billing_router", "register_billing_routes", "router"]

_DETAIL_IDEMPOTENCY_CONFLICT = "existing client_event_id is bound to a different payload"
_DETAIL_FORBIDDEN = "issuer_access_denied"
_DETAIL_NOT_FOUND = "activation_not_found"
_DETAIL_IOS_MANUAL_UNSUPPORTED = "manual_reconciliation_not_supported_for_ios"
_DETAIL_MANUAL_STATUS_UNSUPPORTED = "manual_status_not_supported_for_ios"
_DETAIL_PENDING_REQUIRED = "manual_reconcile_transition_requires_pending_state"
_RESPONSE_401_UNAUTHORIZED = {
    "description": "Missing or invalid API key",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail"],
                "properties": {
                    "detail": {
                        "type": "string",
                        "description": "FastAPI auth error detail from tier guard",
                    }
                },
            }
        }
    },
}
_RESPONSE_422_VALIDATION_OR_PAYMENT = {
    "description": "Request validation failed or reconcile state is invalid",
    "content": {
        "application/json": {
            "schema": {
                "oneOf": [
                    {"$ref": "#/components/schemas/PaymentErrorResponse"},
                    {"$ref": "#/components/schemas/HTTPValidationError"},
                ]
            }
        }
    },
}


def register_billing_routes(app: "FastAPI") -> APIRouter:
    """Register canonical billing routes idempotently on the provided app."""
    routes = getattr(app, "routes", None) or []
    has_canonical_apple_verify = any(
        getattr(route, "path", None) == "/api/v1/billing/apple/verify-receipt"
        and "POST" in (getattr(route, "methods", None) or set())
        for route in routes
    )
    has_legacy_manual_intent = any(
        getattr(route, "path", None) == "/api/v1/pro/payments/ru-by/manual-intent"
        and "POST" in (getattr(route, "methods", None) or set())
        for route in routes
    )
    if not has_canonical_apple_verify:
        app.include_router(billing_router)
    if not has_legacy_manual_intent:
        app.include_router(router)
    return router


def _issuer_from_api_key(api_key: str) -> str:
    """Return deterministic opaque issuer marker from API key."""
    issuer: str = payments_activation.issuer_from_api_key(api_key)
    return issuer


def _payment_error_response(
    *,
    code: str,
    message: str,
    detail: str,
    status_code: int,
) -> JSONResponse:
    """Build deterministic payment error envelope without leaking exception internals."""
    error = PaymentErrorResponse(code=code, message=message, detail=detail)
    return JSONResponse(status_code=status_code, content=error.model_dump(mode="json"))


def _require_billing_transport_key(
    x_api_key: Optional[str] = Security(api_key_header),
) -> str:
    """Require only transport-level API key presence for billing verify route."""
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for billing verification",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    normalized_api_key = x_api_key.strip()
    if not normalized_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for billing verification",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return normalized_api_key


def _apple_operational_error_response(
    exc: payments_activation.AppleVerifyTransportError,
) -> JSONResponse:
    """Return canonical Apple verification transport error response."""
    payload = AppleReceiptVerificationResponse(
        verified=False,
        verification_state=AppleVerificationState.invalid,
        error=AppleProviderError(code=exc.error_code, message=exc.error_message),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
    )


def _activation_state_detail(exc: payments_activation.ActivationStateError) -> str:
    """Map internal state exceptions to stable public error details."""
    detail = str(exc)
    if detail == "ios_app_store activation cannot be reconciled manually":
        return _DETAIL_IOS_MANUAL_UNSUPPORTED
    if detail == "manual reconciliation status is unavailable for ios_app_store":
        return _DETAIL_MANUAL_STATUS_UNSUPPORTED
    if detail == "manual reconcile transition requires pending state":
        return _DETAIL_PENDING_REQUIRED
    return "invalid_reconcile_state"


async def _verify_apple_receipt_response(
    payload: AppleReceiptVerificationRequest,
) -> AppleReceiptVerificationResponse | JSONResponse:
    """Verify Apple receipt and return normalized response without side effects."""
    try:
        return await payments_activation.verify_apple_receipt(payload.receipt_data)
    except payments_activation.AppleVerifyTransportError as exc:
        return _apple_operational_error_response(exc)


@billing_router.post(
    "/apple/verify-receipt",
    response_model=AppleReceiptVerificationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: _RESPONSE_401_UNAUTHORIZED,
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Apple upstream error",
            "model": AppleReceiptVerificationResponse,
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "description": "Apple verify timeout",
            "model": AppleReceiptVerificationResponse,
        },
    },
)
async def verify_apple_receipt(
    payload: AppleReceiptVerificationRequest,
    _x_api_key: str = Depends(_require_billing_transport_key),
) -> AppleReceiptVerificationResponse | JSONResponse:
    """Canonical Apple receipt verification route on additive billing namespace."""
    return await _verify_apple_receipt_response(payload)


@router.post(
    "/ru-by/manual-intent",
    response_model=SubscriptionActivationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_401_UNAUTHORIZED: _RESPONSE_401_UNAUTHORIZED,
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
    except payments_activation.IdempotencyConflictError:
        return _payment_error_response(
            code="idempotency_conflict",
            message="client_event_id conflict",
            detail=_DETAIL_IDEMPOTENCY_CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
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
        status.HTTP_401_UNAUTHORIZED: _RESPONSE_401_UNAUTHORIZED,
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
        status.HTTP_422_UNPROCESSABLE_CONTENT: _RESPONSE_422_VALIDATION_OR_PAYMENT,
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
    except payments_activation.ActivationAccessForbiddenError:
        return _payment_error_response(
            code="forbidden",
            message="Activation access forbidden",
            detail=_DETAIL_FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
        )
    except payments_activation.ActivationNotFoundError:
        return _payment_error_response(
            code="not_found",
            message="Activation not found",
            detail=_DETAIL_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except payments_activation.IdempotencyConflictError:
        return _payment_error_response(
            code="idempotency_conflict",
            message="client_event_id conflict",
            detail=_DETAIL_IDEMPOTENCY_CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
        )
    except payments_activation.ActivationStateError as exc:
        return _payment_error_response(
            code="invalid_reconcile_state",
            message="Reconcile state invalid",
            detail=_activation_state_detail(exc),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


@router.get(
    "/ru-by/reconcile/{intent_id}",
    response_model=SubscriptionActivationResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: _RESPONSE_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN: {
            "description": "Activation access forbidden",
            "model": PaymentErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Activation not found",
            "model": PaymentErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: _RESPONSE_422_VALIDATION_OR_PAYMENT,
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
    except payments_activation.ActivationAccessForbiddenError:
        return _payment_error_response(
            code="forbidden",
            message="Activation access forbidden",
            detail=_DETAIL_FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if activation is None:
        return _payment_error_response(
            code="not_found",
            message="Activation not found",
            detail=_DETAIL_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if activation.payment_source == "ios_app_store":
        return _payment_error_response(
            code="invalid_reconcile_state",
            message="Reconcile state invalid",
            detail=_DETAIL_MANUAL_STATUS_UNSUPPORTED,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return activation
