from __future__ import annotations

import os
from pathlib import Path

import pytest
from unittest.mock import patch

from core import fingerprint_security
from core import log_retention


def test_fingerprint_uses_env_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """compute_fingerprint should respect environment-provided salt."""
    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, "abc123")
    fingerprint_security._get_salt.cache_clear()
    fp = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
    # Deterministic with same salt and source
    fp2 = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
    assert fp == fp2
    fingerprint_security._get_salt.cache_clear()


def test_fingerprint_creates_salt_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When no env salt is provided, module should create/read a salt file."""
    salt_file = tmp_path / "salt.txt"
    monkeypatch.delenv(fingerprint_security.SALT_ENV_VAR, raising=False)
    monkeypatch.setenv(fingerprint_security.SALT_FILE_ENV_VAR, str(salt_file))
    fingerprint_security._get_salt.cache_clear()

    first = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
    # Salt file should now exist and produce same fingerprint
    assert salt_file.exists()
    fingerprint_security._get_salt.cache_clear()
    second = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
    assert first == second
    fingerprint_security._get_salt.cache_clear()


def test_fingerprint_handles_file_exists_race_and_chmod_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_load_salt_from_file handles FileExistsError and chmod failures gracefully."""

    salt_file = tmp_path / "race_salt.txt"
    monkeypatch.delenv(fingerprint_security.SALT_ENV_VAR, raising=False)
    monkeypatch.setenv(fingerprint_security.SALT_FILE_ENV_VAR, str(salt_file))
    fingerprint_security._get_salt.cache_clear()

    # Pre-create an empty file so open("x") will raise FileExistsError
    salt_file.parent.mkdir(parents=True, exist_ok=True)
    salt_file.touch()

    with patch.object(Path, "chmod", side_effect=OSError("no chmod")) as mock_chmod:
        first = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
        fingerprint_security._get_salt.cache_clear()
        second = fingerprint_security.compute_fingerprint("client-ip", truncate=8)

    assert first == second
    assert mock_chmod.called
    fingerprint_security._get_salt.cache_clear()


def test_fingerprint_falls_back_when_salt_file_load_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_get_salt must return a value even if salt file loading fails."""

    salt_file = tmp_path / "broken_salt.txt"
    monkeypatch.delenv(fingerprint_security.SALT_ENV_VAR, raising=False)
    monkeypatch.setenv(fingerprint_security.SALT_FILE_ENV_VAR, str(salt_file))
    fingerprint_security._get_salt.cache_clear()

    with patch.object(
        fingerprint_security, "_load_salt_from_file", return_value=None
    ) as mock_loader:
        salt = fingerprint_security._get_salt()
        fingerprint_security._get_salt.cache_clear()

    assert mock_loader.called
    assert isinstance(salt, str)
    assert len(salt) > 0

    fp = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
    assert isinstance(fp, str)
    assert fp != ""


def test_fingerprint_empty_source_returns_empty_string() -> None:
    """compute_fingerprint returns empty string for empty source."""
    assert fingerprint_security.compute_fingerprint("") == ""
    assert fingerprint_security.compute_fingerprint("", truncate=16) == ""


def test_fingerprint_long_salt_hashed() -> None:
    """Salt longer than 32 bytes is hashed before use in blake2s."""
    # Force a very long salt via environment
    long_salt = "a" * 100

    os.environ[fingerprint_security.SALT_ENV_VAR] = long_salt
    fingerprint_security._get_salt.cache_clear()

    try:
        fp = fingerprint_security.compute_fingerprint("test-source", truncate=12)
        assert isinstance(fp, str)
        assert len(fp) == 12
    finally:
        del os.environ[fingerprint_security.SALT_ENV_VAR]
        fingerprint_security._get_salt.cache_clear()


def test_fingerprint_file_read_exception_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_load_salt_from_file returns None when file operations raise exceptions."""
    salt_file = tmp_path / "error_salt.txt"
    monkeypatch.delenv(fingerprint_security.SALT_ENV_VAR, raising=False)
    monkeypatch.setenv(fingerprint_security.SALT_FILE_ENV_VAR, str(salt_file))
    fingerprint_security._get_salt.cache_clear()

    # Force path.exists() to raise an exception
    with patch.object(Path, "exists", side_effect=OSError("disk error")):
        result = fingerprint_security._load_salt_from_file(salt_file)
        assert result is None

    fingerprint_security._get_salt.cache_clear()


def test_log_retention_manager_properties() -> None:
    """Exercise property setters/getters and singleton creation."""
    mgr = log_retention.get_retention_manager()
    mgr.pseudonymous_retention_days = 10
    mgr.public_retention_days = 20
    mgr.sensitive_retention_days = 5

    assert mgr.pseudonymous_retention_days == 10
    assert mgr.public_retention_days == 20
    assert mgr.sensitive_retention_days == 5


def test_log_retention_cleanup_stub(caplog: pytest.LogCaptureFixture) -> None:
    """cleanup_expired_logs should log warning and return 0."""
    mgr = log_retention.get_retention_manager()
    with caplog.at_level("WARNING"):
        deleted = mgr.cleanup_expired_logs()
    assert deleted == 0
    assert any("not implemented" in rec.message for rec in caplog.records)
