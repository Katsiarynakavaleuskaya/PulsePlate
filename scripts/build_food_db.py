#!/usr/bin/env python3
"""
Build Food Database Script

RU: CLI: построить итоговый data/food_db.csv.
EN: CLI: build final merged CSV.
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

import csv  # noqa: E402
import json  # noqa: E402
from datetime import datetime  # noqa: E402

# from core.food_sources.ciqual import CIQUALAdapter  # Optional
from core.food_merge import merge_records  # noqa: E402
from core.food_sources.off import OFFAdapter  # noqa: E402
from core.food_sources.usda import USDAAdapter  # noqa: E402


def main():
    """Main function to build the food database."""
    print("Building food database...")

    # Define paths
    usda_path = os.path.join(project_root, "external", "usda_fdc_sample.csv")
    off_path = os.path.join(project_root, "external", "off_products_sample.csv")
    output_path = os.path.join(project_root, "data", "food_db.csv")
    report_path = os.path.join(project_root, "data", "food_merge_report.json")

    # Check if source files exist
    if not os.path.exists(usda_path):
        print(f"Warning: USDA file not found at {usda_path}")
        print("Please download USDA FDC data and place it at this location.")
        # Create empty adapter for testing
        usda_records = []
    else:
        print(f"Loading USDA data from {usda_path}")
        usda_adapter = USDAAdapter(csv_path=usda_path)
        usda_records = list(usda_adapter.normalize())
        print(f"Loaded {len(usda_records)} records from USDA")

    if not os.path.exists(off_path):
        print(f"Warning: OFF file not found at {off_path}")
        print("Please download Open Food Facts data and place it at this location.")
        # Create empty adapter for testing
        off_records = []
    else:
        print(f"Loading OFF data from {off_path}")
        off_adapter = OFFAdapter(csv_path=off_path, locale="en")
        off_records = list(off_adapter.normalize())
        print(f"Loaded {len(off_records)} records from OFF")

    # Merge records
    print("Merging records...")
    merged = merge_records(
        [usda_records, off_records]
    )  # Add ciqual_records if available
    print(f"Merged into {len(merged)} unique food items")

    # Write to CSV
    print(f"Writing to {output_path}")
    fieldnames = [
        "name",
        "group",
        "per_g",
        "kcal",
        "protein_g",
        "fat_g",
        "carbs_g",
        "fiber_g",
        "Fe_mg",
        "Ca_mg",
        "VitD_IU",
        "B12_ug",
        "Folate_ug",
        "Iodine_ug",
        "K_mg",
        "Mg_mg",
        "flags",
        "price",
        "source",
        "version_date",
    ]

    # Write to temporary file first
    temp_path = output_path + ".tmp"
    with open(temp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in merged:
            # Convert flags list to string
            row_copy = row.copy()
            if isinstance(row_copy["flags"], list):
                row_copy["flags"] = ";".join(row_copy["flags"])
            writer.writerow(row_copy)

    # Atomically replace the file
    os.replace(temp_path, output_path)
    print(f"Food database written to {output_path}")

    # Generate merge report
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_items": len(merged),
        "sources": ["USDA", "OFF"],  # Add "CIQUAL" if available
        "merge_stats": {
            "usda_records": len(usda_records),
            "off_records": len(off_records),
            # "ciqual_records": len(ciqual_records) if 'ciqual_records' in locals() else 0
        },
        "food_groups": {},
        "top_foods_by_nutrient": {},
    }

    # Count foods by group
    for item in merged:
        group = item["group"]
        report["food_groups"][group] = report["food_groups"].get(group, 0) + 1

    # Find top foods by key nutrients
    top_nutrients = ["protein_g", "fat_g", "carbs_g", "fiber_g", "Fe_mg", "Ca_mg"]
    for nutrient in top_nutrients:
        sorted_foods = sorted(merged, key=lambda x: x.get(nutrient, 0), reverse=True)[
            :5
        ]
        report["top_foods_by_nutrient"][nutrient] = [
            {"name": food["name"], "value": food[nutrient]} for food in sorted_foods
        ]

    # Write report
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Merge report written to {report_path}")
    print("Food database build complete!")


if __name__ == "__main__":
    main()
