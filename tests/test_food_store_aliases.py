import tempfile
from pathlib import Path
import os
import importlib.util

import pytest

# Load food_store module directly to avoid conflicts
spec = importlib.util.spec_from_file_location(
    "food_store",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services", "food_store.py"),
)
if spec is None or spec.loader is None:
    raise ImportError("Cannot load food_store module")
fs_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs_module)
fs = fs_module


def test_get_aliases_merges_defaults_and_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reset lazy cache
    monkeypatch.setattr(fs, "_ALIASES_CACHE", None, raising=False)
    # Provide fake CSV aliases
    monkeypatch.setattr(
        fs, "_load_aliases_csv", lambda p: {"йогурт": ["joghurt"], "avocado": ["avo"]}
    )
    aliases = fs.get_aliases()
    # default key preserved (CSV overrides take precedence for same key)
    assert aliases.get("йогурт") == ["joghurt"]
    # another default key remains
    assert "масло оливковое" in aliases
    # new key from CSV present
    assert aliases.get("avocado") == ["avo"]


def test_expand_query_uses_alias_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fs, "_ALIASES_CACHE", None, raising=False)
    monkeypatch.setattr(fs, "_load_aliases_csv", lambda p: {"масло оливковое": ["olive oil"]})
    terms = set(fs.expand_query("olive oil"))
    # Should include both the alias and the canonical key
    assert {"olive oil", "масло оливковое"}.issubset(terms)


def test_load_aliases_csv_primary_aliases_schema() -> None:
    """Test _load_aliases_csv with primary,aliases schema (original format)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("primary,aliases\n")
        f.write("apple,apples,red apple\n")
        f.write("banana,bananas,yellow fruit\n")
        f.write("cherry,cherries\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert result["apple"] == ["apples", "red apple"]
        assert result["banana"] == ["bananas", "yellow fruit"]
        assert result["cherry"] == ["cherries"]
    finally:
        temp_path.unlink()


def test_load_aliases_csv_alias_canonical_schema() -> None:
    """Test _load_aliases_csv with alias,canonical schema (core.aliases format)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("alias,canonical\n")
        f.write("apples,apple\n")
        f.write("red apple,apple\n")
        f.write("bananas,banana\n")
        f.write("yellow fruit,banana\n")
        f.write("cherries,cherry\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        # Multiple aliases should be grouped under the same canonical
        assert "apple" in result
        assert set(result["apple"]) == {"apples", "red apple"}
        assert "banana" in result
        assert set(result["banana"]) == {"bananas", "yellow fruit"}
        assert result["cherry"] == ["cherries"]
        # Lists should be sorted
        assert result["apple"] == sorted(result["apple"])
    finally:
        temp_path.unlink()


def test_load_aliases_csv_missing_file() -> None:
    """Test _load_aliases_csv when file doesn't exist."""
    non_existent = Path("/non/existent/path.csv")
    result = fs._load_aliases_csv(non_existent)
    assert result == {}


def test_load_aliases_csv_empty_file() -> None:
    """Test _load_aliases_csv with empty CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("primary,aliases\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert result == {}
    finally:
        temp_path.unlink()


def test_load_aliases_csv_primary_aliases_with_duplicates() -> None:
    """Test _load_aliases_csv with primary,aliases schema handling duplicate aliases."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("primary,aliases\n")
        f.write("apple,apples,red apple\n")
        f.write("apple,apples,green apple\n")  # Duplicate primary, different aliases
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        # Should merge aliases and remove duplicates
        assert "apple" in result
        assert set(result["apple"]) == {"apples", "red apple", "green apple"}
        assert result["apple"] == sorted(result["apple"])
    finally:
        temp_path.unlink()


def test_load_aliases_csv_alias_canonical_with_whitespace() -> None:
    """Test _load_aliases_csv with alias,canonical schema handling whitespace."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("alias,canonical\n")
        f.write("  apples  ,  apple  \n")
        f.write("red apple,apple\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert "apple" in result
        assert "apples" in result["apple"]
        assert "red apple" in result["apple"]
    finally:
        temp_path.unlink()


def test_load_aliases_csv_primary_aliases_case_insensitive() -> None:
    """Test _load_aliases_csv normalizes to lowercase for primary,aliases schema."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("primary,aliases\n")
        f.write("Apple,Apples,Red Apple\n")
        f.write("BANANA,bananas\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert "apple" in result
        assert "apples" in result["apple"]
        assert "red apple" in result["apple"]
        assert "banana" in result
        assert "bananas" in result["banana"]
    finally:
        temp_path.unlink()


def test_load_aliases_csv_alias_canonical_case_insensitive() -> None:
    """Test _load_aliases_csv normalizes to lowercase for alias,canonical schema."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("alias,canonical\n")
        f.write("Apples,Apple\n")
        f.write("RED APPLE,Apple\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert "apple" in result
        assert "apples" in result["apple"]
        assert "red apple" in result["apple"]
    finally:
        temp_path.unlink()


def test_load_aliases_csv_primary_aliases_empty_primary_skipped() -> None:
    """Test _load_aliases_csv skips rows with empty primary in primary,aliases schema."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("primary,aliases\n")
        f.write("apple,apples\n")
        f.write(",empty primary\n")
        f.write("banana,bananas\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert "apple" in result
        assert "banana" in result
        assert "" not in result
    finally:
        temp_path.unlink()


def test_load_aliases_csv_alias_canonical_empty_values_skipped() -> None:
    """Test _load_aliases_csv skips rows with empty alias or canonical."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("alias,canonical\n")
        f.write("apples,apple\n")
        f.write(",empty alias\n")
        f.write("empty canonical,\n")
        f.write("bananas,banana\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert "apple" in result
        assert "banana" in result
        assert "" not in result
    finally:
        temp_path.unlink()


def test_load_aliases_csv_unknown_schema_returns_empty() -> None:
    """Test _load_aliases_csv returns empty dict when schema doesn't match."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("unknown,col1\n")
        f.write("value1,value2\n")
        temp_path = Path(f.name)

    try:
        result = fs._load_aliases_csv(temp_path)
        assert result == {}
    finally:
        temp_path.unlink()


def test_load_aliases_csv_error_handling_production_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _load_aliases_csv error handling in production mode returns empty dict."""
    # Create a file that will cause a parse error
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        # Write invalid CSV that will cause parsing error
        f.write("primary,aliases\n")
        f.write('apple,"unclosed quote\n')  # Malformed CSV
        temp_path = Path(f.name)

    try:
        # In production, should return empty dict on error
        result = fs._load_aliases_csv(temp_path, is_production=True)
        assert result == {}
    finally:
        temp_path.unlink()


def test_load_aliases_csv_error_handling_non_production_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _load_aliases_csv error handling in non-production mode raises exception."""
    # Create a file that will cause a parse error
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        # Write invalid CSV that will cause parsing error
        f.write("primary,aliases\n")
        f.write('apple,"unclosed quote\n')  # Malformed CSV
        temp_path = Path(f.name)

    try:
        # In non-production, should raise exception
        import csv

        with pytest.raises((csv.Error, OSError)):
            fs._load_aliases_csv(temp_path, is_production=False)
    finally:
        temp_path.unlink()
