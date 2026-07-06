"""Legacy premium weekly-plan route ownership.

This endpoint remains a hidden compatibility alias for the canonical VIP weekly
menu execution path. Keep the handler thin and behavior-compatible with the
legacy route while route registration ownership moves out of ``legacy_app.py``.
"""

from __future__ import annotations

import os

import legacy_app as _legacy_module
from fastapi import APIRouter, Depends, HTTPException
from legacy_app import LegacyWeekPlanRequest, WeeklyMenuResponse, _get_api_key_dynamic

LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/premium/plan/week", "POST", False),
)

router = APIRouter()


@router.post(
    "/api/v1/premium/plan/week",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WeeklyMenuResponse,
    include_in_schema=False,
    deprecated=True,
)
async def api_weekly_menu(
    req: LegacyWeekPlanRequest,
) -> WeeklyMenuResponse:
    """
    RU: Генерирует недельный план питания (через core.menu_engine.make_weekly_menu).
    EN: Generate a weekly meal plan using core.menu_engine.make_weekly_menu.

    Returns keys: week_summary, daily_menus, weekly_coverage, shopping_list.
    """
    try:
        # Guard VIP feature flag at runtime to support tests that toggle env without full reload.
        # If env var is set explicitly and falsy -> disable; otherwise fall back to module flag.
        _vip_env = os.getenv("VIP_MODULE_ENABLED")
        if _vip_env is not None and _vip_env.strip().lower() not in {"1", "true", "on", "yes"}:
            raise HTTPException(status_code=503, detail="VIP module is disabled")
        if _vip_env is None and not bool(getattr(_legacy_module, "VIP_MODULE_ENABLED", False)):
            raise HTTPException(status_code=503, detail="VIP module is disabled")

        menu_builder = _legacy_module._resolve_legacy_weekly_menu_builder()
        if menu_builder is None:
            raise HTTPException(
                status_code=503, detail="Weekly menu generation feature not available"
            )

        from app.routers.vip import execute_legacy_premium_week_alias_payload

        menu_payload = await execute_legacy_premium_week_alias_payload(
            req.model_dump(exclude_none=True),
            menu_builder=menu_builder,
        )
        return _legacy_module._build_legacy_weekly_menu_response(menu_payload)

    except HTTPException:
        # Pass through expected HTTP errors
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Weekly menu generation failed: {str(e)}"
        ) from e
