from __future__ import annotations

from pathlib import Path

import pytest

from core.shoplist import ShoplistGenerator


def test_packaging_rules_fallback_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad_csv = tmp_path / "rules.csv"
    bad_csv.write_text("category,typical_packages\nfruit,not_a_number\n", encoding="utf-8")
    generator = ShoplistGenerator(packaging_rules_file=str(bad_csv))
    assert "default" in generator.packaging_rules


def test_find_best_package_handles_non_positive_values() -> None:
    generator = ShoplistGenerator(packaging_rules_file="nonexistent.csv")
    amount, packages = generator._find_best_package(500, [0, -10], "up")
    assert amount == 500
    assert packages == 1
