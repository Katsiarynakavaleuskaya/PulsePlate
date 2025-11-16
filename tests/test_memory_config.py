"""Tests for core.memory_config module.

RU: Тесты для модуля конфигурации Memori.
EN: Tests for Memori configuration module.

This test suite ensures 97%+ coverage by testing:
- Configuration from environment variables
- Default values
- Explicit arguments overriding env vars
- Error paths and exception handling
- Global lazy initialization and reset
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.memory_config as memory_config


class FakeMemori:
    """Lightweight stand-in for memori.Memori to capture init arguments."""

    def __init__(
        self,
        *,
        database_connect: str,
        conscious_ingest: bool,
        auto_ingest: bool,
        user_id: str | None,
        openai_api_key: str | None,
        verbose: bool,
    ) -> None:
        self.database_connect = database_connect
        self.conscious_ingest = conscious_ingest
        self.auto_ingest = auto_ingest
        self.user_id = user_id
        self.openai_api_key = openai_api_key
        self.verbose = verbose
        self.enabled = False

    def enable(self) -> None:  # noqa: D401
        self.enabled = True


class FailingMemori:
    """Memori that raises exceptions during initialization."""

    def __init__(self, *, exception_type: type[Exception], **kwargs: object) -> None:
        raise exception_type("Simulated Memori initialization failure")


@pytest.fixture(autouse=True)
def _reset_global_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure global singleton is reset between tests.

    RU: Сбрасывает глобальный экземпляр между тестами для изоляции.
    EN: Resets global instance between tests for isolation.
    """
    monkeypatch.setattr(memory_config, "_memori_instance", None)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean environment variables for Memori configuration.

    RU: Очищает переменные окружения Memori перед тестом.
    EN: Cleans Memori environment variables before test.
    """
    env_vars = [
        "MEMORI_DATABASE_URL",
        "OPENAI_API_KEY",
        "MEMORI_USER_ID",
        "MEMORI_CONSCIOUS_INGEST",
        "MEMORI_AUTO_INGEST",
        "MEMORI_VERBOSE",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


# ============================================================================
# Tests for get_memori_instance with environment variables
# ============================================================================


def test_get_memori_instance_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_memori_instance reads all environment variables correctly."""
    monkeypatch.setenv("MEMORI_DATABASE_URL", "sqlite:///custom.db")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MEMORI_USER_ID", "user-42")
    monkeypatch.setenv("MEMORI_CONSCIOUS_INGEST", "true")
    monkeypatch.setenv("MEMORI_AUTO_INGEST", "true")
    monkeypatch.setenv("MEMORI_VERBOSE", "true")

    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    instance = memory_config.get_memori_instance()

    assert isinstance(instance, FakeMemori)
    assert instance.database_connect == "sqlite:///custom.db"
    assert instance.conscious_ingest is True
    assert instance.auto_ingest is True
    assert instance.user_id == "user-42"
    assert instance.openai_api_key == "test-key"
    assert instance.verbose is True
    assert instance.enabled is True  # enable() must be called


def test_get_memori_instance_uses_default_db_when_no_env(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test that default database URL is used when MEMORI_DATABASE_URL is not set."""
    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    instance = memory_config.get_memori_instance()

    assert instance.database_connect == "sqlite:///memori.db"  # Default value
    assert instance.conscious_ingest is False
    assert instance.auto_ingest is False
    assert instance.user_id is None
    assert instance.openai_api_key is None
    assert instance.verbose is False


def test_get_memori_instance_boolean_parsing_case_insensitive(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test that boolean env vars are parsed case-insensitively."""
    monkeypatch.setenv("MEMORI_CONSCIOUS_INGEST", "TRUE")
    monkeypatch.setenv("MEMORI_AUTO_INGEST", "True")
    monkeypatch.setenv("MEMORI_VERBOSE", "FALSE")

    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    instance = memory_config.get_memori_instance()

    assert instance.conscious_ingest is True
    assert instance.auto_ingest is True
    assert instance.verbose is False


def test_get_memori_instance_boolean_parsing_false_values(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test that non-true values are parsed as False."""
    monkeypatch.setenv("MEMORI_CONSCIOUS_INGEST", "false")
    monkeypatch.setenv("MEMORI_AUTO_INGEST", "0")
    monkeypatch.setenv("MEMORI_VERBOSE", "")

    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    instance = memory_config.get_memori_instance()

    assert instance.conscious_ingest is False
    assert instance.auto_ingest is False
    assert instance.verbose is False


# ============================================================================
# Tests for explicit arguments overriding environment variables
# ============================================================================


def test_get_memori_instance_explicit_args_override_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that explicit arguments override environment variables."""
    monkeypatch.setenv("MEMORI_DATABASE_URL", "sqlite:///env.db")
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("MEMORI_USER_ID", "env-user")
    monkeypatch.setenv("MEMORI_CONSCIOUS_INGEST", "true")
    monkeypatch.setenv("MEMORI_AUTO_INGEST", "true")
    monkeypatch.setenv("MEMORI_VERBOSE", "true")

    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    instance = memory_config.get_memori_instance(
        user_id="explicit-user",
        database_url="sqlite:///explicit.db",
        conscious_ingest=False,
        auto_ingest=False,
    )

    # Explicit args should override env vars
    assert instance.database_connect == "sqlite:///explicit.db"
    assert instance.user_id == "explicit-user"
    assert instance.conscious_ingest is False
    assert instance.auto_ingest is False
    # These should still come from env (no explicit override)
    assert instance.openai_api_key == "env-key"
    assert instance.verbose is True


def test_get_memori_instance_explicit_args_with_default_db(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test explicit args when no env vars are set, using default database."""
    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    instance = memory_config.get_memori_instance(
        user_id="test-user",
        conscious_ingest=True,
        auto_ingest=True,
    )

    assert instance.database_connect == "sqlite:///memori.db"  # Default
    assert instance.user_id == "test-user"
    assert instance.conscious_ingest is True
    assert instance.auto_ingest is True
    assert instance.openai_api_key is None
    assert instance.verbose is False


# ============================================================================
# Tests for error paths and exception handling
# ============================================================================


def test_get_memori_instance_propagates_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_memori_instance propagates ImportError from Memori constructor."""
    monkeypatch.setattr(
        memory_config,
        "Memori",
        lambda **kwargs: FailingMemori(exception_type=ImportError, **kwargs),
    )

    with pytest.raises(ImportError, match="Simulated Memori initialization failure"):
        memory_config.get_memori_instance()


def test_get_memori_instance_propagates_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_memori_instance propagates RuntimeError from Memori constructor."""
    monkeypatch.setattr(
        memory_config,
        "Memori",
        lambda **kwargs: FailingMemori(exception_type=RuntimeError, **kwargs),
    )

    with pytest.raises(RuntimeError, match="Simulated Memori initialization failure"):
        memory_config.get_memori_instance()


def test_get_memori_instance_propagates_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_memori_instance propagates ValueError from Memori constructor."""
    monkeypatch.setattr(
        memory_config,
        "Memori",
        lambda **kwargs: FailingMemori(exception_type=ValueError, **kwargs),
    )

    with pytest.raises(ValueError, match="Simulated Memori initialization failure"):
        memory_config.get_memori_instance()


def test_get_global_memori_returns_none_on_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_global_memori returns None when get_memori_instance raises ImportError."""
    memory_config._memori_instance = None

    def failing_factory() -> None:
        raise ImportError("Memori not available")

    monkeypatch.setattr(memory_config, "get_memori_instance", failing_factory)

    result = memory_config.get_global_memori()
    assert result is None
    assert memory_config._memori_instance is None


def test_get_global_memori_returns_none_on_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_global_memori returns None when get_memori_instance raises RuntimeError."""
    memory_config._memori_instance = None

    def failing_factory() -> None:
        raise RuntimeError("Memori initialization failed")

    monkeypatch.setattr(memory_config, "get_memori_instance", failing_factory)

    result = memory_config.get_global_memori()
    assert result is None
    assert memory_config._memori_instance is None


def test_get_global_memori_returns_none_on_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_global_memori returns None when get_memori_instance raises ValueError."""
    memory_config._memori_instance = None

    def failing_factory() -> None:
        raise ValueError("Invalid configuration")

    monkeypatch.setattr(memory_config, "get_memori_instance", failing_factory)

    result = memory_config.get_global_memori()
    assert result is None
    assert memory_config._memori_instance is None


def test_get_global_memori_propagates_other_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_global_memori propagates exceptions other than ImportError/RuntimeError/ValueError."""
    memory_config._memori_instance = None

    def failing_factory() -> None:
        raise KeyError("Unexpected error")

    monkeypatch.setattr(memory_config, "get_memori_instance", failing_factory)

    with pytest.raises(KeyError, match="Unexpected error"):
        memory_config.get_global_memori()


# ============================================================================
# Tests for global lazy initialization and reset
# ============================================================================


def test_get_global_memori_lazy_initialization(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test that get_global_memori creates instance on first call (lazy init)."""
    # Ensure _memori_instance is None
    memory_config._memori_instance = None

    call_count = {"value": 0}
    sentinel = SimpleNamespace()

    def factory() -> object:
        call_count["value"] += 1
        return sentinel

    monkeypatch.setattr(memory_config, "get_memori_instance", factory)

    # First call should create instance
    first_result = memory_config.get_global_memori()
    assert first_result is sentinel
    assert call_count["value"] == 1
    assert memory_config._memori_instance is sentinel

    # Second call should return cached instance
    second_result = memory_config.get_global_memori()
    assert second_result is sentinel
    assert call_count["value"] == 1  # Not called again


def test_get_global_memori_reset_between_tests(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test that _memori_instance can be reset to None for test isolation."""
    # Set up initial state
    memory_config._memori_instance = None

    sentinel1 = SimpleNamespace()
    sentinel2 = SimpleNamespace()
    call_count = {"value": 0}

    def factory() -> object:
        call_count["value"] += 1
        return sentinel1 if call_count["value"] == 1 else sentinel2

    monkeypatch.setattr(memory_config, "get_memori_instance", factory)

    # First call creates instance
    result1 = memory_config.get_global_memori()
    assert result1 is sentinel1
    assert memory_config._memori_instance is sentinel1

    # Reset to None (simulating test isolation)
    memory_config._memori_instance = None

    # Next call should create new instance
    result2 = memory_config.get_global_memori()
    assert result2 is sentinel2
    assert memory_config._memori_instance is sentinel2
    assert call_count["value"] == 2


def test_get_global_memori_caches_and_handles_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_global_memori caches instance and handles failures correctly."""
    sentinel = SimpleNamespace()
    call_count = {"value": 0}

    def fake_factory() -> object:
        call_count["value"] += 1
        if call_count["value"] == 1:
            return sentinel
        raise AssertionError("Factory called more than once")

    monkeypatch.setattr(memory_config, "get_memori_instance", fake_factory)

    first = memory_config.get_global_memori()
    second = memory_config.get_global_memori()
    assert first is sentinel
    assert second is sentinel
    assert call_count["value"] == 1

    # Now simulate failure on fresh singleton
    memory_config._memori_instance = None

    def failing_factory() -> None:
        raise RuntimeError("memori unavailable")

    monkeypatch.setattr(memory_config, "get_memori_instance", failing_factory)
    assert memory_config.get_global_memori() is None
    assert memory_config._memori_instance is None


# ============================================================================
# Integration tests for complete configuration scenarios
# ============================================================================


def test_complete_configuration_flow(monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    """Test complete configuration flow with all env vars and explicit overrides."""
    # Set all env vars
    monkeypatch.setenv("MEMORI_DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("MEMORI_USER_ID", "global-user")
    monkeypatch.setenv("MEMORI_CONSCIOUS_INGEST", "true")
    monkeypatch.setenv("MEMORI_AUTO_INGEST", "false")
    monkeypatch.setenv("MEMORI_VERBOSE", "true")

    monkeypatch.setattr(memory_config, "Memori", FakeMemori)

    # Test with env vars only
    instance1 = memory_config.get_memori_instance()
    assert instance1.database_connect == "postgresql://user:pass@host/db"
    assert instance1.openai_api_key == "sk-test-key"
    assert instance1.user_id == "global-user"
    assert instance1.conscious_ingest is True
    assert instance1.auto_ingest is False
    assert instance1.verbose is True

    # Test with explicit overrides
    instance2 = memory_config.get_memori_instance(
        user_id="override-user",
        database_url="sqlite:///override.db",
        conscious_ingest=False,
        auto_ingest=True,
    )
    assert instance2.database_connect == "sqlite:///override.db"
    assert instance2.user_id == "override-user"
    assert instance2.conscious_ingest is False
    assert instance2.auto_ingest is True
    # These should still come from env
    assert instance2.openai_api_key == "sk-test-key"
    assert instance2.verbose is True
