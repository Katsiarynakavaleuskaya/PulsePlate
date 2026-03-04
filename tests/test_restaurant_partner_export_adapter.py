from __future__ import annotations

import pytest

from app.schemas.restaurant_partner import FulfillmentMode
from app.services.restaurant_partner_export_adapter import build_order_draft_from_weekly_plan


def _consent() -> dict[str, object]:
    return {
        "consent_share_with_partner": True,
        "consent_version": "v1",
    }


def _week_plan() -> dict[str, object]:
    return {
        "days": [
            {
                "date": "2026-03-04",
                "meals": [
                    {
                        "name": "Breakfast",
                        "items": [
                            {"name": "Oats", "qty": 2, "note": "with berries"},
                            {"title": "Greek yogurt", "qty": 1},
                        ],
                    }
                ],
            }
        ]
    }


def test_build_order_draft_from_weekly_plan_happy_path_deterministic() -> None:
    draft = build_order_draft_from_weekly_plan(
        week_plan=_week_plan(),
        restaurant_id="resto-1",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=99,
        delivery_fee_minor=0,
        customer_note="No peanuts",
        dietary_tags=["high-protein"],
        allergens=["nuts"],
        consent=_consent(),
        attribution_source="vip-weekly-plan",
        unit_price_minor_default=0,
    )

    assert draft.restaurant_id == "resto-1"
    assert draft.currency == "USD"
    assert draft.fulfillment == FulfillmentMode.pickup
    assert [item.menu_item_id for item in draft.items] == [
        "wk-d01-m01-i001",
        "wk-d01-m01-i002",
    ]
    assert [item.title for item in draft.items] == ["Oats", "Greek yogurt"]
    assert [item.qty for item in draft.items] == [2, 1]
    assert draft.items[0].note == "with berries"


def test_build_order_draft_supports_menu_wrapper() -> None:
    wrapped = {"menu": _week_plan()}
    draft = build_order_draft_from_weekly_plan(
        week_plan=wrapped,
        restaurant_id="resto-2",
        currency="USD",
        fulfillment=FulfillmentMode.delivery,
        service_fee_minor=0,
        delivery_fee_minor=199,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=10,
    )
    assert len(draft.items) == 2
    assert all(item.unit_price_minor == 10 for item in draft.items)


def test_build_order_draft_supports_data_days_wrapper() -> None:
    base = build_order_draft_from_weekly_plan(
        week_plan=_week_plan(),
        restaurant_id="resto-base",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    wrapped = build_order_draft_from_weekly_plan(
        week_plan={"data": _week_plan()},
        restaurant_id="resto-base",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    assert wrapped == base


def test_build_order_draft_supports_data_daily_menus_wrapper() -> None:
    base = build_order_draft_from_weekly_plan(
        week_plan=_week_plan(),
        restaurant_id="resto-base-2",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    wrapped = build_order_draft_from_weekly_plan(
        week_plan={"data": {"daily_menus": _week_plan()["days"]}},
        restaurant_id="resto-base-2",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    assert wrapped == base


def test_build_order_draft_qty_is_bounded() -> None:
    week = _week_plan()
    week["days"][0]["meals"][0]["items"][0]["qty"] = 0
    week["days"][0]["meals"][0]["items"][1]["qty"] = 999

    draft = build_order_draft_from_weekly_plan(
        week_plan=week,
        restaurant_id="resto-3",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    assert [item.qty for item in draft.items] == [1, 100]


def test_build_order_draft_qty_none_defaults_to_one() -> None:
    week = _week_plan()
    week["days"][0]["meals"][0]["items"][0]["qty"] = None

    draft = build_order_draft_from_weekly_plan(
        week_plan=week,
        restaurant_id="resto-qty-none",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    assert draft.items[0].qty == 1


def test_build_order_draft_invalid_qty_raises_value_error() -> None:
    week = _week_plan()
    week["days"][0]["meals"][0]["items"][0]["qty"] = "abc"

    with pytest.raises(ValueError, match="qty must be numeric"):
        build_order_draft_from_weekly_plan(
            week_plan=week,
            restaurant_id="resto-bad-qty",
            currency="USD",
            fulfillment=FulfillmentMode.pickup,
            service_fee_minor=0,
            delivery_fee_minor=0,
            customer_note=None,
            dietary_tags=[],
            allergens=[],
            consent=_consent(),
            attribution_source=None,
            unit_price_minor_default=0,
        )


def test_build_order_draft_overflow_qty_raises_value_error() -> None:
    week = _week_plan()
    week["days"][0]["meals"][0]["items"][0]["qty"] = "1e309"

    with pytest.raises(ValueError, match="qty must be numeric"):
        build_order_draft_from_weekly_plan(
            week_plan=week,
            restaurant_id="resto-overflow-qty",
            currency="USD",
            fulfillment=FulfillmentMode.pickup,
            service_fee_minor=0,
            delivery_fee_minor=0,
            customer_note=None,
            dietary_tags=[],
            allergens=[],
            consent=_consent(),
            attribution_source=None,
            unit_price_minor_default=0,
        )


def test_build_order_draft_rejects_negative_default_price() -> None:
    with pytest.raises(ValueError, match="unit_price_minor_default must be >= 0"):
        build_order_draft_from_weekly_plan(
            week_plan=_week_plan(),
            restaurant_id="resto-negative-price",
            currency="USD",
            fulfillment=FulfillmentMode.pickup,
            service_fee_minor=0,
            delivery_fee_minor=0,
            customer_note=None,
            dietary_tags=[],
            allergens=[],
            consent=_consent(),
            attribution_source=None,
            unit_price_minor_default=-1,
        )


def test_build_order_draft_skips_non_list_and_non_dict_nodes() -> None:
    week = {
        "days": [
            {"meals": "oops"},
            {
                "meals": [
                    "not-a-dict-meal",
                    {"items": "not-a-list"},
                    {"items": ["not-a-dict-item", {"name": "Valid", "qty": 1}]},
                ]
            },
        ]
    }
    draft = build_order_draft_from_weekly_plan(
        week_plan=week,
        restaurant_id="resto-shape-skip",
        currency="USD",
        fulfillment=FulfillmentMode.pickup,
        service_fee_minor=0,
        delivery_fee_minor=0,
        customer_note=None,
        dietary_tags=[],
        allergens=[],
        consent=_consent(),
        attribution_source=None,
        unit_price_minor_default=0,
    )
    assert len(draft.items) == 1
    assert draft.items[0].title == "Valid"


def test_build_order_draft_raises_when_shape_missing() -> None:
    with pytest.raises(ValueError, match="days/menu.days/data.daily_menus"):
        build_order_draft_from_weekly_plan(
            week_plan={"menu": {}},
            restaurant_id="resto-4",
            currency="USD",
            fulfillment=FulfillmentMode.pickup,
            service_fee_minor=0,
            delivery_fee_minor=0,
            customer_note=None,
            dietary_tags=[],
            allergens=[],
            consent=_consent(),
            attribution_source=None,
            unit_price_minor_default=0,
        )


def test_build_order_draft_rejects_non_dict_wrappers() -> None:
    with pytest.raises(ValueError, match="days/menu.days/data.daily_menus"):
        build_order_draft_from_weekly_plan(
            week_plan={"menu": ["unexpected"], "data": ["unexpected"]},
            restaurant_id="resto-4b",
            currency="USD",
            fulfillment=FulfillmentMode.pickup,
            service_fee_minor=0,
            delivery_fee_minor=0,
            customer_note=None,
            dietary_tags=[],
            allergens=[],
            consent=_consent(),
            attribution_source=None,
            unit_price_minor_default=0,
        )


def test_build_order_draft_raises_when_no_mappable_items() -> None:
    with pytest.raises(ValueError, match="no mappable items"):
        build_order_draft_from_weekly_plan(
            week_plan={"days": [{"meals": [{"items": [{"qty": 2}]}]}]},
            restaurant_id="resto-5",
            currency="USD",
            fulfillment=FulfillmentMode.pickup,
            service_fee_minor=0,
            delivery_fee_minor=0,
            customer_note=None,
            dietary_tags=[],
            allergens=[],
            consent=_consent(),
            attribution_source=None,
            unit_price_minor_default=0,
        )
