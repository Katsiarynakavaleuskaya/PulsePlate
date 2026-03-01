"""Unit tests for core.rag.validation — philosophy-agent RAG validation layer.

Covers all V1 rules:
- Medical boundary (blocking)
- Weasel word detection (advisory)
- Empty / malformed filter (silent removal)

Plus: ValidationResult contract, fail-safe on internal exception, order preservation.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from core.rag.contracts import RAGChunk
from core.rag.validation import (
    ValidationResult,
    _MIN_CONTENT_LENGTH,
    _MIN_SCORE_THRESHOLD,
    validate_rag_chunks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(
    content: str,
    *,
    chunk_id: str = "c1",
    score: float = 0.85,
    file: str = "test.md",
) -> RAGChunk:
    return RAGChunk(chunk_id=chunk_id, file=file, content=content, score=score)


# ---------------------------------------------------------------------------
# Medical boundary rule
# ---------------------------------------------------------------------------


class TestMedicalBoundaryRule:
    """Chunks with medical/clinical terms are removed (blocking)."""

    @pytest.mark.parametrize(
        "keyword",
        [
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
        ],
    )
    def test_medical_keyword_rejected(self, keyword: str) -> None:
        chunk = _chunk(f"You should seek {keyword} from a professional.")
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1
        assert len(result.filtered_chunks) == 0
        assert any("medical_boundary" in w for w in result.warnings)

    def test_medical_keyword_case_insensitive(self) -> None:
        chunk = _chunk("This DIAGNOSIS requires attention.")
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1

    def test_wellness_content_passes(self) -> None:
        chunk = _chunk("Balanced nutrition supports overall wellness and energy levels.")
        result = validate_rag_chunks([chunk])
        assert result.passed is True
        assert result.rejected_count == 0
        assert len(result.filtered_chunks) == 1

    def test_mixed_chunks_filters_medical_only(self) -> None:
        medical = _chunk("Get a diagnosis from your doctor.", chunk_id="med")
        clean = _chunk("Eat more vegetables for better health.", chunk_id="clean")
        result = validate_rag_chunks([medical, clean])
        assert result.passed is True
        assert result.rejected_count == 1
        assert len(result.filtered_chunks) == 1
        assert result.filtered_chunks[0].chunk_id == "clean"

    def test_all_medical_chunks_rejected(self) -> None:
        c1 = _chunk("Seek medical advice.", chunk_id="c1")
        c2 = _chunk("A prescription is needed.", chunk_id="c2")
        result = validate_rag_chunks([c1, c2])
        assert result.passed is False
        assert result.rejected_count == 2
        assert len(result.filtered_chunks) == 0


# ---------------------------------------------------------------------------
# Weasel word detection (advisory)
# ---------------------------------------------------------------------------


class TestWeaselWordRule:
    """Weasel phrases produce warnings but do NOT remove chunks."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "some say",
            "possibly",
            "it is believed",
            "reportedly",
            "might be",
            "could be",
            "may or may not",
            "some experts",
        ],
    )
    def test_weasel_phrase_produces_warning(self, phrase: str) -> None:
        chunk = _chunk(f"This {phrase} beneficial for wellness.")
        result = validate_rag_chunks([chunk])
        assert result.passed is True
        assert len(result.filtered_chunks) == 1  # NOT removed
        assert any("weasel_word" in w for w in result.warnings)

    def test_clean_text_no_warnings(self) -> None:
        chunk = _chunk("Regular exercise improves cardiovascular health.")
        result = validate_rag_chunks([chunk])
        assert len(result.warnings) == 0

    def test_multiple_weasel_chunks_all_warned(self) -> None:
        c1 = _chunk("Some say it works well.", chunk_id="c1")
        c2 = _chunk("It is believed to help.", chunk_id="c2")
        result = validate_rag_chunks([c1, c2])
        assert len(result.filtered_chunks) == 2  # Both kept
        weasel_warnings = [w for w in result.warnings if "weasel_word" in w]
        assert len(weasel_warnings) == 2


# ---------------------------------------------------------------------------
# Empty / malformed chunk filter
# ---------------------------------------------------------------------------


class TestEmptyChunkFilter:
    """Chunks with no useful content or near-zero score are silently removed."""

    def test_empty_content_removed(self) -> None:
        chunk = _chunk("", chunk_id="empty")
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1
        assert len(result.filtered_chunks) == 0

    def test_short_content_removed(self) -> None:
        chunk = _chunk("tiny", chunk_id="short")
        assert len("tiny") < _MIN_CONTENT_LENGTH
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1

    def test_whitespace_only_removed(self) -> None:
        chunk = _chunk("         ", chunk_id="ws")
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1

    def test_low_score_removed(self) -> None:
        chunk = _chunk(
            "This has enough content but a very low score.",
            chunk_id="low",
            score=0.005,
        )
        assert chunk.score < _MIN_SCORE_THRESHOLD
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1

    def test_zero_score_removed(self) -> None:
        chunk = _chunk("Normal length content here.", chunk_id="zero", score=0.0)
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1

    def test_valid_chunk_passes(self) -> None:
        chunk = _chunk("This content is long enough and has a decent score.", score=0.5)
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 0
        assert len(result.filtered_chunks) == 1

    def test_borderline_length_passes(self) -> None:
        content = "x" * _MIN_CONTENT_LENGTH
        chunk = _chunk(content, score=0.5)
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 0

    def test_borderline_score_passes(self) -> None:
        chunk = _chunk(
            "Content with enough characters for the filter.",
            score=_MIN_SCORE_THRESHOLD,
        )
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 0


# ---------------------------------------------------------------------------
# ValidationResult contract
# ---------------------------------------------------------------------------


class TestValidationResultContract:
    """ValidationResult fields are consistent and complete."""

    def test_empty_input_returns_passed_false(self) -> None:
        result = validate_rag_chunks([])
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.rejected_count == 0
        assert result.validation_latency_ms >= 0

    def test_all_pass_returns_passed_true(self) -> None:
        chunks = [
            _chunk("Good wellness content about sleep.", chunk_id="a"),
            _chunk("Hydration is important for health.", chunk_id="b"),
        ]
        result = validate_rag_chunks(chunks)
        assert result.passed is True
        assert len(result.filtered_chunks) == 2
        assert result.rejected_count == 0

    def test_latency_is_non_negative(self) -> None:
        result = validate_rag_chunks([_chunk("Some valid content here.")])
        assert result.validation_latency_ms >= 0

    def test_order_preserved(self) -> None:
        """Filtered chunks maintain input order."""
        chunks = [
            _chunk("First valid chunk content.", chunk_id="1"),
            _chunk("Get a diagnosis.", chunk_id="2"),  # medical → removed
            _chunk("Third valid chunk content.", chunk_id="3"),
        ]
        result = validate_rag_chunks(chunks)
        assert [c.chunk_id for c in result.filtered_chunks] == ["1", "3"]

    def test_agent_id_accepted(self) -> None:
        """agent_id parameter is accepted without error (reserved for future)."""
        chunk = _chunk("Valid wellness content for testing.")
        result = validate_rag_chunks([chunk], agent_id="philosophy-agent")
        assert result.passed is True


# ---------------------------------------------------------------------------
# Fail-safe on internal exception
# ---------------------------------------------------------------------------


class TestValidationFailSafe:
    """On internal exception, original chunks are returned unchanged."""

    def test_internal_error_returns_originals(self) -> None:
        chunks = [_chunk("Some normal wellness content.")]
        with patch(
            "core.rag.validation._run_validation",
            side_effect=RuntimeError("boom"),
        ):
            result = validate_rag_chunks(chunks)
        assert result.passed is True
        assert len(result.filtered_chunks) == 1
        assert result.filtered_chunks[0] is chunks[0]
        assert any("validation_error" in w for w in result.warnings)

    def test_internal_error_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        chunks = [_chunk("More wellness content here.")]
        with (
            caplog.at_level(logging.WARNING, logger="core.rag.validation"),
            patch(
                "core.rag.validation._run_validation",
                side_effect=RuntimeError("internal"),
            ),
        ):
            validate_rag_chunks(chunks)
        assert "RAG validation failed" in caplog.text
