# -*- coding: utf-8 -*-
"""
Base catalog loader utilities (PR-7).

RU: Базовые утилиты для загрузчиков каталога.
EN: Base utilities for catalog loaders.
"""

from __future__ import annotations

import csv
from pathlib import Path


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """
    RU: Читает CSV файл и возвращает список словарей.
    EN: Reads CSV file and returns list of dictionaries.

    Args:
        path: Path to CSV file

    Returns:
        List of row dictionaries (keys from CSV header)

    Raises:
        FileNotFoundError: If CSV file does not exist
        ValueError: If CSV file is empty or has no data rows
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV file not found: {p}")

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV file is empty or has no data rows: {p}")

    return rows
