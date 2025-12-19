from __future__ import annotations

from types import SimpleNamespace

from app.core.shoplist_day.flatten import flatten_weekly_to_day_items
from app.schemas.shopping_list import ShopAisle, ShopUnit


def test_flatten_weekly_to_day_items_sanitizes_bad_inputs() -> None:
    items = [
        SimpleNamespace(key="bad_qty", name="Bad Qty", quantity="oops", unit="kg"),
        SimpleNamespace(key="nonfinite", name="Nonfinite", quantity=float("inf"), unit="kg"),
        SimpleNamespace(key="bad_unit", name="Bad Unit", quantity=2, unit="nope"),
    ]
    category = SimpleNamespace(key=None, title=None, items=items)
    dto = SimpleNamespace(categories=[category])

    results = flatten_weekly_to_day_items(dto, lang="en")

    assert len(results) == 3
    assert results[0].qty == 1.0
    assert results[1].qty == 1.0
    assert results[2].unit == ShopUnit.pcs
    for result in results:
        assert result.aisle == ShopAisle.other
