import csv
import logging
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List

import pytest

from app.services import food_store

_LEGACY_ROW_ADDITIVE_DEFAULTS: Dict[str, Any] = {
    "nutrition_inputs": [],
    "nutrition_provenance": {},
    "nutrition_confidence": 0.0,
    "nutrition_nutrient_confidence": {},
}


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
    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows

    def fetchall(self) -> List[Any]:
        return self._rows


class _DummyConn:
    def __init__(self) -> None:
        self.last_sql: str | None = None
        self.last_params: List[Any] | None = None

    def execute(self, sql: str, params: Any = None) -> _DummyCursor:
        self.last_sql = sql
        if "PRAGMA table_info(foods)" in sql:
            pragma_rows: List[Any] = [
                (0, "id", "TEXT", 0, None, 0),
                (1, "nutrition_confidence", "REAL", 0, None, 0),
            ]
            return _DummyCursor(pragma_rows)
        self.last_params = list(params) if params is not None else []
        return _DummyCursor([{"id": 1, "canonical_name": "apple", "kcal": 10.0}])

    def __enter__(self) -> "_DummyConn":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None


def test_search_foods_parameter_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    food_store.reset_foods_nutrition_confidence_column_cache()
    dummy = _DummyConn()
    monkeypatch.setattr(food_store, "_connect", lambda: dummy)

    rows = food_store.search_foods("apple", limit="5", offset="1")
    assert rows and rows[0]["canonical_name"] == "apple"
    assert dummy.last_params[-2:] == [5, 1]


def test_normalize_food_row_parses_additive_nutrition_metadata() -> None:
    row = {
        "id": "food-1",
        "canonical_name": "apple",
        "nutrition_inputs_json": '[{"source":"estimate","record_id":"off-1"}]',
        "nutrition_provenance_json": '{"protein_g":"estimate"}',
        "nutrition_confidence": 0.4,
    }

    normalized = food_store._normalize_food_row(row)

    assert normalized["nutrition_inputs"][0]["source"] == "estimate"
    assert normalized["nutrition_provenance"]["protein_g"] == "estimate"
    assert normalized["nutrition_confidence"] == 0.4


def test_normalize_food_row_handles_invalid_json_and_none_confidence() -> None:
    row = {
        "id": "food-2",
        "nutrition_inputs_json": "not-json",
        "nutrition_provenance_json": "not-json",
        "nutrition_confidence": None,
    }

    normalized = food_store._normalize_food_row(row)

    assert normalized["nutrition_inputs"] == []
    assert normalized["nutrition_provenance"] == {}
    assert normalized["nutrition_confidence"] == 0.0


def test_normalize_food_row_ignores_non_list_or_non_dict_payloads() -> None:
    row = {
        "id": "food-3",
        "nutrition_inputs_json": '{"source":"estimate"}',
        "nutrition_provenance_json": '["bad"]',
    }

    normalized = food_store._normalize_food_row(row)

    assert normalized["nutrition_inputs"] == []
    assert normalized["nutrition_provenance"] == {}


def test_normalize_food_row_legacy_shape_without_additive_columns() -> None:
    row = {"id": "food-legacy", "canonical_name": "milk", "kcal": 42.0}

    normalized = food_store._normalize_food_row(row)

    assert normalized["nutrition_inputs"] == []
    assert normalized["nutrition_provenance"] == {}
    assert normalized["nutrition_confidence"] == 0.0
    assert normalized["nutrition_nutrient_confidence"] == {}


def test_normalize_food_row_parses_nutrition_nutrient_confidence_json() -> None:
    row = {
        "id": "food-nc",
        "canonical_name": "oats",
        "nutrition_nutrient_confidence_json": '{"kcal":"0.7","protein_g":0.9}',
    }
    out = food_store._normalize_food_row(row)
    assert out["nutrition_nutrient_confidence"]["kcal"] == pytest.approx(0.7)
    assert out["nutrition_nutrient_confidence"]["protein_g"] == pytest.approx(0.9)


def test_normalize_food_row_nutrient_confidence_from_mapping_not_json_string() -> None:
    row = {
        "id": "food-nc-dict",
        "canonical_name": "tofu",
        "nutrition_nutrient_confidence_json": {"fat_g": 0.4, "kcal": "0.6"},
    }
    out = food_store._normalize_food_row(row)
    assert out["nutrition_nutrient_confidence"]["fat_g"] == pytest.approx(0.4)
    assert out["nutrition_nutrient_confidence"]["kcal"] == pytest.approx(0.6)


def test_foods_db_cache_key_string_fallback_on_resolve_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BadPath:
        def __str__(self) -> str:
            return "/tmp/fake-db-path.sqlite"

        def resolve(self) -> Path:
            raise OSError("simulated resolve failure")

    monkeypatch.setattr(food_store, "DB_PATH", _BadPath())
    assert food_store._foods_db_cache_key() == "/tmp/fake-db-path.sqlite"


def test_foods_db_cache_key_for_connection_uses_db_path_when_database_list_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "foods.sqlite"
    db_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(food_store, "DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    conn.close()
    cache_key = food_store._foods_db_cache_key_for_connection(conn)
    assert cache_key is not None
    assert str(db_path.resolve()) in cache_key


def test_foods_db_cache_key_for_connection_falls_back_when_resolve_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "foods.sqlite"

    class _BadResolvePath:
        def __init__(self, raw_path: str) -> None:
            self._raw_path = Path(raw_path)

        def __str__(self) -> str:
            return str(self._raw_path)

        def resolve(self) -> Path:
            raise OSError("boom")

        def stat(self) -> Any:
            return self._raw_path.stat()

    with sqlite3.connect(db_path) as conn:
        monkeypatch.setattr(food_store, "Path", _BadResolvePath)
        cache_key = food_store._foods_db_cache_key_for_connection(conn)
    assert cache_key is not None
    assert str(db_path) in cache_key


def test_foods_db_cache_key_for_connection_returns_plain_path_when_stat_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "foods.sqlite"
    expected_path = str(db_path.resolve())

    class _BadStatPath:
        def __init__(self, raw_path: str) -> None:
            self._raw_path = Path(raw_path)

        def __str__(self) -> str:
            return str(self._raw_path)

        def resolve(self) -> "_BadStatPath":
            return self

        def stat(self) -> Any:
            raise OSError("boom")

    with sqlite3.connect(db_path) as conn:
        monkeypatch.setattr(food_store, "Path", _BadStatPath)
        cache_key = food_store._foods_db_cache_key_for_connection(conn)
    assert cache_key == expected_path


def test_foods_db_cache_key_for_connection_returns_none_for_non_sqlite_connection() -> None:
    class _NotSqliteConnection:
        pass

    assert food_store._foods_db_cache_key_for_connection(_NotSqliteConnection()) is None


def test_foods_db_cache_key_for_connection_returns_none_for_in_memory_sqlite_connection() -> None:
    with sqlite3.connect(":memory:") as conn:
        assert food_store._foods_db_cache_key_for_connection(conn) is None


def test_foods_db_cache_key_for_connection_prefers_main_database_path_and_changes_on_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "foods.sqlite"
    fallback_db_path = tmp_path / "fallback.sqlite"
    fallback_db_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(food_store, "DB_PATH", fallback_db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE cache_probe (id INTEGER PRIMARY KEY, payload TEXT)")
        conn.commit()

        first_cache_key = food_store._foods_db_cache_key_for_connection(conn)
        assert first_cache_key is not None
        assert first_cache_key.startswith(f"{db_path.resolve()}:")

        first_path, first_mtime_ns, first_size = first_cache_key.rsplit(":", 2)
        assert first_path == str(db_path.resolve())
        assert first_mtime_ns.isdigit()
        assert first_size.isdigit()

        conn.execute(
            "INSERT INTO cache_probe (payload) VALUES (?)",
            ("x" * 10000,),
        )
        conn.commit()

        second_cache_key = food_store._foods_db_cache_key_for_connection(conn)

    assert second_cache_key is not None
    assert second_cache_key.startswith(f"{db_path.resolve()}:")
    assert second_cache_key != first_cache_key


def test_is_missing_nutrition_confidence_column_error_matches_only_legacy_additive_failure() -> (
    None
):
    assert food_store._is_missing_nutrition_confidence_column_error(
        sqlite3.OperationalError("no such column: nutrition_confidence")
    )
    assert food_store._is_missing_nutrition_confidence_column_error(
        sqlite3.OperationalError("No Such Column: f.NUTRITION_CONFIDENCE")
    )
    assert not food_store._is_missing_nutrition_confidence_column_error(
        sqlite3.OperationalError("no such column: canonical_name")
    )
    assert not food_store._is_missing_nutrition_confidence_column_error(
        sqlite3.OperationalError("database is locked")
    )


def test_search_foods_fts_includes_aggregate_confidence_when_pragma_reports_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After cache may be False from error-path tests, pragma on this conn must win."""
    food_store.reset_foods_nutrition_confidence_column_cache()
    dummy = _DummyConn()
    monkeypatch.setattr(food_store, "_connect", lambda: dummy)
    food_store.search_foods("kiwi", limit=3, offset=0)
    assert dummy.last_sql is not None
    assert "f.nutrition_confidence" in dummy.last_sql


def test_search_foods_fts_omits_aggregate_confidence_when_pragma_omits_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FTS path must use lean SELECT when foods lacks nutrition_confidence (legacy DB)."""

    class _NoConfConn(_DummyConn):
        def execute(self, sql: str, params: Any = None) -> _DummyCursor:
            self.last_sql = sql
            if "PRAGMA table_info(foods)" in sql:
                pragma_rows: List[Any] = [
                    (0, "id", "TEXT", 0, None, 0),
                    (1, "canonical_name", "TEXT", 0, None, 0),
                ]
                return _DummyCursor(pragma_rows)
            self.last_params = list(params) if params is not None else []
            return _DummyCursor([{"id": 1, "canonical_name": "apple", "kcal": 10.0}])

    food_store.reset_foods_nutrition_confidence_column_cache()
    dummy = _NoConfConn()
    monkeypatch.setattr(food_store, "_connect", lambda: dummy)
    food_store.search_foods("apple", limit=2, offset=0)
    assert dummy.last_sql is not None
    assert "MATCH" in dummy.last_sql
    assert "f.nutrition_confidence" not in dummy.last_sql


def test_foods_has_nutrition_confidence_column_handles_sqlite_execute_error() -> None:
    food_store.reset_foods_nutrition_confidence_column_cache()

    class _ErrConn:
        def execute(self, *_a: Any, **_kw: Any) -> Any:
            raise sqlite3.Error("pragma failed")

    assert food_store._foods_has_nutrition_confidence_column(_ErrConn()) is False


def test_foods_has_nutrition_confidence_column_returns_cached_value_without_pragma(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    food_store.reset_foods_nutrition_confidence_column_cache()

    class _NoPragmaConn:
        def execute(self, *_a: Any, **_kw: Any) -> Any:
            raise AssertionError("cached path must not execute PRAGMA")

    monkeypatch.setattr(food_store, "_foods_db_cache_key_for_connection", lambda _con: "cache-key")
    food_store._NUTRITION_CONFIDENCE_COLUMN_CACHE["cache-key"] = True

    try:
        assert food_store._foods_has_nutrition_confidence_column(_NoPragmaConn()) is True
    finally:
        food_store.reset_foods_nutrition_confidence_column_cache()


def test_invalidate_foods_nutrition_confidence_cache_drops_active_entry(tmp_path: Path) -> None:
    db_path = tmp_path / "foods.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE foods (
                id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                nutrition_confidence REAL
            )
            """)
        conn.commit()
        original_db_path = food_store.DB_PATH
        food_store.DB_PATH = db_path
        try:
            food_store.reset_foods_nutrition_confidence_column_cache()
            cache_key = food_store._foods_db_cache_key_for_connection(conn)
            assert cache_key is not None
            assert food_store._foods_has_nutrition_confidence_column(conn) is True
            assert cache_key in food_store._NUTRITION_CONFIDENCE_COLUMN_CACHE
            food_store._invalidate_foods_nutrition_confidence_cache(conn)
            assert cache_key not in food_store._NUTRITION_CONFIDENCE_COLUMN_CACHE
        finally:
            food_store.DB_PATH = original_db_path


def test_invalidate_foods_nutrition_confidence_cache_noops_without_cache_key() -> None:
    food_store.reset_foods_nutrition_confidence_column_cache()

    with sqlite3.connect(":memory:") as conn:
        food_store._invalidate_foods_nutrition_confidence_cache(conn)

    assert food_store._NUTRITION_CONFIDENCE_COLUMN_CACHE == {}


def test_execute_foods_query_with_legacy_retry_retries_missing_confidence_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Cursor:
        def __init__(self, rows: List[Dict[str, Any]]) -> None:
            self._rows = rows

        def fetchall(self) -> List[Dict[str, Any]]:
            return self._rows

    class _RetryConn:
        def __init__(self) -> None:
            self.calls: List[str] = []

        def execute(self, sql: str, params: Any = None) -> _Cursor:
            del params
            self.calls.append(sql)
            if "nutrition_confidence" in sql:
                raise sqlite3.OperationalError("no such column: nutrition_confidence")
            return _Cursor([{"id": "fallback"}])

    conn = _RetryConn()
    invalidations: List[str] = []
    monkeypatch.setattr(food_store, "_foods_has_nutrition_confidence_column", lambda _con: True)
    monkeypatch.setattr(
        food_store,
        "_invalidate_foods_nutrition_confidence_cache",
        lambda _con: invalidations.append("invalidated"),
    )

    rows = food_store._execute_foods_query_with_legacy_retry(
        conn,
        lambda has_conf: (
            ("SELECT id, nutrition_confidence FROM foods" if has_conf else "SELECT id FROM foods"),
            (),
        ),
    )

    assert [row["id"] for row in rows] == ["fallback"]
    assert invalidations == ["invalidated"]
    assert conn.calls == [
        "SELECT id, nutrition_confidence FROM foods",
        "SELECT id FROM foods",
    ]


def test_execute_foods_query_with_legacy_retry_reraises_other_operational_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenConn:
        def execute(self, sql: str, params: Any = None) -> Any:
            del sql, params
            raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(food_store, "_foods_has_nutrition_confidence_column", lambda _con: True)

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        food_store._execute_foods_query_with_legacy_retry(
            _BrokenConn(),
            lambda has_conf: (
                (
                    "SELECT id, nutrition_confidence FROM foods"
                    if has_conf
                    else "SELECT id FROM foods"
                ),
                (),
            ),
        )


def test_normalize_food_row_additive_columns_none_or_pre_parsed() -> None:
    parsed_inputs = [{"source": "estimate", "record_id": "x"}]
    parsed_prov = {"protein_g": "estimate"}
    row = {
        "id": "food-mixed",
        "canonical_name": "yogurt",
        "nutrition_inputs_json": None,
        "nutrition_provenance_json": None,
    }
    assert food_store._normalize_food_row(row)["nutrition_inputs"] == []

    row_pre = {
        "id": "food-pre",
        "canonical_name": "kefir",
        "nutrition_inputs_json": parsed_inputs,
        "nutrition_provenance_json": parsed_prov,
        "nutrition_confidence": 0.25,
    }
    out = food_store._normalize_food_row(row_pre)
    assert out["nutrition_inputs"] == parsed_inputs
    assert out["nutrition_provenance"] == parsed_prov
    assert out["nutrition_confidence"] == 0.25


def test_get_food_by_barcode_returns_row_with_normalized_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={"00012345678905": {"id": "f1", "canonical_name": "apple"}}
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode(" 00012345678905 ")

    assert result == {"id": "f1", "canonical_name": "apple", **_LEGACY_ROW_ADDITIVE_DEFAULTS}
    assert conn.calls == ["00012345678905"]


def test_get_food_by_barcode_returns_stored_metadata_from_sqlite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "food.sqlite"
    with sqlite3.connect(db_path) as con:
        con.execute("""
            CREATE TABLE foods (
                id TEXT PRIMARY KEY,
                canonical_name TEXT,
                gtin TEXT,
                brand TEXT,
                fdc_id TEXT,
                nutrition_confidence REAL
            )
            """)
        con.execute(
            "INSERT INTO foods (id, canonical_name, gtin, brand, fdc_id, nutrition_confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("food-gtin", "Granola Bar", "0012345678905", "USDA Brand", "234567", 0.8),
        )

    monkeypatch.setattr(food_store, "DB_PATH", db_path)
    food_store.reset_foods_nutrition_confidence_column_cache()

    result = food_store.get_food_by_barcode("00 123-456 78905")

    assert result is not None
    assert result["id"] == "food-gtin"
    assert result["brand"] == "USDA Brand"
    assert result["gtin"] == "0012345678905"
    assert result["fdc_id"] == "234567"
    assert result["nutrition_confidence"] == 0.8


def test_get_food_by_barcode_uses_leading_zero_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={
            "0123456789012": None,
            "123456789012": {"id": "f2", "canonical_name": "banana"},
        }
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("0123456789012")

    assert result == {"id": "f2", "canonical_name": "banana", **_LEGACY_ROW_ADDITIVE_DEFAULTS}
    assert conn.calls == ["0123456789012", "123456789012"]


def test_get_food_by_barcode_drops_only_one_leading_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={
            "0012345678905": None,
            "012345678905": {"id": "f3", "canonical_name": "pear"},
        }
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("0012345678905")

    assert result == {"id": "f3", "canonical_name": "pear", **_LEGACY_ROW_ADDITIVE_DEFAULTS}
    assert conn.calls == ["0012345678905", "012345678905"]


def test_get_food_by_barcode_uses_full_strip_fallback_as_last_resort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={
            "0012345678905": None,
            "012345678905": None,
            "12345678905": {"id": "f4", "canonical_name": "orange"},
        }
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("0012345678905")

    assert result == {"id": "f4", "canonical_name": "orange", **_LEGACY_ROW_ADDITIVE_DEFAULTS}
    assert conn.calls == ["0012345678905", "012345678905", "12345678905"]


def test_get_food_by_barcode_skips_short_fallback_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _DummyBarcodeConn(rows_by_barcode={"01234567": None})
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("01234567")

    assert result is None
    assert conn.calls == ["01234567"]


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


def test_get_search_backend_prefers_semantic_adapter_over_compat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CompatBackend:
        def __init__(self) -> None:
            self.calls: List[tuple[str, Any, Any]] = []

        def search_foods(
            self, query: str, limit: Any = 20, offset: Any = 0
        ) -> List[Dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [{"id": "compat"}]

    class _SemanticBackend:
        def __init__(self) -> None:
            self.calls: List[tuple[str, Any, Any]] = []

        def search_foods(
            self, query: str, limit: Any = 20, offset: Any = 0
        ) -> List[Dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [{"id": "semantic"}]

    compat_backend = _CompatBackend()
    semantic_backend = _SemanticBackend()
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", "true")
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", "true")
    food_store.register_search_backend_adapter(compat_backend)
    food_store.register_semantic_search_backend_adapter(semantic_backend)
    try:
        backend = food_store.get_search_backend()
        rows = backend.search_foods("banana", limit=5, offset=1)
        assert rows == [{"id": "semantic"}]
        assert semantic_backend.calls == [("banana", 5, 1)]
        assert compat_backend.calls == []
    finally:
        food_store.reset_search_backend_adapter()
        food_store.reset_semantic_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)


def test_get_search_backend_rolls_back_to_legacy_when_semantic_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _SemanticBackend:
        def __init__(self) -> None:
            self.calls: List[tuple[str, Any, Any]] = []

        def search_foods(
            self, query: str, limit: Any = 20, offset: Any = 0
        ) -> List[Dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [{"id": "semantic"}]

    called: dict[str, tuple[Any, Any, Any]] = {}

    def fake_legacy_search(query: str, limit: Any = 20, offset: Any = 0) -> List[Dict[str, Any]]:
        called["params"] = (query, limit, offset)
        return [{"id": "legacy"}]

    semantic_backend = _SemanticBackend()
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", "false")
    monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
    monkeypatch.setattr(food_store, "search_foods", fake_legacy_search)
    food_store.register_semantic_search_backend_adapter(semantic_backend)
    try:
        backend = food_store.get_search_backend()
        rows = backend.search_foods("apple", limit=4, offset=2)
        assert rows == [{"id": "legacy"}]
        assert called["params"] == ("apple", 4, 2)
        assert semantic_backend.calls == []
    finally:
        food_store.reset_semantic_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)


def test_get_search_backend_uses_bootstrap_semantic_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = [
        {
            "id": "sem-1",
            "canonical_name": "High Protein Greek Yogurt",
            "kcal": 110,
            "protein_g": 17.0,
            "fat_g": 0.0,
            "carbs_g": 6.0,
        },
        {
            "id": "sem-2",
            "canonical_name": "Chocolate Cookie",
            "kcal": 220,
            "protein_g": 2.0,
            "fat_g": 8.0,
            "carbs_g": 32.0,
        },
    ]
    fallback_calls: List[tuple[str, int, int]] = []

    def fake_search_foods(
        query: str, limit: int | str = 20, offset: int | str = 0
    ) -> List[Dict[str, Any]]:
        fallback_calls.append((query, int(limit), int(offset)))
        return [{"id": "legacy-fallback"}]

    monkeypatch.setenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", "true")
    monkeypatch.setenv("FOOD_SEARCH_SEMANTIC_CANDIDATE_LIMIT", "10")
    monkeypatch.setattr(food_store, "search_foods", fake_search_foods)
    monkeypatch.setattr(food_store, "_load_semantic_candidates", lambda limit: candidates)
    food_store.reset_semantic_search_backend_adapter()
    try:
        backend = food_store.get_search_backend()
        rows = backend.search_foods("protein yogurt", limit=1, offset=0)
        assert rows[0]["id"] == "sem-1"
        assert fallback_calls == []
    finally:
        food_store.reset_semantic_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)
        monkeypatch.delenv("FOOD_SEARCH_SEMANTIC_CANDIDATE_LIMIT", raising=False)


def test_bootstrap_semantic_backend_empty_query_delegates_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[tuple[str, int, int]] = []

    def fake_search_foods(
        query: str, limit: int | str = 20, offset: int | str = 0
    ) -> List[Dict[str, Any]]:
        calls.append((query, int(limit), int(offset)))
        return [{"id": "legacy-empty"}]

    monkeypatch.setattr(food_store, "search_foods", fake_search_foods)
    backend = food_store._BootstrapSemanticSearchBackend(candidate_limit=5)
    rows = backend.search_foods("", limit=2, offset=1)
    assert rows == [{"id": "legacy-empty"}]
    assert calls == [("", 2, 1)]


def test_bootstrap_semantic_backend_non_token_query_uses_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[tuple[str, int, int]] = []

    def fake_search_foods(
        query: str, limit: int | str = 20, offset: int | str = 0
    ) -> List[Dict[str, Any]]:
        normalized = (query, int(limit), int(offset))
        calls.append(normalized)
        return [{"id": "legacy-non-token"}]

    monkeypatch.setattr(food_store, "search_foods", fake_search_foods)
    monkeypatch.setattr(
        food_store,
        "_load_semantic_candidates",
        lambda limit: [{"id": "candidate", "canonical_name": "Apple", "kcal": 50}],
    )
    backend = food_store._BootstrapSemanticSearchBackend(candidate_limit=7)
    rows = backend.search_foods("!!!", limit=3, offset=0)
    assert rows == [{"id": "legacy-non-token"}]
    assert calls == [("!!!", 3, 0)]


def test_bootstrap_semantic_backend_no_ranked_matches_uses_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[tuple[str, int, int]] = []

    def fake_search_foods(
        query: str, limit: int | str = 20, offset: int | str = 0
    ) -> List[Dict[str, Any]]:
        normalized = (query, int(limit), int(offset))
        calls.append(normalized)
        return [{"id": "legacy-no-rank"}]

    monkeypatch.setattr(food_store, "search_foods", fake_search_foods)
    monkeypatch.setattr(
        food_store,
        "_load_semantic_candidates",
        lambda limit: [
            {"id": "cand-1", "canonical_name": "Chocolate Cookie", "kcal": 250},
            {"id": "cand-2", "canonical_name": "Lemon Pie", "kcal": 300},
        ],
    )
    backend = food_store._BootstrapSemanticSearchBackend(candidate_limit=4)
    rows = backend.search_foods("protein", limit=1, offset=0)
    assert rows == [{"id": "legacy-no-rank"}]
    assert calls == [("protein", 1, 0)]


def test_bootstrap_semantic_backend_large_offset_falls_back_without_candidate_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[tuple[str, int, int]] = []

    def fake_search_foods(
        query: str, limit: int | str = 20, offset: int | str = 0
    ) -> List[Dict[str, Any]]:
        calls.append((query, int(limit), int(offset)))
        return [{"id": "legacy-large-offset"}]

    def _should_not_be_called(limit: int) -> List[Dict[str, Any]]:
        raise AssertionError("candidate scan should not run for oversized offset window")

    monkeypatch.setattr(food_store, "search_foods", fake_search_foods)
    monkeypatch.setattr(food_store, "_load_semantic_candidates", _should_not_be_called)
    backend = food_store._BootstrapSemanticSearchBackend(candidate_limit=32)
    rows = backend.search_foods("protein", limit=10, offset=40)
    assert rows == [{"id": "legacy-large-offset"}]
    assert calls == [("protein", 10, 40)]


def test_load_semantic_candidates_uses_passed_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    food_store.reset_foods_nutrition_confidence_column_cache()

    class _SemanticCursor:
        def __init__(self, rows: List[Any] | None = None) -> None:
            self._rows: List[Any] = (
                rows
                if rows is not None
                else [{"id": "sem-1", "canonical_name": "Apple", "kcal": 52}]
            )

        def fetchall(self) -> List[Any]:
            return self._rows

    class _SemanticConn:
        def __init__(self) -> None:
            self.last_params: tuple[int] | None = None
            self.last_select_sql: str | None = None

        def execute(self, sql: str, params: Any = None) -> _SemanticCursor:
            if "PRAGMA table_info(foods)" in sql:
                pragma_rows: List[Any] = [
                    (0, "id", "TEXT", 0, None, 0),
                    (1, "nutrition_confidence", "REAL", 0, None, 0),
                ]
                return _SemanticCursor(pragma_rows)
            assert "FROM foods ORDER BY id ASC LIMIT ?" in sql
            assert params is not None
            self.last_select_sql = sql
            self.last_params = tuple(params)  # type: ignore[arg-type]
            return _SemanticCursor()

        def __enter__(self) -> "_SemanticConn":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

    conn = _SemanticConn()
    monkeypatch.setattr(food_store, "_connect", lambda: conn)
    rows = food_store._load_semantic_candidates(limit=250)
    assert conn.last_params == (250,)
    assert conn.last_select_sql is not None
    assert "nutrition_confidence" in conn.last_select_sql
    assert rows[0]["id"] == "sem-1"


def test_load_semantic_candidates_skips_aggregate_column_when_pragma_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    food_store.reset_foods_nutrition_confidence_column_cache()

    class _SemanticCursor:
        def __init__(self, rows: List[Any] | None = None) -> None:
            self._rows: List[Any] = (
                rows
                if rows is not None
                else [{"id": "sem-2", "canonical_name": "Pear", "kcal": 57}]
            )

        def fetchall(self) -> List[Any]:
            return self._rows

    class _SemanticConnNoConf:
        def __init__(self) -> None:
            self.last_select_sql: str | None = None

        def execute(self, sql: str, params: Any = None) -> _SemanticCursor:
            if "PRAGMA table_info(foods)" in sql:
                pragma_rows: List[Any] = [
                    (0, "id", "TEXT", 0, None, 0),
                    (1, "canonical_name", "TEXT", 0, None, 0),
                ]
                return _SemanticCursor(pragma_rows)
            assert "FROM foods ORDER BY id ASC LIMIT ?" in sql
            assert params is not None
            self.last_select_sql = sql
            return _SemanticCursor()

        def __enter__(self) -> "_SemanticConnNoConf":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

    conn = _SemanticConnNoConf()
    monkeypatch.setattr(food_store, "_connect", lambda: conn)
    rows = food_store._load_semantic_candidates(limit=12)
    assert conn.last_select_sql is not None
    assert "nutrition_confidence" not in conn.last_select_sql
    assert rows[0]["id"] == "sem-2"


def test_semantic_score_returns_zero_for_empty_tokens() -> None:
    assert food_store._semantic_score(set(), "Apple") == 0.0


def test_resolve_semantic_backend_uses_existing_global_instance() -> None:
    class _ExistingBackend:
        def search_foods(
            self, query: str, limit: int | str = 20, offset: int | str = 0
        ) -> List[Dict[str, Any]]:
            return [{"id": "existing"}]

    existing = _ExistingBackend()
    food_store.register_semantic_search_backend_adapter(existing)
    try:
        resolved = food_store._resolve_semantic_backend(semantic_backend=None)
        assert resolved is existing
    finally:
        food_store.reset_semantic_search_backend_adapter()


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("invalid", 250),
        ("0", 250),
        ("1", 1),
        ("999999", 5000),
    ],
)
def test_semantic_candidate_limit_env_guard(
    raw_value: str, expected: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FOOD_SEARCH_SEMANTIC_CANDIDATE_LIMIT", raw_value)
    assert food_store._semantic_candidate_limit() == expected


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


def test_discover_food_source_keys_falls_back_on_sqlite_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    class _BrokenConn:
        def __enter__(self) -> "_BrokenConn":
            raise sqlite3.OperationalError("db unavailable")

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

    monkeypatch.setattr(food_store, "_connect", lambda: _BrokenConn())
    assert food_store._discover_food_source_keys() == ["usda", "open food facts"]


def test_get_food_source_attributions_maps_known_and_unknown_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        food_store,
        "_discover_food_source_keys",
        lambda: ["merged(off,usda)", "off", "unknown-source"],
    )

    rows = food_store.get_food_source_attributions()

    assert rows[0]["source"] == "USDA + Open Food Facts (merged)"
    assert "ODbL v1.0" in str(rows[0]["license"])
    assert rows[1]["source"] == "Open Food Facts"
    assert rows[1]["license"] == "Open Database License (ODbL) v1.0"
    assert rows[2]["source"] == "UNKNOWN-SOURCE"
    assert rows[2]["license"] == "Unknown / internal source policy"


def test_discover_food_source_keys_returns_sorted_normalized_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _SourceCursor:
        def fetchall(self) -> List[Dict[str, Any]]:
            return [
                {"source": " Open Food Facts "},
                {"source": "USDA"},
                {"source": ""},
            ]

    class _SourceConn:
        def execute(self, sql: str) -> _SourceCursor:
            assert "SELECT DISTINCT source FROM foods" in sql
            return _SourceCursor()

        def __enter__(self) -> "_SourceConn":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

    monkeypatch.setattr(food_store, "_connect", lambda: _SourceConn())
    assert food_store._discover_food_source_keys() == ["open food facts", "usda"]


def test_discover_food_source_keys_returns_defaults_when_rows_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _SourceCursor:
        def fetchall(self) -> List[Dict[str, Any]]:
            return []

    class _SourceConn:
        def execute(self, sql: str) -> _SourceCursor:
            assert "SELECT DISTINCT source FROM foods" in sql
            return _SourceCursor()

        def __enter__(self) -> "_SourceConn":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

    monkeypatch.setattr(food_store, "_connect", lambda: _SourceConn())
    assert food_store._discover_food_source_keys() == ["usda", "open food facts"]


def test_search_foods_works_when_sqlite_foods_lacks_nutrition_confidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy food.sqlite without aggregate confidence column must not break list/search."""

    db_path = tmp_path / "legacy_foods.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE foods (
                id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                kcal REAL,
                protein_g REAL,
                fat_g REAL,
                carbs_g REAL
            )
            """)
        conn.execute(
            "INSERT INTO foods (id, canonical_name, kcal, protein_g, fat_g, carbs_g) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("fid1", "Apple", 52.0, 0.3, 0.2, 14.0),
        )
    monkeypatch.setattr(food_store, "DB_PATH", db_path)
    food_store.reset_foods_nutrition_confidence_column_cache()
    rows = food_store.search_foods("", limit=10, offset=0)
    assert len(rows) == 1
    assert rows[0]["canonical_name"] == "Apple"
    assert "nutrition_confidence" not in rows[0]


def test_coerce_nutrient_confidence_map_skips_unparseable_string_values() -> None:
    """Invalid string numerics hit ValueError branch and are omitted."""
    assert food_store._coerce_nutrient_confidence_map({"protein_g": "not-a-float"}) == {}


def test_coerce_nutrient_confidence_map_skips_non_scalar_values() -> None:
    """Non int/float/str values use the else branch and are omitted."""
    assert food_store._coerce_nutrient_confidence_map({"k": []}) == {}


def test_coerce_nutrient_confidence_map_skips_bool_values() -> None:
    """Bools must not be treated as numeric confidence scalars."""
    out = food_store._coerce_nutrient_confidence_map(
        {"kcal": True, "protein_g": False, "fat_g": 0.25},
    )
    assert "kcal" not in out
    assert "protein_g" not in out
    assert out["fat_g"] == pytest.approx(0.25)
