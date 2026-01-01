# -*- coding: utf-8 -*-
"""
Alias normalization utilities (PR-7).

RU: Утилиты для нормализации алиасов (единый канон).
EN: Alias normalization utilities (canonical form).
"""

from __future__ import annotations


def norm_alias(value: str) -> str:
    """
    RU: Единый канон алиаса: trim + lower + collapse spaces.
    EN: Canonical alias: trim + lower + collapse whitespace.

    Args:
        value: Raw alias string

    Returns:
        Normalized alias (lowercase, trimmed, single spaces).
        Returns empty string if input is empty or whitespace-only.
    """
    s = value.strip().lower()
    # Collapse multiple spaces into single space
    s = " ".join(s.split())
    return s

