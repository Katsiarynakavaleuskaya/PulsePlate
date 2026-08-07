"""Unit tests for core.rag.validation — philosophy-agent RAG validation layer.

Covers all V1 rules:
- Medical boundary (blocking)
- Weasel word detection (advisory)
- Empty / malformed filter (silent removal)

Plus: ValidationResult contract, fail-closed on internal exception, order preservation.
"""

from __future__ import annotations

import logging
import math
import sys
from decimal import Decimal
from fractions import Fraction
from typing import cast
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


class _IntScore(int):
    pass


class _FloatScore(float):
    pass


class _HostileScore:
    def __init__(self) -> None:
        self.invocations: list[str] = []

    def __float__(self) -> float:
        self.invocations.append("__float__")
        raise AssertionError("validator must not coerce unsupported scores")

    def __lt__(self, other: object) -> bool:
        self.invocations.append("__lt__")
        raise AssertionError("validator must not compare unsupported scores")


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

    def test_all_medical_chunks_rejected(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        c1 = _chunk(
            "Seek medical advice SENTINEL_MEDICAL_CONTENT_ONE.",
            chunk_id="SENTINEL_MEDICAL_ID_ONE",
            score=0.73,
            file="/private/SENTINEL_MEDICAL_PATH_ONE.md",
        )
        c2 = _chunk(
            "A prescription is needed SENTINEL_MEDICAL_CONTENT_TWO.",
            chunk_id="SENTINEL_MEDICAL_ID_TWO",
            score=0.74,
            file="/private/SENTINEL_MEDICAL_PATH_TWO.md",
        )
        with caplog.at_level(logging.DEBUG, logger="core.rag.validation"):
            result = validate_rag_chunks([c1, c2])
        assert result.passed is False
        assert result.rejected_count == 2
        assert len(result.filtered_chunks) == 0
        assert result.warnings == ["medical_boundary", "medical_boundary"]
        assert [record for record in caplog.records if record.name == "core.rag.validation"] == []
        diagnostic_payload = repr(result.warnings) + caplog.text
        for sentinel in (
            "SENTINEL_MEDICAL",
            "/private/",
            "medical advice",
            "prescription",
            "0.73",
            "0.74",
        ):
            assert sentinel not in diagnostic_payload


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

    def test_multiple_weasel_chunks_all_warned(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        c1 = _chunk(
            "Some say SENTINEL_WEASEL_CONTENT_ONE works well.",
            chunk_id="SENTINEL_WEASEL_ID_ONE",
            score=0.81,
            file="/private/SENTINEL_WEASEL_PATH_ONE.md",
        )
        c2 = _chunk(
            "It is believed SENTINEL_WEASEL_CONTENT_TWO helps.",
            chunk_id="SENTINEL_WEASEL_ID_TWO",
            score=0.82,
            file="/private/SENTINEL_WEASEL_PATH_TWO.md",
        )
        with caplog.at_level(logging.DEBUG, logger="core.rag.validation"):
            result = validate_rag_chunks([c1, c2])
        assert len(result.filtered_chunks) == 2  # Both kept
        assert result.warnings == ["weasel_word", "weasel_word"]
        assert [record for record in caplog.records if record.name == "core.rag.validation"] == []
        diagnostic_payload = repr(result.warnings) + caplog.text
        for sentinel in (
            "SENTINEL_WEASEL",
            "/private/",
            "Some say",
            "It is believed",
            "0.81",
            "0.82",
        ):
            assert sentinel not in diagnostic_payload


# ---------------------------------------------------------------------------
# Empty / malformed chunk filter
# ---------------------------------------------------------------------------


class TestEmptyChunkFilter:
    """Chunks with no useful content or invalid scores are silently removed."""

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

    def test_negative_zero_score_removed(self) -> None:
        chunk = _chunk("Normal length content here.", chunk_id="negative-zero", score=-0.0)
        result = validate_rag_chunks([chunk])
        assert result.rejected_count == 1

    @pytest.mark.parametrize("score", [math.nan, math.inf, -math.inf])
    def test_nonfinite_score_removed(self, score: float) -> None:
        chunk = _chunk("Normal length content here.", chunk_id="nonfinite", score=score)
        result = validate_rag_chunks([chunk])
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.rejected_count == 1
        assert result.warnings == []

    @pytest.mark.parametrize(
        "score",
        [
            pytest.param(False, id="bool-false"),
            pytest.param(True, id="bool-true"),
            pytest.param(_IntScore(1), id="int-subclass"),
            pytest.param(_FloatScore(0.5), id="float-subclass"),
            pytest.param(Decimal("0.5"), id="decimal"),
            pytest.param(Fraction(1, 2), id="fraction"),
            pytest.param("0.5", id="string"),
            pytest.param(None, id="none"),
            pytest.param(complex(0.5, 0.0), id="complex"),
        ],
    )
    def test_unsupported_runtime_score_type_removed(self, score: object) -> None:
        chunk = _chunk(
            "Normal length content here.",
            chunk_id="unsupported",
            score=cast(float, score),
        )
        result = validate_rag_chunks([chunk])
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.rejected_count == 1
        assert result.warnings == []

    def test_hostile_score_removed_without_invoking_its_methods(self) -> None:
        score = _HostileScore()
        chunk = _chunk(
            "Normal length content here.",
            chunk_id="hostile",
            score=cast(float, score),
        )
        result = validate_rag_chunks([chunk])
        assert score.invocations == []
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.rejected_count == 1
        assert result.warnings == []

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

    @pytest.mark.parametrize(
        "score",
        [
            pytest.param(_MIN_SCORE_THRESHOLD, id="threshold-float"),
            pytest.param(sys.float_info.max, id="max-finite-float"),
            pytest.param(1, id="exact-int"),
            pytest.param(10**300, id="large-finite-int"),
        ],
    )
    def test_exact_builtin_score_at_or_above_threshold_passes(
        self,
        score: int | float,
    ) -> None:
        chunk = _chunk(
            "Content with enough characters for the filter.",
            score=score,
        )
        result = validate_rag_chunks([chunk])
        assert result.passed is True
        assert result.filtered_chunks == [chunk]
        assert result.rejected_count == 0

    @pytest.mark.parametrize("score", [10**400, -(10**400)])
    def test_unrepresentable_exact_int_score_removed_locally(self, score: int) -> None:
        chunk = _chunk(
            "Content with an unrepresentable integer score.",
            chunk_id="unrepresentable-int",
            score=score,
        )
        result = validate_rag_chunks([chunk])
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.rejected_count == 1
        assert result.warnings == []

    def test_mixed_runtime_scores_preserve_exact_survivor_order(self) -> None:
        chunks = [
            _chunk("First finite chunk content.", chunk_id="exact-float", score=0.5),
            _chunk(
                "Boolean score content is rejected.",
                chunk_id="bool",
                score=cast(float, True),
            ),
            _chunk("Exact integer chunk content.", chunk_id="exact-int", score=1),
            _chunk("NaN chunk content is rejected.", chunk_id="nan", score=math.nan),
            _chunk(
                "Decimal score content is rejected.",
                chunk_id="decimal",
                score=cast(float, Decimal("0.8")),
            ),
            _chunk(
                "Large finite integer chunk content.",
                chunk_id="large-finite-int",
                score=10**300,
            ),
            _chunk(
                "Unrepresentable integer content is rejected.",
                chunk_id="unrepresentable-int",
                score=10**400,
            ),
            _chunk(
                "Float subclass content is rejected.",
                chunk_id="float-subclass",
                score=cast(float, _FloatScore(0.9)),
            ),
        ]
        result = validate_rag_chunks(chunks)
        assert result.passed is True
        assert [chunk.chunk_id for chunk in result.filtered_chunks] == [
            "exact-float",
            "exact-int",
            "large-finite-int",
        ]
        assert result.rejected_count == 5
        assert result.warnings == []


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
# Fail-closed on internal exception
# ---------------------------------------------------------------------------


class TestValidationFailClosed:
    """On internal exception, all unvalidated chunks are rejected."""

    def test_internal_error_rejects_all_chunks(self) -> None:
        chunks = [
            _chunk("You need a diagnosis from a doctor.", chunk_id="med"),
            _chunk("Balanced nutrition supports wellness.", chunk_id="clean"),
        ]
        with patch(
            "core.rag.validation._run_validation",
            side_effect=RuntimeError("boom"),
        ):
            result = validate_rag_chunks(chunks)
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.warnings == ["validation_error: internal failure, no chunks accepted"]
        assert result.rejected_count == len(chunks)
        assert result.validation_latency_ms == 0

    def test_internal_error_with_empty_input_accepts_no_chunks(self) -> None:
        with patch(
            "core.rag.validation._run_validation",
            side_effect=RuntimeError("boom"),
        ):
            result = validate_rag_chunks([])
        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.warnings == ["validation_error: internal failure, no chunks accepted"]
        assert result.rejected_count == 0
        assert result.validation_latency_ms == 0

    def test_internal_error_logs_fail_closed_warning(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        chunks = [
            _chunk(
                "sentinel-validation-content",
                chunk_id="sentinel-validation-id",
                score=0.73,
                file="/private/sentinel-validation.md",
            )
        ]
        with (
            caplog.at_level(logging.WARNING, logger="core.rag.validation"),
            patch(
                "core.rag.validation._run_validation",
                side_effect=RuntimeError("sentinel-validation-exception"),
            ),
        ):
            result = validate_rag_chunks(
                chunks,
                agent_id="sentinel-validation-query",
            )

        assert result.passed is False
        assert result.filtered_chunks == []
        assert result.warnings == ["validation_error: internal failure, no chunks accepted"]
        assert result.rejected_count == 1
        assert result.validation_latency_ms == 0
        records = [record for record in caplog.records if record.name == "core.rag.validation"]
        assert len(records) == 1
        record = records[0]
        assert record.getMessage() == "RAG validation failed; rejecting all chunks"
        assert record.levelno == logging.WARNING
        assert record.exc_info is None
        for sentinel in (
            "sentinel-validation-exception",
            "sentinel-validation-id",
            "/private/sentinel-validation.md",
            "sentinel-validation-content",
            "sentinel-validation-query",
            "0.73",
        ):
            assert sentinel not in caplog.text
