"""Day Shopping List API (iOS MVP).

RU: API списка покупок на день (MVP для iOS).
EN: Day shopping list API for iOS offline-first MVP.

Separate router for read-only day shoplist endpoints.
POST weekly generation remains in shopping_list_pro.py (no breaking changes).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.middleware.api_tiers import require_pro_tier
from app.schemas.shopping_list import ShopLang, ShoplistDayResponse
from app.core.shoplist_day.day_generator import generate_day_items
from app.core.shoplist_day.provider import fetch_day_plan

router = APIRouter(prefix="/api/v1/pro/shoplist", tags=["pro", "shoplist-day"])


@router.get(
    "/day",
    response_model=ShoplistDayResponse,
    summary="Shopping list suggestions for a day (MVP placeholder)",
)
async def get_shoplist_day(
    _pro: Annotated[Any, Depends(require_pro_tier)],
    day: Annotated[date, Query(alias="date", description="YYYY-MM-DD")],
    lang: Annotated[ShopLang, Query(description="Language code")] = ShopLang.en,
) -> ShoplistDayResponse:
    """MVP endpoint for day shopping list.

    PR-2: fetches day plan (if available) and generates real items.

    If no plan is found, returns empty items with a "no_day_plan" warning
    to keep the iOS client stable.
    """
    plan = await fetch_day_plan(day=day, pro_ctx=_pro)
    if plan is None:
        return ShoplistDayResponse(
            date=day.isoformat(),
            lang=lang,
            items=[],
            warnings=["no_day_plan"],
        )

    items = generate_day_items(plan_data=plan, lang=lang.value)
    return ShoplistDayResponse(date=day.isoformat(), lang=lang, items=items, warnings=[])


__all__ = ["router"]
