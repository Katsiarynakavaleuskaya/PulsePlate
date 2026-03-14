# -*- coding: utf-8 -*-
from __future__ import annotations

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
from app.services import restaurant_store

router = APIRouter(tags=["restaurants"])
moderation_router = APIRouter(tags=["restaurants"])


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


_STORE: RestaurantStore = _RestaurantStoreCompat()


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
