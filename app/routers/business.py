import logging
import os
import re
from typing import Any, Optional

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.routers.api_key import require_app_api_key
from core.business_bayesian_analyzer import BusinessBayesianAnalyzer
from core.i18n import normalize_lang, t

# Business feature flag: enable/disable business module via env or default True
BUSINESS_MODULE_ENABLED = os.getenv("BUSINESS_MODULE_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/business", tags=["business"])


def _safe_error_summary(err: Exception) -> str:
    """Return a sanitized error summary without user-provided content."""
    return err.__class__.__name__


def _sanitize_log_value(value: str, max_length: int = 100) -> str:
    """Sanitize and truncate user input for safe logging.

    Removes control characters (newlines, tabs, non-printable chars)
    and truncates to max_length to prevent log injection attacks.

    Args:
        value: User-controlled string to sanitize
        max_length: Maximum allowed length (default 100)

    Returns:
        Sanitized and truncated string safe for logging
    """
    # Remove control characters and non-printable chars (except space)
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


class BusinessAnalysisRequest(BaseModel):
    """Request model for business analysis."""

    code: str = Field(..., description="Code to analyze (max 100KB)")
    test_name: str = "business_analysis"
    locale: Optional[str] = None


class BusinessAnalysisResponse(BaseModel):
    """Response model for business analysis."""

    test_name: str
    success: bool
    business_category: str
    error_type: str
    error_message: Optional[str]
    revenue_impact: str
    cost_impact: str
    customer_impact: str
    optimization_potential: Optional[str]


def _localized_error(locale: Optional[str], key: str) -> str:
    """Helper to get localized error message.

    Args:
        locale: User's locale preference (optional)
        key: Translation key

    Returns:
        Localized error message
    """
    lang = normalize_lang(locale)
    message: str = t(lang, key)
    return message


@router.post("/analyze", response_model=list[BusinessAnalysisResponse])
async def analyze_business_code(
    request: BusinessAnalysisRequest,
    _api_key: str = Depends(require_app_api_key),
) -> list[BusinessAnalysisResponse]:
    """
    Analyze code from a business perspective.

    Provides business insights on monetization strategies, cost optimization,
    customer acquisition, revenue growth, and customer retention.
    """
    if not BUSINESS_MODULE_ENABLED:
        detail = _localized_error(request.locale, "business_module_disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    # Defensive check: prevent DoS with extremely large payloads
    code_bytes = len(request.code.encode("utf-8"))
    if code_bytes > 100_000:
        logger.warning(
            "Rejected oversized code payload: %d bytes (max 100KB)",
            code_bytes,
        )
        detail = _localized_error(request.locale, "business_payload_too_large")
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=detail,
        )

    try:
        # Initialize business analyzer
        analyzer = BusinessBayesianAnalyzer(locale=request.locale)

        # Perform business analysis (offload to thread to avoid blocking event loop)
        results = await to_thread.run_sync(analyzer.analyze, request.code, request.test_name)

        # Convert results to response format
        response_items = [
            BusinessAnalysisResponse(
                test_name=result.test_name,
                success=result.success,
                business_category=result.business_category.value,
                error_type=result.error_type.value if result.error_type else "unknown",
                error_message=result.error_message,
                revenue_impact=result.revenue_impact,
                cost_impact=result.cost_impact,
                customer_impact=result.customer_impact,
                optimization_potential=result.optimization_potential,
            )
            for result in results
        ]

        return response_items

    except HTTPException:
        # Re-raise HTTPException (auth/permission errors) untouched
        raise
    except Exception as e:
        # Log and wrap non-HTTPException errors as 500
        # Sanitize user-controlled test_name to prevent log injection
        safe_test_name = _sanitize_log_value(request.test_name)
        logger.error(
            "Business analysis failed for test_name=%s (%s)",
            safe_test_name,
            _safe_error_summary(e),
            exc_info=True,
        )
        detail = _localized_error(request.locale, "business_analysis_failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from e


@router.get("/status")
async def business_status() -> dict[str, Any]:
    """Check if the business module is enabled."""
    return {"enabled": BUSINESS_MODULE_ENABLED, "module": "business_analysis"}
