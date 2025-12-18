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
from app.schemas.shopping_list import ShoplistDayResponse

router = APIRouter(prefix="/api/v1/pro/shoplist", tags=["pro", "shoplist-day"])


@router.get(
    "/day",
    response_model=ShoplistDayResponse,
    summary="Shopping list suggestions for a day (MVP placeholder)",
)
async def get_shoplist_day(
    _pro: Annotated[Any, Depends(require_pro_tier)],
    day: Annotated[date, Query(alias="date", description="YYYY-MM-DD")],
    lang: Annotated[str, Query(pattern="^(ru|en|es)$")] = "en",
) -> ShoplistDayResponse:
    """MVP placeholder endpoint for day shopping list.

    Returns empty list for now (real implementation coming in PR-2).
    Later: fetch actual day plan from database and generate real items.

    **URL:** `GET /api/v1/pro/shoplist/day?date=YYYY-MM-DD&lang=ru`

    **Input:**
    - `date`: Date for shopping list (YYYY-MM-DD, required)
    - `lang`: Language for item titles (ru|en|es, default: en)

    **Output:**
    - Flat list of shopping items (client groups by aisle)
    - Empty warnings array

    **PRO tier required.**

    **Implementation roadmap (PR-2):**
    1. Fetch day_plan from DB (format: {"daily_menus": [{"meals": [...]}]})
    2. Call core engine: aggregate_ingredients(day_plan) + round_to_packages()
    3. Transform to flat day items with aisle mapping (no weekly DTO dependency)
    4. Localize titles using lang parameter
    5. Map category → ShopAisle enum (Produce/Protein/Dairy/Pantry/Frozen/Other)
    """
    # TODO: Real implementation in PR-2
    # from core.shoplist import ShoplistGenerator  # or existing core engine
    #
    # # Fetch day plan from database
    # day_plan = fetch_day_plan_from_db(day)
    #
    # # Use core engine directly (not weekly DTO)
    # generator = ShoplistGenerator()
    # aggregated = generator.aggregate_ingredients(day_plan)
    # items_with_packages = generator.round_to_packages(aggregated)
    #
    # # Transform to flat ShoplistDayItemDTO format
    # items = transform_to_day_items(items_with_packages, lang=lang)
    # return ShoplistDayResponse(date=day.isoformat(), lang=lang, items=items, warnings=[])

    return ShoplistDayResponse(date=day.isoformat(), lang=lang, items=[], warnings=[])


__all__ = ["router"]
