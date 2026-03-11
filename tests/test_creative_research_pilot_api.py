"""Tests for the internal creative research pilot route/runtime."""

from __future__ import annotations

import asyncio
import json
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import Response
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest

from app.middleware.api_tiers import SubscriptionTier, TEST_KEY_VIP
from app.schemas.creative_research import (
    CreativeResearchPilotInput,
    CreativeResearchPilotRequest,
    CreativeResearchPilotTaskEnvelope,
)
from app.telemetry.genai import OPENINFERENCE_KIND_LLM, OPENINFERENCE_SPAN_KIND
from app.telemetry.setup import install_test_exporter, reset_tracing_for_tests

ROUTE_PATH = "/api/v1/internal/creative-research/pilot"


class _StaticProvider:
    """Deterministic provider stub for route/runtime tests."""

    name = "stub"

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return self.payload


def _json_body(response: Response) -> dict[str, object]:
    content_type = response.headers.get("content-type", "").lower()
    assert content_type.startswith("application/json")
    return dict(response.json())


def _valid_provider_payload() -> str:
    return json.dumps(
        {
            "schema_version": "1.0",
            "bundle_id": "provider-bundle",
            "task_class": "creative_research",
            "phase": "verification",
            "prompt_seed": "Meal adherence under time scarcity",
            "reference_corpus": ["Missed dinners increase friction."],
            "candidates": [
                {
                    "candidate_id": "hyp-1",
                    "claim": "Batching fallback dinners can reduce decision fatigue after long workdays.",
                    "mechanism": (
                        "Because a pre-committed fallback reduces friction and shrinks the number "
                        "of end-of-day decisions, adherence should improve."
                    ),
                    "evidence_needed": (
                        "Compare completion and adherence rates across two weeks before and after "
                        "fallback dinner prompts."
                    ),
                    "falsifier": (
                        "If adherence stays flat despite prompt exposure, the mechanism is wrong."
                    ),
                    "confidence": "medium",
                    "known_risks": ["self-report bias"],
                    "wellness_boundary": (
                        "Wellness only; not diagnosis, treatment, or medical advice."
                    ),
                },
                {
                    "candidate_id": "hyp-2",
                    "claim": "Unexpected weekend depletion may explain Sunday adherence drops.",
                    "mechanism": (
                        "Weekend depletion shifts planning effort into late Sunday, increasing "
                        "decision fatigue and reducing follow-through."
                    ),
                    "evidence_needed": "Track Sunday completion rates and compare against weekday baselines.",
                    "falsifier": "",
                    "confidence": "high",
                    "known_risks": ["confounding events"],
                    "wellness_boundary": (
                        "Wellness only; not diagnosis, treatment, or medical advice."
                    ),
                },
            ],
        }
    )


def _task_payload(
    *,
    reference_corpus: list[str] | None = None,
    candidate_count: int = 2,
) -> CreativeResearchPilotTaskEnvelope:
    """Build a deterministic creative-research task envelope for runtime tests."""

    return CreativeResearchPilotTaskEnvelope.model_validate(
        {
            "mode": "auto-safe",
            "input": {
                "prompt_seed": "Meal adherence under time scarcity",
                "reference_corpus": reference_corpus or ["Missed dinners increase friction."],
                "candidate_count": candidate_count,
                "api_key": TEST_KEY_VIP,
                "endpoint": ROUTE_PATH,
                "method": "POST",
            },
        }
    )


def test_creative_research_route_is_hidden_from_openapi() -> None:
    """The pilot route must stay registered at runtime but hidden from public schema."""

    from app.main import app

    runtime_routes = {
        str(getattr(route, "path", "")): getattr(route, "include_in_schema", True)
        for route in app.routes
    }

    assert ROUTE_PATH in runtime_routes
    assert runtime_routes[ROUTE_PATH] is False
    assert ROUTE_PATH not in app.openapi().get("paths", {})


def test_creative_research_feature_flag_disabled_returns_503(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabled pilot must fail closed before runtime work."""

    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "false")

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "meal adherence", "candidate_count": 2},
        headers=vip_headers,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "FEATURE_CREATIVE_RESEARCH_PILOT is disabled"}


def test_creative_research_execution_mode_review_required_returns_503(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review-required mode must block the internal pilot."""

    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "true")
    monkeypatch.setenv("CREATIVE_RESEARCH_EXECUTION_MODE", "review-required")

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "meal adherence", "candidate_count": 2},
        headers=vip_headers,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "agent_execution_review_required"}


def test_creative_research_execution_mode_invalid_returns_503(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid execution mode must surface a stable misconfiguration error."""

    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "true")
    monkeypatch.setenv("CREATIVE_RESEARCH_EXECUTION_MODE", "definitely-invalid")

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "meal adherence", "candidate_count": 2},
        headers=vip_headers,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "agent_execution_mode_misconfigured"}


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"prompt_seed": "   ", "candidate_count": 2}, "prompt_seed must not be blank"),
        (
            {"prompt_seed": "meal adherence", "reference_corpus": ["valid", "   "]},
            "reference_corpus items must not be blank",
        ),
        (
            {"prompt_seed": "meal adherence", "reference_corpus": ["x" * 501]},
            "reference_corpus items must be <= 500 chars",
        ),
    ],
)
def test_creative_research_request_schema_rejects_invalid_inputs(
    payload: dict[str, object],
    message: str,
) -> None:
    """Schema validators must fail closed on blank or oversized request inputs."""

    with pytest.raises(ValueError, match=message):
        CreativeResearchPilotRequest.model_validate(payload)


@pytest.mark.parametrize("field_name", ["api_key", "endpoint", "method"])
def test_creative_research_internal_input_rejects_blank_transport_fields(
    field_name: str,
) -> None:
    """Internal envelope fields must reject whitespace-only transport metadata."""

    payload = {
        "prompt_seed": "Meal adherence under time scarcity",
        "reference_corpus": ["Missed dinners increase friction."],
        "candidate_count": 2,
        "api_key": TEST_KEY_VIP,
        "endpoint": ROUTE_PATH,
        "method": "POST",
    }
    payload[field_name] = "   "

    with pytest.raises(ValueError, match="internal string fields must not be blank"):
        CreativeResearchPilotInput.model_validate(payload)


def test_creative_research_success_returns_evaluated_candidates(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful pilot should return evaluated candidates plus bounded budget state."""

    provider = _StaticProvider(_valid_provider_payload())
    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "true")
    monkeypatch.setenv("CREATIVE_RESEARCH_EXECUTION_MODE", "auto-safe")
    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr("llm.get_provider", lambda: provider)

    response = client.post(
        ROUTE_PATH,
        json={
            "prompt_seed": "Meal adherence under time scarcity",
            "reference_corpus": ["Missed dinners increase friction."],
            "candidate_count": 2,
        },
        headers=vip_headers,
    )

    assert response.status_code == 200
    data = _json_body(response)
    assert data["task_class"] == "creative_research"
    assert data["quota_state"] == "consumed"
    assert data["summary"] == {
        "candidate_count": 2,
        "promote": 1,
        "defer": 0,
        "discard": 1,
    }
    assert data["budget_state"]["max_branches"] == 6
    assert data["budget_state"]["llm_calls_used"] == 1
    assert provider.calls == 1

    by_id = {candidate["candidate_id"]: candidate for candidate in data["candidates"]}
    assert by_id["hyp-1"]["promotion_decision"] == "promote"
    assert by_id["hyp-2"]["output_class"] == "creative_ideation"
    assert by_id["hyp-2"]["presentation_label"] == "interesting but unverified hypothesis"


def test_creative_research_quota_exceeded_blocks_provider_call(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quota must hard-stop before any provider generation happens."""

    def _unexpected_provider() -> None:
        pytest.fail("get_provider must not run when quota is exhausted")

    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "true")
    monkeypatch.setenv("CREATIVE_RESEARCH_EXECUTION_MODE", "auto-safe")
    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr("llm.get_provider", _unexpected_provider)

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "Meal adherence under time scarcity", "candidate_count": 2},
        headers=vip_headers,
    )

    assert response.status_code == 429
    assert _json_body(response) == {"detail": "quota_exceeded"}


def test_creative_research_invalid_provider_payload_returns_503(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed provider output must fail closed with a stable detail string."""

    provider = _StaticProvider("not-json")
    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "true")
    monkeypatch.setenv("CREATIVE_RESEARCH_EXECUTION_MODE", "auto-safe")
    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr("llm.get_provider", lambda: provider)

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "Meal adherence under time scarcity", "candidate_count": 2},
        headers=vip_headers,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "creative_research_provider_invalid_response"}


@pytest.mark.asyncio
async def test_runtime_missing_transparency_registry_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing transparency metadata must stop the runtime before quota consumption."""

    monkeypatch.setattr(
        "app.services.creative_research_runtime.get_transparency_registry", lambda: {}
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: pytest.fail("quota must not run"),
    )

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "transparency_registry_unavailable"


@pytest.mark.asyncio
async def test_runtime_incomplete_transparency_registry_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Incomplete transparency metadata must fail closed before provider use."""

    monkeypatch.setattr(
        "app.services.creative_research_runtime.get_transparency_registry",
        lambda: {"ai_generated_insight": {"surface_id": "ai_generated_insight"}},
    )

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "transparency_registry_incomplete"


@pytest.mark.asyncio
async def test_runtime_non_auto_safe_mode_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service must reject unsupported execution modes before provider use."""

    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: pytest.fail("quota must not run"),
    )

    task = CreativeResearchPilotTaskEnvelope.model_validate(
        {
            "mode": "review-required",
            "input": {
                "prompt_seed": "Meal adherence under time scarcity",
                "reference_corpus": ["Missed dinners increase friction."],
                "candidate_count": 2,
                "api_key": TEST_KEY_VIP,
                "endpoint": ROUTE_PATH,
                "method": "POST",
            },
        }
    )

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(task)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "agent_execution_review_required"


@pytest.mark.asyncio
async def test_runtime_non_vip_api_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service must reject non-VIP keys before quota or provider work."""

    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: pytest.fail("quota must not run"),
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.get_subscription_tier",
        lambda _api_key: SubscriptionTier.PRO,
    )

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "creative_research_vip_required"


@pytest.mark.asyncio
async def test_runtime_llm_gate_failure_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Privileged-action audit failures must fail closed before quota/provider work."""

    def _audit(**_: object) -> None:
        raise RuntimeError("llm gate down")

    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        _audit,
    )

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "llm_generation_unavailable"


@pytest.mark.asyncio
async def test_runtime_provider_none_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing provider instance must fail closed with stable detail."""

    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr("llm.get_provider", lambda: None)

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "LLM provider not available"


@pytest.mark.asyncio
async def test_runtime_provider_exception_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected provider failures must map to the stable unavailable detail."""

    class _ExplodingProvider:
        name = "broken"

        def generate(self, prompt: str) -> str:
            del prompt
            raise RuntimeError("provider boom")

    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr("llm.get_provider", lambda: _ExplodingProvider())

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "creative_research_generation_unavailable"


@pytest.mark.asyncio
async def test_runtime_empty_provider_payload_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-string or empty provider payloads must fail closed."""

    class _EmptyProvider:
        name = "empty"

        def generate(self, prompt: str) -> object:
            del prompt
            return {}

    monkeypatch.setattr(
        "app.services.creative_research_runtime._persist_privileged_action_audit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr("llm.get_provider", lambda: _EmptyProvider())

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    with pytest.raises(HTTPException) as exc_info:
        await run_creative_research_pilot_task(_task_payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "creative_research_provider_invalid_response"


def test_creative_research_service_emits_minimized_llm_tracing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracing must capture only allowlisted metadata for the pilot."""

    exporter = InMemorySpanExporter()
    reset_tracing_for_tests()
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("PULSE_OBS_HMAC_KEY", "test-genai-hmac-key")
    install_test_exporter(exporter)

    try:
        provider = _StaticProvider(_valid_provider_payload())
        monkeypatch.setattr(
            "app.services.creative_research_runtime._persist_privileged_action_audit",
            lambda **_: None,
        )
        monkeypatch.setattr(
            "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
            lambda *args, **kwargs: True,
        )
        monkeypatch.setattr("llm.get_provider", lambda: provider)

        from app.services.creative_research_runtime import run_creative_research_pilot_task

        result = asyncio.run(run_creative_research_pilot_task(_task_payload()))

        spans = exporter.get_finished_spans()
        llm_spans = [
            span
            for span in spans
            if span.attributes.get(OPENINFERENCE_SPAN_KIND) == OPENINFERENCE_KIND_LLM
        ]
        assert result.summary.promote == 1
        assert llm_spans, "Expected an LLM span for the creative research pilot"

        llm_attrs = dict(llm_spans[-1].attributes)
        assert llm_attrs["pulseplate.feature_flags.creative_research_pilot"] is True
        assert llm_attrs["pulseplate.route_type"] == "internal"
        assert "Meal adherence under time scarcity" not in str(llm_attrs)
    finally:
        reset_tracing_for_tests()


def test_creative_research_timeout_finalizes_llm_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout path must still finalize the LLM span with bounded metadata."""

    exporter = InMemorySpanExporter()
    reset_tracing_for_tests()
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("PULSE_OBS_HMAC_KEY", "test-genai-hmac-key")
    install_test_exporter(exporter)

    try:
        provider = _StaticProvider(_valid_provider_payload())
        monkeypatch.setattr(
            "app.services.creative_research_runtime._persist_privileged_action_audit",
            lambda **_: None,
        )
        monkeypatch.setattr(
            "app.services.creative_research_runtime.attempt_consume_llm_monthly_quota",
            lambda *args, **kwargs: True,
        )
        monkeypatch.setattr("llm.get_provider", lambda: provider)

        async def _timeout(_awaitable: object, *, timeout: float) -> object:
            del timeout
            raise asyncio.TimeoutError

        monkeypatch.setattr("app.services.creative_research_runtime.asyncio.wait_for", _timeout)

        from app.services.creative_research_runtime import run_creative_research_pilot_task

        with pytest.raises(Exception) as exc_info:
            asyncio.run(run_creative_research_pilot_task(_task_payload()))

        assert getattr(exc_info.value, "status_code", None) == 504

        spans = exporter.get_finished_spans()
        llm_spans = [
            span
            for span in spans
            if span.attributes.get(OPENINFERENCE_SPAN_KIND) == OPENINFERENCE_KIND_LLM
        ]
        assert llm_spans, "Expected an LLM span even when the provider times out"

        llm_attrs = dict(llm_spans[-1].attributes)
        assert llm_attrs["gen_ai.usage.output_tokens"] == 0
        assert llm_attrs["pulseplate.feature_flags.creative_research_pilot"] is True
    finally:
        reset_tracing_for_tests()
