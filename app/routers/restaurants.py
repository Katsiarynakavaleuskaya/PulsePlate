# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Protocol, Sequence, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.http_error_details import (
    INVALID_SUBMISSION_DETAIL,
    INVALID_SUBMISSION_TRANSITION_DETAIL,
)
from app.schemas.restaurants import (
    RestaurantHit,
    RestaurantMenuItem,
    RestaurantSubmission,
    RestaurantSubmissionCreate,
    SubmissionReviewRequest,
)
from app.services import restaurant_postgres_read, restaurant_shadow_parity, restaurant_store

router = APIRouter(tags=["restaurants"])
moderation_router = APIRouter(tags=["restaurants"])
logger = logging.getLogger(__name__)
FEATURE_RESTAURANT_POSTGRES_SHADOW_READS = "FEATURE_RESTAURANT_POSTGRES_SHADOW_READS"
RESTAURANT_POSTGRES_SHADOW_READS_URL = "RESTAURANT_POSTGRES_SHADOW_READS_URL"


class RestaurantStore(Protocol):
    def search_restaurants(
        self, query: str, limit: int, offset: int
    ) -> Sequence[Mapping[str, Any]]: ...

    def get_restaurant_menu(self, chain_id: str, limit: int) -> Sequence[Mapping[str, Any]]: ...

    def create_submission(
        self,
        *,
        canonical_name: str,
        payload: dict[str, Any],
        barcode: str | None,
        off_url: str | None,
        entity_type: str,
    ) -> Mapping[str, Any]: ...

    def get_submission(self, submission_id: str) -> Mapping[str, Any] | None: ...

    def review_submission(
        self, submission_id: str, *, status: str, reviewer_notes: str | None
    ) -> Mapping[str, Any] | None: ...


class _RestaurantStoreCompat:
    """Compatibility adapter around local restaurant service."""

    def search_restaurants(
        self, query: str, limit: int, offset: int
    ) -> Sequence[Mapping[str, Any]]:
        return cast(
            Sequence[Mapping[str, Any]],
            restaurant_store.search_restaurants(query=query, limit=limit, offset=offset),
        )

    def get_restaurant_menu(self, chain_id: str, limit: int) -> Sequence[Mapping[str, Any]]:
        return cast(
            Sequence[Mapping[str, Any]],
            restaurant_store.get_restaurant_menu(chain_id=chain_id, limit=limit),
        )

    def create_submission(
        self,
        *,
        canonical_name: str,
        payload: dict[str, Any],
        barcode: str | None,
        off_url: str | None,
        entity_type: str,
    ) -> Mapping[str, Any]:
        return cast(
            Mapping[str, Any],
            restaurant_store.create_submission(
                canonical_name=canonical_name,
                payload=payload,
                barcode=barcode,
                off_url=off_url,
                entity_type=entity_type,
            ),
        )

    def get_submission(self, submission_id: str) -> Mapping[str, Any] | None:
        return cast(Mapping[str, Any] | None, restaurant_store.get_submission(submission_id))

    def review_submission(
        self, submission_id: str, *, status: str, reviewer_notes: str | None
    ) -> Mapping[str, Any] | None:
        return cast(
            Mapping[str, Any] | None,
            restaurant_store.review_submission(
                submission_id,
                status=status,
                reviewer_notes=reviewer_notes,
            ),
        )


def _shadow_reads_enabled() -> bool:
    """RU: Shadow lane включается только явным env flag. EN: Shadow lane needs explicit env flag."""

    raw_value = os.getenv(FEATURE_RESTAURANT_POSTGRES_SHADOW_READS, "false")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _shadow_reads_pg_url() -> str | None:
    """RU: Override URL можно задать отдельно, иначе берём DATABASE_URL.

    EN: Use dedicated override when provided, otherwise fall back to DATABASE_URL.
    """

    override_url = os.getenv(RESTAURANT_POSTGRES_SHADOW_READS_URL)
    if override_url:
        return override_url
    database_url = os.getenv("DATABASE_URL")
    return database_url or None


def _log_shadow_read_mismatch(
    operation: str, parity: restaurant_shadow_parity.ParityResult
) -> None:
    logger.warning(
        "restaurant PostgreSQL shadow-read mismatch for %s: sqlite=%s postgres=%s reasons=%s",
        operation,
        parity.sqlite_count,
        parity.postgres_count,
        "; ".join(parity.mismatch_reasons) or "unknown mismatch",
    )


class _RestaurantStoreShadowCompat(_RestaurantStoreCompat):
    """SQLite-authoritative adapter with optional PostgreSQL shadow reads."""

    def search_restaurants(
        self, query: str, limit: int, offset: int
    ) -> Sequence[Mapping[str, Any]]:
        sqlite_rows = list(super().search_restaurants(query, limit, offset))
        self._run_search_shadow(query=query, limit=limit, offset=offset, sqlite_rows=sqlite_rows)
        return sqlite_rows

    def get_restaurant_menu(self, chain_id: str, limit: int) -> Sequence[Mapping[str, Any]]:
        sqlite_rows = list(super().get_restaurant_menu(chain_id, limit))
        self._run_menu_shadow(chain_id=chain_id, limit=limit, sqlite_rows=sqlite_rows)
        return sqlite_rows

    def _run_search_shadow(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
        sqlite_rows: list[Mapping[str, Any]],
    ) -> None:
        if not _shadow_reads_enabled():
            return
        pg_url = _shadow_reads_pg_url()
        if not pg_url:
            logger.warning(
                "restaurant PostgreSQL shadow reads enabled for search without a PostgreSQL URL"
            )
            return
        try:
            pg_rows = restaurant_postgres_read.search_restaurants_pg(
                pg_url=pg_url,
                query=query,
                limit=limit,
                offset=offset,
            )
            parity = restaurant_shadow_parity.compare_restaurant_hits(sqlite_rows, pg_rows)
            if not parity.match:
                _log_shadow_read_mismatch("search_restaurants", parity)
        except Exception:
            logger.warning(
                "restaurant PostgreSQL shadow search failed; keeping SQLite canonical response",
                exc_info=True,
            )

    def _run_menu_shadow(
        self,
        *,
        chain_id: str,
        limit: int,
        sqlite_rows: list[Mapping[str, Any]],
    ) -> None:
        if not _shadow_reads_enabled():
            return
        pg_url = _shadow_reads_pg_url()
        if not pg_url:
            logger.warning(
                "restaurant PostgreSQL shadow reads enabled for menu without a PostgreSQL URL"
            )
            return
        try:
            pg_rows = restaurant_postgres_read.get_restaurant_menu_pg(
                pg_url=pg_url,
                chain_id=chain_id,
                limit=limit,
            )
            parity = restaurant_shadow_parity.compare_restaurant_menu(sqlite_rows, pg_rows)
            if not parity.match:
                _log_shadow_read_mismatch("get_restaurant_menu", parity)
        except Exception:
            logger.warning(
                "restaurant PostgreSQL shadow menu read failed; keeping SQLite canonical response",
                exc_info=True,
            )


_STORE: RestaurantStore = _RestaurantStoreShadowCompat()


def get_restaurant_store() -> RestaurantStore:
    return _STORE


@router.get("/api/v1/restaurants/search", response_model=list[RestaurantHit])
def search_restaurants(
    query: str = Query("", max_length=128),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    store: RestaurantStore = Depends(get_restaurant_store),
) -> list[RestaurantHit]:
    if limit > 100 or limit < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="limit must be in [1,100]"
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="offset must be >= 0"
        )
    rows = store.search_restaurants(query, limit, offset)
    return [RestaurantHit(**dict(row)) for row in rows]


@router.get(
    "/api/v1/restaurants/{chain_id}/menu",
    response_model=list[RestaurantMenuItem],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Restaurant menu not found"}},
)
def get_restaurant_menu(
    chain_id: str,
    limit: int = Query(200, ge=1, le=500),
    store: RestaurantStore = Depends(get_restaurant_store),
) -> list[RestaurantMenuItem]:
    rows = store.get_restaurant_menu(chain_id, limit=limit)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant menu not found"
        )
    return [RestaurantMenuItem(**dict(row)) for row in rows]


@router.post(
    "/api/v1/restaurants/submissions",
    response_model=RestaurantSubmission,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid submission"}},
)
def create_restaurant_submission(
    payload: RestaurantSubmissionCreate,
    store: RestaurantStore = Depends(get_restaurant_store),
) -> RestaurantSubmission:
    try:
        created = store.create_submission(
            canonical_name=payload.canonical_name,
            payload=payload.payload,
            barcode=payload.barcode,
            off_url=payload.off_url,
            entity_type="restaurant_menu",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=INVALID_SUBMISSION_DETAIL,
        ) from exc
    result: RestaurantSubmission = RestaurantSubmission.model_validate(created)
    return result


@router.get(
    "/api/v1/restaurants/submissions/{submission_id}",
    response_model=RestaurantSubmission,
)
def get_restaurant_submission(
    submission_id: str,
    store: RestaurantStore = Depends(get_restaurant_store),
) -> RestaurantSubmission:
    row = store.get_submission(submission_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    result: RestaurantSubmission = RestaurantSubmission.model_validate(row)
    return result


@moderation_router.patch(
    "/api/v1/restaurants/submissions/{submission_id}/status",
    response_model=RestaurantSubmission,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Submission not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid transition"},
    },
)
def review_restaurant_submission(
    submission_id: str,
    payload: SubmissionReviewRequest,
    store: RestaurantStore = Depends(get_restaurant_store),
) -> RestaurantSubmission:
    try:
        row = store.review_submission(
            submission_id,
            status=payload.status.value,
            reviewer_notes=payload.reviewer_notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=INVALID_SUBMISSION_TRANSITION_DETAIL,
        ) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    result: RestaurantSubmission = RestaurantSubmission.model_validate(row)
    return result
