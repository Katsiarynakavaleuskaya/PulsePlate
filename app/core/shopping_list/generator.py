"""Shopping List Generator.

RU: Основная логика генерации списка покупок.
EN: Main shopping list generation logic.

This module orchestrates the shopping list generation pipeline:
1. Extract ingredients from plan_data
2. Normalize and aggregate by key
3. Group by categories
4. Generate DTO with warnings
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.schemas.shopping_list import (
    ShoppingListCategory,
    ShoppingListDTO,
    ShoppingListItem,
    ShoppingListMeta,
    ShoppingListPreferences,
    SourceType,
)

from .categories import CATEGORY_TITLES, category_for_ingredient
from .extractor import extract_ingredients_from_plan
from .normalize import humanize_title, normalize_key


def generate_shopping_list_from_plan(
    plan_data: Dict[str, Any],
    preferences: ShoppingListPreferences,
    source: SourceType = "inline_plan",
) -> ShoppingListDTO:
    """Generate shopping list from weekly plan data.

    Args:
        plan_data: Weekly plan data with daily_menus structure
        preferences: User preferences for list generation
        source: Source type ("weekly_plan_id" or "inline_plan")

    Returns:
        ShoppingListDTO with categorized items and metadata

    Algorithm:
        1. Extract all ingredients from meals
        2. Normalize keys (lowercase, snake_case)
        3. Aggregate quantities by normalized key
        4. Group by category
        5. Collect warnings for unknown categories
    """
    # Extract raw ingredients
    raw_items = extract_ingredients_from_plan(plan_data)

    # Collect warnings
    warnings: List[str] = []

    # Check if we got any ingredients
    if not raw_items:
        warnings.append("missing_ingredients")

    # Aggregate by normalized key
    aggregated: Dict[str, Dict[str, Any]] = {}

    for item in raw_items:
        key = normalize_key(item["key"])

        if key not in aggregated:
            aggregated[key] = {
                "key": key,
                "title": humanize_title(key),
                "quantity": 0.0,
                "unit": item["unit"],
                "recipe_refs": set(),
            }

        # Aggregate quantity
        aggregated[key]["quantity"] += item["quantity"]
        aggregated[key]["recipe_refs"].add(item["recipe_ref"])

    # Group by category
    categories_map: Dict[str, List[ShoppingListItem]] = defaultdict(list)

    for normalized_key in sorted(aggregated):
        data = aggregated[normalized_key]
        category_key = category_for_ingredient(data["key"])

        # Track unknown categories for debugging
        if category_key == "other" and data["key"] not in {"salt", "pepper", "water"}:
            warnings.append(f"unknown_category:{data['key']}")

        # Apply quantity rounding if enabled
        quantity = data["quantity"]
        if preferences.round_quantities:
            quantity = round(quantity, 1)
        else:
            quantity = round(quantity, 2)

        categories_map[category_key].append(
            ShoppingListItem(
                key=data["key"],
                name=data["title"],
                quantity=quantity,
                unit=data["unit"],
                recipe_refs=sorted(data["recipe_refs"]),
            )
        )

    # Build category list
    categories: List[ShoppingListCategory] = []
    for cat_key, items in categories_map.items():
        categories.append(
            ShoppingListCategory(
                key=cat_key,
                title=CATEGORY_TITLES.get(cat_key, cat_key.replace("_", " ").title()),
                items=sorted(items, key=lambda i: i.name),
            )
        )

    # Sort categories for deterministic output
    categories.sort(key=lambda c: c.title)

    return ShoppingListDTO(
        categories=categories,
        total_items=len(aggregated),
        generated_at=datetime.now(timezone.utc),
        meta=ShoppingListMeta(
            source=source,
            unit_system=preferences.unit_system,
            warnings=warnings,
        ),
    )
