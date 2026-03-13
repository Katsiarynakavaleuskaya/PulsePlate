"""
Тесты для покрытия исключений при импорте в llm.py
Цель: достичь 100% покрытия кода включая fallback провайдеры
"""

import importlib
import os
import sys
from importlib import reload
from unittest.mock import Mock, patch

import pytest

import llm


@pytest.fixture(autouse=True)
def _llm_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate llm env defaults per test."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")


class TestImportFallbacks:
    """Тесты fallback поведения при недоступности внешних провайдеров"""

    def test_grok_import_exception_coverage(self, monkeypatch):
        """Тест покрытия GrokLiteProvider при ошибке импорта providers.grok"""
        # IMPORTANT: do not mutate sys.modules directly; use monkeypatch so pytest
        # automatically restores state after the test (repo rule after #406).
        provider_modules = [
            name for name in list(sys.modules.keys()) if name.startswith("providers")
        ]
        for name in provider_modules:
            monkeypatch.delitem(sys.modules, name, raising=False)

        original_import_module = importlib.import_module

        def side_effect(name, *args, **kwargs):
            if name == "providers.grok":
                raise ImportError("No module named providers.grok")
            return original_import_module(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=side_effect):
            # Перезагружаем модуль llm чтобы активировать except блок
            reload(llm)

            # Ошибка импорта должна оставить реальный провайдер недоступным.
            # EN: Import failure must leave the real provider unavailable.
            assert llm.GrokProvider is None
            # Теперь GrokLiteProvider должен быть доступен
            assert hasattr(llm, "GrokLiteProvider")

            # Тестируем создание и использование GrokLiteProvider
            provider = llm.GrokLiteProvider()
            assert provider.name == "grok"

        # Восстанавливаем "стабильную" версию llm после теста.
        # sys.modules будет восстановлен pytest monkeypatch автоматически.
        reload(llm)

    @pytest.mark.asyncio
    async def test_grok_lite_provider_generate_coverage(self):
        """Тест метода generate класса GrokLiteProvider"""
        # Убеждаемся, что в модуле доступен реальный GrokLiteProvider
        assert hasattr(llm, "GrokLiteProvider"), "GrokLiteProvider должен существовать в llm"

        provider = llm.GrokLiteProvider()
        assert getattr(provider, "name", None) == "grok"

        result = await provider.generate("test input")

        # Поведение задокументировано в llm.GrokLiteProvider.generate
        # Ожидаем маркер grok-lite и возврат исходного текста
        assert result.startswith("[grok-lite] ")
        assert result.endswith("test input")
        assert "grok-lite" in result

    def test_ollama_import_exception_coverage(self):
        """Тест покрытия исключения при импорте OllamaProvider"""
        # Мокаем ошибку импорта OllamaProvider
        original_import_module = importlib.import_module
        with patch("importlib.import_module") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "providers.ollama":
                    raise ImportError("No module named 'providers.ollama'")
                return original_import_module(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            # Перезагружаем модуль для активации except блока
            reload(llm)

            # OllamaProvider должен быть None
            assert llm.OllamaProvider is None

        # Восстанавливаем нормальное состояние
        reload(llm)

    def test_pico_import_exception_coverage(self):
        """Тест покрытия исключения при импорте PicoProvider"""
        # Мокаем ошибку импорта PicoProvider
        original_import_module = importlib.import_module
        with patch("importlib.import_module") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "providers.pico":
                    raise ImportError("No module named 'providers.pico'")
                return original_import_module(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            # Перезагружаем модуль для активации except блока
            reload(llm)

            # PicoProvider должен быть None
            assert llm.PicoProvider is None

        # Восстанавливаем нормальное состояние
        reload(llm)


class TestGetProviderEdgeCases:
    """Тесты граничных случаев функции get_provider()"""

    def test_get_provider_with_pico(self):
        """Тест несуществующего провайдера pico"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "pico"}, clear=False):
            provider = llm.get_provider()
            # Должен вернуться None так как pico не обрабатывается в get_provider
            assert provider is None

    def test_get_provider_ollama_with_exception_coverage(self):
        """Тест покрытия всех путей исключений в Ollama"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            with patch.object(llm, "OllamaProvider") as mock_ollama:
                # Тест TypeError в первом try/except блоке
                mock_ollama.side_effect = [TypeError("keyword error"), Exception("creation failed")]

                provider = llm.get_provider()
                # При ошибках должен вернуться OllamaLiteProvider (консистентно с GrokProvider)
                assert provider is not None
                assert provider.name == "ollama"
                assert mock_ollama.call_count == 2

    @patch("llm.GrokProvider")
    def test_grok_provider_positional_args_fallback(self, mock_grok_class):
        """Тест fallback на позиционные аргументы для GrokProvider"""
        # Первый вызов с keyword args падает, второй с positional успешен
        mock_instance = Mock()
        mock_grok_class.side_effect = [TypeError("unexpected keyword"), mock_instance]

        with patch.dict(os.environ, {"LLM_PROVIDER": "grok", "GROK_API_KEY": "dummy"}, clear=False):
            provider = llm.get_provider()

            # Должно быть два вызова: kwargs и positional
            assert mock_grok_class.call_count == 2
            assert provider == mock_instance

    def test_get_provider_grok_without_real_provider(self):
        """Тест get_provider с grok когда GrokProvider недоступен"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "grok"}, clear=False):
            with patch.object(llm, "GrokProvider", None):
                provider = llm.get_provider()
                # Если у нас нет GrokLiteProvider, должен вернуться None
                # В реальном модуле возвращается GrokLiteProvider только если GrokProvider=None
                # When GrokProvider is None, should fallback to GrokLiteProvider
                if hasattr(llm, "GrokLiteProvider"):
                    assert provider is not None
                    assert provider.name == "grok"
                else:
                    assert provider is None


class TestEnvironmentVariableEdgeCases:
    """Тесты граничных случаев обработки переменных окружения"""

    def test_empty_string_values(self):
        """Тест различных форм пустых строк"""
        empty_values = ["", " ", "\t", "\n", "\r\n", "  \t\n  "]

        for empty_val in empty_values:
            with patch.dict(os.environ, {"LLM_PROVIDER": empty_val}, clear=False):
                provider = llm.get_provider()
                assert provider is None, f"Failed for empty value: '{repr(empty_val)}'"

    def test_case_variations(self):
        """Тест различных вариантов регистра"""
        # Тест для stub
        stub_variations = ["stub", "STUB", "Stub", "StUb", "sTuB"]
        for variation in stub_variations:
            with patch.dict(os.environ, {"LLM_PROVIDER": variation}, clear=False):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "stub"

        # Тест для grok
        grok_variations = ["grok", "GROK", "Grok", "GrOk", "gRoK"]
        for variation in grok_variations:
            with patch.dict(os.environ, {"LLM_PROVIDER": variation}, clear=False):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "grok"

    def test_special_none_values(self):
        """Тест специальных значений, означающих None"""
        none_values = ["none", "NONE", "None", "no", "NO", "No"]

        for none_val in none_values:
            with patch.dict(os.environ, {"LLM_PROVIDER": none_val}, clear=False):
                provider = llm.get_provider()
                assert provider is None, f"Should be None for: '{none_val}'"
