# -*- coding: utf-8 -*-
"""
Tests for catalog models module (PR-7).

RU: Тесты для модуля models (re-export проверка).
EN: Tests for models module (re-export verification).
"""

from __future__ import annotations

from core.catalog.models import (
    CatalogRegion,
    CatalogSKU,
    CatalogSnapshot,
    CatalogStore,
)


def test_models_imports() -> None:
    """Test that models module correctly re-exports all models."""
    # Verify all models are importable
    assert CatalogRegion is not None
    assert CatalogStore is not None
    assert CatalogSKU is not None
    assert CatalogSnapshot is not None

    # Verify they are the same objects from provider
    from core.catalog.provider import (
        CatalogRegion as ProviderCatalogRegion,
        CatalogSKU as ProviderCatalogSKU,
        CatalogSnapshot as ProviderCatalogSnapshot,
        CatalogStore as ProviderCatalogStore,
    )

    assert CatalogRegion is ProviderCatalogRegion
    assert CatalogStore is ProviderCatalogStore
    assert CatalogSKU is ProviderCatalogSKU
    assert CatalogSnapshot is ProviderCatalogSnapshot
