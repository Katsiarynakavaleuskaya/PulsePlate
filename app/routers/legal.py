"""Legal publication helpers for runtime-safe policy endpoints.

RU: Typed helpers for legal/publication payloads.
EN: Typed helpers for legal/publication payloads.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TermsServiceScope(BaseModel):
    """Service-scope disclosure for `/terms`."""

    category: str = Field(..., description="High-level service category.")
    medical_boundary: str = Field(..., description="Explicit wellness-only boundary.")
    age_requirement: str = Field(..., description="Age or eligibility note.")


class TermsBillingSubscriptions(BaseModel):
    """Billing and subscription disclosure for `/terms`."""

    ios_app_store: str = Field(..., description="Apple-managed purchase path.")
    manual_rails: str = Field(..., description="Manual reconciliation rails when configured.")
    cancellation: str = Field(..., description="Cancellation responsibility note.")
    entitlement_truth: str = Field(..., description="Backend source of truth for entitlement.")


class TermsAcceptableUse(BaseModel):
    """Acceptable-use disclosure for `/terms`."""

    forbidden: list[str] = Field(..., description="Blocked usage scenarios.")
    security_note: str = Field(..., description="Abuse-prevention disclosure.")


class TermsResponse(BaseModel):
    """Typed response contract for `/terms`."""

    terms_of_use: str = Field(..., description="Top-level terms-of-use summary.")
    service_scope: TermsServiceScope
    billing_and_subscriptions: TermsBillingSubscriptions
    acceptable_use: TermsAcceptableUse
    liability_boundary: str = Field(..., description="Liability boundary summary.")
    contact: str = Field(..., description="Legal/billing contact guidance.")
    effective_date: str = Field(..., description="Terms effective date in ISO format.")


def build_terms_endpoint_payload() -> TermsResponse:
    """Return the canonical typed payload for `GET /terms`."""

    response: TermsResponse = TermsResponse(
        terms_of_use=(
            "PulsePlate provides wellness-oriented planning, nutrition, and coaching-style "
            "features. It does not provide medical diagnosis, treatment, emergency response, "
            "or licensed clinical services."
        ),
        service_scope=TermsServiceScope(
            category="wellness / nutrition planning / coaching support",
            medical_boundary=(
                "Content is informational and product-guidance only. Users must not treat the "
                "service as medical, psychiatric, or emergency advice."
            ),
            age_requirement="The service is intended for adults unless a specific flow states otherwise.",
        ),
        billing_and_subscriptions=TermsBillingSubscriptions(
            ios_app_store="Apple-managed digital subscription flow with server-side verification.",
            manual_rails="Operational fallback rails may include ERIP QR or SWIFT manual reconciliation.",
            cancellation="Users manage subscription cancellation in the original purchase channel.",
            entitlement_truth="Subscription entitlement is determined by backend verification and audit state.",
        ),
        acceptable_use=TermsAcceptableUse(
            forbidden=[
                "attempting to bypass tier controls or payment verification",
                "submitting unlawful, abusive, or malicious content",
                "using the service for medical triage or emergency decisions",
            ],
            security_note=(
                "Abuse-prevention and platform-protection controls may block unsafe or fraudulent use."
            ),
        ),
        liability_boundary=(
            "The service is provided on a best-effort basis for wellness support. Users remain "
            "responsible for critical health, legal, and financial decisions."
        ),
        contact="For legal or billing questions, please contact the application administrator.",
        effective_date="2026-03-08",
    )
    return response
