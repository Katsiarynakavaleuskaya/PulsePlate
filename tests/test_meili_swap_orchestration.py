"""Tests for Meili zero-downtime swap orchestration (httpx.MockTransport)."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from app.services.meili_swap_orchestration import (
    MeiliSwapConfig,
    MeiliSwapOrchestrator,
    ensure_distinct_primary_and_candidate,
)


def _cfg(
    *,
    primary: str = "foods",
    candidate: str = "foods_v2",
    base: str = "http://meili.test",
) -> MeiliSwapConfig:
    return MeiliSwapConfig(
        base_url=base,
        primary_index=primary,
        candidate_index=candidate,
        api_key=None,
        timeout_seconds=5.0,
    )


def test_ensure_distinct_rejects_equal_uids() -> None:
    cfg = _cfg(primary="foods", candidate="foods")
    with pytest.raises(ValueError, match="must differ"):
        ensure_distinct_primary_and_candidate(cfg)


def test_ensure_distinct_rejects_empty() -> None:
    cfg = _cfg(primary="", candidate="foods_v2")
    with pytest.raises(ValueError, match="non-empty"):
        ensure_distinct_primary_and_candidate(cfg)


def test_connect_error_wraps_safe_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope", request=request)

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(RuntimeError, match="MEILI_URL="):
            orch.get_index_document_count("foods_v2")


def test_timeout_wraps_safe_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(RuntimeError, match="MEILI_URL="):
            orch.get_index_document_count("foods_v2")


def test_perform_index_swap_waits_for_task() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path == "/swap-indexes":
            return httpx.Response(202, json={"taskUid": 42})
        if request.method == "GET" and request.url.path == "/tasks/42":
            if calls.count("GET /tasks/42") < 2:
                return httpx.Response(200, json={"status": "enqueued"})
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(404, json={"message": "unexpected"})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        orch.perform_index_swap()
    assert "POST /swap-indexes" in calls
    assert calls.count("GET /tasks/42") >= 2


def test_orchestrate_build_batches() -> None:
    next_task = 1

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal next_task
        if request.method == "DELETE" and request.url.path == "/indexes/foods_v2":
            return httpx.Response(404, json={})
        if request.method == "POST" and request.url.path == "/indexes":
            return httpx.Response(202, json={"taskUid": 50})
        if request.method == "GET" and request.url.path == "/tasks/50":
            return httpx.Response(200, json={"status": "succeeded"})
        if request.method == "POST" and request.url.path.endswith("/documents"):
            body = json.loads(request.content.decode("utf-8"))
            assert isinstance(body, list)
            uid = next_task
            next_task += 1
            return httpx.Response(202, json={"taskUid": uid})
        if request.method == "GET" and request.url.path.startswith("/tasks/"):
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(404, json={"message": str(request.url)})

    transport = httpx.MockTransport(handler)
    docs = [{"id": str(i)} for i in range(3)]
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        n = orch.orchestrate_build(iter(docs), batch_size=2, recreate_candidate=True)
    assert n == 3


def test_run_full_pipeline_empty_requires_flag() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(404, json={}))
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(ValueError, match="empty document"):
            orch.run_full_pipeline([], skip_swap=False)


def test_run_full_pipeline_empty_skip_swap_ok() -> None:
    """Empty docs + skip_swap: validate with no expected count; no swap HTTP."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/indexes/foods_v2/stats":
            return httpx.Response(200, json={"numberOfDocuments": 0})
        return httpx.Response(500, json={"message": "unexpected"})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        orch.run_full_pipeline([], skip_swap=True, recreate_candidate=False)


def test_orchestrate_validate_mismatch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/indexes/foods_v2/stats":
            return httpx.Response(200, json={"numberOfDocuments": 2})
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(RuntimeError, match="mismatch"):
            orch.orchestrate_validate(expected_documents=99)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            lambda: httpx.ConnectError("x", request=httpx.Request("GET", "http://x")), id="connect"
        ),
        pytest.param(
            lambda: httpx.TimeoutException("x", request=httpx.Request("GET", "http://x")),
            id="timeout",
        ),
    ],
)
def test_search_foods_index_network_errors(factory: Callable[[], Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise factory()

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(RuntimeError, match="MEILI_URL="):
            orch.search_foods_index("foods_v2", query="rice")


def test_delete_index_if_exists_404_returns_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        assert orch.delete_index_if_exists("missing") is False


def test_delete_index_if_exists_waits_for_task() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "DELETE" and request.url.path == "/indexes/foods_v2":
            return httpx.Response(202, json={"taskUid": 99})
        if request.method == "GET" and request.url.path == "/tasks/99":
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(404, json={"message": "unexpected"})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        assert orch.delete_index_if_exists("foods_v2") is True
    assert "DELETE /indexes/foods_v2" in calls
    assert "GET /tasks/99" in calls


def test_wait_for_task_failed_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/swap-indexes":
            return httpx.Response(202, json={"taskUid": 7})
        if request.url.path == "/tasks/7":
            return httpx.Response(200, json={"status": "failed", "error": {"type": "bad"}})
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(RuntimeError, match="task 7 failed"):
            orch.perform_index_swap()


def test_http_error_after_connect_not_wrapped_as_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "internal"})

    transport = httpx.MockTransport(handler)
    with MeiliSwapOrchestrator(_cfg(), client=httpx.Client(transport=transport)) as orch:
        with pytest.raises(httpx.HTTPStatusError):
            orch.get_index_document_count("foods_v2")
