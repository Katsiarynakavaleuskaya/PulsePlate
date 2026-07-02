from __future__ import annotations

from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, Query

from app.metrics import LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE, record_legacy_alias_hit
from app.middleware.api_tiers import require_pro_tier
from app.routers.pro import get_daily_nutrition
from core.meal_i18n import Language

LEGACY_NUTRITION_ALIAS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    (LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE, "GET", False),
)

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

    sex_value = cast(Literal["female", "male"], sex)
    activity_value = cast(
        Literal["sedentary", "light", "moderate", "active", "very_active"], activity
    )
    goal_value = cast(Literal["loss", "maintain", "gain"], goal)
    lang_value: Language = "en"

    response = await get_daily_nutrition(
        date_str=date_str,
        sex=sex_value,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity=activity_value,
        goal=goal_value,
        lang=lang_value,
    )
    # Return canonical response as-is (avoid serialization drift in shim).
    return response
