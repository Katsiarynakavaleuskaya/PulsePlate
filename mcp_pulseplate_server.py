#!/usr/bin/env python3
"""
MCP Server for PulsePlate Project
Integrates ChatGPT with project-specific context
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

import openai


class PulsePlateMCPServer:
    """MCP Server for PulsePlate project with ChatGPT integration"""

    # Default OpenAI model for MCP server
    DEFAULT_MODEL: str = "gpt-4o"

    # Allowed OpenAI model names (fail-fast validation)
    # Keep in sync with models supported by the pinned openai client.
    ALLOWED_MODELS: set[str] = {
        "gpt-4o",
        "gpt-4o-mini",
        "o1",
        "o3",
        "o3-mini",
    }
    # Ensure DEFAULT_MODEL remains whitelisted (bandit-safe, no assert)
    if DEFAULT_MODEL not in ALLOWED_MODELS:
        raise ValueError(
            f"DEFAULT_MODEL {DEFAULT_MODEL!r} must be in ALLOWED_MODELS. "
            f"Current ALLOWED_MODELS: {sorted(ALLOWED_MODELS)}"
        )

    def __init__(self) -> None:
        self.api_key: str | None = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Configurable model via MCP_OPENAI_MODEL environment variable
        # Falls back to DEFAULT_MODEL if not set or empty after stripping
        model_env_raw: str | None = os.getenv("MCP_OPENAI_MODEL")
        if model_env_raw is None:
            self.model = self.DEFAULT_MODEL
        elif model_env_raw == "":
            # Explicit empty string falls back to default
            self.model = self.DEFAULT_MODEL
        else:
            model_env = model_env_raw.strip()
            if not model_env:
                raise ValueError(
                    f"Invalid model name: {model_env_raw!r}. "
                    f"Expected one of: {sorted(self.ALLOWED_MODELS)}"
                )
            self.model = model_env

        # Whitelist validation: ensure model is a known OpenAI model
        if self.model not in self.ALLOWED_MODELS:
            raise ValueError(
                f"Unknown model: {self.model!r}. "
                f"Allowed models: {sorted(self.ALLOWED_MODELS)}. "
                f"Update ALLOWED_MODELS if using a newer model."
            )

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
            response = self.client.chat.completions.create(
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
            response = self.client.chat.completions.create(
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
            response = self.client.chat.completions.create(
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
            response = await server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()

        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
