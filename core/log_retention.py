"""Log retention policy management for GDPR/privacy compliance.

Manages automatic cleanup of logs based on data classification and retention periods.
"""

from enum import Enum
import logging
from pathlib import Path
import threading
import time
from typing import Dict, Optional
import os

# Module-level logger
logger = logging.getLogger(__name__)


class DataClass(Enum):
    """Data classification levels for retention policy.

    Based on GDPR Article 30 data processing categories.
    """

    PSEUDONYMOUS = "PSEUDONYMOUS"  # Pseudonymized data (longer retention)
    PUBLIC = "PUBLIC"  # Public non-personal data (longest retention)
    SENSITIVE = "SENSITIVE"  # Sensitive personal data (shortest retention)


# Default data class for logs without explicit classification
DATA_CLASS_PSEUDONYMOUS: DataClass = DataClass.PSEUDONYMOUS


class LogRetentionManager:
    """Manages log file retention and cleanup based on data classification."""

    LOG_ROOT_ENV = "LOG_RETENTION_ROOT"
    DEFAULT_LOG_ROOT = Path("logs")

    def __init__(self) -> None:
        """Initialize retention manager with default policies."""
        # Retention periods in days by data class (private to enforce validation)
        self._retention_periods: Dict[DataClass, int] = {
            DataClass.PUBLIC: 365,  # 1 year for public data
            DataClass.PSEUDONYMOUS: 180,  # 6 months for pseudonymized
            DataClass.SENSITIVE: 90,  # 3 months for sensitive data
        }

    def _set_retention(self, data_class: DataClass, days: int) -> None:
        """Set retention period with validation.

        Args:
            data_class: Data classification level
            days: Retention period in days (must be >= 0)

        Raises:
            ValueError: If days is negative or cannot be converted to int
        """
        try:
            days_int = int(days)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Retention days for {data_class.value} must be an integer, got {type(days).__name__}: {days}"
            ) from e

        if days_int < 0:
            raise ValueError(f"Retention days for {data_class.value} must be >= 0, got {days_int}")

        self._retention_periods[data_class] = days_int

    # Backwards-compatible properties used by the app/tests:
    @property
    def pseudonymous_retention_days(self) -> int:
        return self._retention_periods[DataClass.PSEUDONYMOUS]

    @pseudonymous_retention_days.setter
    def pseudonymous_retention_days(self, days: int) -> None:
        self._set_retention(DataClass.PSEUDONYMOUS, days)

    @property
    def public_retention_days(self) -> int:
        return self._retention_periods[DataClass.PUBLIC]

    @public_retention_days.setter
    def public_retention_days(self, days: int) -> None:
        self._set_retention(DataClass.PUBLIC, days)

    @property
    def sensitive_retention_days(self) -> int:
        return self._retention_periods[DataClass.SENSITIVE]

    @sensitive_retention_days.setter
    def sensitive_retention_days(self, days: int) -> None:
        self._set_retention(DataClass.SENSITIVE, days)

    @staticmethod
    def _is_within_root(path: Path, root: Path) -> bool:
        """Return True if path is under root after symlink resolution."""
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except (ValueError, OSError, RuntimeError):
            return False

    def _resolve_log_root(self) -> Path:
        """Resolve configured log root directory."""
        raw_path = os.getenv(self.LOG_ROOT_ENV, "").strip()
        if raw_path:
            return Path(raw_path).expanduser().resolve()
        return self.DEFAULT_LOG_ROOT.resolve()

    @staticmethod
    def _classify_file(path: Path, root: Path) -> DataClass:
        """Infer data class from path segments; default to pseudonymous."""
        try:
            parts = [part.lower() for part in path.resolve().relative_to(root.resolve()).parts]
        except (ValueError, OSError, RuntimeError):
            return DATA_CLASS_PSEUDONYMOUS

        if DataClass.SENSITIVE.value.lower() in parts:
            return DataClass.SENSITIVE
        if DataClass.PUBLIC.value.lower() in parts:
            return DataClass.PUBLIC
        if DataClass.PSEUDONYMOUS.value.lower() in parts:
            return DataClass.PSEUDONYMOUS
        return DATA_CLASS_PSEUDONYMOUS

    def cleanup_expired_logs(
        self, data_class: Optional[DataClass] = None, *, dry_run: bool = False
    ) -> int:
        """Clean up expired log files based on retention policy.

        Args:
            data_class: Optional data class filter. If None, process all classes.
            dry_run: If True, count deletions without removing files.

        Returns:
            Number of deleted log files
        """
        root = self._resolve_log_root()
        if not root.exists() or not root.is_dir():
            logger.info("Log cleanup skipped: root directory not found (%s)", root)
            return 0

        now_ts = time.time()
        deleted_count = 0
        data_class_str = data_class.value if data_class else "ALL"

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if not self._is_within_root(file_path, root):
                logger.warning("Skipping file outside retention root: %s", file_path)
                continue

            file_data_class = self._classify_file(file_path, root)
            if data_class is not None and file_data_class != data_class:
                continue

            retention_days = self._retention_periods[file_data_class]
            retention_seconds = retention_days * 24 * 60 * 60

            try:
                file_age_seconds = max(0.0, now_ts - file_path.stat().st_mtime)
            except OSError:
                logger.warning("Cannot stat file during log cleanup: %s", file_path)
                continue

            if file_age_seconds <= retention_seconds:
                continue

            if dry_run:
                deleted_count += 1
                continue

            try:
                file_path.unlink()
                deleted_count += 1
            except OSError:
                logger.warning("Cannot delete expired log file: %s", file_path)

        logger.info(
            "Log cleanup completed: deleted=%d, dry_run=%s, data_class=%s, root=%s",
            deleted_count,
            dry_run,
            data_class_str,
            root,
        )
        return deleted_count


# Global singleton instance
_retention_manager: Optional[LogRetentionManager] = None
_lock = threading.Lock()


def get_retention_manager() -> LogRetentionManager:
    """Get or create the global retention manager instance.

    Returns:
        Global LogRetentionManager singleton
    """
    global _retention_manager
    with _lock:
        if _retention_manager is None:
            _retention_manager = LogRetentionManager()
    return _retention_manager
