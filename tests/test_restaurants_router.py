from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Sequence

import pytest
from fastapi import HTTPException

from app.routers import restaurants
from app.schemas.restaurants import (
    RestaurantSubmissionCreate,
    SubmissionReviewRequest,
    SubmissionStatus,
)


@dataclass
class _StubStore:
    search_rows: Sequence[Mapping[str, Any]] = field(default_factory=list)
    menu_rows: Sequence[Mapping[str, Any]] = field(default_factory=list)
    create_response: Mapping[str, Any] | None = None
    get_response: Mapping[str, Any] | None = None
    review_response: Mapping[str, Any] | None = None
    create_error: Exception | None = None
    review_error: Exception | None = None

    def search_restaurants(
        self, query: str, limit: int, offset: int
    ) -> Sequence[Mapping[str, Any]]:
        return self.search_rows

    def get_restaurant_menu(self, chain_id: str, limit: int) -> Sequence[Mapping[str, Any]]:
        return self.menu_rows

    def create_submission(
        self,
        *,
        canonical_name: str,
        payload: Dict[str, Any],
        barcode: str | None,
        off_url: str | None,
        entity_type: str,
    ) -> Mapping[str, Any]:
        if self.create_error is not None:
            raise self.create_error
        return self.create_response or {}

    def get_submission(self, submission_id: str) -> Mapping[str, Any] | None:
        return self.get_response

    def review_submission(
        self, submission_id: str, *, status: str, reviewer_notes: str | None
    ) -> Mapping[str, Any] | None:
        if self.review_error is not None:
            raise self.review_error
        return self.review_response


def test_search_restaurants_limit_validation() -> None:
    with pytest.raises(HTTPException) as exc:
        restaurants.search_restaurants(query="x", limit=0, offset=0, store=_StubStore())
    assert exc.value.status_code == 422
    assert exc.value.detail == "limit must be in [1,100]"


def test_get_restaurant_store_returns_singleton() -> None:
    assert restaurants.get_restaurant_store() is restaurants._STORE


def test_compat_wrapper_delegates_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    compat = restaurants._RestaurantStoreCompat()
    monkeypatch.setattr(
        restaurants.restaurant_store, "search_restaurants", lambda **_: [{"id": "c1"}]
    )
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "get_restaurant_menu",
        lambda **_: [{"id": "m1"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "create_submission",
        lambda **_: {"id": "s1"},
    )
    monkeypatch.setattr(restaurants.restaurant_store, "get_submission", lambda _sid: {"id": "s1"})
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "review_submission",
        lambda _sid, **_: {"id": "s1"},
    )

    assert list(compat.search_restaurants("q", 1, 0))[0]["id"] == "c1"
    assert list(compat.get_restaurant_menu("c1", 1))[0]["id"] == "m1"
    assert (
        compat.create_submission(
            canonical_name="X",
            payload={},
            barcode=None,
            off_url=None,
            entity_type="restaurant_menu",
        )["id"]
        == "s1"
    )
    assert compat.get_submission("s1")["id"] == "s1"
    assert compat.review_submission("s1", status="approved", reviewer_notes=None)["id"] == "s1"


def test_search_restaurants_maps_hits() -> None:
    store = _StubStore(
        search_rows=[{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}]
    )
    result = restaurants.search_restaurants(query="chain", limit=10, offset=0, store=store)
    assert len(result) == 1
    assert result[0].id == "c1"
    assert result[0].name == "Chain 1"


def test_get_restaurant_menu_not_found() -> None:
    with pytest.raises(HTTPException) as exc:
        restaurants.get_restaurant_menu("missing", limit=20, store=_StubStore(menu_rows=[]))
    assert exc.value.status_code == 404
    assert exc.value.detail == "Restaurant menu not found"


def test_get_restaurant_menu_maps_rows() -> None:
    store = _StubStore(
        menu_rows=[
            {
                "id": "m1",
                "chain_id": "c1",
                "item_name": "Protein Burger",
                "category": "Burgers",
                "serving_size_g": 200.0,
                "kcal": 540.0,
                "protein_g": 30.0,
                "fat_g": 24.0,
                "carbs_g": 50.0,
                "sodium_mg": 910.0,
                "source": "menustat",
                "source_id": "menu-001",
                "is_active": 1,
            }
        ]
    )
    result = restaurants.get_restaurant_menu("c1", limit=20, store=store)
    assert len(result) == 1
    assert result[0].id == "m1"
    assert result[0].item_name == "Protein Burger"


def test_create_submission_validation_error_maps_422() -> None:
    store = _StubStore(create_error=ValueError("canonical_name is required"))
    payload = RestaurantSubmissionCreate(canonical_name="abc", payload={})
    with pytest.raises(HTTPException) as exc:
        restaurants.create_restaurant_submission(payload, store=store)
    assert exc.value.status_code == 422
    assert exc.value.detail == "canonical_name is required"


def test_create_submission_success() -> None:
    store = _StubStore(
        create_response={
            "id": "s1",
            "entity_type": "restaurant_menu",
            "canonical_name": "Protein Burger",
            "barcode": None,
            "off_url": None,
            "payload": {"kcal": 540},
            "status": "pending",
            "reviewer_notes": None,
            "created_at": "2026-02-24T00:00:00+00:00",
            "updated_at": "2026-02-24T00:00:00+00:00",
            "audit": [],
        }
    )
    payload = RestaurantSubmissionCreate(canonical_name="Protein Burger", payload={"kcal": 540})
    result = restaurants.create_restaurant_submission(payload, store=store)
    assert result.id == "s1"
    assert result.status == SubmissionStatus.PENDING


def test_get_submission_not_found() -> None:
    with pytest.raises(HTTPException) as exc:
        restaurants.get_restaurant_submission("missing", store=_StubStore(get_response=None))
    assert exc.value.status_code == 404
    assert exc.value.detail == "Submission not found"


def test_get_submission_success() -> None:
    store = _StubStore(
        get_response={
            "id": "s1",
            "entity_type": "restaurant_menu",
            "canonical_name": "Protein Burger",
            "barcode": None,
            "off_url": None,
            "payload": {"kcal": 540},
            "status": "approved",
            "reviewer_notes": "ok",
            "created_at": "2026-02-24T00:00:00+00:00",
            "updated_at": "2026-02-24T00:05:00+00:00",
            "audit": [],
        }
    )
    result = restaurants.get_restaurant_submission("s1", store=store)
    assert result.id == "s1"
    assert result.status == SubmissionStatus.APPROVED


def test_review_submission_maps_response() -> None:
    store = _StubStore(
        review_response={
            "id": "s1",
            "entity_type": "restaurant_menu",
            "canonical_name": "Protein Burger",
            "barcode": None,
            "off_url": None,
            "payload": {"kcal": 540},
            "status": "approved",
            "reviewer_notes": "ok",
            "created_at": "2026-02-24T00:00:00+00:00",
            "updated_at": "2026-02-24T00:05:00+00:00",
            "audit": [],
        }
    )
    payload = SubmissionReviewRequest(status=SubmissionStatus.APPROVED, reviewer_notes="ok")
    result = restaurants.review_restaurant_submission("s1", payload, store=store)
    assert result.id == "s1"
    assert result.status == SubmissionStatus.APPROVED


def test_review_submission_validation_error_maps_422() -> None:
    store = _StubStore(review_error=ValueError("status must be one of: approved, rejected"))
    payload = SubmissionReviewRequest(status=SubmissionStatus.REJECTED)
    with pytest.raises(HTTPException) as exc:
        restaurants.review_restaurant_submission("s1", payload, store=store)
    assert exc.value.status_code == 422


def test_review_submission_not_found_maps_404() -> None:
    payload = SubmissionReviewRequest(status=SubmissionStatus.REJECTED)
    with pytest.raises(HTTPException) as exc:
        restaurants.review_restaurant_submission(
            "s1",
            payload,
            store=_StubStore(review_response=None),
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Submission not found"
