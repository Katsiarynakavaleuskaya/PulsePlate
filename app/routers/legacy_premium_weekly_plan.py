"""Legacy premium weekly-plan route ownership.

This endpoint remains a hidden compatibility alias for the canonical VIP weekly
menu execution path. Keep the handler thin and behavior-compatible with the
legacy route while route registration ownership moves out of ``legacy_app.py``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.routers.api_key import _get_api_key_dynamic
from app.schemas.legacy_premium_weekly_plan import LegacyWeekPlanRequest, WeeklyMenuResponse
from app.services.legacy_premium_weekly_plan import (
    build_legacy_weekly_menu_response,
    get_weekly_menu_builder,
)
from app.utils.feature_flags import is_vip_module_enabled

logger = logging.getLogger(__name__)

_SAFE_DOWNSTREAM_HTTP_ERRORS = frozenset(
    {
        (
            422,
            "Targets-based weekly plans are not supported on this endpoint. "
            "Provide full profile data or use /api/v1/premium/plan/week-flexible.",
        ),
        (422, "Invalid weekly plan request payload"),
    }
)

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
    # Guard VIP feature flag at request time to support tests that toggle env without reload.
    try:
        vip_module_enabled = is_vip_module_enabled()
    except Exception:
        logger.exception("Legacy weekly menu generation failed")
        raise HTTPException(status_code=500, detail="Weekly menu generation failed") from None
    if not vip_module_enabled:
        raise HTTPException(status_code=503, detail="VIP module is disabled")

    try:
        menu_builder = get_weekly_menu_builder()
    except Exception:
        logger.exception("Legacy weekly menu generation failed")
        raise HTTPException(status_code=500, detail="Weekly menu generation failed") from None

    if menu_builder is None:
        raise HTTPException(status_code=503, detail="Weekly menu generation feature not available")

    try:
        from app.routers.vip import execute_legacy_premium_week_alias_payload

        menu_payload = await execute_legacy_premium_week_alias_payload(
            req.model_dump(exclude_none=True),
            menu_builder=menu_builder,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid input") from None
    except HTTPException as exc:
        if (
            exc.headers is None
            and isinstance(exc.detail, str)
            and (exc.status_code, exc.detail) in _SAFE_DOWNSTREAM_HTTP_ERRORS
        ):
            raise
        logger.exception("Legacy weekly menu generation failed")
        raise HTTPException(status_code=500, detail="Weekly menu generation failed") from None
    except Exception:
        logger.exception("Legacy weekly menu generation failed")
        raise HTTPException(status_code=500, detail="Weekly menu generation failed") from None

    try:
        return build_legacy_weekly_menu_response(menu_payload)
    except Exception:
        logger.exception("Legacy weekly menu generation failed")
        raise HTTPException(status_code=500, detail="Weekly menu generation failed") from None
