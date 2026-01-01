# -*- coding: utf-8 -*-
"""
Unit tests for catalog adapter (mock provider).

RU: Unit-тесты для catalog adapter (mock provider).
EN: Unit tests for catalog adapter (mock provider).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    QuantityDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)
from app.services.catalog_adapter import (
    MockCatalogProvider,
    enrich_shoplist_response,
    reset_catalog_provider_for_tests,
)
from core.catalog.provider import CatalogProvider


class FakeCatalogProvider:
    """
    RU: Фейковый provider для тестов enrichment (контракт PR-7).
    EN: Fake provider for enrichment tests (PR-7 contract).

    Гарантирует стабильное поведение независимо от реализации MockCatalogProvider.
    """

    def get_catalog_info(
        self,
        *,
        food_id: str,
        region_id: str,
        store_id: str | None = None,
    ) -> CatalogInfoDTO | None:
        """RU/EN: Return catalog for carrot in ES region, None otherwise."""
        rid = region_id.strip().lower()
        sid = (store_id or "carrefour_es").strip().lower()

        if food_id == "carrot" and rid == "es":
            return CatalogInfoDTO(
                sku="SKU_TEST_CARROT",
                store_id=sid,
                region_id="es",
                pack_label="500 G",
                aisle="Vegetables",
                price=MoneyDTO(value=Decimal("1.29"), currency=CurrencyDTO.EUR),
            )
        return None

    def list_stores(self, *, region_id: str) -> list:
        """RU/EN: Return empty list for fake provider."""
        return []


def test_enrich_adds_catalog_when_food_id_found() -> None:
    """Test that enrichment adds catalog when food_id is found in provider."""
    reset_catalog_provider_for_tests()
    provider = FakeCatalogProvider()

    base = ShoplistGenerateResponse(
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
                reasons=["min_packs"],
            )
        ],
        unpacked=[],
        analytics=None,
    )

    out = enrich_shoplist_response(base, region_id="es", store_id="carrefour_es", provider=provider)

    assert out.packed[0].catalog is not None
    assert out.packed[0].catalog.sku == "SKU_TEST_CARROT"
    assert out.packed[0].catalog.store_id == "carrefour_es"
    assert out.packed[0].catalog.region_id == "es"


def test_enrich_is_fail_soft_when_not_found() -> None:
    """Test that enrichment is fail-soft when catalog not found."""
    provider = MockCatalogProvider(data={})

    base = ShoplistGenerateResponse(
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
                reasons=["min_packs"],
            )
        ],
        unpacked=[
            UnpackedLineDTO(
                food_id="milk",
                requested=QuantityDTO(value=Decimal("1"), unit="L"),
                reason="no_packaging_rule",
            )
        ],
        analytics=None,
    )

    out = enrich_shoplist_response(base, region_id="es", store_id="carrefour_es", provider=provider)

    assert out.packed[0].catalog is None
    assert out.unpacked[0].catalog is None


def test_enrich_does_not_mutate_core_fields() -> None:
    """Test that enrichment does not mutate packs/reasons/analytics."""
    reset_catalog_provider_for_tests()
    provider = FakeCatalogProvider()

    base = ShoplistGenerateResponse(
        packed=[
            PackedLineDTO(
                food_id="carrot",
                requested=QuantityDTO(value=Decimal("100"), unit="G"),
                pack_size=QuantityDTO(value=Decimal("500"), unit="G"),
                packs=2,
                provided=QuantityDTO(value=Decimal("1000"), unit="G"),
                overage=QuantityDTO(value=Decimal("900"), unit="G"),
                rounding="CEIL",
                min_packs=1,
                reasons=["rounding", "min_packs"],
            )
        ],
        unpacked=[],
        analytics=None,
    )

    out = enrich_shoplist_response(base, region_id="es", store_id="carrefour_es", provider=provider)

    # Core fields unchanged
    assert out.packed[0].packs == 2
    assert out.packed[0].reasons == ["rounding", "min_packs"]
    assert out.packed[0].food_id == "carrot"

    # Catalog added
    assert out.packed[0].catalog is not None
    assert out.packed[0].catalog.sku == "SKU_TEST_CARROT"


def test_enrich_no_op_when_region_store_not_provided() -> None:
    """Test that enrichment is no-op when region_id or store_id is None."""
    reset_catalog_provider_for_tests()
    provider = FakeCatalogProvider()

    base = ShoplistGenerateResponse(
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
                reasons=["min_packs"],
            )
        ],
        unpacked=[],
        analytics=None,
    )

    # No region_id
    out1 = enrich_shoplist_response(
        base, region_id=None, store_id="carrefour_es", provider=provider
    )
    assert out1.packed[0].catalog is None

    # No store_id
    out2 = enrich_shoplist_response(base, region_id="es", store_id=None, provider=provider)
    assert out2.packed[0].catalog is None

    # Both None
    out3 = enrich_shoplist_response(base, region_id=None, store_id=None, provider=provider)
    assert out3.packed[0].catalog is None
