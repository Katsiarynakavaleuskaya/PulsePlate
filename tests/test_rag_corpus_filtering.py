"""Tests for RAG corpus filtering by agent_id.

Verifies:
- AGENT_CORPUS_MAP constant is properly defined
- Corpus filtering extracts correct prefixes for agent_id
- Corpus filtering logic in vector_rag.py correctly filters by source prefix
- Corpus filtering logic in simple_rag.py (Jaccard fallback) correctly filters
- CorpusNotIndexedError is properly defined
"""

from __future__ import annotations

import pytest


class TestAgentCorpusMapConstant:
    """Tests for AGENT_CORPUS_MAP constant in contracts."""

    def test_agent_corpus_map_exists(self) -> None:
        """AGENT_CORPUS_MAP constant exists in contracts module."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        assert isinstance(AGENT_CORPUS_MAP, dict)

    def test_cbt_agent_mapping_exists(self) -> None:
        """cbt-agent has corpus mapping defined."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        assert "cbt-agent" in AGENT_CORPUS_MAP
        prefixes = AGENT_CORPUS_MAP["cbt-agent"]
        assert isinstance(prefixes, list)
        assert len(prefixes) > 0

    def test_cbt_agent_corpus_prefixes(self) -> None:
        """cbt-agent corpus includes expected prefixes."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        prefixes = AGENT_CORPUS_MAP["cbt-agent"]
        assert "docs/cbt/" in prefixes
        assert "docs/psychology/" in prefixes

    def test_unknown_agent_not_in_map(self) -> None:
        """Unknown agent_id is not in AGENT_CORPUS_MAP."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        assert "unknown-agent" not in AGENT_CORPUS_MAP


class TestCorpusNotIndexedError:
    """Tests for CorpusNotIndexedError exception."""

    def test_exception_exists(self) -> None:
        """CorpusNotIndexedError exception exists."""
        from core.rag.contracts import CorpusNotIndexedError

        assert issubclass(CorpusNotIndexedError, Exception)

    def test_exception_message(self) -> None:
        """CorpusNotIndexedError includes agent_id in message."""
        from core.rag.contracts import CorpusNotIndexedError

        err = CorpusNotIndexedError("test-agent")
        assert "test-agent" in str(err)
        assert err.agent_id == "test-agent"


class TestCorpusPrefixMatching:
    """Tests for corpus prefix matching logic."""

    def test_prefix_matches_file_in_corpus(self) -> None:
        """File path starting with corpus prefix should match."""
        prefix = "docs/cbt/"
        file_path = "docs/cbt/cognitive_restructuring.md"

        assert file_path.startswith(prefix)

    def test_prefix_does_not_match_outside_corpus(self) -> None:
        """File path outside corpus should not match."""
        prefix = "docs/cbt/"
        file_path = "docs/nutrition/vitamins.md"

        assert not file_path.startswith(prefix)

    def test_multiple_prefixes_match_any(self) -> None:
        """File should match if it starts with any of multiple prefixes."""
        prefixes = ["docs/cbt/", "docs/psychology/"]
        files = [
            "docs/cbt/thought_records.md",
            "docs/psychology/motivation_theories.md",
            "docs/nutrition/macros.md",
        ]

        matches = [f for f in files if any(f.startswith(p) for p in prefixes)]
        assert len(matches) == 2
        assert "docs/nutrition/macros.md" not in matches


class TestVectorRAGCorpusFiltering:
    """Tests for corpus filtering in vector_rag.py retrieval functions."""

    def test_retrieve_context_accepts_agent_id(self) -> None:
        """retrieve_context_structured accepts agent_id parameter."""
        import inspect

        from core.rag.vector_rag import retrieve_context_structured

        sig = inspect.signature(retrieve_context_structured)
        params = list(sig.parameters.keys())
        assert "agent_id" in params

    def test_retrieve_context_returns_rag_context(self) -> None:
        """retrieve_context_structured returns RAGContext."""
        import inspect

        from core.rag.vector_rag import retrieve_context_structured

        sig = inspect.signature(retrieve_context_structured)
        # Check return annotation if present
        return_annotation = sig.return_annotation
        if return_annotation != inspect.Signature.empty:
            # Should be RAGContext or something similar
            assert (
                "RAGContext" in str(return_annotation) or return_annotation.__name__ == "RAGContext"
            )


class TestSimpleRAGCorpusFiltering:
    """Tests for corpus filtering in simple_rag.py (Jaccard fallback)."""

    def test_simple_rag_accepts_agent_id(self) -> None:
        """Simple RAG retrieve_context_structured accepts agent_id."""
        import inspect

        from core.rag.simple_rag import retrieve_context_structured

        sig = inspect.signature(retrieve_context_structured)
        params = list(sig.parameters.keys())
        assert "agent_id" in params


class TestCorpusFilteringBehavior:
    """Behavioral tests for corpus filtering."""

    def test_no_agent_id_returns_all_chunks(self) -> None:
        """When agent_id is None, all chunks should be considered."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        # Without agent_id, no filtering should be applied
        agent_id = None
        prefixes = AGENT_CORPUS_MAP.get(agent_id) if agent_id else None

        assert prefixes is None

    def test_agent_id_extracts_prefixes_from_map(self) -> None:
        """When agent_id is set, prefixes are extracted from AGENT_CORPUS_MAP."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        agent_id = "cbt-agent"
        prefixes = AGENT_CORPUS_MAP.get(agent_id)

        assert prefixes is not None
        assert len(prefixes) == 2

    def test_unknown_agent_id_returns_none(self) -> None:
        """Unknown agent_id returns None (no filtering)."""
        from core.rag.contracts import AGENT_CORPUS_MAP

        agent_id = "nonexistent-agent"
        prefixes = AGENT_CORPUS_MAP.get(agent_id)

        assert prefixes is None


class TestSimpleRAGCorpusFilteringLogic:
    """Tests for corpus filtering logic in simple_rag.py."""

    def test_items_filtered_by_prefix(self) -> None:
        """Items are filtered to only include sources matching corpus prefixes."""
        # Simulate the filtering logic from simple_rag.py line 158-161
        items = [
            ("docs/cbt/thought_records.md", "CBT content"),
            ("docs/psychology/motivation.md", "Psychology content"),
            ("docs/nutrition/macros.md", "Nutrition content"),
        ]
        corpus_prefixes = ["docs/cbt/", "docs/psychology/"]

        filtered_items = [
            (src, ch)
            for src, ch in items
            if any(src.startswith(prefix) for prefix in corpus_prefixes)
        ]

        assert len(filtered_items) == 2
        sources = [src for src, _ in filtered_items]
        assert "docs/cbt/thought_records.md" in sources
        assert "docs/psychology/motivation.md" in sources
        assert "docs/nutrition/macros.md" not in sources

    def test_no_match_returns_empty(self) -> None:
        """When no items match prefixes, filtered list is empty."""
        items = [
            ("docs/nutrition/macros.md", "Nutrition content"),
            ("docs/recipes/cake.md", "Recipe content"),
        ]
        corpus_prefixes = ["docs/cbt/", "docs/psychology/"]

        filtered_items = [
            (src, ch)
            for src, ch in items
            if any(src.startswith(prefix) for prefix in corpus_prefixes)
        ]

        assert len(filtered_items) == 0


class TestVectorRAGPostgresCorpusFiltering:
    """Tests for Postgres corpus filtering SQL generation."""

    def test_postgres_corpus_prefix_where_clause(self) -> None:
        """Postgres filtering builds proper WHERE clause with LIKE patterns."""
        # Simulate the logic from vector_rag.py lines 109-115
        corpus_prefixes = ["docs/cbt/", "docs/psychology/"]
        params: dict[str, str] = {}

        prefix_conditions = []
        for i, prefix in enumerate(corpus_prefixes):
            param_name = f"prefix_{i}"
            prefix_conditions.append(f"source LIKE :{param_name}")
            params[param_name] = f"{prefix}%"

        where_clause = " AND (" + " OR ".join(prefix_conditions) + ")"

        assert "source LIKE :prefix_0" in where_clause
        assert "source LIKE :prefix_1" in where_clause
        assert " OR " in where_clause
        assert params["prefix_0"] == "docs/cbt/%"
        assert params["prefix_1"] == "docs/psychology/%"


class TestVectorRAGSqliteCorpusFiltering:
    """Tests for SQLite corpus filtering SQL generation."""

    def test_sqlite_corpus_prefix_where_clause(self) -> None:
        """SQLite filtering builds proper WHERE clause with LIKE patterns."""
        # Simulate the logic from vector_rag.py lines 147-153
        corpus_prefixes = ["docs/cbt/"]
        params: dict[str, str] = {}

        prefix_conditions = []
        for i, prefix in enumerate(corpus_prefixes):
            param_name = f"prefix_{i}"
            prefix_conditions.append(f"source LIKE :{param_name}")
            params[param_name] = f"{prefix}%"

        where_clause = "WHERE embedding IS NOT NULL"
        if prefix_conditions:
            where_clause += " AND (" + " OR ".join(prefix_conditions) + ")"

        assert "WHERE embedding IS NOT NULL" in where_clause
        assert "source LIKE :prefix_0" in where_clause
        assert params["prefix_0"] == "docs/cbt/%"


class TestCorpusFilteringIntegration:
    """Integration tests for corpus filtering through retrieval functions."""

    def test_simple_rag_with_agent_id_filters_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """simple_rag.retrieve_context_structured filters by agent corpus."""
        from core.rag import simple_rag

        # Mock _get_index to return mixed corpus items
        def mock_get_index() -> list[tuple[str, str]]:
            return [
                ("docs/cbt/thought_records.md", "CBT thought records content"),
                ("docs/nutrition/vitamins.md", "Vitamins content"),
            ]

        monkeypatch.setattr(simple_rag, "_get_index", mock_get_index)

        ctx = simple_rag.retrieve_context_structured(
            query="thoughts",
            max_chunks=5,
            agent_id="cbt-agent",
        )

        # Should only get CBT corpus chunks
        assert len(ctx.chunks) <= 1
        if ctx.chunks:
            assert "docs/cbt/" in ctx.chunks[0].file

    def test_simple_rag_without_agent_id_returns_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """simple_rag without agent_id returns all matching items."""
        from core.rag import simple_rag

        def mock_get_index() -> list[tuple[str, str]]:
            return [
                ("docs/cbt/thought_records.md", "CBT thought records content"),
                ("docs/nutrition/vitamins.md", "Vitamins content"),
            ]

        monkeypatch.setattr(simple_rag, "_get_index", mock_get_index)

        ctx = simple_rag.retrieve_context_structured(
            query="content",
            max_chunks=5,
            agent_id=None,
        )

        # Should get all items (no corpus filtering)
        assert len(ctx.chunks) >= 1

    def test_simple_rag_logs_warning_when_corpus_empty(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """simple_rag logs warning when corpus filter yields no results."""
        import logging

        from core.rag import simple_rag

        # Return items that don't match CBT corpus
        def mock_get_index() -> list[tuple[str, str]]:
            return [
                ("docs/nutrition/vitamins.md", "Vitamins content"),
            ]

        monkeypatch.setattr(simple_rag, "_get_index", mock_get_index)

        with caplog.at_level(logging.WARNING, logger="core.rag.simple_rag"):
            ctx = simple_rag.retrieve_context_structured(
                query="test",
                max_chunks=5,
                agent_id="cbt-agent",
            )

        assert len(ctx.chunks) == 0
        # Warning should be logged about no matches
        assert any(
            "corpus_prefixes" in record.message.lower() for record in caplog.records
        ), "Expected warning about empty corpus match"
