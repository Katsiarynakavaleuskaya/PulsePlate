# -*- coding: utf-8 -*-
"""
Diff-coverage tests for PDF export (VIP shoplist).

These tests target specific lines that diff-cover reports as missing in:
- app/services/shoplist_export/pdf_export.py
"""

from __future__ import annotations

from decimal import Decimal

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


def test_export_shoplist_to_pdf_covers_packed_metadata_and_totals() -> None:
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

    data = pdf_export.export_shoplist_to_pdf(response)
    assert data.startswith(b"%PDF")

    assert pdf_export._fmt_decimal(None) == ""
    assert pdf_export._fmt_quantity(None, "G") == ""
    assert "requested=600 G" in pdf_export._get_reason_str(packed)
    assert pdf_export._sort_key(packed)[1] == "store-1"


def test_export_shoplist_to_pdf_wraps_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BoomDoc:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def build(self, _elements: object) -> None:
            raise ValueError("boom")

    monkeypatch.setattr(pdf_export, "SimpleDocTemplate", _BoomDoc)

    response = ShoplistGenerateResponse(
        packed=[],
        unpacked=[UnpackedLineDTO(food_id="carrot", requested=_qty("100"))],
    )

    with pytest.raises(RuntimeError, match=r"PDF generation failed"):
        pdf_export.export_shoplist_to_pdf(response)
