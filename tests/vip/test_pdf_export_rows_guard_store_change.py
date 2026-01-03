# -*- coding: utf-8 -*-
"""
Guard test for branch coverage:
- covers `if line.catalog` == True
- ensures subtotal is flushed on STORE change (not only aisle)
- deterministic, no reportlab
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
from tests.vip._pdf_rows_assert import (
    RowType,
    assert_contains_subsequence,
    assert_subtotals_and_total,
    find_item,
    find_rows,
    rows_sig,
)


def _qty(value: str, unit: UnitDTO = "G") -> QuantityDTO:
    return QuantityDTO(value=Decimal(value), unit=unit)


def _packed(
    food_id: str,
    store_id: str,
    aisle: str,
    price: str,
    packs: int,
) -> PackedLineDTO:
    catalog = CatalogInfoDTO(
        sku=f"SKU-{food_id}",
        store_id=store_id,
        region_id="region-1",
        aisle=aisle,
        price=MoneyDTO(value=Decimal(price), currency=CurrencyDTO.EUR),
    )
    return PackedLineDTO(
        food_id=food_id,
        requested=_qty("600"),
        pack_size=_qty("500"),
        packs=packs,
        provided=_qty(str(500 * packs)),
        overage=_qty(str(max(0, 500 * packs - 600))),
        rounding="CEIL",
        min_packs=1,
        reasons=["guard"],
        catalog=catalog,
    )


def test_build_pdf_rows_flushes_subtotal_on_store_change() -> None:
    """
    Covers:
    - branch where line.catalog is present
    - subtotal flush when store_id changes
    """
    a = _packed("carrot", "store-1", "A1", "1.50", 2)  # 3.00
    b = _packed("bread", "store-2", "A1", "2.00", 1)  # 2.00

    response = ShoplistGenerateResponse(packed=[a, b], unpacked=[])

    rows = pdf_export.build_pdf_rows(response)

    sig = rows_sig(rows)

    assert len(find_rows(rows, RowType.STORE)) == 2
    assert len(find_rows(rows, RowType.AISLE)) == 2
    assert len(find_rows(rows, RowType.SUBTOTAL)) == 2
    assert len(find_rows(rows, RowType.GRAND_TOTAL)) == 1

    # Order contract: STORE -> AISLE -> ITEM -> SUBTOTAL -> STORE -> AISLE -> ITEM -> SUBTOTAL -> GRAND_TOTAL
    assert_contains_subsequence(
        sig,
        [
            RowType.STORE.value,
            RowType.AISLE.value,
            RowType.ITEM.value,
            RowType.SUBTOTAL.value,
            RowType.STORE.value,
            RowType.AISLE.value,
            RowType.ITEM.value,
            RowType.SUBTOTAL.value,
            RowType.GRAND_TOTAL.value,
        ],
    )

    carrot = find_item(rows, "carrot")
    assert carrot.cells[6] == "3.00 EUR"
    bread = find_item(rows, "bread")
    assert bread.cells[6] == "2.00 EUR"

    assert_subtotals_and_total(rows, subtotals=["3.00 EUR", "2.00 EUR"], total="5.00 EUR")
