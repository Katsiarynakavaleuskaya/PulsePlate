"""Session endpoint schemas.

RU: Схемы для web session endpoints.
EN: Schemas for web session endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SessionTier = Literal["PRO", "VIP"]
SessionSource = Literal["header", "cookie"]


class SessionExchangeRequest(BaseModel):
    """Exchange request schema (empty body, explicit contract)."""

    model_config = ConfigDict(extra="forbid")


class SessionExchangeResponse(BaseModel):
    """Exchange/refresh response contract."""

    status: Literal["ok"] = "ok"
    tier: SessionTier = Field(..., description="Resolved tier stored in session cookie")
    auth_source: SessionSource = Field(
        ...,
        description="Authentication source used for this request",
    )
    expires_at_epoch: int = Field(..., ge=1, description="Session expiry Unix epoch (UTC)")
    ttl_seconds: int = Field(..., ge=1, description="Session TTL in seconds")


class SessionStatusResponse(BaseModel):
    """Session status response contract."""

    status: Literal["ok"] = "ok"
    authenticated: Literal[True] = True
    tier: SessionTier = Field(..., description="Current authenticated tier")
    auth_source: SessionSource = Field(..., description="Current authentication source")
    expires_at_epoch: int | None = Field(
        default=None,
        description="Cookie expiry Unix epoch (UTC), null when header auth is used",
    )


class SessionLogoutResponse(BaseModel):
    """Logout response contract."""

    status: Literal["ok"] = "ok"
    logged_out: Literal[True] = True
