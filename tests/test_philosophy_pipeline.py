"""Unit tests for philosophy validation pipeline (core/rag/philosophy_pipeline.py).

Tests cover all 4 stages individually plus pipeline-level integration:
- Stage 1: Rule validation delegation to validation.py
- Stage 2: Claim classification (NUTRITION_FACT / RECOMMENDATION / SPECULATION / UNKNOWN)
- Stage 3: Source-claim alignment (score-vs-content mismatch detection)
- Stage 4: Logical consistency (contradictions, single-source echo)
- Pipeline: All stages run, fail-safe, warning accumulation, latency
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.rag.contracts import RAGChunk
from core.rag.philosophy_pipeline import (
    ClaimType,
    PipelineResult,
    _alignment_score,
    _extract_anchored_numeric_ranges,
    _extract_context_terms,
    _extract_numeric_ranges,
    _extract_query_anchors,
    _extract_query_terms,
    _query_binding_is_ambiguous,
    _ranges_contradict,
    _stage1_rule_validation,
    _stage2_claim_classification,
    _stage3_source_alignment,
    _stage4_logical_consistency,
    classify_chunk,
    run_pipeline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(
    chunk_id: str = "c1",
    content: str = "Some test content for chunk.",
    score: float = 0.85,
    file: str = "docs/test.md",
) -> RAGChunk:
    return RAGChunk(chunk_id=chunk_id, file=file, content=content, score=score)


# ===========================================================================
# Stage 1: Rule validation (delegates to validation.py)
# ===========================================================================


class TestStage1RuleValidation:
    """Stage 1 delegates to validate_rag_chunks and wraps the result."""

    def test_delegation_filters_medical_chunks(self) -> None:
        """Medical chunks are rejected by the underlying validator."""
        chunks = [
            _chunk("c1", "You need a diagnosis from a doctor.", 0.9),
            _chunk("c2", "Balanced nutrition supports wellness.", 0.85),
        ]
        filtered, result = _stage1_rule_validation(chunks)

        assert result.stage_name == "rule_validation"
        assert len(filtered) == 1
        assert filtered[0].chunk_id == "c2"
        assert result.metadata["rejected_count"] == 1
        assert any("medical_boundary" in w for w in result.warnings)

    def test_clean_chunks_pass_through(self) -> None:
        """All clean chunks survive stage 1."""
        chunks = [
            _chunk("c1", "Hydration improves energy levels.", 0.88),
            _chunk("c2", "Sleep quality affects metabolism.", 0.82),
        ]
        filtered, result = _stage1_rule_validation(chunks)

        assert result.stage_name == "rule_validation"
        assert result.passed is True
        assert len(filtered) == 2
        assert result.metadata["rejected_count"] == 0

    def test_empty_input_returns_empty(self) -> None:
        """Empty chunk list produces empty result."""
        filtered, result = _stage1_rule_validation([])

        assert result.stage_name == "rule_validation"
        assert filtered == []
        assert result.passed is False
        assert result.metadata["rejected_count"] == 0


# ===========================================================================
# Stage 2: Claim classification
# ===========================================================================


class TestClassifyChunk:
    """classify_chunk() categorises individual chunks."""

    def test_nutrition_fact(self) -> None:
        chunk = _chunk(content="Adults need approximately 2000 kcal per day.")
        assert classify_chunk(chunk) == ClaimType.NUTRITION_FACT

    def test_nutrition_fact_bmi_reference(self) -> None:
        chunk = _chunk(content="A healthy BMI 18.5 to 24.9 range is typical.")
        assert classify_chunk(chunk) == ClaimType.NUTRITION_FACT

    def test_recommendation(self) -> None:
        chunk = _chunk(content="You should aim for at least 150 minutes of activity.")
        assert classify_chunk(chunk) == ClaimType.RECOMMENDATION

    def test_speculation(self) -> None:
        chunk = _chunk(content="Some experts say this approach might be effective.")
        assert classify_chunk(chunk) == ClaimType.SPECULATION

    def test_unknown_plain_text(self) -> None:
        chunk = _chunk(content="The weather is nice today and birds are singing.")
        assert classify_chunk(chunk) == ClaimType.UNKNOWN

    def test_priority_nutrition_over_recommendation(self) -> None:
        """NUTRITION_FACT takes priority over RECOMMENDATION."""
        chunk = _chunk(content="You should aim for 2000 kcal per day.")
        assert classify_chunk(chunk) == ClaimType.NUTRITION_FACT

    def test_priority_recommendation_over_speculation(self) -> None:
        """RECOMMENDATION takes priority over SPECULATION."""
        chunk = _chunk(content="Some experts say you should consider this approach.")
        assert classify_chunk(chunk) == ClaimType.RECOMMENDATION


class TestStage2ClaimClassification:
    """Stage 2 classifies and produces warnings for speculation."""

    def test_speculation_produces_warning(self) -> None:
        chunks = [
            _chunk("c1", "Some say this diet might be beneficial."),
        ]
        result = _stage2_claim_classification(chunks)

        assert result.stage_name == "claim_classification"
        assert result.passed is True
        assert len(result.warnings) == 1
        assert "claim_speculation" in result.warnings[0]
        assert "c1" in result.warnings[0]

    def test_clean_chunks_no_warnings(self) -> None:
        chunks = [
            _chunk("c1", "Adults need approximately 2000 kcal per day."),
            _chunk("c2", "Sleep quality affects metabolic health strongly."),
        ]
        result = _stage2_claim_classification(chunks)

        assert result.passed is True
        assert result.warnings == []

    def test_classification_distribution_in_metadata(self) -> None:
        chunks = [
            _chunk("c1", "Protein intake is 50 grams daily."),
            _chunk("c2", "You should consider stretching routines."),
            _chunk("c3", "The weather is nice today outside."),
        ]
        result = _stage2_claim_classification(chunks)

        dist = result.metadata["classifications"]
        assert "c1" in dist.get("nutrition_fact", [])
        assert "c2" in dist.get("recommendation", [])
        assert "c3" in dist.get("unknown", [])

    def test_empty_input(self) -> None:
        result = _stage2_claim_classification([])
        assert result.passed is True
        assert result.warnings == []
        assert result.metadata["classifications"] == {}


# ===========================================================================
# Stage 3: Source-claim alignment
# ===========================================================================


class TestAlignmentScore:
    """_alignment_score detects score-vs-content mismatches."""

    def test_high_score_very_short_text(self) -> None:
        chunk = _chunk(content="Short.", score=0.9)
        assert _alignment_score(chunk) == 0.9

    def test_high_score_short_text(self) -> None:
        chunk = _chunk(content="A slightly longer text.", score=0.8)
        assert _alignment_score(chunk) == 0.8

    def test_medium_score_very_short_text(self) -> None:
        chunk = _chunk(content="Tiny.", score=0.6)
        assert _alignment_score(chunk) == 0.7

    def test_normal_chunk_zero_score(self) -> None:
        chunk = _chunk(
            content="This is a perfectly normal chunk with enough content.",
            score=0.85,
        )
        assert _alignment_score(chunk) == 0.0

    def test_low_score_short_text_zero(self) -> None:
        chunk = _chunk(content="Short.", score=0.3)
        assert _alignment_score(chunk) == 0.0


class TestStage3SourceAlignment:
    """Stage 3 flags score-content mismatches."""

    def test_flags_high_score_short_text(self) -> None:
        chunks = [
            _chunk("c1", "Short.", score=0.9),
            _chunk("c2", "This is a normal chunk with decent content.", score=0.85),
        ]
        result = _stage3_source_alignment(chunks)

        assert result.stage_name == "source_alignment"
        assert result.passed is True  # advisory only
        assert len(result.warnings) == 1
        assert "alignment_mismatch" in result.warnings[0]
        assert "c1" in result.warnings[0]
        assert "c1" in result.metadata["flagged_chunks"]

    def test_no_flags_for_normal_chunks(self) -> None:
        chunks = [
            _chunk("c1", "Good content with substance and detail.", score=0.8),
            _chunk("c2", "Another solid chunk with real information.", score=0.7),
        ]
        result = _stage3_source_alignment(chunks)

        assert result.warnings == []
        assert result.metadata["flagged_chunks"] == []

    def test_empty_input(self) -> None:
        result = _stage3_source_alignment([])
        assert result.warnings == []
        assert result.metadata["flagged_chunks"] == []


# ===========================================================================
# Stage 4: Logical consistency
# ===========================================================================


class TestNumericRangeExtraction:
    """_extract_numeric_ranges and _ranges_contradict."""

    def test_extracts_simple_range(self) -> None:
        ranges = _extract_numeric_ranges("BMI 18.5-24.9 is healthy")
        assert ranges == [(18.5, 24.9)]

    def test_extracts_multiple_ranges(self) -> None:
        ranges = _extract_numeric_ranges("BMI 18.5-24.9 and 25-30 range")
        assert len(ranges) == 2
        assert (18.5, 24.9) in ranges
        assert (25.0, 30.0) in ranges

    def test_ignores_reversed_range(self) -> None:
        """Ranges where low >= high are skipped."""
        ranges = _extract_numeric_ranges("Values 30-10 are wrong")
        assert ranges == []

    def test_no_ranges_found(self) -> None:
        ranges = _extract_numeric_ranges("No numbers here at all.")
        assert ranges == []

    def test_unicode_en_dash(self) -> None:
        ranges = _extract_numeric_ranges("BMI 18.5\u201324.9 is healthy")
        assert ranges == [(18.5, 24.9)]

    def test_ranges_contradict_non_overlapping(self) -> None:
        assert _ranges_contradict((10.0, 20.0), (25.0, 30.0)) is True

    def test_ranges_do_not_contradict_overlapping(self) -> None:
        assert _ranges_contradict((10.0, 25.0), (20.0, 30.0)) is False

    def test_ranges_touching_do_not_contradict(self) -> None:
        assert _ranges_contradict((10.0, 20.0), (20.0, 30.0)) is False


class TestQueryAwareAnchors:
    """Stage 4 query anchors suppress ambiguity before contradiction warnings."""

    def test_extract_query_terms_drops_generic_tokens(self) -> None:
        query_terms = _extract_query_terms("What is a healthy normal range?")

        assert query_terms == set()

    def test_extract_query_terms_keeps_two_letter_domain_acronyms(self) -> None:
        query_terms = _extract_query_terms("What BP range is normal?")

        assert "bp" in query_terms

    def test_extract_query_terms_keeps_alphanumeric_medical_tokens(self) -> None:
        query_terms = _extract_query_terms("A1C and LDL-C targets")

        assert "a1c" in query_terms
        assert "ldl-c" in query_terms

    def test_extract_query_terms_keeps_alphanumeric_nutrition_tokens(self) -> None:
        query_terms = _extract_query_terms("What B12 range is normal?")

        assert "b12" in query_terms

    def test_extract_query_terms_supports_unicode_letters(self) -> None:
        query_terms = _extract_query_terms("Índice BMI y presión")

        assert "índice" in query_terms
        assert "presión" in query_terms

    def test_extract_query_anchors_returns_topic_specific_terms(self) -> None:
        query_terms = _extract_query_terms("What is the BMI range for adults?")

        anchors = _extract_query_anchors("Healthy BMI is 18.5-24.9 for adults.", query_terms)

        assert "bmi" in anchors

    def test_query_binding_is_ambiguous_when_each_range_has_distinct_query_anchor(self) -> None:
        """Conflicting topic anchors should keep stage 4 in the ambiguous path."""

        assert (
            _query_binding_is_ambiguous(
                {"bmi", "vitamin"},
                {"bmi", "protein"},
                {"adult"},
                {"adult"},
                {"bmi", "vitamin", "protein"},
            )
            is True
        )

    def test_extract_anchored_numeric_ranges_binds_anchors_per_range(self) -> None:
        query_terms = _extract_query_terms("What is the BMI range?")
        anchored_ranges = _extract_anchored_numeric_ranges(
            "Healthy BMI is 18.5-24.9 and protein intake is 30-40 grams per meal.",
            query_terms,
        )

        first_range, first_anchors, first_context_terms = anchored_ranges[0]
        second_range, second_anchors, second_context_terms = anchored_ranges[1]

        assert first_range == (18.5, 24.9)
        assert first_anchors == {"bmi"}
        assert isinstance(first_context_terms, set)

        assert second_range == (30.0, 40.0)
        assert second_anchors == set()
        assert {"grams", "meal"} <= second_context_terms

    def test_extract_anchored_numeric_ranges_skips_reversed_ranges(self) -> None:
        query_terms = _extract_query_terms("What BMI range is normal?")

        anchored_ranges = _extract_anchored_numeric_ranges("BMI 30-10 is invalid.", query_terms)

        assert anchored_ranges == []

    def test_extract_context_terms_preserves_two_letter_disambiguators(self) -> None:
        context_terms = _extract_context_terms("Protein intake is 0.8-1.2 grams per kg per day.")

        assert "kg" in context_terms


class TestStage4LogicalConsistency:
    """Stage 4 detects contradictions and single-source echo."""

    def test_single_source_echo_detected(self) -> None:
        chunks = [
            _chunk("c1", "Fact one about health.", 0.9, file="docs/a.md"),
            _chunk("c2", "Fact two about health.", 0.8, file="docs/a.md"),
        ]
        result = _stage4_logical_consistency(chunks, "health query")

        assert result.stage_name == "logical_consistency"
        assert any("single_source_echo" in w for w in result.warnings)
        assert result.metadata["unique_sources"] == 1

    def test_diverse_sources_no_echo(self) -> None:
        chunks = [
            _chunk("c1", "Fact one about health.", 0.9, file="docs/a.md"),
            _chunk("c2", "Fact two about health.", 0.8, file="docs/b.md"),
        ]
        result = _stage4_logical_consistency(chunks, "health query")

        assert not any("single_source_echo" in w for w in result.warnings)
        assert result.metadata["unique_sources"] == 2

    def test_contradictory_numeric_ranges(self) -> None:
        chunks = [
            _chunk("c1", "Healthy BMI is 18.5-24.9 for adults.", 0.9),
            _chunk("c2", "Normal BMI range is 30-40 in this system.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "BMI query")

        assert any("numeric_contradiction" in w for w in result.warnings)
        assert len(result.metadata["contradictions"]) >= 1

    def test_contradictory_numeric_ranges_detected_for_two_letter_acronym_query(self) -> None:
        chunks = [
            _chunk("c1", "Normal BP range is 90-120 for adults.", 0.9),
            _chunk("c2", "Normal BP range is 140-180 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What BP range is normal?")

        assert any("numeric_contradiction" in w for w in result.warnings)
        assert len(result.metadata["contradictions"]) >= 1

    def test_contradiction_suppressed_when_query_targets_other_topic(self) -> None:
        chunks = [
            _chunk("c1", "Healthy BMI is 18.5-24.9 for adults.", 0.9),
            _chunk("c2", "Normal BMI range is 30-40 in this system.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "protein intake query")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_when_query_binding_is_ambiguous(self) -> None:
        chunks = [
            _chunk("c1", "Healthy BMI is 18.5-24.9 for adults.", 0.9),
            _chunk("c2", "Normal BMI range is 30-40 in this system.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What is a normal healthy range?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_mixed_topic_query(self) -> None:
        chunks = [
            _chunk("c1", "Healthy BMI is 18.5-24.9 for adults.", 0.9),
            _chunk("c2", "Normal blood pressure range is 140-180 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(
            chunks,
            "What BMI and blood pressure ranges are normal for adults?",
        )

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_same_audience_different_metric(self) -> None:
        chunks = [
            _chunk("c1", "Healthy BMI is 18.5-24.9 for adults.", 0.9),
            _chunk("c2", "Protein intake is 30-40 grams per meal for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What is the BMI range for adults?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_irrelevant_range_inside_multi_topic_chunk(self) -> None:
        chunks = [
            _chunk(
                "c1",
                "Healthy BMI is 18.5-24.9 and protein intake is 30-40 grams per meal.",
                0.9,
            ),
            _chunk("c2", "Normal BMI range is 20-22 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What is the BMI range for adults?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_broad_vitamin_query_with_specific_mismatch(self) -> None:
        chunks = [
            _chunk("c1", "Normal vitamin B12 range is 200-900 for adults.", 0.9),
            _chunk("c2", "Normal vitamin D range is 1000-1400 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What vitamin range is normal?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_partial_lexical_overlap(self) -> None:
        chunks = [
            _chunk("c1", "Normal blood pressure range is 90-120 for adults.", 0.9),
            _chunk("c2", "Normal blood sugar range is 140-180 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What blood pressure range is normal?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_cohort_specific_protein_ranges(self) -> None:
        chunks = [
            _chunk("c1", "Protein intake is 20-40 grams per meal for adults.", 0.9),
            _chunk("c2", "Protein intake is 5-10 grams per meal for children.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What protein intake range is normal?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradiction_suppressed_for_per_meal_vs_per_kg_ranges(self) -> None:
        chunks = [
            _chunk("c1", "Protein intake is 20-40 grams per meal for adults.", 0.9),
            _chunk("c2", "Protein intake is 0.8-1.2 grams per kg per day for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What protein intake range is normal?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_contradictory_numeric_ranges_detected_for_b12_query(self) -> None:
        chunks = [
            _chunk("c1", "Normal B12 range is 200-900 for adults.", 0.9),
            _chunk("c2", "Normal B12 range is 1000-1400 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What B12 range is normal?")

        assert any("numeric_contradiction" in w for w in result.warnings)
        assert len(result.metadata["contradictions"]) >= 1

    def test_contradictory_numeric_ranges_detected_for_subset_anchor_binding(self) -> None:
        chunks = [
            _chunk("c1", "Normal vitamin B12 range is 200-900 for adults.", 0.9),
            _chunk("c2", "Normal B12 range is 1000-1400 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What vitamin B12 range is normal?")

        assert any("numeric_contradiction" in w for w in result.warnings)
        assert len(result.metadata["contradictions"]) >= 1

    def test_contradictory_numeric_ranges_detected_for_benign_b12_qualifiers(self) -> None:
        chunks = [
            _chunk("c1", "Normal serum B12 range is 200-900 for adults.", 0.9),
            _chunk("c2", "Normal vitamin B12 range is 1000-1400 for adults.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What vitamin B12 range is normal?")

        assert any("numeric_contradiction" in w for w in result.warnings)
        assert len(result.metadata["contradictions"]) >= 1

    def test_contradiction_suppressed_for_cohort_specific_bmi_ranges(self) -> None:
        chunks = [
            _chunk("c1", "Normal adult BMI range is 18.5-24.9.", 0.9),
            _chunk("c2", "Normal child BMI range is 14-18.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "What BMI range is normal?")

        assert not any("numeric_contradiction" in w for w in result.warnings)
        assert "contradictions" not in result.metadata

    def test_no_contradictions_consistent_ranges(self) -> None:
        chunks = [
            _chunk("c1", "BMI 18.5-24.9 is normal weight.", 0.9),
            _chunk("c2", "BMI 20.0-22.0 is the ideal sub-range.", 0.8),
        ]
        result = _stage4_logical_consistency(chunks, "BMI query")

        assert not any("numeric_contradiction" in w for w in result.warnings)

    def test_single_chunk_no_echo(self) -> None:
        """Single chunk cannot produce echo or contradiction."""
        chunks = [_chunk("c1", "BMI 18.5-24.9 is healthy.", 0.9)]
        result = _stage4_logical_consistency(chunks, "query")

        assert result.warnings == []

    def test_empty_input(self) -> None:
        result = _stage4_logical_consistency([], "query")
        assert result.warnings == []
        assert result.passed is True


# ===========================================================================
# Pipeline integration (run_pipeline)
# ===========================================================================


class TestRunPipeline:
    """Integration tests for the full run_pipeline entry point."""

    def test_all_four_stages_run(self) -> None:
        """Pipeline produces 4 stage results."""
        chunks = [
            _chunk("c1", "Adults need approximately 2000 kcal per day.", 0.9, "a.md"),
            _chunk("c2", "Sleep quality affects metabolic health.", 0.8, "b.md"),
        ]
        result = run_pipeline(chunks, "nutrition query")

        assert isinstance(result, PipelineResult)
        assert len(result.stage_results) == 4
        stage_names = [s.stage_name for s in result.stage_results]
        assert stage_names == [
            "rule_validation",
            "claim_classification",
            "source_alignment",
            "logical_consistency",
        ]

    def test_fail_safe_returns_original_chunks(self) -> None:
        """On internal exception, original chunks returned unchanged."""
        chunks = [_chunk("c1", "Some valid content here.", 0.9)]

        with patch(
            "core.rag.philosophy_pipeline._run_pipeline_inner",
            side_effect=RuntimeError("boom"),
        ):
            result = run_pipeline(chunks, "query")

        assert len(result.filtered_chunks) == 1
        assert result.filtered_chunks[0].chunk_id == "c1"
        assert result.stage_results == []
        assert any("pipeline_error" in w for w in result.warnings)

    def test_warning_accumulation(self) -> None:
        """Warnings from all stages are accumulated."""
        chunks = [
            # This chunk has speculation AND high score + short text
            _chunk("c1", "Some say this is true.", 0.9, "a.md"),
            _chunk("c2", "Some say that is true.", 0.9, "a.md"),
        ]
        result = run_pipeline(chunks, "query")

        # Should have: speculation warnings + single_source_echo
        assert len(result.warnings) >= 2
        # Stage 2 speculation + stage 4 echo at minimum
        warning_text = " ".join(result.warnings)
        assert "claim_speculation" in warning_text
        assert "single_source_echo" in warning_text

    def test_latency_tracked(self) -> None:
        """Pipeline records total and per-stage latency."""
        chunks = [_chunk("c1", "Hydration improves energy levels.", 0.85)]
        result = run_pipeline(chunks, "query")

        assert result.total_latency_ms >= 0
        for stage in result.stage_results:
            assert stage.latency_ms >= 0

    def test_stage1_blocking_propagates(self) -> None:
        """Chunks rejected by stage 1 are not seen by stages 2-4."""
        chunks = [
            _chunk("c1", "You need a diagnosis from a doctor.", 0.9, "a.md"),
            _chunk("c2", "Balanced nutrition supports wellness.", 0.85, "b.md"),
        ]
        result = run_pipeline(chunks, "query")

        # Only c2 survives stage 1
        assert len(result.filtered_chunks) == 1
        assert result.filtered_chunks[0].chunk_id == "c2"

        # Stage 2 classification should only see c2
        s2 = result.stage_results[1]
        all_classified_ids = []
        for ids in s2.metadata["classifications"].values():
            all_classified_ids.extend(ids)
        assert "c1" not in all_classified_ids
        assert "c2" in all_classified_ids

    def test_empty_input(self) -> None:
        """Empty input produces empty pipeline result."""
        result = run_pipeline([], "query")

        assert result.filtered_chunks == []
        assert len(result.stage_results) == 4
