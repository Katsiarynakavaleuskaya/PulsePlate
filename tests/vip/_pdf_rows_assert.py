# -*- coding: utf-8 -*-
"""
RU: Хелперы для guard-тестов PDF rows (без reportlab).
EN: Helpers for PDF rows guard tests (no reportlab).

Goal:
- avoid brittle index-based assertions
- test semantic layout contract (store/aisle/items/subtotals/total)
"""

from __future__ import annotations

from collections.abc import Sequence

from app.services.shoplist_export import pdf_export

RowType = pdf_export.PdfRowType
PdfRow = pdf_export.PdfRow


def rows_sig(rows: Sequence[PdfRow]) -> list[str]:
    """Return row type signature."""
    return [r.row_type.value if hasattr(r.row_type, "value") else str(r.row_type) for r in rows]


def assert_contains_subsequence(sig: Sequence[str], subseq: Sequence[str]) -> None:
    """
    RU: Проверяет что subseq встречается в sig в том же порядке (не обязательно подряд).
    EN: Checks that subseq appears in sig in the same order (not necessarily contiguous).
    """
    it = iter(sig)
    for token in subseq:
        for cur in it:
            if cur == token:
                break
        else:
            raise AssertionError(
                f"Signature does not contain token in order: {token}. sig={list(sig)}"
            )


def find_rows(rows: Sequence[PdfRow], row_type: RowType) -> list[PdfRow]:
    """Find all rows of given type."""
    return [r for r in rows if r.row_type == row_type]


def find_item(rows: Sequence[PdfRow], food_id: str) -> PdfRow:
    """Find ITEM row by food_id."""
    for r in rows:
        if r.row_type == RowType.ITEM and r.cells and r.cells[0] == food_id:
            return r
    raise AssertionError(f"ITEM row not found for food_id={food_id}")


# PDF table column index contract: subtotal/total column
MONEY_COLUMN_INDEX = 6


def money_cell(row: PdfRow) -> str:
    """
    Contract: subtotal/total are stored in cells[MONEY_COLUMN_INDEX].
    """
    if len(row.cells) <= MONEY_COLUMN_INDEX:
        raise AssertionError(
            f"Expected money cell at [{MONEY_COLUMN_INDEX}], got cells={row.cells}"
        )
    return row.cells[MONEY_COLUMN_INDEX]


def item_packs(row: PdfRow) -> str:
    """Get packs value from ITEM row (cells[3])."""
    if row.row_type != RowType.ITEM:
        raise AssertionError(f"Expected ITEM row, got {row.row_type}")
    if len(row.cells) < 4:
        raise AssertionError(f"Expected packs at [3], got cells={row.cells}")
    return row.cells[3]


def item_subtotal(row: PdfRow) -> str:
    """Get subtotal value from ITEM row (cells[6])."""
    if row.row_type != RowType.ITEM:
        raise AssertionError(f"Expected ITEM row, got {row.row_type}")
    return money_cell(row)


def assert_subtotals_and_total(
    rows: Sequence[PdfRow],
    subtotals: Sequence[str],
    total: str,
) -> None:
    """
    RU: Проверяет значения subtotal-строк и grand total.
    EN: Verifies subtotal rows values and grand total.
    """
    sub_rows = find_rows(rows, RowType.SUBTOTAL)
    assert [money_cell(r) for r in sub_rows] == list(subtotals)

    total_row = next((r for r in rows if r.row_type == RowType.GRAND_TOTAL), None)
    assert total_row is not None, "GRAND_TOTAL row not found"
    assert money_cell(total_row) == total
