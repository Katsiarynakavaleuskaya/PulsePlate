#!/usr/bin/env python3
"""
Food Database Builder

RU: Сборка профессиональной базы данных продуктов из CSV в Parquet/SQLite.
EN: Build professional food database from CSV to Parquet/SQLite.
"""

import hashlib
import json
import sqlite3

# Add project root to path
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
from pydantic import ValidationError

sys.path.append(str(Path(__file__).parent.parent))

from core.food_merge import merge_records
from core.food_sources.off import OFFAdapter
from core.food_sources.usda import USDAAdapter
from core.schemas import FoodItem


class FoodDatabaseBuilder:
    """
    RU: Сборщик базы данных продуктов с полной прослеживаемостью.
    EN: Food database builder with full provenance tracking.
    """

    def __init__(self, project_root: str = None):
        """Initialize builder with project paths."""
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "data"
        self.external_dir = self.project_root / "external"
        self.usda_chunks_dir = self.external_dir / "usda_chunks"
        self.off_chunks_dir = self.external_dir / "off_chunks"

        # Output paths
        self.food_parquet = self.data_dir / "food.parquet"
        self.food_sqlite = self.data_dir / "food.sqlite"
        self.build_report = self.data_dir / "build_report.json"

        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.external_dir.mkdir(exist_ok=True)

    def load_source_data(self) -> tuple[List[Dict], List[Dict]]:
        """
        RU: Загрузить данные из всех источников (USDA + OFF).
        EN: Load data from all sources (USDA + OFF).
        """
        print("🔄 Loading source data...")

        # Load USDA data (from chunks or single file)
        usda_data = []
        if self.usda_chunks_dir.exists() and any(self.usda_chunks_dir.glob("*.csv")):
            print(f"  📊 Loading USDA chunks from {self.usda_chunks_dir}")
            adapter = USDAAdapter(str(self.usda_chunks_dir))
        else:
            print("  📊 Loading USDA from single file")
            adapter = USDAAdapter()

        try:
            usda_data = list(adapter.normalize())
            print(f"  ✅ USDA: {len(usda_data)} records")
        except Exception as e:
            print(f"  ❌ USDA error: {e}")

        # Load OFF data (from chunks or single file)
        off_data = []
        if self.off_chunks_dir.exists() and any(self.off_chunks_dir.glob("*.csv")):
            print(f"  📊 Loading OFF chunks from {self.off_chunks_dir}")
            adapter = OFFAdapter(str(self.off_chunks_dir))
        else:
            print("  📊 Loading OFF from single file")
            adapter = OFFAdapter()

        try:
            off_data = list(adapter.normalize())
            print(f"  ✅ OFF: {len(off_data)} records")
        except Exception as e:
            print(f"  ❌ OFF error: {e}")

        return usda_data, off_data

    def merge_and_validate(
        self, usda_data: List[Dict], off_data: List[Dict]
    ) -> List[FoodItem]:
        """
        RU: Объединить данные и валидировать через Pydantic.
        EN: Merge data and validate through Pydantic.
        """
        print("🔄 Merging and validating data...")

        # Merge records (pass objects directly)
        merged_records = merge_records([usda_data, off_data])
        print(f"  📊 Merged: {len(merged_records)} unique foods")

        # Validate and convert to FoodItem
        validated_foods = []
        validation_errors = []

        for i, record in enumerate(merged_records):
            try:
                # Generate deterministic ID
                canonical_name = record.get("name", f"unknown_{i}")
                food_id = self._generate_food_id(canonical_name, record)

                # Create FoodItem with full provenance
                food_item = FoodItem(
                    id=food_id,
                    canonical_name=canonical_name,
                    group=record.get("group", "unknown"),
                    per_g=record.get("per_g", 100.0),
                    kcal=record.get("kcal", 0.0),
                    protein_g=record.get("protein_g", 0.0),
                    fat_g=record.get("fat_g", 0.0),
                    carbs_g=record.get("carbs_g", 0.0),
                    fiber_g=record.get("fiber_g", 0.0),
                    Fe_mg=record.get("Fe_mg", 0.0),
                    Ca_mg=record.get("Ca_mg", 0.0),
                    K_mg=record.get("K_mg", 0.0),
                    Mg_mg=record.get("Mg_mg", 0.0),
                    VitD_IU=record.get("VitD_IU", 0.0),
                    B12_ug=record.get("B12_ug", 0.0),
                    Folate_ug=record.get("Folate_ug", 0.0),
                    Iodine_ug=record.get("Iodine_ug", 0.0),
                    flags=record.get("flags", []),
                    brand=record.get("brand"),
                    gtin=record.get("gtin"),
                    fdc_id=record.get("fdc_id"),
                    source=record.get("source", "unknown"),
                    source_priority=record.get("source_priority", 0),
                    version_date=record.get("version_date", datetime.now().isoformat()),
                    price_per_100g=record.get("price_per_100g", 0.0),
                )
                validated_foods.append(food_item)

            except ValidationError as e:
                validation_errors.append(
                    {"index": i, "record": record, "error": str(e)}
                )

        if validation_errors:
            print(f"  ⚠️  Validation errors: {len(validation_errors)}")
            for error in validation_errors[:3]:  # Show first 3
                print(f"    - {error['error']}")

        print(f"  ✅ Validated: {len(validated_foods)} foods")
        return validated_foods

    def _generate_food_id(self, canonical_name: str, record: Dict) -> str:
        """
        RU: Генерировать детерминированный ID продукта.
        EN: Generate deterministic food ID.
        """
        # Use canonical name + source + key fields for deterministic ID
        key_data = (
            f"{canonical_name}_{record.get('source', '')}_"
            f"{record.get('fdc_id', '')}_{record.get('gtin', '')}"
        )
        return hashlib.md5(key_data.encode()).hexdigest()[:12]

    def save_parquet(self, foods: List[FoodItem]) -> None:
        """
        RU: Сохранить данные в Parquet для быстрого доступа.
        EN: Save data to Parquet for fast access.
        """
        print("🔄 Saving to Parquet...")

        # Convert to DataFrame
        data = []
        for food in foods:
            row = food.dict()
            # Convert lists to JSON strings for Parquet compatibility
            row["flags"] = json.dumps(row["flags"])
            data.append(row)

        df = pd.DataFrame(data)
        df.to_parquet(self.food_parquet, index=False)

        print(f"  ✅ Parquet saved: {self.food_parquet}")
        print(f"  📊 Records: {len(df)}")

    def save_sqlite(self, foods: List[FoodItem]) -> None:
        """
        RU: Сохранить в SQLite с FTS для поиска.
        EN: Save to SQLite with FTS for search.
        """
        print("🔄 Saving to SQLite with FTS...")

        # Remove existing database
        if self.food_sqlite.exists():
            self.food_sqlite.unlink()

        conn = sqlite3.connect(self.food_sqlite)
        cursor = conn.cursor()

        # Create main table
        cursor.execute(
            """
            CREATE TABLE foods (
                id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                group_name TEXT,
                per_g REAL,
                kcal REAL,
                protein_g REAL,
                fat_g REAL,
                carbs_g REAL,
                fiber_g REAL,
                Fe_mg REAL,
                Ca_mg REAL,
                K_mg REAL,
                Mg_mg REAL,
                VitD_IU REAL,
                B12_ug REAL,
                Folate_ug REAL,
                Iodine_ug REAL,
                flags TEXT,
                brand TEXT,
                gtin TEXT,
                fdc_id TEXT,
                source TEXT,
                source_priority INTEGER,
                version_date TEXT,
                price_per_100g REAL
            )
        """
        )

        # Create FTS table for search
        cursor.execute(
            """
            CREATE VIRTUAL TABLE foods_fts USING fts5(
                canonical_name,
                group_name,
                brand,
                flags,
                content='foods',
                content_rowid='rowid'
            )
        """
        )

        # Insert data
        for food in foods:
            cursor.execute(
                """
                INSERT INTO foods VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """,
                (
                    food.id,
                    food.canonical_name,
                    food.group,
                    food.per_g,
                    food.kcal,
                    food.protein_g,
                    food.fat_g,
                    food.carbs_g,
                    food.fiber_g,
                    food.Fe_mg,
                    food.Ca_mg,
                    food.K_mg,
                    food.Mg_mg,
                    food.VitD_IU,
                    food.B12_ug,
                    food.Folate_ug,
                    food.Iodine_ug,
                    json.dumps(food.flags),
                    food.brand,
                    food.gtin,
                    food.fdc_id,
                    food.source,
                    food.source_priority,
                    food.version_date,
                    food.price_per_100g,
                ),
            )

        # Populate FTS
        cursor.execute("INSERT INTO foods_fts(foods_fts) VALUES('rebuild')")

        # Create indexes
        cursor.execute("CREATE INDEX idx_foods_group ON foods(group_name)")
        cursor.execute("CREATE INDEX idx_foods_source ON foods(source)")
        cursor.execute("CREATE INDEX idx_foods_flags ON foods(flags)")

        conn.commit()
        conn.close()

        print(f"  ✅ SQLite saved: {self.food_sqlite}")
        print("  🔍 FTS enabled for search")

    def generate_report(
        self, foods: List[FoodItem], usda_count: int, off_count: int
    ) -> None:
        """
        RU: Сгенерировать отчет о сборке.
        EN: Generate build report.
        """
        print("🔄 Generating build report...")

        # Calculate statistics
        total_foods = len(foods)
        sources = {}
        groups = {}
        micronutrient_coverage = {}

        for food in foods:
            # Source distribution
            sources[food.source] = sources.get(food.source, 0) + 1

            # Group distribution
            groups[food.group] = groups.get(food.group, 0) + 1

            # Micronutrient coverage
            micronutrient_fields = [
                "Fe_mg",
                "Ca_mg",
                "K_mg",
                "Mg_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
            ]
            for field in micronutrient_fields:
                if getattr(food, field) > 0:
                    micronutrient_coverage[field] = (
                        micronutrient_coverage.get(field, 0) + 1
                    )

        # Calculate coverage percentages
        micronutrient_percentages = {
            field: (count / total_foods * 100) if total_foods > 0 else 0
            for field, count in micronutrient_coverage.items()
        }

        report = {
            "build_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_foods": total_foods,
                "usda_input": usda_count,
                "off_input": off_count,
                "merge_efficiency": (total_foods / max(usda_count + off_count, 1))
                * 100,
            },
            "sources": sources,
            "groups": groups,
            "micronutrient_coverage": micronutrient_percentages,
            "files": {
                "parquet": str(self.food_parquet),
                "sqlite": str(self.food_sqlite),
                "report": str(self.build_report),
            },
        }

        with open(self.build_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Report saved: {self.build_report}")

        # Print summary
        print("\n📊 BUILD SUMMARY:")
        print(f"  Total foods: {total_foods}")
        print(f"  Sources: {sources}")
        print(f"  Groups: {len(groups)}")
        print("  Micronutrient coverage:")
        for field, pct in micronutrient_percentages.items():
            print(f"    {field}: {pct:.1f}%")

    def build(self) -> None:
        """
        RU: Выполнить полную сборку базы данных.
        EN: Perform complete database build.
        """
        print("🚀 Starting food database build...")

        try:
            # Load source data
            usda_data, off_data = self.load_source_data()

            # Merge and validate
            foods = self.merge_and_validate(usda_data, off_data)

            if not foods:
                print("❌ No valid foods found!")
                return

            # Save outputs
            self.save_parquet(foods)
            self.save_sqlite(foods)

            # Generate report
            self.generate_report(foods, len(usda_data), len(off_data))

            print("✅ Build completed successfully!")

        except Exception as e:
            print(f"❌ Build failed: {e}")
            raise


def main():
    """Main entry point."""
    builder = FoodDatabaseBuilder()
    builder.build()


if __name__ == "__main__":
    main()
