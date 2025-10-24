"""
AI Chat Router - Smart AI routing for nutrition and health queries
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Tuple, Literal
import logging

from core.ai_router import ai_router, RequestComplexity

logger = logging.getLogger(__name__)


def estimate_openai_cost(message: str) -> Tuple[float, int]:
    """
    Estimate OpenAI API cost and token usage for a message.

    Returns:
        Tuple of (estimated_cost, estimated_tokens)
    """
    # Constants for OpenAI GPT-4o-mini pricing (as of 2025-10-23)
    TOKEN_MULTIPLIER = 1.3  # Rough approximation factor
    INPUT_RATIO = 0.7  # 70% of tokens are input
    OUTPUT_RATIO = 0.3  # 30% of tokens are output
    INPUT_COST_PER_1K = 0.0006  # $0.0006 per 1K input tokens (from $0.60 per 1M)
    OUTPUT_COST_PER_1K = 0.0024  # $0.0024 per 1K output tokens (from $2.40 per 1M)

    # Calculate estimated tokens
    estimated_tokens = len(message.split()) * TOKEN_MULTIPLIER

    # Split into input/output tokens
    input_tokens = estimated_tokens * INPUT_RATIO
    output_tokens = estimated_tokens * OUTPUT_RATIO

    # Calculate cost
    cost = (input_tokens / 1000) * INPUT_COST_PER_1K + (output_tokens / 1000) * OUTPUT_COST_PER_1K

    # Round cost to 6 decimal places
    return round(cost, 6), int(estimated_tokens)


router = APIRouter(prefix="/api/ai", tags=["AI Chat"])


class ChatRequest(BaseModel):
    """Chat request model"""

    message: str = Field(..., description="User message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_tier: Literal["free", "premium"] = Field(
        default="free", description="User subscription tier"
    )
    task_type: str = Field(default="text", description="Task type (text/embedding)")
    force_provider: Optional[str] = Field(
        None, description="Force specific provider (ollama/huggingface/openai)"
    )

    @validator("message")
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response model"""

    response: str
    provider: str
    model: str
    cost: float
    tokens_used: int
    complexity: str
    fallback_used: bool = False


class NutritionAnalysisRequest(BaseModel):
    """Nutrition analysis request"""

    food_items: List[str] = Field(..., description="List of food items to analyze")
    user_profile: Dict[str, Any] = Field(default_factory=dict, description="User profile data")
    user_tier: Literal["free", "premium"] = Field(
        default="free", description="User tier (free/premium)"
    )
    analysis_type: Literal["basic", "detailed", "comprehensive"] = Field(
        default="basic", description="Type of analysis (basic/detailed/comprehensive)"
    )

    @validator("food_items")
    def validate_food_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one food item is required")
        return v


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    """
    Chat with AI using smart routing between Ollama and OpenAI
    """
    try:
        # Analyze complexity first
        complexity = ai_router.analyze_complexity(request.message, request.context)

        # Use smart routing with optional provider override
        result = await ai_router.route_request(
            request.message,
            request.context,
            request.user_tier,
            user_id=request.context.get("user_id", "anonymous"),
            provider=request.force_provider,
            task_type=request.task_type,
        )

        return ChatResponse(
            response=result.response,
            provider=result.provider,
            model=result.model,
            cost=result.cost,
            tokens_used=result.tokens_used,
            complexity=complexity.value,
            fallback_used=result.fallback_used,
        )

    except Exception as e:
        logger.exception("Error in AI chat")
        raise HTTPException(status_code=500, detail=f"AI service error: {e!s}") from e


@router.post("/analyze-nutrition", response_model=ChatResponse)
async def analyze_nutrition(request: NutritionAnalysisRequest) -> ChatResponse:
    """
    Analyze nutrition data using appropriate AI provider
    """
    try:
        # Build analysis prompt
        prompt = (
            f"Analyze the nutrition content of these food items: {', '.join(request.food_items)}"
        )

        # Create normalized user profile
        user_profile = {
            **request.user_profile,
            "analysis_type": request.analysis_type or "basic",
            "tier": request.user_tier or "free",
        }

        # Determine complexity based on analysis type
        if request.analysis_type == "comprehensive":
            complexity = RequestComplexity.COMPLEX
        elif request.analysis_type == "detailed":
            complexity = RequestComplexity.MEDIUM
        else:
            complexity = RequestComplexity.SIMPLE

        # Route request
        result = await ai_router.route_request(
            prompt,
            user_profile,
            request.user_tier or "free",
            user_id=request.user_profile.get("user_id", "anonymous"),
        )

        return ChatResponse(
            response=result.response,
            provider=result.provider,
            model=result.model,
            cost=result.cost,
            tokens_used=result.tokens_used,
            complexity=complexity.value,
            fallback_used=result.fallback_used,
        )

    except Exception as e:
        logger.exception("Error in nutrition analysis")
        raise HTTPException(status_code=500, detail=f"Analysis error: {e!s}") from e


@router.get("/providers")
async def get_available_providers() -> dict[str, Any]:
    """
    Get information about available AI providers
    """
    return {
        "providers": [
            {
                "name": "ollama",
                "description": "Local/Cloud Ollama - Free for simple queries",
                "models": ["llama3", "qwen3", "codellama"],
                "cost": "Free (local) or $20/month (cloud)",
                "best_for": ["Simple nutrition queries", "Basic meal planning"],
            },
            {
                "name": "openai",
                "description": "OpenAI API - High quality for complex queries",
                "models": ["gpt-4o-mini", "gpt-4o"],
                "cost": "$0.60 per 1M input tokens, $2.40 per 1M output tokens",
                "best_for": ["Complex analysis", "Personalized recommendations"],
            },
        ],
        "routing_strategy": {
            "simple_queries": "Ollama (free)",
            "medium_queries": "Ollama (free) or OpenAI (premium)",
            "complex_queries": "OpenAI (with fallback to Ollama)",
        },
    }


@router.get("/cost-estimate")
async def estimate_cost(message: str, provider: str = "auto") -> dict[str, Any]:
    """
    Estimate cost for a message
    """
    try:
        complexity = None
        if provider == "auto":
            complexity = ai_router.analyze_complexity(message, {})
            provider_enum = ai_router.choose_provider(complexity, "free")
            chosen_provider = provider_enum.value
        else:
            chosen_provider = provider

        complexity_value = complexity.value if complexity is not None else "unknown"

        if chosen_provider == "ollama":
            return {
                "provider": "ollama",
                "estimated_cost": 0.0,
                "complexity": complexity_value,
            }
        else:
            # Use centralized cost estimation
            estimated_cost, estimated_tokens = estimate_openai_cost(message)

            return {
                "provider": "openai",
                "estimated_cost": estimated_cost,
                "estimated_tokens": estimated_tokens,
                "complexity": complexity_value,
                "estimated_cost_note": "Cost is an estimate and may differ from final billed amount",
            }

    except Exception as e:
        logger.exception("Error estimating cost")
        raise HTTPException(status_code=500, detail=f"Cost estimation error: {e!s}") from e
