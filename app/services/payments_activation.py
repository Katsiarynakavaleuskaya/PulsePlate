# -*- coding: utf-8 -*-
"""DB-backed payment activation service for billing verify + activation runtime.

RU: DB-backed сервис для Apple verify и persisted subscription activation state.
EN: DB-backed service for Apple verify and persisted subscription activation state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import hmac
import httpx
import json
from typing import Any, Literal, cast, overload
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.models import Subscription, SubscriptionActivationAudit
from app.schemas.payments import (
    ActivateSubscriptionRequest,
    AppleProviderError,
    AppleReceiptVerificationResponse,
    AppleVerificationEnvironment,
    AppleVerificationState,
    IOSAppStoreActivationPayload,
    IOSVerifiedActivationResult,
    IosVerificationStatus,
    ManualActivationPayload,
    ManualRailIntentRequest,
    ManualRailReconcileRequest,
    PaymentPlatform,
    PaymentSource,
    ReconcileDecision,
    ReconcileStatus,
    SubscriptionActivationResponse,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
    SubscriptionTierValue,
)
from app.services import subscriptions as subscriptions_store
from core.billing_policy import manual_monthly_entitlement_expires_at
from core.db import get_session_factory
from settings import require_apple_shared_secret

APPLE_VERIFY_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_VERIFY_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_SANDBOX_RECEIPT_STATUS = 21007
APPLE_EXPIRED_RECEIPT_STATUS = 21006
APPLE_VERIFY_TIMEOUT_SECONDS = 10.0
APPLE_ETC_GMT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S Etc/GMT"
_LEGACY_ISSUER_PREFIX = "subject:"
_ACTIVATIONS: dict[str, dict[str, Any]] = {}


class ActivationAccessForbiddenError(PermissionError):
    """Raised when a user attempts to read another user's activation."""


class ActivationNotFoundError(LookupError):
    """Raised when activation record is missing."""


class IdempotencyConflictError(ValueError):
    """Raised when a deterministic idempotency key is reused with a different payload."""


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


class ActivationReverifyRejectedError(ValueError):
    """Raised when iOS activation cannot be completed because server-side receipt reverification failed."""

    status_code = 403
    error_code = "activation_reverify_rejected"
    error_message = "Apple receipt verification required for activation"


@dataclass(frozen=True)
class NormalizedActivation:
    """Internal normalized activation state before persistence."""

    source: PaymentSource
    tier: SubscriptionTier
    status: SubscriptionStatus
    platform: PaymentPlatform
    idempotency_key: str
    payload_hash: str
    source_reference: str | None
    product_id: str | None
    expires_at: datetime | None
    activated_at: datetime | None
    provider_receipt_hash: str | None
    submitted_amount_minor: int | None
    submitted_currency: str | None
    requested_plan: SubscriptionPlan | None
    external_txn_id: str | None
    reconcile_status: ReconcileStatus
    evidence_summary: dict[str, Any]


def _utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _hash_payload(payload: dict[str, Any]) -> str:
    """Build stable payload hash for deterministic idempotency validation."""

    dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _hash_receipt(receipt_data: str | None) -> str | None:
    """Hash receipt content before persistence to avoid storing raw provider artifacts."""

    if receipt_data is None:
        return None
    return hashlib.sha256(receipt_data.encode("utf-8")).hexdigest()


def validate_webhook_signature(secret: str, payload: bytes, signature: str) -> bool:
    """Validate webhook payload signature before state transition.

    Contract:
    - HMAC-SHA256 hex digest over the exact raw HTTP request body bytes.
    - Secret bytes are used exactly as configured.
    - Signature comparison is fail-closed.
    - Hex casing is normalized, but whitespace is significant.

    Returns True if signature is valid, otherwise False.
    """
    if not secret:
        return False
    if not signature:
        return False

    try:
        provided_signature = signature.encode("ascii").decode("ascii").lower()
    except UnicodeEncodeError:
        return False

    if len(provided_signature) != 64:
        return False
    if any(ch not in "0123456789abcdef" for ch in provided_signature):
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, provided_signature)


def _amount_to_minor_units(submitted_amount: str | None) -> int | None:
    """Convert human-readable amount into minor currency units."""

    if submitted_amount is None:
        return None
    try:
        amount = Decimal(submitted_amount)
    except InvalidOperation as exc:
        raise ValueError("submitted_amount must be a valid decimal string") from exc

    if amount < 0:
        raise ValueError("submitted_amount must be non-negative")

    normalized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(normalized * 100)


def _plan_to_tier(plan: SubscriptionPlan) -> SubscriptionTierValue:
    """Map plan to legacy paid-tier response."""

    if plan is SubscriptionPlan.vip_monthly:
        return SubscriptionTierValue.vip
    if plan is SubscriptionPlan.pro_monthly:
        return SubscriptionTierValue.pro
    raise ValueError(f"unsupported subscription plan: {plan}")


def _plan_to_subscription_tier(plan: SubscriptionPlan) -> SubscriptionTier:
    """Map plan to persisted subscription tier."""

    return SubscriptionTier(_plan_to_tier(plan).value)


def _manual_plan_expires_at(*, plan: SubscriptionPlan, activated_at: datetime) -> datetime:
    """Derive bounded expiry for verified manual monthly plans.

    RU: Manual monthly plans должны получать детерминированный bounded expiry.
    EN: Verified manual monthly plans must persist a deterministic bounded expiry.
    """

    if plan not in {SubscriptionPlan.pro_monthly, SubscriptionPlan.vip_monthly}:
        raise ValueError(f"unsupported subscription plan: {plan}")
    return manual_monthly_entitlement_expires_at(activated_at=activated_at)


def _reconcile_status_from_subscription_status(
    *,
    status: SubscriptionStatus,
) -> ReconcileStatus:
    """Map persisted status into legacy reconcile status vocabulary."""

    if status in {
        SubscriptionStatus.pending_manual_review,
        SubscriptionStatus.pending_verification,
    }:
        return ReconcileStatus.pending
    if status is SubscriptionStatus.rejected:
        return ReconcileStatus.rejected
    if status in {SubscriptionStatus.active, SubscriptionStatus.expired}:
        return ReconcileStatus.verified
    return ReconcileStatus.not_required


def _parse_optional_plan(raw_value: Any) -> SubscriptionPlan | None:
    """Parse optional plan value from evidence summary."""

    if not isinstance(raw_value, str):
        return None
    try:
        return SubscriptionPlan(raw_value)
    except ValueError:
        return None


def _parse_optional_subscription_tier_value(raw_value: Any) -> SubscriptionTierValue | None:
    """Parse optional legacy tier from evidence summary."""

    if not isinstance(raw_value, str):
        return None
    try:
        return SubscriptionTierValue(raw_value)
    except ValueError:
        return None


def _response_tier_value(
    *,
    tier: SubscriptionTier,
    evidence_summary: dict[str, Any],
) -> SubscriptionTierValue | None:
    """Resolve legacy subscription_tier field for compatibility responses."""

    tier_value = _parse_optional_subscription_tier_value(evidence_summary.get("subscription_tier"))
    if tier_value is not None:
        return tier_value
    if tier in {SubscriptionTier.pro, SubscriptionTier.vip}:
        return SubscriptionTierValue(tier.value)
    return None


def _resolve_user_id(
    *,
    user_id: int | None,
    issuer: str | None,
) -> int:
    """Resolve canonical user id from the new or legacy principal contract."""

    if user_id is not None:
        return user_id
    if issuer is None:
        raise ValueError("user_id or issuer is required")
    if not issuer.startswith(_LEGACY_ISSUER_PREFIX):
        raise ValueError("issuer is invalid")
    raw_subject = issuer.removeprefix(_LEGACY_ISSUER_PREFIX)
    if not raw_subject.isdigit():
        raise ValueError("issuer is invalid")
    return int(raw_subject)


def _legacy_response_mode(*, user_id: int | None, issuer: str | None) -> bool:
    """Return True for legacy callers that expect `(response, is_new)` tuple semantics."""

    return user_id is None and issuer is not None


def _build_audit_evidence(
    *,
    normalized: NormalizedActivation,
    base_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build persisted evidence summary without raw provider secrets."""

    evidence = dict(base_evidence or {})
    evidence.update(normalized.evidence_summary)
    if normalized.requested_plan is not None:
        evidence["requested_plan"] = normalized.requested_plan.value
    tier_value = _response_tier_value(
        tier=normalized.tier,
        evidence_summary=evidence,
    )
    if tier_value is not None:
        evidence["subscription_tier"] = tier_value.value
    evidence["reconcile_status"] = normalized.reconcile_status.value
    if normalized.external_txn_id is not None:
        evidence["external_txn_id"] = normalized.external_txn_id
    return evidence


def _build_idempotency_key(prefix: str, *parts: str) -> str:
    """Build bounded deterministic idempotency keys from normalized parts."""

    joined_parts = "|".join(parts)
    digest = hashlib.sha256(joined_parts.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _normalize_canonical_ios_activation(
    *,
    payload: ActivateSubscriptionRequest,
    verification_result: IOSVerifiedActivationResult,
) -> NormalizedActivation:
    """Normalize iOS activation from the PR-1 verification contract."""

    ios_payload = payload.get_ios_payload()
    status = SubscriptionStatus(verification_result.status.value)
    reconcile_status = ReconcileStatus.verified
    activated_at = _utc_now() if status is SubscriptionStatus.active else None
    receipt_hash = _hash_receipt(ios_payload.receipt_data)
    safe_payload = payload.model_dump(mode="json", exclude_none=True)
    return NormalizedActivation(
        source=PaymentSource.ios_app_store,
        tier=SubscriptionTier(verification_result.subscription_tier.value),
        status=status,
        platform=verification_result.platform,
        idempotency_key=_build_idempotency_key(
            PaymentSource.ios_app_store.value,
            verification_result.transaction_id,
        ),
        payload_hash=_hash_payload(safe_payload),
        source_reference=verification_result.transaction_id,
        product_id=verification_result.product_id,
        expires_at=verification_result.expires_at,
        activated_at=activated_at,
        provider_receipt_hash=receipt_hash,
        submitted_amount_minor=None,
        submitted_currency=None,
        requested_plan=None,
        external_txn_id=None,
        reconcile_status=reconcile_status,
        evidence_summary={
            "transaction_id": verification_result.transaction_id,
            "original_transaction_id": verification_result.original_transaction_id,
            "product_id": verification_result.product_id,
            "status": verification_result.status.value,
            "expires_at": (
                verification_result.expires_at.isoformat()
                if verification_result.expires_at is not None
                else None
            ),
            "receipt_hash_present": receipt_hash is not None,
        },
    )


def _normalize_canonical_manual_activation(
    *,
    source: PaymentSource,
    manual_payload: ManualActivationPayload,
    request_payload: ActivateSubscriptionRequest,
) -> NormalizedActivation:
    """Normalize canonical manual-rail activation requests."""

    amount_minor = _amount_to_minor_units(manual_payload.submitted_amount)
    safe_payload = request_payload.model_dump(mode="json", exclude_none=True)
    return NormalizedActivation(
        source=source,
        tier=SubscriptionTier.pro,
        status=SubscriptionStatus.pending_manual_review,
        platform=PaymentPlatform.web,
        idempotency_key=_build_idempotency_key(
            source.value,
            manual_payload.source_reference,
        ),
        payload_hash=_hash_payload(safe_payload),
        source_reference=manual_payload.source_reference,
        product_id=None,
        expires_at=None,
        activated_at=None,
        provider_receipt_hash=None,
        submitted_amount_minor=amount_minor,
        submitted_currency=manual_payload.submitted_currency,
        requested_plan=None,
        external_txn_id=None,
        reconcile_status=ReconcileStatus.pending,
        evidence_summary={
            "source_reference": manual_payload.source_reference,
            "submitted_amount_minor": amount_minor,
            "submitted_currency": manual_payload.submitted_currency,
        },
    )


def _resolve_legacy_status(
    *,
    source: PaymentSource,
    verification_ok: bool | None,
) -> tuple[SubscriptionStatus, ReconcileStatus]:
    """Resolve legacy activation statuses used by compatibility routes/tests."""

    if source is PaymentSource.ios_app_store:
        if verification_ok is True:
            return SubscriptionStatus.active, ReconcileStatus.verified
        if verification_ok is False:
            return SubscriptionStatus.rejected, ReconcileStatus.rejected
        return SubscriptionStatus.pending_verification, ReconcileStatus.pending
    return SubscriptionStatus.pending_verification, ReconcileStatus.pending


def _normalize_legacy_activation(
    *,
    payload: ActivateSubscriptionRequest,
) -> NormalizedActivation:
    """Normalize legacy activation requests from the additive billing surface."""

    if payload.plan is None or payload.client_event_id is None:
        raise ValueError("legacy activation requires plan and client_event_id")
    status, reconcile_status = _resolve_legacy_status(
        source=payload.source,
        verification_ok=payload.verification_ok,
    )
    requested_tier = _plan_to_subscription_tier(payload.plan)
    activated_at = _utc_now() if status is SubscriptionStatus.active else None
    raw_product_id = payload.verification_payload.get("product_id")
    product_id = (
        raw_product_id if isinstance(raw_product_id, str) and raw_product_id.strip() else None
    )
    amount_minor = payload.verification_payload.get("amount_minor")
    submitted_amount_minor = amount_minor if isinstance(amount_minor, int) else None
    raw_currency = payload.verification_payload.get("currency")
    submitted_currency = raw_currency if isinstance(raw_currency, str) else None
    raw_receipt = payload.verification_payload.get("receipt")
    receipt_hash = _hash_receipt(raw_receipt if isinstance(raw_receipt, str) else None)
    safe_payload = payload.model_dump(mode="json", exclude_none=True)
    return NormalizedActivation(
        source=payload.source,
        tier=requested_tier,
        status=status,
        platform=(
            PaymentPlatform.ios
            if payload.source is PaymentSource.ios_app_store
            else PaymentPlatform.web
        ),
        idempotency_key=_build_idempotency_key(
            "legacy",
            payload.source.value,
            payload.client_event_id,
        ),
        payload_hash=_hash_payload(safe_payload),
        source_reference=payload.external_txn_id or payload.client_event_id,
        product_id=product_id,
        expires_at=None,
        activated_at=activated_at,
        provider_receipt_hash=receipt_hash,
        submitted_amount_minor=submitted_amount_minor,
        submitted_currency=submitted_currency,
        requested_plan=payload.plan,
        external_txn_id=payload.external_txn_id,
        reconcile_status=reconcile_status,
        evidence_summary={
            "legacy_client_event_id": payload.client_event_id,
            "verification_ok": payload.verification_ok,
            "requested_plan": payload.plan.value,
            "subscription_tier": _plan_to_tier(payload.plan).value,
            "external_txn_id": payload.external_txn_id,
            "submitted_amount_minor": submitted_amount_minor,
            "submitted_currency": submitted_currency,
            "receipt_hash_present": receipt_hash is not None,
        },
    )


def _normalize_activation(
    *,
    payload: ActivateSubscriptionRequest,
) -> NormalizedActivation:
    """Normalize any supported source into the canonical persistence contract."""

    if payload.uses_canonical_payload:
        if payload.source is PaymentSource.ios_app_store:
            return _normalize_canonical_ios_activation(
                payload=payload,
                verification_result=payload.get_ios_payload().verification_result,
            )
        return _normalize_canonical_manual_activation(
            source=payload.source,
            manual_payload=payload.get_manual_payload(),
            request_payload=payload,
        )
    return _normalize_legacy_activation(payload=payload)


def _replay_existing_activation_or_raise(
    *,
    session: Any,
    user_id: int,
    normalized: NormalizedActivation,
    user_id_was_explicit: bool,
    issuer: str | None,
    error: IntegrityError,
) -> SubscriptionActivationResponse | tuple[SubscriptionActivationResponse, bool]:
    """Return replayed activation after a uniqueness race when payload matches."""

    existing_audit = subscriptions_store.get_audit_by_user_key(
        session=session,
        user_id=user_id,
        idempotency_key=normalized.idempotency_key,
    )
    if existing_audit is None:
        raise error
    if existing_audit.payload_hash != normalized.payload_hash:
        raise IdempotencyConflictError("deterministic activation key conflict")
    existing_response = _to_response(
        activation_id=existing_audit.id,
        audit=existing_audit,
    )
    if _legacy_response_mode(user_id=user_id if user_id_was_explicit else None, issuer=issuer):
        return existing_response, False
    return existing_response


def _apply_subscription_state(
    *,
    subscription: Subscription | None,
    user_id: int,
    normalized: NormalizedActivation,
    now: datetime,
) -> Subscription:
    """Create or update the current-state subscription row."""

    if subscription is None:
        subscription = Subscription(
            id=str(uuid4()),
            user_id=user_id,
            source=normalized.source.value,
            tier=normalized.tier.value,
            status=normalized.status.value,
            platform=normalized.platform.value,
            provider_receipt_hash=normalized.provider_receipt_hash,
            source_reference=normalized.source_reference,
            product_id=normalized.product_id,
            expires_at=normalized.expires_at,
            activated_at=normalized.activated_at,
            submitted_amount_minor=normalized.submitted_amount_minor,
            submitted_currency=normalized.submitted_currency,
            created_at=now,
            updated_at=now,
        )
        return subscription

    subscription.tier = normalized.tier.value
    subscription.status = normalized.status.value
    subscription.platform = normalized.platform.value
    subscription.provider_receipt_hash = normalized.provider_receipt_hash
    subscription.source_reference = normalized.source_reference
    subscription.product_id = normalized.product_id
    subscription.expires_at = normalized.expires_at
    subscription.activated_at = normalized.activated_at
    subscription.submitted_amount_minor = normalized.submitted_amount_minor
    subscription.submitted_currency = normalized.submitted_currency
    subscription.updated_at = now
    return subscription


def _coerce_datetime(raw_value: Any) -> datetime | None:
    """Coerce ISO timestamps stored in JSON evidence into aware datetimes."""

    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        if raw_value.tzinfo is None:
            return raw_value.replace(tzinfo=timezone.utc)
        return raw_value.astimezone(timezone.utc)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _to_response(
    *,
    activation_id: str,
    audit: SubscriptionActivationAudit,
    subscription: Subscription | None = None,
    status_override: SubscriptionStatus | None = None,
    reconcile_status_override: ReconcileStatus | None = None,
    external_txn_id_override: str | None = None,
) -> SubscriptionActivationResponse:
    """Convert persisted activation data into API response."""

    evidence_summary = audit.evidence_summary or {}
    source = PaymentSource(audit.source)
    tier = SubscriptionTier((subscription.tier if subscription is not None else audit.tier))
    status = SubscriptionStatus(
        status_override.value
        if status_override is not None
        else (subscription.status if subscription is not None else audit.status)
    )
    platform = PaymentPlatform(
        subscription.platform if subscription is not None else audit.platform
    )
    reconcile_status = (
        reconcile_status_override
        or _parse_optional_reconcile_status(evidence_summary.get("reconcile_status"))
        or _reconcile_status_from_subscription_status(status=status)
    )
    external_txn_id = external_txn_id_override
    if external_txn_id is None:
        raw_external_txn = evidence_summary.get("external_txn_id")
        if isinstance(raw_external_txn, str) and raw_external_txn.strip():
            external_txn_id = raw_external_txn.strip()
    plan = _parse_optional_plan(evidence_summary.get("requested_plan"))
    verified_at = _coerce_datetime(evidence_summary.get("verified_at"))
    if verified_at is None and reconcile_status in {
        ReconcileStatus.verified,
        ReconcileStatus.rejected,
    }:
        verified_at = subscription.updated_at if subscription is not None else audit.created_at
    response: SubscriptionActivationResponse
    response = SubscriptionActivationResponse.model_validate(
        {
            "activation_id": activation_id,
            "user_id": audit.user_id,
            "source": source,
            "tier": tier,
            "status": status,
            "platform": platform,
            "product_id": subscription.product_id if subscription is not None else audit.product_id,
            "source_reference": (
                subscription.source_reference
                if subscription is not None
                else audit.source_reference
            ),
            "expires_at": subscription.expires_at if subscription is not None else audit.expires_at,
            "activated_at": (
                subscription.activated_at if subscription is not None else audit.activated_at
            ),
            "intent_id": activation_id,
            "audit_id": audit.id,
            "payment_source": source,
            "plan": plan,
            "subscription_tier": _response_tier_value(
                tier=tier,
                evidence_summary=evidence_summary,
            ),
            "reconcile_status": reconcile_status,
            "external_txn_id": external_txn_id,
            "verified_at": verified_at,
            "created_at": audit.created_at,
            "updated_at": subscription.updated_at if subscription is not None else audit.created_at,
        }
    )
    return response


def _current_response_overrides(
    *,
    session: Any,
    audit: SubscriptionActivationAudit,
) -> tuple[Subscription | None, ReconcileStatus | None, str | None]:
    """Return current-state overrides for activation read paths.

    RU: Для readback-эндпоинтов источником истины остаётся текущее persisted
    subscription state, а не исторический audit snapshot.
    EN: For readback endpoints, current persisted subscription state remains the
    source of truth rather than the historical audit snapshot.
    """

    subscription = subscriptions_store.get_subscription_by_id(
        session=session,
        subscription_id=audit.subscription_id,
    )
    if subscription is None:
        return None, None, None
    if subscription.user_id != audit.user_id:
        raise ActivationAccessForbiddenError("activation access forbidden")
    latest_audit = subscriptions_store.get_latest_audit_for_subscription(
        session=session,
        subscription_id=subscription.id,
    )
    if latest_audit is None:
        return subscription, None, None

    latest_summary = latest_audit.evidence_summary or {}
    external_txn_id = None
    raw_external_txn = latest_summary.get("external_txn_id")
    if isinstance(raw_external_txn, str) and raw_external_txn.strip():
        external_txn_id = raw_external_txn.strip()

    reconcile_status = None
    if (
        audit.source != PaymentSource.ios_app_store.value
        and latest_audit.status == subscription.status
    ):
        reconcile_status = _parse_optional_reconcile_status(latest_summary.get("reconcile_status"))

    return (
        subscription,
        reconcile_status,
        external_txn_id,
    )


def _parse_optional_reconcile_status(raw_value: Any) -> ReconcileStatus | None:
    """Parse optional reconcile status from evidence summary."""

    if not isinstance(raw_value, str):
        return None
    try:
        return ReconcileStatus(raw_value)
    except ValueError:
        return None


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


def _entry_transaction_id(entry: dict[str, Any]) -> str | None:
    """Return transaction_id from Apple receipt entry."""

    raw = _first_present_entry_value(entry, "transaction_id", "transactionId")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _entry_original_transaction_id(entry: dict[str, Any]) -> str | None:
    """Return original_transaction_id from Apple receipt entry."""

    raw = _first_present_entry_value(entry, "original_transaction_id", "originalTransactionId")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


# Canonical Apple product_id → tier map for the B2 verify->activation handoff.
# StoreKit catalog governance is tracked separately in `ledger-p1-ios-storekit-products`.
APPLE_PRODUCT_TIER_MAP: dict[str, SubscriptionTier] = {
    "com.pulseplate.premium.monthly": SubscriptionTier.pro,
    "com.pulseplate.premium.yearly": SubscriptionTier.pro,
    "com.pulseplate.vip.monthly": SubscriptionTier.vip,
}


def _subscription_tier_for_product(product_id: str | None) -> SubscriptionTier | None:
    """Map Apple product identifiers to SubscriptionTier for activation contract.

    Uses explicit allowlist only; unknown or prefix-like SKUs return None (fail-closed).
    """
    if not product_id:
        return None
    normalized = product_id.strip().lower()
    return APPLE_PRODUCT_TIER_MAP.get(normalized)


def _verification_state_to_ios_status(
    state: AppleVerificationState,
) -> IosVerificationStatus:
    """Map AppleVerificationState to IosVerificationStatus for activation contract."""

    if state is AppleVerificationState.active or state is AppleVerificationState.restored:
        return IosVerificationStatus.active
    if state is AppleVerificationState.expired:
        return IosVerificationStatus.expired
    return IosVerificationStatus.rejected


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


def _build_activation_contract_from_entry(
    *,
    entry: dict[str, Any],
    product_id: str,
    expires_at: datetime | None,
    verification_state: AppleVerificationState,
) -> IOSVerifiedActivationResult | None:
    """Build IOSVerifiedActivationResult (activation-contract shape) from Apple receipt entry."""

    transaction_id = _entry_transaction_id(entry)
    if not transaction_id:
        return None
    subscription_tier = _subscription_tier_for_product(product_id)
    if subscription_tier is None:
        return None
    ios_status = _verification_state_to_ios_status(verification_state)
    if ios_status not in {IosVerificationStatus.active, IosVerificationStatus.expired}:
        return None
    if expires_at is None:
        return None
    accepted_ios_status = cast(
        Literal[IosVerificationStatus.active, IosVerificationStatus.expired],
        ios_status,
    )
    try:
        return IOSVerifiedActivationResult(
            transaction_id=transaction_id,
            original_transaction_id=_entry_original_transaction_id(entry),
            product_id=product_id,
            subscription_tier=SubscriptionTierValue(subscription_tier.value),
            status=accepted_ios_status,
            expires_at=expires_at,
            platform=PaymentPlatform.ios,
        )
    except ValidationError:
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
        if not product_id:
            return _build_invalid_verification_response(
                environment=environment,
                product_id=product_id,
                expires_at=expires_at,
                code="APPLE_RECEIPT_INVALID",
                message="Receipt verification failed",
                verification_state=AppleVerificationState.invalid,
            )
        return AppleReceiptVerificationResponse(
            verified=False,
            verification_state=AppleVerificationState.expired,
            environment=environment,
            product_id=product_id,
            expires_at=expires_at,
            error=AppleProviderError(
                code="APPLE_RECEIPT_EXPIRED",
                message="Apple receipt is expired",
            ),
        )

    if not product_id:
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
    activation_payload = _build_activation_contract_from_entry(
        entry=latest_entry,
        product_id=product_id,
        expires_at=expires_at,
        verification_state=verification_state,
    )
    if activation_payload is None:
        return _build_invalid_verification_response(
            environment=environment,
            product_id=product_id,
            expires_at=expires_at,
            code="APPLE_RECEIPT_INVALID",
            message="Receipt verification failed",
            verification_state=AppleVerificationState.invalid,
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
    """Return deterministic issuer marker aligned with canonical subject id."""

    normalized_api_key = api_key.strip()
    if not normalized_api_key:
        raise ValueError("api_key is required for issuer derivation")
    subject_id = derive_subject_id_from_api_key(normalized_api_key)
    return f"{_LEGACY_ISSUER_PREFIX}{subject_id}"


async def verify_apple_receipt(receipt_data: str) -> AppleReceiptVerificationResponse:
    """Verify Apple receipt via transitional server-only verifyReceipt flow."""

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


async def activate_subscription_async(
    *,
    payload: ActivateSubscriptionRequest,
    user_id: int,
) -> SubscriptionActivationResponse:
    """Activate subscription with server-side Apple receipt reverification for iOS.

    For source=ios_app_store, receipt_data is required. The server re-verifies
    the receipt with Apple and uses only the server-verified result for
    persistence. Client-supplied verification_result is never trusted as
    entitlement truth.
    """
    if payload.source is not PaymentSource.ios_app_store:
        return activate_subscription(payload=payload, user_id=user_id)

    ios_payload = payload.get_ios_payload()
    receipt_data = ios_payload.receipt_data
    normalized_receipt_data = receipt_data.strip()
    if not normalized_receipt_data:
        raise ActivationReverifyRejectedError(
            "receipt_data is required for iOS activation; server must verify with Apple"
        )

    verify_response = await verify_apple_receipt(normalized_receipt_data)
    if verify_response.activation_payload is None:
        raise ActivationReverifyRejectedError(
            "Apple receipt verification failed or did not produce activation payload"
        )

    server_verified = verify_response.activation_payload
    server_payload = IOSAppStoreActivationPayload(
        verification_result=server_verified,
        receipt_data=normalized_receipt_data,
    )
    server_request = ActivateSubscriptionRequest(
        source=payload.source,
        payload=server_payload,
    )
    return activate_subscription(payload=server_request, user_id=user_id)


@overload
def activate_subscription(
    *,
    payload: ActivateSubscriptionRequest,
    user_id: int,
    issuer: None = None,
) -> SubscriptionActivationResponse: ...


@overload
def activate_subscription(
    *,
    payload: ActivateSubscriptionRequest,
    user_id: None = None,
    issuer: str,
) -> tuple[SubscriptionActivationResponse, bool]: ...


def activate_subscription(
    *,
    payload: ActivateSubscriptionRequest,
    user_id: int | None = None,
    issuer: str | None = None,
) -> SubscriptionActivationResponse | tuple[SubscriptionActivationResponse, bool]:
    """Persist canonical subscription state and return activation response."""

    resolved_user_id = _resolve_user_id(user_id=user_id, issuer=issuer)
    normalized = _normalize_activation(payload=payload)
    session_factory = get_session_factory()
    session = session_factory()
    now = _utc_now()

    try:
        existing_audit = subscriptions_store.get_audit_by_user_key(
            session=session,
            user_id=resolved_user_id,
            idempotency_key=normalized.idempotency_key,
        )
        if existing_audit is not None:
            if existing_audit.payload_hash != normalized.payload_hash:
                raise IdempotencyConflictError("deterministic activation key conflict")
            existing_response = _to_response(
                activation_id=existing_audit.id,
                audit=existing_audit,
            )
            if _legacy_response_mode(user_id=user_id, issuer=issuer):
                return existing_response, False
            return existing_response

        subscription = subscriptions_store.get_subscription_for_user_source(
            session=session,
            user_id=resolved_user_id,
            source=normalized.source,
        )
        subscription = _apply_subscription_state(
            subscription=subscription,
            user_id=resolved_user_id,
            normalized=normalized,
            now=now,
        )
        session.add(subscription)
        session.flush()

        audit = SubscriptionActivationAudit(
            id=str(uuid4()),
            subscription_id=subscription.id,
            user_id=resolved_user_id,
            source=normalized.source.value,
            idempotency_key=normalized.idempotency_key,
            payload_hash=normalized.payload_hash,
            tier=normalized.tier.value,
            status=normalized.status.value,
            platform=normalized.platform.value,
            provider_receipt_hash=normalized.provider_receipt_hash,
            source_reference=normalized.source_reference,
            product_id=normalized.product_id,
            expires_at=normalized.expires_at,
            activated_at=normalized.activated_at,
            submitted_amount_minor=normalized.submitted_amount_minor,
            submitted_currency=normalized.submitted_currency,
            evidence_summary=_build_audit_evidence(normalized=normalized),
            created_at=now,
        )
        session.add(audit)
        session.commit()
        session.refresh(audit)
        session.refresh(subscription)

        response = _to_response(
            activation_id=audit.id,
            audit=audit,
            subscription=subscription,
        )
        _ACTIVATIONS[audit.id] = {
            "payment_source": normalized.source.value,
            "reconcile_status": normalized.reconcile_status.value,
            "status": normalized.status.value,
        }
        if _legacy_response_mode(user_id=user_id, issuer=issuer):
            return response, True
        return response
    except IntegrityError as exc:
        session.rollback()
        return _replay_existing_activation_or_raise(
            session=session,
            user_id=resolved_user_id,
            normalized=normalized,
            user_id_was_explicit=user_id is not None,
            issuer=issuer,
            error=exc,
        )
    except IdempotencyConflictError:
        session.rollback()
        raise
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def get_activation(
    activation_id: str,
    *,
    user_id: int | None = None,
    issuer: str | None = None,
) -> SubscriptionActivationResponse | None:
    """Fetch activation view by id with user-level access control.

    RU: Readback keyed by activation id returns the current persisted entitlement
    view for that activation lineage, not a frozen audit-only snapshot.
    EN: Activation-id readback returns the current persisted entitlement view for
    the activation lineage rather than a frozen audit-only snapshot.
    """

    resolved_user_id = _resolve_user_id(user_id=user_id, issuer=issuer)
    session_factory = get_session_factory()
    session = session_factory()
    try:
        audit = subscriptions_store.get_audit_by_id(session=session, activation_id=activation_id)
        if audit is None:
            return None
        if audit.user_id != resolved_user_id:
            raise ActivationAccessForbiddenError("activation access forbidden")
        subscription, reconcile_status, external_txn_id = _current_response_overrides(
            session=session,
            audit=audit,
        )
        return _to_response(
            activation_id=activation_id,
            audit=audit,
            subscription=subscription,
            reconcile_status_override=reconcile_status,
            external_txn_id_override=external_txn_id,
        )
    finally:
        session.close()


def get_reconcile_activation_status(
    intent_id: str,
    *,
    user_id: int | None = None,
    issuer: str | None = None,
) -> SubscriptionActivationResponse | None:
    """Return current manual-reconcile status for the original activation intent."""

    resolved_user_id = _resolve_user_id(user_id=user_id, issuer=issuer)
    session_factory = get_session_factory()
    session = session_factory()
    try:
        audit = subscriptions_store.get_audit_by_id(session=session, activation_id=intent_id)
        if audit is None:
            return None
        if audit.user_id != resolved_user_id:
            raise ActivationAccessForbiddenError("activation access forbidden")
        if audit.source == PaymentSource.ios_app_store.value:
            raise ActivationStateError(
                "manual reconciliation status is unavailable for ios_app_store"
            )
        subscription, reconcile_status, external_txn_id = _current_response_overrides(
            session=session,
            audit=audit,
        )
        if subscription is None:
            return None
        return _to_response(
            activation_id=intent_id,
            audit=audit,
            subscription=subscription,
            reconcile_status_override=reconcile_status,
            external_txn_id_override=external_txn_id,
        )
    finally:
        session.close()


def build_manual_intent_request(
    *,
    payload: ManualRailIntentRequest,
) -> ActivateSubscriptionRequest:
    """Convert manual-rail intent request into legacy-compatible activation request."""

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
    payload: ManualRailReconcileRequest,
    user_id: int | None = None,
    issuer: str | None = None,
) -> SubscriptionActivationResponse:
    """Apply deterministic reconciliation to a pending manual payment intent."""

    resolved_user_id = _resolve_user_id(user_id=user_id, issuer=issuer)
    session_factory = get_session_factory()
    session = session_factory()
    now = _utc_now()

    try:
        initial_audit = subscriptions_store.get_audit_by_id(
            session=session,
            activation_id=payload.intent_id,
        )
        if initial_audit is None:
            raise ActivationNotFoundError("activation not found")
        if initial_audit.user_id != resolved_user_id:
            raise ActivationAccessForbiddenError("activation access forbidden")
        idempotency_key = f"reconcile:{payload.intent_id}:{payload.client_event_id}"
        payload_hash = _hash_payload(payload.model_dump(mode="json"))
        replay_audit = subscriptions_store.get_audit_by_user_key(
            session=session,
            user_id=resolved_user_id,
            idempotency_key=idempotency_key,
        )
        if initial_audit.source == PaymentSource.ios_app_store.value:
            raise ActivationStateError("ios_app_store activation cannot be reconciled manually")

        subscription = subscriptions_store.get_subscription_by_id(
            session=session,
            subscription_id=initial_audit.subscription_id,
        )
        if subscription is None:
            raise ActivationNotFoundError("activation not found")
        if replay_audit is not None:
            if replay_audit.payload_hash != payload_hash:
                raise IdempotencyConflictError(
                    "client_event_id conflict: reconcile payload mismatch"
                )
            return _to_response(
                activation_id=payload.intent_id,
                audit=initial_audit,
                subscription=subscription,
                status_override=SubscriptionStatus(subscription.status),
                reconcile_status_override=_parse_optional_reconcile_status(
                    (replay_audit.evidence_summary or {}).get("reconcile_status")
                ),
                external_txn_id_override=payload.external_txn_id,
            )
        if subscription.status not in {
            SubscriptionStatus.pending_manual_review.value,
            SubscriptionStatus.pending_verification.value,
        }:
            raise ActivationStateError("manual reconcile transition requires pending state")

        reconcile_status = (
            ReconcileStatus.verified
            if payload.decision is ReconcileDecision.verified
            else ReconcileStatus.rejected
        )
        subscription.status = (
            SubscriptionStatus.active.value
            if payload.decision is ReconcileDecision.verified
            else SubscriptionStatus.rejected.value
        )
        subscription.activated_at = now if payload.decision is ReconcileDecision.verified else None
        requested_plan = _parse_optional_plan(
            (initial_audit.evidence_summary or {}).get("requested_plan")
        )
        if payload.decision is ReconcileDecision.verified:
            if requested_plan is None:
                raise ActivationStateError("manual reconcile requires requested plan")
            subscription.expires_at = _manual_plan_expires_at(
                plan=requested_plan,
                activated_at=now,
            )
        else:
            subscription.expires_at = None
        subscription.updated_at = now

        initial_summary = initial_audit.evidence_summary or {}
        audit_summary = {
            **initial_summary,
            "reconcile_status": reconcile_status.value,
            "external_txn_id": payload.external_txn_id,
            "verified_at": now.isoformat(),
        }
        reconcile_audit = SubscriptionActivationAudit(
            id=str(uuid4()),
            subscription_id=subscription.id,
            user_id=resolved_user_id,
            source=subscription.source,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            tier=subscription.tier,
            status=subscription.status,
            platform=subscription.platform,
            provider_receipt_hash=subscription.provider_receipt_hash,
            source_reference=subscription.source_reference,
            product_id=subscription.product_id,
            expires_at=subscription.expires_at,
            activated_at=subscription.activated_at,
            submitted_amount_minor=subscription.submitted_amount_minor,
            submitted_currency=subscription.submitted_currency,
            evidence_summary=audit_summary,
            created_at=now,
        )
        session.add(reconcile_audit)
        session.commit()
        session.refresh(reconcile_audit)
        session.refresh(subscription)
        _ACTIVATIONS[payload.intent_id] = {
            "payment_source": initial_audit.source,
            "reconcile_status": reconcile_status.value,
            "status": subscription.status,
        }

        return _to_response(
            activation_id=payload.intent_id,
            audit=initial_audit,
            subscription=subscription,
            status_override=SubscriptionStatus(subscription.status),
            reconcile_status_override=reconcile_status,
            external_txn_id_override=payload.external_txn_id,
        )
    except (ActivationNotFoundError, ActivationAccessForbiddenError, ActivationStateError):
        session.rollback()
        raise
    except IdempotencyConflictError:
        session.rollback()
        raise
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def reset_state() -> None:
    """Reset DB-backed activation state for deterministic tests."""

    session_factory = get_session_factory()
    session = session_factory()
    try:
        session.execute(delete(SubscriptionActivationAudit))
        session.execute(delete(Subscription))
        session.commit()
        _ACTIVATIONS.clear()
    except SQLAlchemyError:
        session.rollback()
    finally:
        session.close()
