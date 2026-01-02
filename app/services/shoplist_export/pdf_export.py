# -*- coding: utf-8 -*-
"""
RU: Детерминированный PDF-экспорт из ShoplistGenerateResponse (VIP shoplist).
EN: Deterministic PDF export from ShoplistGenerateResponse (VIP shoplist).

Invariants:
- No disk I/O (BytesIO only)
- No timestamps / randomness (deterministic given same input)
- Same sorting logic as CSV export
"""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)


def _fmt_decimal(value: Decimal | None) -> str:
    """
    RU: Decimal -> строка без scientific notation.
    EN: Decimal -> plain string without scientific notation.
    """
    if value is None:
        return ""
    return format(value, "f")


def _fmt_quantity(value: Decimal | None, unit: str | None) -> str:
    """
    RU: Форматирует Quantity (value + unit) для PDF.
    EN: Formats Quantity (value + unit) for PDF.
    """
    if value is None:
        return ""
    unit_str = unit or ""
    return f"{_fmt_decimal(value)} {unit_str}".strip()


def _get_reason_str(line: PackedLineDTO | UnpackedLineDTO) -> str:
    """
    RU: Извлекает reason как строку (для packed = reasons.join, для unpacked = reason).
    EN: Extracts reason as string (for packed = reasons.join, for unpacked = reason).
    """
    if isinstance(line, PackedLineDTO):
        return "; ".join(line.reasons) if line.reasons else ""
    return line.reason or ""


def _sort_key(line: PackedLineDTO | UnpackedLineDTO) -> tuple[bool, str, bool, str, str]:
    """
    RU: Ключ сортировки (такой же, как в CSV export).
    EN: Sort key (same as CSV export).

    Ordering:
    - store_id (non-empty first; empty last)
    - aisle (non-empty first; empty last)
    - food_id
    """
    store_id = ""
    if line.catalog and line.catalog.store_id:
        store_id = line.catalog.store_id
    aisle = ""
    if line.catalog and line.catalog.aisle:
        aisle = line.catalog.aisle
    # False < True => непустые значения раньше, пустые позже
    return (store_id == "", store_id, aisle == "", aisle, line.food_id)


def export_shoplist_to_pdf(response: ShoplistGenerateResponse) -> bytes:
    """
    RU: Экспортирует shoplist в PDF (строго детерминированно).
    EN: Exports shoplist to PDF (strictly deterministic).

    Ordering:
    - store_id (non-empty first; empty last)
    - aisle (non-empty first; empty last)
    - food_id

    Args:
        response: ShoplistGenerateResponse from generate endpoint (already enriched with catalog)

    Returns:
        PDF data as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="PulsePlate VIP Shoplist",
        author="PulsePlate",
    )

    styles = getSampleStyleSheet()
    from reportlab.platypus import Flowable

    elements: list[Flowable] = []

    # Title
    elements.append(Paragraph("PulsePlate — VIP Shoplist", styles["Title"]))
    elements.append(Spacer(1, 0.2 * mm))

    # Metadata (extract from first line's catalog if available)
    meta_info: list[str] = []
    all_lines: list[PackedLineDTO | UnpackedLineDTO] = []
    all_lines.extend(response.packed)
    all_lines.extend(response.unpacked)
    if all_lines and all_lines[0].catalog:
        if all_lines[0].catalog.region_id:
            meta_info.append(f"Region ID: {all_lines[0].catalog.region_id}")
        if all_lines[0].catalog.store_id:
            meta_info.append(f"Store ID: {all_lines[0].catalog.store_id}")
    if meta_info:
        elements.append(Paragraph(" | ".join(meta_info), styles["Normal"]))
        elements.append(Spacer(1, 0.1 * mm))

    # Sort lines (same logic as CSV)
    sorted_lines = sorted(all_lines, key=_sort_key)

    # Table Header
    table_data: list[list[str]] = [
        [
            "Food ID",
            "Requested",
            "Pack Size",
            "Packs",
            "Reason",
            "Aisle",
            "Price",
            "Subtotal",
        ]
    ]

    # Populate table data
    for line in sorted_lines:
        requested_qty = (
            _fmt_quantity(line.requested.value, line.requested.unit) if line.requested else ""
        )
        pack_size_qty = ""
        packs_str = ""  # empty for unpacked
        reason_str = _get_reason_str(line)
        aisle_str = line.catalog.aisle if (line.catalog and line.catalog.aisle) else ""
        price_str = ""
        subtotal_str = ""

        if isinstance(line, PackedLineDTO):
            pack_size_qty = (
                _fmt_quantity(line.pack_size.value, line.pack_size.unit) if line.pack_size else ""
            )
            packs_str = str(line.packs)

            if line.catalog and line.catalog.price:
                price_str = _fmt_decimal(line.catalog.price.value)

            # Calculate subtotal (price * packs)
            if line.catalog and line.catalog.price and line.packs > 0:
                subtotal_str = _fmt_decimal(line.catalog.price.value * Decimal(line.packs))

        table_data.append(
            [
                line.food_id,
                requested_qty,
                pack_size_qty,
                packs_str,
                reason_str,
                aisle_str,
                price_str,
                subtotal_str,
            ]
        )

    table = Table(table_data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(table)

    # Build PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
