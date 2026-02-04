"""
Export format primitives.

RU: Примитивы форматов экспорта (расширение, Content-Type).
EN: Export format primitives (extension, Content-Type).
"""

from __future__ import annotations

from enum import StrEnum


class ExportFormat(StrEnum):
    """Supported export formats for file downloads."""

    CSV = "csv"
    PDF = "pdf"
    JSON = "json"

    @property
    def extension(self) -> str:
        return self.value

    @property
    def media_type(self) -> str:
        if self is ExportFormat.CSV:
            return "text/csv"
        if self is ExportFormat.PDF:
            return "application/pdf"
        return "application/json"
