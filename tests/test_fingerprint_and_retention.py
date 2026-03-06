from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

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


def test_fingerprint_changes_when_source_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Different inputs must produce different pseudonymous fingerprints."""
    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, "stable-salt")
    fingerprint_security._get_salt.cache_clear()

    first = fingerprint_security.compute_fingerprint("client-ip-a", truncate=16)
    second = fingerprint_security.compute_fingerprint("client-ip-b", truncate=16)

    assert first != second
    fingerprint_security._get_salt.cache_clear()


def test_fingerprint_changes_when_salt_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing salt must change the fingerprint for the same source."""
    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, "salt-a")
    fingerprint_security._get_salt.cache_clear()
    first = fingerprint_security.compute_fingerprint("client-ip", truncate=16)

    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, "salt-b")
    fingerprint_security._get_salt.cache_clear()
    second = fingerprint_security.compute_fingerprint("client-ip", truncate=16)

    assert first != second
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

    # Store the original chmod for targeted patching
    original_chmod = Path.chmod
    chmod_call_count = 0

    def selective_chmod_error(self: Path, mode: int) -> None:
        """Raise OSError only for the specific salt_file, allow others."""
        nonlocal chmod_call_count
        chmod_call_count += 1
        if self == salt_file:
            raise OSError("no chmod")
        # Allow chmod to proceed for other Path instances
        original_chmod(self, mode)

    # Patch Path.chmod but only affect the specific salt_file
    with patch.object(Path, "chmod", selective_chmod_error):
        first = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
        fingerprint_security._get_salt.cache_clear()
        second = fingerprint_security.compute_fingerprint("client-ip", truncate=8)

    assert first == second
    assert chmod_call_count > 0, "chmod should have been called"
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
        assert mock_loader.called
        assert isinstance(salt, str)
        assert len(salt) > 0

        # Compute fingerprint while mock is still active
        fp = fingerprint_security.compute_fingerprint("client-ip", truncate=8)
        assert isinstance(fp, str)
        assert fp != ""

    # Clear cache after all assertions that depend on the mocked loader
    fingerprint_security._get_salt.cache_clear()


def test_fingerprint_empty_source_returns_empty_string() -> None:
    """compute_fingerprint returns empty string for empty source."""
    assert fingerprint_security.compute_fingerprint("") == ""
    assert fingerprint_security.compute_fingerprint("", truncate=16) == ""


def test_fingerprint_truncate_zero_returns_full_digest() -> None:
    """truncate=0 should return the full HMAC-SHA256 hex digest."""
    fp = fingerprint_security.compute_fingerprint("test-data", truncate=0)
    assert len(fp) == 64
    assert isinstance(fp, str)


def test_fingerprint_negative_truncate_raises_value_error() -> None:
    """Negative truncate should raise ValueError with clear message."""
    with pytest.raises(ValueError, match=r"truncate must be non-negative, got -5"):
        fingerprint_security.compute_fingerprint("test-data", truncate=-5)

    with pytest.raises(ValueError, match=r"truncate must be non-negative"):
        fingerprint_security.compute_fingerprint("test-data", truncate=-1)


def test_fingerprint_truncate_larger_than_digest_returns_full() -> None:
    """truncate larger than digest length should return full digest (64 chars)."""
    fp = fingerprint_security.compute_fingerprint("test-data", truncate=100)
    assert len(fp) == 64  # Returns full digest, not padded

    # Also test with 1000
    fp_large = fingerprint_security.compute_fingerprint("test-data", truncate=1000)
    assert len(fp_large) == 64


def test_fingerprint_long_salt_is_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    """Long salts remain supported and deterministic."""
    long_salt = "a" * 100

    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, long_salt)
    fingerprint_security._get_salt.cache_clear()

    first = fingerprint_security.compute_fingerprint("test-source", truncate=12)
    second = fingerprint_security.compute_fingerprint("test-source", truncate=12)
    assert isinstance(first, str)
    assert len(first) == 12
    assert first == second
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


def test_secret_marker_uses_pbkdf2_for_limited_input_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API-key style markers remain deterministic and salt-sensitive."""
    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, "secret-salt-a")
    fingerprint_security._get_salt.cache_clear()
    first = fingerprint_security.compute_secret_marker("api-key-123", truncate=32)
    repeat = fingerprint_security.compute_secret_marker("api-key-123", truncate=32)

    monkeypatch.setenv(fingerprint_security.SALT_ENV_VAR, "secret-salt-b")
    fingerprint_security._get_salt.cache_clear()
    changed = fingerprint_security.compute_secret_marker("api-key-123", truncate=32)

    assert first == repeat
    assert first != changed
    assert len(first) == 32
    fingerprint_security._get_salt.cache_clear()


def test_secret_marker_empty_secret_returns_empty_string() -> None:
    """Empty limited-input secrets should not produce opaque markers."""
    assert fingerprint_security.compute_secret_marker("") == ""
    assert fingerprint_security.compute_secret_marker("", truncate=16) == ""


def test_secret_marker_negative_truncate_raises_value_error() -> None:
    """Negative truncate must fail fast for secret markers too."""
    with pytest.raises(ValueError, match=r"truncate must be non-negative, got -1"):
        fingerprint_security.compute_secret_marker("api-key-123", truncate=-1)


def test_log_retention_manager_properties() -> None:
    """Exercise property setters/getters and singleton creation.

    Saves and restores default retention periods to prevent test isolation issues.
    """
    mgr = log_retention.get_retention_manager()

    # Save original values for restoration
    original_pseudonymous = mgr.pseudonymous_retention_days
    original_public = mgr.public_retention_days
    original_sensitive = mgr.sensitive_retention_days

    try:
        # Test setters/getters
        mgr.pseudonymous_retention_days = 10
        mgr.public_retention_days = 20
        mgr.sensitive_retention_days = 5

        assert mgr.pseudonymous_retention_days == 10
        assert mgr.public_retention_days == 20
        assert mgr.sensitive_retention_days == 5
    finally:
        # Restore original values to maintain test isolation
        mgr.pseudonymous_retention_days = original_pseudonymous
        mgr.public_retention_days = original_public
        mgr.sensitive_retention_days = original_sensitive


def test_log_retention_cleanup_missing_root_returns_zero(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """cleanup_expired_logs returns 0 when log root does not exist."""
    mgr = log_retention.get_retention_manager()
    missing_root = tmp_path / "missing-retention-root"
    monkeypatch.setenv(mgr.LOG_ROOT_ENV, str(missing_root))
    with caplog.at_level("INFO"):
        deleted = mgr.cleanup_expired_logs()

    assert deleted == 0
    assert any("root directory not found" in rec.message for rec in caplog.records)
