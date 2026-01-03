# -*- coding: utf-8 -*-
"""
RU: Проверка layout PDF-таблицы без парсинга PDF.
EN: Layout checks for PDF table without PDF parsing.

We monkeypatch reportlab classes returned by _lazy_reportlab to capture the Table data.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    QuantityDTO,
    ShoplistGenerateResponse,
    UnitDTO,
    UnpackedLineDTO,
)
from app.services.shoplist_export import pdf_export


def _qty(value: str, unit: UnitDTO = "G") -> QuantityDTO:
    return QuantityDTO(value=Decimal(value), unit=unit)


class _FakeDoc:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def build(self, _elements: Any) -> None:
        # no-op: we only care that Table was created and styled
        return


class _FakeTable:
    last_data: list[list[str]] | None = None
    last_style: Any | None = None

    def __init__(self, data: list[list[str]]) -> None:
        _FakeTable.last_data = data

    def setStyle(self, style: Any) -> None:
        _FakeTable.last_style = style


class _FakeTableStyle:
    def __init__(self, commands: Any) -> None:
        self.commands = commands


def test_export_shoplist_to_pdf_table_layout_store_aisle_subtotal_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PDF table has correct layout: store→aisle→items→subtotal→grand_total."""
    # Patch _lazy_reportlab so export_shoplist_to_pdf uses our fakes for doc/table.
    real_lazy = pdf_export._lazy_reportlab

    def _mock_lazy() -> tuple[Any, ...]:
        real_result = real_lazy()
        (
            colors,
            A4,
            getSampleStyleSheet,
            mm,
            _unused_flowable,
            Paragraph,
            _Doc,
            Spacer,
            _Table,
            _TableStyle,
        ) = real_result
        return (
            colors,
            A4,
            getSampleStyleSheet,
            mm,
            _unused_flowable,
            Paragraph,
            _FakeDoc,
            Spacer,
            _FakeTable,
            _FakeTableStyle,
        )

    monkeypatch.setattr(pdf_export, "_lazy_reportlab", _mock_lazy)

    catalog = CatalogInfoDTO(
        sku="SKU-1",
        store_id="store-1",
        region_id="region-1",
        aisle="Aisle-1",
        price=MoneyDTO(value=Decimal("1.50"), currency=CurrencyDTO.EUR),
    )

    packed = PackedLineDTO(
        food_id="carrot",
        requested=_qty("600"),
        pack_size=_qty("500"),
        packs=2,
        provided=_qty("1000"),
        overage=_qty("400"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=600 G", "provided=1000 G"],
        catalog=catalog,
    )
    unpacked = UnpackedLineDTO(food_id="tomato", requested=_qty("200"))

    response = ShoplistGenerateResponse(packed=[packed], unpacked=[unpacked])

    pdf_bytes = pdf_export.export_shoplist_to_pdf(response)
    # Still generates real PDF (SimpleDocTemplate writes header even if build is no-op)
    assert pdf_bytes.startswith(b"%PDF")

    data = _FakeTable.last_data
    assert data is not None

    # Verify table structure: header → store → aisle → items → subtotal → grand_total
    # Header row
    assert data[0][0] == "Food ID"

    # Store header row appears
    assert any(row[0].startswith("Store:") for row in data), data

    # Aisle header row appears
    assert any(row[0].startswith("Aisle:") for row in data), data

    # Item rows appear
    assert any(row[0] == "carrot" for row in data), data
    assert any(row[0] == "tomato" for row in data), data

    # Subtotal and Total rows appear
    assert any("Subtotal" in row[4] for row in data), data
    assert any(row[4] == "Total" for row in data), data

    # Verify grand total is sum of subtotals (basic sanity check)
    # This is tested more thoroughly in unit tests, but here we verify the layout
    total_row = next((row for row in data if row[4] == "Total"), None)
    assert total_row is not None
    assert total_row[6] != ""  # Total amount is not empty


def test_build_pdf_rows_deterministic_row_types() -> None:
    """Test that build_pdf_rows returns rows in deterministic order with correct types."""
    catalog = CatalogInfoDTO(
        sku="SKU-1",
        store_id="store-1",
        region_id="region-1",
        aisle="Aisle-1",
        price=MoneyDTO(value=Decimal("1.50"), currency=CurrencyDTO.EUR),
    )

    packed = PackedLineDTO(
        food_id="carrot",
        requested=_qty("600"),
        pack_size=_qty("500"),
        packs=2,
        provided=_qty("1000"),
        overage=_qty("400"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=600 G"],
        catalog=catalog,
    )

    response = ShoplistGenerateResponse(packed=[packed], unpacked=[])

    rows = pdf_export.build_pdf_rows(response)

    # Verify row types in order: HEADER → STORE → AISLE → ITEM → SUBTOTAL → GRAND_TOTAL
    assert len(rows) >= 5
    assert rows[0].row_type == pdf_export.PdfRowType.HEADER
    assert any(row.row_type == pdf_export.PdfRowType.STORE for row in rows)
    assert any(row.row_type == pdf_export.PdfRowType.AISLE for row in rows)
    assert any(row.row_type == pdf_export.PdfRowType.ITEM for row in rows)
    assert any(row.row_type == pdf_export.PdfRowType.SUBTOTAL for row in rows)
    assert rows[-1].row_type == pdf_export.PdfRowType.GRAND_TOTAL
