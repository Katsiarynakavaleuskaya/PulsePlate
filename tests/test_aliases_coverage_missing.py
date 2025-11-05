"""Tests for missing coverage lines in core/aliases.py."""

import csv
import types
import os
from pathlib import Path
from typing import Any

import pytest

from core import aliases


def test_load_aliases_unmatched_schema(tmp_path: Path) -> None:
    """Cover line 72: warning when CSV headers don't match expected schemas."""
    alias_file = tmp_path / "aliases.csv"
    # Create CSV with unexpected headers
    alias_file.write_text("wrong,headers\nvalue1,value2\n", encoding="utf-8")

    # Clear cache to force reload
    aliases.clear_alias_cache()

    # Load aliases - should log warning and return empty dict
    result = aliases._load_aliases(str(alias_file))
    assert result == {}


def test_load_aliases_csv_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover lines 81, 83: handle csv.Error during file loading."""
    alias_file = tmp_path / "aliases.csv"
    alias_file.write_text("alias,canonical\ninvalid,csv\n", encoding="utf-8")

    # Mock csv.DictReader to raise csv.Error
    class FailingDictReader(csv.DictReader):
        def __next__(self) -> dict[str, Any]:
            raise csv.Error("Malformed CSV")

    monkeypatch.setattr(csv, "DictReader", FailingDictReader)

    # Clear cache to force reload
    aliases.clear_alias_cache()

    # Load aliases - should handle csv.Error gracefully and return empty dict
    result = aliases._load_aliases(str(alias_file))
    assert result == {}


def test_load_aliases_unicode_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover lines 81, 83: handle UnicodeDecodeError during file loading."""
    alias_file = tmp_path / "aliases.csv"
    # Write file with invalid UTF-8 encoding
    alias_file.write_bytes(b"alias,canonical\n\xff\xfe\x00invalid\n")

    # Clear cache to force reload
    aliases.clear_alias_cache()

    # Load aliases - should handle UnicodeDecodeError gracefully and return empty dict
    result = aliases._load_aliases(str(alias_file))
    assert result == {}
