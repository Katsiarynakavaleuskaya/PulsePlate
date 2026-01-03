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
from tests.vip._pdf_rows_assert import (
    RowType,
    assert_contains_subsequence,
    assert_subtotals_and_total,
    find_item,
    find_rows,
    money_cell,
    rows_sig,
)


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

    sig = rows_sig(rows1)

    # Counts (semantic)
    # Note: unpacked lines without catalog create a separate STORE row with empty store_id
    store_rows = find_rows(rows1, RowType.STORE)
    assert len(store_rows) >= 1  # At least one store (packed line), possibly more (unpacked lines)
    # Verify we have the expected store for packed line
    assert any("store-1" in r.cells[0] for r in store_rows)

    assert len(find_rows(rows1, RowType.AISLE)) >= 1
    assert len(find_rows(rows1, RowType.ITEM)) >= 1
    assert len(find_rows(rows1, RowType.SUBTOTAL)) >= 1
    assert len(find_rows(rows1, RowType.GRAND_TOTAL)) == 1

    # Contract: STORE -> AISLE -> ITEM -> SUBTOTAL -> GRAND_TOTAL
    assert_contains_subsequence(
        sig,
        [
            RowType.STORE.value,
            RowType.AISLE.value,
            RowType.ITEM.value,
            RowType.SUBTOTAL.value,
            RowType.GRAND_TOTAL.value,
        ],
    )

    # Validate presence of the item row for packed line
    packed_row = find_item(rows1, "carrot")
    # Columns: Food ID, Requested, Pack Size, Packs, Reason, Price, Subtotal
    assert packed_row.cells[0] == "carrot"
    assert packed_row.cells[3] == "2"
    assert packed_row.cells[5].endswith("EUR")  # price
    # Use money_cell() for semantic access to subtotal column
    assert money_cell(packed_row).endswith("EUR")  # subtotal

    # Validate subtotal and grand total numeric equality via Money string
    # Subtotal for carrot: 1.50 * 2 = 3.00 EUR
    assert_subtotals_and_total(rows1, subtotals=["3.00 EUR"], total="3.00 EUR")


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

    sig = rows_sig(rows)

    # Counts (semantic)
    assert len(find_rows(rows, RowType.STORE)) == 1
    assert len(find_rows(rows, RowType.AISLE)) == 2
    assert len(find_rows(rows, RowType.ITEM)) == 2
    assert len(find_rows(rows, RowType.SUBTOTAL)) == 2
    assert len(find_rows(rows, RowType.GRAND_TOTAL)) == 1

    # Order contract: STORE -> AISLE -> ITEM -> SUBTOTAL -> AISLE -> ITEM -> SUBTOTAL -> GRAND_TOTAL
    assert_contains_subsequence(
        sig,
        [
            RowType.STORE.value,
            RowType.AISLE.value,
            RowType.ITEM.value,
            RowType.SUBTOTAL.value,
            RowType.AISLE.value,
            RowType.ITEM.value,
            RowType.SUBTOTAL.value,
            RowType.GRAND_TOTAL.value,
        ],
    )

    # Item-level checks (ensures correct row association independent of order)
    row_a = find_item(rows, "item-a")
    row_b = find_item(rows, "item-b")
    assert money_cell(row_a) == "1.00 EUR"  # line subtotal
    assert money_cell(row_b) == "2.00 EUR"

    # Subtotals should be exactly per-aisle, in deterministic order
    # (Aisle-A subtotal then Aisle-B subtotal)
    subtotal_rows = find_rows(rows, RowType.SUBTOTAL)
    assert len(subtotal_rows) == 2
    assert "Aisle-A" in subtotal_rows[0].cells[4]
    assert money_cell(subtotal_rows[0]) == "1.00 EUR"
    assert "Aisle-B" in subtotal_rows[1].cells[4]
    assert money_cell(subtotal_rows[1]) == "2.00 EUR"

    # Grand total: 1.00 + 2.00 = 3.00 EUR
    assert_subtotals_and_total(rows, subtotals=["1.00 EUR", "2.00 EUR"], total="3.00 EUR")
