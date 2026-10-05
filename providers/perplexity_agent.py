"""Bounded Perplexity Agent API text adapter for development-only FitChef work."""

from __future__ import annotations

from contextvars import ContextVar
import logging
from typing import Any, Literal, cast

import httpx
from openai import APITimeoutError, AsyncOpenAI, DefaultAsyncHttpxClient
from openai._models import FinalRequestOptions

AGENT_API_BASE_URL = "https://api.perplexity.ai/v1"
AGENT_API_MODELS = frozenset({"openai/gpt-6-luna", "openai/gpt-6-sol", "openai/gpt-6.1-sol"})
AGENT_API_REASONING_EFFORTS = frozenset({"none", "low"})
AGENT_API_MAX_PROMPT_BYTES = 32_768
AGENT_API_MAX_OUTPUT_TOKENS = 2_048
AGENT_API_MAX_OUTPUT_BYTES = 32_768
AGENT_API_TIMEOUT_SECONDS = 45.0

_PLACEHOLDER_KEYS = frozenset(
    {"__replace_me__", "paste_your_real_key_here", "changeme", "your_api_key_here"}
)
_AGENT_REQUEST_ACTIVE: ContextVar[bool] = ContextVar(
    "fitchef_agent_api_request_active", default=False
)


class _AgentSDKLogFilter(logging.Filter):
    """Suppress all exact-SDK-logger records in active or inherited Agent contexts."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not _AGENT_REQUEST_ACTIVE.get()


_SDK_LOG_FILTER = _AgentSDKLogFilter()
# The installed Responses SDK logs raw input at DEBUG before our exception
# sanitizer runs. Suppress every record on these two loggers in the entire
# active/inherited Agent context. Independent contexts outside Agent retain
# their diagnostics; nested SDK calls do not gain a confidentiality exception.
for _sdk_logger_name in ("openai._base_client", "openai._response"):
    logging.getLogger(_sdk_logger_name).addFilter(_SDK_LOG_FILTER)


class _AgentAsyncOpenAI(AsyncOpenAI):
    """Bind redirects and the two OpenAI identity headers to each request."""

    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        prepared = await super()._prepare_options(options)
        return prepared.model_copy(update={"follow_redirects": False})

    async def _prepare_request(self, request: httpx.Request) -> None:
        await super()._prepare_request(request)
        # HTTPX merges borrowed defaults after SDK header construction. Remove
        # only these names from the individual request, preserving the client.
        request.headers.pop("OpenAI-Organization", None)
        request.headers.pop("OpenAI-Project", None)


def _item_field(item: object, name: str) -> Any:
    """Read one SDK or raw-dict output field without serializing provider payloads."""

    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


class PerplexityAgentProvider:
    """Return one completed assistant text from a tool-free Agent API request."""

    name = "perplexity_agent"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_key = api_key.strip()
        if (
            not normalized_key
            or normalized_key.lower() in _PLACEHOLDER_KEYS
            or any(not 33 <= ord(character) <= 126 for character in normalized_key)
        ):
            raise ValueError("FitChef Agent API key is not configured")
        if model not in AGENT_API_MODELS:
            raise ValueError("FitChef Agent API model is not approved")
        if reasoning_effort not in AGENT_API_REASONING_EFFORTS:
            raise ValueError("FitChef Agent API reasoning effort is not approved")
        self._require_safe_http_client(http_client)

        self.model = model
        self.reasoning_effort = cast(Literal["none", "low"], reasoning_effort)
        # Delay client allocation until the runtime has admitted quota. A quota
        # denial must not leave an unused connection pool behind.
        self._api_key = normalized_key
        self._http_client = http_client

    @staticmethod
    def _require_safe_http_client(client: httpx.AsyncClient | None) -> None:
        if client is not None and (client.follow_redirects is not False or client.is_closed):
            raise ValueError("FitChef Agent API HTTP client is not configured safely")

    @staticmethod
    def require_prompt_in_budget(prompt: str) -> None:
        """Reject oversized text before quota debit or a provider request."""

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("FitChef Agent API prompt is empty")
        if len(prompt.encode("utf-8")) > AGENT_API_MAX_PROMPT_BYTES:
            raise ValueError("FitChef Agent API prompt exceeds the byte budget")

    async def generate(self, text: str) -> str:
        self.require_prompt_in_budget(text)
        log_context = _AGENT_REQUEST_ACTIVE.set(True)
        try:
            self._require_safe_http_client(self._http_client)
            owned_http_client: httpx.AsyncClient | None = None
            try:
                http_client = self._http_client
                if http_client is None:
                    owned_http_client = DefaultAsyncHttpxClient(
                        follow_redirects=False, timeout=AGENT_API_TIMEOUT_SECONDS
                    )
                    http_client = owned_http_client
                # Empty native identity state disables unrelated SDK env defaults.
                sdk_identity_default = ""
                client = _AgentAsyncOpenAI(
                    api_key=self._api_key,
                    base_url=AGENT_API_BASE_URL,
                    organization=sdk_identity_default,
                    project=sdk_identity_default,
                    webhook_secret=sdk_identity_default,
                    max_retries=0,
                    timeout=AGENT_API_TIMEOUT_SECONDS,
                    http_client=http_client,
                )
                response = await client.responses.create(
                    model=self.model,
                    input=text,
                    reasoning={"effort": self.reasoning_effort},
                    max_output_tokens=AGENT_API_MAX_OUTPUT_TOKENS,
                    tools=[],
                    store=False,
                )
            finally:
                if owned_http_client is not None:
                    await owned_http_client.aclose()
            if (
                response.status != "completed"
                or response.error is not None
                or response.model != self.model
                or response.incomplete_details is not None
            ):
                raise RuntimeError("FitChef Agent API response is not completed")

            output = response.output
            if not isinstance(output, list) or not output:
                raise RuntimeError("FitChef Agent API response has no assistant message")
            assistant_messages = 0
            text_parts: list[str] = []
            for item in output:
                item_type = _item_field(item, "type")
                if item_type == "reasoning":
                    continue
                if item_type != "message" or _item_field(item, "role") != "assistant":
                    raise RuntimeError("FitChef Agent API returned an unexpected output item")
                if _item_field(item, "status") != "completed":
                    raise RuntimeError("FitChef Agent API assistant message is not completed")
                if _item_field(item, "phase") not in (None, "final"):
                    raise RuntimeError("FitChef Agent API assistant message is not final")
                content = _item_field(item, "content")
                if not isinstance(content, list) or not content:
                    raise RuntimeError("FitChef Agent API response has no assistant text")
                for part in content:
                    part_text = _item_field(part, "text")
                    if _item_field(part, "type") != "output_text" or not isinstance(part_text, str):
                        raise RuntimeError(
                            "FitChef Agent API returned unexpected assistant content"
                        )
                    text_parts.append(part_text)
                assistant_messages += 1
            if assistant_messages != 1:
                raise RuntimeError(
                    "FitChef Agent API response requires one final assistant message"
                )

            final_text = "".join(text_parts).strip()
            if not final_text:
                raise RuntimeError("FitChef Agent API response has no assistant text")
            if len(final_text.encode("utf-8")) > AGENT_API_MAX_OUTPUT_BYTES:
                raise RuntimeError("FitChef Agent API response exceeds the byte budget")
            return final_text
        except (APITimeoutError, TimeoutError):
            raise TimeoutError("FitChef Agent API timed out") from None
        except Exception:
            # The runtime logs this exception with exc_info=True. Do not attach
            # SDK errors, response bodies, credentials, or prompt text as context.
            raise RuntimeError("FitChef Agent API unavailable") from None
        finally:
            _AGENT_REQUEST_ACTIVE.reset(log_context)
