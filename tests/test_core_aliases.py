from pathlib import Path

import pytest

from core import aliases


def test_load_aliases_schema_one(tmp_path: Path) -> None:
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text("alias,canonical\nleche,Milk\n", encoding="utf-8")

    table = aliases._load_aliases(str(csv_path))
    assert table == {"leche": "Milk"}


def test_load_aliases_schema_two(tmp_path: Path) -> None:
    csv_path = tmp_path / "aliases2.csv"
    csv_path.write_text("primary,aliases\nTomato,tomate;tomatoes\n", encoding="utf-8")

    table = aliases._load_aliases(str(csv_path))
    assert table["tomate"] == "Tomato"
    assert table["tomato"] == "Tomato"


def test_load_aliases_handles_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    assert aliases._load_aliases(str(missing)) == {}


def test_map_to_canonical_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aliases, "_load_aliases", lambda path=None: {"leche": "Milk"})
    assert aliases.map_to_canonical("leche") == "Milk"
    assert aliases.map_to_canonical(" Fresh Apple ") == "fresh_apple"
