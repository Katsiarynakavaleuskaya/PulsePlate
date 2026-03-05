# -*- coding: utf-8 -*-
"""Payment activation schemas for PRO payment baseline.

RU: Схемы активации платежей для базового PRO-контракта.
EN: Payment activation schemas for baseline PRO contract.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PaymentSource(str, Enum):
    """Canonical payment sources (RU/BY + iOS baseline)."""

    ios_app_store = "ios_app_store"
    erip_qr = "erip_qr"
    swift_manual = "swift_manual"


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


class ActivateSubscriptionRequest(BaseModel):
    """Activation request payload (contract-first, deterministic)."""

    source: PaymentSource
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

    @field_validator("client_event_id")
    @classmethod
    def _normalize_client_event_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("client_event_id must not be empty")
        return normalized

    @field_validator("external_txn_id")
    @classmethod
    def _normalize_external_txn_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SubscriptionActivationResponse(BaseModel):
    """Canonical activation response for all payment sources."""

    activation_id: str
    payment_source: PaymentSource
    status: ActivationStatus
    reconcile_status: ReconcileStatus
    external_txn_id: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PaymentErrorResponse(BaseModel):
    """Deterministic error envelope for payment activation endpoints."""

    status: str = "error"
    code: str
    message: str
    detail: str
