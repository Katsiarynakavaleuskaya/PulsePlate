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
    return str(value).strip().lower() in _TRUTHY


def is_vip_module_enabled() -> bool:
    """Check if VIP module is enabled via environment variable."""
    return _is_truthy(os.getenv("VIP_MODULE_ENABLED", "true"))


def is_rag_vector_enabled() -> bool:
    """Check if vector-based RAG retrieval is enabled.

    When True, RAG pipeline uses pgvector cosine similarity instead of
    Jaccard tokenization.  Falls back to Jaccard on failure regardless.
    """
    return _is_truthy(os.getenv("FEATURE_RAG_VECTOR"))


__all__ = ["is_vip_module_enabled", "is_rag_vector_enabled", "_is_truthy"]
