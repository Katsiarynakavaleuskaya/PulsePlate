# -*- coding: utf-8 -*-
"""Payment activation schemas for PRO payment baseline.

RU: Схемы активации платежей для базового PRO-контракта.
EN: Payment activation schemas for baseline PRO contract.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentSource(str, Enum):
    """Canonical payment sources (RU/BY + iOS baseline)."""

    ios_app_store = "ios_app_store"
    erip_qr = "erip_qr"
    swift_manual = "swift_manual"


class ManualPaymentSource(str, Enum):
    """Manual payment sources allowed in RU/BY intent flow."""

    erip_qr = "erip_qr"
    swift_manual = "swift_manual"


class RuByCurrency(str, Enum):
    """Currencies allowed in RU/BY manual payment flows."""

    byn = "BYN"
    rub = "RUB"


class SubscriptionPlan(str, Enum):
    """Canonical subscription plans for billing activation."""

    pro_monthly = "pro_monthly"
    vip_monthly = "vip_monthly"


class SubscriptionTierValue(str, Enum):
    """Lowercase tier value used by billing contracts."""

    free = "free"
    pro = "pro"
    vip = "vip"


class ActivationStatus(str, Enum):
    """Canonical activation state for subscription activation flow."""

    pending_verification = "pending_verification"
    active = "active"
    rejected = "rejected"


class ReconcileStatus(str, Enum):
    """Reconciliation status for financial audit trail."""

    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    not_required = "not_required"


class PaymentRequestModel(BaseModel):
    """Base request DTO that fails closed on unknown keys."""

    model_config = ConfigDict(extra="forbid")


class ActivateSubscriptionRequest(PaymentRequestModel):
    """Activation request payload (contract-first, deterministic)."""

    source: PaymentSource
    plan: SubscriptionPlan = Field(
        ...,
        description="Canonical required plan code for activation intent",
    )
    client_event_id: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Client-generated idempotency event ID",
    )
    external_txn_id: str | None = Field(
        default=None,
        min_length=3,
        max_length=128,
        description="Provider-side transaction or intent ID",
    )
    verification_ok: bool | None = Field(
        default=None,
        description="Deterministic verification result for baseline R1 contract",
    )
    verification_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Opaque verification payload. Server remains source of truth.",
    )

    @field_validator("client_event_id", mode="before")
    @classmethod
    def _normalize_client_event_id(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("client_event_id must not be empty")
        return normalized

    @field_validator("external_txn_id", mode="before")
    @classmethod
    def _normalize_external_txn_id(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class SubscriptionActivationResponse(BaseModel):
    """Canonical activation response for all payment sources."""

    activation_id: str
    intent_id: str
    audit_id: str
    payment_source: PaymentSource
    plan: SubscriptionPlan
    subscription_tier: SubscriptionTierValue
    status: ActivationStatus
    reconcile_status: ReconcileStatus
    external_txn_id: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AppleReceiptVerificationRequest(PaymentRequestModel):
    """Request contract for iOS receipt verification."""

    plan: SubscriptionPlan
    client_event_id: str = Field(..., min_length=6, max_length=128)
    receipt: str = Field(..., min_length=8, description="Opaque App Store receipt blob")
    external_txn_id: str | None = Field(default=None, min_length=3, max_length=128)

    @field_validator("client_event_id", "receipt", mode="before")
    @classmethod
    def _normalize_non_empty_str(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("external_txn_id", mode="before")
    @classmethod
    def _normalize_optional_txn_id(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


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
        if value is None:
            return None
        if not isinstance(value, str):
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
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class PaymentErrorResponse(BaseModel):
    """Deterministic error envelope for payment activation endpoints."""

    status: str = "error"
    code: str
    message: str
    detail: str
