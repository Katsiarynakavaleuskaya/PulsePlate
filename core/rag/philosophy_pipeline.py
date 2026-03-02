"""Philosophy-agent RAG validation pipeline.

Multi-stage deterministic validation of RAG chunks before LLM generation.
Replaces flat ``validate_rag_chunks()`` call when philosophy validation is
enabled (``FEATURE_PHILOSOPHY_VALIDATION``).

Stages:
1. **Rule validation** — delegate to existing ``validation.validate_rag_chunks``
2. **Claim classification** — classify chunks (fact / recommendation / speculation)
3. **Source-claim alignment** — flag score-vs-content mismatches
4. **Logical consistency** — detect contradictions and single-source echo

Only stage 1 blocks chunks.  Stages 2-4 add advisory warnings.
On any internal exception the pipeline returns original chunks (fail-safe).

See: docs/roadmap/BACKLOG_LEDGER.md line 1852 (P2 Philosophy-agent pipeline)
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
) -> PipelineResult:
    """Run all 4 stages sequentially with fail-safe error handling.

    Parameters
    ----------
    chunks:
        RAG chunks to validate.
    query:
        Original user query for context.

    Returns
    -------
    PipelineResult
        Filtered chunks, per-stage results, and aggregated warnings.
        On any unhandled exception returns original chunks unchanged.
    """
    try:
        return _run_pipeline_inner(chunks, query)
    except Exception:
        logger.warning(
            "Philosophy pipeline failed; returning original chunks",
            exc_info=True,
        )
        return PipelineResult(
            filtered_chunks=list(chunks),
            stage_results=[],
            warnings=["pipeline_error: internal failure, chunks unfiltered"],
            total_latency_ms=0.0,
        )


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------


def _run_pipeline_inner(
    chunks: list[RAGChunk],
    query: str,
) -> PipelineResult:
    """Execute all 4 stages sequentially."""
    pipeline_start = time.perf_counter()
    all_warnings: list[str] = []
    stage_results: list[StageResult] = []

    # Stage 1: Rule-based validation (blocking)
    filtered, s1 = _stage1_rule_validation(chunks)
    stage_results.append(s1)
    all_warnings.extend(s1.warnings)

    # Stage 2: Claim classification (enrichment only)
    s2 = _stage2_claim_classification(filtered)
    stage_results.append(s2)
    all_warnings.extend(s2.warnings)

    # Stage 3: Source-claim alignment (advisory)
    s3 = _stage3_source_alignment(filtered)
    stage_results.append(s3)
    all_warnings.extend(s3.warnings)

    # Stage 4: Logical consistency (advisory)
    s4 = _stage4_logical_consistency(filtered, query)
    stage_results.append(s4)
    all_warnings.extend(s4.warnings)

    total_ms = (time.perf_counter() - pipeline_start) * 1000

    return PipelineResult(
        filtered_chunks=filtered,
        stage_results=stage_results,
        warnings=all_warnings,
        total_latency_ms=round(total_ms, 2),
    )


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
    classifications: dict[str, list[str]] = {}

    for chunk in chunks:
        claim_type = classify_chunk(chunk)
        classifications.setdefault(claim_type.value, []).append(chunk.chunk_id)
        if claim_type == ClaimType.SPECULATION:
            warnings.append(f"claim_speculation: chunk {chunk.chunk_id} classified as speculation")

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
    flagged: list[str] = []

    for chunk in chunks:
        score = _alignment_score(chunk)
        if score > _ALIGNMENT_WARNING_THRESHOLD:
            flagged.append(chunk.chunk_id)
            warnings.append(
                f"alignment_mismatch: chunk {chunk.chunk_id} "
                f"(score={chunk.score:.2f}, len={len(chunk.content.strip())})"
            )

    latency = (time.perf_counter() - start) * 1000

    return StageResult(
        stage_name="source_alignment",
        passed=True,
        warnings=warnings,
        metadata={"flagged_chunks": flagged},
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


def _stage4_logical_consistency(
    chunks: list[RAGChunk],
    query: str,  # noqa: ARG001 - reserved for future semantic contradiction detection
) -> StageResult:
    """Detect contradictory numeric claims and single-source echo.

    Parameters
    ----------
    chunks:
        Filtered chunks to check for consistency.
    query:
        Original user query (reserved for future query-aware contradiction
        detection, e.g. flagging when query asks about X but chunks contradict on X).
    """
    _ = query  # Silence unused-variable linters; see docstring for rationale
    start = time.perf_counter()
    warnings: list[str] = []
    metadata: dict[str, Any] = {}

    # Check 1: Single-source echo
    if len(chunks) > 1:
        unique_sources = {c.file for c in chunks}
        metadata["unique_sources"] = len(unique_sources)
        if len(unique_sources) == 1:
            warnings.append(
                f"single_source_echo: all {len(chunks)} chunks from {next(iter(unique_sources))}"
            )

    # Check 2: Contradictory numeric ranges
    chunk_ranges: list[tuple[str, tuple[float, float]]] = []
    for chunk in chunks:
        for r in _extract_numeric_ranges(chunk.content):
            chunk_ranges.append((chunk.chunk_id, r))

    contradictions: list[str] = []
    for i, (id_a, range_a) in enumerate(chunk_ranges):
        for id_b, range_b in chunk_ranges[i + 1 :]:
            if id_a != id_b and _ranges_contradict(range_a, range_b):
                contradictions.append(
                    f"{id_a}({range_a[0]}-{range_a[1]}) vs {id_b}({range_b[0]}-{range_b[1]})"
                )

    if contradictions:
        metadata["contradictions"] = contradictions
        warnings.append(
            f"numeric_contradiction: {len(contradictions)} conflicting range(s) detected"
        )

    latency = (time.perf_counter() - start) * 1000

    return StageResult(
        stage_name="logical_consistency",
        passed=True,
        warnings=warnings,
        metadata=metadata,
        latency_ms=round(latency, 2),
    )
