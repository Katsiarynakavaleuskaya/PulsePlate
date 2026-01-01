# -*- coding: utf-8 -*-
"""
Common normalization functions (PR-7).

RU: Общие функции нормализации (Decimal, currency, units).
EN: Common normalization functions (Decimal, currency, units).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_decimal(value: str | None) -> Decimal | None:
    """
    RU: Строгий парсер Decimal без float. Поддерживает "1 234,56" и "1234.56".
    EN: Strict Decimal parser (no float). Supports spaces and comma decimals.

    Args:
        value: Input string (may contain spaces, commas, or dots)

    Returns:
        Decimal if valid, None otherwise (fail-soft)
    """
    if value is None:
        return None

    s = value.strip()
    if not s:
        return None

    # Remove spaces as thousand separators
    s = s.replace(" ", "")

    # Handle mixed separators (deterministic: use last separator as decimal)
    if "," in s and "." in s:
        # Determine decimal separator by last occurrence
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma > last_dot:
            # EU format: "1.234,56" -> "1234.56"
            s = s.replace(".", "").replace(",", ".")
        else:
            # US format: "1,234.56" -> "1234.56"
            s = s.replace(",", "")
    elif s.count(",") == 1 and "." not in s:
        # "1234,56" -> "1234.56" (EU decimal)
        s = s.replace(",", ".")
    elif s.count(",") > 1 and "." in s:
        # "1,234,567.89" -> "1234567.89" (US with multiple thousands)
        s = s.replace(",", "")

    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def normalize_currency(value: str | None, *, default: str) -> str:
    """
    RU: Нормализует валюту. EN: Normalizes currency.

    Args:
        value: Currency code or symbol
        default: Default currency if value is empty/invalid

    Returns:
        Normalized currency code (uppercase)
    """
    if not value:
        return default
    return value.strip().upper()


def normalize_unit(value: str | None) -> str | None:
    """
    RU: Приводит единицы к канону. EN: Normalizes unit labels.

    Args:
        value: Unit string (e.g., "g", "kg", "ml", "L", "pcs")

    Returns:
        Normalized unit code (lowercase) or None
    """
    if not value:
        return None
    u = value.strip().lower()
    mapping = {
        "g": "g",
        "гр": "g",
        "gram": "g",
        "grams": "g",
        "kg": "kg",
        "ml": "ml",
        "l": "l",
        "pcs": "pcs",
        "pc": "pcs",
        "piece": "pcs",
        "pieces": "pcs",
        "шт": "pcs",
    }
    return mapping.get(u, u)
