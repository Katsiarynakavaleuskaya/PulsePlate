"""Shoplist export endpoints (JSON, CSV, PDF).

Provides a simple read-only representation of the current shopping list and
file exports so the frontend can offer downloads without blocking future
integration with the richer generator pipeline.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import logging
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen import canvas
from app.security.rate_limit import RATE_LIMIT_429_RESPONSES, RATE_LIMIT_EXPORTS, limit_if_available


class ShoplistItem(BaseModel):
    """Single item in the shoplist."""

    aisle: str
    id: Optional[str] = None
    name: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    note: Optional[str] = None


class ShoplistGroup(BaseModel):
    """Group of items by aisle."""

    aisle: str
    items: List[Dict[str, Any]]


class ShoplistResponse(BaseModel):
    """Response model for shoplist endpoint."""

    store: str
    currency: str
    total_estimated: float
    groups: List[ShoplistGroup]
    items: List[ShoplistItem]


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/shoplist", tags=["shoplist"])

FONTS_DIR = Path("assets/fonts")
FONT_PATH = FONTS_DIR / "DejaVuSans.ttf"
FONT_NAME = "DejaVuSans"


def _export_timestamp() -> str:
    """Return an RFC3339-like timestamp usable in filenames."""

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _demo_shoplist() -> Dict[str, Any]:
    """Return a deterministic demo shoplist structure for now.

    Once the full profile-aware generator is ready we can replace this helper
    with a real service call but the shape of the response will remain stable.
    """

    groups: List[Dict[str, Any]] = [
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


def _flatten_shop_items(groups: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten grouped shoplist items into a single list."""

    rows: List[Dict[str, Any]] = []
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


def _iter_flat_rows(items: Iterable[Dict[str, Any]]) -> Iterable[List[str]]:
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

    if FONT_PATH.exists():
        try:
            if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
            return FONT_NAME
        except (OSError, TTFError, ValueError) as exc:
            logger.warning("Font registration failed, falling back to Helvetica: %s", exc)
            return "Helvetica"
    else:
        logger.debug("Bundled font file not found at %s, using Helvetica fallback", FONT_PATH)
    return "Helvetica"


def _render_pdf(shop: Dict[str, Any]) -> bytes:
    """Render a printable PDF representation of *shop*."""

    buf = BytesIO()
    page_w, page_h = A4
    font = _register_font_if_available()

    c = canvas.Canvas(buf, pagesize=A4)

    generated_at = datetime.now(timezone.utc)
    header = "Список покупок / Shoplist"
    meta = f"Store: {shop.get('store', '-')}  |  Currency: {shop.get('currency', '')}"
    total = shop.get("total_estimated")

    def draw_table_head(current_canvas: canvas.Canvas, ypos: float) -> float:
        current_canvas.setFont(font, 11)
        current_canvas.drawString(40, ypos, "Aisle")
        current_canvas.drawString(160, ypos, "Item")
        current_canvas.drawString(380, ypos, "Qty")
        current_canvas.drawString(430, ypos, "Unit")
        current_canvas.drawString(470, ypos, "Note")
        ypos -= 14
        current_canvas.line(40, ypos, 550, ypos)
        return ypos - 10

    c.setFont(font, 16)
    c.drawString(40, page_h - 50, header)
    c.setFont(font, 10)
    c.drawString(40, page_h - 70, meta)
    if isinstance(total, (int, float)):
        c.drawString(
            40,
            page_h - 85,
            f"Estimated total: {total} {shop.get('currency', '')}",
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
            c.drawString(40, page_h - 50, "Список покупок (продолжение)")
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
        generated_at.strftime("Generated %Y-%m-%d %H:%M UTC"),
    )
    c.save()

    return buf.getvalue()


@router.get("", responses=RATE_LIMIT_429_RESPONSES, response_model=ShoplistResponse)
@limit_if_available(RATE_LIMIT_EXPORTS)
def get_shoplist(request: Request) -> ShoplistResponse:
    """Return the current shoplist in JSON form."""

    return ShoplistResponse(**_demo_shoplist())


@router.get("/export.csv", responses=RATE_LIMIT_429_RESPONSES)
@limit_if_available(RATE_LIMIT_EXPORTS)
def export_shoplist_csv(request: Request) -> Response:
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


@router.get("/export.pdf", responses=RATE_LIMIT_429_RESPONSES)
@limit_if_available(RATE_LIMIT_EXPORTS)
def export_shoplist_pdf(request: Request) -> Response:
    """Return a fully rendered PDF attachment for the shoplist."""

    shop = _demo_shoplist()
    pdf_bytes = _render_pdf(shop)
    filename = f"shoplist_{_export_timestamp()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["router"]
