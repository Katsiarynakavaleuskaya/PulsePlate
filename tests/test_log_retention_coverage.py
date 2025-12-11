import pytest

from core.log_retention import DataClass, LogRetentionManager, get_retention_manager


def test_log_retention_invalid_days_type_raises() -> None:
    manager: LogRetentionManager = LogRetentionManager()
    with pytest.raises(ValueError) as exc_info:
        manager.public_retention_days = "thirty"  # type: ignore[assignment]
    message = str(exc_info.value)
    assert "must be an integer" in message
    assert DataClass.PUBLIC.value in message


def test_log_retention_negative_days_raises_and_manager_singleton() -> None:
    manager = get_retention_manager()
    same_manager = get_retention_manager()
    # Verify singleton semantics: both calls return the same instance
    assert manager is same_manager

    with pytest.raises(ValueError) as exc_info:
        manager.sensitive_retention_days = -1
    message = str(exc_info.value)
    assert "must be >= 0" in message
    assert DataClass.SENSITIVE.value in message
