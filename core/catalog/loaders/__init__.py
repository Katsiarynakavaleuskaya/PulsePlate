# -*- coding: utf-8 -*-
"""
Catalog loaders (PR-7).

RU: Загрузчики каталога для преобразования raw данных в канонические snapshots.
EN: Catalog loaders for converting raw data into canonical snapshots.
"""

from __future__ import annotations

from core.catalog.loaders.base import read_csv_rows

__all__ = [
    "read_csv_rows",
]
