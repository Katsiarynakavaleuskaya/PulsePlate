# -*- coding: utf-8 -*-
"""
Tests for alias normalization (PR-7).

RU: Тесты для нормализации алиасов.
EN: Tests for alias normalization.

These tests protect the architectural decision: norm_alias returns empty string
for empty/whitespace inputs (no exceptions), allowing fail-soft logic in loaders.
"""

from __future__ import annotations

from core.catalog.normalize.alias import norm_alias


def test_norm_alias_canonicalization() -> None:
    """Test canonical alias normalization (trim + lower + collapse spaces)."""
    assert norm_alias("  Olive   Oil  ") == "olive oil"
    assert norm_alias("OLIVE OIL") == "olive oil"
    assert norm_alias(" olive   oil ") == "olive oil"
    assert norm_alias("") == ""
    assert norm_alias("   ") == ""


def test_norm_alias_returns_empty_for_whitespace() -> None:
    """Test that norm_alias returns empty string for whitespace-only input (no exceptions)."""
    # This is the architectural decision: no ValueError, return empty string
    # Loaders handle empty aliases with: if not alias: continue
    assert norm_alias("") == ""
    assert norm_alias("   ") == ""
    assert norm_alias("\t\n") == ""
    assert norm_alias(" \t \n ") == ""


def test_norm_alias_preserves_content() -> None:
    """Test that norm_alias preserves content while normalizing format."""
    assert norm_alias("carrot") == "carrot"
    assert norm_alias("Carrot") == "carrot"
    assert norm_alias("  CARROT  ") == "carrot"
    assert norm_alias("olive oil 1l") == "olive oil 1l"
    assert norm_alias("Olive Oil 1L") == "olive oil 1l"


def test_norm_alias_collapses_multiple_spaces() -> None:
    """Test that multiple spaces are collapsed to single space."""
    assert norm_alias("olive   oil") == "olive oil"
    assert norm_alias("olive\t\toil") == "olive oil"  # tabs become spaces
    assert norm_alias("olive\n\noil") == "olive oil"  # newlines become spaces
