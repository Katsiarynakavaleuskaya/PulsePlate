"""Mock-transport contract tests for the bounded FitChef Agent API adapter."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from copy import deepcopy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from openai._models import FinalRequestOptions
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_VIP
from providers.perplexity_agent import (
    AGENT_API_MAX_OUTPUT_TOKENS,
    AGENT_API_MAX_OUTPUT_BYTES,
    AGENT_API_MAX_PROMPT_BYTES,
    PerplexityAgentProvider,
    _AgentAsyncOpenAI,
)

MODEL = "openai/gpt-6-luna"
PROMPT = "Give one bounded FitChef planning reflection."
_APPROVED_MODELS = [MODEL, "openai/gpt-6-sol", "openai/gpt-6.1-sol"]
_SDK_ENV_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_ORG_ID",
    "OPENAI_PROJECT_ID",
    "OPENAI_WEBHOOK_SECRET",
    "PERPLEXITY_API_KEY",
    "OPENAI_LOG",
)
_NEAR_MODEL_IDS = [
    "gpt-6.1",
    "openai/gpt-6.1",
    "openai/gpt-6.10-sol",
    "openai/gpt-6.1-preview",
    "openai/gpt-6.1-luna",
    "OPENAI/gpt-6.1-sol",
    "openai/GPT-6.1-sol",
    " openai/gpt-6.1-sol",
    "openai/gpt-6.1-sol ",
    "openai/gpt-6.1-sol-extra",
]


def _clear_sdk_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every credential assertion independent of host credential sources."""
    for name in _SDK_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def isolated_sdk_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every SDK credential and identity source before each synthetic test."""

    _clear_sdk_environment(monkeypatch)


def _response_body(
    *,
    status: str = "completed",
    model: str = MODEL,
    text: str = "Choose one balanced next meal.",
    output: list[dict[str, object]] | None = None,
    error: object = None,
) -> dict[str, object]:
    """Build a synthetic completed Responses payload with selectable status and text."""

    if output is None:
        output = [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ]
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1,
        "status": status,
        "model": model,
        "output": output,
        "error": error,
    }


async def _generate_with_transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    prompt: str = PROMPT,
    model: str = MODEL,
    effort: str = "low",
) -> str:
    """Exercise generation through an injected mock transport and borrowed client."""

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        provider = PerplexityAgentProvider(
            api_key=TEST_KEY_VIP,
            model=model,
            reasoning_effort=effort,
            http_client=http_client,
        )
        return await provider.generate(prompt)


@pytest.mark.parametrize("model", _APPROVED_MODELS)
@pytest.mark.parametrize("effort", ["none", "low"])
def test_exact_tool_free_request_and_single_attempt(model: str, effort: str) -> None:
    """Assert the fixed tool-free request contract and exactly one physical send."""

    requests: list[dict[str, object]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        """Capture the request body and return one synthetic completed response."""

        assert str(request.url) == "https://api.perplexity.ai/v1/responses"
        assert request.method == "POST"
        assert request.headers["authorization"] == f"Bearer {TEST_KEY_VIP}"
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=_response_body(model=model))

    assert (
        asyncio.run(_generate_with_transport(_handler, model=model, effort=effort))
        == "Choose one balanced next meal."
    )
    assert requests == [
        {
            "model": model,
            "input": PROMPT,
            "reasoning": {"effort": effort},
            "max_output_tokens": AGENT_API_MAX_OUTPUT_TOKENS,
            "tools": [],
            "store": False,
        }
    ]


@pytest.mark.parametrize("status", ["failed", "incomplete", "cancelled", "queued"])
def test_http_200_noncompleted_status_fails_closed(status: str) -> None:
    """Reject noncompleted Responses statuses even when the HTTP status is 200."""

    calls = 0

    def _handler(_request: httpx.Request) -> httpx.Response:
        """Return the selected noncompleted status and count the physical send."""

        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_response_body(status=status))

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
        asyncio.run(_generate_with_transport(_handler))
    assert calls == 1


@pytest.mark.parametrize(
    "body",
    [
        _response_body(model="openai/gpt-6-sol"),
        _response_body(text="  "),
        _response_body(output=[]),
        _response_body(
            output=[
                {
                    "id": "msg_empty",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [],
                }
            ]
        ),
        _response_body(error={"message": "hidden-provider-detail"}),
        _response_body(
            output=[
                {"type": "search_results", "results": [{"url": "https://example.org"}]},
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": "A tool was used", "annotations": []}
                    ],
                },
            ]
        ),
    ],
)
def test_malformed_or_unexpected_result_fails_closed(body: dict[str, object]) -> None:
    """Reject malformed or unexpected Responses payloads through the native SDK seam."""

    def _handler(_request: httpx.Request) -> httpx.Response:
        """Return the selected malformed synthetic response body."""

        return httpx.Response(200, json=body)

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
        asyncio.run(_generate_with_transport(_handler))


def test_sdk_error_is_sanitized_without_retry_or_secret_traceback() -> None:
    """Sanitize SDK failures without retries or secret-bearing tracebacks."""

    calls = 0

    def _handler(_request: httpx.Request) -> httpx.Response:
        """Count the send and return a synthetic server error containing private details."""

        nonlocal calls
        calls += 1
        return httpx.Response(
            500,
            json={"error": {"message": "secret prompt and credential", "type": "server_error"}},
        )

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable") as caught:
        asyncio.run(_generate_with_transport(_handler))
    assert calls == 1
    formatted = "".join(traceback.format_exception(caught.value))
    assert "secret prompt and credential" not in formatted


@pytest.mark.parametrize(
    ("key", "model", "effort"),
    [
        ("", MODEL, "low"),
        ("__replace_me__", MODEL, "low"),
        ("synthetic-test-key", "anthropic/claude-opus-5", "low"),
        ("synthetic-test-key", MODEL, "high"),
    ],
)
def test_invalid_configuration_fails_before_client(key: str, model: str, effort: str) -> None:
    """Reject invalid explicit configuration before any SDK client can be allocated."""

    with pytest.raises(ValueError):
        PerplexityAgentProvider(api_key=key, model=model, reasoning_effort=effort)


def test_prompt_byte_budget_is_preflighted() -> None:
    """Enforce the UTF-8 prompt limit before quota or provider execution."""

    with pytest.raises(ValueError, match="byte budget"):
        PerplexityAgentProvider.require_prompt_in_budget(
            "é" * (AGENT_API_MAX_PROMPT_BYTES // 2 + 1)
        )


@pytest.mark.parametrize(
    "output",
    [
        [{"type": "reasoning", "id": "reason_1", "summary": []}],
        [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "status": "incomplete",
                "content": [{"type": "output_text", "text": "partial", "annotations": []}],
            }
        ],
        [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "refusal", "refusal": "refused"}],
            }
        ],
        [
            {
                "type": "message",
                "id": "msg_1",
                "role": "user",
                "status": "completed",
                "content": [{"type": "output_text", "text": "user text", "annotations": []}],
            }
        ],
        [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "status": "completed",
                "phase": "analysis",
                "content": [{"type": "output_text", "text": "analysis text", "annotations": []}],
            }
        ],
    ],
)
def test_only_completed_final_assistant_text_is_admitted(output: list[dict[str, object]]) -> None:
    """Accept only one completed final assistant text message."""

    def _handler(_request: httpx.Request) -> httpx.Response:
        """Return the selected assistant message shape for admission checks."""

        return httpx.Response(200, json=_response_body(output=output))

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
        asyncio.run(_generate_with_transport(_handler))


def test_reasoning_then_one_final_message_is_admitted() -> None:
    """Allow reasoning output followed by one completed final assistant message."""

    body = _response_body()
    output = body["output"]
    assert isinstance(output, list)
    output.insert(0, {"type": "reasoning", "id": "reason_1", "summary": []})

    def _handler(_request: httpx.Request) -> httpx.Response:
        """Return reasoning and final text in the same synthetic response."""

        return httpx.Response(200, json=body)

    assert asyncio.run(_generate_with_transport(_handler)) == "Choose one balanced next meal."


@pytest.mark.parametrize("mode", ["too_large", "incomplete_details", "multiple", "malformed_json"])
def test_other_invalid_response_bodies_are_rejected(mode: str) -> None:
    """Reject invalid JSON, empty text, oversized text, and response-level errors."""

    body = _response_body()
    if mode == "too_large":
        body = _response_body(text="é" * (AGENT_API_MAX_OUTPUT_BYTES // 2 + 1))
    elif mode == "incomplete_details":
        body["incomplete_details"] = {"reason": "max_output_tokens"}
    elif mode == "multiple":
        output = body["output"]
        assert isinstance(output, list)
        output.append(output[0])

    def _handler(_request: httpx.Request) -> httpx.Response:
        """Return the selected invalid body or response-level error fixture."""

        if mode == "malformed_json":
            return httpx.Response(200, content=b"not-json secret-provider-body")
        return httpx.Response(200, json=body)

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable") as caught:
        asyncio.run(_generate_with_transport(_handler))
    assert "secret-provider-body" not in "".join(traceback.format_exception(caught.value))


def test_timeout_is_sanitized_and_not_retried() -> None:
    """Sanitize a transport timeout and preserve the single-send boundary."""

    calls = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        """Count the send and raise a synthetic timeout containing private details."""

        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("secret prompt and credential", request=request)

    with pytest.raises(TimeoutError, match="FitChef Agent API timed out") as caught:
        asyncio.run(_generate_with_transport(_handler))
    assert calls == 1
    assert "secret prompt and credential" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("status", [307, 308])
@pytest.mark.parametrize("cross_origin", [False, True])
@pytest.mark.parametrize("owned", [False, True])
def test_redirect_is_rejected_after_one_physical_send(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status: int,
    cross_origin: bool,
    owned: bool,
) -> None:
    """Reject same-origin and cross-origin redirects after one physical send."""

    calls: list[httpx.Request] = []
    created: list[httpx.AsyncClient] = []
    caplog.set_level(logging.DEBUG, logger="openai._base_client")
    caplog.set_level(logging.DEBUG, logger="openai._response")
    location = (
        "https://example.invalid/private-redirect"
        if cross_origin
        else "https://api.perplexity.ai/v1/responses?private-redirect=1"
    )

    def _handler(request: httpx.Request) -> httpx.Response:
        """Record the request and return the selected redirect target and status."""

        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                status,
                headers={"location": location},
                json={"error": {"message": "secret-redirect-body"}},
            )
        return httpx.Response(200, json=_response_body())

    def _owned_client(**kwargs: Any) -> httpx.AsyncClient:
        """Allocate and track the owned mock client for redirect cleanup assertions."""

        assert kwargs["follow_redirects"] is False
        client = DefaultAsyncHttpxClient(**kwargs, transport=httpx.MockTransport(_handler))
        created.append(client)
        return client

    monkeypatch.setattr("providers.perplexity_agent.DefaultAsyncHttpxClient", _owned_client)

    async def _run() -> None:
        """Exercise owned or borrowed redirect rejection and verify client ownership."""

        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as borrowed:
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP,
                model=MODEL,
                reasoning_effort="low",
                http_client=None if owned else borrowed,
            )
            with pytest.raises(RuntimeError, match="FitChef Agent API unavailable") as caught:
                await provider.generate(PROMPT)
            assert "secret-redirect-body" not in "".join(traceback.format_exception(caught.value))
            assert not borrowed.is_closed and borrowed.follow_redirects is False
        assert len(created) == (1 if owned else 0)
        if owned:
            assert created[0].is_closed

    asyncio.run(_run())
    assert len(calls) == 1
    assert str(calls[0].url) == "https://api.perplexity.ai/v1/responses"
    assert calls[0].method == "POST"
    assert calls[0].headers["authorization"] == f"Bearer {TEST_KEY_VIP}"
    assert json.loads(calls[0].content)["input"] == PROMPT
    assert location not in caplog.text and "secret-redirect-body" not in caplog.text
    assert TEST_KEY_VIP not in caplog.text and PROMPT not in caplog.text


@pytest.mark.parametrize(
    "stage",
    ["constructor_true", "before_generate_true", "constructor_closed", "before_generate_closed"],
)
def test_unsafe_borrowed_client_rejected_without_send_allocation_or_owner_effects(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Reject unsafe borrowed clients without sends, allocation, or owner-state changes."""

    monkeypatch.setattr(
        "providers.perplexity_agent.DefaultAsyncHttpxClient",
        lambda **kwargs: pytest.fail("unsafe borrowed client must not allocate owned HTTPX"),
    )
    monkeypatch.setattr(
        "providers.perplexity_agent._AgentAsyncOpenAI",
        lambda **kwargs: pytest.fail("unsafe borrowed client must not allocate SDK"),
    )

    async def _run() -> None:
        """Exercise unsafe-client rejection while preserving borrowed client state."""

        borrowed = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: pytest.fail("unsafe client must not send")
            ),
            follow_redirects=stage == "constructor_true",
        )
        try:
            if stage == "constructor_closed":
                await borrowed.aclose()
            if stage.startswith("constructor"):
                with pytest.raises(ValueError, match="not configured safely"):
                    PerplexityAgentProvider(
                        api_key=TEST_KEY_VIP,
                        model=MODEL,
                        reasoning_effort="low",
                        http_client=borrowed,
                    )
            else:
                provider = PerplexityAgentProvider(
                    api_key=TEST_KEY_VIP, model=MODEL, reasoning_effort="low", http_client=borrowed
                )
                if stage == "before_generate_true":
                    borrowed.follow_redirects = True
                else:
                    await borrowed.aclose()
                with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
                    await provider.generate(PROMPT)
            assert borrowed.follow_redirects == stage.endswith("true")
            assert borrowed.is_closed == stage.endswith("closed")
        finally:
            await borrowed.aclose()

    asyncio.run(_run())


@pytest.mark.parametrize("status", [307, 308])
@pytest.mark.parametrize("cross_origin", [False, True])
def test_request_bound_redirect_option_survives_late_borrowed_flag_mutation(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    cross_origin: bool,
) -> None:
    """Keep redirects disabled after a borrowed client flag changes during preparation."""

    calls: list[httpx.Request] = []

    async def _run() -> None:
        """Mutate the borrowed flag after option preparation and assert one redirect response."""

        def _handler(request: httpx.Request) -> httpx.Response:
            """Capture the admitted request before returning the redirect fixture."""

            calls.append(request)
            return httpx.Response(
                status,
                headers={
                    "location": (
                        "https://example.invalid/redirect" if cross_origin else "/v1/redirect"
                    )
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as borrowed:

            async def _mutate_after_options(
                self: _AgentAsyncOpenAI, request: httpx.Request
            ) -> None:
                """Change the borrowed redirect flag after native request options are copied."""

                borrowed.follow_redirects = True

            monkeypatch.setattr(_AgentAsyncOpenAI, "_prepare_request", _mutate_after_options)
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP, model=MODEL, reasoning_effort="low", http_client=borrowed
            )
            with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
                await provider.generate(PROMPT)
            assert borrowed.follow_redirects is True and not borrowed.is_closed

    asyncio.run(_run())
    assert len(calls) == 1 and calls[0].url.host == "api.perplexity.ai"


def test_native_sdk_redirect_hook_copies_options_and_borrowed_success_stays_open() -> None:
    """Preserve original native options and keep a successful borrowed client open."""

    async def _run() -> None:
        """Assert copied redirect options and successful generation through the borrowed client."""

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=_response_body())
            )
        ) as borrowed:
            sdk = _AgentAsyncOpenAI(api_key=TEST_KEY_VIP, http_client=borrowed)
            options = FinalRequestOptions.construct(
                method="post", url="/responses", follow_redirects=True
            )
            prepared = await sdk._prepare_options(options)
            assert prepared is not options and prepared.follow_redirects is False
            assert options.follow_redirects is True
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP, model=MODEL, reasoning_effort="low", http_client=borrowed
            )
            assert await provider.generate(PROMPT) == "Choose one balanced next meal."
            assert not borrowed.is_closed and borrowed.follow_redirects is False

    asyncio.run(_run())


@pytest.mark.parametrize("outcome", ["success", "sdk_allocation_error", "cancelled"])
@pytest.mark.parametrize("owned", [False, True])
def test_client_ownership_includes_allocation_error_and_cancellation(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    owned: bool,
) -> None:
    """Close owned resources on success, SDK allocation error, and cancellation."""

    created: list[httpx.AsyncClient] = []

    async def _run() -> None:
        """Exercise the selected outcome and verify owned versus borrowed cleanup."""

        entered = asyncio.Event()
        release = asyncio.Event()

        async def _handler(request: httpx.Request) -> httpx.Response:
            """Signal transport entry and wait when the selected outcome is cancellation."""

            entered.set()
            if outcome == "cancelled":
                await release.wait()
            return httpx.Response(200, json=_response_body())

        def _factory(**kwargs: Any) -> httpx.AsyncClient:
            """Allocate and track the owned mock client used by the cleanup scenario."""

            client = DefaultAsyncHttpxClient(**kwargs, transport=httpx.MockTransport(_handler))
            created.append(client)
            return client

        monkeypatch.setattr("providers.perplexity_agent.DefaultAsyncHttpxClient", _factory)
        if outcome == "sdk_allocation_error":

            def _fail_sdk(**kwargs: Any) -> _AgentAsyncOpenAI:
                """Raise an SDK allocation failure containing synthetic private details."""

                raise RuntimeError("secret SDK allocation details")

            monkeypatch.setattr("providers.perplexity_agent._AgentAsyncOpenAI", _fail_sdk)
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as borrowed:
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP,
                model=MODEL,
                reasoning_effort="low",
                http_client=None if owned else borrowed,
            )
            if outcome == "cancelled":
                task = asyncio.create_task(provider.generate(PROMPT))
                await asyncio.wait_for(entered.wait(), timeout=5.0)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            elif outcome == "sdk_allocation_error":
                with pytest.raises(RuntimeError, match="FitChef Agent API unavailable") as caught:
                    await provider.generate(PROMPT)
                assert "secret SDK allocation details" not in "".join(
                    traceback.format_exception(caught.value)
                )
            else:
                assert await provider.generate(PROMPT) == "Choose one balanced next meal."
            assert not borrowed.is_closed and borrowed.follow_redirects is False
        assert len(created) == (1 if owned else 0)
        if owned:
            assert created[0].is_closed

    asyncio.run(_run())


def test_inherited_sdk_log_context_remains_private_after_parent_reset(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep inherited Agent diagnostics private after the parent context is reset."""

    caplog.set_level(logging.DEBUG, logger="openai._base_client")
    caplog.set_level(logging.DEBUG, logger="openai._response")

    async def _run() -> None:
        """Compare inherited child logging with independent logging after generation."""

        release_child = asyncio.Event()
        children: list[asyncio.Task[None]] = []

        async def _child() -> None:
            """Emit inherited SDK diagnostics after the parent releases the child task."""

            await release_child.wait()
            for name in ("openai._base_client", "openai._response"):
                logging.getLogger(name).warning("inherited Agent child diagnostic")

        def _handler(request: httpx.Request) -> httpx.Response:
            """Spawn the inherited child and emit an active Agent diagnostic."""

            children.append(asyncio.create_task(_child()))
            logging.getLogger("openai._base_client").warning("nested Agent diagnostic")
            return httpx.Response(200, json=_response_body())

        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as borrowed:
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP, model=MODEL, reasoning_effort="low", http_client=borrowed
            )
            await provider.generate(PROMPT)
            logging.getLogger("openai._base_client").warning("independent outside Agent diagnostic")
            release_child.set()
            await asyncio.wait_for(asyncio.gather(*children), timeout=5.0)

    asyncio.run(_run())
    assert "inherited Agent child diagnostic" not in caplog.text
    assert "nested Agent diagnostic" not in caplog.text
    assert "independent outside Agent diagnostic" in caplog.text


def test_sdk_debug_logs_are_private_and_concurrent_diagnostics_are_preserved(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Suppress Agent SDK logs while preserving independent concurrent diagnostics."""

    caplog.set_level(logging.DEBUG, logger="openai._base_client")
    caplog.set_level(logging.DEBUG, logger="openai._response")
    sdk_logger = logging.getLogger("openai._base_client")

    async def _run() -> None:
        """Coordinate a failing Agent task and independent SDK logging contexts."""

        entered = asyncio.Event()
        release = asyncio.Event()

        async def _handler(request: httpx.Request) -> httpx.Response:
            """Emit private SDK text, await release, and raise the synthetic timeout."""

            sdk_logger.debug("secret prompt and credential")
            entered.set()
            await release.wait()
            raise httpx.ReadTimeout("secret-provider-body synthetic-test-key", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http_client:
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP,
                model=MODEL,
                reasoning_effort="low",
                http_client=http_client,
            )
            task = asyncio.create_task(provider.generate(PROMPT))
            await asyncio.wait_for(entered.wait(), timeout=5.0)
            # This separate task context must keep ordinary SDK diagnostics.
            sdk_logger.debug("unrelated concurrent diagnostic")
            release.set()
            with pytest.raises(TimeoutError, match="FitChef Agent API timed out"):
                await task
            sdk_logger.debug("diagnostic after Agent request")

    asyncio.run(_run())
    assert "unrelated concurrent diagnostic" in caplog.text
    assert "diagnostic after Agent request" in caplog.text
    assert PROMPT not in caplog.text
    assert "secret prompt and credential" not in caplog.text
    assert "secret-provider-body" not in caplog.text
    assert "synthetic-test-key" not in caplog.text
    assert TEST_KEY_VIP not in caplog.text


@pytest.mark.parametrize("prompt", ["", " ", "é" * (AGENT_API_MAX_PROMPT_BYTES // 2 + 1)])
def test_invalid_prompt_does_not_allocate_client(
    monkeypatch: pytest.MonkeyPatch,
    prompt: str,
) -> None:
    """Reject invalid prompts before allocating any owned HTTP client."""

    monkeypatch.setattr(
        "providers.perplexity_agent._AgentAsyncOpenAI",
        lambda **kwargs: pytest.fail("bad prompt must not allocate a client"),
    )
    provider = PerplexityAgentProvider(api_key=TEST_KEY_VIP, model=MODEL, reasoning_effort="low")
    with pytest.raises(ValueError):
        asyncio.run(provider.generate(prompt))


@pytest.fixture
def agent_runtime_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Callable[[httpx.Request], httpx.Response]], None]:
    """Keep the real Responses adapter while replacing its physical transport."""

    from core.rag.contracts import RAGContext

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("FITCHEF_AGENT_API_ENABLED", "true")
    monkeypatch.setenv("FITCHEF_AGENT_API_MODEL", MODEL)
    monkeypatch.setenv("FITCHEF_AGENT_API_REASONING_EFFORT", "low")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("FEATURE_FITCHEF_MASCOT", "true")
    monkeypatch.setenv("FEATURE_FITCHEF_STRUCTURED_COACH", "true")
    monkeypatch.setenv("FITCHEF_MASCOT_EXECUTION_MODE", "auto-safe")
    monkeypatch.setenv("FITCHEF_STRUCTURED_COACH_EXECUTION_MODE", "auto-safe")
    monkeypatch.setattr(
        "llm.get_provider", lambda: pytest.fail("global selector/Sonar reroute must not run")
    )
    monkeypatch.setattr(
        "core.rag.vector_rag.retrieve_context_structured",
        lambda *args, **kwargs: RAGContext(
            query="test",
            refined_queries=[],
            chunks=[],
            confidence=0.0,
            hops=1,
            latency_ms=1,
        ),
    )
    monkeypatch.setattr(
        "app.services.fitchef_runtime.get_transparency_registry",
        lambda: {
            key: {"surface_id": key, "boundary": "Wellness planning only."}
            for key in ("ai_generated_insight", "fitchef_structured_v1")
        },
    )

    def _install(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        """Install a mock client factory bound to the supplied synthetic request handler."""

        def _client(**kwargs: Any) -> httpx.AsyncClient:
            """Build a mock SDK HTTP client without permitting redirects."""

            assert kwargs["follow_redirects"] is False
            return DefaultAsyncHttpxClient(**kwargs, transport=httpx.MockTransport(handler))

        monkeypatch.setattr("providers.perplexity_agent.DefaultAsyncHttpxClient", _client)

    return _install


_ROUTE_CASES = [
    (
        "/api/v1/insight/fitchef",
        "VIP",
        {"query": "Need support with dinner"},
        "FitChef says: choose one balanced next meal.",
        "message",
        "FitChef says: choose one balanced next meal.",
    ),
    (
        "/api/v1/pro/fitchef/explain",
        "PRO",
        {
            "situation": "I ate dessert",
            "automatic_thought": "I ruined the whole day",
            "emotion": "guilt",
        },
        json.dumps(
            {
                "distortion_labels": ["all_or_nothing_thinking"],
                "why_it_matches": "One moment became a total-day verdict.",
                "evidence_for": ["Dessert happened."],
                "evidence_against": ["The day had other meals."],
                "balanced_reframe": "This was one moment, not the whole pattern.",
                "next_small_action": "Choose one balanced next meal.",
            }
        ),
        "balanced_reframe",
        "This was one moment, not the whole pattern.",
    ),
    (
        "/api/v1/vip/fitchef/insight",
        "VIP",
        {
            "goal": "steady dinners",
            "recent_pattern": "I stop planning after work",
            "self_talk": "I am inconsistent",
        },
        json.dumps(
            {
                "identity_loop": {
                    "belief": "Dinner is difficult.",
                    "behavior": "I skip planning.",
                    "short_term_reward": "Less pressure.",
                    "long_term_cost": "Less support.",
                },
                "identity_shift_statement": "I can return to one small habit.",
                "replacement_action": "Choose a default dinner.",
                "repair_if_slip": "Restart with the next meal.",
            }
        ),
        "identity_shift_statement",
        "I can return to one small habit.",
    ),
]


@pytest.mark.parametrize(("url", "tier", "payload", "text", "field", "expected"), _ROUTE_CASES)
def test_agent_fitchef_routes_preserve_envelopes_and_quota_order(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    tmp_path: Path,
    url: str,
    tier: str,
    payload: dict[str, str],
    text: str,
    field: str,
    expected: str,
) -> None:
    """Exercise PRO JSON/balanced_reframe and both VIP tasks over the real SDK."""

    events: list[str] = []
    audit_path = tmp_path / "agent-audit.jsonl"
    monkeypatch.setenv("AGENT_CONTROL_AUDIT_LOG_PATH", str(audit_path))

    def _quota(_api_key: str, *, tier: str) -> bool:
        """Record quota admission before the route calls the mock provider."""

        events.append(tier)
        return True

    def _handler(request: httpx.Request) -> httpx.Response:
        """Record the provider call and render the route-specific synthetic output."""

        events.append("provider")
        body = json.loads(request.content)
        assert body["model"] == MODEL
        assert body["tools"] == [] and body["store"] is False
        assert "preset" not in body and "models" not in body
        return httpx.Response(200, json=_response_body(text=text))

    monkeypatch.setattr("app.services.fitchef_runtime.attempt_consume_llm_monthly_quota", _quota)
    agent_runtime_transport(_handler)
    response = client.post(url, json=payload, headers=pro_headers if tier == "PRO" else vip_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data[field] == expected
    assert data["quota_state"] == "consumed"
    assert "provider" not in data
    assert events == [tier, "provider"]
    assert "provider://default" in audit_path.read_text()
    assert "synthetic-test-key" not in audit_path.read_text()


@pytest.mark.parametrize("url", [case[0] for case in _ROUTE_CASES])
def test_agent_routes_quota_denied_makes_zero_provider_calls(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    url: str,
) -> None:
    """Prevent client allocation and provider calls when monthly quota is denied."""

    case = next(case for case in _ROUTE_CASES if case[0] == url)
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: False,
    )
    agent_runtime_transport(
        lambda request: pytest.fail("quota denial must prevent physical request")
    )
    monkeypatch.setattr(
        "providers.perplexity_agent.DefaultAsyncHttpxClient",
        lambda **kwargs: pytest.fail("quota denial must not allocate a client"),
    )
    response = client.post(
        url, json=case[2], headers=pro_headers if case[1] == "PRO" else vip_headers
    )
    assert response.status_code == 429
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "quota_exceeded"


@pytest.mark.parametrize(
    "failure",
    [
        "sdk_error",
        "timeout",
        "failed",
        "incomplete",
        "wrong_model",
        "tool",
        "empty",
        "redirect_same307",
        "redirect_cross307",
        "redirect_same308",
        "redirect_cross308",
    ],
)
def test_agent_route_failure_is_sanitized_without_sonar_reroute(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    vip_headers: dict[str, str],
    failure: str,
) -> None:
    """Preserve sanitized route errors without retrying or rerouting to Sonar."""

    calls = 0
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )

    def _handler(request: httpx.Request) -> httpx.Response:
        """Emit the selected timeout, server error, redirect, or invalid output fixture."""

        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-provider-body synthetic-test-key", request=request)
        if failure == "sdk_error":
            return httpx.Response(
                500, json={"error": {"message": "secret-provider-body synthetic-test-key"}}
            )
        if failure.startswith("redirect_"):
            return httpx.Response(
                307 if failure.endswith("307") else 308,
                headers={
                    "location": (
                        "https://example.invalid/private-redirect"
                        if "cross" in failure
                        else "/v1/private-redirect"
                    )
                },
                json={"error": {"message": "secret-provider-body synthetic-test-key"}},
            )
        body = _response_body()
        if failure in ("failed", "incomplete"):
            body["status"] = failure
        elif failure == "wrong_model":
            body["model"] = "openai/gpt-6-sol"
        elif failure == "tool":
            body["output"] = [
                {
                    "type": "function_call",
                    "name": "unexpected",
                    "arguments": "{}",
                    "call_id": "call_1",
                }
            ]
        elif failure == "empty":
            body = _response_body(text=" ")
        return httpx.Response(200, json=body)

    agent_runtime_transport(_handler)
    response = client.post(
        _ROUTE_CASES[0][0], json={"query": "Need support with dinner"}, headers=vip_headers
    )
    assert response.status_code == (504 if failure == "timeout" else 503)
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == (
        "LLM provider call timed out" if failure == "timeout" else "fitchef_mascot_unavailable"
    )
    assert calls == 1
    assert "synthetic-test-key" not in caplog.text + response.text
    assert "secret-provider-body" not in caplog.text + response.text
    assert "Need support with dinner" not in caplog.text


@pytest.mark.parametrize(
    ("env_name", "env_value", "detail"),
    [
        ("FITCHEF_AGENT_API_ENABLED", "invalid", "fitchef_agent_api_configuration_invalid"),
        ("PERPLEXITY_API_KEY", "", "fitchef_agent_api_configuration_invalid"),
        ("PERPLEXITY_API_KEY", "bad key", "fitchef_agent_api_configuration_invalid"),
        ("PERPLEXITY_API_KEY", "non-ascii-💥", "fitchef_agent_api_configuration_invalid"),
        ("FITCHEF_AGENT_API_MODEL", "", "fitchef_agent_api_configuration_invalid"),
        ("FITCHEF_AGENT_API_MODEL", "sonar", "fitchef_agent_api_configuration_invalid"),
        ("FITCHEF_AGENT_API_REASONING_EFFORT", "", "fitchef_agent_api_configuration_invalid"),
        ("FITCHEF_AGENT_API_REASONING_EFFORT", "high", "fitchef_agent_api_configuration_invalid"),
        ("APP_ENV", "production", "fitchef_agent_api_development_only"),
        ("ENVIRONMENT", "staging", "fitchef_agent_api_development_only"),
        ("APP_ENV", "unknown", "fitchef_agent_api_development_only"),
        *[
            ("FITCHEF_AGENT_API_MODEL", model, "fitchef_agent_api_configuration_invalid")
            for model in _NEAR_MODEL_IDS
        ],
    ],
)
@pytest.mark.parametrize("structured", [False, True])
def test_agent_bad_configuration_stops_before_quota_and_client(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    env_name: str,
    env_value: str,
    detail: str,
    structured: bool,
) -> None:
    # Isolate provider admission; audit permissions are a separate earlier gate.
    """Reject invalid Agent runtime settings before quota consumption or allocation."""

    monkeypatch.setattr(
        "app.services.fitchef_runtime._persist_privileged_action_audit", lambda **kwargs: None
    )
    monkeypatch.setenv(env_name, env_value)
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: pytest.fail("bad configuration must not debit quota"),
    )
    monkeypatch.setattr(
        "providers.perplexity_agent._AgentAsyncOpenAI",
        lambda **kwargs: pytest.fail("bad configuration must not allocate a client"),
    )
    case = _ROUTE_CASES[1 if structured else 0]
    # Production-like tier auth correctly rejects synthetic test credentials;
    # exercise the admitted runtime task directly to isolate this later gate.
    if env_name in ("APP_ENV", "ENVIRONMENT"):
        from fastapi import HTTPException
        from app.schemas.fitchef import (
            FitChefDistortionSimulatorInput,
            FitChefDistortionSimulatorTaskEnvelope,
            FitChefMascotInsightInput,
            FitChefMascotInsightTaskEnvelope,
        )
        from app.services import fitchef_runtime
        from app.middleware.api_tiers import TEST_KEY_PRO, TEST_KEY_VIP

        with pytest.raises(HTTPException) as caught:
            if structured:
                asyncio.run(
                    fitchef_runtime.run_distortion_simulator_task(
                        FitChefDistortionSimulatorTaskEnvelope(
                            mode="auto-safe",
                            input=FitChefDistortionSimulatorInput(
                                safe_situation="I ate dessert",
                                safe_automatic_thought="I ruined the day",
                                safe_emotion="guilt",
                                api_key=TEST_KEY_PRO,
                                endpoint=case[0],
                                method="POST",
                            ),
                        )
                    )
                )
            else:
                asyncio.run(
                    fitchef_runtime.run_mascot_insight_task(
                        FitChefMascotInsightTaskEnvelope(
                            mode="auto-safe",
                            input=FitChefMascotInsightInput(
                                safe_query="Need support with dinner",
                                api_key=TEST_KEY_VIP,
                                endpoint=case[0],
                                method="POST",
                            ),
                        )
                    )
                )
        assert caught.value.status_code == 503
        assert caught.value.detail == detail
    else:
        response = client.post(
            case[0], json=case[2], headers=pro_headers if structured else vip_headers
        )
        assert response.status_code == 503
        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["detail"] == detail


@pytest.mark.parametrize("flag", [None, "false"])
def test_default_agent_option_preserves_existing_selector(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    vip_headers: dict[str, str],
    flag: str | None,
) -> None:
    """Preserve the existing provider selector when the Agent option is disabled."""

    if flag is None:
        monkeypatch.delenv("FITCHEF_AGENT_API_ENABLED")
    else:
        monkeypatch.setenv("FITCHEF_AGENT_API_ENABLED", flag)

    class _BaselineProvider:
        name = "baseline"

        async def generate(self, prompt: str) -> str:
            """Return deterministic baseline text from the existing selector."""

            return "Plan one balanced meal."

    monkeypatch.setattr("llm.get_provider", lambda: _BaselineProvider())
    monkeypatch.setattr(
        "providers.perplexity_agent.PerplexityAgentProvider",
        lambda **kwargs: pytest.fail("disabled Agent option must not select Agent"),
    )
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )
    response = client.post(_ROUTE_CASES[0][0], json=_ROUTE_CASES[0][2], headers=vip_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["message"] == "Plan one balanced meal."


@pytest.mark.parametrize("requested", _APPROVED_MODELS)
@pytest.mark.parametrize("returned", _APPROVED_MODELS)
def test_model_identity_relation_is_exact(requested: str, returned: str) -> None:
    """A successful response from another approved model still fails closed."""
    calls = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        """Capture the requested model and return the selected response model identity."""

        nonlocal calls
        calls += 1
        assert json.loads(request.content)["model"] == requested
        return httpx.Response(200, json=_response_body(model=returned))

    if requested == returned:
        assert asyncio.run(_generate_with_transport(_handler, model=requested))
    else:
        with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
            asyncio.run(_generate_with_transport(_handler, model=requested))
    assert calls == 1


@pytest.mark.parametrize("model", _NEAR_MODEL_IDS)
def test_near_model_ids_fail_before_sdk_allocation(
    monkeypatch: pytest.MonkeyPatch, model: str
) -> None:
    """Reject near-match model identifiers before SDK allocation."""

    monkeypatch.setattr(
        "providers.perplexity_agent._AgentAsyncOpenAI",
        lambda **kwargs: pytest.fail("unapproved model must not allocate SDK"),
    )
    with pytest.raises(ValueError, match="model is not approved"):
        PerplexityAgentProvider(api_key=TEST_KEY_VIP, model=model, reasoning_effort="none")


def test_model61_factory_preserves_explicit_configuration_and_delayed_allocation(
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
) -> None:
    """Keep the explicit 6.1 settings and defer allocation until generation."""

    from app.services.fitchef_runtime import _require_fitchef_llm_provider

    monkeypatch.setenv("FITCHEF_AGENT_API_MODEL", "openai/gpt-6.1-sol")
    monkeypatch.setenv("FITCHEF_AGENT_API_REASONING_EFFORT", "none")
    monkeypatch.setattr(
        "providers.perplexity_agent._AgentAsyncOpenAI",
        lambda **kwargs: pytest.fail("factory must not allocate SDK before admitted generation"),
    )
    provider = _require_fitchef_llm_provider(PROMPT)
    assert isinstance(provider, PerplexityAgentProvider)
    assert provider.model == "openai/gpt-6.1-sol" and provider.reasoning_effort == "none"


@pytest.mark.parametrize(("url", "tier", "payload", "text", "field", "expected"), _ROUTE_CASES)
def test_model61_routes_keep_backend_envelopes_and_quota_order(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    url: str,
    tier: str,
    payload: dict[str, str],
    text: str,
    field: str,
    expected: str,
) -> None:
    """Preserve backend envelopes and quota-before-provider ordering for model 6.1."""

    monkeypatch.setenv("FITCHEF_AGENT_API_MODEL", "openai/gpt-6.1-sol")
    events: list[str] = []

    def _quota(_api_key: str, *, tier: str) -> bool:
        """Record model 6.1 quota admission before the mock provider send."""

        events.append(tier)
        return True

    def _handler(request: httpx.Request) -> httpx.Response:
        """Record the 6.1 provider request and return route-specific synthetic output."""

        events.append("provider")
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-6.1-sol"
        assert body["tools"] == [] and body["store"] is False
        assert request.headers["authorization"] == "Bearer synthetic-test-key"
        return httpx.Response(200, json=_response_body(model=body["model"], text=text))

    monkeypatch.setattr("app.services.fitchef_runtime.attempt_consume_llm_monthly_quota", _quota)
    agent_runtime_transport(_handler)
    response = client.post(url, json=payload, headers=pro_headers if tier == "PRO" else vip_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data[field] == expected and data["quota_state"] == "consumed"
    assert "provider" not in data and events == [tier, "provider"]


@pytest.mark.parametrize("url", [case[0] for case in _ROUTE_CASES])
def test_model61_quota_denial_still_prevents_client_and_send(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    url: str,
) -> None:
    """Prevent client allocation and sends when model 6.1 quota is denied."""

    monkeypatch.setenv("FITCHEF_AGENT_API_MODEL", "openai/gpt-6.1-sol")
    test_agent_routes_quota_denied_makes_zero_provider_calls(
        client, monkeypatch, agent_runtime_transport, pro_headers, vip_headers, url
    )


@pytest.mark.parametrize("flag", [None, "false"])
def test_model61_configuration_does_not_enable_the_default_off_option(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    vip_headers: dict[str, str],
    flag: str | None,
) -> None:
    """Keep Agent selection disabled when only the 6.1 configuration is present."""

    monkeypatch.setenv("FITCHEF_AGENT_API_MODEL", "openai/gpt-6.1-sol")
    test_default_agent_option_preserves_existing_selector(
        client, monkeypatch, agent_runtime_transport, vip_headers, flag
    )


def test_module_credential_clearing_uses_the_same_seam_before_sdk_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seed synthetic sources before clearing; never examine host values."""
    seeded = {name: f"synthetic-{name.lower()}" for name in _SDK_ENV_NAMES}
    for name, value in seeded.items():
        monkeypatch.setenv(name, value)
    calls = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        """Assert synthetic-only authentication and no inherited identity headers."""

        nonlocal calls
        calls += 1
        assert request.url.host == "api.perplexity.ai"
        assert request.headers["authorization"] == f"Bearer {TEST_KEY_VIP}"
        assert "OpenAI-Organization" not in request.headers
        assert "OpenAI-Project" not in request.headers
        return httpx.Response(200, json=_response_body())

    with monkeypatch.context() as cleared:
        _clear_sdk_environment(cleared)
        assert all(name not in os.environ for name in _SDK_ENV_NAMES)
        assert asyncio.run(_generate_with_transport(_handler))
    assert calls == 1
    assert {name: os.environ[name] for name in _SDK_ENV_NAMES} == seeded


@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize(
    "stimulus",
    ["OPENAI_ORG_ID", "OPENAI_PROJECT_ID", "OPENAI_WEBHOOK_SECRET", "combined"],
)
def test_runtime_sdk_identity_defaults_are_disabled_after_harness_clearing(
    monkeypatch: pytest.MonkeyPatch, stimulus: str, owned: bool
) -> None:
    """Observe real SDK state and request with inputs deliberately still present."""
    names = (
        ("OPENAI_ORG_ID", "OPENAI_PROJECT_ID", "OPENAI_WEBHOOK_SECRET")
        if stimulus == "combined"
        else (stimulus,)
    )
    injected = {name: f"synthetic-runtime-{name.lower()}" for name in names}
    for name, value in injected.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-unrelated-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/unrelated")
    states: list[tuple[str | None, str | None, str | None]] = []
    created: list[httpx.AsyncClient] = []
    calls = 0

    class _ObservedSDK(_AgentAsyncOpenAI):
        def __init__(self, **kwargs: Any) -> None:
            """Record native SDK identity state after its constructor completes."""

            super().__init__(**kwargs)
            states.append((self.organization, self.project, self.webhook_secret))

    def _handler(request: httpx.Request) -> httpx.Response:
        """Assert the fixed Agent endpoint and synthetic authentication on the wire."""

        nonlocal calls
        calls += 1
        assert request.url == httpx.URL("https://api.perplexity.ai/v1/responses")
        assert request.headers["authorization"] == f"Bearer {TEST_KEY_VIP}"
        assert "OpenAI-Organization" not in request.headers
        assert "OpenAI-Project" not in request.headers
        assert json.loads(request.content)["input"] == PROMPT
        return httpx.Response(200, json=_response_body())

    def _owned_client(**kwargs: Any) -> httpx.AsyncClient:
        """Allocate and track the owned client for SDK identity isolation checks."""

        result = DefaultAsyncHttpxClient(**kwargs, transport=httpx.MockTransport(_handler))
        created.append(result)
        return result

    monkeypatch.setattr("providers.perplexity_agent._AgentAsyncOpenAI", _ObservedSDK)
    monkeypatch.setattr("providers.perplexity_agent.DefaultAsyncHttpxClient", _owned_client)

    async def _run() -> None:
        """Exercise native SDK defaults with an owned or borrowed synthetic transport."""

        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as borrowed:
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP,
                model=MODEL,
                reasoning_effort="low",
                http_client=None if owned else borrowed,
            )
            assert await provider.generate(PROMPT)
            assert not borrowed.is_closed

    asyncio.run(_run())
    assert states == [("", "", "")] and calls == 1
    assert {name: os.environ[name] for name in names} == injected
    assert len(created) == (1 if owned else 0)
    if owned:
        assert created[0].is_closed


@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("case", ["canonical", "lower", "mixed_duplicates"])
def test_effective_request_omits_identity_headers_without_mutating_client_defaults(
    monkeypatch: pytest.MonkeyPatch, owned: bool, failure: bool, case: str
) -> None:
    """Borrowed defaults survive until build; exact names disappear on the request."""
    identity = {
        "canonical": [("OpenAI-Organization", "synthetic-org"), ("OpenAI-Project", "synthetic-p")],
        "lower": [("openai-organization", "synthetic-org"), ("openai-project", "synthetic-p")],
        "mixed_duplicates": [
            ("OpenAI-Organization", "synthetic-org"),
            ("OPENAI-ORGANIZATION", "synthetic-other-org"),
            ("oPeNaI-pRoJeCt", "synthetic-p"),
            ("OpenAI-Project", "synthetic-other-p"),
        ],
    }[case]
    defaults = [*identity, ("X-OpenAI-Organization", "neighbor"), ("X-Control", "preserved")]
    created: list[httpx.AsyncClient] = []
    created_raw: list[list[tuple[bytes, bytes]]] = []
    calls = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        """Capture all effective headers and assert exact identity-header absence."""

        nonlocal calls
        calls += 1
        assert "OpenAI-Organization" not in request.headers
        assert "OpenAI-Project" not in request.headers
        assert request.headers["X-OpenAI-Organization"] == "neighbor"
        assert request.headers["X-Control"] == "preserved"
        assert request.headers["authorization"] == f"Bearer {TEST_KEY_VIP}"
        assert request.url == httpx.URL("https://api.perplexity.ai/v1/responses")
        body = json.loads(request.content)
        assert body["model"] == MODEL and body["tools"] == [] and body["store"] is False
        assert body["input"] == PROMPT
        return httpx.Response(500 if failure else 200, json=_response_body())

    def _owned_client(**kwargs: Any) -> httpx.AsyncClient:
        """Build an owned mock client with the same synthetic default-header fixture."""

        result = DefaultAsyncHttpxClient(
            **kwargs, headers=defaults, transport=httpx.MockTransport(_handler)
        )
        created.append(result)
        created_raw.append(list(result.headers.raw))
        return result

    monkeypatch.setattr("providers.perplexity_agent.DefaultAsyncHttpxClient", _owned_client)

    async def _run() -> None:
        """Compare effective request headers with the unchanged client defaults."""

        async with httpx.AsyncClient(
            headers=defaults,
            cookies={"synthetic-cookie": "unchanged"},
            transport=httpx.MockTransport(_handler),
            timeout=17.0,
            trust_env=False,
        ) as borrowed:
            raw = list(borrowed.headers.raw)
            cookies = dict(borrowed.cookies)
            timeout = borrowed.timeout
            auth = borrowed.auth
            provider = PerplexityAgentProvider(
                api_key=TEST_KEY_VIP,
                model=MODEL,
                reasoning_effort="low",
                http_client=None if owned else borrowed,
            )
            if failure:
                with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
                    await provider.generate(PROMPT)
            else:
                assert await provider.generate(PROMPT)
            assert list(borrowed.headers.raw) == raw
            assert dict(borrowed.cookies) == cookies
            assert borrowed.timeout == timeout and borrowed.auth is auth
            assert borrowed.follow_redirects is False and borrowed.trust_env is False
            assert not borrowed.is_closed

    asyncio.run(_run())
    assert calls == 1 and len(created) == (1 if owned else 0)
    if owned:
        assert created[0].is_closed
        assert list(created[0].headers.raw) == created_raw[0]


@pytest.mark.parametrize("header_state", ["absent", "empty", "populated"])
def test_identity_hook_preserves_original_native_options_header_data(header_state: str) -> None:
    """Preserve the original native option headers while preparing the wire request."""

    async def _run() -> None:
        """Compare original options, prepared options, and the final request headers."""

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200))
        ) as borrowed:
            sdk = _AgentAsyncOpenAI(api_key=TEST_KEY_VIP, http_client=borrowed)
            kwargs: dict[str, Any] = {}
            if header_state != "absent":
                kwargs["headers"] = (
                    {"OpenAI-Organization": "synthetic", "X-Control": "preserved"}
                    if header_state == "populated"
                    else {}
                )
            options = FinalRequestOptions.construct(
                method="post", url="/responses", follow_redirects=True, **kwargs
            )
            original = {
                name: deepcopy(value) if isinstance(value, dict) else value
                for name, value in options.__dict__.items()
            }
            prepared = await sdk._prepare_options(options)
            assert prepared is not options and prepared.follow_redirects is False
            assert options.__dict__ == original and options.follow_redirects is True
            assert prepared.headers == options.headers
            request = borrowed.build_request(
                "POST", "https://api.perplexity.ai/v1/responses", headers=kwargs.get("headers")
            )
            await sdk._prepare_request(request)
            assert "OpenAI-Organization" not in request.headers
            assert "OpenAI-Project" not in request.headers
            if header_state == "populated":
                assert request.headers["X-Control"] == "preserved"
            assert options.__dict__ == original
            assert not borrowed.is_closed

    asyncio.run(_run())


def test_concurrent_agent_requests_leave_independent_sdk_identity_and_client_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep concurrent Agent calls from mutating an independent SDK or its client."""

    monkeypatch.setenv("OPENAI_ORG_ID", "synthetic-independent-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "synthetic-independent-project")
    monkeypatch.setenv("OPENAI_WEBHOOK_SECRET", "synthetic-independent-webhook")

    async def _run() -> None:
        """Coordinate two Agent requests and inspect independent SDK and client state."""

        both_entered = asyncio.Event()
        requests: list[httpx.Request] = []

        async def _handler(request: httpx.Request) -> httpx.Response:
            """Hold both Agent sends until their effective identity headers are captured."""

            requests.append(request)
            if len(requests) == 2:
                both_entered.set()
            await asyncio.wait_for(both_entered.wait(), timeout=5.0)
            assert "OpenAI-Organization" not in request.headers
            assert "OpenAI-Project" not in request.headers
            assert request.headers["X-Control"] == "preserved"
            assert request.headers["authorization"] == f"Bearer {TEST_KEY_VIP}"
            return httpx.Response(200, json=_response_body())

        async with httpx.AsyncClient(
            headers={
                "OpenAI-Organization": "borrowed-org",
                "OpenAI-Project": "borrowed-p",
                "X-Control": "preserved",
            },
            transport=httpx.MockTransport(_handler),
        ) as borrowed:
            raw = list(borrowed.headers.raw)
            independent = AsyncOpenAI(api_key="synthetic-independent-key", http_client=borrowed)
            states = (independent.organization, independent.project, independent.webhook_secret)
            providers = [
                PerplexityAgentProvider(
                    api_key=TEST_KEY_VIP, model=MODEL, reasoning_effort="none", http_client=borrowed
                )
                for _ in range(2)
            ]
            assert await asyncio.gather(
                *(p.generate(f"synthetic prompt {i}") for i, p in enumerate(providers))
            )
            assert len(requests) == 2 and requests[0] is not requests[1]
            assert [json.loads(r.content)["input"] for r in requests] == [
                "synthetic prompt 0",
                "synthetic prompt 1",
            ]
            assert list(borrowed.headers.raw) == raw and not borrowed.is_closed
            assert (
                independent.organization,
                independent.project,
                independent.webhook_secret,
            ) == states
            assert states == (
                "synthetic-independent-org",
                "synthetic-independent-project",
                "synthetic-independent-webhook",
            )
            assert independent.default_headers["OpenAI-Organization"] == states[0]
            assert independent.default_headers["OpenAI-Project"] == states[1]

    asyncio.run(_run())
