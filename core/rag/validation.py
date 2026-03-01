"""Philosophy-agent RAG validation layer.

Deterministic, rule-based validation of RAG chunks before LLM generation.
Feature-gated via ``FEATURE_PHILOSOPHY_VALIDATION``.

Rules enforce:
- **Medical boundary**: reject chunks with therapy/diagnosis language
- **Weasel word detection**: warn on unverifiable claim patterns
- **Empty/malformed filter**: remove chunks with no useful content

All rules operate on ``chunk.content`` (case-insensitive word-boundary matching).
On any internal exception the validator returns original chunks unchanged
(fail-safe: never block LLM generation).

See: .cursor/agents/philosophy-agent.md (claim semantics, falsifiability)
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from core.rag.contracts import RAGChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# V1 Rule patterns
# ---------------------------------------------------------------------------

# Medical boundary: chunks containing these terms are removed.
# Word-boundary matching prevents false positives (e.g. "treatment" in
# "heat treatment" is an accepted risk; the boundary is wellness vs clinical).
_MEDICAL_KEYWORDS: tuple[str, ...] = (
    "diagnose",
    "diagnosis",
    "diagnostic",
    "prescription",
    "prescribe",
    "medication",
    "clinical trial",
    "medical advice",
    "medical treatment",
    "psychiatric",
    "psychotherapy",
)

_MEDICAL_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(kw) for kw in _MEDICAL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Weasel word patterns: advisory warnings (non-blocking).
_WEASEL_PHRASES: tuple[str, ...] = (
    "some say",
    "possibly",
    "it is believed",
    "reportedly",
    "might be",
    "could be",
    "may or may not",
    "some experts",
)

_WEASEL_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _WEASEL_PHRASES) + r")\b",
    re.IGNORECASE,
)

# Minimum content length for a chunk to be useful.
_MIN_CONTENT_LENGTH = 10

# Minimum score threshold for chunk hygiene.
_MIN_SCORE_THRESHOLD = 0.01


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating RAG chunks before LLM generation."""

    passed: bool
    """True if at least one chunk survived filtering."""

    filtered_chunks: list[RAGChunk]
    """Chunks that passed all blocking rules."""

    warnings: list[str] = field(default_factory=list)
    """Non-blocking advisory messages (e.g. weasel word detections)."""

    rejected_count: int = 0
    """Number of chunks removed by blocking rules."""

    validation_latency_ms: int = 0
    """Time spent on validation (milliseconds)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_rag_chunks(
    chunks: list[RAGChunk],
    agent_id: Optional[str] = None,
) -> ValidationResult:
    """Validate RAG chunks against claim semantics and wellness boundaries.

    Runs V1 rules (medical boundary, weasel words, empty filter) on each
    chunk.  Returns a :class:`ValidationResult` with filtered chunks and
    any advisory warnings.

    On internal exception returns original chunks unchanged (fail-safe).

    Parameters
    ----------
    chunks:
        Retrieved RAG chunks to validate.
    agent_id:
        Optional agent identifier (reserved for future per-agent rules).
    """
    try:
        return _run_validation(chunks, agent_id)
    except Exception:
        logger.warning(
            "RAG validation failed; returning original chunks",
            exc_info=True,
        )
        return ValidationResult(
            passed=bool(chunks),
            filtered_chunks=list(chunks),
            warnings=["validation_error: internal failure, chunks unfiltered"],
            rejected_count=0,
            validation_latency_ms=0,
        )


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------


def _run_validation(
    chunks: list[RAGChunk],
    agent_id: Optional[str],
) -> ValidationResult:
    """Execute all V1 rules against chunks."""
    start = time.perf_counter()
    warnings: list[str] = []
    filtered: list[RAGChunk] = []
    rejected = 0

    for chunk in chunks:
        # Rule 1: empty / malformed filter (silent removal)
        if _is_empty_or_malformed(chunk):
            rejected += 1
            continue

        # Rule 2: medical boundary (blocking + warning)
        medical_match = _MEDICAL_RE.search(chunk.content)
        if medical_match:
            warnings.append(
                f"medical_boundary: chunk {chunk.chunk_id} rejected "
                f"(matched '{medical_match.group()}')"
            )
            rejected += 1
            continue

        # Rule 3: weasel word detection (advisory only)
        weasel_match = _WEASEL_RE.search(chunk.content)
        if weasel_match:
            warnings.append(
                f"weasel_word: chunk {chunk.chunk_id} contains "
                f"unverifiable pattern '{weasel_match.group()}'"
            )

        # Chunk passed blocking rules
        filtered.append(chunk)

    latency_ms = int((time.perf_counter() - start) * 1000)

    return ValidationResult(
        passed=bool(filtered),
        filtered_chunks=filtered,
        warnings=warnings,
        rejected_count=rejected,
        validation_latency_ms=latency_ms,
    )


def _is_empty_or_malformed(chunk: RAGChunk) -> bool:
    """Return True if chunk has no useful content or near-zero score."""
    if len(chunk.content.strip()) < _MIN_CONTENT_LENGTH:
        return True
    if chunk.score < _MIN_SCORE_THRESHOLD:
        return True
    return False
