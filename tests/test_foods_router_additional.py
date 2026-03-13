from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from app.routers import foods
from app.schemas.food import FoodHit, FoodItem


def _build_food_item_payload(flags: Any) -> dict[str, Any]:
    return {
        "id": "f1",
        "canonical_name": "Apple",
        "kcal": 52,
        "protein_g": 0.3,
        "fat_g": 0.2,
        "carbs_g": 14,
        "flags": flags,
        "version_date": "2024-01-01",
    }


@pytest.mark.parametrize(
    ("raw_flags", "expected"),
    [
        ('["VEG","GF"]', ["VEG", "GF"]),
        ("['VEG', 'GF']", ["VEG", "GF"]),
        ("VEG, GF", ["VEG", "GF"]),
        ("VEG;GF", ["VEG", "GF"]),
        ("VEG|GF", ["VEG", "GF"]),
        ("VEG", ["VEG"]),
        (" null ", []),
        ("None", []),
        (["VEG", "GF"], ["VEG", "GF"]),
        (("VEG", "GF"), ["VEG", "GF"]),
        ({"VEG", "GF"}, {"VEG", "GF"}),
        ("", []),
        ("[]", []),
        (None, []),
        (123, []),
    ],
)
def test_food_item_flags_normalization(raw_flags: Any, expected: Any) -> None:
    item = FoodItem(**_build_food_item_payload(raw_flags))
    if isinstance(expected, set):
        assert set(item.flags) == expected
    else:
        assert item.flags == expected


def test_list_foods_invalid_limit() -> None:
    with pytest.raises(HTTPException):
        foods.list_foods(query="apple", limit=0, offset=0, store=foods.food_store)


def test_list_foods_success(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "id": "f1",
            "canonical_name": "Apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14,
        },
    ]

    monkeypatch.setattr(foods.food_store, "search_foods", lambda *args, **kwargs: rows)
    result = foods.list_foods(query="apple", limit=10, offset=0, store=foods.food_store)
    assert isinstance(result, list)
    assert isinstance(result[0], FoodHit)
    assert result[0].id == "f1"


def test_list_foods_search_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, tuple[Any, ...]] = {}

    def fake_list_foods(*args: Any, **kwargs: Any) -> list[FoodHit]:
        called["args"] = (args, kwargs)
        return [FoodHit(id="fX", name="X", kcal=1, protein_g=0, fat_g=0, carbs_g=0)]

    monkeypatch.setattr(foods, "list_foods", fake_list_foods)
    foods.list_foods_search(query="x", limit=5, offset=2, store=foods.food_store)
    assert called["args"][0] == ()
    assert called["args"][1] == {"query": "x", "limit": 5, "offset": 2, "store": foods.food_store}


def test_get_food_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(foods.food_store, "get_food", lambda *_: None)
    with pytest.raises(HTTPException) as exc:
        foods.get_food("missing", store=foods.food_store)
    assert exc.value.status_code == 404


def test_get_food_success(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "id": "f1",
        "canonical_name": "Apple",
        "kcal": 52,
        "protein_g": 0.3,
        "fat_g": 0.2,
        "carbs_g": 14,
        "version_date": "2024-01-01",
    }
    monkeypatch.setattr(foods.food_store, "get_food", lambda *_: row)
    result = foods.get_food("f1", store=foods.food_store)
    assert isinstance(result, FoodItem)
    assert result.id == "f1"


def test_get_food_by_barcode_success(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "id": "f1",
        "canonical_name": "Apple",
        "kcal": 52,
        "protein_g": 0.3,
        "fat_g": 0.2,
        "carbs_g": 14,
        "version_date": "2024-01-01",
    }
    monkeypatch.setattr(foods.food_store, "get_food_by_barcode", lambda *_: row)

    result = foods.get_food_by_barcode("0123456789012", store=foods.get_food_store())

    assert isinstance(result, FoodItem)
    assert result.id == "f1"


@pytest.mark.parametrize(
    "flags_value",
    ['["VEG","GF"]', "['VEG', 'GF']", "VEG,GF", "VEG;GF", "VEG|GF"],
)
def test_get_food_by_barcode_success_normalizes_string_flags(
    monkeypatch: pytest.MonkeyPatch,
    flags_value: str,
) -> None:
    row = {
        "id": "f1",
        "canonical_name": "Apple",
        "kcal": 52,
        "protein_g": 0.3,
        "fat_g": 0.2,
        "carbs_g": 14,
        "flags": flags_value,
        "version_date": "2024-01-01",
    }
    monkeypatch.setattr(foods.food_store, "get_food_by_barcode", lambda *_: row)

    result = foods.get_food_by_barcode("0123456789012", store=foods.get_food_store())

    assert isinstance(result, FoodItem)
    assert result.flags == ["VEG", "GF"]


def test_get_food_by_barcode_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(foods.food_store, "get_food_by_barcode", lambda *_: None)

    with pytest.raises(HTTPException) as exc:
        foods.get_food_by_barcode("0123456789012", store=foods.get_food_store())

    assert exc.value.status_code == 404


def test_get_food_by_barcode_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_invalid(_: str) -> None:
        raise ValueError("barcode must have length in [8,14]")

    monkeypatch.setattr(foods.food_store, "get_food_by_barcode", _raise_invalid)

    with pytest.raises(HTTPException) as exc:
        foods.get_food_by_barcode("123", store=foods.get_food_store())

    assert exc.value.status_code == 422
    assert exc.value.detail == foods.MALFORMED_BARCODE_DETAIL


def test_get_food_by_barcode_invalid_sanitizes_unexpected_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_invalid(_: str) -> None:
        raise ValueError("barcode secret path /tmp/off-cache.json")

    monkeypatch.setattr(foods.food_store, "get_food_by_barcode", _raise_invalid)

    with pytest.raises(HTTPException) as exc:
        foods.get_food_by_barcode("123", store=foods.get_food_store())

    assert exc.value.status_code == 422
    assert exc.value.detail == foods.MALFORMED_BARCODE_DETAIL
    assert "/tmp/off-cache.json" not in exc.value.detail


def test_get_food_by_barcode_route_documents_404() -> None:
    route = next(
        r
        for r in foods.router.routes
        if getattr(r, "path", "") == "/api/v1/foods/barcode/{barcode}"
    )
    assert 422 in route.responses
    assert 404 in route.responses


def test_list_foods_compat_backend_via_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    class _CompatBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def search_foods(
            self, query: str, limit: int = 20, offset: int = 0
        ) -> list[dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [
                {
                    "id": "compat-1",
                    "canonical_name": "Compat Apple",
                    "kcal": 77,
                    "protein_g": 1.0,
                    "fat_g": 0.5,
                    "carbs_g": 18.0,
                }
            ]

    compat_backend = _CompatBackend()
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", "true")
    foods.food_store.register_search_backend_adapter(compat_backend)
    try:
        store = foods.get_food_store()
        result = foods.list_foods(query="apple", limit=10, offset=0, store=store)
        assert result[0].id == "compat-1"
        assert compat_backend.calls == [("apple", 10, 0)]
    finally:
        foods.food_store.reset_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)


def test_list_foods_compat_flag_without_adapter_falls_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, tuple[Any, ...]] = {}

    def fake_legacy_search(query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        called["params"] = (query, limit, offset)
        return [
            {
                "id": "legacy-1",
                "canonical_name": "Legacy Apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
            }
        ]

    monkeypatch.setenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", "true")
    foods.food_store.reset_search_backend_adapter()
    monkeypatch.setattr(foods.food_store, "search_foods", fake_legacy_search)

    store = foods.get_food_store()
    result = foods.list_foods(query="apple", limit=10, offset=0, store=store)
    assert result[0].id == "legacy-1"
    assert called["params"] == ("apple", 10, 0)


def test_list_foods_semantic_flag_uses_semantic_backend_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CompatBackend:
        def search_foods(
            self, query: str, limit: int = 20, offset: int = 0
        ) -> list[dict[str, Any]]:
            return [
                {
                    "id": "compat-1",
                    "canonical_name": "Compat Apple",
                    "kcal": 88,
                    "protein_g": 1.0,
                    "fat_g": 0.2,
                    "carbs_g": 19.0,
                }
            ]

    class _SemanticBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def search_foods(
            self, query: str, limit: int = 20, offset: int = 0
        ) -> list[dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [
                {
                    "id": "semantic-1",
                    "canonical_name": "Semantic Apple",
                    "kcal": 66,
                    "protein_g": 0.7,
                    "fat_g": 0.1,
                    "carbs_g": 14.0,
                }
            ]

    semantic_backend = _SemanticBackend()
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", "true")
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", "true")
    foods.food_store.register_search_backend_adapter(_CompatBackend())
    foods.food_store.register_semantic_search_backend_adapter(semantic_backend)
    try:
        result = foods.list_foods(query="apple", limit=10, offset=0, store=foods.get_food_store())
        assert result[0].id == "semantic-1"
        assert semantic_backend.calls == [("apple", 10, 0)]
    finally:
        foods.food_store.reset_search_backend_adapter()
        foods.food_store.reset_semantic_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)


def test_list_foods_semantic_adapter_not_used_when_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _SemanticBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def search_foods(
            self, query: str, limit: int = 20, offset: int = 0
        ) -> list[dict[str, Any]]:
            self.calls.append((query, limit, offset))
            return [
                {
                    "id": "semantic-ignored",
                    "canonical_name": "Semantic Apple",
                    "kcal": 66,
                    "protein_g": 0.7,
                    "fat_g": 0.1,
                    "carbs_g": 14.0,
                }
            ]

    called: dict[str, tuple[str, int, int]] = {}

    def fake_legacy_search(query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        called["params"] = (query, limit, offset)
        return [
            {
                "id": "legacy-rollback",
                "canonical_name": "Legacy Apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
            }
        ]

    semantic_backend = _SemanticBackend()
    monkeypatch.setenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", "false")
    monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
    monkeypatch.setattr(foods.food_store, "search_foods", fake_legacy_search)
    foods.food_store.register_semantic_search_backend_adapter(semantic_backend)
    try:
        result = foods.list_foods(query="apple", limit=10, offset=0, store=foods.get_food_store())
        assert result[0].id == "legacy-rollback"
        assert called["params"] == ("apple", 10, 0)
        assert semantic_backend.calls == []
    finally:
        foods.food_store.reset_semantic_search_backend_adapter()
        monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)
