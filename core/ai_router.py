"""
AI Router - Smart routing between Ollama and OpenAI based on request complexity
"""

import os
import time
import threading
from typing import Dict, Any, Optional, Union, List
from enum import Enum
import logging
import httpx
import openai

# Optional imports for Hugging Face functionality
try:
    import torch
    from transformers import AutoModel, AutoTokenizer

    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    AutoModel = None  # type: ignore
    AutoTokenizer = None  # type: ignore
    TORCH_AVAILABLE = False
from pydantic import BaseModel

from core.ai_constants import (
    OPENAI_INPUT_COST_PER_1M,
    OPENAI_OUTPUT_COST_PER_1M,
    DEFAULT_RATE_LIMIT_FREE,
    DEFAULT_RATE_LIMIT_PREMIUM,
    DEFAULT_RATE_LIMIT_ENTERPRISE,
)

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"


class RequestComplexity(Enum):
    SIMPLE = "simple"  # Basic nutrition info, simple questions
    MEDIUM = "medium"  # Meal planning, basic analysis
    COMPLEX = "complex"  # Detailed analysis, complex recommendations


class AIResponse(BaseModel):
    """Structured response from AI providers"""

    response: Union[str, List[float]]  # Support both text responses and embeddings
    provider: str
    model: str
    cost: float
    tokens_used: int
    fallback_used: bool = False
    error: bool = False


class AIRouter:
    """
    Smart AI router that chooses between Ollama, Hugging Face, and OpenAI based on:
    1. Request complexity
    2. Cost optimization
    3. Quality requirements
    4. Task type (embeddings vs text generation)
    """

    def __init__(self) -> None:
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        self.ollama_api_key = os.getenv("OLLAMA_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

        # Safe parsing of OPENAI_MAX_TOKENS
        try:
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        except ValueError:
            msg = f"Invalid OPENAI_MAX_TOKENS value: {os.getenv('OPENAI_MAX_TOKENS')}, using default 1000"
            logger.warning(msg)
            self.max_tokens = 1000

        # Hugging Face model caching
        self._hf_tokenizer: Optional[Any] = None
        self._hf_model: Optional[Any] = None
        self._hf_model_name: Optional[str] = None
        self._hf_revision: Optional[str] = None
        self._hf_trust_remote: Optional[bool] = None
        self._hf_token: Optional[str] = None
        self._hf_lock = threading.Lock()

        # Hugging Face configuration
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self.huggingface_model = os.getenv("HUGGINGFACE_MODEL", "nvidia/llama-embed-nemotron-8b")
        self.huggingface_model_revision = os.getenv("HUGGINGFACE_MODEL_REVISION")

        # Safe parsing of HUGGINGFACE_MAX_LENGTH
        try:
            self.huggingface_max_length = int(os.getenv("HUGGINGFACE_MAX_LENGTH", "512"))
        except ValueError:
            msg = f"Invalid HUGGINGFACE_MAX_LENGTH value: {os.getenv('HUGGINGFACE_MAX_LENGTH')}, using default 512"
            logger.warning(msg)
            self.huggingface_max_length = 512

        # Validate required environment variables (only in production)
        # Skip validation during testing or when environment variables are not set
        if os.getenv("ENVIRONMENT") == "production":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            if not self.ollama_api_key:
                raise ValueError("OLLAMA_API_KEY environment variable is required")
            if not self.huggingface_model_revision:
                msg = "HUGGINGFACE_MODEL_REVISION environment variable is required for security"
                raise ValueError(msg)
            # HuggingFace API token required for embedding tasks in production
            if not self.huggingface_api_token:
                msg = "HUGGINGFACE_API_TOKEN environment variable is required for embedding tasks"
                raise ValueError(msg)

        # Validate OLLAMA_ENDPOINT URL
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.ollama_endpoint)
            if not parsed.scheme or not parsed.netloc:
                msg = f"Invalid OLLAMA_ENDPOINT URL: {self.ollama_endpoint}"
                raise ValueError(msg)
        except Exception as e:
            msg = f"Invalid OLLAMA_ENDPOINT URL: {self.ollama_endpoint} - {str(e)}"
            raise ValueError(msg) from e

        # Rate limiting implemented via _is_rate_limited method (lines 168-208)
        # Uses in-memory sliding window with configurable limits per user tier
        self._rate_limit_store: dict[str, list[float]] = {}
        self._rate_limit_lock: threading.Lock = threading.Lock()

        # Redis client for rate limiting
        self._redis_client = None
        try:
            import redis  # type: ignore[import-not-found]

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._redis_client.ping()
            logger.info("Redis client initialized successfully for rate limiting")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}, using in-memory fallback")
            self._redis_client = None

        # Configurable per-tier hourly limits (defaults are conservative)
        try:
            self.rate_limit_free = int(
                os.getenv("AI_RATE_LIMIT_FREE_PER_HOUR", str(DEFAULT_RATE_LIMIT_FREE))
            )
            self.rate_limit_premium = int(
                os.getenv("AI_RATE_LIMIT_PREMIUM_PER_HOUR", str(DEFAULT_RATE_LIMIT_PREMIUM))
            )
            self.rate_limit_enterprise = int(
                os.getenv("AI_RATE_LIMIT_ENTERPRISE_PER_HOUR", str(DEFAULT_RATE_LIMIT_ENTERPRISE))
            )
        except ValueError:
            logger.warning("Invalid AI_RATE_LIMIT_* envs; using defaults 10/1000/10000")
            self.rate_limit_free, self.rate_limit_premium, self.rate_limit_enterprise = (
                DEFAULT_RATE_LIMIT_FREE,
                DEFAULT_RATE_LIMIT_PREMIUM,
                DEFAULT_RATE_LIMIT_ENTERPRISE,
            )

        # Quality thresholds
        self.complexity_keywords: dict[RequestComplexity, list[str]] = {
            RequestComplexity.SIMPLE: [
                "calories",
                "protein",
                "carbs",
                "fat",
                "vitamin",
                "mineral",
                "basic",
                "simple",
                "quick",
                "amount",
                "quantity",
            ],
            RequestComplexity.MEDIUM: [
                "meal plan",
                "diet",
                "nutrition",
                "recommendation",
                "suggest",
                "balance",
                "healthy",
                "recipe",
                "ingredient",
            ],
            RequestComplexity.COMPLEX: [
                "detailed analysis",
                "comprehensive",
                "personalized",
                "custom",
                "medical",
                "condition",
                "allergy",
                "intolerance",
                "special",
                "optimization",
                "advanced",
                "scientific",
            ],
        }

    def analyze_complexity(self, prompt: str, context: Dict[str, Any]) -> RequestComplexity:
        """
        Analyze request complexity based on prompt and context
        """
        prompt_lower = prompt.lower()

        # Keyword-based detection (priority: COMPLEX > MEDIUM)
        for level in (RequestComplexity.COMPLEX, RequestComplexity.MEDIUM):
            if any(kw in prompt_lower for kw in self.complexity_keywords[level]):
                return level

        # Check context for complexity indicators
        if context.get("user_conditions") or context.get("allergies"):
            return RequestComplexity.COMPLEX

        if context.get("meal_planning") or context.get("diet_goals"):
            return RequestComplexity.MEDIUM

        # Default to simple
        return RequestComplexity.SIMPLE

    def choose_provider(
        self,
        complexity: RequestComplexity,
        user_tier: str = "free",
        user_id: str = "anonymous",
        task_type: str = "text",
    ) -> AIProvider:
        """
        Choose AI provider based on complexity, user tier, and task type
        """
        # For embedding tasks, prefer Hugging Face (free tier available)
        if task_type == "embedding" and self.huggingface_api_token and TORCH_AVAILABLE:
            return AIProvider.HUGGINGFACE

        # Check rate limits for all users (not just free)
        if self._is_rate_limited(user_id, user_tier):
            return AIProvider.OLLAMA

        # Premium users get OpenAI for all text requests (if not rate limited)
        if user_tier == "premium" and task_type == "text":
            return AIProvider.OPENAI

        # Free users: Allow complex queries if not rate limited
        if user_tier == "free" and complexity == RequestComplexity.COMPLEX:
            return AIProvider.OPENAI

        # Explicit complexity-based routing for other cases
        if complexity == RequestComplexity.SIMPLE:
            return AIProvider.OLLAMA
        elif complexity == RequestComplexity.MEDIUM:
            return AIProvider.OPENAI
        else:  # RequestComplexity.COMPLEX or any other value
            return AIProvider.OPENAI

    def _is_rate_limited(self, user_id: str, user_tier: str) -> bool:
        """
        Check if user is rate limited using Redis sliding window
        """
        try:
            if not hasattr(self, "_redis_client") or self._redis_client is None:
                # Fallback to in-memory rate limiting if Redis is not available
                return self._is_rate_limited_memory(user_id, user_tier)

            current_time = time.time()
            window_size = 3600  # 1 hour window

            # Rate limits per tier (requests per hour)
            limits = {
                "free": self.rate_limit_free,
                "premium": self.rate_limit_premium,
                "enterprise": self.rate_limit_enterprise,
            }
            limit = limits.get(user_tier, 10)

            # Redis key for this user
            redis_key = f"rate_limit:{user_tier}:{user_id}"

            # Remove old entries (older than window_size)
            self._redis_client.zremrangebyscore(redis_key, 0, current_time - window_size)

            # Count current requests
            current_count = self._redis_client.zcard(redis_key)

            # Check if over limit
            if current_count >= limit:
                return True

            # Add current request
            self._redis_client.zadd(redis_key, {str(current_time): current_time})

            # Set expiration on the key
            self._redis_client.expire(redis_key, window_size)

        except Exception as e:
            logger.warning(f"Redis rate limiting failed: {e}, falling back to memory")
            return self._is_rate_limited_memory(user_id, user_tier)

        return False

    def _is_rate_limited_memory(self, user_id: str, user_tier: str) -> bool:
        """
        Fallback in-memory rate limiter when Redis is not available
        """
        try:
            with self._rate_limit_lock:
                current_time = time.time()
                window_size = 3600  # 1 hour window

                # Rate limits per tier (requests per hour)
                limits = {
                    "free": self.rate_limit_free,
                    "premium": self.rate_limit_premium,
                    "enterprise": self.rate_limit_enterprise,
                }
                limit = limits.get(user_tier, 10)

                # Clean old entries
                if user_id in self._rate_limit_store:
                    self._rate_limit_store[user_id] = [
                        timestamp
                        for timestamp in self._rate_limit_store[user_id]
                        if current_time - timestamp < window_size
                    ]
                else:
                    self._rate_limit_store[user_id] = []

                # Check if over limit
                if len(self._rate_limit_store[user_id]) >= limit:
                    return True

                # Add current request
                self._rate_limit_store[user_id].append(current_time)
        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"Memory rate limiting check failed: {e}, defaulting to rate limited")
            return True  # Conservative: treat as rate limited on error

        return False

    async def route_request(
        self,
        prompt: str,
        context: Dict[str, Any],
        user_tier: str = "free",
        user_id: str = "anonymous",
        provider: Optional[str] = None,
        task_type: str = "text",
    ) -> AIResponse:
        """
        Route request to appropriate AI provider
        """
        if provider:
            # Force specific provider
            if provider == "ollama":
                return await self._call_ollama(prompt, context)
            elif provider == "openai":
                return await self._call_openai(prompt, context)
            elif provider == "huggingface":
                return await self._call_huggingface(prompt, context)
            else:
                valid_providers = "'ollama', 'openai', or 'huggingface'"
                return AIResponse(
                    response=f"Invalid provider: {provider}. Use {valid_providers}",
                    provider="unknown",
                    model="error",
                    cost=0.0,
                    tokens_used=0,
                    fallback_used=False,
                    error=True,
                )

        complexity = self.analyze_complexity(prompt, context)
        chosen_provider = self.choose_provider(complexity, user_tier, user_id, task_type)

        logger.info(
            f"Routing request: complexity={complexity.value}, provider={chosen_provider.value}"
        )

        try:
            if chosen_provider == AIProvider.OLLAMA:
                return await self._call_ollama(prompt, context)
            elif chosen_provider == AIProvider.HUGGINGFACE:
                return await self._call_huggingface(prompt, context)
            else:
                return await self._call_openai(prompt, context)
        except (httpx.HTTPError, openai.APIError, Exception) as e:
            logger.exception(f"Error with {chosen_provider.value}, attempting fallback")
            # Fallback to other provider (prioritize Ollama for free users)
            if chosen_provider == AIProvider.HUGGINGFACE:
                fallback_provider = AIProvider.OLLAMA
            elif chosen_provider == AIProvider.OLLAMA:
                fallback_provider = AIProvider.OPENAI
            else:
                fallback_provider = AIProvider.OLLAMA

            logger.info(f"Falling back to {fallback_provider.value}")

            try:
                if fallback_provider == AIProvider.OLLAMA:
                    result = await self._call_ollama(prompt, context)
                    result.fallback_used = True
                    return result
                elif fallback_provider == AIProvider.HUGGINGFACE:
                    result = await self._call_huggingface(prompt, context)
                    result.fallback_used = True
                    return result
                else:
                    result = await self._call_openai(prompt, context)
                    result.fallback_used = True
                    return result
            except Exception as fallback_error:
                logger.exception(f"Fallback to {fallback_provider.value} also failed")
                # Return error structure instead of re-raising
                return AIResponse(
                    response=f"Both AI providers failed. Original error: {e}, Fallback error: {fallback_error}",
                    provider=fallback_provider.value,
                    model="error",
                    cost=0.0,
                    tokens_used=0,
                    fallback_used=True,
                    error=True,
                )

    async def _call_ollama(self, prompt: str, context: Dict[str, Any]) -> AIResponse:
        """
        Call Ollama API
        """

        # Prepare context for Ollama
        system_prompt = self._build_system_prompt(context)
        full_prompt = f"{system_prompt}\n\nUser: {prompt}"

        # Configure timeout for connection and requests
        try:
            timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        except ValueError:
            logger.warning(
                f"Invalid OLLAMA_TIMEOUT value: {os.getenv('OLLAMA_TIMEOUT')}, using default 30"
            )
            timeout_seconds = 30
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.9},
                },
                headers=(
                    {"Authorization": f"Bearer {self.ollama_api_key}"}
                    if self.ollama_api_key
                    else {}
                ),
            )
            response.raise_for_status()
            result = response.json()

            # Validate and normalize response
            if not isinstance(result, dict):
                logger.error(f"Invalid Ollama response format: {type(result)}")
                return AIResponse(
                    response="Error: Invalid response format from Ollama",
                    provider="ollama",
                    model=self.ollama_model,
                    cost=0.0,
                    tokens_used=0,
                    fallback_used=True,
                    error=True,
                )

            # Ensure required fields exist and are correct types
            response_text = result.get("response", "")
            if not isinstance(response_text, str):
                logger.warning(f"Ollama response field is not string: {type(response_text)}")
                response_text = str(response_text) if response_text is not None else ""

            eval_count = result.get("eval_count", 0)
            if not isinstance(eval_count, int):
                try:
                    eval_count = int(eval_count) if eval_count is not None else 0
                except (ValueError, TypeError):
                    logger.warning(f"Invalid eval_count from Ollama: {eval_count}")
                    eval_count = 0

            return AIResponse(
                response=response_text,
                provider="ollama",
                model=self.ollama_model,
                cost=0.0,  # Free
                tokens_used=eval_count,
                fallback_used=False,
                error=False,
            )

    async def _call_openai(self, prompt: str, context: Dict[str, Any]) -> AIResponse:
        """
        Call OpenAI API
        """

        # Configure timeout (configurable via environment)
        try:
            timeout_seconds = int(os.getenv("OPENAI_TIMEOUT", "30"))
        except ValueError:
            logger.warning(
                f"Invalid OPENAI_TIMEOUT value: {os.getenv('OPENAI_TIMEOUT')}, using default 30"
            )
            timeout_seconds = 30
        client = openai.AsyncOpenAI(api_key=self.openai_api_key, timeout=timeout_seconds)

        # Import proper typing for OpenAI messages
        from openai.types.chat import ChatCompletionMessageParam

        # Ensure messages are properly typed
        typed_messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._build_system_prompt(context)},
            {"role": "user", "content": prompt},
        ]

        response = await client.chat.completions.create(
            model=self.openai_model,
            messages=typed_messages,
            temperature=0.7,
            max_tokens=self.max_tokens,
        )

        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        cost = self._calculate_openai_cost(usage) if usage else 0.0

        # Check if choices array is empty
        if not response.choices or len(response.choices) == 0:
            msg = "OpenAI API returned empty choices array"
            raise ValueError(msg)

        # Check if content is None (content filtering)
        content = response.choices[0].message.content
        if content is None:
            msg = "OpenAI API returned None content (likely content filtering)"
            raise ValueError(msg)

        return AIResponse(
            response=content,
            provider="openai",
            model=self.openai_model,
            cost=cost,
            tokens_used=tokens_used,
            fallback_used=False,
            error=False,
        )

    def _load_huggingface_model(self) -> None:
        """Load and cache Hugging Face model and tokenizer"""
        if not TORCH_AVAILABLE:
            raise ImportError("torch and transformers are required for Hugging Face functionality")

        with self._hf_lock:
            # Check if we need to reload the model
            trust_remote = os.getenv("HUGGINGFACE_TRUST_REMOTE_CODE", "false").lower() == "true"
            if (
                self._hf_tokenizer is None
                or self._hf_model is None
                or self._hf_model_name != self.huggingface_model
                or self._hf_revision != self.huggingface_model_revision
                or self._hf_trust_remote != trust_remote
                or self._hf_token != self.huggingface_api_token
            ):
                logger.info(f"Loading Hugging Face model: {self.huggingface_model}")

                # Only enable trust_remote_code for explicitly vetted models
                if trust_remote and self.huggingface_model != "nvidia/llama-embed-nemotron-8b":
                    msg = f"trust_remote_code=True only allowed for vetted models, got: {self.huggingface_model}"
                    raise ValueError(msg)

                # Use specific commit hash for security (required in production)
                if not self.huggingface_model_revision:
                    msg = "HUGGINGFACE_MODEL_REVISION must be set to a specific commit hash for security"
                    raise ValueError(msg)

                self._hf_tokenizer = (
                    AutoTokenizer.from_pretrained(  # nosec B615 - revision pinned for security
                        self.huggingface_model,
                        revision=self.huggingface_model_revision,
                        trust_remote_code=trust_remote,
                        token=self.huggingface_api_token,
                    )
                )
                self._hf_model = (
                    AutoModel.from_pretrained(  # nosec B615 - revision pinned for security
                        self.huggingface_model,
                        revision=self.huggingface_model_revision,
                        trust_remote_code=trust_remote,
                        token=self.huggingface_api_token,
                    )
                )

                # Cache the configuration
                self._hf_model_name = self.huggingface_model
                self._hf_revision = self.huggingface_model_revision
                self._hf_trust_remote = trust_remote
                self._hf_token = self.huggingface_api_token

                logger.info(
                    f"Successfully loaded and cached Hugging Face model: {self.huggingface_model}"
                )

    async def _call_huggingface(self, prompt: str, _context: Dict[str, Any]) -> AIResponse:
        """
        Call Hugging Face API for embeddings

        Args:
            prompt: Text to generate embeddings for
            context: Optional context dictionary (currently unused but reserved for future features)
                   Expected keys in future versions:
                   - user_conditions: List[str] - User health conditions
                   - allergies: List[str] - User allergies
                   - meal_planning: bool - Whether this is for meal planning
                   - diet_goals: List[str] - User diet goals
                   - user_id: str - User identifier for personalization
                   - task_type: str - Type of task (embedding, text, etc.)
                   Can be None or empty dict for current implementation
        """
        if not TORCH_AVAILABLE:
            raise ImportError("torch and transformers are required for Hugging Face functionality")

        try:
            # Load model and tokenizer (cached)
            self._load_huggingface_model()

            # Ensure model and tokenizer are loaded
            if self._hf_tokenizer is None or self._hf_model is None:
                raise RuntimeError("Failed to load Hugging Face model and tokenizer")

            # Tokenize input using cached tokenizer
            inputs = self._hf_tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.huggingface_max_length,
            )

            # Generate embedding using cached model
            with torch.no_grad():
                outputs = self._hf_model(**inputs)
                # Use mean pooling for sentence-level embedding
                embeddings = outputs.last_hidden_state.mean(dim=1)

            # Convert embeddings to list of floats for proper serialization
            embeddings_list = embeddings.tolist()
            # If we have multiple embeddings, return the first one
            if len(embeddings_list) > 1:
                embeddings_list = embeddings_list[0]

            return AIResponse(
                response=embeddings_list,  # Return as native list of floats
                provider="huggingface",
                model=self.huggingface_model,
                cost=0.0,  # Free tier
                tokens_used=inputs.input_ids.shape[1],
                fallback_used=False,
                error=False,
            )

        except Exception:
            logger.exception("Hugging Face API error")
            raise

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build system prompt based on context
        """
        base_prompt = (
            "You are a nutrition and health AI assistant for PulsePlate. "
            "Provide accurate, helpful, and personalized nutrition guidance. "
            "Do not provide medical diagnosis or emergency advice. "
            "Advise users to consult a healthcare professional for medical concerns. "
            "If information is uncertain, state limitations and suggest evidence-based sources."
        )

        if context.get("user_conditions"):
            conditions = context.get("user_conditions", [])
            if conditions and isinstance(conditions, list):
                # Sanitize and validate conditions
                safe_conditions = [str(c).strip() for c in conditions if c]
                if safe_conditions:
                    base_prompt += f"\nUser has conditions: {', '.join(safe_conditions)}"

        if context.get("allergies"):
            allergies = context.get("allergies", [])
            if allergies and isinstance(allergies, list):
                safe_allergies = [str(a).strip() for a in allergies if a]
                if safe_allergies:
                    base_prompt += f"\nUser allergies: {', '.join(safe_allergies)}"

        if context.get("diet_goals"):
            diet_goals = context.get("diet_goals", [])
            if diet_goals and isinstance(diet_goals, list):
                safe_goals = [str(g).strip() for g in diet_goals if g]
                if safe_goals:
                    base_prompt += f"\nUser goals: {', '.join(safe_goals)}"

        return base_prompt

    def _calculate_openai_cost(self, usage: Any) -> float:
        """
        Calculate OpenAI API cost based on usage
        Pricing based on GPT-4o-mini rates as of October 2025
        See: https://openai.com/pricing
        """
        if not usage:
            return 0.0

        # Use centralized pricing constants
        input_cost = (usage.prompt_tokens / 1_000_000) * OPENAI_INPUT_COST_PER_1M
        output_cost = (usage.completion_tokens / 1_000_000) * OPENAI_OUTPUT_COST_PER_1M

        return float(input_cost + output_cost)


# Global router instance
ai_router = AIRouter()
