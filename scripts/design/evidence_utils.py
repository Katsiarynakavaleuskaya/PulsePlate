"""Shared evidence-value helpers for design review artifacts."""

from __future__ import annotations

from typing import Any


def _has_meaningful_evidence_value(value: Any) -> bool:
    """Return True only when evidence contains at least one non-empty string."""

    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_meaningful_evidence_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_meaningful_evidence_value(item) for item in value.values())
    return False
