# -*- coding: utf-8 -*-
"""
Дополнительные тесты для покрытия llm.py и связанных веток.
"""

import builtins
import os
import sys
import types


def test__with_name_handles_attribute_error():
    import llm
    # У некоторых веток llm.py нет вспомогательной функции _with_name
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
    orig_stub = sys.modules.get("providers.stub")
    orig_llm = sys.modules.get("llm")
    sys.modules["providers.stub"] = fake

    try:
        # Перезагружаем llm, чтобы прошёл путь с import Provider as StubProvider
        if "llm" in sys.modules:
            del sys.modules["llm"]
        import llm as llm_reloaded  # noqa: F401

        # sanity: получаем провайдера stub и убеждаемся, что generate работает
        os.environ["LLM_PROVIDER"] = "stub"
        from llm import get_provider  # type: ignore

        p = get_provider()
        assert p is not None
        assert hasattr(p, "generate")
        assert p.name == "stub"
    finally:
        if orig_stub is not None:
            sys.modules["providers.stub"] = orig_stub
        else:
            sys.modules.pop("providers.stub", None)
        if orig_llm is not None:
            sys.modules["llm"] = orig_llm
        else:
            sys.modules.pop("llm", None)


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
    orig = sys.modules.get("providers.grok")
    sys.modules["providers.grok"] = mod

    try:
        # Даём непустой ключ, чтобы пройти до конструктора
        os.environ["GROK_API_KEY"] = "dummy"
        os.environ.pop("XAI_API_KEY", None)
        os.environ["LLM_PROVIDER"] = "grok"
        from llm import get_provider  # type: ignore

        p = get_provider()
        # Первая попытка с именованными параметрами падает, вторая (позиционная) — успешна
        assert p is not None and getattr(p, "name", "") == "grok"
    finally:
        if orig is not None:
            sys.modules["providers.grok"] = orig
        else:
            sys.modules.pop("providers.grok", None)


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
    orig = sys.modules.get("providers.ollama")
    sys.modules["providers.ollama"] = mod

    try:
        os.environ["LLM_PROVIDER"] = "ollama"
        from llm import get_provider  # type: ignore

        p = get_provider()
        assert p is not None and getattr(p, "name", "") == "ollama"
    finally:
        if orig is not None:
            sys.modules["providers.ollama"] = orig
        else:
            sys.modules.pop("providers.ollama", None)


def test_get_provider_ollama_import_error_fallback(monkeypatch):
    """Импорт providers.ollama падает — получаем заглушку под именем ollama."""
    sys.modules.pop("providers.ollama", None)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "providers.ollama":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    os.environ["LLM_PROVIDER"] = "ollama"
    from llm import get_provider  # type: ignore

    p = get_provider()
    assert p is not None and getattr(p, "name", "") == "ollama"


def test_get_provider_grok_missing_api_key_triggers_branch():
    """Импорт grok успешен, ключа нет — покрываем ветку raise RuntimeError('no api key')."""
    mod = types.ModuleType("providers.grok")

    class GrokProvider:
        def __init__(self, *args, **kwargs):
            pass

    mod.GrokProvider = GrokProvider
    orig = sys.modules.get("providers.grok")
    sys.modules["providers.grok"] = mod
    try:
        os.environ.pop("GROK_API_KEY", None)
        os.environ.pop("XAI_API_KEY", None)
        os.environ["LLM_PROVIDER"] = "grok"
        from llm import get_provider  # type: ignore

        p = get_provider()
        # Возвращается заглушка под именем grok
        assert p is not None and getattr(p, "name", "") == "grok"
    finally:
        if orig is not None:
            sys.modules["providers.grok"] = orig
        else:
            sys.modules.pop("providers.grok", None)
