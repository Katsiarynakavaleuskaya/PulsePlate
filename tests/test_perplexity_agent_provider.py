"""Mock-transport contract tests for the bounded FitChef Agent API adapter."""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import AsyncOpenAI
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_VIP
from providers.perplexity_agent import (
    AGENT_API_MAX_OUTPUT_TOKENS,
    AGENT_API_MAX_OUTPUT_BYTES,
    AGENT_API_MAX_PROMPT_BYTES,
    PerplexityAgentProvider,
)

MODEL = "openai/gpt-6-luna"
PROMPT = "Give one bounded FitChef planning reflection."


def _response_body(
    *,
    status: str = "completed",
    model: str = MODEL,
    text: str = "Choose one balanced next meal.",
    output: list[dict[str, object]] | None = None,
    error: object = None,
) -> dict[str, object]:
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
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        provider = PerplexityAgentProvider(
            api_key=TEST_KEY_VIP,
            model=model,
            reasoning_effort=effort,
            http_client=http_client,
        )
        return await provider.generate(prompt)


@pytest.mark.parametrize("model", [MODEL, "openai/gpt-6-sol"])
@pytest.mark.parametrize("effort", ["none", "low"])
def test_exact_tool_free_request_and_single_attempt(model: str, effort: str) -> None:
    requests: list[dict[str, object]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
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
    calls = 0

    def _handler(_request: httpx.Request) -> httpx.Response:
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
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
        asyncio.run(_generate_with_transport(_handler))


def test_sdk_error_is_sanitized_without_retry_or_secret_traceback() -> None:
    calls = 0

    def _handler(_request: httpx.Request) -> httpx.Response:
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
    with pytest.raises(ValueError):
        PerplexityAgentProvider(api_key=key, model=model, reasoning_effort=effort)


def test_prompt_byte_budget_is_preflighted() -> None:
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
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_response_body(output=output))

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable"):
        asyncio.run(_generate_with_transport(_handler))


def test_reasoning_then_one_final_message_is_admitted() -> None:
    body = _response_body()
    output = body["output"]
    assert isinstance(output, list)
    output.insert(0, {"type": "reasoning", "id": "reason_1", "summary": []})

    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    assert asyncio.run(_generate_with_transport(_handler)) == "Choose one balanced next meal."


@pytest.mark.parametrize("mode", ["too_large", "incomplete_details", "multiple", "malformed_json"])
def test_other_invalid_response_bodies_are_rejected(mode: str) -> None:
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
        if mode == "malformed_json":
            return httpx.Response(200, content=b"not-json secret-provider-body")
        return httpx.Response(200, json=body)

    with pytest.raises(RuntimeError, match="FitChef Agent API unavailable") as caught:
        asyncio.run(_generate_with_transport(_handler))
    assert "secret-provider-body" not in "".join(traceback.format_exception(caught.value))


def test_timeout_is_sanitized_and_not_retried() -> None:
    calls = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("secret prompt and credential", request=request)

    with pytest.raises(TimeoutError, match="FitChef Agent API timed out") as caught:
        asyncio.run(_generate_with_transport(_handler))
    assert calls == 1
    assert "secret prompt and credential" not in "".join(traceback.format_exception(caught.value))


def test_sdk_debug_logs_are_private_and_concurrent_diagnostics_are_preserved(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="openai._base_client")
    caplog.set_level(logging.DEBUG, logger="openai._response")
    sdk_logger = logging.getLogger("openai._base_client")

    async def _run() -> None:
        entered = asyncio.Event()
        release = asyncio.Event()

        async def _handler(request: httpx.Request) -> httpx.Response:
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
    monkeypatch.setattr(
        "providers.perplexity_agent.AsyncOpenAI",
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
        def _client(**kwargs: Any) -> AsyncOpenAI:
            kwargs.pop("http_client", None)
            return AsyncOpenAI(
                **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
            )

        monkeypatch.setattr("providers.perplexity_agent.AsyncOpenAI", _client)

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
        events.append(tier)
        return True

    def _handler(request: httpx.Request) -> httpx.Response:
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
    case = next(case for case in _ROUTE_CASES if case[0] == url)
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: False,
    )
    agent_runtime_transport(
        lambda request: pytest.fail("quota denial must prevent physical request")
    )
    monkeypatch.setattr(
        "providers.perplexity_agent.AsyncOpenAI",
        lambda **kwargs: pytest.fail("quota denial must not allocate a client"),
    )
    response = client.post(
        url, json=case[2], headers=pro_headers if case[1] == "PRO" else vip_headers
    )
    assert response.status_code == 429
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "quota_exceeded"


@pytest.mark.parametrize(
    "failure", ["sdk_error", "timeout", "failed", "incomplete", "wrong_model", "tool", "empty"]
)
def test_agent_route_failure_is_sanitized_without_sonar_reroute(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    agent_runtime_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    vip_headers: dict[str, str],
    failure: str,
) -> None:
    calls = 0
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-provider-body synthetic-test-key", request=request)
        if failure == "sdk_error":
            return httpx.Response(
                500, json={"error": {"message": "secret-provider-body synthetic-test-key"}}
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
    monkeypatch.setattr(
        "app.services.fitchef_runtime._persist_privileged_action_audit", lambda **kwargs: None
    )
    monkeypatch.setenv(env_name, env_value)
    monkeypatch.setattr(
        "app.services.fitchef_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: pytest.fail("bad configuration must not debit quota"),
    )
    monkeypatch.setattr(
        "providers.perplexity_agent.AsyncOpenAI",
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
    if flag is None:
        monkeypatch.delenv("FITCHEF_AGENT_API_ENABLED")
    else:
        monkeypatch.setenv("FITCHEF_AGENT_API_ENABLED", flag)

    class _BaselineProvider:
        name = "baseline"

        async def generate(self, prompt: str) -> str:
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
