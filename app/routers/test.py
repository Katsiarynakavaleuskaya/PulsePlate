"""
Test endpoints for development and staging environments.

These endpoints are used for testing rate limiting and other infrastructure features.
Should NOT be included in production builds.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from settings import get_runtime_env_name


def _ensure_non_production() -> None:
    """
    Guard test routes from being used in production.

    This is evaluated per-request so tests that toggle runtime env still work
    even if the router was included earlier in the process lifecycle.
    """
    env = get_runtime_env_name()
    if env == "production":
        raise HTTPException(status_code=404, detail="Test endpoints disabled in production")

    # Staging may be externally accessible; require explicit enablement.
    if env == "staging" and (os.getenv("ENABLE_TEST_ROUTES", "").strip() != "1"):
        raise HTTPException(status_code=404, detail="Test endpoints disabled in staging")


router = APIRouter(
    prefix="/api/v1/test",
    tags=["test"],
    dependencies=[Depends(_ensure_non_production)],
)


class TestResponse(BaseModel):
    """Standard test response model."""

    status: str
    message: str
    timestamp: str
    request_id: str | None = None


@router.post("/rate-limit", response_model=TestResponse)
async def test_rate_limit(request: Request, response: Response) -> TestResponse:
    """
    Test endpoint for rate limiting without authentication.

    This endpoint is intentionally public to allow testing of rate limiting
    functionality without the need for authentication tokens.

    Returns:
        TestResponse: Simple response with timestamp and request info
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Add custom headers for debugging
    response.headers["X-Test-Timestamp"] = timestamp
    response.headers["X-Test-Endpoint"] = "rate-limit"

    # Extract request ID if available (from Cloudflare or other proxy)
    request_id = request.headers.get("cf-ray") or request.headers.get("x-request-id")

    return TestResponse(
        status="ok", message="Rate limit test endpoint", timestamp=timestamp, request_id=request_id
    )


@router.get("/health", response_model=TestResponse)
async def test_health(response: Response) -> TestResponse:
    """
    Simple health check endpoint for testing.

    Returns:
        TestResponse: Health status with timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    response.headers["X-Test-Timestamp"] = timestamp

    return TestResponse(
        status="healthy",
        message="Test endpoints are operational",
        timestamp=timestamp,
        request_id=None,
    )


@router.post("/echo")
async def test_echo(data: Dict[str, Any], response: Response) -> Dict[str, Any]:
    """
    Echo endpoint that returns the received data.

    Useful for testing request/response payloads and headers.

    Args:
        data: Any JSON data to echo back

    Returns:
        Dict containing the echoed data and metadata
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    response.headers["X-Test-Timestamp"] = timestamp

    return {"echo": data, "metadata": {"timestamp": timestamp, "endpoint": "echo"}}
