"""
Legacy BMI Pro Endpoint Alias (Deprecated)

RU: Устаревший алиас для BMI Pro endpoint (обратная совместимость).
EN: Deprecated alias for BMI Pro endpoint (backward compatibility).

⚠️ DEPRECATED: This router provides backward compatibility for `/api/v1/bmi/pro`.
Use the canonical endpoint `/api/v1/pro/bmi` instead.

This shim follows the same pattern as `premium_week.py`:
- Thin proxy to canonical handler
- Guarded with `require_pro_tier`
- Marked as deprecated in OpenAPI
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.middleware.api_tiers import require_pro_tier
from app.routers.bmi_pro import BMIProRequest, BMIProResponse, bmi_pro

router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])


@router.post(
    "/pro",
    response_model=BMIProResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/bmi",
        "x-migration-path": "Migrate to POST /api/v1/pro/bmi (same contract)",
    },
)
def bmi_pro_legacy_alias(
    req: BMIProRequest,
    _: str = Depends(require_pro_tier),
) -> BMIProResponse:
    """Legacy BMI Pro endpoint (deprecated).

    This endpoint is maintained for backward compatibility only.
    New clients should use the canonical endpoint: POST /api/v1/pro/bmi

    Args:
        req: BMI Pro request payload
        _: Pro tier guard (required)

    Returns:
        BMI Pro response with analysis results
    """
    return bmi_pro(req, _)
