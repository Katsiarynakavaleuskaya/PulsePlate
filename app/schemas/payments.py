# -*- coding: utf-8 -*-
"""Payment activation schemas for billing verify + activation runtime.

RU: Схемы для verify/activation runtime с backward-compatible billing surface.
EN: Schemas for verify/activation runtime with backward-compatible billing surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class PaymentSource(str, Enum):
    """Canonical payment sources for the current billing baseline."""

    ios_app_store = "ios_app_store"
    erip_qr = "erip_qr"
    swift_manual = "swift_manual"


class ManualPaymentSource(str, Enum):
    """Manual payment sources allowed on RU/BY billing surfaces."""

    erip_qr = "erip_qr"
    swift_manual = "swift_manual"


class RuByCurrency(str, Enum):
    """Currencies allowed in RU/BY manual payment flows."""

    byn = "BYN"
    rub = "RUB"


class SubscriptionPlan(str, Enum):
    """Legacy plan contract kept for billing compatibility routes."""

    pro_monthly = "pro_monthly"
    vip_monthly = "vip_monthly"


class SubscriptionTierValue(str, Enum):
    """Paid subscription tiers used by legacy billing responses."""

    pro = "pro"
    vip = "vip"


class SubscriptionTier(str, Enum):
    """Canonical persisted subscription tiers."""

    free = "free"
    pro = "pro"
    vip = "vip"


class SubscriptionStatus(str, Enum):
    """Persisted subscription lifecycle values."""

    pending_manual_review = "pending_manual_review"
    pending_verification = "pending_verification"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    rejected = "rejected"


class ReconcileStatus(str, Enum):
    """Reconciliation state used by legacy manual-rail routes."""

    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    not_required = "not_required"


class PaymentPlatform(str, Enum):
    """Platform surface for the payment state."""

    ios = "ios"
    web = "web"


class IosVerificationStatus(str, Enum):
    """Normalized iOS verification outcomes from PR-1."""

    active = "active"
    expired = "expired"
    rejected = "rejected"


class AppleVerificationEnvironment(str, Enum):
    """Verification environment resolved by Apple receipt validation."""

    production = "production"
    sandbox = "sandbox"


class AppleVerificationState(str, Enum):
    """Normalized business outcome of Apple receipt verification."""

    active = "active"
    expired = "expired"
    restored = "restored"
    invalid = "invalid"


class PaymentRequestModel(BaseModel):
    """Base request DTO that fails closed on unknown keys."""

    model_config = ConfigDict(extra="forbid")


class IOSVerifiedActivationResult(PaymentRequestModel):
    """Normalized iOS verification result produced by PR-1 Apple verify."""

    transaction_id: str = Field(..., min_length=3, max_length=255)
    original_transaction_id: str | None = Field(default=None, min_length=3, max_length=255)
    product_id: str = Field(..., min_length=3, max_length=255)
    subscription_tier: SubscriptionTier
    status: IosVerificationStatus
    expires_at: datetime | None = None
    platform: PaymentPlatform = Field(
        ...,
        json_schema_extra={"default": PaymentPlatform.ios.value},
    )

    @field_validator("transaction_id", "product_id", "original_transaction_id", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("expires_at")
    @classmethod
    def _normalize_expires_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_result(self) -> "IOSVerifiedActivationResult":
        if self.platform is not PaymentPlatform.ios:
            raise ValueError("ios verification result must use ios platform")
        if self.status in {IosVerificationStatus.active, IosVerificationStatus.expired}:
            if self.expires_at is None:
                raise ValueError("expires_at is required for active or expired iOS results")
        return self


class IOSAppStoreActivationPayload(PaymentRequestModel):
    """Canonical iOS activation payload for PR-2 activation route."""

    verification_result: IOSVerifiedActivationResult
    receipt_data: str = Field(..., min_length=1, max_length=512_000)

    @field_validator("receipt_data", mode="before")
    @classmethod
    def _normalize_receipt_data(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("receipt_data must not be empty")
        return normalized


class ManualActivationPayload(PaymentRequestModel):
    """Canonical manual-rail payload for PR-2 activation route."""

    source_reference: str = Field(..., min_length=3, max_length=255)
    submitted_amount: str | None = Field(default=None, min_length=1, max_length=32)
    submitted_currency: str | None = Field(default=None, min_length=3, max_length=8)

    @field_validator("source_reference", "submitted_amount", mode="before")
    @classmethod
    def _normalize_manual_text(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("submitted_currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        return normalized or None


class ActivateSubscriptionRequest(PaymentRequestModel):
    """Activation request envelope supporting canonical and legacy contracts."""

    source: PaymentSource
    payload: IOSAppStoreActivationPayload | ManualActivationPayload | None = None
    plan: SubscriptionPlan | None = None
    client_event_id: str | None = Field(default=None, min_length=6, max_length=128)
    external_txn_id: str | None = Field(default=None, min_length=3, max_length=128)
    verification_ok: bool | None = Field(default=None)
    verification_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("client_event_id", mode="before")
    @classmethod
    def _normalize_client_event_id(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("client_event_id must not be empty")
        return normalized

    @field_validator("external_txn_id", mode="before")
    @classmethod
    def _normalize_external_txn_id(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _validate_payload_shape(self) -> "ActivateSubscriptionRequest":
        if self.payload is not None:
            normalized_payload: IOSAppStoreActivationPayload | ManualActivationPayload
            if self.source is PaymentSource.ios_app_store:
                normalized_payload = IOSAppStoreActivationPayload.model_validate(self.payload)
            else:
                normalized_payload = ManualActivationPayload.model_validate(self.payload)
            self.payload = normalized_payload
            return self

        if self.plan is None:
            raise ValueError("plan is required when payload is omitted")
        if self.client_event_id is None:
            raise ValueError("client_event_id is required when payload is omitted")
        return self

    def get_ios_payload(self) -> IOSAppStoreActivationPayload:
        """Return typed iOS activation payload."""

        if self.payload is None:
            raise ValueError("ios activation payload is unavailable for legacy requests")
        if isinstance(self.payload, IOSAppStoreActivationPayload):
            return self.payload
        payload_obj: IOSAppStoreActivationPayload = IOSAppStoreActivationPayload.model_validate(
            self.payload
        )
        return payload_obj

    def get_manual_payload(self) -> ManualActivationPayload:
        """Return typed manual activation payload."""

        if self.payload is None:
            raise ValueError("manual activation payload is unavailable for legacy requests")
        if isinstance(self.payload, ManualActivationPayload):
            return self.payload
        payload_obj: ManualActivationPayload = ManualActivationPayload.model_validate(self.payload)
        return payload_obj

    @property
    def uses_canonical_payload(self) -> bool:
        """Return True when request uses the PR-2 canonical payload contract."""

        return self.payload is not None


class AppleReceiptVerificationRequest(PaymentRequestModel):
    """Request contract for iOS receipt verification."""

    receipt_data: str = Field(
        ...,
        min_length=8,
        max_length=512_000,
        description=(
            "Opaque App Store receipt blob. "
            "Canonical field: receipt_data. Compatibility alias accepted: receipt."
        ),
        validation_alias=AliasChoices("receipt_data", "receipt"),
        json_schema_extra={"x-accepted-aliases": ["receipt"]},
    )

    @field_validator("receipt_data", mode="before")
    @classmethod
    def _normalize_non_empty_str(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class AppleProviderError(BaseModel):
    """Canonical provider error details for Apple receipt verification."""

    code: str
    message: str


class AppleReceiptVerificationResponse(BaseModel):
    """Normalized Apple receipt verification result without activation side effects.

    When verified=True, activation_payload carries the full IOSVerifiedActivationResult
    (activation-contract shape) for downstream POST /api/v1/pro/payments/activate.
    When verified=False, activation_payload is always None (fail-closed).
    """

    provider: str = "apple"
    verified: bool
    verification_state: AppleVerificationState
    environment: AppleVerificationEnvironment | None = None
    product_id: str | None = None
    expires_at: datetime | None = None
    activation_payload: IOSVerifiedActivationResult | None = Field(
        default=None,
        description=(
            "Activation-contract shaped payload when verified. "
            "Must be null whenever verified=false. "
            "Client passes this as payload.verification_result and receipt_data as payload.receipt_data "
            "inside ActivateSubscriptionRequest to POST /api/v1/pro/payments/activate."
        ),
    )
    error: AppleProviderError | None = None


class ManualRailIntentRequest(PaymentRequestModel):
    """Request contract for RU/BY manual payment intent creation."""

    source: ManualPaymentSource
    plan: SubscriptionPlan
    client_event_id: str = Field(..., min_length=6, max_length=128)
    external_txn_id: str | None = Field(default=None, min_length=3, max_length=128)
    amount_minor: int = Field(..., ge=1, description="Minor currency units")
    currency: RuByCurrency
    verification_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("client_event_id", "currency", mode="before")
    @classmethod
    def _normalize_required_str(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized.upper() if len(normalized) == 3 else normalized

    @field_validator("external_txn_id", mode="before")
    @classmethod
    def _normalize_manual_external_txn_id(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class ReconcileDecision(str, Enum):
    """Manual reconciliation decisions."""

    verified = "verified"
    rejected = "rejected"


class ManualRailReconcileRequest(PaymentRequestModel):
    """Request contract for RU/BY reconciliation transition."""

    intent_id: str = Field(..., min_length=3, max_length=128)
    client_event_id: str = Field(..., min_length=6, max_length=128)
    decision: ReconcileDecision
    external_txn_id: str | None = Field(default=None, min_length=3, max_length=128)
    verification_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("intent_id", "client_event_id", mode="before")
    @classmethod
    def _normalize_identifier(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("external_txn_id", mode="before")
    @classmethod
    def _normalize_reconcile_txn_id(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class SubscriptionActivationResponse(BaseModel):
    """Canonical response with compatibility fields for legacy billing routes."""

    activation_id: str
    user_id: int | None = None
    source: PaymentSource | None = None
    tier: SubscriptionTier | None = None
    status: SubscriptionStatus
    platform: PaymentPlatform | None = None
    product_id: str | None = None
    source_reference: str | None = None
    expires_at: datetime | None = None
    activated_at: datetime | None = None
    intent_id: str | None = None
    audit_id: str | None = None
    payment_source: PaymentSource | None = None
    plan: SubscriptionPlan | None = None
    subscription_tier: SubscriptionTierValue | None = Field(
        default=None,
        description=(
            "Requested paid tier implied by the billing intent or verified product mapping. "
            "This is the paid target tier, not a free-access fallback."
        ),
    )
    reconcile_status: ReconcileStatus | None = None
    external_txn_id: str | None = None
    verified_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def _fill_compatibility_fields(self) -> "SubscriptionActivationResponse":
        if self.intent_id is None:
            self.intent_id = self.activation_id
        if self.audit_id is None:
            self.audit_id = self.activation_id
        if self.source is None and self.payment_source is not None:
            self.source = self.payment_source
        if self.payment_source is None and self.source is not None:
            self.payment_source = self.source
        if self.tier is None and self.subscription_tier is not None:
            self.tier = SubscriptionTier(self.subscription_tier.value)
        if self.subscription_tier is None and self.tier in {
            SubscriptionTier.pro,
            SubscriptionTier.vip,
        }:
            self.subscription_tier = SubscriptionTierValue(self.tier.value)
        return self


class PaymentErrorResponse(BaseModel):
    """Deterministic error envelope for payment activation endpoints."""

    status: str = "error"
    code: str
    message: str
    detail: str
