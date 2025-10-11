"""Shoplist export endpoints (JSON, CSV, PDF).

Provides a simple read-only representation of the current shopping list and
file exports so the frontend can offer downloads without blocking future
integration with the richer generator pipeline.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import csv
from datetime import UTC, datetime
from io import BytesIO, StringIO
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Response
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from core.i18n import Language, t


router = APIRouter(prefix="/api/v1/shoplist", tags=["shoplist"])

FONTS_DIR = Path("assets/fonts")
FONT_PATH = FONTS_DIR / "DejaVuSans.ttf"
FONT_NAME = "DejaVuSans"
DEFAULT_LANG: Language = "en"


def _export_timestamp() -> str:
    """Return an RFC3339-like timestamp usable in filenames."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _demo_shoplist() -> dict[str, Any]:
    """Return a deterministic demo shoplist structure for now.

    Once the full profile-aware generator is ready we can replace this helper
    with a real service call but the shape of the response will remain stable.
    """
    groups: list[dict[str, Any]] = [
        {
            "aisle": "Produce",
            "items": [
                {
                    "id": "apple",
                    "name": "Яблоко",
                    "qty": 4,
                    "unit": "шт",
                    "note": "сладкие",
                },
                {
                    "id": "spinach",
                    "name": "Baby spinach",
                    "qty": 0.3,
                    "unit": "кг",
                    "note": "для смузи",
                },
            ],
        },
        {
            "aisle": "Dairy",
            "items": [
                {
                    "id": "yogurt",
                    "name": "Greek yogurt",
                    "qty": 2,
                    "unit": "шт",
                    "note": "500 g tubs",
                }
            ],
        },
        {
            "aisle": "Pantry",
            "items": [
                {
                    "id": "oats",
                    "name": "Rolled oats",
                    "qty": 1,
                    "unit": "кг",
                },
                {
                    "id": "almonds",
                    "name": "Almonds",
                    "qty": 0.25,
                    "unit": "кг",
                },
            ],
        },
    ]

    flat_items = _flatten_shop_items(groups)

    return {
        "store": "PulsePlate Demo Store",
        "currency": "USD",
        "total_estimated": 42.7,
        "groups": groups,
        "items": flat_items,
    }


def _flatten_shop_items(groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten grouped shoplist items into a single list."""
    rows: list[dict[str, Any]] = []
    for group in groups:
        aisle = group.get("aisle", "") if isinstance(group, dict) else ""
        items = group.get("items") if isinstance(group, dict) else None
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    {
                        "aisle": aisle,
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "qty": item.get("qty"),
                        "unit": item.get("unit"),
                        "note": item.get("note"),
                    }
                )
    return rows


def _iter_flat_rows(items: Iterable[dict[str, Any]]) -> Iterable[list[str]]:
    """Yield CSV rows as lists of strings."""
    for item in items:
        yield [
            str(item.get("aisle", "") or ""),
            str(item.get("name", "") or ""),
            str(item.get("qty", "") or ""),
            str(item.get("unit", "") or ""),
            str(item.get("note", "") or ""),
        ]


def _register_font_if_available() -> str:
    """Register the bundled DejaVuSans font to support Cyrillic text."""
    # Check if font is already registered
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME

    if not FONT_PATH.exists():
        return "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        return FONT_NAME
    except Exception as exc:
        # Fall back to Helvetica for any registration error
        logging.warning("Font registration failed, using Helvetica fallback: %s", exc)
        return "Helvetica"


def _render_pdf(shop: dict[str, Any], lang: Language = DEFAULT_LANG) -> bytes:
    """Render a printable PDF representation of *shop*."""
    buf = BytesIO()
    page_w, page_h = A4
    font = _register_font_if_available()

    c = canvas.Canvas(buf, pagesize=A4)

    generated_at = datetime.now(UTC)
    header = t(lang, "shoplist.header.title")
    meta = t(
        lang,
        "shoplist.meta",
        store=shop.get("store", "-"),
        currency=shop.get("currency", ""),
    )
    total = shop.get("total_estimated")

    def draw_table_head(current_canvas: canvas.Canvas, ypos: float) -> float:
        current_canvas.setFont(font, 11)
        current_canvas.drawString(40, ypos, t(lang, "shoplist.columns.aisle"))
        current_canvas.drawString(160, ypos, t(lang, "shoplist.columns.item"))
        current_canvas.drawString(380, ypos, t(lang, "shoplist.columns.qty"))
        current_canvas.drawString(430, ypos, t(lang, "shoplist.columns.unit"))
        current_canvas.drawString(470, ypos, t(lang, "shoplist.columns.note"))
        ypos -= 14
        current_canvas.line(40, ypos, 550, ypos)
        return ypos - 10

    c.setFont(font, 16)
    c.drawString(40, page_h - 50, header)
    c.setFont(font, 10)
    c.drawString(40, page_h - 70, meta)
    if isinstance(total, int | float):
        total_str = t(
            lang,
            "shoplist.total",
            total=f"{total}",
            currency=shop.get("currency", ""),
        )
        c.drawString(
            40,
            page_h - 85,
            total_str,
        )

    raw_rows = shop.get("items")
    if isinstance(raw_rows, list) and raw_rows:
        rows = raw_rows
    else:
        rows = _flatten_shop_items(shop.get("groups", []))
    y = draw_table_head(c, page_h - 110)
    c.setFont(font, 10)

    for row in rows:
        if y < 60:
            c.showPage()
            c.setFont(font, 16)
            c.drawString(40, page_h - 50, t(lang, "shoplist.continued"))
            y = draw_table_head(c, page_h - 70)
            c.setFont(font, 10)

        c.drawString(40, y, str(row.get("aisle", ""))[:24])
        c.drawString(160, y, str(row.get("name", ""))[:40])
        c.drawString(380, y, str(row.get("qty", "")))
        c.drawString(430, y, str(row.get("unit", "")))
        c.drawString(470, y, str(row.get("note", ""))[:22])
        y -= 14

    c.setFont(font, 8)
    c.drawRightString(
        550,
        30,
        generated_at.strftime(t(lang, "export.generated_at") + " %Y-%m-%d %H:%M UTC"),
    )
    c.save()

    return buf.getvalue()


@router.get("")
async def get_shoplist() -> dict[str, Any]:
    """Return the current shoplist in JSON form."""
    return _demo_shoplist()


@router.get("/export.csv")
async def export_shoplist_csv(
    lang: Language = Query(DEFAULT_LANG, pattern="^(en|ru|es)$"),
) -> Response:
    """Export the current shoplist as a CSV attachment."""
    shop = _demo_shoplist()
    items = shop.get("items", [])

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["aisle", "name", "qty", "unit", "note"])
    writer.writerows(_iter_flat_rows(items))

    csv_bytes = buffer.getvalue().encode("utf-8")
    filename = f"shoplist_{_export_timestamp()}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.pdf")
async def export_shoplist_pdf(
    lang: Language = Query(DEFAULT_LANG, pattern="^(en|ru|es)$"),
) -> Response:
    """Return a fully rendered PDF attachment for the shoplist."""
    shop = _demo_shoplist()
    pdf_bytes = await asyncio.to_thread(_render_pdf, shop, lang)
    filename = f"shoplist_{_export_timestamp()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["router"]
