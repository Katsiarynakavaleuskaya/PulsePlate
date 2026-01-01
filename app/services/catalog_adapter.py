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

import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Optional

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    ShoplistGenerateResponse,
    UnpackedLineDTO,
)
from core.catalog.provider import CatalogProvider, CatalogStore

logger = logging.getLogger(__name__)

# ----------------------------
# Provider interface (mock-first)
# ----------------------------


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
        store_id: str | None = None,
    ) -> Optional[CatalogInfoDTO]:
        """Get catalog info from in-memory data."""
        # Normalize region_id to lowercase (matching data keys)
        region_id_norm = region_id.strip().lower()
        # Mock implementation: if store_id provided, use it; otherwise match any
        if store_id:
            store_id_norm = store_id.strip().lower()
            return self.data.get((region_id_norm, store_id_norm, food_id))
        # Try to find any store for this region
        for (r, s, f), catalog in self.data.items():
            if r == region_id_norm and f == food_id:
                return catalog
        return None

    def list_stores(self, *, region_id: str) -> list[CatalogStore]:
        """
        RU: Список магазинов в регионе (mock implementation).
        EN: List stores in region (mock implementation).

        Returns empty list for mock provider.
        """
        from core.catalog.provider import CatalogStore

        # Extract unique stores from mock data for this region
        region_id_norm = region_id.strip().lower()
        stores: dict[str, CatalogStore] = {}
        for (r, store_id, _), catalog in self.data.items():
            if r == region_id_norm and store_id not in stores:
                stores[store_id] = CatalogStore(
                    store_id=store_id,
                    region_id=region_id_norm,
                    name=f"Mock Store {store_id}",
                    provider="mock",
                    meta_json=None,
                )
        return list(stores.values())


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


# ----------------------------
# Provider selection (PR-7)
# ----------------------------

_PROVIDER: Optional[CatalogProvider] = None


def _get_provider() -> CatalogProvider:
    """
    RU: Выбирает provider по env. EN: Select provider via env flag.
    Fail-soft: при ошибке возвращаем mock (или no-op provider).

    Returns:
        CatalogProvider instance (MockCatalogProvider or SQLiteCatalogProvider)
    """
    global _PROVIDER

    if _PROVIDER is not None:
        return _PROVIDER

    provider_type = (os.getenv("CATALOG_PROVIDER") or "mock").strip().lower()

    if provider_type == "sqlite":
        sqlite_path_str = (
            os.getenv("CATALOG_SQLITE_PATH") or "data/catalog/snapshots/catalog_demo.sqlite"
        )
        sqlite_path = Path(sqlite_path_str)
        if not sqlite_path.is_absolute():
            # Resolve relative to project root
            project_root = Path(__file__).resolve().parents[2]
            sqlite_path = project_root / sqlite_path

        try:
            from app.services.catalog_provider_sqlite import SQLiteCatalogProvider

            _PROVIDER = SQLiteCatalogProvider(str(sqlite_path))
            return _PROVIDER
        except (ValueError, FileNotFoundError) as e:
            # Fallback to mock if SQLite provider is misconfigured (fail-soft)
            logger.warning(
                f"SQLite catalog provider failed (path={sqlite_path}): {e}. "
                "Falling back to mock provider.",
                exc_info=True,
            )

    # Default: mock
    _PROVIDER = build_default_mock_provider()
    return _PROVIDER


def reset_catalog_provider_for_tests() -> None:
    """
    RU: Сброс singleton provider для тестов/reload.
    EN: Reset cached provider for tests.

    This allows tests to change CATALOG_PROVIDER env var and get a fresh provider.
    """
    global _PROVIDER
    _PROVIDER = None


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
    for packed_line in response.packed:
        catalog = provider.get_catalog_info(
            food_id=packed_line.food_id,
            region_id=region_id,
            store_id=store_id,
        )
        # model_copy preserves the type correctly
        enriched_packed.append(packed_line.model_copy(update={"catalog": catalog}, deep=False))

    enriched_unpacked: list[UnpackedLineDTO] = []
    for unpacked_line in response.unpacked:
        catalog = provider.get_catalog_info(
            food_id=unpacked_line.food_id,
            region_id=region_id,
            store_id=store_id,
        )
        # model_copy preserves the type correctly
        enriched_unpacked.append(unpacked_line.model_copy(update={"catalog": catalog}, deep=False))

    return response.model_copy(
        update={
            "packed": enriched_packed,
            "unpacked": enriched_unpacked,
        },
        deep=False,
    )
