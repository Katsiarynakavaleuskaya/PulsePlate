"""
Realistic tests for core/db.py using Faker-backed inputs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from faker import Faker
from sqlalchemy.pool import NullPool

import core.db as core_db

fake = Faker()


class TestDbRealisticCoverage:
    """Exercise realistic DB helper scenarios against exported core.db behavior."""

    def setup_method(self) -> None:
        Faker.seed(42)
        core_db.reset_db_for_tests()

    def teardown_method(self) -> None:
        core_db.reset_db_for_tests()

    def test_extract_sqlite_path_handles_realistic_urls(self) -> None:
        relative_name = fake.file_name(extension="db")
        absolute_path = Path("/tmp") / fake.file_name(extension="sqlite3")
        absolute_result = core_db._extract_sqlite_path(f"sqlite:////{absolute_path}")

        assert core_db._extract_sqlite_path(f"sqlite:///{relative_name}") == relative_name
        assert absolute_result is not None
        assert absolute_result.startswith("/")
        assert absolute_result.endswith(str(absolute_path).lstrip("/"))

    def test_extract_sqlite_path_rejects_non_sqlite_and_memory(self) -> None:
        assert core_db._extract_sqlite_path("sqlite:///:memory:") is None
        assert core_db._extract_sqlite_path(f"postgresql:///{fake.slug()}") is None

    def test_sqlite_connect_args_enable_uri_and_timeout(self) -> None:
        args = core_db._sqlite_connect_args("sqlite:///cache/app.db?mode=rwc&uri=true")

        assert args["check_same_thread"] is False
        assert args["uri"] is True
        assert args["timeout"] == 5.0

    def test_get_sqlite_poolclass_returns_nullpool_for_test_sqlite(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

        pool_class = core_db._get_sqlite_poolclass(f"sqlite:///{fake.file_name(extension='db')}")

        assert pool_class is NullPool

    def test_get_sqlite_poolclass_skips_non_test_runtime(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

        pool_class = core_db._get_sqlite_poolclass(f"sqlite:///{fake.file_name(extension='db')}")

        assert pool_class is None

    def test_build_engine_url_preserves_env_sqlite_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        db_path = tmp_path / fake.file_name(extension="db")
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

        url = core_db._build_engine_url()

        assert str(db_path) in url
        assert "mode=rwc" not in url

    def test_init_db_creates_file_backed_sqlite_engine(self, tmp_path: Path) -> None:
        db_path = tmp_path / fake.file_name(extension="db")

        engine = core_db.init_db(f"sqlite:///{db_path}")

        try:
            assert engine.url.database is not None
            assert engine.url.database.endswith(db_path.name)
            assert db_path.exists()
        finally:
            engine.dispose()

    def test_create_tables_is_idempotent_after_init(self, tmp_path: Path) -> None:
        db_path = tmp_path / fake.file_name(extension="db")
        engine = core_db.init_db(f"sqlite:///{db_path}")

        try:
            core_db.create_tables()
            core_db.create_tables()
        finally:
            engine.dispose()
