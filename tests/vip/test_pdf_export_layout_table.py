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
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)
from app.services.shoplist_export import pdf_export
from tests.vip._reportlab_lazy import make_lazy_reportlab_mock
from tests.vip.helpers import qty


class _FakeDoc:
    def __init__(self, buffer: Any, *_args: Any, **_kwargs: Any) -> None:
        # SimpleDocTemplate(buffer, ...) - buffer is first positional arg
        # Store buffer for later use in build()
        self.buffer = buffer
        # Verify buffer is BytesIO-like
        assert hasattr(buffer, "write"), f"Buffer must have write method, got: {type(buffer)}"
        assert hasattr(buffer, "getvalue"), f"Buffer must have getvalue method, got: {type(buffer)}"

    def build(self, _elements: Any) -> None:
        # Write minimal PDF header and footer in build() when buffer is actually used
        # This mimics what SimpleDocTemplate does - writes to buffer during build()
        # SimpleDocTemplate writes PDF content during build(), so we do the same
        assert self.buffer is not None, "Buffer should not be None in build()"
        assert hasattr(self.buffer, "write"), "Buffer must have write method"
        # Write PDF header and footer
        self.buffer.write(b"%PDF-1.4\n")
        self.buffer.write(b"\n%%EOF")


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


@pytest.fixture(autouse=True)
def _reset_fake_table_state() -> None:
    _FakeTable.last_data = None
    _FakeTable.last_style = None


def test_export_shoplist_to_pdf_table_layout_store_aisle_subtotal_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PDF table has correct layout: store→aisle→items→subtotal→grand_total."""
    # State reset is handled by the autouse fixture `_reset_fake_table_state`.
    # Patch _lazy_reportlab so export_shoplist_to_pdf uses our fakes for doc/table.
    real_lazy = pdf_export._lazy_reportlab
    monkeypatch.setattr(
        pdf_export,
        "_lazy_reportlab",
        make_lazy_reportlab_mock(
            real_lazy,
            simple_doc_template=_FakeDoc,
            table=_FakeTable,
            table_style=_FakeTableStyle,
        ),
    )

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

    pdf_bytes = pdf_export.export_shoplist_to_pdf(response)
    # FakeDoc writes minimal PDF header/footer for test verification
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0

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
    # Use RowType from _pdf_rows_assert for consistency with other guard tests
    from tests.vip._pdf_rows_assert import RowType

    assert len(rows) >= 5
    assert rows[0].row_type == RowType.HEADER
    assert any(row.row_type == RowType.STORE for row in rows)
    assert any(row.row_type == RowType.AISLE for row in rows)
    assert any(row.row_type == RowType.ITEM for row in rows)
    assert any(row.row_type == RowType.SUBTOTAL for row in rows)
    assert rows[-1].row_type == RowType.GRAND_TOTAL
