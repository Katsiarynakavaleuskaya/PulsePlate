"""Canonical ownership for legacy BMI compatibility routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.schemas.bmi_compat import BMIRequest, BMIRequestV1
from app.services import bmi_compat as bmi_compat_service

BMI_COMPAT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/bmi", "POST", False),
    ("/plan", "POST", False),
    ("/api/v1/bmi", "POST", True),
)

router = APIRouter()


@router.post("/bmi", include_in_schema=False)
async def bmi_endpoint(req: BMIRequest) -> dict[str, Any]:
    """
    RU: Shim endpoint. Исторически использовал legacy BMI math (calc_bmi, bmi_category).
    Теперь это тонкий прокси в канонический handler (app/routers/bmi.py),
    чтобы не было дублирования BMI-логики и чтобы результаты были идентичны.

    EN: Shim endpoint. Historically used legacy BMI math (calc_bmi, bmi_category).
    Now it is a thin proxy to the canonical handler (app/routers/bmi.py)
    to avoid duplicate BMI logic and ensure identical results.
    """
    return await bmi_compat_service.bmi_endpoint(req)


@router.post("/plan", include_in_schema=False)
async def plan_endpoint(req: BMIRequest) -> dict[str, Any]:
    """
    RU: Legacy endpoint /plan (contract must remain stable in PR-457=A).
    EN: Legacy /plan endpoint (contract must remain stable in PR-457=A).

    PR-457=A: Delegates to canonical BMI engine but preserves legacy response contract.
    """
    return await bmi_compat_service.plan_endpoint(req)


@router.post("/api/v1/bmi")
async def bmi_endpoint_v1(req: BMIRequestV1) -> dict[str, Any]:
    """
    RU: Shim endpoint. Исторически использовал legacy BMI math (calc_bmi, bmi_category).
    Теперь это тонкий прокси в канонический handler (app/routers/bmi.py),
    чтобы не было дублирования BMI-логики и чтобы результаты были идентичны.

    EN: Shim endpoint. Historically used legacy BMI math (calc_bmi, bmi_category).
    Now it is a thin proxy to the canonical handler (app/routers/bmi.py)
    to avoid duplicate BMI logic and ensure identical results.
    """
    return await bmi_compat_service.bmi_endpoint_v1(req)
