# -*- coding: utf-8 -*-
"""
RU: Guard-тест на структуру PDF rows (без reportlab).
EN: Guard test for PDF rows structure (no reportlab).

Purpose:
- lock store→aisle grouping order
- lock subtotal and grand total placement
- lock deterministic output
"""

from __future__ import annotations

from decimal import Decimal

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


def test_build_pdf_rows_structure_and_totals_are_deterministic() -> None:
    """Test that build_pdf_rows returns deterministic structure with correct totals."""
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

    rows1 = pdf_export.build_pdf_rows(response)
    rows2 = pdf_export.build_pdf_rows(response)

    # Deterministic: row types and cell strings match exactly
    assert [(r.row_type, r.cells) for r in rows1] == [(r.row_type, r.cells) for r in rows2]

    # Helper: find row indices by type
    idx_store = next(i for i, r in enumerate(rows1) if r.row_type == pdf_export.PdfRowType.STORE)
    idx_aisle = next(i for i, r in enumerate(rows1) if r.row_type == pdf_export.PdfRowType.AISLE)
    idx_subtotal = next(i for i, r in enumerate(rows1) if r.row_type == pdf_export.PdfRowType.SUBTOTAL)
    idx_total = next(i for i, r in enumerate(rows1) if r.row_type == pdf_export.PdfRowType.GRAND_TOTAL)

    # Structural order
    assert idx_store < idx_aisle < idx_subtotal < idx_total

    # Items must be between aisle header and subtotal
    item_indices = [i for i, r in enumerate(rows1) if r.row_type == pdf_export.PdfRowType.ITEM]
    assert item_indices, "Expected at least one ITEM row"
    assert all(idx_aisle < i < idx_subtotal for i in item_indices)

    # Validate presence of the item row for packed line
    packed_row = next(
        r for r in rows1 if r.row_type == pdf_export.PdfRowType.ITEM and r.cells[0] == "carrot"
    )
    # Columns: Food ID, Requested, Pack Size, Packs, Reason, Price, Subtotal
    assert packed_row.cells[0] == "carrot"
    assert packed_row.cells[3] == "2"
    assert packed_row.cells[5].endswith("EUR")  # price
    assert packed_row.cells[6].endswith("EUR")  # subtotal

    # Validate subtotal and grand total numeric equality via Money string
    # Subtotal for carrot: 1.50 * 2 = 3.00 EUR
    subtotal_row = rows1[idx_subtotal]
    total_row = rows1[idx_total]

    # Subtotal label format: "Subtotal (Aisle-1):"
    assert subtotal_row.cells[4].startswith("Subtotal (")
    assert subtotal_row.cells[4].endswith("):")
    assert subtotal_row.cells[6] == "3.00 EUR"

    assert total_row.cells[4] == "Total"
    assert total_row.cells[6] == "3.00 EUR"


def test_build_pdf_rows_multi_aisle_subtotals() -> None:
    """Test that multiple aisles in one store each get their own subtotal."""
    catalog1 = CatalogInfoDTO(
        sku="SKU-1",
        store_id="store-1",
        region_id="region-1",
        aisle="Aisle-A",
        price=MoneyDTO(value=Decimal("1.00"), currency=CurrencyDTO.EUR),
    )
    catalog2 = CatalogInfoDTO(
        sku="SKU-2",
        store_id="store-1",
        region_id="region-1",
        aisle="Aisle-B",
        price=MoneyDTO(value=Decimal("2.00"), currency=CurrencyDTO.EUR),
    )

    packed1 = PackedLineDTO(
        food_id="item-a",
        requested=_qty("100"),
        pack_size=_qty("100"),
        packs=1,
        provided=_qty("100"),
        overage=_qty("0"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=100 G"],
        catalog=catalog1,
    )
    packed2 = PackedLineDTO(
        food_id="item-b",
        requested=_qty("200"),
        pack_size=_qty("200"),
        packs=1,
        provided=_qty("200"),
        overage=_qty("0"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=200 G"],
        catalog=catalog2,
    )

    response = ShoplistGenerateResponse(packed=[packed1, packed2], unpacked=[])

    rows = pdf_export.build_pdf_rows(response)

    # Find indices
    store_indices = [i for i, r in enumerate(rows) if r.row_type == pdf_export.PdfRowType.STORE]
    aisle_indices = [i for i, r in enumerate(rows) if r.row_type == pdf_export.PdfRowType.AISLE]
    subtotal_indices = [i for i, r in enumerate(rows) if r.row_type == pdf_export.PdfRowType.SUBTOTAL]

    # One store, two aisles, two subtotals
    assert len(store_indices) == 1
    assert len(aisle_indices) == 2
    assert len(subtotal_indices) == 2

    # Order: STORE → AISLE-A → item-a → SUBTOTAL-A → AISLE-B → item-b → SUBTOTAL-B → GRAND_TOTAL
    assert store_indices[0] < aisle_indices[0] < subtotal_indices[0] < aisle_indices[1] < subtotal_indices[1]

    # Validate subtotals
    subtotal_a = rows[subtotal_indices[0]]
    subtotal_b = rows[subtotal_indices[1]]
    grand_total = next(r for r in rows if r.row_type == pdf_export.PdfRowType.GRAND_TOTAL)

    # Aisle-A subtotal: 1.00 * 1 = 1.00 EUR
    assert "Aisle-A" in subtotal_a.cells[4]
    assert subtotal_a.cells[6] == "1.00 EUR"

    # Aisle-B subtotal: 2.00 * 1 = 2.00 EUR
    assert "Aisle-B" in subtotal_b.cells[4]
    assert subtotal_b.cells[6] == "2.00 EUR"

    # Grand total: 1.00 + 2.00 = 3.00 EUR
    assert grand_total.cells[6] == "3.00 EUR"
