"""Legacy premium weekly-plan route ownership.

This endpoint remains a hidden compatibility alias for the canonical VIP weekly
menu execution path. Keep the handler thin and behavior-compatible with the
legacy route while route registration ownership moves out of ``legacy_app.py``.
"""

from __future__ import annotations

import logging
from typing import Any, NoReturn

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError

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
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Targets-based weekly plans are not supported on this endpoint. "
            "Provide full profile data or use /api/v1/premium/plan/week-flexible.",
        ),
        (status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid weekly plan request payload"),
    }
)

LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/premium/plan/week", "POST", False),
)

router = APIRouter()


def _raise_weekly_menu_failure() -> NoReturn:
    """Log the active server-side exception and raise the stable client error."""

    logger.exception("Legacy weekly menu generation failed")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Weekly menu generation failed",
    ) from None


@router.post(
    "/api/v1/premium/plan/week",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WeeklyMenuResponse,
    include_in_schema=False,
    deprecated=True,
)
async def api_weekly_menu(
    raw_body: Any = Body(...),
) -> WeeklyMenuResponse:
    """
    RU: Генерирует недельный план питания (через core.menu_engine.make_weekly_menu).
    EN: Generate a weekly meal plan using core.menu_engine.make_weekly_menu.

    Returns keys: week_summary, daily_menus, weekly_coverage, shopping_list.
    """
    try:
        req = LegacyWeekPlanRequest.model_validate(raw_body)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid weekly plan request payload",
        ) from None

    # Guard VIP feature flag at request time to support tests that toggle env without reload.
    try:
        vip_module_enabled = is_vip_module_enabled()
    except Exception:
        _raise_weekly_menu_failure()
    if not vip_module_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VIP module is disabled",
        )

    try:
        menu_builder = get_weekly_menu_builder()
    except Exception:
        _raise_weekly_menu_failure()

    if menu_builder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weekly menu generation feature not available",
        )

    try:
        from app.routers.vip import execute_legacy_premium_week_alias_payload

        menu_payload = await execute_legacy_premium_week_alias_payload(
            req.model_dump(exclude_none=True),
            menu_builder=menu_builder,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input",
        ) from None
    except HTTPException as exc:
        if (
            exc.headers is None
            and isinstance(exc.detail, str)
            and (exc.status_code, exc.detail) in _SAFE_DOWNSTREAM_HTTP_ERRORS
        ):
            raise
        _raise_weekly_menu_failure()
    except Exception:
        _raise_weekly_menu_failure()

    try:
        response: WeeklyMenuResponse = build_legacy_weekly_menu_response(menu_payload)
        return response
    except Exception:
        _raise_weekly_menu_failure()
