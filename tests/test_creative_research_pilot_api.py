"""Tests for the internal creative research pilot route/runtime."""

from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest

from app.main import app
from app.schemas.creative_research import CreativeResearchPilotTaskEnvelope
from app.telemetry.genai import OPENINFERENCE_KIND_LLM, OPENINFERENCE_SPAN_KIND
from app.telemetry.setup import install_test_exporter, reset_tracing_for_tests

API_KEY_HEADERS = {"X-API-Key": "test_vip_key"}
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


def _json_body(response: object) -> dict[str, object]:
    return json.loads(getattr(response, "text"))


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


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_creative_research_route_is_hidden_from_openapi() -> None:
    """The pilot route must stay registered at runtime but hidden from public schema."""

    runtime_routes = {
        str(getattr(route, "path", "")): getattr(route, "include_in_schema", True)
        for route in app.routes
    }

    assert ROUTE_PATH in runtime_routes
    assert runtime_routes[ROUTE_PATH] is False
    assert ROUTE_PATH not in app.openapi().get("paths", {})


def test_creative_research_feature_flag_disabled_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabled pilot must fail closed before runtime work."""

    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "false")

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "meal adherence", "candidate_count": 2},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "FEATURE_CREATIVE_RESEARCH_PILOT is disabled"}


def test_creative_research_execution_mode_review_required_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review-required mode must block the internal pilot."""

    monkeypatch.setenv("FEATURE_CREATIVE_RESEARCH_PILOT", "true")
    monkeypatch.setenv("CREATIVE_RESEARCH_EXECUTION_MODE", "review-required")

    response = client.post(
        ROUTE_PATH,
        json={"prompt_seed": "meal adherence", "candidate_count": 2},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "agent_execution_review_required"}


def test_creative_research_success_returns_evaluated_candidates(
    client: TestClient,
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
        headers=API_KEY_HEADERS,
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
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 429
    assert _json_body(response) == {"detail": "quota_exceeded"}


def test_creative_research_invalid_provider_payload_returns_503(
    client: TestClient,
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
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "creative_research_provider_invalid_response"}


def test_creative_research_service_emits_minimized_llm_tracing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracing must capture only allowlisted metadata for the pilot."""

    exporter = InMemorySpanExporter()
    reset_tracing_for_tests()
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("PULSE_OBS_HMAC_KEY", "test-genai-hmac-key")
    install_test_exporter(exporter)

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

    task = CreativeResearchPilotTaskEnvelope.model_validate(
        {
            "mode": "auto-safe",
            "input": {
                "prompt_seed": "Meal adherence under time scarcity",
                "reference_corpus": ["Missed dinners increase friction."],
                "candidate_count": 2,
                "api_key": API_KEY_HEADERS["X-API-Key"],
                "endpoint": ROUTE_PATH,
                "method": "POST",
            },
        }
    )

    from app.services.creative_research_runtime import run_creative_research_pilot_task

    result = asyncio.run(run_creative_research_pilot_task(task))

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

    reset_tracing_for_tests()
