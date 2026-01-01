# -*- coding: utf-8 -*-
"""
Tests for core/catalog/loaders/base.py (PR-7).

RU: Тесты для базовых утилит загрузчиков каталога.
EN: Tests for base catalog loader utilities.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.catalog.loaders.base import read_csv_rows


def test_read_csv_rows_success(tmp_path: Path) -> None:
    """Test successful CSV reading."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,price,unit\nApple,1.99,kg\nBanana,2.49,kg", encoding="utf-8")

    rows = read_csv_rows(csv_file)

    assert len(rows) == 2
    assert rows[0] == {"name": "Apple", "price": "1.99", "unit": "kg"}
    assert rows[1] == {"name": "Banana", "price": "2.49", "unit": "kg"}


def test_read_csv_rows_file_not_found(tmp_path: Path) -> None:
    """Test that FileNotFoundError is raised for non-existent file."""
    non_existent = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        read_csv_rows(non_existent)


def test_read_csv_rows_empty_file(tmp_path: Path) -> None:
    """Test that ValueError is raised for empty CSV file."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("name,price\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV file is empty or has no data rows"):
        read_csv_rows(empty_file)


def test_read_csv_rows_header_only(tmp_path: Path) -> None:
    """Test that ValueError is raised for CSV with header only (no data rows)."""
    header_only = tmp_path / "header_only.csv"
    header_only.write_text("name,price,unit\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV file is empty or has no data rows"):
        read_csv_rows(header_only)


def test_read_csv_rows_with_utf8(tmp_path: Path) -> None:
    """Test that CSV with UTF-8 characters is read correctly."""
    utf8_file = tmp_path / "utf8.csv"
    utf8_file.write_text("name,price\nМолоко,2.99\nХлеб,1.50", encoding="utf-8")

    rows = read_csv_rows(utf8_file)

    assert len(rows) == 2
    assert rows[0]["name"] == "Молоко"
    assert rows[1]["name"] == "Хлеб"
