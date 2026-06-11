from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Sequence

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.http_error_details import (
    INVALID_SUBMISSION_DETAIL,
    INVALID_SUBMISSION_TRANSITION_DETAIL,
)
from app.routers import restaurants
from app.schemas.restaurants import (
    RestaurantSubmissionCreate,
    SubmissionReviewRequest,
    SubmissionReviewStatus,
    SubmissionStatus,
)


@pytest.fixture(autouse=True)
def _reset_shadow_read_circuit() -> Iterator[None]:
    restaurants._shadow_read_circuit_open_until.clear()
    yield
    restaurants._shadow_read_circuit_open_until.clear()


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


def test_search_restaurants_offset_validation() -> None:
    with pytest.raises(HTTPException) as exc:
        restaurants.search_restaurants(query="x", limit=10, offset=-1, store=_StubStore())
    assert exc.value.status_code == 422
    assert exc.value.detail == "offset must be >= 0"


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
                "snapshot_date": "2026-02-24",
                "provenance_source": "menustat",
                "provenance_record_id": "menu-001",
            }
        ]
    )
    result = restaurants.get_restaurant_menu("c1", limit=20, store=store)
    assert len(result) == 1
    assert result[0].id == "m1"
    assert result[0].item_name == "Protein Burger"
    assert result[0].snapshot_date == "2026-02-24"
    assert result[0].provenance_source == "menustat"
    assert result[0].provenance_record_id == "menu-001"


def test_get_restaurant_menu_maps_rows_without_provenance() -> None:
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
    assert result[0].snapshot_date is None
    assert result[0].provenance_source is None
    assert result[0].provenance_record_id is None


def test_create_submission_validation_error_maps_422() -> None:
    store = _StubStore(create_error=ValueError("canonical_name is required"))
    payload = RestaurantSubmissionCreate(canonical_name="abc", payload={})
    with pytest.raises(HTTPException) as exc:
        restaurants.create_restaurant_submission(payload, store=store)
    assert exc.value.status_code == 422
    assert exc.value.detail == INVALID_SUBMISSION_DETAIL


def test_create_submission_validation_error_sanitizes_unexpected_detail() -> None:
    store = _StubStore(create_error=ValueError("sqlite:///tmp/private.db"))
    payload = RestaurantSubmissionCreate(canonical_name="abc", payload={})
    with pytest.raises(HTTPException) as exc:
        restaurants.create_restaurant_submission(payload, store=store)
    assert exc.value.status_code == 422
    assert exc.value.detail == INVALID_SUBMISSION_DETAIL
    assert "sqlite" not in exc.value.detail


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
    payload = SubmissionReviewRequest(status=SubmissionReviewStatus.APPROVED, reviewer_notes="ok")
    result = restaurants.review_restaurant_submission("s1", payload, store=store)
    assert result.id == "s1"
    assert result.status == SubmissionStatus.APPROVED


def test_review_submission_validation_error_maps_422() -> None:
    store = _StubStore(review_error=ValueError("status must be one of: approved, rejected"))
    payload = SubmissionReviewRequest(status=SubmissionReviewStatus.REJECTED)
    with pytest.raises(HTTPException) as exc:
        restaurants.review_restaurant_submission("s1", payload, store=store)
    assert exc.value.status_code == 422
    assert exc.value.detail == INVALID_SUBMISSION_TRANSITION_DETAIL


def test_review_submission_validation_error_sanitizes_unexpected_detail() -> None:
    store = _StubStore(review_error=ValueError("internal reviewer path /srv/review"))
    payload = SubmissionReviewRequest(status=SubmissionReviewStatus.REJECTED)
    with pytest.raises(HTTPException) as exc:
        restaurants.review_restaurant_submission("s1", payload, store=store)
    assert exc.value.status_code == 422
    assert exc.value.detail == INVALID_SUBMISSION_TRANSITION_DETAIL
    assert "/srv/review" not in exc.value.detail


def test_review_submission_not_found_maps_404() -> None:
    payload = SubmissionReviewRequest(status=SubmissionReviewStatus.REJECTED)
    with pytest.raises(HTTPException) as exc:
        restaurants.review_restaurant_submission(
            "s1",
            payload,
            store=_StubStore(review_response=None),
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Submission not found"


def test_review_payload_rejects_pending_status() -> None:
    with pytest.raises(ValidationError):
        SubmissionReviewRequest(status=SubmissionStatus.PENDING)


def test_submission_create_rejects_invalid_off_url() -> None:
    with pytest.raises(ValidationError):
        RestaurantSubmissionCreate(canonical_name="X", off_url="not-a-url", payload={})


def test_shadow_wrapper_skips_postgres_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.delenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, raising=False)
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "search_restaurants",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "search_restaurants_pg",
        lambda **_: (_ for _ in ()).throw(AssertionError("shadow search should stay disabled")),
    )

    rows = wrapper.search_restaurants("chain", 10, 0)
    assert list(rows)[0]["id"] == "c1"


def test_shadow_wrapper_uses_postgres_search_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    seen: dict[str, str] = {}
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://shadow")
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "search_restaurants",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}],
    )

    def _shadow_search(**kwargs: Any) -> list[dict[str, Any]]:
        seen["pg_url"] = kwargs["pg_url"]
        return [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}]

    monkeypatch.setattr(
        restaurants.restaurant_postgres_read, "search_restaurants_pg", _shadow_search
    )
    monkeypatch.setattr(
        restaurants.restaurant_shadow_parity,
        "compare_restaurant_hits",
        lambda sqlite_rows, postgres_rows: restaurants.restaurant_shadow_parity.ParityResult(
            match=True,
            sqlite_count=len(sqlite_rows),
            postgres_count=len(postgres_rows),
            mismatched_indexes=(),
            mismatch_reasons=(),
        ),
    )

    rows = wrapper.search_restaurants("chain", 10, 0)
    assert list(rows)[0]["id"] == "c1"
    assert seen["pg_url"] == "postgresql://shadow"


def test_shadow_wrapper_prefers_dedicated_postgres_override_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    seen: dict[str, str] = {}
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://canonical")
    monkeypatch.setenv(
        restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL,
        "postgresql://shadow-override",
    )
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "search_restaurants",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}],
    )

    def _shadow_search(**kwargs: Any) -> list[dict[str, Any]]:
        seen["pg_url"] = kwargs["pg_url"]
        return [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}]

    monkeypatch.setattr(
        restaurants.restaurant_postgres_read, "search_restaurants_pg", _shadow_search
    )
    monkeypatch.setattr(
        restaurants.restaurant_shadow_parity,
        "compare_restaurant_hits",
        lambda sqlite_rows, postgres_rows: restaurants.restaurant_shadow_parity.ParityResult(
            match=True,
            sqlite_count=len(sqlite_rows),
            postgres_count=len(postgres_rows),
            mismatched_indexes=(),
            mismatch_reasons=(),
        ),
    )

    rows = wrapper.search_restaurants("chain", 10, 0)

    assert list(rows)[0]["id"] == "c1"
    assert seen["pg_url"] == "postgresql://shadow-override"


def test_shadow_wrapper_warns_when_enabled_without_postgres_url(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "search_restaurants",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "search_restaurants_pg",
        lambda **_: (_ for _ in ()).throw(AssertionError("shadow search should not run")),
    )

    with caplog.at_level("WARNING"):
        rows = wrapper.search_restaurants("chain", 10, 0)

    assert list(rows)[0]["id"] == "c1"
    assert "shadow reads enabled for search without a PostgreSQL URL" in caplog.text


def test_shadow_wrapper_logs_search_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://shadow")
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "search_restaurants",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "search_restaurants_pg",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "openfoodfacts"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_shadow_parity,
        "compare_restaurant_hits",
        lambda sqlite_rows, postgres_rows: restaurants.restaurant_shadow_parity.ParityResult(
            match=False,
            sqlite_count=len(sqlite_rows),
            postgres_count=len(postgres_rows),
            mismatched_indexes=(0,),
            mismatch_reasons=("field source mismatch at index 0",),
        ),
    )

    with caplog.at_level("WARNING"):
        rows = wrapper.search_restaurants("chain", 10, 0)

    assert list(rows)[0]["id"] == "c1"
    assert "restaurant PostgreSQL shadow-read mismatch for search_restaurants" in caplog.text


def test_shadow_wrapper_fails_open_when_postgres_menu_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://shadow")
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "get_restaurant_menu",
        lambda **_: [{"id": "m1", "chain_id": "c1", "item_name": "Protein Bowl"}],
    )

    def _boom(**kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("pg down")

    monkeypatch.setattr(restaurants.restaurant_postgres_read, "get_restaurant_menu_pg", _boom)

    with caplog.at_level("WARNING"):
        rows = wrapper.get_restaurant_menu("c1", 20)
    assert list(rows)[0]["id"] == "m1"
    assert "keeping SQLite canonical response" in caplog.text


def test_shadow_wrapper_menu_skips_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.delenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, raising=False)
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "get_restaurant_menu",
        lambda **_: [{"id": "m1", "chain_id": "c1", "item_name": "Protein Bowl"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "get_restaurant_menu_pg",
        lambda **_: (_ for _ in ()).throw(AssertionError("shadow menu should stay disabled")),
    )

    rows = wrapper.get_restaurant_menu("c1", 10)

    assert list(rows)[0]["id"] == "m1"


def test_shadow_wrapper_menu_warns_when_enabled_without_postgres_url(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "get_restaurant_menu",
        lambda **_: [{"id": "m1", "chain_id": "c1", "item_name": "Protein Bowl"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "get_restaurant_menu_pg",
        lambda **_: (_ for _ in ()).throw(AssertionError("shadow menu should not run")),
    )

    with caplog.at_level("WARNING"):
        rows = wrapper.get_restaurant_menu("c1", 10)

    assert list(rows)[0]["id"] == "m1"
    assert "shadow reads enabled for menu without a PostgreSQL URL" in caplog.text


def test_shadow_wrapper_logs_menu_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://shadow")
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "get_restaurant_menu",
        lambda **_: [{"id": "m1", "chain_id": "c1", "item_name": "Protein Bowl"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "get_restaurant_menu_pg",
        lambda **_: [{"id": "m1", "chain_id": "c1", "item_name": "Protein Bowl"}],
    )
    monkeypatch.setattr(
        restaurants.restaurant_shadow_parity,
        "compare_restaurant_menu",
        lambda sqlite_rows, postgres_rows: restaurants.restaurant_shadow_parity.ParityResult(
            match=False,
            sqlite_count=len(sqlite_rows),
            postgres_count=len(postgres_rows),
            mismatched_indexes=(0,),
            mismatch_reasons=("field source mismatch at index 0",),
        ),
    )

    with caplog.at_level("WARNING"):
        rows = wrapper.get_restaurant_menu("c1", 10)

    assert list(rows)[0]["id"] == "m1"
    assert "restaurant PostgreSQL shadow-read mismatch for get_restaurant_menu" in caplog.text


def test_shadow_wrapper_submission_paths_remain_sqlite_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://shadow")
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "search_restaurants_pg",
        lambda **_: (_ for _ in ()).throw(AssertionError("search shadow should not run here")),
    )
    monkeypatch.setattr(
        restaurants.restaurant_postgres_read,
        "get_restaurant_menu_pg",
        lambda **_: (_ for _ in ()).throw(AssertionError("menu shadow should not run here")),
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

    assert (
        wrapper.create_submission(
            canonical_name="Protein Bowl",
            payload={"kcal": 540},
            barcode=None,
            off_url=None,
            entity_type="restaurant_menu",
        )["id"]
        == "s1"
    )
    assert wrapper.get_submission("s1")["id"] == "s1"
    assert wrapper.review_submission("s1", status="approved", reviewer_notes=None)["id"] == "s1"


def test_shadow_wrapper_opens_circuit_after_search_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    wrapper = restaurants._RestaurantStoreShadowCompat()
    calls = 0
    monkeypatch.setenv(restaurants.FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "true")
    monkeypatch.delenv(restaurants.RESTAURANT_POSTGRES_SHADOW_READS_URL, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://shadow")
    monkeypatch.setattr(
        restaurants.restaurant_store,
        "search_restaurants",
        lambda **_: [{"id": "c1", "name": "Chain 1", "country": "US", "source": "menustat"}],
    )

    def _boom(**kwargs: Any) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        raise RuntimeError("pg down")

    monkeypatch.setattr(restaurants.restaurant_postgres_read, "search_restaurants_pg", _boom)

    with caplog.at_level("WARNING"):
        first = wrapper.search_restaurants("chain", 10, 0)
        second = wrapper.search_restaurants("chain", 10, 0)

    assert list(first)[0]["id"] == "c1"
    assert list(second)[0]["id"] == "c1"
    assert calls == 1
    assert "keeping SQLite canonical response" in caplog.text
