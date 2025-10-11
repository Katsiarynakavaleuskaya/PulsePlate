"""Tests for the optional LLMFlow provider adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from providers.llmflow import LLMFlowError, LLMFlowProvider


class _DummyResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str | None = None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text if text is not None else str(json_data)

    def json(self) -> Any:
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class _DummyClient:
    def __init__(
        self,
        response_factory: Callable[[], _DummyResponse],
        recorder: dict[str, Any] | None = None,
    ):
        self._response_factory = response_factory
        self._recorder = recorder

    async def __aenter__(self) -> _DummyClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args, **kwargs) -> _DummyResponse:
        if self._recorder is not None:
            self._recorder["args"] = args
            self._recorder["kwargs"] = kwargs
        return self._response_factory()


def _mock_async_client(
    monkeypatch: pytest.MonkeyPatch,
    response: _DummyResponse,
    recorder: dict[str, Any] | None = None,
) -> None:
    """Replace httpx.AsyncClient with a deterministic dummy."""

    def _factory(*args, **kwargs) -> _DummyClient:  # noqa: ANN202
        return _DummyClient(lambda: response, recorder=recorder)

    import httpx  # Local import to avoid polluting module scope

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_llmflow_requires_flow_id() -> None:
    """A missing flow_id must raise an error before performing HTTP requests."""
    provider = LLMFlowProvider(endpoint="http://localhost:8000", flow_id="")
    with pytest.raises(LLMFlowError, match="flow_id is required"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_llmflow_extracts_primary_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the configured output key is present it is returned."""
    response = _DummyResponse(json_data={"result": "  Hi there  "})
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(
        endpoint="http://localhost:8000",
        flow_id="demo",
        output_key="result",
    )
    text = await provider.generate("Hello")
    assert text == "Hi there"


@pytest.mark.asyncio
async def test_llmflow_uses_fallback_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI-style payloads should be parsed via choices -> message."""
    response = _DummyResponse(
        json_data={
            "choices": [
                {
                    "message": {"content": "  Greetings!  "},
                }
            ]
        }
    )
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(
        endpoint="http://localhost:8000",
        flow_id="demo",
        output_key=None,
    )
    text = await provider.generate("Hello")
    assert text == "Greetings!"


@pytest.mark.asyncio
async def test_llmflow_error_status_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP errors should surface as LLMFlowError with status code context."""
    response = _DummyResponse(status_code=500, text="boom")
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(endpoint="http://localhost:8000", flow_id="demo")
    with pytest.raises(LLMFlowError, match="LLMFlow error 500"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_llmflow_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid JSON responses must raise a descriptive error."""
    response = _DummyResponse(json_data=ValueError("not json"))
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(endpoint="http://localhost:8000", flow_id="demo")
    with pytest.raises(LLMFlowError, match="invalid JSON"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_llmflow_returns_stringified_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-dict payloads fall back to string representation."""
    response = _DummyResponse(json_data=["unstructured", "data"])
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(endpoint="http://localhost:8000", flow_id="demo")
    result = await provider.generate("Hello")
    assert result == "['unstructured', 'data']"


@pytest.mark.asyncio
async def test_llmflow_attaches_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Authorization header must be forwarded when api_key is provided."""
    recorder: dict[str, Any] = {}
    response = _DummyResponse(json_data={"result": "ok"})
    _mock_async_client(monkeypatch, response, recorder=recorder)

    provider = LLMFlowProvider(
        endpoint="http://localhost:8000",
        flow_id="demo",
        api_key="secret",
    )
    await provider.generate("Hello")
    assert recorder["kwargs"]["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_llmflow_fallback_text_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plain text keys should be stripped and returned."""
    response = _DummyResponse(json_data={"text": "  hello  "})
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(endpoint="http://localhost:8000", flow_id="demo", output_key=None)
    assert await provider.generate("Ping") == "hello"


@pytest.mark.asyncio
async def test_llmflow_choice_text_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure choices with direct text property are handled."""
    response = _DummyResponse(json_data={"choices": [{"text": "  reply  "}]})
    _mock_async_client(monkeypatch, response)

    provider = LLMFlowProvider(endpoint="http://localhost:8000", flow_id="demo", output_key=None)
    assert await provider.generate("Ping") == "reply"
