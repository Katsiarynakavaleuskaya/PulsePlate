# -*- coding: utf-8 -*-
"""
Catalog enrichment adapter (mock-first).

RU: Adapter для обогащения shoplist каталожной информацией (SKU, цена, aisle).
EN: Adapter for enriching shoplist with catalog info (SKU, price, aisle).

Principles:
- Adapter-only (engine unchanged)
- Fail-soft (missing catalog is not an error)
- Deterministic (enrichment does not change packs/reasons/analytics)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Optional, Protocol

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)

# ----------------------------
# Provider interface (mock-first)
# ----------------------------


class CatalogProvider(Protocol):
    """
    RU: Контракт провайдера каталога. В PR-6 — только mock.
    EN: Catalog provider contract. PR-6 uses mock only.

    Future PR-7 will implement real loaders (Carrefour/Walmart) behind this interface.
    """

    def get_catalog_info(
        self,
        *,
        food_id: str,
        region_id: str,
        store_id: str,
    ) -> Optional[CatalogInfoDTO]:
        """
        RU: Получить каталожную информацию для food_id в регионе/магазине.
        EN: Get catalog info for food_id in region/store.

        Returns None if not found (fail-soft).
        """
        ...


@dataclass(frozen=True)
class MockCatalogProvider:
    """
    RU: In-memory mock provider для PR-6.
    EN: In-memory mock provider for PR-6.

    Key: (region_id, store_id, food_id) -> CatalogInfoDTO
    """

    # key: (region_id, store_id, food_id)
    data: Mapping[tuple[str, str, str], CatalogInfoDTO]

    def get_catalog_info(
        self,
        *,
        food_id: str,
        region_id: str,
        store_id: str,
    ) -> Optional[CatalogInfoDTO]:
        """Get catalog info from in-memory data."""
        return self.data.get((region_id, store_id, food_id))


def build_default_mock_provider() -> MockCatalogProvider:
    """
    RU: Дефолтный мок. В PR-6 можно оставить минимальный набор.
    EN: Default mock dataset. Keep minimal in PR-6.

    Future PR-7 will replace this with real loaders.
    """
    data = {
        ("es", "carrefour_es", "carrot"): CatalogInfoDTO(
            sku="CRF-ES-000123",
            store_id="carrefour_es",
            region_id="es",
            pack_label="500 g bag",
            aisle="Vegetables",
            price=MoneyDTO(value=Decimal("1.29"), currency=CurrencyDTO.EUR),
        ),
        ("us", "walmart_us", "carrot"): CatalogInfoDTO(
            sku="WMT-US-009991",
            store_id="walmart_us",
            region_id="us",
            pack_label="1 lb bag",
            aisle="Produce",
            price=MoneyDTO(value=Decimal("1.18"), currency=CurrencyDTO.USD),
        ),
    }
    return MockCatalogProvider(data=data)


def enrich_shoplist_response(
    response: ShoplistGenerateResponse,
    *,
    region_id: Optional[str],
    store_id: Optional[str],
    provider: CatalogProvider,
) -> ShoplistGenerateResponse:
    """
    RU: Enrichment fail-soft. Если region/store не заданы — ничего не делаем.
        Если catalog не найден — поле catalog остаётся None.
        ВАЖНО: packs/reasons/analytics НЕ меняем.
    EN: Fail-soft enrichment. If region/store not set -> no-op.
        If no catalog -> catalog stays None.
        IMPORTANT: Do not mutate packs/reasons/analytics.

    Args:
        response: Base shoplist response (from engine)
        region_id: Optional region identifier
        store_id: Optional store identifier
        provider: Catalog provider (mock in PR-6)

    Returns:
        Enriched response (catalog fields added where available)
    """
    if not region_id or not store_id:
        return response

    # Pydantic models are mutable by default; we keep changes minimal & explicit
    # by reconstructing line DTOs (safer for invariants).
    enriched_packed: list[PackedLineDTO] = []
    for line in response.packed:
        catalog = provider.get_catalog_info(
            food_id=line.food_id,
            region_id=region_id,
            store_id=store_id,
        )
        enriched_packed.append(line.model_copy(update={"catalog": catalog}, deep=False))

    enriched_unpacked: list[UnpackedLineDTO] = []
    for line in response.unpacked:
        catalog = provider.get_catalog_info(
            food_id=line.food_id,
            region_id=region_id,
            store_id=store_id,
        )
        enriched_unpacked.append(line.model_copy(update={"catalog": catalog}, deep=False))

    return response.model_copy(
        update={
            "packed": enriched_packed,
            "unpacked": enriched_unpacked,
        },
        deep=False,
    )

