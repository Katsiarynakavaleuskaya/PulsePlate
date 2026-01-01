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
    """
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]
