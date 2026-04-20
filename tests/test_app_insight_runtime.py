"""Unit tests for app-layer insight runtime tracing adapters."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.insight_runtime import TracedInsightProvider


@pytest.mark.asyncio
async def test_traced_provider_updates_span_provider_name_after_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback winner must be reflected in tracing metadata and wrapper identity."""

    observed_attrs: dict[str, Any] = {}

    @contextmanager
    def _fake_llm_span(**_kwargs: object) -> Any:
        yield SimpleNamespace()

    async def _generate(_text: str) -> str:
        return "fallback response"

    provider = SimpleNamespace(
        name="perplexity",
        active_provider_name="stub",
        generate=_generate,
    )

    monkeypatch.setattr("app.services.insight_runtime.llm_span", _fake_llm_span, raising=True)
    monkeypatch.setattr(
        "app.services.insight_runtime.set_attributes",
        lambda _span, **attrs: observed_attrs.update(attrs),
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_runtime.finalize_llm_span",
        lambda _span, _result: None,
        raising=True,
    )

    traced = TracedInsightProvider(provider, user_tier="VIP", route="/api/v1/insight")

    result = await traced.generate("hello")

    assert result == "fallback response"
    assert traced.name == "stub"
    assert observed_attrs["gen_ai.provider.name"] == "stub"
