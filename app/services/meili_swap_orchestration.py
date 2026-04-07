"""Offline Meilisearch foods index build / validate / warm / swap orchestration.

RU: Оркестрация zero-downtime смены индекса через Meilisearch swap-indexes.
EN: Zero-downtime index cutover orchestration using Meilisearch swap-indexes API.

Uses a dedicated ``httpx.Client`` (not the FastAPI-pooled Meili client) so CLI and
tests can run without app lifespan and can inject ``httpx.MockTransport``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Mapping, Sequence
from itertools import chain
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.food_search_indexing import build_swap_indexes_payload
from app.services.search_meili import (
    build_meili_foods_search_payload,
    build_meili_foods_search_url,
)

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_SIZE = 500
_DEFAULT_WARM_QUERIES = ("", "a", "rice")
_TASK_POLL_INTERVAL_SEC = 0.2
_TASK_TIMEOUT_SEC = 600.0


@dataclass(frozen=True)
class MeiliSwapConfig:
    """Configuration for swap orchestration (primary = live UID, candidate = build target)."""

    base_url: str
    primary_index: str
    candidate_index: str
    api_key: str | None
    timeout_seconds: float


def ensure_distinct_primary_and_candidate(cfg: MeiliSwapConfig) -> None:
    """Fail fast when primary and candidate UIDs are equal (misconfiguration)."""

    primary = (cfg.primary_index or "").strip()
    candidate = (cfg.candidate_index or "").strip()
    if not primary or not candidate:
        raise ValueError("primary_index and candidate_index must be non-empty")
    if primary == candidate:
        raise ValueError(
            "Meili swap misconfiguration: primary_index and candidate_index must differ "
            f"(both {primary!r})"
        )


def _meili_unreachable_message(meili_url: str) -> str:
    """Human-safe hint without secrets (API key must never appear here)."""

    return (
        f"Meilisearch unreachable or timed out (MEILI_URL={meili_url!r}). "
        "Check network, firewall, and that the Meilisearch process is healthy."
    )


class MeiliSwapOrchestrator:
    """HTTP orchestration against Meilisearch admin/task/search endpoints."""

    def __init__(
        self,
        cfg: MeiliSwapConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._cfg = cfg
        self._owns_client = client is None
        timeout = httpx.Timeout(cfg.timeout_seconds)
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the underlying HTTP client when this orchestrator owns it."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> MeiliSwapOrchestrator:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _root(self) -> str:
        return self._cfg.base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        # Mirror ``build_meili_foods_search_headers`` (``app/services/search_meili.py``) so
        # pre-push mypy with ``--follow-imports=skip`` does not widen this to ``Any``.
        cleaned = (self._cfg.api_key or "").strip()
        if not cleaned:
            return {}
        return {"Authorization": f"Bearer {cleaned}"}

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
    ) -> Any:
        url = f"{self._root()}{path}"
        try:
            response = self._client.request(
                method,
                url,
                json=json_body,
                headers=self._headers(),
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return response.json()
        except httpx.ConnectError as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.HTTPError:
            raise

    def _request_ignore_404(self, method: str, path: str) -> bool:
        """Return True if the request succeeded; False if Meilisearch returned 404."""

        url = f"{self._root()}{path}"
        try:
            response = self._client.request(method, url, headers=self._headers())
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except httpx.ConnectError as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.HTTPError:
            raise

    def delete_index_if_exists(self, index_uid: str) -> bool:
        """Delete index UID when present; return whether a delete was issued.

        Meilisearch enqueues index deletion as an async task; we wait for it before
        callers recreate the same UID (avoids index_already_exists races).
        """

        path = f"/indexes/{index_uid}"
        url = f"{self._root()}{path}"
        try:
            response = self._client.request("DELETE", url, headers=self._headers())
        except httpx.ConnectError as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.HTTPError:
            raise
        if response.status_code == 404:
            return False
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            logger.info("Meili index delete completed uid=%s (no task body)", index_uid)
            return True
        payload: Any = response.json()
        if isinstance(payload, dict) and "taskUid" in payload:
            self._wait_for_task(int(payload["taskUid"]))
        return True

    def create_index(self, index_uid: str, *, primary_key: str = "id") -> None:
        """Create a new index with the given primary key."""

        ensure_distinct_primary_and_candidate(self._cfg)
        task = self._request_json(
            "POST",
            "/indexes",
            json_body={"uid": index_uid, "primaryKey": primary_key},
        )
        if not isinstance(task, dict) or "taskUid" not in task:
            raise RuntimeError(f"Unexpected index create response: {task!r}")
        self._wait_for_task(int(task["taskUid"]))
        logger.info("Meili index created uid=%s primary_key=%s", index_uid, primary_key)

    def _wait_for_task(self, task_uid: int) -> None:
        deadline = time.monotonic() + _TASK_TIMEOUT_SEC
        while time.monotonic() < deadline:
            payload = self._request_json("GET", f"/tasks/{task_uid}")
            if not isinstance(payload, dict):
                raise RuntimeError(f"Unexpected task payload for uid={task_uid}: {payload!r}")
            status = str(payload.get("status", ""))
            if status == "succeeded":
                return
            if status == "failed":
                err = payload.get("error")
                raise RuntimeError(f"Meilisearch task {task_uid} failed: {err!r}")
            time.sleep(_TASK_POLL_INTERVAL_SEC)
        raise TimeoutError(
            f"Meilisearch task {task_uid} did not finish within {_TASK_TIMEOUT_SEC}s"
        )

    def _post_document_batch_and_wait(self, index_uid: str, batch: list[Mapping[str, Any]]) -> None:
        path = f"/indexes/{index_uid}/documents"
        task = self._request_json("POST", path, json_body=list(batch))
        if not isinstance(task, dict) or "taskUid" not in task:
            raise RuntimeError(f"Unexpected document enqueue response: {task!r}")
        self._wait_for_task(int(task["taskUid"]))

    def get_index_document_count(self, index_uid: str) -> int:
        """Return numberOfDocuments from GET /indexes/{uid}/stats."""

        stats = self._request_json("GET", f"/indexes/{index_uid}/stats")
        if not isinstance(stats, dict):
            raise RuntimeError(f"Unexpected stats payload: {stats!r}")
        raw = stats.get("numberOfDocuments")
        if not isinstance(raw, int):
            raise RuntimeError(f"Unexpected numberOfDocuments in stats: {raw!r}")
        return raw

    def search_foods_index(
        self, index_uid: str, *, query: str, limit: int = 5
    ) -> Mapping[str, Any]:
        """Run a contract-shaped foods search against an arbitrary index UID."""

        ensure_distinct_primary_and_candidate(self._cfg)
        url = build_meili_foods_search_url(self._root(), index_uid)
        headers = self._headers()
        body = build_meili_foods_search_payload(
            query=query,
            limit=limit,
            offset=0,
            show_performance_details=False,
        )
        try:
            response = self._client.post(url, json=body, headers=headers)
            response.raise_for_status()
            parsed: Any = response.json()
        except httpx.ConnectError as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(_meili_unreachable_message(self._cfg.base_url)) from exc
        except httpx.HTTPError:
            raise
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Unexpected search response: {parsed!r}")
        return parsed

    def perform_index_swap(self) -> None:
        """Swap primary and candidate index UIDs in Meilisearch (atomic on server)."""

        ensure_distinct_primary_and_candidate(self._cfg)
        payload = build_swap_indexes_payload(
            [(self._cfg.primary_index, self._cfg.candidate_index)],
        )
        task = self._request_json("POST", "/swap-indexes", json_body=payload)
        if not isinstance(task, dict) or "taskUid" not in task:
            raise RuntimeError(f"Unexpected swap-indexes response: {task!r}")
        self._wait_for_task(int(task["taskUid"]))
        logger.info(
            "Meili swap-indexes completed primary=%s candidate=%s",
            self._cfg.primary_index,
            self._cfg.candidate_index,
        )

    def orchestrate_build(
        self,
        documents: Iterable[Mapping[str, Any]],
        *,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        recreate_candidate: bool = True,
    ) -> int:
        """Create candidate index and bulk-load documents; return documents indexed."""

        ensure_distinct_primary_and_candidate(self._cfg)
        candidate = self._cfg.candidate_index
        if recreate_candidate:
            self.delete_index_if_exists(candidate)
            self.create_index(candidate)
        batch: list[Mapping[str, Any]] = []
        total = 0
        for doc in documents:
            batch.append(doc)
            if len(batch) >= batch_size:
                self._post_document_batch_and_wait(candidate, batch)
                total += len(batch)
                batch = []
        if batch:
            self._post_document_batch_and_wait(candidate, batch)
            total += len(batch)
        logger.info("Meili candidate build finished uid=%s documents=%s", candidate, total)
        return total

    def orchestrate_validate(self, *, expected_documents: int | None = None) -> int:
        """Validate candidate index stats (and optional expected document count)."""

        ensure_distinct_primary_and_candidate(self._cfg)
        count = self.get_index_document_count(self._cfg.candidate_index)
        if expected_documents is not None and count != expected_documents:
            raise RuntimeError(
                f"Candidate document count mismatch: got {count}, expected {expected_documents}"
            )
        logger.info(
            "Meili candidate validate ok uid=%s numberOfDocuments=%s",
            self._cfg.candidate_index,
            count,
        )
        return count

    def orchestrate_warm(self, queries: Sequence[str] | None = None) -> None:
        """Issue lightweight search traffic against the candidate index."""

        ensure_distinct_primary_and_candidate(self._cfg)
        warm_queries = tuple(queries) if queries is not None else _DEFAULT_WARM_QUERIES
        for q in warm_queries:
            self.search_foods_index(self._cfg.candidate_index, query=q, limit=3)
        logger.info(
            "Meili candidate warm finished uid=%s queries=%s",
            self._cfg.candidate_index,
            warm_queries,
        )

    def run_full_pipeline(
        self,
        documents: Iterable[Mapping[str, Any]],
        *,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        recreate_candidate: bool = True,
        warm_queries: Sequence[str] | None = None,
        skip_swap: bool = False,
        allow_empty_swap: bool = False,
    ) -> None:
        """build → validate → warm → optional swap."""

        ensure_distinct_primary_and_candidate(self._cfg)
        iterator = iter(documents)
        first = next(iterator, None)
        if first is None:
            if not skip_swap and not allow_empty_swap:
                raise ValueError(
                    "Refusing full pipeline swap with an empty document set "
                    "(set skip_swap=True or allow_empty_swap=True for advanced recovery flows)"
                )
            doc_iter: Iterable[Mapping[str, Any]] = ()
        else:
            doc_iter = chain((first,), iterator)
        indexed = self.orchestrate_build(
            doc_iter,
            batch_size=batch_size,
            recreate_candidate=recreate_candidate,
        )
        self.orchestrate_validate(expected_documents=indexed if first is not None else None)
        if first is not None:
            self.orchestrate_warm(queries=warm_queries)
        if not skip_swap:
            self.perform_index_swap()
