# -*- coding: utf-8 -*-
"""
Canonical catalog models (PR-7).

RU: Канонические модели каталога для PR-7 (re-export из provider.py для удобства).
EN: Canonical catalog models for PR-7 (re-export from provider.py for convenience).

This module re-exports the canonical models from provider.py to avoid circular imports.
"""

from __future__ import annotations

from core.catalog.provider import (
    CatalogRegion,
    CatalogSKU,
    CatalogSnapshot,
    CatalogStore,
)

__all__ = [
    "CatalogRegion",
    "CatalogStore",
    "CatalogSKU",
    "CatalogSnapshot",
]
