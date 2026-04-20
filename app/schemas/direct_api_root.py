"""Pydantic contract for direct FastAPI ``GET /`` probe (bypassing Caddy)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DirectApiRootLinks(BaseModel):
    """Stable relative links for operators hitting uvicorn directly."""

    model_config = ConfigDict(extra="forbid")

    health: str = Field(default="/health", description="Liveness JSON probe")
    docs: str = Field(default="/docs", description="Swagger UI")
    openapi: str = Field(default="/openapi.json", description="OpenAPI document")
    legacy_bmi_web_ui: str = Field(
        default="/legacy/bmi-calculator",
        description="Embedded legacy HTML BMI form (moved from /)",
    )


class DirectApiRootProbe(BaseModel):
    """JSON body for ``GET /`` when traffic reaches FastAPI without SPA static host."""

    model_config = ConfigDict(extra="forbid")

    service: str = Field(default="pulseplate-api")
    surface: str = Field(default="api")
    message: str = Field(
        ...,
        description="Explains apex SPA vs direct API access for operators.",
    )
    links: DirectApiRootLinks
