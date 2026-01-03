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
    ShoplistGenerateResponse,
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
from tests.vip.helpers import qty


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
        requested=qty("600"),
        pack_size=qty("500"),
        packs=packs,
        provided=qty(str(500 * packs)),
        overage=qty(str(max(0, 500 * packs - 600))),
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

    sig = rows_sig(rows)

    # Counts (semantic)
    assert len(find_rows(rows, RowType.STORE)) == 1
    assert len(find_rows(rows, RowType.AISLE)) == 2
    assert len(find_rows(rows, RowType.SUBTOTAL)) == 2
    assert len(find_rows(rows, RowType.GRAND_TOTAL)) == 1

    aisle_rows = find_rows(rows, RowType.AISLE)
    assert any("Aisle-1" in (r.cells[0] if r.cells else "") for r in aisle_rows)
    assert any("Aisle-2" in (r.cells[0] if r.cells else "") for r in aisle_rows)

    # Order contract (no indices): STORE -> AISLE -> ITEM -> SUBTOTAL -> AISLE -> ITEM -> SUBTOTAL -> GRAND_TOTAL
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

    # Validate key item rows (semantic, no indices)
    carrot_row = find_item(rows, "carrot")
    assert carrot_row.cells[3] == "2"  # packs
    assert money_cell(carrot_row) == "3.00 EUR"  # subtotal

    bread_row = find_item(rows, "bread")
    assert bread_row.cells[3] == "1"  # packs
    assert money_cell(bread_row) == "2.00 EUR"  # subtotal

    # Subtotals & total
    assert_subtotals_and_total(rows, subtotals=["3.00 EUR", "2.00 EUR"], total="5.00 EUR")


def test_build_pdf_rows_store_change_flushes_previous_aisle() -> None:
    """Test that store change flushes previous aisle subtotal (not just aisle change)."""
    # Store-1, Aisle-1: carrot subtotal = 1.50 * 2 = 3.00 EUR
    # Store-2, Aisle-1: bread subtotal  = 2.00 * 1 = 2.00 EUR
    packed1 = _packed(food_id="carrot", aisle="Aisle-1", price="1.50", packs=2, store_id="store-1")
    packed2 = _packed(food_id="bread", aisle="Aisle-1", price="2.00", packs=1, store_id="store-2")

    response = ShoplistGenerateResponse(packed=[packed1, packed2], unpacked=[])

    rows = pdf_export.build_pdf_rows(response)

    # Two store headers
    store_rows = [r for r in rows if r.row_type == RowType.STORE]
    assert len(store_rows) == 2
    assert any("store-1" in r.cells[0] for r in store_rows)
    assert any("store-2" in r.cells[0] for r in store_rows)

    # Two aisle headers (both Aisle-1, but different stores)
    aisle_rows = [r for r in rows if r.row_type == RowType.AISLE]
    assert len(aisle_rows) == 2
    assert all("Aisle-1" in r.cells[0] for r in aisle_rows)

    # Two subtotals (one per store/aisle combination)
    subtotal_rows = find_rows(rows, RowType.SUBTOTAL)
    assert len(subtotal_rows) == 2

    # Grand total must be 5.00 EUR (3.00 + 2.00)
    total_rows = find_rows(rows, RowType.GRAND_TOTAL)
    assert len(total_rows) == 1
    assert money_cell(total_rows[0]) == "5.00 EUR"

    # Structural order: Store-1 → Aisle-1 → item → subtotal → Store-2 → Aisle-1 → item → subtotal → Total
    # Use semantic helpers instead of index-based checks
    idx_store1 = next(
        i for i, r in enumerate(rows) if r.row_type == RowType.STORE and "store-1" in r.cells[0]
    )
    idx_aisle1_store1 = next(
        i
        for i, r in enumerate(rows)
        if r.row_type == RowType.AISLE and i > idx_store1 and "Aisle-1" in r.cells[0]
    )
    idx_sub1 = next(
        i for i, r in enumerate(rows) if r.row_type == RowType.SUBTOTAL and i > idx_aisle1_store1
    )
    idx_store2 = next(
        i for i, r in enumerate(rows) if r.row_type == RowType.STORE and "store-2" in r.cells[0]
    )

    # Verify order: store-1 → aisle-1 → item → subtotal → store-2
    assert idx_store1 < idx_aisle1_store1 < idx_sub1 < idx_store2
