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

    # Two store headers
    stores = [r for r in rows if r.row_type == pdf_export.PdfRowType.STORE]
    assert len(stores) == 2

    # Two subtotals (store change forces flush)
    subtotals = [r for r in rows if r.row_type == pdf_export.PdfRowType.SUBTOTAL]
    assert [r.cells[6] for r in subtotals] == ["3.00 EUR", "2.00 EUR"]

    # Grand total
    total = next(r for r in rows if r.row_type == pdf_export.PdfRowType.GRAND_TOTAL)
    assert total.cells[6] == "5.00 EUR"
