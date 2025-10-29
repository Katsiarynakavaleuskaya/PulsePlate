"""
Tests for app.routers.shoplist_export helper utilities.

We avoid exercising FastAPI routes and focus on pure helpers to
increase coverage safely and quickly.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pytest

pytest.importorskip("app.routers.shoplist_export")
from app.routers import shoplist_export as se


def test_flatten_and_iter_rows() -> None:
    groups: List[Dict[str, Any]] = [
        {
            "aisle": "Produce",
            "items": [
                {"id": "a", "name": "Apple", "qty": 3, "unit": "pcs", "note": "red"},
                42,  # non-dict item to exercise continue branch
            ],
        },
        {"aisle": "Pantry", "items": [{"id": "o", "name": "Oats", "qty": 1, "unit": "kg"}]},
    ]

    flat = se._flatten_shop_items(groups)
    assert len(flat) == 2
    assert flat[0]["aisle"] == "Produce"
    assert flat[1]["name"] == "Oats"

    rows = list(se._iter_flat_rows(flat))
    assert rows[0] == ["Produce", "Apple", "3", "pcs", "red"]
    assert rows[1][:3] == ["Pantry", "Oats", "1"]


def test_export_timestamp_format() -> None:
    ts = se._export_timestamp()
    # RFC3339-like compact format: YYYYMMDDTHHMMSSZ
    assert len(ts) == 16 and ts.endswith("Z") and "T" in ts


def test_register_font_and_render_pdf() -> None:
    # If font is missing, fallback returns a default font name
    font_name = se._register_font_if_available()
    assert isinstance(font_name, str) and len(font_name) > 0

    # Render demo shop as PDF; ensure non-empty bytes
    pdf_bytes = se._render_pdf(se._demo_shoplist())
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 500  # sanity threshold


def test_render_pdf_without_items_triggers_group_flatten_and_page_break() -> None:
    # Construct many rows via groups only to trigger page break path
    many = [
        {
            "aisle": f"A{i}",
            "items": [
                {"id": str(j), "name": f"Item {j}", "qty": j, "unit": "u"} for j in range(10)
            ],
        }
        for i in range(30)
    ]
    shop = {"store": "s", "currency": "USD", "groups": many}
    pdf_bytes = se._render_pdf(shop)
    assert isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) > 1000


def test_route_helpers_return_data() -> None:
    # Call route functions directly to cover return paths
    data = se.get_shoplist()
    assert isinstance(data, dict) and "items" in data

    resp_csv = se.export_shoplist_csv()
    assert hasattr(resp_csv, "media_type") and "text/csv" in resp_csv.media_type

    resp_pdf = se.export_shoplist_pdf()
    assert hasattr(resp_pdf, "media_type") and "application/pdf" in resp_pdf.media_type
