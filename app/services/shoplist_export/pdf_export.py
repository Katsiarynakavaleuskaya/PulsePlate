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
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Type, TypeAlias

from app.schemas.catalog import CurrencyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)

ReportLabComponents: TypeAlias = tuple[
    Any,  # colors
    Any,  # A4
    Callable[[], Any],  # getSampleStyleSheet
    Any,  # mm
    Type[Any],  # Paragraph
    Type[Any],  # SimpleDocTemplate
    Type[Any],  # Spacer
    Type[Any],  # Table
    Type[Any],  # TableStyle
]


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


_MONEY_Q_DEFAULT = Decimal("0.01")
_MONEY_Q_ZERO_DECIMAL = Decimal("1")
_ZERO_DECIMAL_CURRENCIES = frozenset({"JPY", "KRW"})


def _money_quantize_for_currency(currency: str | None) -> Decimal:
    currency_code = (currency or "").upper()
    if currency_code in _ZERO_DECIMAL_CURRENCIES:
        return _MONEY_Q_ZERO_DECIMAL
    return _MONEY_Q_DEFAULT


class PdfRowType(str, Enum):
    """
    RU: Тип строки для стилизации таблицы без "магических" префиксов.
    EN: Row type used for table styling without string-prefix heuristics.
    """

    HEADER = "header"
    STORE = "store"
    AISLE = "aisle"
    ITEM = "item"
    SUBTOTAL = "subtotal"
    GRAND_TOTAL = "grand_total"


@dataclass(frozen=True)
class PdfRow:
    """
    RU: Одна строка PDF-таблицы.
    EN: One PDF table row.
    """

    row_type: PdfRowType
    cells: tuple[str, ...]


def _fmt_money(value: Decimal | None, currency: str | None) -> str:
    """
    RU: Форматирует деньги (value + currency) для PDF.
    EN: Formats money (value + currency) for PDF.

    Args:
        value: Decimal value (quantized per currency)
        currency: Currency code (e.g., "EUR", "USD") or None

    Returns:
        Formatted string (e.g., "1.50 EUR" or "1.50")
    """
    if value is None:
        return ""
    v = value.quantize(_money_quantize_for_currency(currency))
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


@lru_cache(maxsize=1)
def _lazy_reportlab() -> ReportLabComponents:
    """
    RU: Ленивый импорт reportlab (модуль должен импортироваться без reportlab).
    EN: Lazy import reportlab (module must be import-safe without reportlab).

    Uses @lru_cache for thread-safe atomic initialization.

    Returns:
        Tuple of reportlab components:
        (colors, A4, getSampleStyleSheet, mm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    return (
        colors,
        A4,
        getSampleStyleSheet,
        mm,
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
                currency = line.catalog.price.currency
                currency_code = (
                    currency.value if isinstance(currency, CurrencyDTO) else str(currency)
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


def _pick_currency(currency_codes: set[str]) -> str | None:
    """Pick first currency from set (all should be same by invariant)."""
    if not currency_codes:
        return None

    return sorted(currency_codes)[0]


def build_pdf_rows(response: ShoplistGenerateResponse) -> list[PdfRow]:
    """
    RU: Готовит строки для PDF (pure, без reportlab).
    EN: Prepares PDF rows (pure, no reportlab).

    Ordering:
    - store_id (non-empty first; empty last)
    - aisle (non-empty first; empty last)
    - food_id

    Args:
        response: ShoplistGenerateResponse from generate endpoint

    Returns:
        List of PdfRow objects with row_type for styling
    """
    all_lines: list[PackedLineDTO | UnpackedLineDTO] = [*response.packed, *response.unpacked]
    sorted_lines = sorted(all_lines, key=_sort_key)

    # Header row
    rows: list[PdfRow] = [
        PdfRow(
            row_type=PdfRowType.HEADER,
            cells=("Food ID", "Requested", "Pack Size", "Packs", "Reason", "Price", "Subtotal"),
        )
    ]

    # Group: store -> aisle
    current_store: str | None = None
    current_aisle: str | None = None
    aisle_subtotal = Decimal("0")
    grand_total = Decimal("0")
    currency_codes: set[str] = set()

    def _store_id(line: PackedLineDTO | UnpackedLineDTO) -> str:
        if line.catalog and line.catalog.store_id:
            return str(line.catalog.store_id)
        return ""

    def _aisle(line: PackedLineDTO | UnpackedLineDTO) -> str:
        if line.catalog and line.catalog.aisle:
            return str(line.catalog.aisle)
        return ""

    def flush_aisle_subtotal() -> None:
        nonlocal aisle_subtotal, grand_total, current_aisle
        if current_aisle is None:
            return
        aisle_currency = _pick_currency(currency_codes)
        rows.append(
            PdfRow(
                row_type=PdfRowType.SUBTOTAL,
                cells=(
                    "",
                    "",
                    "",
                    "",
                    f"Subtotal ({current_aisle}):",
                    "",
                    _fmt_money(aisle_subtotal, aisle_currency),
                ),
            )
        )
        grand_total += aisle_subtotal
        aisle_subtotal = Decimal("0")
        current_aisle = None

    for line in sorted_lines:
        store_id = _store_id(line)
        aisle = _aisle(line)

        if current_store != store_id:
            # Store changed => flush previous aisle subtotal
            flush_aisle_subtotal()
            current_store = store_id
            current_aisle = None
            rows.append(
                PdfRow(
                    row_type=PdfRowType.STORE,
                    cells=(f"Store: {store_id or '—'}", "", "", "", "", "", ""),
                )
            )

        # Normalize empty aisle to None to prevent duplicate "Aisle: —" headers
        normalized_aisle: str | None = aisle if aisle else None
        if current_aisle != normalized_aisle:
            # Aisle changed => flush previous aisle subtotal
            flush_aisle_subtotal()
            current_aisle = normalized_aisle
            rows.append(
                PdfRow(
                    row_type=PdfRowType.AISLE,
                    cells=(f"Aisle: {aisle or '—'}", "", "", "", "", "", ""),
                )
            )

        requested_qty = (
            _fmt_quantity(line.requested.value, line.requested.unit) if line.requested else ""
        )
        pack_size_qty = ""
        packs_str = ""
        price_str = ""
        subtotal_str = ""
        subtotal_value = Decimal("0")

        reason_str = _get_reason_str(line)

        if isinstance(line, PackedLineDTO):
            packs = int(line.packs)
            pack_size_qty = (
                _fmt_quantity(line.pack_size.value, line.pack_size.unit) if line.pack_size else ""
            )
            packs_str = str(packs)

            if line.catalog and line.catalog.price:
                currency = line.catalog.price.currency
                currency_code = (
                    currency.value if isinstance(currency, CurrencyDTO) else str(currency)
                )
                currency_codes.add(currency_code)
                price_str = _fmt_money(line.catalog.price.value, currency_code)
                if packs > 0:
                    subtotal_value = line.catalog.price.value * Decimal(packs)
                    subtotal_str = _fmt_money(subtotal_value, currency_code)

        aisle_subtotal += subtotal_value

        rows.append(
            PdfRow(
                row_type=PdfRowType.ITEM,
                cells=(
                    line.food_id,
                    requested_qty,
                    pack_size_qty,
                    packs_str,
                    reason_str,
                    price_str,
                    subtotal_str,
                ),
            )
        )

    # Flush last aisle subtotal
    flush_aisle_subtotal()

    # Defensive guard: mixed currencies are not supported by design.
    # If this invariant is ever broken upstream, fail loudly (caller masks in production).
    if len(currency_codes) > 1:
        raise ValueError("Mixed currencies in VIP shoplist are not supported")

    # Grand total row
    grand_total_currency: str | None = _pick_currency(currency_codes)
    rows.append(
        PdfRow(
            row_type=PdfRowType.GRAND_TOTAL,
            cells=("", "", "", "", "Total", "", _fmt_money(grand_total, grand_total_currency)),
        )
    )

    return rows


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

        elements: list[Any] = []

        # Title
        elements.append(Paragraph("PulsePlate — VIP Shoplist", styles["Title"]))
        elements.append(Spacer(1, 5 * mm))

        # Metadata (extract from first non-empty catalog if available)
        meta_info: list[str] = []
        all_original_lines: list[PackedLineDTO | UnpackedLineDTO] = []
        all_original_lines.extend(response.packed)
        all_original_lines.extend(response.unpacked)
        first_catalog = next((line.catalog for line in all_original_lines if line.catalog), None)
        if first_catalog:
            if first_catalog.region_id:
                meta_info.append(f"Region ID: {first_catalog.region_id}")
            if first_catalog.store_id:
                meta_info.append(f"Store ID: {first_catalog.store_id}")
        if meta_info:
            elements.append(Paragraph(" | ".join(meta_info), styles["Normal"]))
            elements.append(Spacer(1, 5 * mm))

        # Build PDF rows (pure data preparation with row types)
        rows = build_pdf_rows(response)
        table_data = [row.cells for row in rows]

        table = Table(table_data)

        # Styling by row_type, not by string parsing
        style_commands: list[tuple[Any, ...]] = [
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (5, 1), (6, -1), "RIGHT"),  # Price and Subtotal right-aligned
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]

        for idx, row in enumerate(rows):
            if row.row_type == PdfRowType.HEADER:
                style_commands.extend(
                    [
                        ("BACKGROUND", (0, idx), (-1, idx), colors.lightgrey),
                        ("TEXTCOLOR", (0, idx), (-1, idx), colors.black),
                        ("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, idx), (-1, idx), 6),
                    ]
                )
            elif row.row_type == PdfRowType.STORE:
                style_commands.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
                style_commands.append(("BACKGROUND", (0, idx), (-1, idx), colors.whitesmoke))
            elif row.row_type == PdfRowType.AISLE:
                style_commands.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
            elif row.row_type in (PdfRowType.SUBTOTAL, PdfRowType.GRAND_TOTAL):
                style_commands.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))

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
