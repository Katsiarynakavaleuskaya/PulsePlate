"""Paywall analytics schemas.

RU: Hidden internal schemas для paywall exposure ledger ingestion.
EN: Hidden internal schemas for paywall exposure ledger ingestion.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

_SLUG_PATTERN = r"^[a-z0-9]+(?:_[a-z0-9]+)*$"

SlugString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=64,
        pattern=_SLUG_PATTERN,
    ),
]

IdentifierString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=128,
    ),
]


class PaywallExposureEventName(str, Enum):
    """Canonical paywall ledger event names."""

    shown = "shown"
    dismissed = "dismissed"
    cta_clicked = "cta_clicked"
    upgrade_started = "upgrade_started"
    upgrade_completed = "upgrade_completed"


class PaywallExposureEventRequest(BaseModel):
    """Client-reported paywall exposure payload."""

    model_config = ConfigDict(extra="forbid")

    client_event_id: IdentifierString
    exposure_id: IdentifierString
    event_name: PaywallExposureEventName
    source_surface: SlugString
    trigger_reason: SlugString
    via: SlugString | None = None
    metadata: dict[str, Any] | None = Field(default=None)


class PaywallExposureAckResponse(BaseModel):
    """Deterministic hidden-route acknowledgement."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok")
