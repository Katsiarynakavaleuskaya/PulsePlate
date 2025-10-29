from typing import Optional
import asyncio

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class GrokProvider:
    """
    Минималистичный провайдер к x.ai (Grok) через совместимый OpenAI SDK.
    Совместим с вызовом из llm.py:
        GrokProvider(endpoint=..., model=..., api_key=...)
    """

    name = "grok"

    def __init__(self, endpoint: str, model: str, api_key: str, timeout: Optional[float] = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        # Создаём синхронного клиента (OpenAI-совместимый эндпоинт у x.ai)
        self.client = OpenAI(base_url=self.endpoint, api_key=self.api_key)
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate(self, text: str) -> str:
        """
        Generate text using Grok API.

        Args:
            text: Input text to process

        Returns:
            Generated text response

        Raises:
            RuntimeError: If API call fails or returns invalid response
        """
        try:
            # Run the synchronous client call in a thread pool to maintain async interface
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._call_sync_client, text)

            # Extract content from response
            if not hasattr(response, "choices") or not response.choices:
                raise RuntimeError("Invalid response: no choices found")

            choice = response.choices[0]
            if not hasattr(choice, "message") or not hasattr(choice.message, "content"):
                raise RuntimeError("Invalid response: no message content found")

            content = choice.message.content
            if not isinstance(content, str):
                raise RuntimeError(
                    f"Invalid response: expected string content, got {type(content)}"
                )

            return content.strip()

        except Exception as e:
            # Пробрасываем понятную ошибку наверх
            raise RuntimeError(f"Grok error: {type(e).__name__}: {e}")

    def _call_sync_client(self, text: str):
        """Synchronous client call for use with run_in_executor."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": text}],
            timeout=self.timeout,
        )
