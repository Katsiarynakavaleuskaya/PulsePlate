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
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)
from app.services.shoplist_export import pdf_export
from tests.vip._reportlab_lazy import make_lazy_reportlab_mock
from tests.vip.helpers import qty


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
        requested=qty("600"),
        pack_size=qty("500"),
        packs=2,
        provided=qty("1000"),
        overage=qty("400"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=600 G", "provided=1000 G"],
        catalog=catalog,
    )
    unpacked = UnpackedLineDTO(food_id="tomato", requested=qty("200"))

    response = ShoplistGenerateResponse(packed=[packed], unpacked=[unpacked])

    data = pdf_export.export_shoplist_to_pdf(response)
    assert data.startswith(b"%PDF")

    assert pdf_export._fmt_decimal(None) == ""
    assert pdf_export._fmt_quantity(None, "G") == ""
    assert "requested=600 G" in pdf_export._get_reason_str(packed)
    assert pdf_export._sort_key(packed)[1] == "store-1"


def test_export_shoplist_to_pdf_wraps_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that exceptions in PDF generation are wrapped as RuntimeError."""

    class _BoomDoc:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def build(self, _elements: object) -> None:
            raise ValueError("boom")

    # Monkeypatch _lazy_reportlab to return _BoomDoc instead of SimpleDocTemplate
    real_lazy = pdf_export._lazy_reportlab
    monkeypatch.setattr(
        pdf_export,
        "_lazy_reportlab",
        make_lazy_reportlab_mock(real_lazy, simple_doc_template=_BoomDoc),
    )

    response = ShoplistGenerateResponse(
        packed=[],
        unpacked=[UnpackedLineDTO(food_id="carrot", requested=qty("100"))],
    )

    with pytest.raises(RuntimeError, match=r"PDF generation failed"):
        pdf_export.export_shoplist_to_pdf(response)


def test_export_shoplist_to_pdf_covers_first_catalog_scan_filter_branches() -> None:
    """
    Cover the `next((line.catalog for line in ... if line.catalog), None)` scan in
    `export_shoplist_to_pdf` so branch coverage sees both filter outcomes:
    - at least one line with `catalog is None` (filter False)
    - at least one line with a catalog (filter True)
    """
    catalog = CatalogInfoDTO(
        sku="SKU-1",
        store_id="store-1",
        region_id="region-1",
        aisle="Aisle-1",
        price=MoneyDTO(value=Decimal("1.50"), currency=CurrencyDTO.EUR),
    )

    packed_no_catalog = PackedLineDTO(
        food_id="no-catalog-first",
        requested=qty("100"),
        pack_size=qty("100"),
        packs=1,
        provided=qty("100"),
        overage=qty("0"),
        rounding="CEIL",
        min_packs=1,
        reasons=[],
        catalog=None,
    )
    packed_with_catalog = PackedLineDTO(
        food_id="with-catalog-second",
        requested=qty("200"),
        pack_size=qty("100"),
        packs=2,
        provided=qty("200"),
        overage=qty("0"),
        rounding="CEIL",
        min_packs=1,
        reasons=["requested=200 G"],
        catalog=catalog,
    )

    response = ShoplistGenerateResponse(
        packed=[packed_no_catalog, packed_with_catalog], unpacked=[]
    )

    data = pdf_export.export_shoplist_to_pdf(response)
    assert data.startswith(b"%PDF")
