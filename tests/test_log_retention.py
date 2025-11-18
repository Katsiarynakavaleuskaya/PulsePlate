import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core import log_retention


def _create_log(path: Path, days_old: int, content: str = "log") -> None:
    path.write_text(content)
    past = datetime.now() - timedelta(days=days_old)
    timestamp = past.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_classification_and_retention(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    manager = log_retention.LogRetentionManager(
        tmp_path,
        pseudonymous_retention_days=1,
        public_retention_days=10,
        sensitive_retention_days=5,
    )
    caplog.set_level(logging.INFO, logger="core.log_retention.audit")

    pseudonymous = tmp_path / "client_fingerprint.log"
    public_log = tmp_path / "public.log"

    _create_log(pseudonymous, days_old=2)
    _create_log(public_log, days_old=0)

    deleted = manager.cleanup_expired_logs()

    assert deleted == 1
    assert not pseudonymous.exists()
    assert public_log.exists()
    assert any("LOG_ACCESS_AUDIT" in record.msg for record in caplog.records)


def test_should_retain_and_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = log_retention.LogRetentionManager(tmp_path, public_retention_days=1)
    log_file = tmp_path / "public.log"
    _create_log(log_file, days_old=0)

    assert manager.should_retain_log(log_file, log_retention.DATA_CLASS_PUBLIC) is True

    original_stat = Path.stat

    state = {"calls": 0}

    def _boom(self: Path, follow_symlinks: bool = True) -> os.stat_result:
        if self == log_file:
            state["calls"] += 1
            if state["calls"] > 1:
                raise OSError("stat failed")
        return original_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", _boom)
    assert manager.should_retain_log(log_file, log_retention.DATA_CLASS_PUBLIC) is True


def test_cleanup_with_filter(tmp_path: Path) -> None:
    manager = log_retention.LogRetentionManager(tmp_path, sensitive_retention_days=1)
    sensitive = tmp_path / "sensitive_data.log"
    public_log = tmp_path / "info.log"
    _create_log(sensitive, days_old=2)
    _create_log(public_log, days_old=2)

    deleted = manager.cleanup_expired_logs(data_class=log_retention.DATA_CLASS_SENSITIVE)
    assert deleted == 1
    assert not sensitive.exists()
    assert public_log.exists()


def test_audit_helpers_and_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    manager = log_retention.LogRetentionManager(tmp_path)

    with caplog.at_level(logging.INFO, logger="core.log_retention.audit"):
        manager.audit_log_read(
            "/tmp/test.log", log_retention.DATA_CLASS_PSEUDONYMOUS, requester="admin"
        )
    assert any("LOG_ACCESS_AUDIT" in record.msg for record in caplog.records)

    assert log_retention.get_retention_manager() is log_retention.get_retention_manager()

    monkeypatch.setattr(log_retention, "_retention_manager", None)
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    mgr = log_retention.get_retention_manager()
    assert isinstance(mgr, log_retention.LogRetentionManager)
