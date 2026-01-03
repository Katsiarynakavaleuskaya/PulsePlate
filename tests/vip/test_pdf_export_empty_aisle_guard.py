# -*- coding: utf-8 -*-
"""
Guard test: empty aisle should not generate duplicate "Aisle: —" headers.

RU: Гард-тест: пустой aisle не должен генерировать повторяющиеся заголовки "Aisle: —".
EN: Guard test: empty aisle should not generate duplicate "Aisle: —" headers.
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
from tests.vip._pdf_rows_assert import RowType, find_rows


def _qty(value: str, unit: UnitDTO = "G") -> QuantityDTO:
    return QuantityDTO(value=Decimal(value), unit=unit)


def test_build_pdf_rows_does_not_repeat_empty_aisle_headers() -> None:
    """
    Test that multiple lines with empty aisle generate only one "Aisle: —" header per store.
    """
    catalog_no_aisle = CatalogInfoDTO(
        sku="SKU-1",
        store_id="store-1",
        region_id="region-1",
        aisle="",  # empty aisle
        price=MoneyDTO(value=Decimal("1.00"), currency=CurrencyDTO.EUR),
    )

    packed1 = PackedLineDTO(
        food_id="x",
        requested=_qty("100"),
        pack_size=_qty("100"),
        packs=1,
        provided=_qty("100"),
        overage=_qty("0"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=100 G"],
        catalog=catalog_no_aisle,
    )
    packed2 = PackedLineDTO(
        food_id="y",
        requested=_qty("100"),
        pack_size=_qty("100"),
        packs=1,
        provided=_qty("100"),
        overage=_qty("0"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=100 G"],
        catalog=catalog_no_aisle,
    )

    rows = pdf_export.build_pdf_rows(
        ShoplistGenerateResponse(packed=[packed1, packed2], unpacked=[])
    )

    aisle_rows = find_rows(rows, RowType.AISLE)
    # Expect only one "Aisle: —" header in this store section
    labels = [r.cells[0] for r in aisle_rows]
    assert labels.count("Aisle: —") == 1, f"Expected exactly one 'Aisle: —' header, got: {labels}"
