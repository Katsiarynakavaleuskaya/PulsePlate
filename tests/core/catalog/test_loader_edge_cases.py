# -*- coding: utf-8 -*-
"""
Edge case tests for catalog loaders (PR-7).

RU: Тесты для edge cases в loaders (пропуск строк, пустые значения).
EN: Edge case tests for loaders (skipping rows, empty values).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from core.catalog.loaders.carrefour_es import CarrefourESLoader
from core.catalog.loaders.walmart_us import WalmartUSLoader


class TestCarrefourESLoaderEdgeCases:
    """Edge case tests for CarrefourESLoader."""

    def test_loader_skips_rows_with_wrong_region_id(self, tmp_path: Path) -> None:
        """Test that loader skips rows with region_id != ES."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "US",  # Wrong region
                    "store_id": "carrefour_es_main",
                    "alias": "milk",
                    "name": "Milk",
                    "price": "2.99",
                    "currency": "EUR",
                }
            )
            writer.writerow(
                {
                    "region_id": "ES",  # Correct region
                    "store_id": "carrefour_es_main",
                    "alias": "bread",
                    "name": "Bread",
                    "price": "1.50",
                    "currency": "EUR",
                }
            )

        loader = CarrefourESLoader(csv_path)
        snapshot = loader.load()

        # Should only have ES row
        assert len(snapshot.skus) == 1
        assert snapshot.skus[0].name == "Bread"

    def test_loader_skips_rows_with_empty_alias(self, tmp_path: Path) -> None:
        """Test that loader skips rows with empty alias (and no ean/name fallback)."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "ean",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "ES",
                    "store_id": "carrefour_es_main",
                    "alias": "",  # Empty alias
                    "ean": "",  # Empty ean
                    "name": "",  # Empty name (no fallback)
                    "price": "1.00",
                    "currency": "EUR",
                }
            )
            writer.writerow(
                {
                    "region_id": "ES",
                    "store_id": "carrefour_es_main",
                    "alias": "valid_alias",
                    "ean": "",
                    "name": "Valid Product",
                    "price": "2.00",
                    "currency": "EUR",
                }
            )

        loader = CarrefourESLoader(csv_path)
        snapshot = loader.load()

        # Should only have row with valid alias
        assert len(snapshot.skus) == 1
        assert snapshot.skus[0].name == "Valid Product"

    def test_loader_skips_rows_with_empty_name(self, tmp_path: Path) -> None:
        """Test that loader skips rows with empty name."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "ES",
                    "store_id": "carrefour_es_main",
                    "alias": "product_alias",
                    "name": "",  # Empty name
                    "price": "1.00",
                    "currency": "EUR",
                }
            )
            writer.writerow(
                {
                    "region_id": "ES",
                    "store_id": "carrefour_es_main",
                    "alias": "valid_alias",
                    "name": "Valid Name",
                    "price": "2.00",
                    "currency": "EUR",
                }
            )

        loader = CarrefourESLoader(csv_path)
        snapshot = loader.load()

        # Should only have row with valid name
        assert len(snapshot.skus) == 1
        assert snapshot.skus[0].name == "Valid Name"

    def test_loader_deduplicates_aliases(self, tmp_path: Path) -> None:
        """Test that loader deduplicates aliases (only first occurrence kept)."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "ES",
                    "store_id": "carrefour_es_main",
                    "alias": "duplicate",
                    "name": "First Product",
                    "price": "1.00",
                    "currency": "EUR",
                }
            )
            writer.writerow(
                {
                    "region_id": "ES",
                    "store_id": "carrefour_es_main",
                    "alias": "duplicate",  # Duplicate alias
                    "name": "Second Product",
                    "price": "2.00",
                    "currency": "EUR",
                }
            )

        loader = CarrefourESLoader(csv_path)
        snapshot = loader.load()

        # Should have 2 SKUs but only 1 alias (deduplicated)
        assert len(snapshot.skus) == 2
        assert len(snapshot.aliases) == 1
        assert snapshot.aliases[0][0] == "duplicate"
        # First SKU should be linked to alias
        assert snapshot.aliases[0][1] == snapshot.skus[0].sku_id


class TestWalmartUSLoaderEdgeCases:
    """Edge case tests for WalmartUSLoader."""

    def test_loader_skips_rows_with_wrong_region_id(self, tmp_path: Path) -> None:
        """Test that loader skips rows with region_id != US."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "ES",  # Wrong region
                    "store_id": "walmart_us_main",
                    "alias": "milk",
                    "name": "Milk",
                    "price": "2.99",
                    "currency": "USD",
                }
            )
            writer.writerow(
                {
                    "region_id": "US",  # Correct region
                    "store_id": "walmart_us_main",
                    "alias": "bread",
                    "name": "Bread",
                    "price": "1.50",
                    "currency": "USD",
                }
            )

        loader = WalmartUSLoader(csv_path)
        snapshot = loader.load()

        # Should only have US row
        assert len(snapshot.skus) == 1
        assert snapshot.skus[0].name == "Bread"

    def test_loader_skips_rows_with_empty_alias(self, tmp_path: Path) -> None:
        """Test that loader skips rows with empty alias (and no ean/name fallback)."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "ean",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "US",
                    "store_id": "walmart_us_main",
                    "alias": "",  # Empty alias
                    "ean": "",  # Empty ean
                    "name": "",  # Empty name (no fallback)
                    "price": "1.00",
                    "currency": "USD",
                }
            )
            writer.writerow(
                {
                    "region_id": "US",
                    "store_id": "walmart_us_main",
                    "alias": "valid_alias",
                    "ean": "",
                    "name": "Valid Product",
                    "price": "2.00",
                    "currency": "USD",
                }
            )

        loader = WalmartUSLoader(csv_path)
        snapshot = loader.load()

        # Should only have row with valid alias
        assert len(snapshot.skus) == 1
        assert snapshot.skus[0].name == "Valid Product"

    def test_loader_skips_rows_with_empty_name(self, tmp_path: Path) -> None:
        """Test that loader skips rows with empty name."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "US",
                    "store_id": "walmart_us_main",
                    "alias": "product_alias",
                    "name": "",  # Empty name
                    "price": "1.00",
                    "currency": "USD",
                }
            )
            writer.writerow(
                {
                    "region_id": "US",
                    "store_id": "walmart_us_main",
                    "alias": "valid_alias",
                    "name": "Valid Name",
                    "price": "2.00",
                    "currency": "USD",
                }
            )

        loader = WalmartUSLoader(csv_path)
        snapshot = loader.load()

        # Should only have row with valid name
        assert len(snapshot.skus) == 1
        assert snapshot.skus[0].name == "Valid Name"

    def test_loader_deduplicates_aliases(self, tmp_path: Path) -> None:
        """Test that loader deduplicates aliases (only first occurrence kept)."""
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "region_id",
                    "store_id",
                    "alias",
                    "name",
                    "price",
                    "currency",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "region_id": "US",
                    "store_id": "walmart_us_main",
                    "alias": "duplicate",
                    "name": "First Product",
                    "price": "1.00",
                    "currency": "USD",
                }
            )
            writer.writerow(
                {
                    "region_id": "US",
                    "store_id": "walmart_us_main",
                    "alias": "duplicate",  # Duplicate alias
                    "name": "Second Product",
                    "price": "2.00",
                    "currency": "USD",
                }
            )

        loader = WalmartUSLoader(csv_path)
        snapshot = loader.load()

        # Should have 2 SKUs but only 1 alias (deduplicated)
        assert len(snapshot.skus) == 2
        assert len(snapshot.aliases) == 1
        assert snapshot.aliases[0][0] == "duplicate"
        # First SKU should be linked to alias
        assert snapshot.aliases[0][1] == snapshot.skus[0].sku_id
