# -*- coding: utf-8 -*-
"""Weekly-plan to partner-order adapter (W3-R4).

RU: Детеминированный адаптер weekly plan -> PartnerOrderDraft.
EN: Deterministic adapter from weekly plan payload to PartnerOrderDraft.
"""

from __future__ import annotations

from typing import Any

from app.schemas.restaurant_partner import (
    FulfillmentMode,
    PartnerConsent,
    PartnerOrderDraft,
    PartnerOrderItemIn,
)


def _extract_days(week_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract canonical days list from supported weekly-plan wrappers."""
    for candidate in (week_plan, week_plan.get("menu"), week_plan.get("data")):
        if not isinstance(candidate, dict):
            continue
        days = candidate.get("days")
        if isinstance(days, list):
            return [day for day in days if isinstance(day, dict)]

    data_node = week_plan.get("data")
    if isinstance(data_node, dict):
        daily_menus = data_node.get("daily_menus")
        if isinstance(daily_menus, list):
            return [day for day in daily_menus if isinstance(day, dict)]

    raise ValueError("week_plan must contain days/menu.days/data.daily_menus list")


def _coerce_qty(raw_qty: Any) -> int:
    """Convert arbitrary qty to bounded positive integer for partner payload."""
    if raw_qty is None:
        return 1
    try:
        qty = int(float(raw_qty))
    except (TypeError, ValueError) as exc:
        raise ValueError("item qty must be numeric") from exc
    if qty < 1:
        return 1
    if qty > 100:
        return 100
    return qty


def build_order_draft_from_weekly_plan(
    *,
    week_plan: dict[str, Any],
    restaurant_id: str,
    currency: str,
    fulfillment: FulfillmentMode,
    service_fee_minor: int,
    delivery_fee_minor: int,
    customer_note: str | None,
    dietary_tags: list[str],
    allergens: list[str],
    consent: PartnerConsent,
    attribution_source: str | None,
    unit_price_minor_default: int,
) -> PartnerOrderDraft:
    """Build deterministic PartnerOrderDraft by flattening week/day/meal items."""
    if unit_price_minor_default < 0:
        raise ValueError("unit_price_minor_default must be >= 0")

    days = _extract_days(week_plan)
    items: list[PartnerOrderItemIn] = []

    for day_idx, day in enumerate(days, start=1):
        meals = day.get("meals") or []
        if not isinstance(meals, list):
            continue
        for meal_idx, meal in enumerate(meals, start=1):
            if not isinstance(meal, dict):
                continue
            meal_items = meal.get("items") or []
            if not isinstance(meal_items, list):
                continue
            for item_idx, item in enumerate(meal_items, start=1):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("name") or "").strip()
                if not title:
                    continue
                note_raw = item.get("note")
                note = str(note_raw).strip() if note_raw else None
                items.append(
                    PartnerOrderItemIn(
                        menu_item_id=f"wk-d{day_idx:02d}-m{meal_idx:02d}-i{item_idx:03d}",
                        title=title,
                        qty=_coerce_qty(item.get("qty")),
                        unit_price_minor=unit_price_minor_default,
                        note=note,
                    )
                )

    if not items:
        raise ValueError("week_plan contains no mappable items")

    return PartnerOrderDraft(
        restaurant_id=restaurant_id,
        currency=currency,
        fulfillment=fulfillment,
        items=items,
        service_fee_minor=service_fee_minor,
        delivery_fee_minor=delivery_fee_minor,
        customer_note=customer_note,
        dietary_tags=dietary_tags,
        allergens=allergens,
        consent=consent,
        attribution_source=attribution_source,
    )
