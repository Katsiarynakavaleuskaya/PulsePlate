"""Optional Meilisearch-backed search adapters with safe fallbacks."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Mapping, Sequence, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.services.food_store import FoodSearchBackend

logger = logging.getLogger(__name__)

Transport = Callable[[str, dict[str, Any], Mapping[str, str], float], dict[str, Any]]


def _numeric_field_or_default(hit: Mapping[str, Any], key: str) -> int | float:
    """Normalize optional numeric nutrient fields to deterministic defaults."""

    value = hit.get(key)
    if isinstance(value, bool):
        return 0
    return value if isinstance(value, (int, float)) else 0


def _default_transport(
    url: str,
    payload: dict[str, Any],
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Execute a POST request against Meilisearch."""

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(url, json=payload, headers=dict(headers))
        response.raise_for_status()
        parsed_response: dict[str, Any]
        parsed_response = response.json()
        return parsed_response


class MeiliSearchBackend:
    """Optional Meilisearch backend preserving the food-search contract."""

    def __init__(
        self,
        *,
        base_url: str,
        index_name: str,
        api_key: str | None = None,
        timeout_seconds: float = 2.0,
        transport: Transport = _default_transport,
        fallback_backend: "FoodSearchBackend | None" = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._index_name = index_name
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._fallback_backend = fallback_backend

    def search_foods(
        self,
        query: str,
        limit: int | str = 20,
        offset: int | str = 0,
    ) -> Sequence[Mapping[str, Any]]:
        """Query Meilisearch and normalize hits to food contract fields."""

        try:
            normalized_limit = int(limit)
            normalized_offset = int(offset)
        except (TypeError, ValueError) as exc:
            raise ValueError("limit and offset must be integers") from exc

        search_url = f"{self._base_url}/indexes/{self._index_name}/search"
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "q": query,
            "limit": normalized_limit,
            "offset": normalized_offset,
            "attributesToRetrieve": [
                "id",
                "canonical_name",
                "name",
                "kcal",
                "protein_g",
                "fat_g",
                "carbs_g",
                "source",
                "content_hash",
            ],
        }
        try:
            response = self._transport(search_url, payload, headers, self._timeout_seconds)
        except (
            httpx.HTTPError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ):
            logger.warning(
                "Meilisearch request failed; falling back to baseline backend", exc_info=True
            )
            if self._fallback_backend is not None:
                fallback_rows: Sequence[Mapping[str, Any]] = self._fallback_backend.search_foods(
                    query, limit=normalized_limit, offset=normalized_offset
                )
                return fallback_rows
            return []

        hits = response.get("hits", [])
        if not isinstance(hits, list):
            logger.warning("Meilisearch response missing hits list")
            return []

        normalized_hits: list[Mapping[str, Any]] = []
        for hit in hits:
            if not isinstance(hit, Mapping):
                continue
            normalized_hits.append(
                {
                    "id": hit.get("id"),
                    "canonical_name": hit.get("canonical_name") or hit.get("name"),
                    "kcal": _numeric_field_or_default(hit, "kcal"),
                    "protein_g": _numeric_field_or_default(hit, "protein_g"),
                    "fat_g": _numeric_field_or_default(hit, "fat_g"),
                    "carbs_g": _numeric_field_or_default(hit, "carbs_g"),
                    "source": hit.get("source"),
                    "content_hash": hit.get("content_hash"),
                }
            )
        return normalized_hits


class ShadowSearchBackend:
    """Return baseline results while running a best-effort shadow query."""

    def __init__(
        self,
        *,
        baseline_backend: "FoodSearchBackend",
        shadow_backend: "FoodSearchBackend",
    ) -> None:
        self._baseline_backend = baseline_backend
        self._shadow_backend = shadow_backend

    def search_foods(
        self,
        query: str,
        limit: int | str = 20,
        offset: int | str = 0,
    ) -> Sequence[Mapping[str, Any]]:
        """Serve baseline results and record shadow divergence in logs."""

        baseline_rows = list(self._baseline_backend.search_foods(query, limit=limit, offset=offset))
        try:
            shadow_rows = list(self._shadow_backend.search_foods(query, limit=limit, offset=offset))
            baseline_ids = [str(row.get("id")) for row in baseline_rows]
            shadow_ids = [str(row.get("id")) for row in shadow_rows]
            if baseline_ids != shadow_ids:
                logger.info(
                    "Food search shadow divergence detected",
                    extra={
                        "query": query,
                        "baseline_ids": baseline_ids,
                        "shadow_ids": shadow_ids,
                    },
                )
        except Exception:
            logger.debug("Food search shadow query failed", exc_info=True)
        return baseline_rows
