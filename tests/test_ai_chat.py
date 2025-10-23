"""
Tests for AI Chat Router
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.routers.ai_chat import router, ChatRequest, ChatResponse, NutritionAnalysisRequest
from core.ai_router import RequestComplexity, AIProvider


@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_ai_router():
    """Mock AI router"""
    with patch("app.routers.ai_chat.ai_router") as mock:
        yield mock


class TestChatEndpoint:
    """Test /chat endpoint"""

    def test_chat_with_auto_routing(self, client, mock_ai_router):
        """Test chat with automatic routing"""
        # Mock router response
        mock_ai_router.route_request = AsyncMock(
            return_value={
                "response": "Test response",
                "provider": "ollama",
                "model": "llama3",
                "cost": 0.0,
                "tokens_used": 10,
                "fallback_used": False,
            }
        )
        mock_ai_router.analyze_complexity.return_value = RequestComplexity.SIMPLE

        response = client.post(
            "/api/ai/chat", json={"message": "What is protein?", "context": {}, "user_tier": "free"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        assert data["provider"] == "ollama"
        assert data["complexity"] == "simple"
        assert data["fallback_used"] is False

    def test_chat_with_forced_provider(self, client, mock_ai_router):
        """Test chat with forced provider"""
        # Mock router response for forced provider
        mock_ai_router.route_request = AsyncMock(
            return_value={
                "response": "OpenAI response",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "cost": 0.001,
                "tokens_used": 50,
                "fallback_used": False,
            }
        )
        mock_ai_router.analyze_complexity.return_value = RequestComplexity.COMPLEX

        response = client.post(
            "/api/ai/chat",
            json={
                "message": "Complex nutrition analysis",
                "context": {"user_conditions": ["diabetes"]},
                "user_tier": "premium",
                "force_provider": "openai",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert data["complexity"] == "complex"

    def test_chat_with_invalid_provider(self, client, mock_ai_router):
        """Test chat with invalid provider"""
        mock_ai_router.route_request.side_effect = ValueError("Invalid provider: invalid")

        response = client.post(
            "/api/ai/chat",
            json={
                "message": "Test message",
                "context": {},
                "user_tier": "free",
                "force_provider": "invalid",
            },
        )

        assert response.status_code == 500

    def test_chat_router_error(self, client, mock_ai_router):
        """Test chat when router raises exception"""
        mock_ai_router.route_request.side_effect = Exception("Router error")

        response = client.post(
            "/api/ai/chat", json={"message": "Test message", "context": {}, "user_tier": "free"}
        )

        assert response.status_code == 500
        assert "AI service error" in response.json()["detail"]


class TestNutritionAnalysisEndpoint:
    """Test /analyze-nutrition endpoint"""

    def test_nutrition_analysis_simple(self, client, mock_ai_router):
        """Test simple nutrition analysis"""
        mock_ai_router.route_request = AsyncMock(
            return_value={
                "response": "Basic nutrition info",
                "provider": "ollama",
                "model": "llama3",
                "cost": 0.0,
                "tokens_used": 20,
                "fallback_used": False,
            }
        )

        response = client.post(
            "/api/ai/analyze-nutrition",
            json={
                "food_items": ["apple", "banana"],
                "analysis_type": "basic",
                "user_profile": {"tier": "free"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Basic nutrition info"
        assert data["provider"] == "ollama"

    def test_nutrition_analysis_comprehensive(self, client, mock_ai_router):
        """Test comprehensive nutrition analysis"""
        mock_ai_router.route_request = AsyncMock(
            return_value={
                "response": "Comprehensive analysis",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "cost": 0.002,
                "tokens_used": 100,
                "fallback_used": False,
            }
        )

        response = client.post(
            "/api/ai/analyze-nutrition",
            json={
                "food_items": ["chicken breast", "brown rice", "broccoli"],
                "analysis_type": "comprehensive",
                "user_profile": {"tier": "premium", "goals": ["weight_loss"]},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert data["complexity"] == "complex"

    def test_nutrition_analysis_error(self, client, mock_ai_router):
        """Test nutrition analysis error handling"""
        mock_ai_router.route_request.side_effect = Exception("Analysis error")

        response = client.post(
            "/api/ai/analyze-nutrition",
            json={
                "food_items": ["apple"],
                "analysis_type": "basic",
                "user_profile": {"tier": "free"},
            },
        )

        assert response.status_code == 500
        assert "Analysis error" in response.json()["detail"]


class TestProvidersEndpoint:
    """Test /providers endpoint"""

    def test_get_providers(self, client):
        """Test getting available providers"""
        response = client.get("/api/ai/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "routing_strategy" in data
        assert len(data["providers"]) == 2
        assert data["providers"][0]["name"] == "ollama"
        assert data["providers"][1]["name"] == "openai"


class TestCostEstimateEndpoint:
    """Test /cost-estimate endpoint"""

    def test_cost_estimate_auto_ollama(self, client, mock_ai_router):
        """Test cost estimate with auto routing to Ollama"""
        mock_ai_router.analyze_complexity.return_value = RequestComplexity.SIMPLE
        mock_ai_router.choose_provider.return_value = AIProvider.OLLAMA

        response = client.get(
            "/api/ai/cost-estimate", params={"message": "What is protein?", "provider": "auto"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "ollama"
        assert data["estimated_cost"] == 0.0
        assert data["complexity"] == "simple"

    def test_cost_estimate_auto_openai(self, client, mock_ai_router):
        """Test cost estimate with auto routing to OpenAI"""
        mock_ai_router.analyze_complexity.return_value = RequestComplexity.COMPLEX
        mock_ai_router.choose_provider.return_value = AIProvider.OPENAI

        response = client.get(
            "/api/ai/cost-estimate",
            params={
                "message": "Complex nutrition analysis with detailed recommendations",
                "provider": "auto",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert data["estimated_cost"] > 0
        assert data["complexity"] == "complex"

    def test_cost_estimate_forced_provider(self, client, mock_ai_router):
        """Test cost estimate with forced provider"""
        response = client.get(
            "/api/ai/cost-estimate", params={"message": "Test message", "provider": "ollama"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "ollama"
        assert data["estimated_cost"] == 0.0
        assert data["complexity"] == "unknown"

    def test_cost_estimate_error(self, client, mock_ai_router):
        """Test cost estimate error handling"""
        mock_ai_router.analyze_complexity.side_effect = Exception("Analysis error")

        response = client.get(
            "/api/ai/cost-estimate", params={"message": "Test message", "provider": "auto"}
        )

        assert response.status_code == 500
        assert "Cost estimation error" in response.json()["detail"]


class TestRequestModels:
    """Test Pydantic request models"""

    def test_chat_request_validation(self):
        """Test ChatRequest model validation"""
        # Valid request
        request = ChatRequest(message="Test message", context={"key": "value"}, user_tier="free")
        assert request.message == "Test message"
        assert request.context == {"key": "value"}
        assert request.user_tier == "free"
        assert request.force_provider is None

        # With forced provider
        request = ChatRequest(
            message="Test message", context={}, user_tier="premium", force_provider="openai"
        )
        assert request.force_provider == "openai"

    def test_nutrition_analysis_request_validation(self):
        """Test NutritionAnalysisRequest model validation"""
        request = NutritionAnalysisRequest(
            food_items=["apple", "banana"], analysis_type="basic", user_profile={"tier": "free"}
        )
        assert request.food_items == ["apple", "banana"]
        assert request.analysis_type == "basic"
        assert request.user_profile == {"tier": "free"}

    def test_chat_response_validation(self):
        """Test ChatResponse model validation"""
        response = ChatResponse(
            response="Test response",
            provider="ollama",
            model="llama3",
            cost=0.0,
            tokens_used=10,
            complexity="simple",
            fallback_used=False,
        )
        assert response.response == "Test response"
        assert response.provider == "ollama"
        assert response.cost == 0.0
        assert response.fallback_used is False
