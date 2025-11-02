import pytest
from types import TracebackType
from typing import Any

from sqlalchemy import exc as sa_exc

from core.db import EngineCompat


class _FakeConn:
    def __init__(self, commit_raises: Exception | None = None, in_tx: bool = True) -> None:
        self._commit_raises = commit_raises
        self._in_tx = in_tx

    def execute(
        self, stmt: Any, *args: Any, **kwargs: Any
    ) -> str:  # pragma: no cover - trivial pass-through
        return "ok"

    def get_transaction(self) -> object | None:  # emulate SQLAlchemy API
        return object() if self._in_tx else None

    def commit(self) -> None:
        if self._commit_raises is not None:
            raise self._commit_raises

    def rollback(self) -> None:  # pragma: no cover - executed only on error path
        return None

    # context manager protocol
    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:  # pragma: no cover - no-op
        pass


class _FakeEngine:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def connect(self) -> _FakeConn:
        return self._conn


def test_execute_commits_only_when_in_transaction():
    # in_tx=False should skip commit without raising
    engine = EngineCompat(_FakeEngine(_FakeConn(commit_raises=None, in_tx=False)))
    assert engine.execute("SELECT 1") == "ok"


def test_execute_handles_db_errors_on_commit_without_raise():
    fake_exc = sa_exc.IntegrityError("stmt", {}, Exception("detail"))
    engine = EngineCompat(_FakeEngine(_FakeConn(commit_raises=fake_exc, in_tx=True)))
    # Legacy behavior: error is logged and rolled back but not raised
    assert engine.execute("UPDATE t SET a=1") == "ok"
