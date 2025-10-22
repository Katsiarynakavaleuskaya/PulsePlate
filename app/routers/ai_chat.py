"""
AI Chat Router - Smart AI routing for nutrition and health queries
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from core.ai_router import ai_router, RequestComplexity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Chat"])


class ChatRequest(BaseModel):
    """Chat request model"""

    message: str = Field(..., description="User message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_tier: str = Field(default="free", description="User subscription tier")
    force_provider: Optional[str] = Field(
        None, description="Force specific provider (ollama/openai)"
    )


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
    analysis_type: str = Field(
        default="basic", description="Type of analysis (basic/detailed/comprehensive)"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Chat with AI using smart routing between Ollama and OpenAI
    """
    try:
        # Force provider if specified
        if request.force_provider:
            if request.force_provider == "ollama":
                result = await ai_router._call_ollama(request.message, request.context)
            elif request.force_provider == "openai":
                result = await ai_router._call_openai(request.message, request.context)
            else:
                raise HTTPException(
                    status_code=400, detail="Invalid provider. Use 'ollama' or 'openai'"
                )
        else:
            # Use smart routing
            result = await ai_router.route_request(
                request.message, request.context, request.user_tier
            )

        # Analyze complexity for response
        complexity = ai_router.analyze_complexity(request.message, request.context)

        return ChatResponse(
            response=result["response"],
            provider=result["provider"],
            model=result["model"],
            cost=result["cost"],
            tokens_used=result["tokens_used"],
            complexity=complexity.value,
            fallback_used=request.force_provider is not None,
        )

    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/analyze-nutrition", response_model=ChatResponse)
async def analyze_nutrition(request: NutritionAnalysisRequest):
    """
    Analyze nutrition data using appropriate AI provider
    """
    try:
        # Build analysis prompt
        prompt = (
            f"Analyze the nutrition content of these food items: {', '.join(request.food_items)}"
        )

        # Determine complexity based on analysis type
        if request.analysis_type == "comprehensive":
            request.user_profile["analysis_type"] = "comprehensive"
            complexity = RequestComplexity.COMPLEX
        elif request.analysis_type == "detailed":
            complexity = RequestComplexity.MEDIUM
        else:
            complexity = RequestComplexity.SIMPLE

        # Route request
        result = await ai_router.route_request(
            prompt, request.user_profile, request.user_profile.get("tier", "free")
        )

        return ChatResponse(
            response=result["response"],
            provider=result["provider"],
            model=result["model"],
            cost=result["cost"],
            tokens_used=result["tokens_used"],
            complexity=complexity.value,
            fallback_used=False,
        )

    except Exception as e:
        logger.error(f"Error in nutrition analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/providers")
async def get_available_providers():
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
                "cost": "$0.15-0.60 per 1K tokens",
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
async def estimate_cost(message: str, provider: str = "auto"):
    """
    Estimate cost for a message
    """
    try:
        if provider == "auto":
            complexity = ai_router.analyze_complexity(message, {})
            chosen_provider = ai_router.choose_provider(complexity, "free")
        else:
            chosen_provider = provider

        if chosen_provider == "ollama":
            return {
                "provider": "ollama",
                "estimated_cost": 0.0,
                "complexity": complexity.value if provider == "auto" else "unknown",
            }
        else:
            # Rough estimate for OpenAI
            estimated_tokens = len(message.split()) * 1.3  # Rough token estimation
            estimated_cost = (estimated_tokens / 1000) * 0.0006  # Output cost

            return {
                "provider": "openai",
                "estimated_cost": round(estimated_cost, 6),
                "estimated_tokens": int(estimated_tokens),
                "complexity": complexity.value if provider == "auto" else "unknown",
            }

    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=f"Cost estimation error: {str(e)}")
