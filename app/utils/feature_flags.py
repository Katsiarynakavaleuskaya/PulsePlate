"""Feature flag helpers.

Keep parsing logic centralized to avoid drift across modules.
"""

from __future__ import annotations

from typing import Optional

import os

_TRUTHY = {"1", "true", "yes", "on"}


def _is_truthy(value: Optional[str]) -> bool:
    """Check if a string value is truthy.

    Returns True if value (after strip/lower) is in {"1", "true", "yes", "on"}.
    Preserves exact behavior from legacy_app.py.
    """
    return (value or "").strip().lower() in _TRUTHY


def is_vip_module_enabled() -> bool:
    """Check if VIP module is enabled via environment variable."""
    return _is_truthy(os.getenv("VIP_MODULE_ENABLED", "true"))


def is_rag_vector_enabled() -> bool:
    """Check if vector-based RAG retrieval is enabled.

    When True, RAG pipeline uses pgvector cosine similarity instead of
    Jaccard tokenization.  Falls back to Jaccard on failure regardless.
    """
    return _is_truthy(os.getenv("FEATURE_RAG_VECTOR"))


def is_philosophy_validation_enabled() -> bool:
    """Check if philosophy validation layer is enabled for RAG chunks.

    When True, retrieved RAG chunks are validated post-retrieval for
    claim semantics and wellness-safety boundaries before being passed
    to LLM.  Deterministic rule-based checks, no LLM cost.
    """
    return _is_truthy(os.getenv("FEATURE_PHILOSOPHY_VALIDATION"))


def is_recursive_rag_enabled() -> bool:
    """Check if recursive RAG retrieval flow is enabled.

    Default is off; when enabled orchestration can execute multi-hop retrieval
    with bounded refinement/verification budgets.
    """
    return _is_truthy(os.getenv("FEATURE_RAG_RECURSIVE"))


def is_creative_research_pilot_enabled() -> bool:
    """Check if the internal creative research pilot is enabled."""

    return _is_truthy(os.getenv("FEATURE_CREATIVE_RESEARCH_PILOT"))


def is_philosophy_router_enabled() -> bool:
    """Check if pre-generation philosophical router is enabled."""
    return _is_truthy(os.getenv("FEATURE_PHILOSOPHY_ROUTER"))


def is_philosophy_phase12_enabled() -> bool:
    """Check if Aristotelian + Analytical runtime checks are enabled."""
    return _is_truthy(os.getenv("FEATURE_PHILOSOPHY_PHASE12"))


def is_philosophy_linguistic_enabled() -> bool:
    """Check if speech-act and language-game routing is enabled."""
    return _is_truthy(os.getenv("FEATURE_PHILOSOPHY_LINGUISTIC"))


def is_philosophy_pragmatic_enabled() -> bool:
    """Check if pragmatic early-stop policy is enabled."""
    return _is_truthy(os.getenv("FEATURE_PHILOSOPHY_PRAGMATIC"))


__all__ = [
    "is_creative_research_pilot_enabled",
    "is_vip_module_enabled",
    "is_rag_vector_enabled",
    "is_philosophy_validation_enabled",
    "is_philosophy_router_enabled",
    "is_philosophy_phase12_enabled",
    "is_philosophy_linguistic_enabled",
    "is_philosophy_pragmatic_enabled",
    "is_recursive_rag_enabled",
    "_is_truthy",
]
