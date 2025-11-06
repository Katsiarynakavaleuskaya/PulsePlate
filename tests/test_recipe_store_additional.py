from __future__ import annotations

from typing import Any, Dict, List

import pytest

import app.services.recipe_store as rs


class _FakeCursor:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows

    def fetchall(self) -> List[Dict[str, Any]]:
        return self._rows

    def fetchone(self) -> Dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows
        self.executions: List[tuple[str, List[Any]]] = []

    def execute(self, sql: str, params: List[Any] | tuple[Any, ...]) -> _FakeCursor:
        self.executions.append((sql.strip(), list(params)))
        return _FakeCursor(self._rows)

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None


def test_search_recipes_with_query(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"recipe_id": "r1", "title": "Soup", "kcal_per_serv": 150, "tags_json": "[]"}]
    conn_container: dict[str, _FakeConnection] = {}

    def fake_con() -> _FakeConnection:
        conn = _FakeConnection(rows)
        conn_container["conn"] = conn
        return conn

    monkeypatch.setattr(rs, "_con", fake_con)
    result = rs.search_recipes("soup", limit=5, offset=2)
    assert result == rows
    sql, params = conn_container["conn"].executions[0]
    assert "MATCH" in sql
    assert params == ["soup", 5, 2]


def test_search_recipes_empty_query(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"recipe_id": "r1", "title": "Soup", "kcal_per_serv": 150, "tags_json": "[]"}]
    monkeypatch.setattr(rs, "_con", lambda: _FakeConnection(rows))
    result = rs.search_recipes("", limit=3, offset=0)
    assert result == rows


def test_get_recipe_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rs, "_con", lambda: _FakeConnection([]))
    assert rs.get_recipe("nope") is None


def test_search_limit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {"recipe_id": f"r{i}", "title": f"T{i}", "kcal_per_serv": 100 + i, "tags_json": "[]"}
        for i in range(5)
    ]

    class _Conn(_FakeConnection):
        def execute(self, sql: str, params: List[Any] | tuple[Any, ...]) -> _FakeCursor:
            # Normalize params to list
            p = list(params)
            if "MATCH" in sql:
                _, limit, offset = p  # query, limit, offset
            else:
                limit, offset = p  # limit, offset
            # Slice by limit/offset semantics; limit==0 -> empty
            if limit < 0 or offset < 0:
                raise ValueError("negative limit/offset")
            self.executions.append((sql.strip(), list(params)))
            return _FakeCursor(rows[offset : offset + limit])

    conn_container: dict[str, _Conn] = {}

    def _factory() -> _Conn:
        c = _Conn(rows)
        conn_container["c"] = c
        return c

    monkeypatch.setattr(rs, "_con", _factory)
    result = rs.search_recipes("q", limit=0, offset=0)
    assert result == []
    sql, params = conn_container["c"].executions[0]
    assert ("MATCH" in sql) and params[1] == 0


def test_search_large_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {"recipe_id": f"r{i}", "title": f"T{i}", "kcal_per_serv": 100 + i, "tags_json": "[]"}
        for i in range(10)
    ]

    class _Conn(_FakeConnection):
        def execute(self, sql: str, params: List[Any] | tuple[Any, ...]) -> _FakeCursor:
            p = list(params)
            if "MATCH" in sql:
                _, limit, offset = p
            else:
                limit, offset = p
            self.executions.append((sql.strip(), list(params)))
            return _FakeCursor(rows[offset : offset + limit])

    conn_container2: dict[str, _Conn] = {}

    def _factory2() -> _Conn:
        c = _Conn(rows)
        conn_container2["c"] = c
        return c

    monkeypatch.setattr(rs, "_con", _factory2)
    big_limit = 1000
    out = rs.search_recipes("q", limit=big_limit, offset=0)
    # Truncated to available rows
    assert len(out) == len(rows)
    sql, params = conn_container2["c"].executions[0]
    assert ("MATCH" in sql) and params[1] == big_limit


def test_search_negative_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    rows: List[Dict[str, Any]] = []

    class _Conn(_FakeConnection):
        def execute(self, sql: str, params: List[Any] | tuple[Any, ...]) -> _FakeCursor:
            p = list(params)
            if "MATCH" in sql:
                _, limit, offset = p
            else:
                limit, offset = p
            if limit < 0 or offset < 0:
                raise ValueError("negative limit/offset")
            return _FakeCursor(rows)

    monkeypatch.setattr(rs, "_con", lambda: _Conn(rows))
    with pytest.raises(Exception):
        rs.search_recipes("q", limit=-5, offset=-1)


def test_get_recipe_found(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {"recipe_id": "r1", "title": "Soup", "kcal_per_serv": 150, "tags_json": "[]"}

    class _Conn:
        def __init__(self) -> None:
            self.executions: list[tuple[str, list[Any]]] = []

        def execute(self, sql: str, params: List[Any] | tuple[Any, ...]) -> _FakeCursor:
            self.executions.append((sql.strip(), list(params)))
            return _FakeCursor([row])

        def __enter__(self) -> "_Conn":
            return self

        def __exit__(self, *exc: Any) -> None:
            return None

    conn = _Conn()
    monkeypatch.setattr(rs, "_con", lambda: conn)
    out = rs.get_recipe("r1")
    assert out == row
    sql, params = conn.executions[0]
    assert "SELECT * FROM recipes WHERE recipe_id = ?" in sql
    assert params == ["r1"]


def test_search_multiple_results(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {"recipe_id": f"r{i}", "title": f"T{i}", "kcal_per_serv": 100 + i, "tags_json": "[]"}
        for i in range(20)
    ]

    class _Conn(_FakeConnection):
        def execute(self, sql: str, params: List[Any] | tuple[Any, ...]) -> _FakeCursor:
            p = list(params)
            if "MATCH" in sql:
                _, limit, offset = p
            else:
                limit, offset = p
            self.executions.append((sql.strip(), list(params)))
            return _FakeCursor(rows[offset : offset + limit])

    conn_container3: dict[str, _Conn] = {}

    def _factory3() -> _Conn:
        c = _Conn(rows)
        conn_container3["c"] = c
        return c

    monkeypatch.setattr(rs, "_con", _factory3)
    out = rs.search_recipes("q", limit=7, offset=3)
    assert len(out) == 7
    # Ensure SQL params are correct
    sql, params = conn_container3["c"].executions[0]
    assert ("MATCH" in sql) and params[1:] == [7, 3]
