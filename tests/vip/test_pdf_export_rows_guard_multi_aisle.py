# -*- coding: utf-8 -*-
"""
RU: Guard-тест на multi-aisle структуру PDF rows (без reportlab).
EN: Guard test for multi-aisle structure (no reportlab).

Locks:
- store header once
- aisle header for each aisle
- subtotal after each aisle block
- grand total equals sum of aisle subtotals
- deterministic output
"""

from __future__ import annotations

from decimal import Decimal

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    QuantityDTO,
    ShoplistGenerateResponse,
    UnitDTO,
)
from app.services.shoplist_export import pdf_export


def _qty(value: str, unit: UnitDTO = "G") -> QuantityDTO:
    return QuantityDTO(value=Decimal(value), unit=unit)


def _packed(
    *,
    food_id: str,
    aisle: str,
    price: str,
    packs: int,
    store_id: str = "store-1",
    region_id: str = "region-1",
) -> PackedLineDTO:
    catalog = CatalogInfoDTO(
        sku=f"SKU-{food_id}",
        store_id=store_id,
        region_id=region_id,
        aisle=aisle,
        price=MoneyDTO(value=Decimal(price), currency=CurrencyDTO.EUR),
    )
    return PackedLineDTO(
        food_id=food_id,
        requested=_qty("600"),
        pack_size=_qty("500"),
        packs=packs,
        provided=_qty(str(500 * packs)),
        overage=_qty(str(500 * packs - 600)),
        rounding="CEIL",
        min_packs=1,
        reasons=[f"packs={packs}"],
        catalog=catalog,
    )


def test_build_pdf_rows_multi_aisle_flushes_subtotals_and_total() -> None:
    """Test that multiple aisles in one store each get their own subtotal, and grand total is correct."""
    # Aisle-1: carrot subtotal = 1.50 * 2 = 3.00 EUR
    # Aisle-2: bread subtotal  = 2.00 * 1 = 2.00 EUR
    packed1 = _packed(food_id="carrot", aisle="Aisle-1", price="1.50", packs=2)
    packed2 = _packed(food_id="bread", aisle="Aisle-2", price="2.00", packs=1)

    response = ShoplistGenerateResponse(packed=[packed1, packed2], unpacked=[])

    rows = pdf_export.build_pdf_rows(response)

    # Determinism: second call identical
    rows2 = pdf_export.build_pdf_rows(response)
    assert [(r.row_type, r.cells) for r in rows] == [(r.row_type, r.cells) for r in rows2]

    # One store header
    store_rows = [r for r in rows if r.row_type == pdf_export.PdfRowType.STORE]
    assert len(store_rows) == 1

    # Two aisle headers (Aisle-1 and Aisle-2)
    aisle_rows = [r for r in rows if r.row_type == pdf_export.PdfRowType.AISLE]
    assert len(aisle_rows) == 2
    assert any("Aisle-1" in r.cells[0] for r in aisle_rows)
    assert any("Aisle-2" in r.cells[0] for r in aisle_rows)

    # Two subtotals (one per aisle)
    subtotal_rows = [r for r in rows if r.row_type == pdf_export.PdfRowType.SUBTOTAL]
    assert len(subtotal_rows) == 2
    # Subtotal format: "Subtotal (Aisle-1):"
    assert all(r.cells[4].startswith("Subtotal (") for r in subtotal_rows)

    # The subtotal values should include both aisle totals (order matters: Aisle-1 then Aisle-2)
    subtotal_values = [r.cells[6] for r in subtotal_rows]
    assert subtotal_values == ["3.00 EUR", "2.00 EUR"]

    # Grand total must be 5.00 EUR
    total_row = next(r for r in rows if r.row_type == pdf_export.PdfRowType.GRAND_TOTAL)
    assert total_row.cells[4] == "Total"
    assert total_row.cells[6] == "5.00 EUR"

    # Structural order check: Aisle-1 items are before first subtotal; Aisle-2 items before second subtotal
    idx_aisle1 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.AISLE and "Aisle-1" in r.cells[0]
    )
    idx_sub1 = next(i for i, r in enumerate(rows) if r.row_type == pdf_export.PdfRowType.SUBTOTAL)
    idx_aisle2 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.AISLE and "Aisle-2" in r.cells[0]
    )
    idx_sub2 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.SUBTOTAL and i > idx_sub1
    )

    # Items in each aisle sit between its header and subtotal
    idx_item_carrot = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.ITEM and r.cells[0] == "carrot"
    )
    idx_item_bread = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.ITEM and r.cells[0] == "bread"
    )

    assert idx_aisle1 < idx_item_carrot < idx_sub1 < idx_aisle2
    assert idx_aisle2 < idx_item_bread < idx_sub2


def test_build_pdf_rows_store_change_flushes_previous_aisle() -> None:
    """Test that store change flushes previous aisle subtotal (not just aisle change)."""
    # Store-1, Aisle-1: carrot subtotal = 1.50 * 2 = 3.00 EUR
    # Store-2, Aisle-1: bread subtotal  = 2.00 * 1 = 2.00 EUR
    packed1 = _packed(food_id="carrot", aisle="Aisle-1", price="1.50", packs=2, store_id="store-1")
    packed2 = _packed(food_id="bread", aisle="Aisle-1", price="2.00", packs=1, store_id="store-2")

    response = ShoplistGenerateResponse(packed=[packed1, packed2], unpacked=[])

    rows = pdf_export.build_pdf_rows(response)

    # Two store headers
    store_rows = [r for r in rows if r.row_type == pdf_export.PdfRowType.STORE]
    assert len(store_rows) == 2
    assert any("store-1" in r.cells[0] for r in store_rows)
    assert any("store-2" in r.cells[0] for r in store_rows)

    # Two aisle headers (both Aisle-1, but different stores)
    aisle_rows = [r for r in rows if r.row_type == pdf_export.PdfRowType.AISLE]
    assert len(aisle_rows) == 2
    assert all("Aisle-1" in r.cells[0] for r in aisle_rows)

    # Two subtotals (one per store/aisle combination)
    subtotal_rows = [r for r in rows if r.row_type == pdf_export.PdfRowType.SUBTOTAL]
    assert len(subtotal_rows) == 2

    # Grand total must be 5.00 EUR (3.00 + 2.00)
    total_row = next(r for r in rows if r.row_type == pdf_export.PdfRowType.GRAND_TOTAL)
    assert total_row.cells[6] == "5.00 EUR"

    # Structural order: Store-1 → Aisle-1 → item → subtotal → Store-2 → Aisle-1 → item → subtotal → Total
    idx_store1 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.STORE and "store-1" in r.cells[0]
    )
    idx_aisle1_store1 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.AISLE and i > idx_store1 and "Aisle-1" in r.cells[0]
    )
    idx_sub1 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.SUBTOTAL and i > idx_aisle1_store1
    )
    idx_store2 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == pdf_export.PdfRowType.STORE and "store-2" in r.cells[0]
    )

    # Verify order: store-1 → aisle-1 → item → subtotal → store-2
    assert idx_store1 < idx_aisle1_store1 < idx_sub1 < idx_store2
