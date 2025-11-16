"""Tests for core.memory_config module."""

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


@pytest.fixture(autouse=True)
def _reset_global_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure global singleton is reset between tests."""
    monkeypatch.setattr(memory_config, "_memori_instance", None)


def test_get_memori_instance_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_get_global_memori_caches_and_handles_failures(monkeypatch: pytest.MonkeyPatch) -> None:
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
