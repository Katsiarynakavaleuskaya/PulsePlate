"""Canonical runtime-only favicon endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

FAVICON_ROUTE_PATH = "/favicon.ico"

router = APIRouter(tags=["favicon"])


@router.get(FAVICON_ROUTE_PATH, include_in_schema=False)
async def favicon() -> Response:
    """Return an empty favicon response for browsers and crawlers."""

    return Response(status_code=status.HTTP_204_NO_CONTENT)
