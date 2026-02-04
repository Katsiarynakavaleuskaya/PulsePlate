"""
Export format primitives.

RU: Примитивы форматов экспорта (расширение, Content-Type).
EN: Export format primitives (extension, Content-Type).
"""

from __future__ import annotations

from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats for file downloads."""

    CSV = "csv"
    PDF = "pdf"
    JSON = "json"

    @property
    def extension(self) -> str:
        return self.value

    @property
    def media_type(self) -> str:
        try:
            return _MEDIA_TYPES[self]
        except KeyError as exc:  # pragma: no cover
            raise NotImplementedError(
                f"Missing media_type mapping for export format: {self}"
            ) from exc


_MEDIA_TYPES: dict[ExportFormat, str] = {
    ExportFormat.CSV: "text/csv",
    ExportFormat.PDF: "application/pdf",
    ExportFormat.JSON: "application/json",
}
