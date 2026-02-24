import csv
import logging
from pathlib import Path
from typing import Any, Dict, List

import pytest

from app.services import food_store


def test_validate_csv_quotes_valid(tmp_path: Path) -> None:
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text("alias,canonical\nleche,Milk\n", encoding="utf-8")

    assert food_store._validate_csv_quotes(csv_path, is_production=False) is True


def test_validate_csv_quotes_unbalanced_dev(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    # Odd number of quotes triggers imbalance detection
    csv_path.write_text('alias,canonical\n"leche,MILK\n', encoding="utf-8")

    with pytest.raises(csv.Error):
        food_store._validate_csv_quotes(csv_path, is_production=False)


def test_validate_csv_quotes_unbalanced_production(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text('alias,canonical\n"leche,MILK\n', encoding="utf-8")

    assert food_store._validate_csv_quotes(csv_path, is_production=True) is False


def test_load_aliases_csv_alias_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text("alias,canonical\nleche,Milk\n", encoding="utf-8")

    result = food_store._load_aliases_csv(csv_path)
    assert result == {"milk": ["leche"]}


def test_load_aliases_csv_primary_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    csv_path = tmp_path / "primary.csv"
    # Mix commas and semicolons to exercise custom splitting logic
    csv_path.write_text("primary,aliases\nTomato,tomate;tomatoes,Tomate\n", encoding="utf-8")

    result = food_store._load_aliases_csv(csv_path)
    assert result == {"tomato": ["tomate", "tomatoes"]}


def test_load_aliases_csv_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    missing_path = tmp_path / "does_not_exist.csv"
    assert food_store._load_aliases_csv(missing_path) == {}


def test_load_aliases_csv_parse_error_behaviour(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = tmp_path / "aliases.csv"
    csv_path.write_text("alias,canonical\nmilk,Milk\n", encoding="utf-8")

    def boom(path: Path, is_production: bool) -> bool:
        raise csv.Error("bad csv")

    # Development mode should re-raise the csv.Error
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr(food_store, "_validate_csv_quotes", boom)
    with pytest.raises(csv.Error):
        food_store._load_aliases_csv(csv_path)

    # Production mode should swallow the error and return empty mapping
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(food_store, "_validate_csv_quotes", boom)
    assert food_store._load_aliases_csv(csv_path) == {}


def test_log_missing_food_summary(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(food_store, "_MISSING_FOOD_REPORT_THRESHOLD", 2)
    food_store.reset_missing_food_counter()

    with caplog.at_level(logging.INFO):
        food_store._log_missing_food("apple")
        assert "missing food summary" not in caplog.text
        food_store._log_missing_food("banana")

    assert "missing food summary" in caplog.text
    food_store.reset_missing_food_counter()


class _DummyCursor:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows

    def fetchall(self) -> List[Dict[str, Any]]:
        return self._rows


class _DummyConn:
    def __init__(self) -> None:
        self.last_sql: str | None = None
        self.last_params: List[Any] | None = None

    def execute(self, sql: str, params: List[Any]) -> _DummyCursor:
        self.last_sql = sql
        self.last_params = params
        return _DummyCursor([{"id": 1, "canonical_name": "apple", "kcal": 10.0}])

    def __enter__(self) -> "_DummyConn":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _DummyBarcodeCursor:
    def __init__(self, row: Dict[str, Any] | None) -> None:
        self._row = row

    def fetchone(self) -> Dict[str, Any] | None:
        return self._row


class _DummyBarcodeConn:
    def __init__(self, rows_by_barcode: Dict[str, Dict[str, Any] | None]) -> None:
        self.rows_by_barcode = rows_by_barcode
        self.calls: List[str] = []

    def execute(self, sql: str, params: tuple[str]) -> _DummyBarcodeCursor:
        assert "WHERE gtin = ?" in sql
        barcode = params[0]
        self.calls.append(barcode)
        return _DummyBarcodeCursor(self.rows_by_barcode.get(barcode))

    def __enter__(self) -> "_DummyBarcodeConn":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_search_foods_parameter_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = _DummyConn()
    monkeypatch.setattr(food_store, "_connect", lambda: dummy)

    rows = food_store.search_foods("apple", limit="5", offset="1")
    assert rows and rows[0]["canonical_name"] == "apple"
    assert dummy.last_params[-2:] == [5, 1]


def test_get_food_by_barcode_returns_row_with_normalized_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={"00012345678905": {"id": "f1", "canonical_name": "apple"}}
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode(" 00012345678905 ")

    assert result == {"id": "f1", "canonical_name": "apple"}
    assert conn.calls == ["00012345678905"]


def test_get_food_by_barcode_uses_leading_zero_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={
            "0123456789012": None,
            "123456789012": {"id": "f2", "canonical_name": "banana"},
        }
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("0123456789012")

    assert result == {"id": "f2", "canonical_name": "banana"}
    assert conn.calls == ["0123456789012", "123456789012"]


def test_get_food_by_barcode_validation_error() -> None:
    with pytest.raises(ValueError, match=r"barcode must have length in \[8,14\]"):
        food_store.get_food_by_barcode("123")


def test_get_food_by_barcode_validation_error_when_no_digits() -> None:
    with pytest.raises(ValueError, match="barcode must contain at least one digit"):
        food_store.get_food_by_barcode("abc-def")


def test_get_food_by_barcode_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _DummyBarcodeConn(rows_by_barcode={})
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("1234567890123")

    assert result is None
    assert conn.calls == ["1234567890123"]


def test_get_search_backend_defaults_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, tuple[Any, Any, Any]] = {}

    def fake_legacy_search(query: str, limit: Any = 20, offset: Any = 0) -> List[Dict[str, Any]]:
        called["params"] = (query, limit, offset)
        return [{"id": "legacy"}]

    monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
    monkeypatch.setattr(food_store, "search_foods", fake_legacy_search)
    food_store.reset_search_backend_adapter()

    backend = food_store.get_search_backend()
    rows = backend.search_foods("apple", limit=7, offset=3)

    assert rows == [{"id": "legacy"}]
    assert called["params"] == ("apple", 7, 3)


def test_get_search_backend_uses_registered_adapter_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _StubBackend:
        def __init__(self) -> None:
            self.calls: List[tuple[str, Any, Any]] = []

        def search_foods(
            self, query: str, limit: Any = 20, offset: Any = 0
        ) -> List[Dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [{"id": "compat"}]

    stub = _StubBackend()
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", "true")
    food_store.register_search_backend_adapter(stub)
    try:
        backend = food_store.get_search_backend()
        rows = backend.search_foods("banana", limit=5, offset=1)
        assert rows == [{"id": "compat"}]
        assert stub.calls == [("banana", 5, 1)]
    finally:
        food_store.reset_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)


@pytest.mark.parametrize(
    "limit,offset,expected_message",
    [
        ("bad", 0, "limit must be an integer"),
        (0, 0, "limit must be >= 1"),
        (1, "-1", "offset must be >= 0"),
    ],
)
def test_search_foods_validation_errors(
    limit: Any, offset: Any, expected_message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(food_store, "_connect", lambda: _DummyConn())

    with pytest.raises(ValueError) as excinfo:
        food_store.search_foods("apple", limit=limit, offset=offset)
    assert expected_message in str(excinfo.value)


def test_nutrients_for_handles_missing_and_per_g(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(food_store, "_MISSING_FOOD_REPORT_THRESHOLD", 100)
    food_store.reset_missing_food_counter()

    def fake_get_food(food_id: str) -> Dict[str, Any] | None:
        if food_id == "missing":
            return None
        return {
            "per_g": 0,  # triggers DEFAULT_PER_G fallback
            "kcal": 10,
            "protein_g": 5,
        }

    monkeypatch.setattr(food_store, "get_food", fake_get_food)

    ingredients = [
        {"food_id": "missing", "grams": 50},
        {"food_id": "found", "grams": 100},
    ]

    totals = food_store.nutrients_for(ingredients)
    # Missing food contributes nothing, found food uses DEFAULT_PER_G fallback
    assert totals["kcal"] > 0
    assert totals["protein_g"] > 0


def test_db_directory_creation_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import importlib
    import sys

    module_name = "app.services.food_store"
    sys.modules.pop(module_name, None)

    monkeypatch.setenv("FOOD_DB_PATH", str(tmp_path / "nested" / "db.sqlite"))

    original_mkdir = Path.mkdir

    def boom(self: Path, *args: Any, **kwargs: Any) -> None:
        raise OSError("nope")

    monkeypatch.setattr(Path, "mkdir", boom, raising=False)

    with pytest.raises(RuntimeError):
        importlib.import_module(module_name)

    monkeypatch.setattr(Path, "mkdir", original_mkdir, raising=False)
    sys.modules.pop(module_name, None)
    monkeypatch.delenv("FOOD_DB_PATH", raising=False)
    importlib.import_module(module_name)
