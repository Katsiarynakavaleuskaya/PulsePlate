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

import contextlib
import io
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Tuple, Tuple

from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)


_REPORTLAB_UNSET = object()

# reportlab is an optional dependency; keep module import-safe by initializing these lazily
colors: Any = _REPORTLAB_UNSET
A4: Any = _REPORTLAB_UNSET
getSampleStyleSheet: Any = _REPORTLAB_UNSET
mm: Any = _REPORTLAB_UNSET
Flowable: Any = _REPORTLAB_UNSET
Paragraph: Any = _REPORTLAB_UNSET
SimpleDocTemplate: Any = _REPORTLAB_UNSET
Spacer: Any = _REPORTLAB_UNSET
Table: Any = _REPORTLAB_UNSET
TableStyle: Any = _REPORTLAB_UNSET


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


# Money formatting constants
MONEY_Q = Decimal("0.01")


def _fmt_money(value: Decimal | None, currency: str | None) -> str:
    """
    RU: Форматирует деньги (value + currency) для PDF.
    EN: Formats money (value + currency) for PDF.

    Args:
        value: Decimal value (quantized to 0.01)
        currency: Currency code (e.g., "EUR", "USD") or None

    Returns:
        Formatted string (e.g., "1.50 EUR" or "1.50")
    """
    if value is None:
        return ""
    v = value.quantize(MONEY_Q)
    cur = currency or ""
    return f"{format(v, 'f')} {cur}".strip()


def _get_reason_str(line: PackedLineDTO | UnpackedLineDTO) -> str:
    """
    RU: Извлекает reason как строку (для packed = reasons.join, для unpacked = reason).
    EN: Extracts reason as string (for packed = reasons.join, for unpacked = reason).
    """
    if isinstance(line, PackedLineDTO):
        return "; ".join(line.reasons) if line.reasons else ""
    return line.reason or ""


def _lazy_reportlab() -> Tuple[Any, ...]:
    """
    RU: Ленивый импорт reportlab (модуль должен импортироваться без reportlab).
    EN: Lazy import reportlab (module must be import-safe without reportlab).

    Returns:
        Tuple of reportlab components: (colors, A4, getSampleStyleSheet, mm, Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
    """
    global A4, Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, colors, getSampleStyleSheet, mm

    if any(
        value is _REPORTLAB_UNSET
        for value in (
            colors,
            A4,
            getSampleStyleSheet,
            mm,
            Flowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    ):
        from reportlab.lib import colors as _colors
        from reportlab.lib.pagesizes import A4 as _A4
        from reportlab.lib.styles import getSampleStyleSheet as _getSampleStyleSheet
        from reportlab.lib.units import mm as _mm
        from reportlab.platypus import (
            Flowable as _Flowable,
            Paragraph as _Paragraph,
            SimpleDocTemplate as _SimpleDocTemplate,
            Spacer as _Spacer,
            Table as _Table,
            TableStyle as _TableStyle,
        )

        if colors is _REPORTLAB_UNSET:
            colors = _colors
        if A4 is _REPORTLAB_UNSET:
            A4 = _A4
        if getSampleStyleSheet is _REPORTLAB_UNSET:
            getSampleStyleSheet = _getSampleStyleSheet
        if mm is _REPORTLAB_UNSET:
            mm = _mm
        if Flowable is _REPORTLAB_UNSET:
            Flowable = _Flowable
        if Paragraph is _REPORTLAB_UNSET:
            Paragraph = _Paragraph
        if SimpleDocTemplate is _REPORTLAB_UNSET:
            SimpleDocTemplate = _SimpleDocTemplate
        if Spacer is _REPORTLAB_UNSET:
            Spacer = _Spacer
        if Table is _REPORTLAB_UNSET:
            Table = _Table
        if TableStyle is _REPORTLAB_UNSET:
            TableStyle = _TableStyle

    return (
        colors,
        A4,
        getSampleStyleSheet,
        mm,
        Flowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )


@dataclass(frozen=True)
class PdfLine:
    """
    RU: Подготовленная строка для PDF (pure data, без reportlab).
    EN: Prepared line for PDF (pure data, no reportlab).
    """

    store_id: str
    aisle: str
    food_id: str
    requested: str
    pack_size: str
    packs: int | None
    reason: str
    price: str
    subtotal: str
    subtotal_value: Decimal
    currency_code: str | None  # Currency code (e.g., "EUR", "USD") or None


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


def build_pdf_lines(response: ShoplistGenerateResponse) -> list[PdfLine]:
    """
    RU: Подготавливает строки для PDF (pure transformation, без reportlab).
    EN: Prepares lines for PDF (pure transformation, no reportlab).

    Args:
        response: ShoplistGenerateResponse from generate endpoint

    Returns:
        List of PdfLine objects, sorted by (store_id, aisle, food_id)
    """
    all_lines: list[PackedLineDTO | UnpackedLineDTO] = [*response.packed, *response.unpacked]
    sorted_lines = sorted(all_lines, key=_sort_key)

    out: list[PdfLine] = []
    for line in sorted_lines:
        store_id = line.catalog.store_id if (line.catalog and line.catalog.store_id) else ""
        aisle = line.catalog.aisle if (line.catalog and line.catalog.aisle) else ""

        requested_qty = (
            _fmt_quantity(line.requested.value, line.requested.unit) if line.requested else ""
        )

        pack_size_qty = ""
        packs: int | None = None
        price_str = ""
        subtotal_str = ""
        subtotal_value = Decimal("0")
        currency_code: str | None = None

        if isinstance(line, PackedLineDTO):
            packs = int(line.packs)
            pack_size_qty = (
                _fmt_quantity(line.pack_size.value, line.pack_size.unit) if line.pack_size else ""
            )
            if line.catalog and line.catalog.price:
                # Get currency code (CurrencyDTO enum has .value attribute)
                currency_code = (
                    line.catalog.price.currency.value
                    if hasattr(line.catalog.price.currency, "value")
                    else str(line.catalog.price.currency)
                )
                price_str = _fmt_money(line.catalog.price.value, currency_code)
                if packs > 0:
                    subtotal_value = line.catalog.price.value * Decimal(packs)
                    subtotal_str = _fmt_money(subtotal_value, currency_code)

        out.append(
            PdfLine(
                store_id=store_id,
                aisle=aisle,
                food_id=line.food_id,
                requested=requested_qty,
                pack_size=pack_size_qty,
                packs=packs,
                reason=_get_reason_str(line),
                price=price_str,
                subtotal=subtotal_str,
                subtotal_value=subtotal_value,
                currency_code=currency_code,
            )
        )
    return out


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
    # Lazy import reportlab to keep module import-safe
    (
        colors,
        A4,
        getSampleStyleSheet,
        mm,
        Flowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    ) = _lazy_reportlab()

    buffer: io.BytesIO | None = None
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title="PulsePlate VIP Shoplist",
            author="PulsePlate",
        )

        styles = getSampleStyleSheet()

        # Type hint: Flowable is imported lazily, use Any for type checking
        elements: list[Any] = []

        # Title
        elements.append(Paragraph("PulsePlate — VIP Shoplist", styles["Title"]))
        elements.append(Spacer(1, 5 * mm))

        # Build PDF lines (pure data preparation)
        pdf_lines: list[PdfLine] = build_pdf_lines(response)

        # Metadata (extract from first non-empty catalog if available)
        meta_info: list[str] = []
        # Find first non-empty catalog from original response
        all_original_lines: list[PackedLineDTO | UnpackedLineDTO] = []
        all_original_lines.extend(response.packed)
        all_original_lines.extend(response.unpacked)
        first_catalog = None
        for line in all_original_lines:
            if line.catalog:
                first_catalog = line.catalog
                break
        if first_catalog:
            if first_catalog.region_id:
                meta_info.append(f"Region ID: {first_catalog.region_id}")
            if first_catalog.store_id:
                meta_info.append(f"Store ID: {first_catalog.store_id}")
        if meta_info:
            elements.append(Paragraph(" | ".join(meta_info), styles["Normal"]))
            elements.append(Spacer(1, 5 * mm))

        # Group lines by store → aisle
        # Structure: {store_id: {aisle: [lines]}}
        grouped: dict[str, dict[str, list[PdfLine]]] = {}
        for pdf_line in pdf_lines:
            store_id = pdf_line.store_id or ""
            aisle = pdf_line.aisle or ""
            if store_id not in grouped:
                grouped[store_id] = {}
            if aisle not in grouped[store_id]:
                grouped[store_id][aisle] = []
            grouped[store_id][aisle].append(pdf_line)

        # Build table with grouping and subtotals
        table_data: list[list[str]] = [
            [
                "Food ID",
                "Requested",
                "Pack Size",
                "Packs",
                "Reason",
                "Price",
                "Subtotal",
            ]
        ]

        grand_total = Decimal("0")
        currency_code: str | None = None

        # Sort stores (non-empty first)
        sorted_stores = sorted(grouped.keys(), key=lambda s: (s == "", s))

        for store_id in sorted_stores:
            store_lines = grouped[store_id]
            # Store header
            if store_id:
                table_data.append(
                    [
                        f"STORE: {store_id}",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )

            # Sort aisles (non-empty first)
            sorted_aisles = sorted(store_lines.keys(), key=lambda a: (a == "", a))

            for aisle in sorted_aisles:
                aisle_lines = store_lines[aisle]
                aisle_subtotal = Decimal("0")

                # Aisle header
                if aisle:
                    table_data.append(
                        [
                            f"  Aisle: {aisle}",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )

                # Items in aisle
                for pdf_line in aisle_lines:
                    packs_str = str(pdf_line.packs) if pdf_line.packs is not None else ""
                    table_data.append(
                        [
                            pdf_line.food_id,
                            pdf_line.requested,
                            pdf_line.pack_size,
                            packs_str,
                            pdf_line.reason,
                            pdf_line.price,
                            pdf_line.subtotal,
                        ]
                    )
                    aisle_subtotal += pdf_line.subtotal_value
                    # Use currency_code from PdfLine (no string parsing)
                    if currency_code is None and pdf_line.currency_code:
                        currency_code = pdf_line.currency_code

                # Aisle subtotal
                if aisle:
                    subtotal_str = _fmt_money(aisle_subtotal, currency_code)
                    table_data.append(
                        [
                            "",
                            "",
                            "",
                            "",
                            f"Subtotal ({aisle}):",
                            "",
                            subtotal_str,
                        ]
                    )

                grand_total += aisle_subtotal

        # Grand total row
        grand_total_str = _fmt_money(grand_total, currency_code)
        table_data.append(
            [
                "",
                "",
                "",
                "",
                "GRAND TOTAL:",
                "",
                grand_total_str,
            ]
        )

        table = Table(table_data)
        # Build style commands
        style_commands: list[tuple[Any, ...]] = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (5, 1), (6, -1), "RIGHT"),  # Price and Subtotal right-aligned
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]
        # Make store/aisle headers and totals bold
        for row_idx, row in enumerate(table_data):
            if row_idx > 0:  # Skip header
                col0 = str(row[0]) if len(row) > 0 and row[0] is not None else ""
                col4 = str(row[4]) if len(row) > 4 and row[4] is not None else ""
                if (
                    col0.startswith("STORE:")
                    or col0.startswith("  Aisle:")
                    or col4.startswith("Subtotal")
                    or col4.startswith("GRAND TOTAL")
                ):
                    style_commands.append(
                        ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
                    )
        table.setStyle(TableStyle(style_commands))
        elements.append(table)

        doc.build(elements)
        return buffer.getvalue()
    except ImportError:
        # Re-raise ImportError so caller can handle it as 501
        raise
    except Exception as exc:
        logging.exception("PDF generation failed")
        # Do not include exception details in error message (security: no info leak)
        raise RuntimeError("PDF generation failed") from exc
    finally:
        if buffer is not None:
            with contextlib.suppress(Exception):
                buffer.close()
