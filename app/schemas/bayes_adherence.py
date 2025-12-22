"""Pydantic schemas for adherence endpoints.

RU: Схемы для эндпоинтов adherence (соблюдение/срыв).
EN: Schemas for adherence endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AdherenceEventType = Literal["meal_logged", "slip"]


class AdherenceEventRequest(BaseModel):
    """Request schema for recording an adherence event.

    RU: Схема запроса для записи события adherence.
    EN: Request schema for recording an adherence event.

    Security Note:
        subject_id is derived from authenticated API key (not from request payload)
        to prevent horizontal privilege escalation.
    """

    model_config = ConfigDict(extra="forbid")

    # TODO(SEC-001): Mitigation plan - add per-API-key rate limiting, stricter input
    # validation/whitelisting, and logging/alerting for suspicious cross-user requests.

    event_type: AdherenceEventType
    weight: float = Field(1.0, gt=0.0, le=10.0)
    analyzer_key: str = Field("v1:adherence", min_length=3, max_length=64)


class AdherenceResponse(BaseModel):
    """Response schema for adherence endpoints.

    RU: Схема ответа для эндпоинтов adherence.
    EN: Response schema for adherence endpoints.
    """

    user_id: int
    analyzer_key: str
    alpha: float
    beta: float
    n: int
    risk_slip: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_more_data: bool
