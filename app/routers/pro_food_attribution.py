"""PRO endpoint for food-data license attribution."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.middleware.api_tiers import require_pro_tier
from app.schemas.food import FoodAttributionResponse, FoodSourceAttribution
from app.services import food_store

router = APIRouter(
    prefix="/api/v1/pro",
    tags=["pro"],
    dependencies=[Depends(require_pro_tier)],
)


@router.get("/attribution", response_model=FoodAttributionResponse)
def get_food_data_attribution() -> FoodAttributionResponse:
    """
    Return source-license attribution for Food DB providers.

    RU: Возвращает лицензии и атрибуцию источников Food DB.
    EN: Returns source licenses and attribution for Food DB.
    """
    sources = [
        FoodSourceAttribution(
            source=str(row["source"]),
            license=str(row["license"]),
            attribution=str(row["attribution"]),
            source_url=row.get("source_url"),
        )
        for row in food_store.get_food_source_attributions()
    ]
    generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return FoodAttributionResponse(generated_at_utc=generated_at_utc, sources=sources)
