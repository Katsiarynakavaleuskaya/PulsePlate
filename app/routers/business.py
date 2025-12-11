import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.routers.api_key import api_key_header
from core.business_bayesian_analyzer import BusinessBayesianAnalyzer

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


@router.post("/analyze", response_model=list[BusinessAnalysisResponse])
async def analyze_business_code(
    request: BusinessAnalysisRequest,
    api_key: str = Depends(api_key_header),
) -> list[BusinessAnalysisResponse]:
    """
    Analyze code from a business perspective.

    Provides business insights on monetization strategies, cost optimization,
    customer acquisition, revenue growth, and customer retention.
    """
    if not BUSINESS_MODULE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Business analysis module is disabled",
        )

    # Defensive check: prevent DoS with extremely large payloads
    if len(request.code) > 100_000:
        logger.warning(
            "Rejected oversized code payload: %d bytes (max 100000)",
            len(request.code),
        )
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Code payload too large (max 100KB)",
        )

    try:
        # Initialize business analyzer
        analyzer = BusinessBayesianAnalyzer(locale=request.locale)

        # Perform business analysis
        results = analyzer.analyze(request.code, request.test_name)

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
        logger.error(
            "Business analysis failed for test_name=%s (%s)",
            request.test_name,
            _safe_error_summary(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Business analysis failed. Please try again or contact support.",
        ) from e


@router.get("/status")
async def business_status() -> dict[str, Any]:
    """Check if the business module is enabled."""
    return {"enabled": BUSINESS_MODULE_ENABLED, "module": "business_analysis"}
