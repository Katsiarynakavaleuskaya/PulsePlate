from pathlib import Path
from typing import Any, Dict, List, Optional
from types import ModuleType
import csv
import sys
import os
from importlib.machinery import ModuleSpec

import pytest
import importlib

# Load food_store module: check sys.modules first, then fall back to file loading
fs_module: Optional[ModuleType] = sys.modules.get("food_store")
if fs_module is None:
    # Build file path for the food_store module
    food_store_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "app",
        "services",
        "food_store.py",
    )
    spec: Optional[ModuleSpec] = importlib.util.spec_from_file_location(
        "food_store", food_store_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load food_store module")
    fs_module = importlib.util.module_from_spec(spec)


# Expose resolve_attr for test-friendly attribute access
def resolve_attr(name: str) -> Any:
    """Resolve attribute from food_store module for test patching."""
    return getattr(fs_module, name)


# Short alias for backward compatibility
fs: ModuleType = fs_module


def test_validate_pagination_params_limit_zero() -> None:
    """Cover line 376: limit < 1 validation."""
    with pytest.raises(ValueError, match="limit must be >= 1"):
        fs._validate_pagination_params(0, 0)


def test_validate_pagination_params_offset_negative() -> None:
    """Cover line 377: offset < 0 validation."""
    with pytest.raises(ValueError, match="offset must be >= 0"):
        fs._validate_pagination_params(1, -1)


def test_nutrients_for_with_validation_failures() -> None:
    """Cover lines 539 (continue when validation_result is None)."""
    # Empty ingredients list already covered, but ensure continue path is hit
    invalid_ings = [
        "not-a-mapping",  # Will fail validation
        {"food_id": "f1", "grams": 100},  # Valid but food not in database
    ]
    # The test intentionally includes an invalid entry ("not-a-mapping") and an unknown food_id to
    # exercise the 'continue' paths for both validation failure and food-not-found.
    result = fs.nutrients_for(invalid_ings)  # type: ignore[arg-type]
    # Should return a dict with 0.0 for all nutrients
    assert isinstance(result, dict)
    assert all(v == 0.0 for v in result.values())


def test_safe_per_g_zero_value() -> None:
    """Cover line 493: per_g == 0.0 check."""
    result = fs._safe_per_g(0.0, "test_food")
    assert result == fs.DEFAULT_PER_G


def test_validate_ingredient_mapping_negative_grams() -> None:
    """Cover line 464: grams < 0 check."""
    ing = {"food_id": "f1", "grams": -5}
    assert fs._validate_ingredient_mapping(ing) is None


def test_validate_ingredient_mapping_non_numeric_grams() -> None:
    """Cover line 460-461: ValueError in float conversion."""
    ing = {"food_id": "f1", "grams": "not-a-number"}
    assert fs._validate_ingredient_mapping(ing) is None


def test_validate_ingredient_mapping_unsupported_grams_type() -> None:
    """Cover line 452: unsupported type check."""
    ing = {"food_id": "f1", "grams": object()}
    assert fs._validate_ingredient_mapping(ing) is None


def test_validate_ingredient_mapping_blank_food_id() -> None:
    """Cover line 447: blank food_id check."""
    ing = {"food_id": "   ", "grams": 100}
    assert fs._validate_ingredient_mapping(ing) is None


def test_validate_ingredient_mapping_not_mapping() -> None:
    """Cover line 442: not isinstance(ing, Mapping) check."""
    not_a_mapping: str = "not-a-dict"
    result = fs._validate_ingredient_mapping(not_a_mapping)  # type: ignore[arg-type]
    assert result is None


def test_validate_csv_quotes_exception_in_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover lines 106,108,110-112: Exception handling in production mode."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    # Force a non-csv.Error exception during file read
    class FailingReader:
        def __iter__(self):
            raise IOError("I/O error during read")

    def reader(_: Any, *args: Any, **kwargs: Any):
        return FailingReader()

    monkeypatch.setattr("csv.reader", reader)

    # In production mode, should return False and log
    assert fs._validate_csv_quotes(csv_path, is_production=True) is False


def test_validate_csv_quotes_exception_in_dev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover line 110: Exception re-raise in non-production mode."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    class FailingReader:
        def __iter__(self):
            raise IOError("I/O error during read")

    def reader(_: Any, *args: Any, **kwargs: Any):
        return FailingReader()

    monkeypatch.setattr("csv.reader", reader)

    # In dev mode, should re-raise
    with pytest.raises(IOError):
        fs._validate_csv_quotes(csv_path, is_production=False)


def test_parse_primary_aliases_schema_empty_row() -> None:
    """Cover line 169: continue when row_values is empty or too short."""
    import csv
    from io import StringIO

    # CSV with empty row in primary/aliases format
    # Empty row will be parsed as [] by csv.reader, which triggers line 169
    csv_content = "primary,aliases\napple,Apple\n\nbanana,Banana"
    reader = csv.reader(StringIO(csv_content))
    # Function reads header itself, so don't skip it here

    result = fs._parse_primary_aliases_schema(reader)
    # Should skip empty rows and process valid ones
    # Result maps canonical (lowercase) to list of aliases (lowercase)
    assert "apple" in result
    assert "banana" in result
    # Aliases are converted to lowercase, so "Apple" becomes "apple"
    assert "apple" in result.get("apple", [])
    assert "banana" in result.get("banana", [])


def test_load_aliases_csv_alias_canonical(tmp_path: Path) -> None:
    """Ensure alias/canonical schema is parsed correctly and sorted."""
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text("alias,canonical\nKiwi,Kiwifruit\nPear,Pear\n", encoding="utf-8")

    result = fs._load_aliases_csv(csv_path, is_production=False)
    assert result == {"kiwifruit": ["kiwi"], "pear": ["pear"]}


def test_load_aliases_csv_production_error_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed CSV in production should be ignored and return empty dict."""
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text("alias,canonical\nbad,line\n", encoding="utf-8")

    monkeypatch.setattr(fs, "_validate_csv_quotes", lambda *_: True)

    class BrokenDictReader:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise csv.Error("broken csv")

    monkeypatch.setattr(fs.csv, "DictReader", BrokenDictReader)
    assert fs._load_aliases_csv(csv_path, is_production=True) == {}


def test_get_aliases_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure aliases are cached and merged with defaults."""
    monkeypatch.setattr(fs, "_ALIASES_CACHE", None, raising=False)
    monkeypatch.setattr(fs, "DEFAULT_ALIASES", {"banana": ["platano"]}, raising=False)

    calls = {"count": 0}

    def fake_load(_: Path) -> Dict[str, list[str]]:
        calls["count"] += 1
        return {"apple": ["apfel"]}

    monkeypatch.setattr(fs, "_load_aliases_csv", fake_load)
    monkeypatch.setattr(fs, "ALIASES_CSV_PATH", Path("unused.csv"), raising=False)

    first = fs.get_aliases()
    second = fs.get_aliases()
    assert calls["count"] == 1  # cache used
    assert first["banana"] == ["platano"]
    assert first["apple"] == ["apfel"]
    assert first is second  # cached dict reused


def test_expand_query_with_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expand queries using alias mapping."""
    monkeypatch.setattr(fs, "get_aliases", lambda: {"apple": ["apfel"]})
    expanded = fs.expand_query("apfel")
    assert set(expanded) == {"apple", "apfel"}
    assert fs.expand_query("   ") == []


def test_log_missing_food_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover periodic summary path in _log_missing_food."""
    fs.reset_missing_food_counter()
    monkeypatch.setattr(fs, "_MISSING_FOOD_REPORT_THRESHOLD", 2, raising=False)
    info_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(fs.logger, "info", lambda *a, **k: info_calls.append((a, k)))

    fs._log_missing_food("id-1")
    fs._log_missing_food("id-2")
    assert info_calls, "Expected summary log to be emitted"
    assert fs._MISSING_FOOD_COUNTER == {}


def test_search_foods_with_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover FTS path with dynamic SQL placeholders."""

    class FakeCursor:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def fetchall(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeConnection:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self.rows = rows
            self.executions: list[tuple[str, list[Any]]] = []

        def execute(self, sql: str, params: list[Any]) -> FakeCursor:
            self.executions.append((sql, params))
            return FakeCursor(self.rows)

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *exc_info: Any) -> None:
            return None

    rows = [
        {
            "id": "f1",
            "canonical_name": "Kiwi",
            "kcal": 61,
            "protein_g": 1.1,
            "fat_g": 0.5,
            "carbs_g": 14,
        },
    ]
    created: dict[str, Any] = {}

    def fake_connect() -> FakeConnection:
        conn = FakeConnection(rows)
        created["conn"] = conn
        return conn

    monkeypatch.setattr(fs, "_connect", fake_connect)
    monkeypatch.setattr(fs, "expand_query", lambda q: ["kiwi", "kiwifruit"])

    result = fs.search_foods("kiwi", limit="10", offset="1")
    assert result == rows
    sql, params = created["conn"].executions[0]
    assert "MATCH" in sql
    assert params[-2:] == [10, 1]


def test_search_foods_without_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover fallback path when query is empty."""

    class FakeCursor:
        def __init__(self) -> None:
            self._rows = [
                {
                    "id": "f1",
                    "canonical_name": "Kiwi",
                    "kcal": 60,
                    "protein_g": 1.0,
                    "fat_g": 0.4,
                    "carbs_g": 14,
                }
            ]

        def fetchall(self) -> list[dict[str, Any]]:
            return self._rows

    class FakeConnection:
        def execute(self, sql: str, params: list[Any]) -> FakeCursor:
            assert "MATCH" not in sql
            assert params == [5, 0]
            return FakeCursor()

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *exc: Any) -> None:
            return None

    monkeypatch.setattr(fs, "_connect", lambda: FakeConnection())
    result = fs.search_foods("", limit=5, offset=0)
    assert result[0]["canonical_name"] == "Kiwi"


def test_get_food_uses_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover get_food happy path and None return."""

    class FakeCursor:
        def __init__(self, row: dict[str, Any] | None) -> None:
            self._row = row

        def fetchone(self) -> dict[str, Any] | None:
            return self._row

    class FakeConnection:
        def __init__(self, expected_id: str, row: dict[str, Any] | None) -> None:
            self.expected_id = expected_id
            self._row = row
            self.calls: list[tuple[str, ...]] = []

        def execute(self, sql: str, params: tuple[str, ...]) -> FakeCursor:
            self.calls.append(params)
            assert params == (self.expected_id,)
            return FakeCursor(self._row)

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *exc: Any) -> None:
            return None

    monkeypatch.setattr(fs, "_connect", lambda: FakeConnection("f1", {"id": "f1"}))
    assert fs.get_food("f1") == {"id": "f1"}
    monkeypatch.setattr(fs, "_connect", lambda: FakeConnection("f2", None))
    assert fs.get_food("f2") is None


def test_nutrients_for_valid_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover successful aggregation path in nutrients_for."""
    monkeypatch.setattr(
        fs,
        "get_food",
        lambda food_id: {
            "kcal": 100.0,
            "protein_g": 10.0,
            "fat_g": 1.0,
            "carbs_g": 20.0,
            "per_g": 50,
        },
    )
    result = fs.nutrients_for([{"food_id": "abc", "grams": 100}])
    assert result["kcal"] == pytest.approx(200.0)
    assert result["protein_g"] == pytest.approx(20.0)


def test_safe_per_g_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover invalid per_g conversion fallback."""
    assert fs._safe_per_g("not-a-number", "f1") == fs.DEFAULT_PER_G
