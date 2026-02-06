#!/usr/bin/env python3
"""
MCP Server for PulsePlate Project
Integrates ChatGPT with project-specific context
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

import openai

# Configure logging
logger = logging.getLogger(__name__)

JsonRpcId = int | str | None


class PulsePlateMCPServer:
    """MCP Server for PulsePlate project with ChatGPT integration"""

    # Default OpenAI model for MCP server
    DEFAULT_MODEL: str = "gpt-4o"

    # Backwards-compatible whitelist of allowed models.
    # This is kept for compatibility with existing tests that validate that
    # DEFAULT_MODEL is part of a static whitelist before any dynamic checks.
    # Internally we alias this to FALLBACK_ALLOWED_MODELS so the two stay in sync.
    # Cached available models from OpenAI API (populated on first validation)
    _cached_models: set[str] | None = None
    _model_cache_failed: bool = False

    @classmethod
    def _reset_model_cache(cls) -> None:
        """Reset model cache (primarily for testing)."""
        cls._cached_models = None
        cls._model_cache_failed = False

    # Officially released or generally available OpenAI models as of December 2025.
    # This is a fallback when dynamic discovery via openai.models.list() fails.
    # MAINTENANCE: Keep in sync with https://platform.openai.com/docs/models
    FALLBACK_ALLOWED_MODELS: set[str] = {
        # GPT-3.5 series
        "gpt-3.5-turbo",
        # GPT-4 series (original)
        "gpt-4",
        "gpt-4-turbo",
        # GPT-4o series (optimized - current production)
        "gpt-4o",
        "gpt-4o-mini",
        # Note: GPT-5 models are speculative/placeholder names.
        # As of December 2025, no official GPT-5 models have been released.
        # These entries should be removed or updated when actual models are announced.
        # Realtime and audio models
        "gpt-4o-realtime-preview",
        "gpt-4o-audio-preview",
        # O-series (reasoning models - confirmed releases)
        "o1",
        "o1-mini",
        "o1-preview",
        # O3 series (reasoning, higher capability)
        "o3",
        "o3-mini",
    }

    # Alias static whitelist used by older code/tests to the fallback list.
    ALLOWED_MODELS = FALLBACK_ALLOWED_MODELS

    @classmethod
    def _fetch_available_models(cls) -> set[str]:
        """Fetch available models from OpenAI API with caching and fallback.

        Returns:
            Set of available model IDs from OpenAI API, or fallback set on error.

        Note:
            - Uses class-level cache to avoid repeated API calls
            - Falls back to FALLBACK_ALLOWED_MODELS if API call fails
            - Logs failures for monitoring
        """
        # Return cached result if available
        if cls._cached_models is not None:
            return cls._cached_models

        # Don't retry if we already failed once
        if cls._model_cache_failed:
            logger.warning(
                "Using fallback model list (previous API fetch failed): %s",
                sorted(cls.FALLBACK_ALLOWED_MODELS),
            )
            return cls.FALLBACK_ALLOWED_MODELS

        # Try to fetch from OpenAI API
        try:
            # Use environment API key for discovery
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.info(
                    "OPENAI_API_KEY not set; using fallback model list for validation "
                    "and will retry discovery when a key is provided"
                )
                return cls.FALLBACK_ALLOWED_MODELS

            client = openai.OpenAI(api_key=api_key)
            models_response = client.models.list()

            # Extract model IDs from response
            available_models = {model.id for model in models_response.data}

            # If API returned empty list, use fallback
            if not available_models:
                logger.warning(
                    "OpenAI API returned empty model list; using fallback: %s",
                    sorted(cls.FALLBACK_ALLOWED_MODELS),
                )
                cls._model_cache_failed = True
                return cls.FALLBACK_ALLOWED_MODELS

            # Cache successful result
            cls._cached_models = available_models
            logger.info(
                "Successfully fetched %d models from OpenAI API",
                len(available_models),
            )
            return available_models

        except openai.APIError as e:
            # Catch OpenAI-specific API errors (network, auth, rate limits, etc.)
            # Log failure and fall back to static list
            logger.warning(
                "Failed to fetch models from OpenAI API (will use fallback): %s",
                str(e),
            )
            cls._model_cache_failed = True
            return cls.FALLBACK_ALLOWED_MODELS
        # Allow other unexpected exceptions to propagate (ImportError, AttributeError, etc.)
        # This ensures we don't swallow programming errors or configuration issues

    @classmethod
    def _validate_default_model(cls) -> None:
        """Validate that DEFAULT_MODEL is available.

        Called during class initialization to ensure configuration consistency.
        Uses dynamic model discovery via OpenAI API with fallback.
        """
        # First, ensure configuration is internally consistent: DEFAULT_MODEL
        # must be present in the static whitelist (ALLOWED_MODELS). This is a
        # fast, purely local validation that does not depend on network calls.
        if cls.DEFAULT_MODEL not in cls.ALLOWED_MODELS:
            raise ValueError(
                f"DEFAULT_MODEL {cls.DEFAULT_MODEL!r} must be in ALLOWED_MODELS: "
                f"{sorted(cls.ALLOWED_MODELS)}"
            )

        # Then, verify that the DEFAULT_MODEL is actually available according
        # to the dynamically discovered model list (with a robust fallback).
        allowed_models = cls._fetch_available_models()
        if cls.DEFAULT_MODEL not in allowed_models:
            raise ValueError(
                f"DEFAULT_MODEL {cls.DEFAULT_MODEL!r} is not available. "
                f"Available models: {sorted(allowed_models)}"
            )

    def __init__(self) -> None:
        # Validate default model configuration before checking API key.
        # Note: In misconfigured environments (missing API key), this does extra work
        # since _validate_default_model() calls _fetch_available_models() which attempts
        # API calls. However, the fallback logic ensures this won't crash. For cleaner
        # error messages, we could move this after the API key check, but the current
        # order validates configuration consistency first (fail-fast on config issues).
        self._validate_default_model()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.api_key: str = api_key

        # Configurable model via MCP_OPENAI_MODEL environment variable
        model_env_raw: str | None = os.getenv("MCP_OPENAI_MODEL")
        if model_env_raw is None:
            self.model = self.DEFAULT_MODEL
        else:
            model_env = model_env_raw.strip()
            if not model_env:
                # Empty or whitespace-only value is treated as "use default"
                self.model = self.DEFAULT_MODEL
            else:
                # Validate against dynamically fetched models
                allowed_models = self._fetch_available_models()
                if model_env not in allowed_models:
                    raise ValueError(
                        f"Unknown model: {model_env!r}. "
                        f"Available models: {sorted(allowed_models)}. "
                        f"Note: Model list fetched from OpenAI API or fallback set."
                    )
                self.model = model_env

        self.client: openai.OpenAI = openai.OpenAI(api_key=self.api_key)

        self.project_context = self._load_project_context()

    def _load_project_context(self) -> Dict[str, Any]:
        """Load project context for better ChatGPT responses"""
        return {
            "project_name": "PulsePlate",
            "description": "Health and nutrition tracking app with FastAPI backend and iOS SwiftUI frontend",
            "tech_stack": {
                "backend": "FastAPI, Python, SQLite",
                "frontend": "SwiftUI, iOS, HealthKit, StoreKit",
                "testing": "pytest, 97% coverage",
            },
            "key_features": [
                "BMI calculation and tracking",
                "Nutrition analysis and recommendations",
                "HealthKit integration",
                "Premium subscriptions via StoreKit",
                "Multi-language support (EN/RU/ES)",
            ],
            "architecture": {
                "backend": "FastAPI with 97% test coverage",
                "frontend": "SwiftUI with localization",
                "database": "SQLite with food and recipe data",
                "integrations": "HealthKit, StoreKit, OpenAI API",
            },
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests with ChatGPT integration"""
        try:
            method = request.get("method")
            params = request.get("params", {})

            if method == "initialize":
                # RU: MCP использует JSON-RPC 2.0 и требует handshake initialize.
                # EN: MCP uses JSON-RPC 2.0 and requires an initialize handshake.
                protocol_version = params.get("protocolVersion", "2024-11-05")
                return {
                    "protocolVersion": protocol_version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pulseplate-chatgpt", "version": "0.1.0"},
                }
            if method in {"notifications/initialized", "ping"}:
                return {}
            if method == "resources/list":
                return {"resources": []}
            if method == "prompts/list":
                return {"prompts": []}
            if method == "tools/list":
                return await self._list_tools()
            elif method == "tools/call":
                return await self._call_tool(params)
            else:
                return {"error": f"Unknown method: {method}"}

        except Exception as e:
            return {"error": str(e)}

    async def _list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        return {
            "tools": [
                {
                    "name": "chatgpt_query",
                    "description": "Query ChatGPT with project context",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The question or request for ChatGPT",
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context for the query",
                            },
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "code_review",
                    "description": "Review code with ChatGPT",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Code to review"},
                            "language": {"type": "string", "description": "Programming language"},
                        },
                        "required": ["code"],
                    },
                },
                {
                    "name": "generate_code",
                    "description": "Generate code with ChatGPT",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of code to generate",
                            },
                            "language": {"type": "string", "description": "Programming language"},
                        },
                        "required": ["description"],
                    },
                },
            ]
        }

    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "chatgpt_query":
            return await self._chatgpt_query(arguments)
        elif tool_name == "code_review":
            return await self._code_review(arguments)
        elif tool_name == "generate_code":
            return await self._generate_code(arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def _chatgpt_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Query ChatGPT with project context"""
        query = args.get("query", "")
        context = args.get("context", "")

        # Build prompt with project context
        prompt = f"""
Project Context: {json.dumps(self.project_context, indent=2)}

User Query: {query}
Additional Context: {context}

Please provide a helpful response considering the PulsePlate project context.
"""

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant helping with the PulsePlate health and nutrition tracking app development.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                ),
            )

            return {"content": [{"type": "text", "text": response.choices[0].message.content}]}

        except Exception as e:
            return {"error": f"ChatGPT query failed: {str(e)}"}

    async def _code_review(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Review code with ChatGPT"""
        code = args.get("code", "")
        language = args.get("language", "python")

        prompt = f"""
Review this {language} code for the PulsePlate project:

```{language}
{code}
```

Please provide:
1. Code quality assessment
2. Potential improvements
3. Best practices suggestions
4. Security considerations
"""

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior code reviewer for the PulsePlate project.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1500,
                    temperature=0.3,
                ),
            )

            return {"content": [{"type": "text", "text": response.choices[0].message.content}]}

        except Exception as e:
            return {"error": f"Code review failed: {str(e)}"}

    async def _generate_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code with ChatGPT"""
        description = args.get("description", "")
        language = args.get("language", "python")

        prompt = f"""
Generate {language} code for the PulsePlate project based on this description:
{description}

Requirements:
- Follow project coding standards
- Include proper error handling
- Add type hints where appropriate
- Include docstrings
- Consider the FastAPI backend and SwiftUI frontend architecture
"""

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior developer for the PulsePlate project.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2000,
                    temperature=0.5,
                ),
            )

            return {"content": [{"type": "text", "text": response.choices[0].message.content}]}

        except Exception as e:
            return {"error": f"Code generation failed: {str(e)}"}


async def main() -> None:
    """Main function for MCP server"""
    server = PulsePlateMCPServer()

    # Read from stdin and write to stdout
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())

            # RU: MCP ожидает JSON-RPC 2.0 envelope в ответах.
            # EN: MCP expects JSON-RPC 2.0 envelopes in responses.
            if (
                isinstance(request, dict)
                and request.get("jsonrpc") == "2.0"
                and isinstance(request.get("method"), str)
            ):
                has_id = "id" in request
                request_id: JsonRpcId = request.get("id")
                # Notifications (no id) must not produce a response.
                if not has_id:
                    await server.handle_request(request)
                    continue

                result = await server.handle_request(request)
                if isinstance(result, dict) and set(result.keys()) == {"error"}:
                    message = str(result["error"])
                    code = -32601 if message.startswith("Unknown method:") else -32000
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": code, "message": message},
                    }
                else:
                    response = {"jsonrpc": "2.0", "id": request_id, "result": result}

                print(json.dumps(response))
                sys.stdout.flush()
                continue

            response = await server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()

        except Exception as e:
            # RU: Даже ошибки должны быть валидным JSON, иначе клиент MCP "ломается".
            # EN: Even errors must be valid JSON, otherwise MCP clients fail to parse.
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": {"error": str(e)},
                },
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
