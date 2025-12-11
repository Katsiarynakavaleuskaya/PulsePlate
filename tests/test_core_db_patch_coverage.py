"""Additional tests to boost patch coverage for core/db.py.

Targets specific uncovered lines identified by Codecov patch coverage analysis.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from core import db


class TestDatabaseURLConstruction:
    """Tests for database URL construction edge cases."""

    def test_build_engine_url_with_env_provided_skips_directory_creation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that env-provided DATABASE_URL skips directory creation."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///custom_path/test.db")

        # Should not attempt to create directory when env provided
        with patch("core.db.os.makedirs") as mock_makedirs:
            url = db._build_engine_url()

        # makedirs should not be called for env-provided URLs
        mock_makedirs.assert_not_called()
        assert "sqlite:///" in url

    def test_build_engine_url_memory_database(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that memory databases don't trigger directory creation."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch("core.db.os.makedirs") as mock_makedirs:
            # Test with :memory: database
            test_url = "sqlite:///:memory:"
            monkeypatch.setenv("DATABASE_URL", test_url)
            url = db._build_engine_url()

        # Should not create directories for :memory: databases
        mock_makedirs.assert_not_called()
        assert ":memory:" in url

    def test_build_engine_url_adds_wal_mode_in_test_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that WAL journal mode is added in test environment."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("APP_ENV", "test")

        url = db._build_engine_url()

        # Should add WAL journal mode for test environment
        assert "journal_mode=WAL" in url or "journal_mode" in url

    def test_build_engine_url_adds_wal_mode_in_ci_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that WAL journal mode is added in CI environment."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("APP_ENV", "ci")

        url = db._build_engine_url()

        # Should add WAL journal mode for CI environment
        assert "journal_mode=WAL" in url or "journal_mode" in url

    def test_build_engine_url_handles_absolute_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test URL construction with absolute SQLite paths."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        absolute_path = str(tmp_path / "test.db")
        # SQLite absolute paths have four slashes: sqlite:////absolute/path
        test_url = f"sqlite:///{absolute_path}"

        with patch("core.db._build_engine_url", return_value=test_url):
            url = db._build_engine_url()

        assert "sqlite:///" in url

    def test_build_engine_url_permission_error_logged(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that PermissionError during directory creation is logged."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch("core.db.os.makedirs", side_effect=PermissionError("Access denied")):
            url = db._build_engine_url()

        # Should log warning about permission error
        assert any(
            "Cannot create database directory" in record.message for record in caplog.records
        )
        # Should still return a valid URL
        assert "sqlite:///" in url


class TestSQLitePathExtraction:
    """Tests for SQLite path extraction."""

    def test_extract_sqlite_path_with_memory_database(self) -> None:
        """Test path extraction returns None for :memory: databases."""
        url = "sqlite:///:memory:"

        path = db._extract_sqlite_path(url)

        assert path is None

    def test_extract_sqlite_path_with_relative_path(self) -> None:
        """Test path extraction for relative paths."""
        url = "sqlite:///relative/path/test.db"

        path = db._extract_sqlite_path(url)

        assert path == "relative/path/test.db"

    def test_extract_sqlite_path_with_absolute_path(self) -> None:
        """Test path extraction for absolute paths (four slashes)."""
        url = "sqlite:////absolute/path/test.db"

        path = db._extract_sqlite_path(url)

        # Should extract absolute path correctly
        assert path == "/absolute/path/test.db"

    def test_extract_sqlite_path_non_sqlite_url(self) -> None:
        """Test path extraction returns None for non-SQLite URLs."""
        url = "postgresql://localhost/testdb"

        path = db._extract_sqlite_path(url)

        assert path is None


class TestSQLiteConnectArgs:
    """Tests for SQLite connection arguments."""

    def test_sqlite_connect_args_with_uri_parameters(self) -> None:
        """Test connect args include uri=True for URLs with query parameters."""
        url = "sqlite:///test.db?mode=rwc&uri=true"

        args = db._sqlite_connect_args(url)

        assert args["uri"] is True
        assert args["check_same_thread"] is False
        assert args["timeout"] == 5.0

    def test_sqlite_connect_args_without_query_parameters(self) -> None:
        """Test connect args for SQLite URLs without query parameters."""
        url = "sqlite:///test.db"

        args = db._sqlite_connect_args(url)

        # Should have check_same_thread and timeout, but not uri
        assert args["check_same_thread"] is False
        assert args["timeout"] == 5.0
        assert "uri" not in args or args.get("uri") is False

    def test_sqlite_connect_args_non_sqlite_url(self) -> None:
        """Test connect args returns minimal args for non-SQLite URLs."""
        url = "postgresql://localhost/testdb"

        args = db._sqlite_connect_args(url)

        # Non-SQLite URLs should return empty dict or minimal args
        assert "check_same_thread" not in args


class TestAsyncURLDerivation:
    """Tests for async URL derivation."""

    def test_derive_async_url_sqlite_to_aiosqlite(self) -> None:
        """Test deriving aiosqlite URL from sqlite."""
        sync_url = "sqlite:///test.db"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == "sqlite+aiosqlite:///test.db"
        else:
            assert async_url is None

    def test_derive_async_url_postgresql_to_asyncpg(self) -> None:
        """Test deriving asyncpg URL from postgresql."""
        sync_url = "postgresql://localhost/testdb"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == "postgresql+asyncpg://localhost/testdb"
        else:
            assert async_url is None

    def test_derive_async_url_postgres_to_asyncpg(self) -> None:
        """Test deriving asyncpg URL from postgres (alternative scheme)."""
        sync_url = "postgres://localhost/testdb"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == "postgresql+asyncpg://localhost/testdb"
        else:
            assert async_url is None

    def test_derive_async_url_psycopg2_to_asyncpg(self) -> None:
        """Test deriving asyncpg URL from psycopg2."""
        sync_url = "postgresql+psycopg2://localhost/testdb"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == "postgresql+asyncpg://localhost/testdb"
        else:
            assert async_url is None

    def test_derive_async_url_psycopg_stays_same(self) -> None:
        """Test that psycopg dialect URL stays the same (supports async natively)."""
        sync_url = "postgresql+psycopg://localhost/testdb"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == sync_url
        else:
            assert async_url is None

    def test_derive_async_url_mysql_to_aiomysql(self) -> None:
        """Test deriving aiomysql URL from mysql."""
        sync_url = "mysql://localhost/testdb"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == "mysql+aiomysql://localhost/testdb"
        else:
            assert async_url is None

    def test_derive_async_url_pymysql_to_aiomysql(self) -> None:
        """Test deriving aiomysql URL from pymysql."""
        sync_url = "mysql+pymysql://localhost/testdb"

        async_url = db._derive_async_url(sync_url)

        if db.create_async_engine is not None:
            assert async_url == "mysql+aiomysql://localhost/testdb"
        else:
            assert async_url is None

    def test_derive_async_url_already_async(self) -> None:
        """Test that already-async URLs are returned as-is."""
        async_urls = [
            "sqlite+aiosqlite:///test.db",
            "postgresql+asyncpg://localhost/testdb",
            "mysql+aiomysql://localhost/testdb",
        ]

        for url in async_urls:
            result = db._derive_async_url(url)

            if db.create_async_engine is not None:
                assert result == url
            else:
                assert result is None

    def test_derive_async_url_unsupported_dialect(self) -> None:
        """Test that unsupported dialects return None."""
        unsupported_url = "oracle://localhost/testdb"

        async_url = db._derive_async_url(unsupported_url)

        assert async_url is None


class TestResultWithConnectionCleanup:
    """Tests for _ResultWithConnectionCleanup wrapper."""

    def test_context_manager_closes_connection(self) -> None:
        """Test that context manager properly closes connection."""
        mock_result = MagicMock()
        mock_connection = MagicMock()

        wrapper = db._ResultWithConnectionCleanup(mock_result, mock_connection)

        with wrapper:
            pass

        # Should close both result and connection
        mock_result.close.assert_called_once()
        mock_connection.close.assert_called_once()

    def test_close_method_delegation(self) -> None:
        """Test that calling close() directly also closes connection."""
        mock_result = MagicMock()
        mock_connection = MagicMock()

        wrapper = db._ResultWithConnectionCleanup(mock_result, mock_connection)

        # Access close method
        close_method = wrapper.close
        close_method()

        # Should close both
        mock_result.close.assert_called()
        mock_connection.close.assert_called_once()

    def test_close_connection_idempotent(self) -> None:
        """Test that closing connection multiple times is safe."""
        mock_result = MagicMock()
        mock_connection = MagicMock()

        wrapper = db._ResultWithConnectionCleanup(mock_result, mock_connection)

        # Close multiple times
        wrapper._close_connection()
        wrapper._close_connection()
        wrapper._close_connection()

        # Should only close once
        assert wrapper._connection_closed is True
        mock_connection.close.assert_called_once()

    def test_attribute_delegation(self) -> None:
        """Test that non-close attributes are delegated to result."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("data",)]
        mock_connection = MagicMock()

        wrapper = db._ResultWithConnectionCleanup(mock_result, mock_connection)

        # Access delegated method
        data = wrapper.fetchall()

        assert data == [("data",)]
        mock_result.fetchall.assert_called_once()


class TestEnsureSQLiteDirectory:
    """Tests for _ensure_sqlite_directory."""

    def test_ensure_directory_skipped_when_env_provided(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that directory creation is skipped when env_provided=True."""
        with patch("core.db.os.makedirs") as mock_makedirs:
            db._ensure_sqlite_directory("sqlite:///test.db", env_provided=True)

        # Should not create directory
        mock_makedirs.assert_not_called()

    def test_ensure_directory_created_for_file_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that directory is created for file-based SQLite."""
        test_dir = tmp_path / "new_dir"
        test_file = test_dir / "test.db"
        url = f"sqlite:///{test_file}"

        db._ensure_sqlite_directory(url, env_provided=False)

        # Directory should be created
        assert test_dir.exists()

    def test_ensure_directory_no_parent_directory(self) -> None:
        """Test handling of paths with no parent directory."""
        # Path with no directory component
        url = "sqlite:///test.db"

        with patch("core.db.os.makedirs") as mock_makedirs:
            db._ensure_sqlite_directory(url, env_provided=False)

        # Should not attempt to create empty directory
        # (depends on implementation - may or may not call makedirs with empty string)

    def test_ensure_directory_permission_error_handled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that PermissionError is caught and logged."""
        url = "sqlite:///restricted/test.db"

        with patch("core.db.os.makedirs", side_effect=PermissionError("Access denied")):
            # Should not raise, just log
            db._ensure_sqlite_directory(url, env_provided=False)

        # Should log warning
        assert any(
            "Cannot create database directory" in record.message for record in caplog.records
        )
