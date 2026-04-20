"""Knowledge promotion policy types.

RU: Типы policy для bounded knowledge promotion.
EN: Policy types for bounded knowledge promotion.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgePolicy:
    """Deterministic runtime policy for internal knowledge access/promotion."""

    enabled: bool
    allow_reads: bool
    allow_promotion: bool
    min_confidence: float
    require_rag_factual_route: bool
    deny_degraded_reasons: tuple[str, ...]
    subject_scope_required: bool
    rail: str
