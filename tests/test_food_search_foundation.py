from __future__ import annotations

from fastapi import FastAPI
import httpx
import pytest

from app.bootstrap.food_search import (
    _safe_index_name,
    _safe_timeout_seconds,
    register_food_search_backend,
)
from app.services import food_store
from app.services.food_search_indexing import (
    build_swap_indexes_payload,
    canonicalize_food_document,
    content_hash,
    diff_emit,
)
from app.services.search_meili import (
    _default_transport,
    _numeric_field_or_default,
    MeiliSearchBackend,
    ShadowSearchBackend,
)


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


def test_meili_backend_validates_pagination_inputs() -> None:
    backend = MeiliSearchBackend(base_url="https://meili.example", index_name="foods")

    with pytest.raises(ValueError, match="limit and offset must be integers"):
        backend.search_foods("apple", limit="bad", offset=0)


def test_meili_backend_normalizes_missing_nutrient_fields() -> None:
    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: {
            "hits": [
                {
                    "id": "1",
                    "name": "Apple",
                    "source": "shadow",
                },
                "skip-me",
            ]
        },
    )

    rows = backend.search_foods("apple")

    assert rows == [
        {
            "id": "1",
            "canonical_name": "Apple",
            "kcal": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "source": "shadow",
            "content_hash": None,
        }
    ]


def test_meili_backend_returns_empty_when_hits_is_not_a_list() -> None:
    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: {"hits": "not-a-list"},
    )

    assert backend.search_foods("apple") == []


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


def test_shadow_backend_returns_baseline_when_shadow_raises() -> None:
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
            raise RuntimeError("shadow down")

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


def test_register_food_search_backend_registers_meili_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "https://meili.example")
    monkeypatch.setenv("MEILI_FOODS_INDEX", "   ")
    monkeypatch.setenv("MEILI_TIMEOUT_SECONDS", "bad-timeout")

    register_food_search_backend(app)

    assert app.state.food_search_strategy == "meili"
    backend = food_store.get_search_backend()
    assert isinstance(backend, MeiliSearchBackend)
    assert backend._index_name == "foods"
    assert backend._timeout_seconds == 2.0
    food_store.reset_strategy_search_backend_adapter()


def test_register_food_search_backend_registers_shadow_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "hybrid_shadow")
    monkeypatch.setenv("MEILI_URL", "https://meili.example")

    register_food_search_backend(app)

    assert app.state.food_search_strategy == "hybrid_shadow"
    assert isinstance(food_store.get_search_backend(), ShadowSearchBackend)
    food_store.reset_strategy_search_backend_adapter()


def test_safe_timeout_and_index_helpers_use_fallbacks() -> None:
    assert _safe_timeout_seconds(None) == 2.0
    assert _safe_timeout_seconds("0") == 2.0
    assert _safe_timeout_seconds("-1") == 2.0
    assert _safe_timeout_seconds("1.5") == 1.5
    assert _safe_index_name(None) == "foods"
    assert _safe_index_name("   ") == "foods"
    assert _safe_index_name("foods_v2") == "foods_v2"


def test_default_transport_posts_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object], dict[str, str], float]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"hits": []}

    class _Client:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(
            self,
            url: str,
            *,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> _Response:
            calls.append((url, json, headers, self.timeout))
            return _Response()

    monkeypatch.setattr(httpx, "Client", _Client)

    response = _default_transport(
        "https://meili.example/indexes/foods/search",
        {"q": "apple"},
        {"Authorization": "Bearer token"},
        1.25,
    )

    assert response == {"hits": []}
    assert calls == [
        (
            "https://meili.example/indexes/foods/search",
            {"q": "apple"},
            {"Authorization": "Bearer token"},
            1.25,
        )
    ]


def test_content_hash_is_stable_for_semantically_equal_documents() -> None:
    first = {"id": "1", "aliases": ["banana", "apple"], "source": "usda"}
    second = {"source": "usda", "aliases": ["apple", "banana"], "id": "1"}

    assert content_hash(first) == content_hash(second)


def test_canonicalize_food_document_ignores_existing_content_hash() -> None:
    document = {
        "id": "1",
        "aliases": ["banana", "apple"],
        "content_hash": "stale",
    }

    assert canonicalize_food_document(document) == {
        "aliases": ["apple", "banana"],
        "id": "1",
    }


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


def test_diff_emit_ignores_existing_content_hash_in_hash_input() -> None:
    document = {
        "id": "1",
        "canonical_name": "Apple",
        "aliases": ["apple"],
        "content_hash": "stale",
    }
    cache = {"1": content_hash(document)}

    assert diff_emit([document], cache) == []


def test_build_swap_indexes_payload_is_atomic_pair_list() -> None:
    assert build_swap_indexes_payload([("foods", "foods_v2"), ("recipes", "recipes_v2")]) == [
        {"indexes": ["foods", "foods_v2"]},
        {"indexes": ["recipes", "recipes_v2"]},
    ]


def test_numeric_field_or_default_returns_zero_for_missing_values() -> None:
    hit = {"protein_g": None, "fat_g": "bad", "carbs_g": 3, "kcal": True}

    assert _numeric_field_or_default(hit, "protein_g") == 0
    assert _numeric_field_or_default(hit, "fat_g") == 0
    assert _numeric_field_or_default(hit, "carbs_g") == 3
    assert _numeric_field_or_default(hit, "kcal") == 0
