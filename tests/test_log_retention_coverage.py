from pathlib import Path
import os

import pytest

from core.log_retention import DataClass, LogRetentionManager, get_retention_manager


def test_log_retention_invalid_days_type_raises() -> None:
    manager: LogRetentionManager = LogRetentionManager()
    with pytest.raises(ValueError) as exc_info:
        manager.public_retention_days = "thirty"  # type: ignore[assignment]
    message = str(exc_info.value)
    assert "must be an integer" in message
    assert DataClass.PUBLIC.value in message


def test_log_retention_manager_singleton() -> None:
    """Test that get_retention_manager() returns the same instance (singleton behavior)."""
    manager: LogRetentionManager = get_retention_manager()
    same_manager: LogRetentionManager = get_retention_manager()
    # Verify singleton semantics: both calls return the same instance
    assert manager is same_manager


def test_log_retention_negative_days_raises() -> None:
    """Test that setting negative retention days raises ValueError."""
    manager: LogRetentionManager = get_retention_manager()
    with pytest.raises(ValueError) as exc_info:
        manager.sensitive_retention_days = -1
    message = str(exc_info.value)
    assert "must be >= 0" in message
    assert DataClass.SENSITIVE.value in message


def _create_log_file(path: Path, age_days: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("log-entry", encoding="utf-8")
    expired_ts = path.stat().st_mtime - (age_days * 24 * 60 * 60)
    os.utime(path, (expired_ts, expired_ts))


def test_log_retention_cleanup_dry_run_counts_without_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = LogRetentionManager()
    manager.pseudonymous_retention_days = 1
    log_file = tmp_path / "pseudonymous" / "req.log"
    _create_log_file(log_file, age_days=3)

    monkeypatch.setenv(manager.LOG_ROOT_ENV, str(tmp_path))
    deleted = manager.cleanup_expired_logs(dry_run=True)

    assert deleted == 1
    assert log_file.exists()


def test_log_retention_cleanup_deletes_only_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = LogRetentionManager()
    manager.public_retention_days = 10
    old_file = tmp_path / "public" / "old.log"
    fresh_file = tmp_path / "public" / "fresh.log"
    _create_log_file(old_file, age_days=40)
    _create_log_file(fresh_file, age_days=1)

    monkeypatch.setenv(manager.LOG_ROOT_ENV, str(tmp_path))
    deleted = manager.cleanup_expired_logs(data_class=DataClass.PUBLIC)

    assert deleted == 1
    assert not old_file.exists()
    assert fresh_file.exists()


def test_log_retention_cleanup_respects_data_class_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = LogRetentionManager()
    manager.pseudonymous_retention_days = 1
    manager.sensitive_retention_days = 1
    pseudo_file = tmp_path / "pseudonymous" / "pseudo.log"
    sensitive_file = tmp_path / "sensitive" / "secret.log"
    _create_log_file(pseudo_file, age_days=5)
    _create_log_file(sensitive_file, age_days=5)

    monkeypatch.setenv(manager.LOG_ROOT_ENV, str(tmp_path))
    deleted = manager.cleanup_expired_logs(data_class=DataClass.SENSITIVE)

    assert deleted == 1
    assert pseudo_file.exists()
    assert not sensitive_file.exists()


def test_log_retention_cleanup_path_safety_skips_symlink_target_outside_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = LogRetentionManager()
    manager.pseudonymous_retention_days = 1
    outside_file = tmp_path / "outside.log"
    _create_log_file(outside_file, age_days=10)

    logs_root = tmp_path / "logs"
    symlink_path = logs_root / "pseudonymous" / "outside-link.log"
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        symlink_path.symlink_to(outside_file)
    except OSError:
        pytest.skip("Symlinks not supported on this filesystem")

    monkeypatch.setenv(manager.LOG_ROOT_ENV, str(logs_root))
    deleted = manager.cleanup_expired_logs()

    assert deleted == 0
    assert outside_file.exists()
    assert symlink_path.exists()


def test_log_retention_resolve_root_uses_default_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = LogRetentionManager()
    monkeypatch.delenv(manager.LOG_ROOT_ENV, raising=False)

    resolved = manager._resolve_log_root()

    assert resolved == manager.DEFAULT_LOG_ROOT.resolve()


def test_log_retention_classify_file_returns_default_on_relative_error(tmp_path: Path) -> None:
    manager = LogRetentionManager()
    outside_file = tmp_path / "outside.log"
    outside_file.write_text("x", encoding="utf-8")
    unrelated_root = tmp_path / "unrelated"
    unrelated_root.mkdir()

    assert manager._classify_file(outside_file, unrelated_root) == DataClass.PSEUDONYMOUS


def test_log_retention_classify_file_returns_default_for_unknown_directory(tmp_path: Path) -> None:
    manager = LogRetentionManager()
    logs_root = tmp_path / "logs"
    unknown_file = logs_root / "misc" / "event.log"
    unknown_file.parent.mkdir(parents=True, exist_ok=True)
    unknown_file.write_text("entry", encoding="utf-8")

    assert manager._classify_file(unknown_file, logs_root) == DataClass.PSEUDONYMOUS


def test_log_retention_cleanup_skips_file_when_stat_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = LogRetentionManager()
    manager.pseudonymous_retention_days = 1
    target_file = tmp_path / "pseudonymous" / "bad-stat.log"
    _create_log_file(target_file, age_days=30)

    monkeypatch.setenv(manager.LOG_ROOT_ENV, str(tmp_path))
    original_stat = Path.stat
    original_is_file = Path.is_file

    def _patched_stat(self: Path, *args: object, **kwargs: object) -> os.stat_result:
        if self == target_file:
            raise OSError("stat failed")
        return original_stat(self, *args, **kwargs)

    def _patched_is_file(self: Path) -> bool:
        if self == target_file:
            return True
        return original_is_file(self)

    monkeypatch.setattr(Path, "stat", _patched_stat)
    monkeypatch.setattr(Path, "is_file", _patched_is_file)

    deleted = manager.cleanup_expired_logs()

    assert deleted == 0
    with pytest.raises(OSError, match="stat failed"):
        target_file.stat()


def test_log_retention_cleanup_handles_unlink_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = LogRetentionManager()
    manager.pseudonymous_retention_days = 1
    target_file = tmp_path / "pseudonymous" / "cannot-delete.log"
    _create_log_file(target_file, age_days=30)

    monkeypatch.setenv(manager.LOG_ROOT_ENV, str(tmp_path))
    original_unlink = Path.unlink

    def _patched_unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self == target_file:
            raise OSError("unlink failed")
        original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _patched_unlink)

    deleted = manager.cleanup_expired_logs()

    assert deleted == 0
    assert target_file.exists()
