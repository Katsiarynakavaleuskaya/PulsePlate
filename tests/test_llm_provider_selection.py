"""Coverage tests for llm.get_provider branch logic."""

from __future__ import annotations

from typing import Any

import llm


def _clear_provider_env(monkeypatch) -> None:
    keys = [
        "LLM_PROVIDER",
        "LLMFLOW_ENDPOINT",
        "LLMFLOW_FLOW_ID",
        "LLMFLOW_API_KEY",
        "LLMFLOW_TIMEOUT",
        "LLMFLOW_INPUT_KEY",
        "LLMFLOW_OUTPUT_KEY",
        "GROK_API_KEY",
        "GROK_MODEL",
        "GROK_ENDPOINT",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


class _DummyProvider:
    """Minimal async provider used for instrumentation."""

    name = "dummy"

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    async def generate(self, text: str) -> str:
        return text.upper()


def test_get_provider_llmflow_branch(monkeypatch) -> None:
    """LLMFlow selection wires env configuration into the provider."""
    _clear_provider_env(monkeypatch)

    captured: dict[str, Any] = {}

    class _CapturingProvider(_DummyProvider):
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(llm, "LLMFlowProvider", _CapturingProvider)

    monkeypatch.setenv("LLM_PROVIDER", "llmflow")
    monkeypatch.setenv("LLMFLOW_ENDPOINT", "http://flow.local")
    monkeypatch.setenv("LLMFLOW_FLOW_ID", "weekly-insight")
    monkeypatch.setenv("LLMFLOW_API_KEY", "  secret-key  ")
    monkeypatch.setenv("LLMFLOW_TIMEOUT", "7.5")
    monkeypatch.setenv("LLMFLOW_INPUT_KEY", "   prompt_override  ")
    monkeypatch.setenv("LLMFLOW_OUTPUT_KEY", "   ")  # should be treated as None

    provider = llm.get_provider()
    assert isinstance(provider, _CapturingProvider)
    assert captured == {
        "endpoint": "http://flow.local",
        "flow_id": "weekly-insight",
        "api_key": "secret-key",
        "timeout": 7.5,
        "input_key": "prompt_override",
        "output_key": None,
    }


def test_get_provider_llmflow_invalid_timeout(monkeypatch) -> None:
    """Invalid timeout falls back to default 15 seconds."""
    _clear_provider_env(monkeypatch)

    class _AlwaysProvider(_DummyProvider):
        def __init__(self, **kwargs: Any) -> None:
            self.received = kwargs

    monkeypatch.setattr(llm, "LLMFlowProvider", _AlwaysProvider)

    monkeypatch.setenv("LLM_PROVIDER", "flow")
    monkeypatch.setenv("LLMFLOW_FLOW_ID", "demo")
    monkeypatch.setenv("LLMFLOW_TIMEOUT", "not-a-number")

    provider = llm.get_provider()
    assert isinstance(provider, _AlwaysProvider)
    assert provider.received["timeout"] == 15.0


def test_get_provider_llmflow_missing_flow(monkeypatch) -> None:
    """Without flow id, provider selection returns None."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setattr(llm, "LLMFlowProvider", _DummyProvider)

    monkeypatch.setenv("LLM_PROVIDER", "llmflow")
    monkeypatch.delenv("LLMFLOW_FLOW_ID", raising=False)

    assert llm.get_provider() is None


def test_get_provider_grok_without_key(monkeypatch) -> None:
    """When GROK provider lacks API key the lite fallback is used."""
    _clear_provider_env(monkeypatch)

    class _FakeGrok:
        name = "grok"

        def __init__(self, *args, **kwargs):
            raise AssertionError("should not instantiate real Grok provider")

    monkeypatch.setattr(llm, "GrokProvider", _FakeGrok)
    monkeypatch.setenv("LLM_PROVIDER", "grok")
    monkeypatch.delenv("GROK_API_KEY", raising=False)

    provider = llm.get_provider()
    assert isinstance(provider, llm.GrokLiteProvider)


def test_get_provider_unknown(monkeypatch) -> None:
    """Unknown identifiers result in None provider."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "unknown-provider")
    assert llm.get_provider() is None
