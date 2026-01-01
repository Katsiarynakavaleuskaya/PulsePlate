# -*- coding: utf-8 -*-
"""
Unit tests for CSV export functions.

RU: Unit-тесты для функций CSV экспорта.
EN: Unit tests for CSV export functions.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal

import pytest

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    QuantityDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)
from app.services.shoplist_export.csv_export import (
    _cell,
    _fmt_decimal,
    _fmt_quantity,
    _get_reason_str,
    _sanitize_csv_cell,
    export_shoplist_to_csv,
)


class TestSanitizeCSVCell:
    """Tests for _sanitize_csv_cell function."""

    def test_sanitize_equals_prefix(self) -> None:
        """Test that = prefix is escaped."""
        assert _sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"

    def test_sanitize_plus_prefix(self) -> None:
        """Test that + prefix is escaped."""
        assert _sanitize_csv_cell("+123") == "'+123"

    def test_sanitize_minus_prefix(self) -> None:
        """Test that - prefix is escaped."""
        assert _sanitize_csv_cell("-456") == "'-456"

    def test_sanitize_at_prefix(self) -> None:
        """Test that @ prefix is escaped."""
        assert _sanitize_csv_cell("@evil") == "'@evil"

    def test_sanitize_normal_string(self) -> None:
        """Test that normal strings are not escaped."""
        assert _sanitize_csv_cell("carrot") == "carrot"
        assert _sanitize_csv_cell("normal text") == "normal text"

    def test_sanitize_empty_string(self) -> None:
        """Test that empty string is not escaped."""
        assert _sanitize_csv_cell("") == ""


class TestCell:
    """Tests for _cell helper function."""

    def test_cell_with_value(self) -> None:
        """Test _cell with non-empty value."""
        assert _cell("test") == "test"

    def test_cell_with_dangerous_prefix(self) -> None:
        """Test _cell with dangerous prefix."""
        assert _cell("=SUM(1,1)") == "'=SUM(1,1)"

    def test_cell_with_none(self) -> None:
        """Test _cell with None."""
        assert _cell(None) == ""

    def test_cell_with_empty_string(self) -> None:
        """Test _cell with empty string."""
        assert _cell("") == ""


class TestFmtDecimal:
    """Tests for _fmt_decimal function."""

    def test_fmt_decimal_with_value(self) -> None:
        """Test formatting Decimal value."""
        assert _fmt_decimal(Decimal("123.45")) == "123.45"
        assert _fmt_decimal(Decimal("0")) == "0"
        assert _fmt_decimal(Decimal("1000")) == "1000"

    def test_fmt_decimal_with_none(self) -> None:
        """Test formatting None."""
        assert _fmt_decimal(None) == ""


class TestFmtQuantity:
    """Tests for _fmt_quantity function."""

    def test_fmt_quantity_with_value_and_unit(self) -> None:
        """Test formatting quantity with value and unit."""
        assert _fmt_quantity(Decimal("500"), "G") == "500 G"
        assert _fmt_quantity(Decimal("1"), "KG") == "1 KG"

    def test_fmt_quantity_with_value_no_unit(self) -> None:
        """Test formatting quantity with value but no unit."""
        assert _fmt_quantity(Decimal("500"), None) == "500"
        assert _fmt_quantity(Decimal("500"), "") == "500"

    def test_fmt_quantity_with_none(self) -> None:
        """Test formatting None quantity."""
        assert _fmt_quantity(None, "G") == ""
        assert _fmt_quantity(None, None) == ""


class TestGetReasonStr:
    """Tests for _get_reason_str function."""

    def test_get_reason_str_packed_with_reasons(self) -> None:
        """Test getting reason string from PackedLineDTO with reasons."""
        line = PackedLineDTO(
            food_id="carrot",
            requested=QuantityDTO(value=Decimal("100"), unit="G"),
            pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
            packs=1,
            provided=QuantityDTO(value=Decimal("500"), unit="G"),
            overage=QuantityDTO(value=Decimal("400"), unit="G"),
            rounding="CEIL",
            min_packs=1,
            reasons=["rounding=CEIL", "min_packs=1"],
        )
        assert _get_reason_str(line) == "rounding=CEIL; min_packs=1"

    def test_get_reason_str_packed_without_reasons(self) -> None:
        """Test getting reason string from PackedLineDTO without reasons."""
        line = PackedLineDTO(
            food_id="carrot",
            requested=QuantityDTO(value=Decimal("100"), unit="G"),
            pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
            packs=1,
            provided=QuantityDTO(value=Decimal("500"), unit="G"),
            overage=QuantityDTO(value=Decimal("400"), unit="G"),
            rounding="CEIL",
            min_packs=1,
            reasons=[],
        )
        assert _get_reason_str(line) == ""

    def test_get_reason_str_unpacked_with_reason(self) -> None:
        """Test getting reason string from UnpackedLineDTO with reason."""
        line = UnpackedLineDTO(
            food_id="tomato",
            requested=QuantityDTO(value=Decimal("200"), unit="G"),
            reason="no_packaging_rule",
        )
        assert _get_reason_str(line) == "no_packaging_rule"

    def test_get_reason_str_unpacked_without_reason(self) -> None:
        """Test getting reason string from UnpackedLineDTO without reason."""
        line = UnpackedLineDTO(
            food_id="tomato",
            requested=QuantityDTO(value=Decimal("200"), unit="G"),
            reason="",
        )
        assert _get_reason_str(line) == ""


class TestExportShoplistToCSV:
    """Tests for export_shoplist_to_csv function."""

    def test_export_empty_response(self) -> None:
        """Test exporting empty shoplist response."""
        response = ShoplistGenerateResponse(packed=[], unpacked=[])
        csv_data = export_shoplist_to_csv(response)

        rows = list(csv.reader(io.StringIO(csv_data)))
        assert len(rows) == 1  # Only header
        assert rows[0] == [
            "food_id",
            "name",
            "requested",
            "unit",
            "pack_size",
            "packs",
            "min_packs",
            "reason",
            "aisle",
            "price",
            "subtotal",
            "store_id",
            "region_id",
        ]

    def test_export_packed_line_without_catalog(self) -> None:
        """Test exporting packed line without catalog."""
        response = ShoplistGenerateResponse(
            packed=[
                PackedLineDTO(
                    food_id="carrot",
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=1,
                    provided=QuantityDTO(value=Decimal("500"), unit="G"),
                    overage=QuantityDTO(value=Decimal("400"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=["min_packs=1"],
                )
            ],
            unpacked=[],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 2  # Header + 1 data row
        data_row = rows[1]
        assert data_row[0] == "carrot"  # food_id
        assert data_row[1] == ""  # name
        assert data_row[2] == "100"  # requested value
        assert data_row[3] == "G"  # requested unit
        assert data_row[4] == "500 G"  # pack_size
        assert data_row[5] == "1"  # packs
        assert data_row[6] == "1"  # min_packs
        assert data_row[7] == "min_packs=1"  # reason
        assert data_row[8] == ""  # aisle (no catalog)
        assert data_row[9] == ""  # price (no catalog)
        assert data_row[10] == ""  # subtotal (no price)
        assert data_row[11] == ""  # store_id (no catalog)
        assert data_row[12] == ""  # region_id (no catalog)

    def test_export_packed_line_with_catalog_and_price(self) -> None:
        """Test exporting packed line with catalog and price (subtotal calculation)."""
        catalog = CatalogInfoDTO(
            sku="SKU_TEST",
            store_id="carrefour_es",
            region_id="es",
            pack_label="500 G",
            aisle="Vegetables",
            price=MoneyDTO(value=Decimal("1.29"), currency=CurrencyDTO.EUR),
        )

        response = ShoplistGenerateResponse(
            packed=[
                PackedLineDTO(
                    food_id="carrot",
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=2,  # 2 packs for subtotal calculation
                    provided=QuantityDTO(value=Decimal("1000"), unit="G"),
                    overage=QuantityDTO(value=Decimal("900"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=["min_packs=1"],
                    catalog=catalog,
                )
            ],
            unpacked=[],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 2
        data_row = rows[1]
        assert data_row[8] == "Vegetables"  # aisle
        assert data_row[9] == "1.29"  # price
        assert data_row[10] == "2.58"  # subtotal (1.29 * 2)
        assert data_row[11] == "carrefour_es"  # store_id
        assert data_row[12] == "es"  # region_id

    def test_export_unpacked_line(self) -> None:
        """Test exporting unpacked line."""
        response = ShoplistGenerateResponse(
            packed=[],
            unpacked=[
                UnpackedLineDTO(
                    food_id="tomato",
                    requested=QuantityDTO(value=Decimal("200"), unit="G"),
                    reason="no_packaging_rule",
                )
            ],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 2
        data_row = rows[1]
        assert data_row[0] == "tomato"  # food_id
        assert data_row[4] == ""  # pack_size (unpacked)
        assert data_row[5] == "0"  # packs (unpacked)
        assert data_row[6] == "0"  # min_packs (unpacked)
        assert data_row[7] == "no_packaging_rule"  # reason

    def test_export_sorting_empty_values_last(self) -> None:
        """Test that sorting puts empty values last."""
        catalog_with_data = CatalogInfoDTO(
            sku="SKU_A",
            store_id="store_a",
            region_id="es",
            pack_label="500 G",
            aisle="Aisle A",
            price=None,
        )

        response = ShoplistGenerateResponse(
            packed=[
                # Line with empty catalog (should be last)
                PackedLineDTO(
                    food_id="z_empty",
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=1,
                    provided=QuantityDTO(value=Decimal("500"), unit="G"),
                    overage=QuantityDTO(value=Decimal("400"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=[],
                    catalog=None,  # Empty catalog
                ),
                # Line with catalog (should be first)
                PackedLineDTO(
                    food_id="a_with_catalog",
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=1,
                    provided=QuantityDTO(value=Decimal("500"), unit="G"),
                    overage=QuantityDTO(value=Decimal("400"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=[],
                    catalog=catalog_with_data,
                ),
            ],
            unpacked=[],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 3  # Header + 2 data rows
        # First row should have catalog (non-empty store_id)
        assert rows[1][0] == "a_with_catalog"
        # Second row should be empty catalog (empty store_id last)
        assert rows[2][0] == "z_empty"

    def test_export_with_dangerous_characters_in_food_id(self) -> None:
        """Test that dangerous characters in food_id are sanitized."""
        response = ShoplistGenerateResponse(
            packed=[
                PackedLineDTO(
                    food_id="=SUM(A1:A10)",  # Dangerous prefix
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=1,
                    provided=QuantityDTO(value=Decimal("500"), unit="G"),
                    overage=QuantityDTO(value=Decimal("400"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=[],
                )
            ],
            unpacked=[],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 2
        # food_id should be sanitized
        assert rows[1][0].startswith("'=")

    def test_export_with_catalog_empty_fields(self) -> None:
        """Test export with catalog that has empty store_id/aisle."""
        catalog_empty = CatalogInfoDTO(
            sku="SKU_TEST",
            store_id="",  # Empty store_id
            region_id="es",
            pack_label="500 G",
            aisle="",  # Empty aisle
            price=None,
        )

        response = ShoplistGenerateResponse(
            packed=[
                PackedLineDTO(
                    food_id="carrot",
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=1,
                    provided=QuantityDTO(value=Decimal("500"), unit="G"),
                    overage=QuantityDTO(value=Decimal("400"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=[],
                    catalog=catalog_empty,
                )
            ],
            unpacked=[],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 2
        data_row = rows[1]
        assert data_row[8] == ""  # aisle (empty)
        assert data_row[11] == ""  # store_id (empty)
        assert data_row[12] == "es"  # region_id (not empty)

    def test_export_packed_and_unpacked_mixed(self) -> None:
        """Test export with both packed and unpacked lines."""
        response = ShoplistGenerateResponse(
            packed=[
                PackedLineDTO(
                    food_id="carrot",
                    requested=QuantityDTO(value=Decimal("100"), unit="G"),
                    pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                    packs=1,
                    provided=QuantityDTO(value=Decimal("500"), unit="G"),
                    overage=QuantityDTO(value=Decimal("400"), unit="G"),
                    rounding="CEIL",
                    min_packs=1,
                    reasons=["min_packs=1"],
                )
            ],
            unpacked=[
                UnpackedLineDTO(
                    food_id="tomato",
                    requested=QuantityDTO(value=Decimal("200"), unit="G"),
                    reason="no_packaging_rule",
                )
            ],
        )

        csv_data = export_shoplist_to_csv(response)
        rows = list(csv.reader(io.StringIO(csv_data)))

        assert len(rows) == 3  # Header + 2 data rows
        # Both lines should be present
        food_ids = [row[0] for row in rows[1:]]
        assert "carrot" in food_ids
        assert "tomato" in food_ids
