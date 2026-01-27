import pytest
from fastapi.testclient import TestClient


def test_insight_legacy_does_not_leak_provider_exception(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure /insight never returns raw provider exception text."""

    import llm

    class FailingProvider:
        name = "test_provider"

        async def generate(self, text: str) -> str:
            raise RuntimeError("SENSITIVE: model=grok-4-latest path=/tmp/internal secret=abc")

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setattr(llm, "get_provider", lambda: FailingProvider(), raising=True)

    resp = client.post("/insight", json={"text": "hello"})
    assert resp.status_code == 503
    data = resp.json()
    assert "SENSITIVE" not in data.get("detail", "")
    assert "/tmp/internal" not in data.get("detail", "")


def test_insight_v1_does_not_leak_provider_exception(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure /api/v1/insight never returns raw provider exception text."""

    import llm

    class FailingProvider:
        name = "test_provider"

        async def generate(self, text: str) -> str:
            raise RuntimeError("SENSITIVE: model=grok-4-latest path=/tmp/internal secret=abc")

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setattr(llm, "get_provider", lambda: FailingProvider(), raising=True)

    resp = client.post(
        "/api/v1/insight",
        json={"text": "hello"},
        headers={"X-API-Key": "test_key"},
    )
    assert resp.status_code == 503
    data = resp.json()
    assert "SENSITIVE" not in data.get("detail", "")
    assert "/tmp/internal" not in data.get("detail", "")


def test_insight_redacts_rag_source_headers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure RAG context source lines are not forwarded to the LLM prompt."""

    import llm

    class EchoProvider:
        name = "echo"

        async def generate(self, text: str) -> str:
            return text

    def fake_retrieve_context(query: str, max_chunks: int = 3) -> str:
        # Simulate internal metadata that must NOT leak.
        return "# Source: secret.md (score=0.99)\n\nHELLO"

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")
    monkeypatch.setattr(llm, "get_provider", lambda: EchoProvider(), raising=True)
    monkeypatch.setattr(
        "core.rag.simple_rag.retrieve_context",
        fake_retrieve_context,
        raising=True,
    )

    resp = client.post("/insight", json={"text": "What is BMI?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "insight" in data
    assert "Source:" not in data["insight"]
    assert "secret.md" not in data["insight"]
