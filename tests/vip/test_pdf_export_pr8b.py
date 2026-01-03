# -*- coding: utf-8 -*-
"""
Tests for PR-8b: PDF export improvements (deterministic rows + product layout).

RU: Тесты для PR-8b: улучшения PDF экспорта (детерминированные строки + product layout).
EN: Tests for PR-8b: PDF export improvements (deterministic rows + product layout).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)
from app.services.shoplist_export import pdf_export
from tests.vip.helpers import qty


class TestBuildPdfLinesDeterministic:
    """Test deterministic ordering in build_pdf_lines."""

    def test_deterministic_ordering_store_aisle_food_id(self) -> None:
        """Test that build_pdf_lines returns consistent order: store_id, aisle, food_id."""
        catalog1 = CatalogInfoDTO(
            sku="SKU-1",
            store_id="store-b",
            region_id="region-1",
            aisle="Aisle-Z",
            price=MoneyDTO(value=Decimal("1.50"), currency=CurrencyDTO.EUR),
        )
        catalog2 = CatalogInfoDTO(
            sku="SKU-2",
            store_id="store-a",
            region_id="region-1",
            aisle="Aisle-A",
            price=MoneyDTO(value=Decimal("2.00"), currency=CurrencyDTO.EUR),
        )
        catalog3 = CatalogInfoDTO(
            sku="SKU-3",
            store_id="store-a",
            region_id="region-1",
            aisle="Aisle-A",
            price=MoneyDTO(value=Decimal("1.00"), currency=CurrencyDTO.EUR),
        )

        packed1 = PackedLineDTO(
            food_id="carrot-z",
            requested=qty("600"),
            pack_size=qty("500"),
            packs=2,
            provided=qty("1000"),
            overage=qty("400"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=600 G"],
            catalog=catalog1,
        )
        packed2 = PackedLineDTO(
            food_id="apple-a",
            requested=qty("200"),
            pack_size=qty("100"),
            packs=2,
            provided=qty("200"),
            overage=qty("0"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=200 G"],
            catalog=catalog2,
        )
        packed3 = PackedLineDTO(
            food_id="banana-a",
            requested=qty("300"),
            pack_size=qty("200"),
            packs=2,
            provided=qty("400"),
            overage=qty("100"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=300 G"],
            catalog=catalog3,
        )

        response = ShoplistGenerateResponse(packed=[packed1, packed2, packed3], unpacked=[])

        lines = pdf_export.build_pdf_lines(response)

        # Expected order: store-a (before store-b), Aisle-A (before Aisle-Z), apple-a (before banana-a)
        assert len(lines) == 3
        assert lines[0].food_id == "apple-a"  # store-a, Aisle-A, apple-a
        assert lines[0].store_id == "store-a"
        assert lines[0].aisle == "Aisle-A"
        assert lines[1].food_id == "banana-a"  # store-a, Aisle-A, banana-a
        assert lines[1].store_id == "store-a"
        assert lines[1].aisle == "Aisle-A"
        assert lines[2].food_id == "carrot-z"  # store-b, Aisle-Z, carrot-z
        assert lines[2].store_id == "store-b"
        assert lines[2].aisle == "Aisle-Z"

    def test_deterministic_ordering_empty_store_aisle_last(self) -> None:
        """Test that empty store_id/aisle come last."""
        catalog1 = CatalogInfoDTO(
            sku="SKU-1",
            store_id="store-a",
            region_id="region-1",
            aisle="Aisle-A",
            price=MoneyDTO(value=Decimal("1.50"), currency=CurrencyDTO.EUR),
        )

        packed1 = PackedLineDTO(
            food_id="with-catalog",
            requested=qty("100"),
            pack_size=qty("100"),
            packs=1,
            provided=qty("100"),
            overage=qty("0"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=100 G"],
            catalog=catalog1,
        )
        unpacked1 = UnpackedLineDTO(food_id="no-catalog", requested=qty("200"), catalog=None)

        response = ShoplistGenerateResponse(packed=[packed1], unpacked=[unpacked1])

        lines = pdf_export.build_pdf_lines(response)

        # With catalog (store-a) should come before without catalog (empty store)
        assert len(lines) == 2
        assert lines[0].food_id == "with-catalog"
        assert lines[0].store_id == "store-a"
        assert lines[1].food_id == "no-catalog"
        assert lines[1].store_id == ""


class TestBuildPdfLinesGrouping:
    """Test store→aisle grouping logic."""

    def test_grouping_by_store_and_aisle(self) -> None:
        """Test that lines are properly grouped by store and aisle."""
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
        catalog3 = CatalogInfoDTO(
            sku="SKU-3",
            store_id="store-2",
            region_id="region-1",
            aisle="Aisle-A",
            price=MoneyDTO(value=Decimal("3.00"), currency=CurrencyDTO.EUR),
        )

        packed1 = PackedLineDTO(
            food_id="item-1",
            requested=qty("100"),
            pack_size=qty("100"),
            packs=1,
            provided=qty("100"),
            overage=qty("0"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=100 G"],
            catalog=catalog1,
        )
        packed2 = PackedLineDTO(
            food_id="item-2",
            requested=qty("200"),
            pack_size=qty("200"),
            packs=1,
            provided=qty("200"),
            overage=qty("0"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=200 G"],
            catalog=catalog2,
        )
        packed3 = PackedLineDTO(
            food_id="item-3",
            requested=qty("300"),
            pack_size=qty("300"),
            packs=1,
            provided=qty("300"),
            overage=qty("0"),
            rounding="CEIL",
            min_packs=1,
            reasons=["requested=300 G"],
            catalog=catalog3,
        )

        response = ShoplistGenerateResponse(packed=[packed1, packed2, packed3], unpacked=[])

        lines = pdf_export.build_pdf_lines(response)

        # Verify grouping: store-1 (Aisle-A, Aisle-B), store-2 (Aisle-A)
        assert len(lines) == 3
        # Order: store-1, Aisle-A, item-1
        assert lines[0].store_id == "store-1"
        assert lines[0].aisle == "Aisle-A"
        assert lines[0].food_id == "item-1"
        # Order: store-1, Aisle-B, item-2
        assert lines[1].store_id == "store-1"
        assert lines[1].aisle == "Aisle-B"
        assert lines[1].food_id == "item-2"
        # Order: store-2, Aisle-A, item-3
        assert lines[2].store_id == "store-2"
        assert lines[2].aisle == "Aisle-A"
        assert lines[2].food_id == "item-3"


class TestBuildPdfLinesTotals:
    """Test subtotal and total calculations."""

    def test_subtotal_calculation_packed_lines(self) -> None:
        """Test that subtotal_value is correctly calculated (price * packs)."""
        catalog = CatalogInfoDTO(
            sku="SKU-1",
            store_id="store-1",
            region_id="region-1",
            aisle="Aisle-A",
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
            reasons=["requested=600 G"],
            catalog=catalog,
        )

        response = ShoplistGenerateResponse(packed=[packed], unpacked=[])

        lines = pdf_export.build_pdf_lines(response)

        assert len(lines) == 1
        line = lines[0]
        # subtotal = 1.50 * 2 = 3.00
        assert line.subtotal_value == Decimal("3.00")
        assert line.subtotal == "3.00 EUR"
        assert line.price == "1.50 EUR"

    def test_subtotal_zero_for_unpacked_lines(self) -> None:
        """Test that unpacked lines have subtotal_value = 0."""
        unpacked = UnpackedLineDTO(food_id="tomato", requested=qty("200"))

        response = ShoplistGenerateResponse(packed=[], unpacked=[unpacked])

        lines = pdf_export.build_pdf_lines(response)

        assert len(lines) == 1
        line = lines[0]
        assert line.subtotal_value == Decimal("0")
        assert line.subtotal == ""
        assert line.price == ""


class TestExportShoplistToPdfBytes:
    """Test PDF bytes generation."""

    def test_export_returns_pdf_header_and_non_empty(self) -> None:
        """Test that export_shoplist_to_pdf returns valid PDF bytes."""
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
            reasons=["requested=600 G"],
            catalog=catalog,
        )
        unpacked = UnpackedLineDTO(food_id="tomato", requested=qty("200"))

        response = ShoplistGenerateResponse(packed=[packed], unpacked=[unpacked])

        pdf_data = pdf_export.export_shoplist_to_pdf(response)

        # Verify PDF header
        assert pdf_data.startswith(b"%PDF")
        # Verify non-empty (should be at least 500 bytes for a simple PDF)
        assert len(pdf_data) > 500


class TestExportEndpointPdfImportError:
    """Test ImportError → 501 handling at endpoint level."""

    def test_export_endpoint_pdf_importerror_returns_501(
        self, monkeypatch: pytest.MonkeyPatch, client_with_vip_access: TestClient
    ) -> None:
        """Test that ImportError in pdf_export raises 501 with frozen error contract."""

        # Monkeypatch _lazy_reportlab to raise ImportError
        def _mock_lazy_reportlab():
            raise ImportError("reportlab not available")

        monkeypatch.setattr(pdf_export, "_lazy_reportlab", _mock_lazy_reportlab)

        # Enable VIP module
        monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

        payload = {
            "items": [{"food_id": "carrot", "qty": {"value": "100", "unit": "G"}, "form": "RAW"}],
            "packaging_rules": [],
        }

        response = client_with_vip_access.post(
            "/api/v1/vip/shoplist/export?export_format=pdf", json=payload
        )

        assert response.status_code == 501
        data = response.json()

        # Verify content-type is NOT application/pdf for 501
        assert response.headers.get("content-type") != "application/pdf"

        # Verify frozen error contract (supports both default FastAPI and VIP envelope)
        assert (
            data.get("detail") == "PDF export is not available"
            or data.get("message") == "PDF export is not available"
        )

        # If VIP error envelope is present, verify invariants
        if "status" in data:
            assert data["status"] == "error"
            assert data["detail"] == data["message"]
            assert data["error"] == data["code"]


class TestFmtMoneyEdgeCases:
    """Test currency formatting edge cases."""

    def test_fmt_money_with_currency(self) -> None:
        """Test money formatting with currency code."""
        assert pdf_export._fmt_money(Decimal("1.50"), "EUR") == "1.50 EUR"
        assert pdf_export._fmt_money(Decimal("10.00"), "USD") == "10.00 USD"

    def test_fmt_money_without_currency(self) -> None:
        """Test money formatting without currency code."""
        assert pdf_export._fmt_money(Decimal("1"), None) == "1.00"
        assert pdf_export._fmt_money(Decimal("10.5"), "") == "10.50"

    def test_fmt_money_quantize(self) -> None:
        """Test money formatting with quantize to 0.01."""
        # Should quantize to 0.01
        assert pdf_export._fmt_money(Decimal("1.2345"), "EUR") == "1.23 EUR"
        assert pdf_export._fmt_money(Decimal("10.999"), "USD") == "11.00 USD"

    def test_fmt_money_none_value(self) -> None:
        """Test money formatting with None value."""
        assert pdf_export._fmt_money(None, "EUR") == ""
        assert pdf_export._fmt_money(None, None) == ""
