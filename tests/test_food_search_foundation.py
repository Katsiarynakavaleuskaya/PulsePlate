from __future__ import annotations

from fastapi import FastAPI
import pytest

from app.bootstrap.food_search import register_food_search_backend
from app.services import food_store
from app.services.food_search_indexing import (
    build_swap_indexes_payload,
    content_hash,
    diff_emit,
)
from app.services.search_meili import MeiliSearchBackend, ShadowSearchBackend


def test_meili_backend_falls_back_to_legacy_on_transport_error() -> None:
    class _FallbackBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            self.calls.append((query, int(limit), int(offset)))
            return [{"id": "legacy"}]

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: (_ for _ in ()).throw(TimeoutError("boom")),
        fallback_backend=_FallbackBackend(),
    )

    rows = backend.search_foods("apple", limit=3, offset=1)

    assert rows == [{"id": "legacy"}]


def test_shadow_backend_returns_baseline_when_shadow_diverges() -> None:
    class _Baseline:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "baseline"}]

    class _Shadow:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "shadow"}]

    backend = ShadowSearchBackend(baseline_backend=_Baseline(), shadow_backend=_Shadow())

    assert backend.search_foods("banana") == [{"id": "baseline"}]


def test_strategy_backend_prefers_registered_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    class _StrategyBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "meili"}]

    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    food_store.register_strategy_search_backend_adapter(_StrategyBackend())
    try:
        assert food_store.get_search_backend().search_foods("yogurt") == [{"id": "meili"}]
    finally:
        food_store.reset_strategy_search_backend_adapter()
        monkeypatch.delenv("FOOD_SEARCH_BACKEND_STRATEGY", raising=False)


def test_search_backend_strategy_invalid_value_falls_back_to_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "unsupported-shadow-mode")

    assert food_store.get_search_backend_strategy() == "baseline_fts"


def test_get_legacy_search_backend_exposes_legacy_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
    monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)
    monkeypatch.delenv("FOOD_SEARCH_BACKEND_STRATEGY", raising=False)
    food_store.reset_search_backend_adapter()
    food_store.reset_strategy_search_backend_adapter()
    food_store.reset_semantic_search_backend_adapter()

    assert food_store.get_legacy_search_backend() is food_store.get_search_backend()


def test_register_food_search_backend_falls_back_to_baseline_without_meili_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "hybrid_shadow")
    monkeypatch.delenv("MEILI_URL", raising=False)

    register_food_search_backend(app)

    assert app.state.food_search_strategy == "baseline_fts"


def test_content_hash_is_stable_for_semantically_equal_documents() -> None:
    first = {"id": "1", "aliases": ["banana", "apple"], "source": "usda"}
    second = {"source": "usda", "aliases": ["apple", "banana"], "id": "1"}

    assert content_hash(first) == content_hash(second)


def test_diff_emit_returns_only_changed_documents() -> None:
    documents = [
        {"id": "1", "canonical_name": "Apple", "aliases": ["apple"]},
        {"id": "2", "canonical_name": "Banana", "aliases": ["banana"]},
    ]
    cache = {"1": content_hash(documents[0])}

    changed = diff_emit(documents, cache)

    assert changed == [
        {
            "id": "2",
            "canonical_name": "Banana",
            "aliases": ["banana"],
            "content_hash": content_hash(documents[1]),
        }
    ]


def test_build_swap_indexes_payload_is_atomic_pair_list() -> None:
    assert build_swap_indexes_payload([("foods", "foods_v2"), ("recipes", "recipes_v2")]) == [
        {"indexes": ["foods", "foods_v2"]},
        {"indexes": ["recipes", "recipes_v2"]},
    ]
