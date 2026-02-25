"""
Restaurant and moderated submission schemas.

RU: Схемы ресторанов/меню и модерируемых пользовательских добавлений.
EN: Schemas for restaurants/menus and moderated user submissions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class SubmissionStatus(str, Enum):
    """Moderation states for controlled submissions."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubmissionReviewStatus(str, Enum):
    """Allowed status values for moderation PATCH endpoint."""

    APPROVED = "approved"
    REJECTED = "rejected"


class RestaurantHit(BaseModel):
    """Restaurant chain search hit."""

    id: str
    name: str
    country: str | None = None
    source: str


class RestaurantMenuItem(BaseModel):
    """Restaurant menu item payload."""

    id: str
    chain_id: str
    item_name: str
    category: str | None = None
    serving_size_g: float | None = None
    kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    sodium_mg: float | None = None
    source: str
    source_id: str | None = None
    is_active: bool = True


class RestaurantSubmissionCreate(BaseModel):
    """Create request for controlled submission queue."""

    canonical_name: str = Field(..., min_length=1, max_length=256)
    barcode: str | None = Field(default=None, max_length=64)
    off_url: str | None = Field(default=None, max_length=1024)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("off_url")
    @classmethod
    def validate_off_url(cls, value: str | None) -> str | None:
        """Allow only valid HTTP(S) URLs for OFF references."""
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("off_url must be a valid http/https URL")
        return value


class SubmissionAuditEntry(BaseModel):
    """Single status transition for a submission."""

    id: str
    from_status: SubmissionStatus | None = None
    to_status: SubmissionStatus
    reviewer_notes: str | None = None
    changed_at: datetime


class RestaurantSubmission(BaseModel):
    """Submission record returned by API."""

    id: str
    entity_type: str
    canonical_name: str
    barcode: str | None = None
    off_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: SubmissionStatus
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    audit: list[SubmissionAuditEntry] = Field(default_factory=list)


class SubmissionReviewRequest(BaseModel):
    """Request payload for moderation status update."""

    status: SubmissionReviewStatus
    reviewer_notes: str | None = Field(default=None, max_length=1024)
