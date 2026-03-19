# -*- coding: utf-8 -*-
"""Canonical billing endpoints for RU/BY + iOS payment baseline.

RU: Канонические billing endpoints для RU/BY + iOS baseline.
EN: Canonical billing endpoints for RU/BY + iOS baseline.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI

from app.routers.api_key import api_key_header
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_APPLE_VERIFY,
    limit_if_available,
)
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

logger = logging.getLogger(__name__)
_APP_MODULE = None

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


def _validate_billing_transport_key(
    x_api_key: Optional[str],
    *,
    validator_resolver: Callable[[], Callable[..., str] | None],
) -> str:
    """Validate billing transport auth with a strict app-level key validator.

    RU: manual RU/BY routes остаются pre-entitlement, но не принимают произвольный
    непустой ключ. Transport-auth carveout не ослабляет валидацию ключа.
    EN: manual RU/BY routes remain pre-entitlement, but they do not accept an
    arbitrary non-empty key. The transport-auth carveout does not weaken key validation.
    """
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

    app_get_api_key = validator_resolver()
    if not callable(app_get_api_key):
        logger.error("Billing transport key validation is unavailable")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        )

    try:
        result = app_get_api_key(normalized_api_key)
    except HTTPException as exc:
        logger.warning("Billing transport key rejected by app-level validator")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for billing verification",
            headers={"WWW-Authenticate": "ApiKey"},
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Billing transport key validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        ) from exc

    if not isinstance(result, str):
        logger.error("Billing transport key validator returned non-string result")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        )
    return result


def _require_billing_transport_key(
    x_api_key: Optional[str] = Security(api_key_header),
) -> str:
    """Require a strict validated transport API key for billing verification."""
    return _validate_billing_transport_key(
        x_api_key,
        validator_resolver=_get_app_get_api_key,
    )


def _require_manual_billing_transport_key(
    x_api_key: Optional[str] = Security(api_key_header),
) -> str:
    """Require transport auth for manual RU/BY routes before entitlement exists.

    RU: это pre-entitlement transport-auth carveout, а не entitlement truth;
    route не требует entitlement, но всё равно требует валидированный transport key.
    EN: this is a pre-entitlement transport-auth carveout, not entitlement truth;
    the route does not require entitlement, but it still requires a validated transport key.
    """
    return _validate_billing_transport_key(
        x_api_key,
        validator_resolver=_get_effective_app_get_api_key,
    )


def _get_app_get_api_key():
    """Resolve the strict app-level API-key validator from the app module."""
    global _APP_MODULE
    if _APP_MODULE is None:
        import app as app_module

        _APP_MODULE = app_module

    return getattr(_APP_MODULE, "get_api_key", None)


def _get_effective_app_get_api_key():
    """Resolve the effective app-level API-key validator, honoring overrides."""
    app_get_api_key = _get_app_get_api_key()
    if not callable(app_get_api_key):
        return None

    try:
        from app.main import app as fastapi_app
    except Exception:  # pragma: no cover - defensive import guard
        return app_get_api_key

    dependency_overrides = getattr(fastapi_app, "dependency_overrides", None) or {}
    override = dependency_overrides.get(app_get_api_key)
    if callable(override):
        return override
    return app_get_api_key


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
        **RATE_LIMIT_429_RESPONSES,
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
@limit_if_available(RATE_LIMIT_APPLE_VERIFY)
async def verify_apple_receipt(
    request: Request,
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
    x_api_key: str = Depends(_require_manual_billing_transport_key),
) -> SubscriptionActivationResponse | JSONResponse:
    """Create manual RU/BY payment intent on a pre-entitlement transport-auth surface."""
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
    x_api_key: str = Depends(_require_manual_billing_transport_key),
) -> SubscriptionActivationResponse | JSONResponse:
    """Apply reconciliation decision on a pre-entitlement transport-auth surface."""
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
    x_api_key: str = Depends(_require_manual_billing_transport_key),
) -> SubscriptionActivationResponse | JSONResponse:
    """Fetch manual payment reconciliation status on a pre-entitlement transport-auth surface."""
    issuer = _issuer_from_api_key(x_api_key)
    try:
        activation = payments_activation.get_reconcile_activation_status(
            intent_id,
            issuer=issuer,
        )
    except payments_activation.ActivationAccessForbiddenError:
        return _payment_error_response(
            code="forbidden",
            message="Activation access forbidden",
            detail=_DETAIL_FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
        )
    except payments_activation.ActivationStateError as exc:
        return _payment_error_response(
            code="invalid_reconcile_state",
            message="Reconcile state invalid",
            detail=_activation_state_detail(exc),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if activation is None:
        return _payment_error_response(
            code="not_found",
            message="Activation not found",
            detail=_DETAIL_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return activation
