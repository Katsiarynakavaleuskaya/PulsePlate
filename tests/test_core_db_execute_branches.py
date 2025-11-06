from typing import Any, NoReturn

import pytest

from core import db as core_db


class FakeConn:
    def __init__(self, in_tx: bool = False, fail_commit: Exception | None = None) -> None:
        self._in_tx = in_tx
        self._fail_commit = fail_commit
        self.closed = False
        self.rollback_called = False
        self.commit_called = False

    # For _is_in_transaction via get_transaction/in_transaction
    def get_transaction(self) -> Any:
        return object() if self._in_tx else None

    def commit(self) -> None:
        self.commit_called = True
        if self._fail_commit:
            raise self._fail_commit

    def rollback(self) -> None:
        self.rollback_called = True

    def close(self) -> None:
        self.closed = True


class FakeEngine:
    def __init__(self, conn: FakeConn, to_raise: Exception | None = None) -> None:
        self._conn = conn
        self._to_raise = to_raise

    def connect(self) -> FakeConn:
        return self._conn


class FakeResult:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    # allow attribute access passthrough
    def fetchall(self) -> list[int]:
        return [1]


def test_finalize_transaction_commit_ok_and_error_paths() -> None:
    compat = core_db.EngineCompat(object())

    # Commit OK path (in transaction)
    conn_ok = FakeConn(in_tx=True)
    compat._finalize_transaction(conn_ok)
    assert conn_ok.commit_called is True
    assert conn_ok.rollback_called is False

    # SQLAlchemyError branch triggers rollback
    db_err = core_db.sa_exc.SQLAlchemyError("db fail")
    conn_db_fail = FakeConn(in_tx=True, fail_commit=db_err)
    with pytest.raises(core_db.sa_exc.SQLAlchemyError):
        compat._finalize_transaction(conn_db_fail)
    assert conn_db_fail.rollback_called is True

    # Unexpected error branch triggers rollback
    conn_unexp = FakeConn(in_tx=True, fail_commit=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        compat._finalize_transaction(conn_unexp)
    assert conn_unexp.rollback_called is True


def test_execute_error_cleanup_rolls_back_and_closes() -> None:
    conn = FakeConn(in_tx=True)

    class EngineWithFail(FakeEngine):
        def connect(self) -> FakeConn:  # type: ignore[override]
            return conn

    engine = EngineWithFail(conn)
    compat = core_db.EngineCompat(engine)

    def failing_execute(stmt: Any, *args: Any, **kwargs: Any) -> NoReturn:  # type: ignore[no-untyped-def]
        raise RuntimeError("exec fail")

    # Monkeypatch connection to inject execute
    setattr(conn, "execute", failing_execute)

    with pytest.raises(RuntimeError):
        compat.execute("SELECT 1")

    assert conn.rollback_called is True
    assert conn.closed is True


def test_execute_returns_wrapper_that_closes_connection() -> None:
    conn = FakeConn(in_tx=False)

    class EngineOk(FakeEngine):
        def connect(self) -> FakeConn:  # type: ignore[override]
            return conn

    engine = EngineOk(conn)
    compat = core_db.EngineCompat(engine)

    result = FakeResult()

    def ok_execute(stmt: Any, *args: Any, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
        return result

    setattr(conn, "execute", ok_execute)

    wrapper = compat.execute("SELECT 1")
    # Underlying fetchall still works via __getattr__
    assert wrapper.fetchall() == [1]
    # Closing wrapper closes connection
    wrapper.close()
    assert conn.closed is True
    assert result.closed is True
