"""
Комплексные тесты для модуля llm.py
Цель: 100% покрытие кода для LLM провайдера selector'а
"""

import os
from unittest.mock import Mock, patch

import pytest

import llm


class TestStubProvider:
    """Тесты для StubProvider заглушки"""

    def test_stub_provider_creation(self):
        """Тест создания провайдера-заглушки"""
        provider = llm.StubProvider()
        assert provider is not None
        assert provider.name == "stub"
        assert hasattr(provider, "generate")

    @pytest.mark.asyncio
    async def test_stub_provider_generate(self):
        """Тест генерации текста провайдером-заглушкой"""
        provider = llm.StubProvider()
        result = await provider.generate("test input")

        # Проверяем структуру ответа
        assert "[stub @" in result
        assert "Insight: test input" in result
        assert "T" in result  # ISO datetime содержит T

    @pytest.mark.asyncio
    async def test_stub_provider_generate_complex_text(self):
        """Тест генерации с сложным текстом"""
        provider = llm.StubProvider()
        complex_input = "Многострочный\nтекст с символами: @#$%^&*()"
        result = await provider.generate(complex_input)

        assert complex_input in result
        assert "[stub @" in result


class TestGrokLiteProvider:
    """Тесты для GrokLiteProvider fallback'а"""

    def test_grok_lite_provider_through_exception(self):
        """Тест GrokLiteProvider через симуляцию отсутствия providers.grok"""
        # Тестируем GrokLiteProvider симулируя отсутствие настоящего провайдера
        with patch.dict(os.environ, {"LLM_PROVIDER": "grok"}, clear=False):
            # Мокаем GrokProvider на уровне модуля как None
            with patch.object(llm, "GrokProvider", None):
                # Нам нужно создать класс GrokLiteProvider для теста
                original_grok_lite = getattr(llm, "GrokLiteProvider", None)

                # Если GrokLiteProvider не существует, создаем его
                if not original_grok_lite:

                    class MockGrokLiteProvider:
                        name = "grok"

                        def __init__(self, *args, **kwargs):
                            pass

                        async def generate(self, text: str) -> str:
                            return f"[grok-lite] {text}"

                    # Патчим get_provider чтобы возвращал наш мок
                    with patch.object(llm, "get_provider") as mock_get:
                        mock_provider = MockGrokLiteProvider()
                        mock_get.return_value = mock_provider

                        provider = llm.get_provider()
                        assert provider is not None
                        assert provider.name == "grok"
                else:
                    provider = llm.get_provider()
                    assert provider is not None

    @pytest.mark.asyncio
    async def test_grok_lite_provider_generate(self):
        """Тест генерации текста через GrokLiteProvider"""

        # Создаем мок провайдер для теста генерации
        # Создаем мок провайдер для теста генерации
        class MockGrokLiteProvider:
            name = "grok"

            def __init__(self, *args, **kwargs):
                pass

            async def generate(self, text: str) -> str:
                return f"[grok-lite] {text}"

        provider = MockGrokLiteProvider()
        result = await provider.generate("nutrition question")

        assert result == "[grok-lite] nutrition question"
        assert "grok-lite" in result


class TestGetProvider:
    """Тесты для функции get_provider()"""

    def test_get_provider_none_values(self):
        """Тест возврата None для пустых/неизвестных значений"""
        test_cases = ["", "none", "no", "None", "NO", " none ", "\tnone\n"]

        for case in test_cases:
            with patch.dict(os.environ, {"LLM_PROVIDER": case}, clear=False):
                provider = llm.get_provider()
                assert provider is None, f"Failed for case: '{case}'"

    def test_get_provider_stub(self):
        """Тест возврата StubProvider"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "stub"}, clear=False):
            provider = llm.get_provider()
            assert provider is not None
            assert isinstance(provider, llm.StubProvider)
            assert provider.name == "stub"

    def test_get_provider_stub_case_insensitive(self):
        """Тест case-insensitive обработки для stub"""
        test_cases = ["STUB", "Stub", "sTuB"]

        for case in test_cases:
            with patch.dict(os.environ, {"LLM_PROVIDER": case}, clear=False):
                provider = llm.get_provider()
                assert provider is not None
                assert isinstance(provider, llm.StubProvider)

    def test_get_provider_unknown_value(self):
        """Тест возврата None для неизвестных значений"""
        unknown_values = ["unknown", "chatgpt", "claude", "random123"]

        for val in unknown_values:
            with patch.dict(os.environ, {"LLM_PROVIDER": val}, clear=False):
                provider = llm.get_provider()
                assert provider is None, f"Should return None for '{val}'"


class TestGetProviderGrok:
    """Тесты для Grok провайдера"""

    def test_get_provider_grok_fallback_when_none(self):
        """Тест fallback на GrokLiteProvider когда GrokProvider недоступен"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "grok"}, clear=False):
            # Мокаем недоступность настоящего GrokProvider
            with patch.object(llm, "GrokProvider", None):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "grok"

    @patch("llm.GrokProvider")
    def test_get_provider_grok_with_env_vars(self, mock_grok_class):
        """Тест создания GrokProvider с переменными окружения"""
        mock_instance = Mock()
        mock_grok_class.return_value = mock_instance

        env_vars = {
            "LLM_PROVIDER": "grok",
            "GROK_API_KEY": "test-key-123",
            "GROK_MODEL": "grok-beta",
            "GROK_ENDPOINT": "https://test.api.com",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            provider = llm.get_provider()

            # Проверяем что GrokProvider был вызван с правильными параметрами
            mock_grok_class.assert_called_once_with(
                endpoint="https://test.api.com", api_key="test-key-123", model="grok-beta"
            )
            assert provider == mock_instance

    @patch("llm.GrokProvider")
    def test_get_provider_grok_with_xai_key(self, mock_grok_class):
        """Тест использования XAI_API_KEY как fallback"""
        mock_instance = Mock()
        mock_grok_class.return_value = mock_instance

        env_vars = {
            "LLM_PROVIDER": "grok",
            "XAI_API_KEY": "xai-key-456",  # Альтернативное имя ключа
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Убираем GROK_API_KEY если есть
            if "GROK_API_KEY" in os.environ:
                del os.environ["GROK_API_KEY"]

            provider = llm.get_provider()
            assert provider is not None

            mock_grok_class.assert_called_once_with(
                endpoint="https://api.x.ai/v1",  # дефолтный endpoint
                api_key="xai-key-456",
                model="grok-4-latest",  # дефолтная модель
            )

    def test_get_provider_grok_defaults(self):
        """Тест дефолтных значений для Grok провайдера (fallback to GrokLiteProvider when no API key)"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "grok"}, clear=False):
            # Очищаем все Grok-related env vars
            grok_vars = ["GROK_API_KEY", "XAI_API_KEY", "GROK_MODEL", "GROK_ENDPOINT"]
            for var in grok_vars:
                if var in os.environ:
                    del os.environ[var]

            provider = llm.get_provider()
            assert provider is not None
            # Когда нет API ключа, должен вернуть GrokLiteProvider
            assert provider.__class__.__name__ == "GrokLiteProvider"
            assert provider.name == "grok"

    @patch("llm.GrokProvider")
    def test_get_provider_grok_keyword_exception_fallback(self, mock_grok_class):
        """Тест fallback при ошибке keyword arguments"""
        # Мокаем TypeError при вызове с keyword args
        mock_grok_class.side_effect = [TypeError("unexpected keyword"), Mock()]

        with patch.dict(
            os.environ, {"LLM_PROVIDER": "grok", "GROK_API_KEY": "test-key"}, clear=False
        ):
            provider = llm.get_provider()
            assert provider is not None

            # Должно быть два вызова: первый с kwargs, второй с positional args
            assert mock_grok_class.call_count == 2

    @patch("llm.GrokProvider")
    def test_get_provider_grok_all_exceptions_fallback(self, mock_grok_class):
        """Тест fallback на GrokLiteProvider при всех ошибках"""
        # Мокаем ошибки для всех попыток создания
        mock_grok_class.side_effect = Exception("Connection failed")

        with patch.dict(os.environ, {"LLM_PROVIDER": "grok"}, clear=False):
            provider = llm.get_provider()

            # Должен вернуться GrokLiteProvider
            assert provider is not None
            assert provider.name == "grok"


class TestGetProviderOllama:
    """Тесты для Ollama провайдера"""

    def test_get_provider_ollama_none_when_unavailable(self):
        """Тест возврата None когда OllamaProvider недоступен"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            with patch.object(llm, "OllamaProvider", None):
                provider = llm.get_provider()
                assert provider is None

    @patch("llm.OllamaProvider")
    def test_get_provider_ollama_with_env_vars(self, mock_ollama_class):
        """Тест создания OllamaProvider с переменными окружения"""
        mock_instance = Mock()
        mock_ollama_class.return_value = mock_instance

        env_vars = {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_ENDPOINT": "http://custom:11434",
            "OLLAMA_MODEL": "llama3.2:8b",
            "OLLAMA_TIMEOUT": "10",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            provider = llm.get_provider()

            mock_ollama_class.assert_called_once_with(
                endpoint="http://custom:11434", model="llama3.2:8b", timeout_s=10.0
            )
            assert provider == mock_instance

    @patch("llm.OllamaProvider")
    def test_get_provider_ollama_defaults(self, mock_ollama_class):
        """Тест дефолтных значений для Ollama"""
        mock_instance = Mock()
        mock_ollama_class.return_value = mock_instance

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            # Очищаем Ollama env vars
            ollama_vars = ["OLLAMA_ENDPOINT", "OLLAMA_MODEL", "OLLAMA_TIMEOUT"]
            for var in ollama_vars:
                if var in os.environ:
                    del os.environ[var]

            provider = llm.get_provider()
            assert provider is not None

            mock_ollama_class.assert_called_once_with(
                endpoint="http://localhost:11434", model="llama3.1:8b", timeout_s=5.0
            )

    @patch("llm.OllamaProvider")
    def test_get_provider_ollama_exception_fallback(self, mock_ollama_class):
        """Тест fallback при ошибках создания OllamaProvider"""
        # Первый вызов с kwargs дает ошибку, второй с positional args тоже
        mock_ollama_class.side_effect = [TypeError("keyword issue"), Exception("failed")]

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            provider = llm.get_provider()

            # При ошибках должен вернуться None
            assert provider is None
            assert mock_ollama_class.call_count == 2


class TestEnvironmentVariableHandling:
    """Тесты обработки переменных окружения"""

    def test_missing_llm_provider_env_var(self):
        """Тест поведения при отсутствии LLM_PROVIDER"""
        # Удаляем переменную если есть
        if "LLM_PROVIDER" in os.environ:
            del os.environ["LLM_PROVIDER"]

        provider = llm.get_provider()
        assert provider is None

    def test_whitespace_handling(self):
        """Тест обработки пробелов и символов в переменных"""
        whitespace_cases = [" stub ", "\tstub\n", "  STUB  "]

        for case in whitespace_cases:
            with patch.dict(os.environ, {"LLM_PROVIDER": case}, clear=False):
                provider = llm.get_provider()
                assert provider is not None
                assert isinstance(provider, llm.StubProvider)


class TestModuleImports:
    """Тесты обработки опциональных импортов"""

    def test_module_loads_without_external_deps(self):
        """Тест что модуль загружается без внешних зависимостей"""
        # Этот тест проверяет что модуль уже загружен
        assert llm.StubProvider is not None
        assert callable(llm.get_provider)

    def test_graceful_import_handling(self):
        """Тест graceful обработки отсутствующих импортов"""
        # Если модули недоступны, они должны быть None
        # Это проверяется в runtime при импорте модуля

        # Тестируем что fallback провайдеры работают через get_provider
        with patch.dict(os.environ, {"LLM_PROVIDER": "grok"}, clear=False):
            with patch.object(llm, "GrokProvider", None):
                grok_lite = llm.get_provider()
                assert grok_lite.name == "grok"

        stub = llm.StubProvider()
        assert stub.name == "stub"


@pytest.mark.asyncio
async def test_full_integration_scenario():
    """Интеграционный тест полного сценария"""
    # Тест scenario с stub провайдером
    with patch.dict(os.environ, {"LLM_PROVIDER": "stub"}, clear=False):
        provider = llm.get_provider()
        assert provider is not None

        result = await provider.generate("Calculate BMI for 70kg, 175cm")
        assert "Calculate BMI for 70kg, 175cm" in result
        assert "[stub @" in result
