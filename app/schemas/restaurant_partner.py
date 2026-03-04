# -*- coding: utf-8 -*-
"""Contract-first schemas for restaurant partner order flows.

RU: Схемы контрактов для интеграции меню с ресторанами/шефами.
EN: Contract schemas for menu-to-partner restaurant/chef integration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class FulfillmentMode(str, Enum):
    pickup = "pickup"
    delivery = "delivery"


class PartnerOrderStatus(str, Enum):
    draft = "draft"
    pending_partner = "pending_partner"
    confirmed = "confirmed"
    rejected = "rejected"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class PartnerHandoffShareStatus(str, Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class PartnerOrderItemIn(BaseModel):
    menu_item_id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=256)
    qty: int = Field(..., ge=1, le=100)
    unit_price_minor: int = Field(..., ge=0)
    note: str | None = Field(default=None, max_length=256)


class PartnerOrderItemPreview(BaseModel):
    menu_item_id: str
    title: str
    qty: int
    unit_price_minor: int
    line_total_minor: int
    note: str | None = None


class PartnerOrderTotals(BaseModel):
    subtotal_minor: int = Field(..., ge=0)
    service_fee_minor: int = Field(..., ge=0)
    delivery_fee_minor: int = Field(..., ge=0)
    total_minor: int = Field(..., ge=0)


class PartnerConsent(BaseModel):
    consent_share_with_partner: bool = Field(
        ...,
        description="Explicit user consent to share menu package with selected partner.",
    )
    consent_version: str = Field(..., min_length=1, max_length=32)
    accepted_at_utc: datetime | None = None

    @field_validator("consent_share_with_partner")
    @classmethod
    def _validate_partner_share_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("consent_share_with_partner must be true for partner order flows")
        return value


class PartnerOrderDraft(BaseModel):
    restaurant_id: str = Field(..., min_length=1, max_length=64)
    currency: str = Field(..., min_length=3, max_length=3)
    fulfillment: FulfillmentMode
    items: list[PartnerOrderItemIn] = Field(..., min_length=1, max_length=100)
    service_fee_minor: int = Field(default=0, ge=0)
    delivery_fee_minor: int = Field(default=0, ge=0)
    customer_note: str | None = Field(default=None, max_length=500)
    scheduled_for: datetime | None = None
    dietary_tags: list[str] = Field(default_factory=list, max_length=50)
    allergens: list[str] = Field(default_factory=list, max_length=50)
    consent: PartnerConsent
    attribution_source: str | None = Field(default=None, max_length=128)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        upper = value.upper()
        if len(upper) != 3 or not upper.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return upper

    @field_validator("scheduled_for")
    @classmethod
    def _validate_schedule_not_past(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("scheduled_for must include timezone offset")
        value_utc = value.astimezone(timezone.utc)
        if value_utc < _utc_now():
            raise ValueError("scheduled_for must not be in the past")
        return value_utc


class PartnerOrderPreviewRequest(BaseModel):
    draft: PartnerOrderDraft


class PartnerOrderWeeklyAdapterRequest(BaseModel):
    """Request schema for weekly-plan -> partner order adapter preview."""

    week_plan: dict[str, Any]
    restaurant_id: str = Field(..., min_length=1, max_length=64)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    fulfillment: FulfillmentMode = FulfillmentMode.pickup
    service_fee_minor: int = Field(default=0, ge=0)
    delivery_fee_minor: int = Field(default=0, ge=0)
    customer_note: str | None = Field(default=None, max_length=500)
    dietary_tags: list[str] = Field(default_factory=list, max_length=50)
    allergens: list[str] = Field(default_factory=list, max_length=50)
    consent: PartnerConsent
    attribution_source: str | None = Field(default=None, max_length=128)
    unit_price_minor_default: int = Field(default=0, ge=0)

    @field_validator("currency")
    @classmethod
    def _validate_adapter_currency(cls, value: str) -> str:
        upper = value.upper()
        if len(upper) != 3 or not upper.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return upper


class PartnerOrderPreviewResponse(BaseModel):
    restaurant_id: str
    currency: str
    fulfillment: FulfillmentMode
    items: list[PartnerOrderItemPreview]
    totals: PartnerOrderTotals
    warnings: list[str] = Field(default_factory=list)


class PartnerOrderCreateRequest(BaseModel):
    draft: PartnerOrderDraft
    client_event_id: str | None = Field(default=None, min_length=1, max_length=64)


class PartnerOrderResponse(BaseModel):
    id: str
    status: PartnerOrderStatus
    restaurant_id: str
    currency: str
    fulfillment: FulfillmentMode
    items: list[PartnerOrderItemPreview]
    totals: PartnerOrderTotals
    customer_note: str | None
    dietary_tags: list[str]
    allergens: list[str]
    consent: PartnerConsent
    attribution_source: str | None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None
    version: int = Field(default=1, ge=1)


class PartnerOrderErrorResponse(BaseModel):
    detail: str


class PartnerOrderConfirmRequest(BaseModel):
    confirmed_by: str = Field(..., min_length=1, max_length=128)
    client_event_id: str | None = Field(default=None, min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)
    action: Literal["confirm"] = "confirm"


class PartnerHandoffShareIssueRequest(BaseModel):
    partner_id: str = Field(..., min_length=1, max_length=128)
    expires_in_minutes: int = Field(..., ge=1, le=60 * 24 * 30)


class PartnerHandoffShareResponse(BaseModel):
    share_id: str
    order_id: str
    issuer: str
    partner_id: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    status: PartnerHandoffShareStatus
