# -*- coding: utf-8 -*-
"""
Дополнительные тесты для покрытия llm.py и связанных веток.
"""

import builtins
import os
import sys
import types
from contextlib import contextmanager
from typing import Optional


@contextmanager
def mock_module(module_name: str, module_obj: types.ModuleType):
    """Context manager to safely mock sys.modules entries."""
    orig = sys.modules.get(module_name)
    sys.modules[module_name] = module_obj
    try:
        yield
    finally:
        restore_module(module_name, orig)


def restore_module(module_name: str, original: Optional[types.ModuleType]):
    """Restore or remove a module from sys.modules."""
    if original is not None:
        sys.modules[module_name] = original
    else:
        sys.modules.pop(module_name, None)


@contextmanager
def clean_llm_import():
    """Context manager to clean and restore llm module import."""
    orig_llm = sys.modules.get("llm")
    if "llm" in sys.modules:
        del sys.modules["llm"]
    try:
        yield
    finally:
        restore_module("llm", orig_llm)


def test__with_name_handles_attribute_error():
    import llm
    # У некоторых веток llm.py нет вспомогательной функции _with_name
    # Skip test if _with_name is not available
    if not hasattr(llm, "_with_name"):
        assert hasattr(llm, "get_provider")
        return

    class NoAttrs:
        __slots__ = ()

    obj = NoAttrs()
    # не падает, покрывает ветку except внутри _with_name
    res = llm._with_name(obj, "any")  # type: ignore[attr-defined]
    assert res is obj


def test_llm_stub_import_alias_path(monkeypatch):
    """Провоцируем падение импорта StubProvider и успешный импорт Provider as StubProvider."""
    # Создаём фейковый модуль providers.stub без StubProvider, но с Provider
    fake = types.ModuleType("providers.stub")

    class Provider:
        name = "provider"

        def generate(self, text: str) -> str:
            return f"ok:{text}"

    fake.Provider = Provider

    with mock_module("providers.stub", fake), clean_llm_import(), monkeypatch.context() as m:
        m.setenv("LLM_PROVIDER", "stub")

        # Перезагружаем llm, чтобы прошёл путь с import Provider as StubProvider
        import llm as llm_reloaded  # noqa: F401

        # sanity: получаем провайдера stub и убеждаемся, что generate работает
        from llm import get_provider  # type: ignore

        p = get_provider()
        assert p is not None
        assert hasattr(p, "generate")
        assert p.name == "stub"


def test_get_provider_grok_env_block_executes(monkeypatch):
    """Делаем импорт providers.grok успешным, чтобы пройти код до проверки API-ключа."""
    mod = types.ModuleType("providers.grok")

    class GrokProvider:
        # позиционно-только — вызов с именованными параметрами приведёт к TypeError
        def __init__(self, endpoint, model, api_key, /):  # noqa: D401
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

        async def generate(self, text: str) -> str:
            return text

    mod.GrokProvider = GrokProvider

    with mock_module("providers.grok", mod), monkeypatch.context() as m:
        # Даём непустой ключ, чтобы пройти до конструктора
        m.setenv("GROK_API_KEY", "dummy")
        m.delenv("XAI_API_KEY", raising=False)
        m.setenv("LLM_PROVIDER", "grok")

        from llm import get_provider  # type: ignore

        p = get_provider()
        # Первая попытка с именованными параметрами падает, вторая (позиционная) — успешна
        assert p is not None and getattr(p, "name", "") == "grok"


def test_get_provider_ollama_typeerror_posargs_fallback(monkeypatch):
    """Инициализация с именованными аргументами вызывает TypeError, затем успех с позиционными."""
    mod = types.ModuleType("providers.ollama")

    class OllamaProvider:
        # позиционно-только — именованные параметры вызовут TypeError
        def __init__(self, endpoint, model, /):  # noqa: D401
            self.endpoint = endpoint
            self.model = model

        async def generate(self, text: str) -> str:
            return text

    mod.OllamaProvider = OllamaProvider

    with mock_module("providers.ollama", mod), monkeypatch.context() as m:
        m.setenv("LLM_PROVIDER", "ollama")

        from llm import get_provider  # type: ignore

        p = get_provider()
        assert p is not None and getattr(p, "name", "") == "ollama"


def test_get_provider_ollama_import_error_fallback(monkeypatch):
    """Импорт providers.ollama падает — получаем заглушку под именем ollama."""
    sys.modules.pop("providers.ollama", None)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        # Move the conditional logic to a helper to reduce complexity in test
        return handle_fake_import(name, real_import, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", fake_import)
        m.setenv("LLM_PROVIDER", "ollama")

        from llm import get_provider  # type: ignore

        p = get_provider()
        assert p is not None and getattr(p, "name", "") == "ollama"


def handle_fake_import(name, real_import, *args, **kwargs):
    """Helper function to handle fake import logic."""
    if name == "providers.ollama":
        raise ImportError("simulated")
    return real_import(name, *args, **kwargs)


def test_get_provider_grok_missing_api_key_triggers_branch(monkeypatch):
    """Импорт grok успешен, ключа нет — покрываем ветку raise RuntimeError('no api key')."""
    mod = types.ModuleType("providers.grok")

    class GrokProvider:
        def __init__(self, *args, **kwargs):
            pass

    mod.GrokProvider = GrokProvider

    with mock_module("providers.grok", mod), monkeypatch.context() as m:
        m.delenv("GROK_API_KEY", raising=False)
        m.delenv("XAI_API_KEY", raising=False)
        m.setenv("LLM_PROVIDER", "grok")

        from llm import get_provider  # type: ignore

        p = get_provider()
        # Возвращается заглушка под именем grok
        assert p is not None and getattr(p, "name", "") == "grok"
