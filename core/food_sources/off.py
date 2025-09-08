"""
Open Food Facts Adapter

RU: Адаптер для Open Food Facts.
EN: Open Food Facts adapter.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from typing import Dict, Iterable

from ..aliases import map_to_canonical
from .base import BaseAdapter, FoodRecord


class OFFAdapter(BaseAdapter):
    """
    RU: Адаптер для базы данных Open Food Facts.
    EN: Adapter for Open Food Facts database.
    """

    def __init__(self, csv_path: str = None, locale: str = "en"):
        """
        RU: Инициализировать адаптер OFF.
        EN: Initialize OFF adapter.

        Args:
            csv_path: Path to OFF CSV file
            locale: Locale of the data
        """
        if csv_path is None:
            # Default path relative to project root
            csv_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "external",
                "off_products_sample.csv",
            )
        self.csv_path = csv_path
        self.locale = locale

    def fetch(self) -> Iterable[Dict]:
        """
        RU: Читаем CSV Open Food Facts.
        EN: Read Open Food Facts CSV.
        """
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)

    def normalize(self) -> Iterable[FoodRecord]:
        """
        RU: Нормализовать данные OFF к единому формату.
        EN: Normalize OFF data to unified format.
        """
        today = date.today().isoformat()
        for row in self.fetch():
            # Get product name (try multiple fields)
            raw_name = (
                row.get("product_name", "")
                or row.get("generic_name", "")
                or row.get("product_name_en", "")
            )
            canonical = map_to_canonical(raw_name, locale=self.locale)
            per_g = 100.0

            # Extract nutrients (with fallback to 0)
            kcal = float(row.get("energy-kcal_100g", 0) or 0)
            protein_g = float(row.get("proteins_100g", 0) or 0)
            fat_g = float(row.get("fat_100g", 0) or 0)
            carbs_g = float(row.get("carbohydrates_100g", 0) or 0)
            fiber_g = float(row.get("fiber_100g", 0) or 0)

            # Micro nutrients (often empty in OFF)
            Fe_mg = float(row.get("iron_100g", 0) or 0)
            Ca_mg = float(row.get("calcium_100g", 0) or 0)
            VitD_IU = float(
                row.get("vitamin-d_100g", 0) or 0
            )  # May be in µg, needs conversion
            B12_ug = float(row.get("vitamin-b12_100g", 0) or 0)
            Folate_ug = float(row.get("vitamin-b9_100g", 0) or 0)
            Iodine_ug = float(row.get("iodine_100g", 0) or 0)
            K_mg = float(row.get("potassium_100g", 0) or 0)
            Mg_mg = float(row.get("magnesium_100g", 0) or 0)

            # Extract flags
            flags = []
            if row.get("gluten-free") == "yes":
                flags.append("GF")
            if row.get("vegan") == "yes":
                flags.append("VEG")
            if row.get("low-cost") == "yes":
                flags.append("LOW_COST")
            if row.get("dairy_free") == "yes":
                flags.append("DAIRY_FREE")

            yield FoodRecord(
                name=canonical,
                locale=self.locale,
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
                flags=flags,
                price=0.0,
                source="OFF",
                version_date=today,
            )
