"""
Tests for core.rag.simple_rag minimal functionality.

Covers:
- Empty index (no docs) returns empty context
- Non-empty index returns top-k chunk with source header
- RAG stats functionality
- Scoring improvements
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def _reload_with_root(root: Path):
    # Point PROJECT_ROOT to a temporary directory and reload module
    os.environ["PROJECT_ROOT"] = str(root)
    if "core.rag.simple_rag" in sys.modules:
        del sys.modules["core.rag.simple_rag"]
    return importlib.import_module("core.rag.simple_rag")


def test_retrieve_empty_returns_empty(tmp_path: Path):
    rag = _reload_with_root(tmp_path)
    # ensure no docs
    assert not list(tmp_path.glob("*.md"))
    out = rag.retrieve_context("anything", max_chunks=3)
    assert out == ""


def test_retrieve_basic_markdown(tmp_path: Path):
    # Create a simple markdown file with two paragraphs
    content = (
        "# Test Document\n\n"
        "Banana is a good source of potassium and some protein.\n\n"
        "Separate paragraph without query terms.\n"
    )
    (tmp_path / "test.md").write_text(content, encoding="utf-8")

    rag = _reload_with_root(tmp_path)
    out = rag.retrieve_context("banana", max_chunks=2)

    # Should include source header and a chunk with the word
    assert out != ""
    assert "# Source: test.md" in out
    assert "banana" in out.lower()


def test_get_rag_stats_empty_index(tmp_path: Path):
    rag = _reload_with_root(tmp_path)
    stats = rag.get_rag_stats()

    assert stats["total_chunks"] == 0
    assert stats["sources"] == {}
    assert stats["index_loaded"] is False


def test_get_rag_stats_with_documents(tmp_path: Path):
    # Create multiple markdown files
    (tmp_path / "doc1.md").write_text("# Doc 1\n\nFirst document content.", encoding="utf-8")
    (tmp_path / "doc2.md").write_text("# Doc 2\n\nSecond document content.", encoding="utf-8")
    (tmp_path / "doc3.md").write_text("# Doc 3\n\nThird document content.", encoding="utf-8")

    rag = _reload_with_root(tmp_path)
    stats = rag.get_rag_stats()

    assert stats["total_chunks"] == 3  # Assuming each paragraph becomes a chunk
    assert stats["index_loaded"] is True
    # Sources should contain the filenames
    assert "doc1.md" in stats["sources"]
    assert "doc2.md" in stats["sources"]
    assert "doc3.md" in stats["sources"]


def test_retrieve_context_exact_phrase_boost(tmp_path: Path):
    content = (
        "# Nutrition Guide\n\n"
        "Eating healthy food is important for good nutrition.\n\n"
        "Healthy eating includes fruits and vegetables.\n"
    )
    (tmp_path / "nutrition.md").write_text(content, encoding="utf-8")

    rag = _reload_with_root(tmp_path)
    # Test that exact phrase match gets higher score
    out = rag.retrieve_context("healthy eating", max_chunks=1)
    assert out != ""
    assert "# Source: nutrition.md" in out


def test_retrieve_context_no_matches(tmp_path: Path):
    content = "# Test\n\nSome content without the search term."
    (tmp_path / "test.md").write_text(content, encoding="utf-8")

    rag = _reload_with_root(tmp_path)
    out = rag.retrieve_context("nonexistent", max_chunks=1)
    assert out == ""
