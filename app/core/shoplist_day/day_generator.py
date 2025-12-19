from __future__ import annotations

from typing import Any, Dict, List

from app.core.shopping_list.generator import generate_shopping_list_from_plan
from app.schemas.shopping_list import ShoplistDayItemDTO, ShoppingListPreferences

from .flatten import flatten_weekly_to_day_items


def generate_day_items(plan_data: Dict[str, Any], lang: str) -> List[ShoplistDayItemDTO]:
    """Generate flat day shopping list items from a day plan.

    This adapter reuses the existing weekly shopping list generator and
    then flattens its DTO into the iOS day item format.
    """

    prefs = ShoppingListPreferences(
        group_by="category",
        unit_system="metric",
        merge_similar_items=True,
        round_quantities=True,
    )

    weekly_dto = generate_shopping_list_from_plan(
        plan_data=plan_data,
        preferences=prefs,
        source="day_plan",
    )

    return flatten_weekly_to_day_items(weekly_dto, lang=lang)
