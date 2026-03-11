"""Backward-compatible shim for the creative research eval contract.

RU: PR-B harness импортирует этот модуль; логика теперь живёт в core.
EN: PR-B harness imports this module; the logic now lives in core.
"""

from __future__ import annotations

from core.creative_research import (
    CONFIDENCE_LEVELS,
    DISCOVERY_REQUIRED_FIELDS,
    OUTPUT_CLASSES,
    PROMOTION_DECISIONS,
    SCHEMA_VERSION,
    TASK_CLASS,
    VALID_PHASES,
    _count_hints,
    build_scorecard,
    classify_output,
    evaluate_bundle,
    normalize_creative_research_text,
    select_promotion_decision,
    validate_bundle,
)

__all__ = [
    "CONFIDENCE_LEVELS",
    "DISCOVERY_REQUIRED_FIELDS",
    "OUTPUT_CLASSES",
    "PROMOTION_DECISIONS",
    "SCHEMA_VERSION",
    "TASK_CLASS",
    "VALID_PHASES",
    "_count_hints",
    "build_scorecard",
    "classify_output",
    "evaluate_bundle",
    "normalize_creative_research_text",
    "select_promotion_decision",
    "validate_bundle",
]
