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
