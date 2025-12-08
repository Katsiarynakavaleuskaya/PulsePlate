"""Log retention policy management for GDPR/privacy compliance.

Manages automatic cleanup of logs based on data classification and retention periods.

Note: cleanup_expired_logs is a stub that logs a warning and returns 0 (no files deleted).
"""

from enum import Enum
from typing import Dict, Optional
import logging
import threading

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

    def cleanup_expired_logs(self, data_class: Optional[DataClass] = None) -> int:
        """Clean up expired log files based on retention policy.

        Args:
            data_class: Optional data class filter. If None, process all classes.

        Returns:
            Number of deleted log files
        """
        # Non-destructive stub: log cleanup not yet implemented
        # Return 0 to indicate no files deleted (safe default)
        data_class_str = data_class.value if data_class else "all"
        logger.warning(
            "Log cleanup not implemented for data_class=%s - returning 0 (no files deleted). "
            "Implement real deletion logic against log directory using retention_periods.",
            data_class_str,
        )
        return 0


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
