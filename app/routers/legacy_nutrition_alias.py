from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.metrics import LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE, record_legacy_alias_hit
from app.middleware.api_tiers import require_pro_tier
from app.routers.pro import get_daily_nutrition

router = APIRouter(tags=["pro", "legacy"], include_in_schema=False)


@router.get(
    LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE,
    deprecated=True,
)
async def legacy_nutrition_date_alias(
    date_str: str,
    sex: str = Query("female", description="Biological sex (female/male)"),
    age: int = Query(30, gt=10, lt=100, description="Age in years"),
    height_cm: float = Query(165, gt=100, lt=250, description="Height in cm"),
    weight_kg: float = Query(65, gt=30, lt=300, description="Weight in kg"),
    activity: str = Query("moderate", description="Activity level"),
    goal: str = Query("maintain", description="Nutrition goal"),
    _: str = Depends(require_pro_tier),
) -> Any:
    """Legacy alias for iOS nutrition endpoint compatibility.

    RU: Устаревший алиас для iOS совместимости — делегирует на PRO endpoint.
    EN: Legacy alias for iOS compatibility — delegates to PRO endpoint.

    Observability is allowed here; legacy_app.py stays thin-only.
    """
    record_legacy_alias_hit(LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE)

    response = await get_daily_nutrition(
        date_str=date_str,
        sex=sex,  # type: ignore
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity=activity,  # type: ignore
        goal=goal,  # type: ignore
    )
    # Return canonical response as-is (avoid serialization drift in shim).
    return response
