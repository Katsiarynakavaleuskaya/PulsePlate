# -*- coding: utf-8 -*-
"""
Catalog storage layer (PR-7).

RU: Слой хранения каталога (SQLite writer/reader).
EN: Catalog storage layer (SQLite writer/reader).
"""

from __future__ import annotations

from core.catalog.storage.sqlite_writer import write_snapshot

__all__ = [
    "write_snapshot",
]

