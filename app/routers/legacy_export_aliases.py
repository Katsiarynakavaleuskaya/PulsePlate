"""Compatibility ownership for legacy test/demo export aliases."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.security.rate_limit import RATE_LIMIT_429_RESPONSES, RATE_LIMIT_EXPORTS, limit_if_available

LEGACY_EXPORT_ALIAS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/premium/exports/day/{plan_id}.csv", "GET", False),
    ("/api/v1/premium/exports/week/{plan_id}.csv", "GET", False),
)

ExportHandler = Callable[..., Awaitable[Response]]
ExportHandlerResolver = Callable[[], ExportHandler]


def build_legacy_export_aliases_router(
    *,
    api_key_dependency: Callable[..., Any],
    export_daily_plan_csv: ExportHandlerResolver,
    export_weekly_plan_csv: ExportHandlerResolver,
) -> APIRouter:
    """Build the gated legacy export-alias router with injected legacy helpers."""

    router = APIRouter()

    @router.get(
        "/api/v1/premium/exports/day/{plan_id}.csv",
        dependencies=[Depends(api_key_dependency)],
        include_in_schema=False,
        responses=RATE_LIMIT_429_RESPONSES,
    )
    @limit_if_available(RATE_LIMIT_EXPORTS)
    async def export_daily_plan_csv_route(request: Request, plan_id: str) -> Response:
        return await export_daily_plan_csv()(plan_id)

    @router.get(
        "/api/v1/premium/exports/week/{plan_id}.csv",
        dependencies=[Depends(api_key_dependency)],
        include_in_schema=False,
        responses=RATE_LIMIT_429_RESPONSES,
    )
    @limit_if_available(RATE_LIMIT_EXPORTS)
    async def export_weekly_plan_csv_route(request: Request, plan_id: str) -> Response:
        return await export_weekly_plan_csv()(plan_id)

    return router


router = APIRouter()
