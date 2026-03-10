# -*- coding: utf-8 -*-
"""In-memory payment activation service for baseline RU/BY + iOS contracts.

RU: Временный in-memory сервис активации подписок (contract-first фаза).
EN: Temporary in-memory subscription activation service (contract-first phase).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import httpx
import json
import threading
from typing import Any
from uuid import uuid4

from app.schemas.payments import (
    ActivateSubscriptionRequest,
    ActivationStatus,
    AppleActivationHint,
    AppleProviderError,
    AppleReceiptVerificationResponse,
    AppleVerificationEnvironment,
    AppleVerificationState,
    ManualRailIntentRequest,
    ManualRailReconcileRequest,
    PaymentSource,
    ReconcileStatus,
    ReconcileDecision,
    SubscriptionPlan,
    SubscriptionActivationResponse,
    SubscriptionTierValue,
)
from settings import require_apple_shared_secret

_LOCK = threading.Lock()
_ACTIVATIONS: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY_EVENTS: dict[tuple[str, str], tuple[str, str]] = {}
_RECONCILE_EVENTS: dict[tuple[str, str, str], tuple[str, str]] = {}

APPLE_VERIFY_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_VERIFY_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_SANDBOX_RECEIPT_STATUS = 21007
APPLE_EXPIRED_RECEIPT_STATUS = 21006
APPLE_VERIFY_TIMEOUT_SECONDS = 10.0
APPLE_ETC_GMT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S Etc/GMT"


class ActivationAccessForbiddenError(PermissionError):
    """Raised when issuer attempts to read another issuer's activation."""


class ActivationNotFoundError(LookupError):
    """Raised when activation record is missing."""


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused with a different payload."""


class ActivationStateError(ValueError):
    """Raised when activation transition is not allowed."""


class AppleVerifyTransportError(RuntimeError):
    """Base exception for operational Apple receipt verification failures."""

    status_code = 502
    error_code = "APPLE_UPSTREAM_ERROR"
    error_message = "Apple receipt verification failed"


class AppleVerifyTimeoutError(AppleVerifyTransportError):
    """Raised when Apple receipt verification times out."""

    status_code = 504
    error_code = "APPLE_VERIFY_TIMEOUT"
    error_message = "Apple receipt verification timed out"


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


def _apple_request_body(receipt_data: str) -> dict[str, Any]:
    """Build transitional server-side Apple verifyReceipt payload."""
    return {
        "receipt-data": receipt_data,
        "password": require_apple_shared_secret(),
        "exclude-old-transactions": True,
    }


async def _call_apple_verify_endpoint(url: str, receipt_data: str) -> dict[str, Any]:
    """Call Apple verifyReceipt endpoint and return parsed JSON response."""
    try:
        request_body = _apple_request_body(receipt_data)
    except RuntimeError as exc:
        raise AppleVerifyTransportError from exc

    try:
        async with httpx.AsyncClient(timeout=APPLE_VERIFY_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise AppleVerifyTimeoutError from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise AppleVerifyTransportError from exc

    if not isinstance(payload, dict):
        raise AppleVerifyTransportError
    apple_payload: dict[str, Any] = payload
    return apple_payload


def _coerce_apple_status(raw_status: Any) -> int | None:
    """Convert Apple status payload field to int when possible."""
    if isinstance(raw_status, bool):
        return None
    if isinstance(raw_status, int):
        return raw_status
    if isinstance(raw_status, str) and raw_status.strip():
        try:
            return int(raw_status.strip())
        except ValueError:
            return None
    return None


def _parse_apple_datetime(raw_value: Any) -> datetime | None:
    """Parse Apple datetime values expressed as ms since epoch or ISO string."""
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, datetime):
        if raw_value.tzinfo is None:
            return raw_value.replace(tzinfo=timezone.utc)
        return raw_value.astimezone(timezone.utc)
    if isinstance(raw_value, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw_value) / 1000.0, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            try:
                return datetime.fromtimestamp(int(normalized) / 1000.0, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        try:
            return datetime.strptime(
                normalized,
                APPLE_ETC_GMT_DATETIME_FORMAT,
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        iso_value = normalized.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _first_present_entry_value(entry: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty provider field from a receipt entry."""
    for key in keys:
        value = entry.get(key)
        if value not in (None, ""):
            return value
    return None


def _entry_expires_at(entry: dict[str, Any]) -> datetime | None:
    """Return normalized Apple receipt expiry when present."""
    return _parse_apple_datetime(
        _first_present_entry_value(entry, "expires_date_ms", "expires_date")
    )


def _entry_has_expiry_value(entry: dict[str, Any]) -> bool:
    """Return whether Apple provided an expiry value that must be parseable."""
    return _first_present_entry_value(entry, "expires_date_ms", "expires_date") is not None


def _receipt_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return candidate receipt entries from Apple verification response."""
    latest_info = payload.get("latest_receipt_info")
    if isinstance(latest_info, list):
        entries = [entry for entry in latest_info if isinstance(entry, dict)]
        if entries:
            return entries

    receipt = payload.get("receipt")
    if isinstance(receipt, dict):
        in_app = receipt.get("in_app")
        if isinstance(in_app, list):
            entries = [entry for entry in in_app if isinstance(entry, dict)]
            if entries:
                return entries
    return []


def _entry_sort_key(entry: dict[str, Any]) -> tuple[float, float]:
    """Return deterministic ordering key for Apple receipt entries."""
    expires_at = _entry_expires_at(entry)
    purchase_at = _parse_apple_datetime(
        _first_present_entry_value(entry, "purchase_date_ms", "purchase_date")
    )
    expires_ts = expires_at.timestamp() if expires_at is not None else float("-inf")
    purchase_ts = purchase_at.timestamp() if purchase_at is not None else float("-inf")
    return (expires_ts, purchase_ts)


def _select_latest_receipt_entry(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Select the most relevant Apple receipt entry from provider payload."""
    entries = _receipt_entries(payload)
    if not entries:
        return None
    return max(entries, key=_entry_sort_key)


def _has_reliable_restore_signal(
    payload: dict[str, Any],
    entry: dict[str, Any],
) -> bool:
    """Return True only for explicit restore-specific provider/orchestration signals."""
    if payload.get("restore_detected") is True:
        return True
    if payload.get("restored") is True:
        return True
    if entry.get("restore_detected") is True:
        return True
    if entry.get("restored") is True:
        return True
    return False


def _entry_cancellation_at(entry: dict[str, Any]) -> datetime | None:
    """Return Apple cancellation timestamp for refunded/revoked transactions."""
    return _parse_apple_datetime(
        _first_present_entry_value(entry, "cancellation_date_ms", "cancellation_date")
    )


def _activation_payload_for_product(product_id: str | None) -> AppleActivationHint | None:
    """Map Apple product identifiers to downstream activation-prep hints."""
    if not product_id:
        return None
    normalized = product_id.strip().lower()
    if normalized.startswith("com.pulseplate.premium.") or normalized.startswith(
        "com.pulseplate.pro."
    ):
        return AppleActivationHint(tier=SubscriptionTierValue.pro)
    if normalized.startswith("com.pulseplate.vip."):
        return AppleActivationHint(tier=SubscriptionTierValue.vip)
    return None


def _build_invalid_verification_response(
    *,
    environment: AppleVerificationEnvironment | None,
    product_id: str | None = None,
    expires_at: datetime | None = None,
    code: str,
    message: str,
    verification_state: AppleVerificationState,
) -> AppleReceiptVerificationResponse:
    """Return normalized invalid/expired Apple verification response."""
    return AppleReceiptVerificationResponse(
        verified=False,
        verification_state=verification_state,
        environment=environment,
        product_id=product_id,
        expires_at=expires_at,
        error=AppleProviderError(code=code, message=message),
    )


def _normalize_apple_verification(
    *,
    payload: dict[str, Any],
    environment: AppleVerificationEnvironment,
) -> AppleReceiptVerificationResponse:
    """Normalize raw Apple provider payload into canonical verification result."""
    status = _coerce_apple_status(payload.get("status"))
    latest_entry = _select_latest_receipt_entry(payload)
    product_id = None
    expires_at = None
    if latest_entry is not None:
        raw_product_id = latest_entry.get("product_id")
        if isinstance(raw_product_id, str):
            product_id = raw_product_id.strip() or None
        expires_at = _entry_expires_at(latest_entry)
        if _entry_has_expiry_value(latest_entry) and expires_at is None:
            return _build_invalid_verification_response(
                environment=environment,
                product_id=product_id,
                code="APPLE_RECEIPT_INVALID",
                message="Receipt verification failed",
                verification_state=AppleVerificationState.invalid,
            )
        cancellation_at = _entry_cancellation_at(latest_entry)
        if cancellation_at is not None:
            return _build_invalid_verification_response(
                environment=environment,
                product_id=product_id,
                expires_at=expires_at,
                code="APPLE_RECEIPT_INVALID",
                message="Receipt verification failed",
                verification_state=AppleVerificationState.invalid,
            )

    if status == APPLE_EXPIRED_RECEIPT_STATUS:
        return _build_invalid_verification_response(
            environment=environment,
            product_id=product_id,
            expires_at=expires_at,
            code="APPLE_RECEIPT_EXPIRED",
            message="Apple receipt is expired",
            verification_state=AppleVerificationState.expired,
        )

    if status != 0:
        return _build_invalid_verification_response(
            environment=environment,
            product_id=product_id,
            expires_at=expires_at,
            code="APPLE_RECEIPT_INVALID",
            message="Receipt verification failed",
            verification_state=AppleVerificationState.invalid,
        )

    if latest_entry is None:
        return _build_invalid_verification_response(
            environment=environment,
            code="APPLE_RECEIPT_INVALID",
            message="Receipt verification failed",
            verification_state=AppleVerificationState.invalid,
        )

    if expires_at is not None and expires_at <= _utc_now():
        return _build_invalid_verification_response(
            environment=environment,
            product_id=product_id,
            expires_at=expires_at,
            code="APPLE_RECEIPT_EXPIRED",
            message="Apple receipt is expired",
            verification_state=AppleVerificationState.expired,
        )

    activation_payload = _activation_payload_for_product(product_id)
    if activation_payload is None:
        return _build_invalid_verification_response(
            environment=environment,
            product_id=product_id,
            expires_at=expires_at,
            code="APPLE_RECEIPT_INVALID",
            message="Receipt verification failed",
            verification_state=AppleVerificationState.invalid,
        )

    verification_state = (
        AppleVerificationState.restored
        if _has_reliable_restore_signal(payload, latest_entry)
        else AppleVerificationState.active
    )
    return AppleReceiptVerificationResponse(
        verified=True,
        verification_state=verification_state,
        environment=environment,
        product_id=product_id,
        expires_at=expires_at,
        activation_payload=activation_payload,
    )


def issuer_from_api_key(api_key: str) -> str:
    """Return deterministic opaque issuer marker from API key."""
    from core.fingerprint_security import compute_secret_marker

    normalized_api_key = api_key.strip()
    if not normalized_api_key:
        raise ValueError("api_key is required for issuer derivation")
    marker = compute_secret_marker(normalized_api_key, truncate=32)
    return f"api_key:{marker}"


async def verify_apple_receipt(receipt_data: str) -> AppleReceiptVerificationResponse:
    """Verify Apple receipt via transitional server-only verifyReceipt flow.

    RU: Всегда идём в production first и делаем ровно один sandbox fallback на статусе 21007.
    EN: Always use production first with a single sandbox fallback on Apple status 21007.
    """
    production_payload = await _call_apple_verify_endpoint(
        APPLE_VERIFY_PRODUCTION_URL,
        receipt_data,
    )
    production_status = _coerce_apple_status(production_payload.get("status"))
    if production_status == APPLE_SANDBOX_RECEIPT_STATUS:
        sandbox_payload = await _call_apple_verify_endpoint(
            APPLE_VERIFY_SANDBOX_URL,
            receipt_data,
        )
        return _normalize_apple_verification(
            payload=sandbox_payload,
            environment=AppleVerificationEnvironment.sandbox,
        )

    return _normalize_apple_verification(
        payload=production_payload,
        environment=AppleVerificationEnvironment.production,
    )


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
