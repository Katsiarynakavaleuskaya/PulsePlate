import csv
import logging
from pathlib import Path
from types import TracebackType
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


def test_get_food_by_barcode_drops_only_one_leading_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _DummyBarcodeConn(
        rows_by_barcode={
            "0012345678905": None,
            "012345678905": {"id": "f3", "canonical_name": "pear"},
        }
    )
    monkeypatch.setattr(food_store, "_connect", lambda: conn)

    result = food_store.get_food_by_barcode("0012345678905")

    assert result == {"id": "f3", "canonical_name": "pear"}
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

    assert result == {"id": "f4", "canonical_name": "orange"}
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
    class _SemanticCursor:
        def fetchall(self) -> List[Dict[str, Any]]:
            return [{"id": "sem-1", "canonical_name": "Apple", "kcal": 52}]

    class _SemanticConn:
        def __init__(self) -> None:
            self.last_params: tuple[int] | None = None

        def execute(self, sql: str, params: tuple[int]) -> _SemanticCursor:
            assert "FROM foods ORDER BY id ASC LIMIT ?" in sql
            self.last_params = params
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
    assert rows[0]["id"] == "sem-1"


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
