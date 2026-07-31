"""Deterministic contracts for opt-in TestClient SQLite isolation."""

from __future__ import annotations

import os
import re
import stat
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Generator, cast

import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.pool import NullPool

import core.db as core_db
from core.models import User
import tests.conftest as conftest_module

_ENV_KEYS = (
    "DATABASE_URL",
    "TEST_DB_PATH",
    "DB_FALLBACK_URL",
    "DATABASE_ASYNC_URL",
    "DATABASE_USE_ASYNC",
)
_EXPLICIT_USER_ID = 814_221


class _PrimaryIsolationFailure(RuntimeError):
    """Sentinel proving cleanup never replaces the primary failure."""


def _env_snapshot() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _ENV_KEYS}


def _fake_request(nodeid: str) -> pytest.FixtureRequest:
    request = SimpleNamespace(
        config=SimpleNamespace(workerinput={"workerid": "gw-contract"}),
        node=SimpleNamespace(nodeid=nodeid),
    )
    return cast(pytest.FixtureRequest, request)


def _finish_lifecycle(lifecycle: Generator[Path, None, None]) -> None:
    with pytest.raises(StopIteration):
        next(lifecycle)


def _traceback_contains_code(error: BaseException, expected_code: Any) -> bool:
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code is expected_code:
            return True
        traceback = traceback.tb_next
    return False


def _assert_insert_isolated_user(own_marker: str, other_marker: str) -> None:
    with core_db.session_scope() as session:
        assert session.get(User, _EXPLICIT_USER_ID) is None
        assert session.scalar(select(User).where(User.email == other_marker)) is None
        session.add(
            User(
                id=_EXPLICIT_USER_ID,
                email=own_marker,
                name="TC1b isolation marker",
            )
        )

    with core_db.session_scope() as session:
        stored = session.get(User, _EXPLICIT_USER_ID)
        assert stored is not None
        assert stored.email == own_marker


def test_isolated_sqlite_database_has_exact_engine_and_file_contract(
    isolated_sqlite_database: Path,
    tmp_path: Path,
) -> None:
    db_path = isolated_sqlite_database
    engine = core_db._RAW_ENGINE

    assert engine is not None
    assert db_path.parent == tmp_path.resolve(strict=True)
    assert len(db_path.name) <= 96
    assert re.fullmatch(r"[A-Za-z0-9_.-]+", db_path.name)
    assert stat.S_ISREG(db_path.lstat().st_mode)
    assert stat.S_IMODE(db_path.lstat().st_mode) == 0o600
    assert os.environ["DATABASE_URL"] == f"sqlite:///{db_path}"
    assert os.environ["TEST_DB_PATH"] == str(db_path)
    assert os.environ["DB_FALLBACK_URL"] == f"sqlite:///{db_path}"
    assert "DATABASE_ASYNC_URL" not in os.environ
    assert "DATABASE_USE_ASYNC" not in os.environ
    assert str(engine.url) == os.environ["DATABASE_URL"]
    assert Path(str(engine.url.database)).resolve(strict=True) == db_path
    assert isinstance(engine.pool, NullPool)

    _args, connect_kwargs = engine.dialect.create_connect_args(engine.url)
    assert connect_kwargs["check_same_thread"] is False


def test_isolated_sqlite_database_restores_exact_env_and_baseline_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_url = os.environ["DATABASE_URL"]
    monkeypatch.setenv("DB_FALLBACK_URL", "baseline-fallback-value")
    monkeypatch.setenv("DATABASE_ASYNC_URL", "")
    monkeypatch.setenv("DATABASE_USE_ASYNC", "0")
    expected_env = _env_snapshot()

    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request("tests/test_testclient_database_isolation.py::env-restore"),
    )
    db_path = next(lifecycle)
    assert os.environ["DATABASE_URL"] == f"sqlite:///{db_path}"

    _finish_lifecycle(lifecycle)

    assert _env_snapshot() == expected_env
    assert core_db._RAW_ENGINE is not None
    assert str(core_db._RAW_ENGINE.url) == baseline_url


@pytest.mark.parametrize(
    ("active_source", "active_value"),
    (
        ("DATABASE_ASYNC_URL", "sqlite+aiosqlite:////tmp/active.sqlite"),
        ("DATABASE_USE_ASYNC", "1"),
        ("_ASYNC_ENGINE", object()),
        ("AsyncSessionLocal", object()),
        ("async_engine", object()),
    ),
)
def test_isolated_sqlite_database_fails_before_mutation_for_async_state(
    active_source: str,
    active_value: object,
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_ASYNC_URL", raising=False)
    monkeypatch.delenv("DATABASE_USE_ASYNC", raising=False)
    for attr_name in ("_ASYNC_ENGINE", "AsyncSessionLocal", "async_engine"):
        monkeypatch.setattr(core_db, attr_name, None, raising=True)

    if active_source in {"DATABASE_ASYNC_URL", "DATABASE_USE_ASYNC"}:
        monkeypatch.setenv(active_source, cast(str, active_value))
    else:
        monkeypatch.setattr(core_db, active_source, active_value, raising=True)

    expected_env = _env_snapshot()
    baseline_engine = core_db._RAW_ENGINE
    original_entries = tuple(tmp_path.iterdir())

    with pytest.raises(RuntimeError, match=re.escape(active_source)):
        request.getfixturevalue("isolated_sqlite_database")

    assert _env_snapshot() == expected_env
    assert core_db._RAW_ENGINE is baseline_engine
    assert tuple(tmp_path.iterdir()) == original_entries


def test_isolated_sqlite_database_rejects_query_delimiter_before_mutation(
    tmp_path: Path,
) -> None:
    unsafe_root = tmp_path / "unsafe?query"
    unsafe_root.mkdir()
    truncated_sibling = Path(str(unsafe_root).split("?", maxsplit=1)[0])
    expected_entries = tuple(tmp_path.iterdir())
    expected_env = _env_snapshot()
    baseline_engine = core_db._RAW_ENGINE
    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        unsafe_root,
        _fake_request("tests/test_testclient_database_isolation.py::query-delimiter"),
    )

    with pytest.raises(RuntimeError, match=r"refuses tmp_path containing '\?'"):
        next(lifecycle)

    assert tuple(unsafe_root.iterdir()) == ()
    assert not truncated_sibling.exists()
    assert tuple(tmp_path.iterdir()) == expected_entries
    assert _env_snapshot() == expected_env
    assert core_db._RAW_ENGINE is baseline_engine


@pytest.mark.parametrize(
    ("attribute_present", "unsupported_value"),
    (
        (False, None),
        (True, "not-an-integer"),
        (True, False),
        (True, 0),
    ),
    ids=("missing", "non-int", "bool", "zero"),
)
def test_isolated_sqlite_database_requires_nofollow_before_mutation(
    attribute_present: bool,
    unsupported_value: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_entries = tuple(tmp_path.iterdir())
    expected_env = _env_snapshot()
    baseline_engine = core_db._RAW_ENGINE
    if attribute_present:
        monkeypatch.setattr(conftest_module.os, "O_NOFOLLOW", unsupported_value, raising=True)
    else:
        monkeypatch.delattr(conftest_module.os, "O_NOFOLLOW", raising=True)
    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request("tests/test_testclient_database_isolation.py::missing-nofollow"),
    )

    with pytest.raises(RuntimeError, match=r"requires os\.O_NOFOLLOW support"):
        next(lifecycle)

    assert tuple(tmp_path.iterdir()) == expected_entries
    assert _env_snapshot() == expected_env
    assert core_db._RAW_ENGINE is baseline_engine


def test_isolated_sqlite_database_removes_exact_file_after_mode_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_env = _env_snapshot()
    baseline_engine = core_db._RAW_ENGINE
    tmp_root = tmp_path.resolve(strict=True)
    original_open = os.open
    original_fstat = os.fstat
    created_descriptor: int | None = None
    invalid_mode_returned = False

    def open_and_record_descriptor(
        path: Any,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal created_descriptor
        if dir_fd is None:
            file_descriptor = original_open(path, flags, mode)
        else:
            file_descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        candidate = Path(os.fsdecode(path))
        if candidate.parent == tmp_root and candidate.name.startswith("isolated-"):
            created_descriptor = file_descriptor
        return file_descriptor

    def fstat_with_invalid_mode(file_descriptor: int) -> Any:
        nonlocal invalid_mode_returned
        actual = original_fstat(file_descriptor)
        if file_descriptor != created_descriptor or invalid_mode_returned:
            return actual
        invalid_mode_returned = True
        return SimpleNamespace(
            st_mode=(actual.st_mode & ~0o777) | 0o644,
            st_dev=actual.st_dev,
            st_ino=actual.st_ino,
        )

    monkeypatch.setattr(conftest_module.os, "open", open_and_record_descriptor)
    monkeypatch.setattr(conftest_module.os, "fstat", fstat_with_invalid_mode)
    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request("tests/test_testclient_database_isolation.py::invalid-created-mode"),
    )

    with pytest.raises(
        RuntimeError,
        match="regular file created with exact mode 0600",
    ) as error_info:
        next(lifecycle)

    assert error_info.value.__cause__ is None
    assert tuple(tmp_path.iterdir()) == ()
    assert _env_snapshot() == expected_env
    assert core_db._RAW_ENGINE is baseline_engine
    assert created_descriptor is not None
    assert invalid_mode_returned


@pytest.mark.parametrize("failure_phase", ("setup", "body"))
def test_primary_failure_survives_cleanup_failure_and_baseline_is_restored(
    failure_phase: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_env = _env_snapshot()
    baseline_url = os.environ["DATABASE_URL"]
    primary = _PrimaryIsolationFailure(f"primary {failure_phase} failure")
    original_init = core_db.init_db
    origin_code: Any

    if failure_phase == "setup":
        init_calls = 0

        def init_with_primary_failure() -> Any:
            nonlocal init_calls
            init_calls += 1
            if init_calls == 1:
                raise primary
            return original_init()

        origin_code = init_with_primary_failure.__code__
        monkeypatch.setattr(core_db, "init_db", init_with_primary_failure)

    def fail_owned_unlink(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic cleanup failure")

    monkeypatch.setattr(
        conftest_module,
        "_unlink_owned_isolated_sqlite_file",
        fail_owned_unlink,
    )
    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request(f"tests/test_testclient_database_isolation.py::primary-{failure_phase}"),
    )

    try:
        if failure_phase == "setup":
            with pytest.raises(_PrimaryIsolationFailure) as error_info:
                next(lifecycle)
        else:
            next(lifecycle)

            def raise_body_primary() -> None:
                raise primary

            origin_code = raise_body_primary.__code__
            try:
                raise_body_primary()
            except _PrimaryIsolationFailure:
                pass

            with pytest.raises(_PrimaryIsolationFailure) as error_info:
                lifecycle.throw(primary)

        raised = error_info.value
        assert raised is primary
        assert type(raised) is _PrimaryIsolationFailure
        assert str(raised) == f"primary {failure_phase} failure"
        assert isinstance(raised.__cause__, ExceptionGroup)
        assert len(raised.__cause__.exceptions) == 1
        assert str(raised.__cause__.exceptions[0]) == "synthetic cleanup failure"
        assert _traceback_contains_code(raised, origin_code)
        assert _env_snapshot() == expected_env
        assert core_db._RAW_ENGINE is not None
        assert str(core_db._RAW_ENGINE.url) == baseline_url
    finally:
        for db_path in tmp_path.glob("isolated-*.sqlite3"):
            db_path.unlink(missing_ok=True)


def test_isolated_sqlite_database_item_alpha(
    isolated_sqlite_database: Path,
) -> None:
    del isolated_sqlite_database
    _assert_insert_isolated_user("tc1b-alpha@example.test", "tc1b-beta@example.test")


def test_isolated_sqlite_database_item_beta(
    isolated_sqlite_database: Path,
) -> None:
    del isolated_sqlite_database
    _assert_insert_isolated_user("tc1b-beta@example.test", "tc1b-alpha@example.test")


def test_isolated_client_shutdown_precedes_database_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_reset = core_db.reset_db_for_tests

    def recording_reset() -> None:
        events.append("reset")
        original_reset()

    monkeypatch.setattr(core_db, "reset_db_for_tests", recording_reset)
    db_lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request("tests/test_testclient_database_isolation.py::shutdown-order"),
    )
    db_path = next(db_lifecycle)
    events.clear()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> Any:
        yield
        events.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    with conftest_module.open_test_client(app):
        pass
    _finish_lifecycle(db_lifecycle)

    assert events[0] == "shutdown"
    assert "reset" in events[1:]


@pytest.mark.parametrize("replacement_kind", ("symlink", "different-inode"))
def test_isolated_sqlite_database_refuses_replacement_cleanup(
    replacement_kind: str,
    tmp_path: Path,
) -> None:
    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request(f"tests/test_testclient_database_isolation.py::{replacement_kind}"),
    )
    db_path = next(lifecycle)
    target_path = tmp_path / f"{replacement_kind}-target.sqlite3"

    try:
        target_path.write_bytes(b"replacement")
        if replacement_kind == "symlink":
            db_path.unlink()
            db_path.symlink_to(target_path)
        else:
            os.replace(target_path, db_path)

        with pytest.raises(ExceptionGroup) as error_info:
            next(lifecycle)

        assert "Refusing to unlink replaced isolated SQLite file" in str(
            error_info.value.exceptions[0]
        )
        assert db_path.exists() or db_path.is_symlink()
        if replacement_kind == "symlink":
            assert db_path.is_symlink()
            assert target_path.read_bytes() == b"replacement"
        else:
            assert db_path.read_bytes() == b"replacement"
    finally:
        db_path.unlink(missing_ok=True)
        target_path.unlink(missing_ok=True)


def test_isolated_sqlite_database_cleanup_failure_still_restores_and_reinitializes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_url = os.environ["DATABASE_URL"]
    expected_env = _env_snapshot()
    lifecycle = conftest_module._isolated_sqlite_database_lifecycle(
        tmp_path,
        _fake_request("tests/test_testclient_database_isolation.py::cleanup-failure"),
    )
    db_path = next(lifecycle)

    def fail_unlink(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic owned-file cleanup failure")

    monkeypatch.setattr(conftest_module, "_unlink_owned_isolated_sqlite_file", fail_unlink)
    try:
        with pytest.raises(ExceptionGroup, match="isolated_sqlite_database cleanup failed"):
            next(lifecycle)

        assert _env_snapshot() == expected_env
        assert core_db._RAW_ENGINE is not None
        assert str(core_db._RAW_ENGINE.url) == baseline_url
        assert db_path.exists()
    finally:
        db_path.unlink(missing_ok=True)
