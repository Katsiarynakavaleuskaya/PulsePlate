"""Pydantic schemas for adherence endpoints.

RU: Схемы для эндпоинтов adherence (соблюдение/срыв).
EN: Schemas for adherence endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AdherenceEventType = Literal["meal_logged", "slip"]


class AdherenceEventRequest(BaseModel):
    """Request schema for recording an adherence event.

    RU: Схема запроса для записи события adherence.
    EN: Request schema for recording an adherence event.

    Security Note:
        TODO: Remove user_id from request body once proper user authentication
        is implemented. Currently accepts user_id in payload which allows
        horizontal privilege escalation. Should use Depends(get_current_user)
        to extract user_id from auth context.
    """

    user_id: int = Field(..., ge=1)
    event_type: AdherenceEventType
    weight: float = Field(1.0, gt=0.0, le=10.0)  # Changed from ge=0.0 to gt=0.0
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
