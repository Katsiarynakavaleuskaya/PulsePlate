from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from providers import ProviderBase


class LLMFlowError(RuntimeError):
    """Raised when the LLMFlow backend reports an error."""


@dataclass(slots=True)
class LLMFlowProvider(ProviderBase):
    """Adapter for the optional LLMFlow service.

    The provider communicates with a running LLMFlow instance via HTTP.
    Configuration is intentionally simple and mirrors the environment
    variables consumed in ``llm.get_provider``.
    """

    endpoint: str
    flow_id: str
    api_key: str | None = None
    timeout: float = 15.0
    input_key: str = "prompt"
    output_key: str | None = "result"

    name: str = "llmflow"

    async def generate(self, text: str) -> str:
        if not self.flow_id:
            raise LLMFlowError("LLMFlow flow_id is required")

        payload = {
            "flow_id": self.flow_id,
            "inputs": {self.input_key: text},
        }
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.endpoint.rstrip('/')}/api/v1/flows/run"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            raise LLMFlowError(f"LLMFlow request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMFlowError(f"LLMFlow error {response.status_code}: {response.text}")

        try:
            data: Any = response.json()
        except ValueError as exc:  # pragma: no cover - invalid backend payload
            raise LLMFlowError("LLMFlow returned invalid JSON") from exc

        if isinstance(data, dict):
            # Honour explicit output key first when provided
            if self.output_key:
                value = data.get(self.output_key)
                if isinstance(value, str):
                    return value.strip()

            # Common fallbacks used by many backends
            for key in ("result", "output", "text", "content"):
                value = data.get(key)
                if isinstance(value, str):
                    return value.strip()

            # Handle OpenAI-like responses
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                choice = choices[0]
                if isinstance(choice, dict):
                    text_value = choice.get("text")
                    if isinstance(text_value, str):
                        return text_value.strip()
                    message = choice.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            return content.strip()

        # As a last resort, return the serialised response
        return str(data)


__all__ = ["LLMFlowProvider", "LLMFlowError"]
