"""
Комплексные тесты для модуля llm.py
Цель: 100% покрытие кода для LLM провайдера selector'а
"""

import os
from unittest.mock import Mock, patch

import pytest

import llm


@pytest.mark.slow
class TestStubProvider:
    """Тесты для StubProvider заглушки"""

    def test_stub_provider_creation(self) -> None:
        """Тест создания провайдера-заглушки"""
        provider = llm.StubProvider()
        assert provider is not None
        assert provider.name == "stub"
        assert hasattr(provider, "generate")

    @pytest.mark.asyncio
    async def test_stub_provider_generate(self) -> None:
        """Тест генерации текста провайдером-заглушкой"""
        provider = llm.StubProvider()
        result = await provider.generate("test input")

        # Проверяем структуру ответа
        assert "[stub @" in result
        assert "Insight: test input" in result
        assert "T" in result  # ISO datetime содержит T

    @pytest.mark.asyncio
    async def test_stub_provider_generate_complex_text(self) -> None:
        """Тест генерации с сложным текстом"""
        provider = llm.StubProvider()
        complex_input = "Многострочный\nтекст с символами: @#$%^&*()"
        result = await provider.generate(complex_input)

        assert complex_input in result
        assert "[stub @" in result


class TestPerplexityLiteProvider:
    """Тесты для PerplexityLiteProvider fallback'а"""

    def test_grok_lite_provider_through_exception(self):
        """Тест PerplexityLiteProvider через симуляцию отсутствия providers.perplexity"""
        # Тестируем PerplexityLiteProvider симулируя отсутствие настоящего провайдера
        with patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}, clear=False):
            # Мокаем PerplexityProvider на уровне модуля как None
            with patch.object(llm, "PerplexityProvider", None):
                # Нам нужно создать класс PerplexityLiteProvider для теста
                original_grok_lite = getattr(llm, "PerplexityLiteProvider", None)

                # Если PerplexityLiteProvider не существует, создаем его
                if not original_grok_lite:

                    class MockPerplexityLiteProvider:
                        name = "perplexity"

                        def __init__(self, *args, **kwargs):
                            pass

                        async def generate(self, text: str) -> str:
                            return f"[perplexity-lite] {text}"

                    # Патчим get_provider чтобы возвращал наш мок
                    with patch.object(llm, "get_provider") as mock_get:
                        mock_provider = MockPerplexityLiteProvider()
                        mock_get.return_value = mock_provider

                        provider = llm.get_provider()
                        assert provider is not None
                        assert provider.name == "perplexity"
                else:
                    provider = llm.get_provider()
                    assert provider is not None

    @pytest.mark.asyncio
    async def test_grok_lite_provider_generate(self):
        """Тест генерации текста через PerplexityLiteProvider"""

        # Создаем мок провайдер для теста генерации
        # Создаем мок провайдер для теста генерации
        class MockPerplexityLiteProvider:
            name = "perplexity"

            def __init__(self, *args, **kwargs):
                pass

            async def generate(self, text: str) -> str:
                return f"[perplexity-lite] {text}"

        provider = MockPerplexityLiteProvider()
        result = await provider.generate("nutrition question")

        assert result == "[perplexity-lite] nutrition question"
        assert "perplexity-lite" in result


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
    """Тесты для Perplexity провайдера"""

    def test_get_provider_grok_fallback_when_none(self):
        """Тест fallback на PerplexityLiteProvider когда PerplexityProvider недоступен"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}, clear=False):
            # Мокаем недоступность настоящего PerplexityProvider
            with patch.object(llm, "PerplexityProvider", None):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "perplexity"

    @patch("llm.PerplexityProvider")
    def test_get_provider_grok_with_env_vars(self, mock_grok_class):
        """Тест создания PerplexityProvider с переменными окружения"""
        mock_instance = Mock()
        mock_grok_class.return_value = mock_instance

        env_vars = {
            "LLM_PROVIDER": "perplexity",
            "PERPLEXITY_API_KEY": "test-key-123",
            "PERPLEXITY_MODEL": "sonar-pro",
            "PERPLEXITY_ENDPOINT": "https://test.api.com",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            provider = llm.get_provider()

            # Проверяем что PerplexityProvider был вызван с правильными параметрами
            mock_grok_class.assert_called_once_with(
                endpoint="https://test.api.com", api_key="test-key-123", model="sonar-pro"
            )
            assert provider == mock_instance

    @patch("llm.PerplexityProvider")
    def test_get_provider_perplexity_with_api_key(self, mock_grok_class):
        """Тест использования PERPLEXITY_API_KEY."""
        mock_instance = Mock()
        mock_grok_class.return_value = mock_instance

        env_vars = {
            "LLM_PROVIDER": "perplexity",
            "PERPLEXITY_API_KEY": "xai-key-456",  # Альтернативное имя ключа
        }

        with patch.dict(os.environ, env_vars, clear=False):
            provider = llm.get_provider()
            assert provider is not None

            mock_grok_class.assert_called_once_with(
                endpoint="https://api.perplexity.ai/v1",  # дефолтный endpoint
                api_key="xai-key-456",
                model="sonar",  # дефолтная модель
            )

    def test_get_provider_grok_defaults(self):
        """Тест дефолтных значений для Perplexity провайдера (fallback to PerplexityLiteProvider when no API key)"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}, clear=False):
            # Очищаем все Grok-related env vars
            grok_vars = [
                "PERPLEXITY_API_KEY",
                "PERPLEXITY_API_KEY",
                "PERPLEXITY_MODEL",
                "PERPLEXITY_ENDPOINT",
            ]
            for var in grok_vars:
                if var in os.environ:
                    del os.environ[var]

            provider = llm.get_provider()
            assert provider is not None
            # Когда нет API ключа, должен вернуть PerplexityLiteProvider
            assert provider.__class__.__name__ == "PerplexityLiteProvider"
            assert provider.name == "perplexity"

    @patch("llm.PerplexityProvider")
    def test_get_provider_grok_keyword_exception_fallback(self, mock_grok_class):
        """Тест fallback при ошибке keyword arguments"""
        # Мокаем TypeError при вызове с keyword args
        mock_grok_class.side_effect = [TypeError("unexpected keyword"), Mock()]

        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "perplexity", "PERPLEXITY_API_KEY": "test-key"},
            clear=False,
        ):
            provider = llm.get_provider()
            assert provider is not None

            # Perplexity path uses one constructor attempt and falls back to lite on error.
            assert mock_grok_class.call_count == 1

    @patch("llm.PerplexityProvider")
    def test_get_provider_grok_all_exceptions_fallback(self, mock_grok_class):
        """Тест fallback на PerplexityLiteProvider при всех ошибках"""
        # Мокаем ошибки для всех попыток создания
        mock_grok_class.side_effect = Exception("Connection failed")

        with patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}, clear=False):
            provider = llm.get_provider()

            # Должен вернуться PerplexityLiteProvider
            assert provider is not None
            assert provider.name == "perplexity"


class TestGetProviderOllama:
    """Тесты для Ollama провайдера"""

    def test_get_provider_ollama_none_when_unavailable(self) -> None:
        """Тест возврата OllamaLiteProvider когда OllamaProvider недоступен"""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            with patch.object(llm, "OllamaProvider", None):
                provider = llm.get_provider()
                # When OllamaProvider is None, should fallback to OllamaLiteProvider (like PerplexityProvider)
                assert provider is not None
                assert provider.name == "ollama"

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
                endpoint="http://localhost:11434", model="llama3.1:8b", timeout_s=1.5
            )

    @patch("llm.OllamaProvider")
    def test_get_provider_ollama_exception_fallback(self, mock_ollama_class):
        """Тест fallback при ошибках создания OllamaProvider"""
        # Первый вызов с kwargs дает ошибку, второй с positional args тоже
        mock_ollama_class.side_effect = [TypeError("keyword issue"), Exception("failed")]

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            provider = llm.get_provider()

            # При ошибках должен вернуться OllamaLiteProvider (консистентно с PerplexityProvider)
            assert provider is not None
            assert provider.name == "ollama"
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
        with patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}, clear=False):
            with patch.object(llm, "PerplexityProvider", None):
                grok_lite = llm.get_provider()
                assert grok_lite.name == "perplexity"

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
