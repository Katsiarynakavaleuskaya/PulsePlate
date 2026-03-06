# -*- coding: utf-8 -*-
"""In-memory payment activation service for baseline RU/BY + iOS contracts.

RU: Временный in-memory сервис активации подписок (contract-first фаза).
EN: Temporary in-memory subscription activation service (contract-first phase).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import threading
from typing import Any
from uuid import uuid4

from app.schemas.payments import (
    ActivateSubscriptionRequest,
    ActivationStatus,
    AppleReceiptVerificationRequest,
    ManualRailIntentRequest,
    ManualRailReconcileRequest,
    PaymentSource,
    ReconcileStatus,
    ReconcileDecision,
    SubscriptionPlan,
    SubscriptionActivationResponse,
    SubscriptionTierValue,
)

_LOCK = threading.Lock()
_ACTIVATIONS: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY_EVENTS: dict[tuple[str, str], tuple[str, str]] = {}
_RECONCILE_EVENTS: dict[tuple[str, str, str], tuple[str, str]] = {}


class ActivationAccessForbiddenError(PermissionError):
    """Raised when issuer attempts to read another issuer's activation."""


class ActivationNotFoundError(LookupError):
    """Raised when activation record is missing."""


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused with a different payload."""


class ActivationStateError(ValueError):
    """Raised when activation transition is not allowed."""


def _utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _payload_hash(payload: dict[str, Any]) -> str:
    """Build stable payload hash for idempotency validation."""
    dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _resolve_statuses(
    source: PaymentSource,
    verification_ok: bool | None,
) -> tuple[ActivationStatus, ReconcileStatus]:
    """Resolve baseline statuses without external provider calls."""
    if source is PaymentSource.ios_app_store:
        if verification_ok is True:
            return ActivationStatus.active, ReconcileStatus.verified
        if verification_ok is False:
            return ActivationStatus.rejected, ReconcileStatus.rejected
        return ActivationStatus.pending_verification, ReconcileStatus.pending

    # RU: Manual rails проходят через reconcile-флоу, поэтому стартуют с pending.
    # EN: Manual rails start as pending until reconciliation completes.
    return ActivationStatus.pending_verification, ReconcileStatus.pending


def _plan_to_tier(plan: SubscriptionPlan) -> SubscriptionTierValue:
    """Map canonical plan code to canonical subscription tier."""
    if plan is SubscriptionPlan.vip_monthly:
        return SubscriptionTierValue.vip
    if plan is SubscriptionPlan.pro_monthly:
        return SubscriptionTierValue.pro
    raise ValueError(f"unsupported subscription plan: {plan}")


def issuer_from_api_key(api_key: str) -> str:
    """Return deterministic opaque issuer marker from API key."""
    from core.fingerprint_security import compute_secret_marker

    if not api_key:
        return "api_key:anonymous"
    marker = compute_secret_marker(api_key, truncate=32)
    return f"api_key:{marker}"


def activate_subscription(
    *,
    issuer: str,
    payload: ActivateSubscriptionRequest,
) -> tuple[SubscriptionActivationResponse, bool]:
    """Create activation record or return idempotent replay.

    Returns:
        (response, created_new)
    """
    request_payload = payload.model_dump(mode="json")
    fingerprint = _payload_hash(request_payload)
    idempotency_key = (issuer, payload.client_event_id)
    now = _utc_now()

    with _LOCK:
        existing_event = _IDEMPOTENCY_EVENTS.get(idempotency_key)
        if existing_event is not None:
            activation_id, existing_hash = existing_event
            if existing_hash != fingerprint:
                raise IdempotencyConflictError("client_event_id conflict: payload mismatch")
            replay_data = deepcopy(_ACTIVATIONS[activation_id])
            replay: SubscriptionActivationResponse = SubscriptionActivationResponse.model_validate(
                replay_data
            )
            return replay, False

        status, reconcile_status = _resolve_statuses(payload.source, payload.verification_ok)
        verified_at = (
            now
            if reconcile_status in {ReconcileStatus.verified, ReconcileStatus.rejected}
            else None
        )
        subscription_tier = _plan_to_tier(payload.plan)

        activation_id = str(uuid4())
        stored: dict[str, Any] = {
            "activation_id": activation_id,
            "intent_id": activation_id,
            "audit_id": activation_id,
            "issuer": issuer,
            "payment_source": payload.source.value,
            "plan": payload.plan.value,
            "subscription_tier": subscription_tier.value,
            "status": status.value,
            "reconcile_status": reconcile_status.value,
            "external_txn_id": payload.external_txn_id,
            "verified_at": verified_at.isoformat() if verified_at is not None else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        _ACTIVATIONS[activation_id] = stored
        _IDEMPOTENCY_EVENTS[idempotency_key] = (activation_id, fingerprint)

        created: SubscriptionActivationResponse = SubscriptionActivationResponse.model_validate(
            deepcopy(stored)
        )
        return created, True


def get_activation(
    activation_id: str,
    *,
    issuer: str,
) -> SubscriptionActivationResponse | None:
    """Fetch activation by id with issuer-level access control."""
    with _LOCK:
        stored = _ACTIVATIONS.get(activation_id)
        if stored is None:
            return None
        if stored.get("issuer") != issuer:
            raise ActivationAccessForbiddenError("activation access forbidden")
        response: SubscriptionActivationResponse = SubscriptionActivationResponse.model_validate(
            deepcopy(stored)
        )
        return response


def build_ios_activation_request(
    *,
    payload: AppleReceiptVerificationRequest,
) -> ActivateSubscriptionRequest:
    """Convert receipt verification request into canonical activation request."""
    verification_ok = len(payload.receipt.strip()) >= 12
    verification_payload = {"receipt": payload.receipt}
    return ActivateSubscriptionRequest(
        source=PaymentSource.ios_app_store,
        plan=payload.plan,
        client_event_id=payload.client_event_id,
        external_txn_id=payload.external_txn_id,
        verification_ok=verification_ok,
        verification_payload=verification_payload,
    )


def build_manual_intent_request(
    *,
    payload: ManualRailIntentRequest,
) -> ActivateSubscriptionRequest:
    """Convert manual rail intent request into canonical activation request."""
    verification_payload = {
        **payload.verification_payload,
        "amount_minor": payload.amount_minor,
        "currency": payload.currency.value,
    }
    return ActivateSubscriptionRequest(
        source=PaymentSource(payload.source.value),
        plan=payload.plan,
        client_event_id=payload.client_event_id,
        external_txn_id=payload.external_txn_id,
        verification_ok=None,
        verification_payload=verification_payload,
    )


def reconcile_activation(
    *,
    issuer: str,
    payload: ManualRailReconcileRequest,
) -> SubscriptionActivationResponse:
    """Apply deterministic reconciliation to manual payment intents."""
    request_payload = payload.model_dump(mode="json")
    fingerprint = _payload_hash(request_payload)
    idempotency_key = (issuer, payload.intent_id, payload.client_event_id)
    now = _utc_now()

    with _LOCK:
        existing_event = _RECONCILE_EVENTS.get(idempotency_key)
        if existing_event is not None:
            activation_id, existing_hash = existing_event
            if existing_hash != fingerprint:
                raise IdempotencyConflictError(
                    "client_event_id conflict: reconcile payload mismatch"
                )
            replay_data = deepcopy(_ACTIVATIONS[activation_id])
            replay: SubscriptionActivationResponse = SubscriptionActivationResponse.model_validate(
                replay_data
            )
            return replay

        stored = _ACTIVATIONS.get(payload.intent_id)
        if stored is None:
            raise ActivationNotFoundError("activation not found")
        if stored.get("issuer") != issuer:
            raise ActivationAccessForbiddenError("activation access forbidden")
        source = stored.get("payment_source")
        if source == PaymentSource.ios_app_store.value:
            raise ActivationStateError("ios_app_store activation cannot be reconciled manually")
        if stored.get("reconcile_status") != ReconcileStatus.pending.value:
            raise ActivationStateError("manual reconcile transition requires pending state")

        decision = payload.decision
        status = (
            ActivationStatus.active
            if decision is ReconcileDecision.verified
            else ActivationStatus.rejected
        )
        stored["reconcile_status"] = decision.value
        stored["status"] = status.value
        stored["verified_at"] = now.isoformat()
        if payload.external_txn_id is not None:
            stored["external_txn_id"] = payload.external_txn_id
        stored["updated_at"] = now.isoformat()
        _RECONCILE_EVENTS[idempotency_key] = (payload.intent_id, fingerprint)

        response: SubscriptionActivationResponse = SubscriptionActivationResponse.model_validate(
            deepcopy(stored)
        )
        return response


def reset_state() -> None:
    """Reset in-memory state for deterministic tests."""
    with _LOCK:
        _ACTIVATIONS.clear()
        _IDEMPOTENCY_EVENTS.clear()
        _RECONCILE_EVENTS.clear()
