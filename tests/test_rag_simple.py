"""
Tests for core.rag.simple_rag minimal functionality.

Covers:
- Empty index (no docs) returns empty context
- Non-empty index returns top-k chunk with source header
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
    assert list(tmp_path.glob("*.md")) == []
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

