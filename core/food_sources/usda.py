"""
USDA Adapter

RU: Адаптер для USDA.
EN: USDA adapter.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from typing import Dict, Iterable, Optional, TypeAlias

from core.aliases import map_to_canonical
from core.units import iu_vitd_from_ug
from core.food_sources.base import BaseAdapter, FoodRecord

RawValue: TypeAlias = str | float | int | None


def _parse_nutrient_value(raw_value: RawValue) -> Optional[float]:
    """
    RU: Парсинг значения питательного вещества.
    EN: Parse nutrient value.

    Returns None if the value is missing, empty, or invalid.
    Only returns a float if the raw value is a valid numeric string.

    Args:
        raw_value: Raw value from data source

    Returns:
        Parsed float value or None if missing/invalid
    """
    if raw_value is None or raw_value == "" or raw_value == "unknown":
        return None
    try:
        # Strip whitespace and check if it's a valid number
        cleaned = str(raw_value).strip()
        if cleaned == "" or cleaned.lower() in {"nan", "null", "none"}:
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None


class USDAAdapter(BaseAdapter):
    """
    RU: Адаптер для базы данных USDA.
    EN: Adapter for USDA database.
    """

    def __init__(self, csv_path: Optional[str] = None) -> None:
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

    def fetch(self) -> Iterable[Dict[str, str]]:
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

            # Extract nutrients (None for missing/unknown values)
            kcal = _parse_nutrient_value(row.get("energy_kcal"))
            protein_g = _parse_nutrient_value(row.get("protein_g"))
            fat_g = _parse_nutrient_value(row.get("fat_g"))
            carbs_g = _parse_nutrient_value(row.get("carbs_g"))
            fiber_g = _parse_nutrient_value(row.get("fiber_g"))
            Fe_mg = _parse_nutrient_value(row.get("iron_mg"))
            Ca_mg = _parse_nutrient_value(row.get("calcium_mg"))

            # Vitamin D conversion
            vitd_ug = _parse_nutrient_value(row.get("vitd_ug"))
            VitD_IU = iu_vitd_from_ug(vitd_ug) if vitd_ug is not None else None

            B12_ug = _parse_nutrient_value(row.get("b12_ug"))
            Folate_ug = _parse_nutrient_value(row.get("folate_ug"))
            Iodine_ug = _parse_nutrient_value(row.get("iodine_ug"))
            K_mg = _parse_nutrient_value(row.get("potassium_mg"))
            Mg_mg = _parse_nutrient_value(row.get("magnesium_mg"))

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
