"""
Tests for AI Router
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
from typing import Any, Generator

from core.ai_router import AIRouter, RequestComplexity, AIProvider


@pytest.fixture
def ai_router() -> AIRouter:
    """Create AI router instance"""
    return AIRouter()


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Mock environment variables"""
    with patch.dict(
        os.environ,
        {
            "OLLAMA_ENDPOINT": "http://localhost:11434",
            "OLLAMA_API_KEY": "test_ollama_key",
            "OPENAI_API_KEY": "test_openai_key",
            "OPENAI_MODEL": "gpt-4o-mini",
            "OLLAMA_MODEL": "llama3",
        },
    ):
        yield


class TestRequestComplexity:
    """Test request complexity analysis"""

    def test_analyze_complexity_simple(self, ai_router: AIRouter) -> None:
        """Test simple request complexity"""
        complexity = ai_router.analyze_complexity("What is protein?", {})
        assert complexity == RequestComplexity.SIMPLE

    def test_analyze_complexity_medium(self, ai_router: AIRouter) -> None:
        """Test medium request complexity"""
        complexity = ai_router.analyze_complexity("Create a meal plan", {})
        assert complexity == RequestComplexity.MEDIUM

    def test_analyze_complexity_complex(self, ai_router: AIRouter) -> None:
        """Test complex request complexity"""
        complexity = ai_router.analyze_complexity("Analyze my medical condition", {})
        assert complexity == RequestComplexity.COMPLEX

    def test_analyze_complexity_with_context(self, ai_router: AIRouter) -> None:
        """Test complexity analysis with context"""
        # Complex context
        context: dict[str, Any] = {"user_conditions": ["diabetes"], "allergies": ["nuts"]}
        complexity = ai_router.analyze_complexity("Simple question", context)
        assert complexity == RequestComplexity.COMPLEX

        # Medium context
        context = {"meal_planning": True, "diet_goals": ["weight_loss"]}
        complexity = ai_router.analyze_complexity("Simple question", context)
        assert complexity == RequestComplexity.MEDIUM

    def test_analyze_complexity_priority(self, ai_router: AIRouter) -> None:
        """Test that COMPLEX keywords take priority over MEDIUM"""
        # Message with both complex and medium keywords
        message = "Analyze my medical condition and create a meal plan"
        complexity = ai_router.analyze_complexity(message, {})
        assert complexity == RequestComplexity.COMPLEX


class TestProviderSelection:
    """Test provider selection logic"""

    def test_choose_provider_free_tier(self, ai_router: AIRouter) -> None:
        """Test provider selection for free tier"""
        # Simple request should use Ollama
        provider = ai_router.choose_provider(RequestComplexity.SIMPLE, "free")
        assert provider == AIProvider.OLLAMA

        # Medium request should use OpenAI
        provider = ai_router.choose_provider(RequestComplexity.MEDIUM, "free")
        assert provider == AIProvider.OPENAI

    def test_choose_provider_default_behavior(self, ai_router: AIRouter) -> None:
        """Test default provider selection behavior"""
        # Test the default case (line 145) - should return OPENAI for non-simple complexity
        assert (
            ai_router.choose_provider(RequestComplexity.MEDIUM, "unknown_tier") == AIProvider.OPENAI
        )
        assert (
            ai_router.choose_provider(RequestComplexity.COMPLEX, "unknown_tier")
            == AIProvider.OPENAI
        )

        # Complex request should use OpenAI for free users (if not rate limited)
        provider = ai_router.choose_provider(RequestComplexity.COMPLEX, "free", "test_user")
        assert provider == AIProvider.OPENAI

    def test_choose_provider_premium_tier(self, ai_router: AIRouter) -> None:
        """Test provider selection for premium tier"""
        # All requests should use OpenAI for premium
        for complexity in [
            RequestComplexity.SIMPLE,
            RequestComplexity.MEDIUM,
            RequestComplexity.COMPLEX,
        ]:
            provider = ai_router.choose_provider(complexity, "premium")
            assert provider == AIProvider.OPENAI


class TestRouteRequest:
    """Test request routing"""

    @pytest.mark.asyncio
    async def test_route_request_auto_routing(
        self, ai_router: AIRouter, mock_env_vars: Any  # noqa: ARG002
    ) -> None:
        """Test automatic routing"""
        with patch.object(ai_router, "_call_ollama", new_callable=AsyncMock) as mock_ollama:
            mock_ollama.return_value = {
                "response": "Test response",
                "provider": "ollama",
                "model": "llama3",
                "cost": 0.0,
                "tokens_used": 10,
                "fallback_used": False,
            }

            result = await ai_router.route_request("What is protein?", {}, "free")

            assert result["provider"] == "ollama"
            assert result["response"] == "Test response"
            mock_ollama.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_request_forced_provider(
        self, ai_router: AIRouter, mock_env_vars: Any  # noqa: ARG002
    ) -> None:
        """Test forced provider routing"""
        with (
            patch.object(ai_router, "_call_openai", new_callable=AsyncMock) as mock_openai,
            patch.object(ai_router, "_call_ollama", new_callable=AsyncMock) as mock_ollama,
        ):
            mock_openai.return_value = {
                "response": "OpenAI response",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "cost": 0.001,
                "tokens_used": 50,
                "fallback_used": False,
            }
            mock_ollama.return_value = {
                "response": "Ollama response",
                "provider": "ollama",
                "model": "llama3",
                "cost": 0.0,
                "tokens_used": 0,
                "fallback_used": False,
            }

            result = await ai_router.route_request(
                "Test message", {}, "free", "anonymous", "openai"
            )

            assert result["provider"] == "openai"
            assert result["response"] == "OpenAI response"
            mock_openai.assert_called_once()
            mock_ollama.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_request_invalid_provider(self, ai_router: AIRouter) -> None:
        """Test invalid provider handling"""
        result = await ai_router.route_request("Test message", {}, "free", "test_user", "invalid")
        assert result.provider == "unknown"
        assert "Invalid provider" in result.response

    @pytest.mark.asyncio
    async def test_route_request_fallback(self, ai_router: AIRouter, mock_env_vars: Any) -> None:
        """Test fallback mechanism"""
        # Use premium user so it chooses OpenAI first
        with patch.object(ai_router, "_call_openai", new_callable=AsyncMock) as mock_openai:
            # First call fails
            mock_openai.side_effect = Exception("OpenAI error")

            with patch.object(ai_router, "_call_ollama", new_callable=AsyncMock) as mock_ollama:
                mock_ollama.return_value = {
                    "response": "Fallback response",
                    "provider": "ollama",
                    "model": "llama3",
                    "cost": 0.0,
                    "tokens_used": 10,
                    "fallback_used": False,
                }

                result = await ai_router.route_request("Complex query", {}, "premium")

                assert result["provider"] == "ollama"
                assert result["fallback_used"] is True


class TestOllamaCall:
    """Test Ollama API calls"""

    @pytest.mark.asyncio
    async def test_call_ollama_success(self, ai_router: AIRouter, mock_env_vars: Any) -> None:
        """Test successful Ollama call"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Ollama response", "eval_count": 15}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            result = await ai_router._call_ollama("Test prompt", {})

            assert result["response"] == "Ollama response"
            assert result["provider"] == "ollama"
            assert result["cost"] == 0.0
            assert result["tokens_used"] == 15
            assert result["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_call_ollama_error(self, ai_router: AIRouter, mock_env_vars: Any) -> None:
        """Test Ollama call error handling"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
                "Connection error"
            )

            with pytest.raises(Exception, match="Connection error"):
                await ai_router._call_ollama("Test prompt", {})


class TestOpenAICall:
    """Test OpenAI API calls"""

    @pytest.mark.asyncio
    async def test_call_openai_success(self, ai_router: AIRouter, mock_env_vars: Any) -> None:
        """Test successful OpenAI call"""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 50

        mock_choice = MagicMock()
        mock_choice.message.content = "OpenAI response"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await ai_router._call_openai("Test prompt", {})

            assert result["response"] == "OpenAI response"
            assert result["provider"] == "openai"
            assert result["tokens_used"] == 100
            assert result["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_call_openai_error(self, ai_router: AIRouter, mock_env_vars: Any) -> None:
        """Test OpenAI call error handling"""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create.side_effect = Exception("API error")

            with pytest.raises(Exception, match="API error"):
                await ai_router._call_openai("Test prompt", {})

    @pytest.mark.asyncio
    async def test_call_openai_empty_choices(self, ai_router: AIRouter, mock_env_vars: Any) -> None:
        """Test OpenAI call with empty choices array"""
        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices array
        mock_response.usage = None

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            with pytest.raises(ValueError, match="OpenAI API returned empty choices array"):
                await ai_router._call_openai("Test prompt", {})


class TestSystemPrompt:
    """Test system prompt building"""

    def test_build_system_prompt_basic(self, ai_router: AIRouter) -> None:
        """Test basic system prompt"""
        context: dict[str, Any] = {}
        prompt = ai_router._build_system_prompt(context)

        assert "nutrition and health AI assistant" in prompt
        assert "PulsePlate" in prompt

    def test_build_system_prompt_with_context(self, ai_router: AIRouter) -> None:
        """Test system prompt with context"""
        context = {"diet_goals": ["weight_loss", "muscle_gain"], "user_conditions": ["diabetes"]}
        prompt = ai_router._build_system_prompt(context)

        assert "weight_loss" in prompt
        assert "muscle_gain" in prompt

    def test_build_system_prompt_medical_disclaimer(self, ai_router: AIRouter) -> None:
        """Test that medical disclaimer is included"""
        context: dict[str, Any] = {}
        prompt = ai_router._build_system_prompt(context)

        assert "medical diagnosis" in prompt.lower()
        assert "healthcare professional" in prompt.lower()


class TestCostCalculation:
    """Test cost calculation"""

    def test_calculate_openai_cost(self, ai_router: AIRouter) -> None:
        """Test OpenAI cost calculation"""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1000
        mock_usage.completion_tokens = 500

        cost = ai_router._calculate_openai_cost(mock_usage)

        # Expected: (1000/1M) * 0.15 + (500/1M) * 0.60 = 0.00015 + 0.0003 = 0.00045
        expected_cost = (1000 / 1_000_000) * 0.15 + (500 / 1_000_000) * 0.60
        assert abs(cost - expected_cost) < 0.0001

    def test_calculate_openai_cost_none_usage(self, ai_router: AIRouter) -> None:
        """Test cost calculation with None usage"""
        cost = ai_router._calculate_openai_cost(None)
        assert cost == 0.0

    def test_calculate_openai_cost_zero_tokens(self, ai_router: AIRouter) -> None:
        """Test cost calculation with zero tokens"""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 0
        mock_usage.completion_tokens = 0

        cost = ai_router._calculate_openai_cost(mock_usage)
        assert cost == 0.0


class TestEnvironmentConfiguration:
    """Test environment variable configuration"""

    def test_environment_variables_loaded(self, mock_env_vars: Any) -> None:
        """Test that environment variables are properly loaded"""
        router = AIRouter()

        assert router.ollama_endpoint == "http://localhost:11434"
        assert router.ollama_api_key == "test_ollama_key"
        assert router.openai_api_key == "test_openai_key"
        assert router.openai_model == "gpt-4o-mini"

    def test_default_values(self) -> None:
        """Test default values when environment variables are not set"""
        with patch.dict(os.environ, {}, clear=True):
            router = AIRouter()

            assert router.ollama_endpoint == "http://localhost:11434"
            assert router.openai_model == "gpt-4o-mini"
            assert router.ollama_api_key is None
            assert router.openai_api_key is None

    def test_production_validation_missing_openai_key(self) -> None:
        """Test production validation with missing OpenAI API key"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "OLLAMA_API_KEY": "test"}):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                AIRouter()

    def test_production_validation_missing_ollama_key(self) -> None:
        """Test production validation with missing Ollama API key"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "OPENAI_API_KEY": "test"}):
            with pytest.raises(ValueError, match="OLLAMA_API_KEY environment variable is required"):
                AIRouter()

    def test_invalid_ollama_endpoint_no_scheme(self) -> None:
        """Test invalid Ollama endpoint without scheme"""
        with patch.dict(os.environ, {"OLLAMA_ENDPOINT": "invalid-url"}):
            with pytest.raises(ValueError, match="Invalid OLLAMA_ENDPOINT URL"):
                AIRouter()

    def test_invalid_ollama_endpoint_no_netloc(self) -> None:
        """Test invalid Ollama endpoint without netloc"""
        with patch.dict(os.environ, {"OLLAMA_ENDPOINT": "http://"}):
            with pytest.raises(ValueError, match="Invalid OLLAMA_ENDPOINT URL"):
                AIRouter()

    def test_invalid_ollama_endpoint_exception(self) -> None:
        """Test invalid Ollama endpoint with exception during parsing"""
        with patch.dict(os.environ, {"OLLAMA_ENDPOINT": "http://test.com"}):
            with patch("urllib.parse.urlparse", side_effect=Exception("Parse error")):
                with pytest.raises(ValueError, match="Invalid OLLAMA_ENDPOINT URL"):
                    AIRouter()


class TestAdditionalCoverage:
    """Test additional coverage for uncovered lines"""

    @pytest.mark.asyncio
    async def test_route_request_forced_ollama_provider(
        self, ai_router: AIRouter, mock_env_vars: Any  # noqa: ARG002
    ) -> None:
        """Test route request with forced Ollama provider (line 160)"""
        with patch.object(ai_router, "_call_ollama", new_callable=AsyncMock) as mock_ollama:
            from core.ai_router import AIResponse

            mock_ollama.return_value = AIResponse(
                response="Test response",
                provider="ollama",
                model="llama3",
                cost=0.0,
                tokens_used=10,
                fallback_used=False,
            )

            result = await ai_router.route_request(
                "test message", {}, "free", "anonymous", "ollama"
            )

            assert result.response == "Test response"
            assert result.provider == "ollama"
            mock_ollama.assert_called_once_with("test message", {})

    @pytest.mark.asyncio
    async def test_route_request_fallback_openai_success(
        self, ai_router: AIRouter, mock_env_vars: Any
    ) -> None:
        """Test fallback to OpenAI when Ollama fails (lines 193-194)"""
        with patch.object(ai_router, "_call_ollama", new_callable=AsyncMock) as mock_ollama:
            with patch.object(ai_router, "_call_openai", new_callable=AsyncMock) as mock_openai:
                # Mock Ollama failure
                mock_ollama.side_effect = Exception("Ollama failed")

                # Mock OpenAI success
                mock_openai.return_value = {
                    "response": "OpenAI response",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "cost": 0.001,
                    "tokens_used": 20,
                    "fallback_used": False,
                }

                result = await ai_router.route_request("test message", {}, "free")

                assert result["response"] == "OpenAI response"
                assert result["provider"] == "openai"
                assert result["fallback_used"] is True
                mock_ollama.assert_called_once()
                mock_openai.assert_called_once()

    def test_build_system_prompt_with_allergies(self, ai_router: AIRouter) -> None:
        """Test _build_system_prompt with allergies context (line 294)"""
        context = {
            "allergies": ["nuts", "dairy"],
            "user_conditions": ["diabetes"],
            "diet_goals": ["weight_loss"],
        }

        prompt = ai_router._build_system_prompt(context)

        assert "User has conditions: diabetes" in prompt
        assert "User allergies: nuts, dairy" in prompt
        assert "User goals: weight_loss" in prompt
