# -*- coding: utf-8 -*-
"""Shared helpers for monkeypatching `pdf_export._lazy_reportlab` in tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

LazyReportlabFn = Callable[[], tuple[Any, ...]]


def make_lazy_reportlab_mock(
    real_lazy: LazyReportlabFn,
    *,
    simple_doc_template: Any | None = None,
    table: Any | None = None,
    table_style: Any | None = None,
) -> LazyReportlabFn:
    """Return a `_lazy_reportlab` replacement with selective overrides."""

    def _mock() -> tuple[Any, ...]:
        (
            colors,
            A4,
            getSampleStyleSheet,
            mm,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        ) = real_lazy()

        return (
            colors,
            A4,
            getSampleStyleSheet,
            mm,
            Paragraph,
            simple_doc_template or SimpleDocTemplate,
            Spacer,
            table or Table,
            table_style or TableStyle,
        )

    return _mock
