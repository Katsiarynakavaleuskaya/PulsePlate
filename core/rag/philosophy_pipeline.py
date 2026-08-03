"""Baseline RAG validation with optional philosophy enrichment.

Multi-stage deterministic validation of RAG chunks before LLM generation.
Stage 1 is mandatory. ``FEATURE_PHILOSOPHY_VALIDATION`` controls only the
advisory post-Stage-1 enrichment stages.

Stages:
1. **Rule validation** — delegate to existing ``validation.validate_rag_chunks``
2. **Claim classification** — classify chunks (fact / recommendation / speculation)
3. **Source-claim alignment** — flag score-vs-content mismatches
4. **Logical consistency** — detect contradictions and single-source echo

Only stage 1 blocks chunks.  Stages 2-4 add advisory warnings.
Stage-1 failures reject all chunks. Optional-stage failures roll back to an
untouched snapshot of the Stage-1 survivors.

See: ``docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-s2-baseline-validation-boundary``
and ``docs/contracts/RAG_CONTRACT.md#33-mandatory-stage-1-validation-boundary``.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.rag.contracts import RAGChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Claim type taxonomy
# ---------------------------------------------------------------------------


class ClaimType(str, Enum):
    """Claim classification for RAG chunks."""

    NUTRITION_FACT = "nutrition_fact"
    RECOMMENDATION = "recommendation"
    SPECULATION = "speculation"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    """Result of a single pipeline stage."""

    stage_name: str
    passed: bool
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class PipelineResult:
    """Result of the full philosophy validation pipeline."""

    filtered_chunks: list[RAGChunk]
    """Chunks that survived blocking stages."""

    stage_results: list[StageResult]
    """Per-stage results in execution order."""

    warnings: list[str]
    """Aggregated warnings from all stages."""

    total_latency_ms: float
    """Total pipeline execution time in milliseconds."""

    post_stage1_enrichment_completed: bool = False
    """Whether configured advisory stages completed for non-empty survivors."""

    def __post_init__(self) -> None:
        """Reject completion state that has no validated survivor carrier."""

        if self.post_stage1_enrichment_completed and not self.filtered_chunks:
            raise ValueError("post-Stage-1 enrichment cannot complete without filtered chunks")


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Stage 2: Claim classification
_NUTRITION_FACT_RE = re.compile(
    r"\b\d+\.?\d*\s*(?:kcal|cal|kj|grams?|mg|mcg|g/kg|ml)\b"
    r"|\b(?:BMI|BMR|TDEE|RDA|DRI)\s*[\d<>=]",
    re.IGNORECASE,
)

_RECOMMENDATION_RE = re.compile(
    r"\b(?:aim\s+for|try\s+to|consider|should|recommended?|at\s+least|no\s+more\s+than)\b",
    re.IGNORECASE,
)

_SPECULATION_RE = re.compile(
    r"\b(?:some\s+say|possibly|it\s+is\s+believed|reportedly"
    r"|might\s+be|could\s+be|may\s+or\s+may\s+not|some\s+experts)\b",
    re.IGNORECASE,
)

# Stage 4: Numeric range extraction
_NUMERIC_RANGE_RE = re.compile(
    r"(\d+\.?\d*)\s*[-\u2013]\s*(\d+\.?\d*)",
)
_TOKEN_RE = re.compile(r"\b[^\W\d_][\w-]*\b", re.UNICODE)

# Audience/cadence words stay non-binding on purpose: they tend to create
# false contradictions across different metrics that happen to share a cohort.
_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "adult",
        "adults",
        "be",
        "best",
        "child",
        "children",
        "daily",
        "female",
        "for",
        "good",
        "healthy",
        "how",
        "ideal",
        "in",
        "is",
        "level",
        "levels",
        "many",
        "male",
        "meal",
        "meals",
        "men",
        "normal",
        "of",
        "per",
        "people",
        "person",
        "practical",
        "range",
        "ranges",
        "recommended",
        "should",
        "target",
        "targets",
        "the",
        "to",
        "value",
        "values",
        "what",
        "with",
        "women",
    }
)
_BROAD_QUERY_MODIFIERS = frozenset({"vitamin"})
_CONTEXT_DISAMBIGUATION_TERMS = frozenset(
    {
        "adult",
        "adults",
        "child",
        "children",
        "daily",
        "day",
        "female",
        "gram",
        "grams",
        "kg",
        "kilogram",
        "kilograms",
        "male",
        "meal",
        "meals",
        "men",
        "women",
    }
)
_CONTEXT_STOPWORDS = _QUERY_STOPWORDS - _CONTEXT_DISAMBIGUATION_TERMS
_RANGE_ANCHOR_PREFIX_CHARS = 24
_RANGE_ANCHOR_SUFFIX_CHARS = 12
_RANGE_CONTEXT_SUFFIX_CHARS = 36

# Stage 3: Alignment thresholds
# These thresholds detect score-vs-content quality mismatches.
# High score + short text suggests the retriever matched on boilerplate/headers.
_HIGH_SCORE_THRESHOLD = 0.7  # Above this, chunk is considered "high confidence"
_SHORT_TEXT_THRESHOLD = 30  # Below 30 chars is suspiciously short for useful content
_VERY_SHORT_TEXT_THRESHOLD = 20  # Below 20 chars is almost certainly low quality
_MEDIUM_SCORE_THRESHOLD = 0.5  # Medium confidence threshold
_ALIGNMENT_WARNING_THRESHOLD = 0.5  # Misalignment score above this triggers warning


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_pipeline(
    chunks: list[RAGChunk],
    query: str,
    *,
    enrichment_enabled: bool = True,
) -> PipelineResult:
    """Run mandatory Stage 1 before optional advisory enrichment.

    Parameters
    ----------
    chunks:
        RAG chunks to validate.
    query:
        Original user query for context.
    enrichment_enabled:
        Whether to run advisory stages 2-4 after Stage 1 succeeds.

    Returns
    -------
    PipelineResult
        Canonical Stage-1 survivors, completed stage results, and warnings.
    """
    pipeline_start = time.perf_counter()

    try:
        filtered, stage1 = _stage1_rule_validation(chunks)
    except Exception:
        logger.warning("Stage-1 RAG validation failed; rejecting all chunks")
        return PipelineResult(
            filtered_chunks=[],
            stage_results=[],
            warnings=["validation_error: internal failure, no chunks accepted"],
            total_latency_ms=round((time.perf_counter() - pipeline_start) * 1000, 2),
        )

    stage1_warnings = list(stage1.warnings)
    if not filtered:
        return PipelineResult(
            filtered_chunks=[],
            stage_results=[stage1],
            warnings=stage1_warnings,
            total_latency_ms=round((time.perf_counter() - pipeline_start) * 1000, 2),
        )

    baseline_survivors = _copy_chunks(filtered)
    if not enrichment_enabled:
        return PipelineResult(
            filtered_chunks=baseline_survivors,
            stage_results=[stage1],
            warnings=stage1_warnings,
            total_latency_ms=round((time.perf_counter() - pipeline_start) * 1000, 2),
        )

    stage_results = [stage1]
    all_warnings = list(stage1_warnings)
    try:
        stage2 = _stage2_claim_classification(_copy_chunks(baseline_survivors))
        stage_results.append(stage2)
        all_warnings.extend(stage2.warnings)

        stage3 = _stage3_source_alignment(_copy_chunks(baseline_survivors))
        stage_results.append(stage3)
        all_warnings.extend(stage3.warnings)

        stage4 = _stage4_logical_consistency(_copy_chunks(baseline_survivors), query)
        stage_results.append(stage4)
        all_warnings.extend(stage4.warnings)
    except Exception:
        logger.warning("Post-Stage-1 RAG enrichment failed; using baseline survivors")
        return PipelineResult(
            filtered_chunks=baseline_survivors,
            stage_results=[stage1],
            warnings=stage1_warnings + ["post_stage1_enrichment_error: internal failure"],
            total_latency_ms=round((time.perf_counter() - pipeline_start) * 1000, 2),
        )

    return PipelineResult(
        filtered_chunks=baseline_survivors,
        stage_results=stage_results,
        warnings=all_warnings,
        total_latency_ms=round((time.perf_counter() - pipeline_start) * 1000, 2),
        post_stage1_enrichment_completed=True,
    )


def _copy_chunks(chunks: list[RAGChunk]) -> list[RAGChunk]:
    """Copy the primitive chunk carrier without preserving mutable aliases."""

    return [
        RAGChunk(
            chunk_id=chunk.chunk_id,
            file=chunk.file,
            content=chunk.content,
            score=chunk.score,
            hop=chunk.hop,
        )
        for chunk in chunks
    ]


# ---------------------------------------------------------------------------
# Stage 1: Rule-based validation (delegates to validation.py)
# ---------------------------------------------------------------------------


def _stage1_rule_validation(
    chunks: list[RAGChunk],
) -> tuple[list[RAGChunk], StageResult]:
    """Delegate to existing ``validate_rag_chunks()`` for blocking rules."""
    start = time.perf_counter()

    from core.rag.validation import validate_rag_chunks

    val_result = validate_rag_chunks(chunks)
    latency = (time.perf_counter() - start) * 1000

    return val_result.filtered_chunks, StageResult(
        stage_name="rule_validation",
        passed=val_result.passed,
        warnings=val_result.warnings,
        metadata={
            "rejected_count": val_result.rejected_count,
            "validation_latency_ms": val_result.validation_latency_ms,
        },
        latency_ms=round(latency, 2),
    )


# ---------------------------------------------------------------------------
# Stage 2: Claim classification (enrichment — no blocking)
# ---------------------------------------------------------------------------


def classify_chunk(chunk: RAGChunk) -> ClaimType:
    """Classify a single chunk by claim type.

    Priority: NUTRITION_FACT > RECOMMENDATION > SPECULATION > UNKNOWN.
    """
    text = chunk.content
    if _NUTRITION_FACT_RE.search(text):
        return ClaimType.NUTRITION_FACT
    if _RECOMMENDATION_RE.search(text):
        return ClaimType.RECOMMENDATION
    if _SPECULATION_RE.search(text):
        return ClaimType.SPECULATION
    return ClaimType.UNKNOWN


def _stage2_claim_classification(chunks: list[RAGChunk]) -> StageResult:
    """Classify each chunk and record distribution in metadata."""
    start = time.perf_counter()
    warnings: list[str] = []
    classifications: dict[str, int] = {}

    for chunk in chunks:
        claim_type = classify_chunk(chunk)
        classifications[claim_type.value] = classifications.get(claim_type.value, 0) + 1
        if claim_type == ClaimType.SPECULATION:
            warnings.append("claim_speculation")

    latency = (time.perf_counter() - start) * 1000

    return StageResult(
        stage_name="claim_classification",
        passed=True,
        warnings=warnings,
        metadata={"classifications": classifications},
        latency_ms=round(latency, 2),
    )


# ---------------------------------------------------------------------------
# Stage 3: Source-claim alignment (advisory — no blocking)
# ---------------------------------------------------------------------------


def _alignment_score(chunk: RAGChunk) -> float:
    """Score misalignment between retrieval score and content quality.

    Returns 0.0 for well-aligned chunks, higher for suspicious mismatches.
    A high retrieval score on very short text suggests a quality issue.
    """
    text_len = len(chunk.content.strip())
    if chunk.score > _HIGH_SCORE_THRESHOLD and text_len < _VERY_SHORT_TEXT_THRESHOLD:
        return 0.9
    if chunk.score > _HIGH_SCORE_THRESHOLD and text_len < _SHORT_TEXT_THRESHOLD:
        return 0.8
    if chunk.score > _MEDIUM_SCORE_THRESHOLD and text_len < _VERY_SHORT_TEXT_THRESHOLD:
        return 0.7
    return 0.0


def _stage3_source_alignment(chunks: list[RAGChunk]) -> StageResult:
    """Flag chunks where retrieval score does not match content quality."""
    start = time.perf_counter()
    warnings: list[str] = []
    flagged_count = 0

    for chunk in chunks:
        score = _alignment_score(chunk)
        if score > _ALIGNMENT_WARNING_THRESHOLD:
            flagged_count += 1
            warnings.append("alignment_mismatch")

    latency = (time.perf_counter() - start) * 1000

    return StageResult(
        stage_name="source_alignment",
        passed=True,
        warnings=warnings,
        metadata={"flagged_count": flagged_count},
        latency_ms=round(latency, 2),
    )


# ---------------------------------------------------------------------------
# Stage 4: Logical consistency (advisory — no blocking)
# ---------------------------------------------------------------------------


def _extract_numeric_ranges(text: str) -> list[tuple[float, float]]:
    """Extract numeric ranges (e.g. '18.5-24.9') from text."""
    ranges: list[tuple[float, float]] = []
    for match in _NUMERIC_RANGE_RE.finditer(text):
        try:
            low = float(match.group(1))
            high = float(match.group(2))
            if low < high:
                ranges.append((low, high))
        except ValueError:  # pragma: no cover - defensive; regex ensures valid floats
            continue
    return ranges


def _ranges_contradict(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Return True if two numeric ranges are non-overlapping (contradiction)."""
    return a[1] < b[0] or b[1] < a[0]


def _extract_query_terms(query: str) -> set[str]:
    """Return significant query anchors for query-aware contradiction checks."""
    return {
        token.lower()
        for token in _TOKEN_RE.findall(query)
        if len(token) >= 2 and token.lower() not in _QUERY_STOPWORDS
    }


def _extract_query_anchors(text: str, query_terms: set[str]) -> set[str]:
    """Return query terms that are explicitly present in chunk-local text."""
    if not query_terms:
        return set()

    text_terms = {token.lower() for token in _TOKEN_RE.findall(text)}
    return text_terms & query_terms


def _extract_context_terms(text: str) -> set[str]:
    """Return disambiguation markers that distinguish closely related range claims."""
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _CONTEXT_STOPWORDS
        and (
            len(token) >= 3
            or any(char.isdigit() for char in token)
            or len(token) == 1
            or token.lower() in _CONTEXT_DISAMBIGUATION_TERMS
        )
    }


def _is_context_disambiguator(token: str) -> bool:
    """Return True when a context token can distinguish one metric/topic from another."""
    return (
        token in _CONTEXT_DISAMBIGUATION_TERMS
        or any(char.isdigit() for char in token)
        or len(token) == 1
    )


def _extract_anchored_numeric_ranges(
    text: str,
    query_terms: set[str],
) -> list[tuple[tuple[float, float], set[str], set[str]]]:
    """Extract numeric ranges together with query anchors near each range.

    Using range-local context prevents one topic inside a mixed chunk from
    lending its anchor to unrelated numeric ranges later in the paragraph.
    """
    anchored_ranges: list[tuple[tuple[float, float], set[str], set[str]]] = []
    for match in _NUMERIC_RANGE_RE.finditer(text):
        try:
            low = float(match.group(1))
            high = float(match.group(2))
        except ValueError:  # pragma: no cover - defensive; regex ensures valid floats
            continue

        if low >= high:
            continue

        context_start = max(0, match.start() - _RANGE_ANCHOR_PREFIX_CHARS)
        anchor_context_end = min(len(text), match.end() + _RANGE_ANCHOR_SUFFIX_CHARS)
        context_context_end = min(len(text), match.end() + _RANGE_CONTEXT_SUFFIX_CHARS)
        anchor_context = text[context_start:anchor_context_end]
        context_context = text[context_start:context_context_end]
        anchored_ranges.append(
            (
                (low, high),
                _extract_query_anchors(anchor_context, query_terms),
                _extract_context_terms(context_context),
            )
        )

    return anchored_ranges


def _query_binding_is_ambiguous(
    anchors_a: set[str],
    anchors_b: set[str],
    context_terms_a: set[str],
    context_terms_b: set[str],
    query_terms: set[str],
) -> bool:
    """Return True when broad query anchors do not bind both ranges to one topic."""
    shared_query_anchors = anchors_a & anchors_b
    if not shared_query_anchors:
        return True

    extra_query_anchors_a = anchors_a - shared_query_anchors
    extra_query_anchors_b = anchors_b - shared_query_anchors
    conflicting_query_anchors = extra_query_anchors_a and extra_query_anchors_b
    if conflicting_query_anchors:
        return True

    unexpected_query_anchors_a = extra_query_anchors_a - _BROAD_QUERY_MODIFIERS
    unexpected_query_anchors_b = extra_query_anchors_b - _BROAD_QUERY_MODIFIERS
    if unexpected_query_anchors_a or unexpected_query_anchors_b:
        return True

    extra_context_a = context_terms_a - query_terms
    extra_context_b = context_terms_b - query_terms
    shared_context = extra_context_a & extra_context_b
    unique_context_a = {
        token for token in (extra_context_a - shared_context) if _is_context_disambiguator(token)
    }
    unique_context_b = {
        token for token in (extra_context_b - shared_context) if _is_context_disambiguator(token)
    }
    return bool(unique_context_a and unique_context_b)


def _stage4_logical_consistency(
    chunks: list[RAGChunk],
    query: str,
) -> StageResult:
    """Detect contradictory numeric claims and single-source echo.

    Parameters
    ----------
    chunks:
        Filtered chunks to check for consistency.
    query:
        Original user query used to anchor contradiction checks to the active topic.
    """
    start = time.perf_counter()
    warnings: list[str] = []
    query_terms = _extract_query_terms(query)

    # Check 1: Single-source echo
    unique_sources = {c.file for c in chunks}
    if len(chunks) > 1:
        if len(unique_sources) == 1:
            warnings.append("single_source_echo")

    # Check 2: Contradictory numeric ranges
    chunk_ranges: list[tuple[str, tuple[float, float], set[str], set[str]]] = []
    for chunk in chunks:
        for r, anchors, context_terms in _extract_anchored_numeric_ranges(
            chunk.content,
            query_terms,
        ):
            chunk_ranges.append(
                (
                    chunk.chunk_id,
                    r,
                    anchors,
                    context_terms,
                )
            )

    contradiction_count = 0
    for i, (id_a, range_a, anchors_a, context_terms_a) in enumerate(chunk_ranges):
        for id_b, range_b, anchors_b, context_terms_b in chunk_ranges[i + 1 :]:
            if (
                id_a != id_b
                and not _query_binding_is_ambiguous(
                    anchors_a,
                    anchors_b,
                    context_terms_a,
                    context_terms_b,
                    query_terms,
                )
                and _ranges_contradict(range_a, range_b)
            ):
                contradiction_count += 1

    if contradiction_count:
        warnings.append("numeric_contradiction")

    latency = (time.perf_counter() - start) * 1000

    return StageResult(
        stage_name="logical_consistency",
        passed=True,
        warnings=warnings,
        metadata={
            "unique_sources": len(unique_sources),
            "contradiction_count": contradiction_count,
        },
        latency_ms=round(latency, 2),
    )
