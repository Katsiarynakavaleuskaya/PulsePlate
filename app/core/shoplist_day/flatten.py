from __future__ import annotations

import math

from app.schemas.shopping_list import ShopAisle, ShopUnit, ShoplistDayItemDTO, ShoppingListDTO

_CATEGORY_TO_AISLE: dict[str, ShopAisle] = {
    # Fresh produce
    "produce": ShopAisle.produce,
    "vegetables": ShopAisle.produce,
    "fruits": ShopAisle.produce,
    # Proteins
    "proteins": ShopAisle.protein,
    "protein": ShopAisle.protein,
    "meat": ShopAisle.protein,
    "fish": ShopAisle.protein,
    # Dairy
    "dairy": ShopAisle.dairy,
    # Pantry / dry goods
    "pantry": ShopAisle.pantry,
    "grains": ShopAisle.pantry,
    "spices": ShopAisle.pantry,
    # Frozen
    "frozen": ShopAisle.frozen,
}


def _aisle_from_category(category: str | None) -> ShopAisle:
    if not category:
        return ShopAisle.other
    key = category.strip().lower()
    return _CATEGORY_TO_AISLE.get(key, ShopAisle.other)


def flatten_weekly_to_day_items(dto: ShoppingListDTO, lang: str) -> list[ShoplistDayItemDTO]:
    """Flatten weekly ShoppingListDTO into flat day items for iOS.

    The lang parameter is threaded for future localization, but not yet
    used in PR-2 to keep the implementation minimal and safe.
    """

    _ = lang
    items: list[ShoplistDayItemDTO] = []

    for category in getattr(dto, "categories", []):
        cat_key = getattr(category, "key", None) or getattr(category, "title", None)
        aisle = _aisle_from_category(cat_key)

        for it in getattr(category, "items", []):
            key = str(
                getattr(it, "key", "")
                or getattr(it, "name", "")
                or getattr(it, "title", "")
                or "item"
            )
            title = str(getattr(it, "name", "") or getattr(it, "title", "") or key)

            quantity = getattr(it, "quantity", None)
            try:
                qty = float(quantity) if quantity is not None else 1.0
            except (TypeError, ValueError):
                qty = 1.0
            if not math.isfinite(qty) or qty <= 0:
                qty = 1.0

            raw_unit = getattr(it, "unit", None) or ShopUnit.pcs.value
            try:
                unit = ShopUnit(str(raw_unit))
            except (ValueError, TypeError):
                unit = ShopUnit.pcs

            items.append(
                ShoplistDayItemDTO(
                    key=key[:128],
                    title=title[:256],
                    qty=qty,
                    unit=unit,
                    aisle=aisle,
                    notes=None,
                    source=None,
                )
            )

    return items
