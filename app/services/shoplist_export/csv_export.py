# -*- coding: utf-8 -*-
"""
RU: Детерминированный CSV-экспорт из ShoplistGenerateResponse.
EN: Deterministic CSV export from ShoplistGenerateResponse.

Инварианты:
- НЕ меняет packs / reasons / analytics
- НЕ трогает core engine
- Чистая функция (no I/O, no time, no env)
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal

from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)

CSV_HEADER = [
    "food_id",
    "name",
    "requested",
    "unit",
    "pack_size",
    "packs",
    "min_packs",
    "reason",
    "aisle",
    "price",
    "subtotal",
    "store_id",
    "region_id",
]

# CSV injection protection: prefix dangerous formulas
DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@")


def _sanitize_csv_cell(value: str) -> str:
    """
    RU: Защита от CSV injection (формулы в Excel/Sheets).
    EN: CSV injection protection (formulas in Excel/Sheets).

    Prefixes values starting with =, +, -, @ with single quote.
    """
    if value and value.startswith(DANGEROUS_CSV_PREFIXES):
        return f"'{value}"
    return value


def _fmt_decimal(value: Decimal | None) -> str:
    """
    RU: Decimal -> строка без scientific notation.
    EN: Decimal -> plain string without scientific notation.
    """
    return "" if value is None else format(value, "f")


def _fmt_quantity(value: Decimal | None, unit: str | None) -> str:
    """
    RU: Форматирует Quantity (value + unit) для CSV.
    EN: Formats Quantity (value + unit) for CSV.
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


def _cell(value: str | None) -> str:
    """
    RU: Применяет CSV sanitize к строковому значению.
    EN: Applies CSV sanitize to string value.
    """
    return _sanitize_csv_cell(value or "")


def export_shoplist_to_csv(response: ShoplistGenerateResponse) -> str:
    """
    RU: Экспортирует shoplist в CSV (строго детерминированно).
    EN: Exports shoplist to CSV (strictly deterministic).

    Ordering:
    - store_id (non-empty first; empty last)
    - aisle (non-empty first; empty last)
    - food_id

    Args:
        response: ShoplistGenerateResponse from generate endpoint (already enriched with catalog)

    Returns:
        CSV string with header and rows
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)

    # Объединяем packed и unpacked в один список для сортировки
    all_lines: list[PackedLineDTO | UnpackedLineDTO] = []
    all_lines.extend(response.packed)
    all_lines.extend(response.unpacked)

    # Детерминированная сортировка: empty values last
    def sort_key(
        line: PackedLineDTO | UnpackedLineDTO,
    ) -> tuple[bool, str, bool, str, str]:
        # Извлекаем store_id из catalog или используем пустую строку
        store_id = ""
        if line.catalog and line.catalog.store_id:
            store_id = line.catalog.store_id
        # Извлекаем aisle из catalog или используем пустую строку
        aisle = ""
        if line.catalog and line.catalog.aisle:
            aisle = line.catalog.aisle

        # False < True => непустые значения раньше, пустые позже
        return (store_id == "", store_id, aisle == "", aisle, line.food_id)

    sorted_lines = sorted(all_lines, key=sort_key)

    for line in sorted_lines:
        # Извлекаем данные из line
        requested_value = line.requested.value if line.requested else None
        requested_unit = line.requested.unit if line.requested else None

        # Для packed: pack_size, packs, min_packs
        # Для unpacked: pack_size = None, packs = 0, min_packs = 0
        if isinstance(line, PackedLineDTO):
            pack_size_value = line.pack_size.value if line.pack_size else None
            pack_size_unit = line.pack_size.unit if line.pack_size else None
            packs = line.packs
            min_packs = line.min_packs
        else:
            pack_size_value = None
            pack_size_unit = None
            packs = 0
            min_packs = 0

        # Извлекаем catalog данные
        catalog_store_id = ""
        catalog_region_id = ""
        catalog_aisle = ""
        catalog_price_value = None
        if line.catalog:
            catalog_store_id = line.catalog.store_id or ""
            catalog_region_id = line.catalog.region_id or ""
            catalog_aisle = line.catalog.aisle or ""
            if line.catalog.price:
                catalog_price_value = line.catalog.price.value

        # Используем region_id из catalog (enrichment уже применён в endpoint)
        final_region_id = catalog_region_id or ""

        # Вычисляем subtotal (price * packs, если price есть)
        subtotal_value = None
        if catalog_price_value is not None and packs > 0:
            subtotal_value = catalog_price_value * Decimal(packs)

        # Формируем строку CSV (sanitize для всех строковых полей)
        writer.writerow(
            [
                _cell(line.food_id),
                "",  # name - нет в DTO, оставляем пустым
                _fmt_decimal(requested_value),
                _cell(requested_unit),
                _fmt_quantity(pack_size_value, pack_size_unit),
                str(packs),
                str(min_packs),
                _cell(_get_reason_str(line)),
                _cell(catalog_aisle),
                _fmt_decimal(catalog_price_value),
                _fmt_decimal(subtotal_value),
                _cell(catalog_store_id),
                _cell(final_region_id),
            ]
        )

    return buf.getvalue()
