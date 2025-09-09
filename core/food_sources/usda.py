"""
USDA Adapter

RU: Адаптер для USDA.
EN: USDA adapter.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from typing import Dict, Iterable

from ..aliases import map_to_canonical
from ..units import iu_vitd_from_ug
from .base import BaseAdapter, FoodRecord


class USDAAdapter(BaseAdapter):
    """
    RU: Адаптер для базы данных USDA.
    EN: Adapter for USDA database.
    """

    def __init__(self, csv_path: str = None):
        """
        RU: Инициализировать адаптер USDA.
        EN: Initialize USDA adapter.

        Args:
            csv_path: Path to USDA CSV file
        """
        if csv_path is None:
            # Default path relative to project root
            csv_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "external", "usda_fdc_sample.csv"
            )
        self.csv_path = csv_path

    def fetch(self) -> Iterable[Dict]:
        """
        RU: Читаем один CSV или все CSV в директории (чанки).
        EN: Read a single CSV or all CSVs in a directory (chunks).
        """
        path = self.csv_path
        if os.path.isdir(path):
            # Iterate over CSV files in directory, sorted for determinism
            for name in sorted(os.listdir(path)):
                if not name.lower().endswith(".csv"):
                    continue
                full = os.path.join(path, name)
                with open(full, newline="", encoding="utf-8") as f:
                    yield from csv.DictReader(f)
            return

        with open(path, newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)

    def normalize(self) -> Iterable[FoodRecord]:
        """
        RU: Нормализовать данные USDA к единому формату.
        EN: Normalize USDA data to unified format.
        """
        today = date.today().isoformat()
        for row in self.fetch():
            raw_name = row.get("description", "")
            canonical = map_to_canonical(raw_name, locale="en")
            per_g = 100.0

            # Extract nutrients (with fallback to 0)
            kcal = float(row.get("energy_kcal", 0) or 0)
            protein_g = float(row.get("protein_g", 0) or 0)
            fat_g = float(row.get("fat_g", 0) or 0)
            carbs_g = float(row.get("carbs_g", 0) or 0)
            fiber_g = float(row.get("fiber_g", 0) or 0)
            Fe_mg = float(row.get("iron_mg", 0) or 0)
            Ca_mg = float(row.get("calcium_mg", 0) or 0)

            # Vitamin D conversion
            vitd_ug = float(row.get("vitd_ug", 0) or 0)
            VitD_IU = iu_vitd_from_ug(vitd_ug)

            B12_ug = float(row.get("b12_ug", 0) or 0)
            Folate_ug = float(row.get("folate_ug", 0) or 0)
            Iodine_ug = float(row.get("iodine_ug", 0) or 0)
            K_mg = float(row.get("potassium_mg", 0) or 0)
            Mg_mg = float(row.get("magnesium_mg", 0) or 0)

            yield FoodRecord(
                name=canonical,
                locale="en",
                per_g=per_g,
                kcal=kcal,
                protein_g=protein_g,
                fat_g=fat_g,
                carbs_g=carbs_g,
                fiber_g=fiber_g,
                Fe_mg=Fe_mg,
                Ca_mg=Ca_mg,
                VitD_IU=VitD_IU,
                B12_ug=B12_ug,
                Folate_ug=Folate_ug,
                Iodine_ug=Iodine_ug,
                K_mg=K_mg,
                Mg_mg=Mg_mg,
                flags=[],
                price=0.0,
                source="USDA",
                version_date=today,
            )
