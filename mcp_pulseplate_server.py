#!/usr/bin/env python3
"""
MCP Server for PulsePlate Project
Integrates ChatGPT with project-specific context
Fixed: Added memory limits and resource management
"""

import asyncio
import json
import os
import sys
import resource
import signal
from typing import Any, Dict

import openai

# Set memory limit to prevent excessive RAM usage (default: 512 MB)
MAX_MEMORY_MB = int(os.getenv("MCP_MAX_MEMORY_MB", "512"))
try:
    # Set soft and hard limits for memory usage
    resource.setrlimit(
        resource.RLIMIT_AS,
        (MAX_MEMORY_MB * 1024 * 1024, MAX_MEMORY_MB * 1024 * 1024)
    )
except (ValueError, OSError) as e:
    # Log warning but continue - some systems don't support memory limits
    print(f"Warning: Could not set memory limit: {e}", file=sys.stderr)

# Flag for graceful shutdown
_shutdown_flag = False


def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    global _shutdown_flag
    _shutdown_flag = True
    print("\nReceived shutdown signal, cleaning up...", file=sys.stderr)


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


class PulsePlateMCPServer:
    """MCP Server for PulsePlate project with ChatGPT integration"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = openai.OpenAI(api_key=self.api_key)
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

        # Build minimal prompt to reduce memory usage
        prompt = f"""User Query: {query}
Context: {context}

Project: PulsePlate (FastAPI backend, SwiftUI iOS frontend, 97% test coverage)
"""

        try:
            # Use timeout to prevent hanging
            timeout = int(os.getenv("MCP_TIMEOUT_SECONDS", "30"))
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant for PulsePlate health app. Be concise.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=500,  # Reduced from 1000 to save memory
                    temperature=0.7,
                ),
                timeout=timeout
            )

            return {"content": [{"type": "text", "text": response.choices[0].message.content}]}

        except asyncio.TimeoutError:
            return {"error": "ChatGPT query timed out"}
        except Exception as e:
            return {"error": f"ChatGPT query failed: {str(e)}"}

    async def _code_review(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Review code with ChatGPT"""
        code = args.get("code", "")
        language = args.get("language", "python")
        
        # Limit code size to prevent memory issues
        max_code_length = 2000
        if len(code) > max_code_length:
            return {"error": f"Code too large (max {max_code_length} chars)"}

        prompt = f"""Review this {language} code (PulsePlate project):

```{language}
{code}
```

Focus on: quality, improvements, best practices, security."""

        try:
            timeout = int(os.getenv("MCP_TIMEOUT_SECONDS", "30"))
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a code reviewer for PulsePlate. Be concise.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=800,  # Reduced from 1500
                    temperature=0.3,
                ),
                timeout=timeout
            )

            return {"content": [{"type": "text", "text": response.choices[0].message.content}]}

        except asyncio.TimeoutError:
            return {"error": "Code review timed out"}
        except Exception as e:
            return {"error": f"Code review failed: {str(e)}"}

    async def _generate_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code with ChatGPT"""
        description = args.get("description", "")
        language = args.get("language", "python")

        prompt = f"""Generate {language} code for PulsePlate:
{description}

Requirements: Follow standards, error handling, type hints, docstrings."""

        try:
            timeout = int(os.getenv("MCP_TIMEOUT_SECONDS", "30"))
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a developer for PulsePlate. Be concise.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,  # Reduced from 2000
                    temperature=0.5,
                ),
                timeout=timeout
            )

            return {"content": [{"type": "text", "text": response.choices[0].message.content}]}

        except asyncio.TimeoutError:
            return {"error": "Code generation timed out"}
        except Exception as e:
            return {"error": f"Code generation failed: {str(e)}"}


async def main() -> None:
    """Main function for MCP server"""
    server = PulsePlateMCPServer()

    # Read from stdin and write to stdout
    while not _shutdown_flag:
        try:
            # Use select-like behavior to check for input with timeout
            line = await asyncio.wait_for(
                asyncio.to_thread(sys.stdin.readline),
                timeout=1.0
            )
            
            if not line or _shutdown_flag:
                break

            request = json.loads(line.strip())
            response = await server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()

        except asyncio.TimeoutError:
            # Timeout is normal, just check shutdown flag and continue
            continue
        except json.JSONDecodeError as e:
            error_response = {"error": f"Invalid JSON: {str(e)}"}
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response))
            sys.stdout.flush()
    
    print("MCP server shutdown complete", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
