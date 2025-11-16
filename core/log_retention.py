"""
Log Retention and Data Classification Module.

RU: Модуль управления хранением логов и классификации данных.
EN: Log retention and data classification module.

This module provides:
- Data classification labels for logs containing pseudonymous identifiers
- Automatic log retention policy enforcement (TTL-based deletion)
- Access audit logging for log stores containing fingerprints
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Data classification labels
DATA_CLASS_PSEUDONYMOUS = "PSEUDONYMOUS"  # Contains pseudonymous identifiers
DATA_CLASS_PUBLIC = "PUBLIC"  # No sensitive data
DATA_CLASS_SENSITIVE = "SENSITIVE"  # Contains sensitive data

# Default retention periods (in days)
# Short TTL for logs containing pseudonymous identifiers per GDPR best practices
DEFAULT_PSEUDONYMOUS_RETENTION_DAYS = int(
    os.getenv("LOG_PSEUDONYMOUS_RETENTION_DAYS", "30")
)  # 30 days default, configurable
DEFAULT_PUBLIC_RETENTION_DAYS = int(os.getenv("LOG_PUBLIC_RETENTION_DAYS", "90"))
DEFAULT_SENSITIVE_RETENTION_DAYS = int(os.getenv("LOG_SENSITIVE_RETENTION_DAYS", "90"))


class LogRetentionManager:
    """Manages log retention policies and automatic deletion.

    RU: Управляет политиками хранения логов и автоматическим удалением.
    EN: Manages log retention policies and automatic deletion.
    """

    def __init__(
        self,
        logs_dir: Path | str,
        pseudonymous_retention_days: int = DEFAULT_PSEUDONYMOUS_RETENTION_DAYS,
        public_retention_days: int = DEFAULT_PUBLIC_RETENTION_DAYS,
        sensitive_retention_days: int = DEFAULT_SENSITIVE_RETENTION_DAYS,
    ) -> None:
        """Initialize log retention manager.

        Args:
            logs_dir: Directory containing log files
            pseudonymous_retention_days: Retention period for pseudonymous logs (days)
            public_retention_days: Retention period for public logs (days)
            sensitive_retention_days: Retention period for sensitive logs (days)
        """
        self.logs_dir = Path(logs_dir)
        self.pseudonymous_retention_days = pseudonymous_retention_days
        self.public_retention_days = public_retention_days
        self.sensitive_retention_days = sensitive_retention_days
        self.audit_logger = logging.getLogger(f"{__name__}.audit")

    def classify_log_entry(self, contains_fingerprint: bool) -> str:
        """Classify a log entry based on its content.

        Args:
            contains_fingerprint: Whether the log entry contains a client fingerprint

        Returns:
            Data classification label
        """
        if contains_fingerprint:
            return DATA_CLASS_PSEUDONYMOUS
        return DATA_CLASS_PUBLIC

    def get_retention_days(self, data_class: str) -> int:
        """Get retention period in days for a data classification.

        Args:
            data_class: Data classification label

        Returns:
            Retention period in days
        """
        if data_class == DATA_CLASS_PSEUDONYMOUS:
            return self.pseudonymous_retention_days
        if data_class == DATA_CLASS_SENSITIVE:
            return self.sensitive_retention_days
        return self.public_retention_days

    def should_retain_log(self, log_file: Path, data_class: str) -> bool:
        """Check if a log file should be retained based on its classification and age.

        Args:
            log_file: Path to log file
            data_class: Data classification label

        Returns:
            True if file should be retained, False if it should be deleted
        """
        if not log_file.exists():
            return False

        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            retention_days = self.get_retention_days(data_class)
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            return file_mtime > cutoff_date
        except OSError as e:
            logger.warning("Failed to check retention for %s: %s", log_file, e)
            return True  # Err on the side of caution

    def cleanup_expired_logs(self, data_class: Optional[str] = None) -> int:
        """Delete expired log files based on retention policy.

        Args:
            data_class: Optional data classification to filter by.
                       If None, processes all classifications.

        Returns:
            Number of files deleted
        """
        if not self.logs_dir.exists():
            return 0

        deleted_count = 0
        classifications_to_check = (
            [data_class]
            if data_class
            else [DATA_CLASS_PSEUDONYMOUS, DATA_CLASS_PUBLIC, DATA_CLASS_SENSITIVE]
        )

        for log_file in self.logs_dir.glob("*.log"):
            # Determine classification from filename or content
            file_class = self._infer_log_classification(log_file)

            if file_class not in classifications_to_check:
                continue

            if not self.should_retain_log(log_file, file_class):
                try:
                    log_file.unlink()
                    deleted_count += 1
                    self._audit_log_access(
                        "DELETE",
                        str(log_file),
                        file_class,
                        f"Expired log deleted (retention: {self.get_retention_days(file_class)} days)",
                    )
                    logger.info(
                        "Deleted expired log: %s (classification: %s)", log_file, file_class
                    )
                except OSError as e:
                    logger.error("Failed to delete expired log %s: %s", log_file, e)

        return deleted_count

    def _infer_log_classification(self, log_file: Path) -> str:
        """Infer log classification from filename or content.

        Args:
            log_file: Path to log file

        Returns:
            Data classification label
        """
        # Check filename for classification markers
        filename = log_file.name.lower()
        if "pseudonymous" in filename or "fingerprint" in filename or "client" in filename:
            return DATA_CLASS_PSEUDONYMOUS
        if "sensitive" in filename:
            return DATA_CLASS_SENSITIVE

        # Default to pseudonymous if we can't determine (safer default)
        # In production, logs with fingerprints should be explicitly named
        return DATA_CLASS_PSEUDONYMOUS

    def _audit_log_access(self, action: str, log_path: str, data_class: str, reason: str) -> None:
        """Log access to log files containing pseudonymous data for audit purposes.

        Args:
            action: Action performed (READ, DELETE, etc.)
            log_path: Path to log file
            data_class: Data classification label
            reason: Reason for access
        """
        # Only audit access to pseudonymous/sensitive logs
        if data_class in (DATA_CLASS_PSEUDONYMOUS, DATA_CLASS_SENSITIVE):
            self.audit_logger.info(
                "LOG_ACCESS_AUDIT: action=%s path=%s classification=%s reason=%s timestamp=%s",
                action,
                log_path,
                data_class,
                reason,
                datetime.utcnow().isoformat(),
            )

    def audit_log_read(
        self, log_path: str, data_class: str, requester: Optional[str] = None
    ) -> None:
        """Audit read access to log files.

        Args:
            log_path: Path to log file
            data_class: Data classification label
            requester: Optional identifier of the requester
        """
        reason = f"Read access by {requester}" if requester else "Read access"
        self._audit_log_access("READ", log_path, data_class, reason)


# Global instance (initialized on first use)
_retention_manager: Optional[LogRetentionManager] = None


def get_retention_manager() -> LogRetentionManager:
    """Get or create the global log retention manager.

    Returns:
        LogRetentionManager instance
    """
    global _retention_manager
    if _retention_manager is None:
        logs_dir = Path(os.getenv("LOG_DIR", "logs"))
        _retention_manager = LogRetentionManager(logs_dir)
    return _retention_manager
