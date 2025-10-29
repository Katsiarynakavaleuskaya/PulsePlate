# -*- coding: utf-8 -*-
"""
Tests for AI integration system based on Claude Cookbooks patterns.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, TYPE_CHECKING

import pytest

from core.ai_integration import PulsePlateAI, create_pulseplate_ai
from core.llm_enhanced import ResponseFormat, LLMResponse, EnhancedLLMProvider
from core.agent_system import AgentTask, AgentType, AgentOrchestrator

if TYPE_CHECKING:
    from core.llm_enhanced import EnhancedLLMProvider
    from core.agent_system import AgentOrchestrator


class TestPulsePlateAI:
    """Test PulsePlate AI integration system."""

    @pytest.fixture
    def mock_llm_provider(self) -> MagicMock:
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(
            return_value='{"nutrition_score": 8, "health_benefits": ["High fiber", "Vitamin C"]}'
        )
        return provider

    @pytest.fixture
    def temp_storage(self) -> Path:
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def ai_system(self, mock_llm_provider: MagicMock, temp_storage: Path) -> PulsePlateAI:
        """Create AI system for testing."""
        return create_pulseplate_ai(mock_llm_provider, temp_storage)

    @pytest.mark.asyncio
    async def test_analyze_food_comprehensive(self, ai_system: PulsePlateAI) -> None:
        """Test comprehensive food analysis."""
        food_data = {
            "name": "Apple",
            "nutrients_per_100g": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
            "source": "test",
            "source_id": "test_apple",
        }

        result = await ai_system.analyze_food_comprehensive(food_data)

        assert "food_name" in result
        assert "analysis_timestamp" in result
        assert "nutrition_analysis" in result
        assert "overall_score" in result
        assert result["food_name"] == "Apple"
        assert result["overall_score"] > 0

    @pytest.mark.asyncio
    async def test_create_personalized_meal_plan(self, ai_system: PulsePlateAI) -> None:
        """Test personalized meal plan creation."""
        user_profile = {
            "dietary_goals": "weight loss",
            "preferences": {"vegetarian": True},
            "allergies": [],
        }

        available_foods = [
            {"name": "Apple", "nutrients_per_100g": {"calories": 52}},
            {"name": "Banana", "nutrients_per_100g": {"calories": 89}},
        ]

        result = await ai_system.create_personalized_meal_plan(user_profile, available_foods)

        assert "meal_plan" in result
        assert "evaluation" in result
        assert "creation_timestamp" in result
        assert "score" in result["evaluation"]

    @pytest.mark.asyncio
    async def test_answer_nutrition_question(self, ai_system: PulsePlateAI) -> None:
        """Test nutrition question answering."""
        question = "What are the health benefits of apples?"
        user_context = {"dietary_goals": "healthy eating"}

        result = await ai_system.answer_nutrition_question(question, user_context)

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
        assert "evaluation" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_optimize_meal_plan_cost(self, ai_system: PulsePlateAI) -> None:
        """Test meal plan cost optimization."""
        meal_plan = {
            "breakfast": {"foods": ["Apple"], "calories": 100},
            "lunch": {"foods": ["Banana"], "calories": 150},
        }

        budget = 50.0
        available_foods = [
            {"name": "Apple", "cost_per_100g": 0.5},
            {"name": "Banana", "cost_per_100g": 0.3},
        ]

        result = await ai_system.optimize_meal_plan_cost(meal_plan, budget, available_foods)

        assert "optimized_plan" in result
        assert "optimization_timestamp" in result
        assert "success" in result

    @pytest.mark.asyncio
    async def test_get_health_advice(self, ai_system: PulsePlateAI) -> None:
        """Test health advice generation."""
        health_data = {"age": 30, "weight": 70, "height": 170, "dietary_restrictions": []}

        question = "What should I eat for better energy?"

        result = await ai_system.get_health_advice(health_data, question)

        assert "advice" in result
        assert "safety_evaluation" in result
        assert "timestamp" in result
        assert "score" in result["safety_evaluation"]

    @pytest.mark.asyncio
    async def test_populate_knowledge_base(self, ai_system: PulsePlateAI) -> None:
        """Test knowledge base population."""
        foods_data = {
            "apple": {
                "name": "Apple",
                "nutrients_per_100g": {"calories": 52},
                "source": "test",
                "source_id": "test_apple",
            },
            "banana": {
                "name": "Banana",
                "nutrients_per_100g": {"calories": 89},
                "source": "test",
                "source_id": "test_banana",
            },
        }

        await ai_system.populate_knowledge_base(foods_data)

        # Verify knowledge base was populated
        assert len(ai_system.rag_system.vector_store.documents) == 2

    @pytest.mark.asyncio
    async def test_evaluate_system_performance(self, ai_system: PulsePlateAI) -> None:
        """Test system performance evaluation."""
        result = await ai_system.evaluate_system_performance()

        assert "analysis_performance" in result
        assert "rag_performance" in result
        assert "system_status" in result
        assert "evaluation_timestamp" in result
        assert result["system_status"] == "operational"

    @pytest.mark.asyncio
    async def test_error_handling(self, ai_system: PulsePlateAI) -> None:
        """Test error handling in AI system."""
        # Test with invalid food data
        invalid_food = {"invalid": "data"}

        result = await ai_system.analyze_food_comprehensive(invalid_food)

        # Should still return a result structure
        assert "food_name" in result
        assert "analysis_timestamp" in result
        assert "overall_score" in result

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, ai_system: PulsePlateAI) -> None:
        """Test concurrent AI operations."""
        food_data = {
            "name": "Apple",
            "nutrients_per_100g": {"calories": 52},
            "source": "test",
            "source_id": "test_apple",
        }

        # Run multiple operations concurrently
        tasks = [
            ai_system.analyze_food_comprehensive(food_data),
            ai_system.answer_nutrition_question("What is an apple?"),
            ai_system.evaluate_system_performance(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)


class TestEnhancedLLMProvider:
    """Test enhanced LLM provider functionality."""

    @pytest.fixture
    def mock_base_provider(self) -> MagicMock:
        """Create mock base provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value='{"test": "value"}')
        return provider

    @pytest.fixture
    def enhanced_provider(self, mock_base_provider: MagicMock) -> EnhancedLLMProvider:
        """Create enhanced provider."""
        from core.llm_enhanced import create_enhanced_provider

        return create_enhanced_provider(mock_base_provider)

    @pytest.mark.asyncio
    async def test_generate_structured_json(self, enhanced_provider: EnhancedLLMProvider) -> None:
        """Test structured JSON generation."""
        prompt = "Generate a test response"
        schema = {"test": str}

        result = await enhanced_provider.generate_structured(prompt, ResponseFormat.JSON, schema)

        assert isinstance(result, LLMResponse)
        assert result.format == ResponseFormat.JSON
        assert result.is_valid
        assert result.content == '{"test": "value"}'

    @pytest.mark.asyncio
    async def test_generate_structured_text(self, enhanced_provider: EnhancedLLMProvider) -> None:
        """Test structured text generation."""
        prompt = "Generate a test response"

        result = await enhanced_provider.generate_structured(prompt, ResponseFormat.TEXT)

        assert isinstance(result, LLMResponse)
        assert result.format == ResponseFormat.TEXT
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_validation_failure(self, enhanced_provider: EnhancedLLMProvider) -> None:
        """Test validation failure handling."""
        # Mock provider to return invalid JSON
        enhanced_provider.base_provider.generate = AsyncMock(return_value="invalid json")

        result = await enhanced_provider.generate_structured("test", ResponseFormat.JSON)

        assert not result.is_valid
        assert "Invalid JSON" in result.error_message


class TestAgentSystem:
    """Test agent system functionality."""

    @pytest.fixture
    def mock_llm_provider(self) -> MagicMock:
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value='{"nutrition_score": 8}')
        return provider

    @pytest.fixture
    def agent_orchestrator(self, mock_llm_provider: MagicMock) -> AgentOrchestrator:
        """Create agent orchestrator."""
        from core.agent_system import create_agent_orchestrator

        return create_agent_orchestrator(mock_llm_provider)

    @pytest.mark.asyncio
    async def test_execute_nutrition_analyzer_task(
        self, agent_orchestrator: AgentOrchestrator
    ) -> None:
        """Test nutrition analyzer task execution."""
        task = AgentTask(
            task_type=AgentType.NUTRITION_ANALYZER,
            input_data={"food_data": {"name": "Apple", "calories": 52}},
            priority=1,
        )

        result = await agent_orchestrator.execute_task(task)

        assert result.success
        assert result.agent_type == AgentType.NUTRITION_ANALYZER
        assert "nutrition_score" in result.data

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self, agent_orchestrator: AgentOrchestrator) -> None:
        """Test parallel task execution."""
        tasks = [
            AgentTask(
                task_type=AgentType.NUTRITION_ANALYZER,
                input_data={"food_data": {"name": "Apple"}},
                priority=1,
            ),
            AgentTask(
                task_type=AgentType.MEAL_PLANNER,
                input_data={"user_profile": {"goals": "health"}},
                priority=2,
            ),
        ]

        results = await agent_orchestrator.execute_parallel_tasks(tasks)

        assert len(results) == 2
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_task_error_handling(self, agent_orchestrator: AgentOrchestrator) -> None:
        """Test task error handling."""
        # Mock the LLM provider to raise an exception
        agent_orchestrator.agents[AgentType.NUTRITION_ANALYZER].llm_provider.generate = AsyncMock(
            side_effect=Exception("Test error")
        )

        task = AgentTask(
            task_type=AgentType.NUTRITION_ANALYZER,
            input_data={"food_data": {"name": "Apple"}},
            priority=1,
        )

        result = await agent_orchestrator.execute_task(task)

        # Should handle error gracefully - agent catches exception and returns error in data
        assert result.success is False  # Agent should fail when LLM provider raises exception
        assert "error" in result.data or "error" in str(result.error_message)
        # Error message should contain the test error
        assert "Test error" in str(result.data.get("error", "")) or "Test error" in str(
            result.error_message
        )


# Integration test
@pytest.mark.asyncio
async def test_full_ai_workflow() -> None:
    """Test complete AI workflow integration."""
    # Create mock provider
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(
        return_value='{"nutrition_score": 8, "health_benefits": ["High fiber"]}'
    )

    # Create temporary storage
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_path = Path(tmp_dir)

        # Create AI system
        ai_system = create_pulseplate_ai(mock_provider, storage_path)

        # Test complete workflow
        food_data = {
            "name": "Apple",
            "nutrients_per_100g": {"calories": 52, "protein": 0.3},
            "source": "test",
            "source_id": "test_apple",
        }

        # Analyze food
        analysis = await ai_system.analyze_food_comprehensive(food_data)
        assert analysis["overall_score"] > 0

        # Answer question
        answer = await ai_system.answer_nutrition_question("What are apples good for?")
        assert "answer" in answer

        # Evaluate performance
        performance = await ai_system.evaluate_system_performance()
        assert performance["system_status"] == "operational"
