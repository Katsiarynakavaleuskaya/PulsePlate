"""Unit tests for the shared insight application service."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.services.insight_application_service import execute_insight_request
from core.ai.insight_runtime import InsightTransparencyNotice


@pytest.mark.asyncio
async def test_execute_insight_request_uses_injected_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service must preserve injected patch-points and response mapping."""

    observed: dict[str, object] = {}

    @dataclass
    class _Request:
        text: str

    def _input_guard(text: str) -> None:
        observed["guard_text"] = text

    def _provider_loader() -> object:
        observed["provider_loader_called"] = True
        return object()

    def _transparency_loader() -> tuple[str, str]:
        observed["transparency_loader_called"] = True
        return ("ai_generated_insight", "Wellness only.")

    def _response_factory(**payload: object) -> dict[str, object]:
        observed["response_payload"] = payload
        return dict(payload)

    def _source_item_factory(**payload: object) -> dict[str, object]:
        return dict(payload)

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=object(),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="fake-provider",
            source_dicts=[{"chunk_id": "c1", "file": "doc.md", "score": 0.9, "hop": 1}],
            confidence=0.9,
            rag_used=True,
            hops=1,
            latency_ms=12,
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=2,
                verification_rate=0.8,
                falsifiability_rate=0.7,
                contradiction_count=0,
                reason_codes=["legacy_path"],
                optimization_applied=False,
            ),
        )

    def _fake_prepare_insight_runtime(**kwargs: object) -> object:
        observed["prepare_kwargs"] = kwargs
        return prepared_runtime

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        _fake_prepare_insight_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=123,
        input_guard=_input_guard,
        provider_loader=_provider_loader,
        transparency_loader=_transparency_loader,
        response_factory=_response_factory,
        source_item_factory=_source_item_factory,
    )

    assert observed["guard_text"] == "hello"
    assert observed["prepare_kwargs"] == {
        "text": "hello",
        "use_rag": False,
        "philosophy_router_enabled": False,
        "philosophy_linguistic_enabled": False,
        "provider_loader": _provider_loader,
        "transparency_loader": _transparency_loader,
    }
    assert observed["generate_kwargs"]["subject_id"] == 123
    assert observed["generate_kwargs"]["route_path"] == "/api/v1/insight"
    assert response["provider"] == "fake-provider"
    assert response["transparency_notice_id"] == "ai_generated_insight"
    assert response["sources"][0]["chunk_id"] == "c1"
