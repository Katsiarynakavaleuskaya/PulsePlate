"""
Tests for core.rag.simple_rag minimal functionality.

Covers:
- Empty index (no docs) returns empty context
- Non-empty index returns top-k chunk with source header
"""

from __future__ import annotations

import concurrent.futures
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


def test_retrieve_structured_redacts_pii(tmp_path: Path):
    content = (
        "# Support Note\n\n" "Contact me at test@example.com or 555-123-4567 about banana habits.\n"
    )
    (tmp_path / "support.md").write_text(content, encoding="utf-8")

    rag = _reload_with_root(tmp_path)
    result = rag.retrieve_context_structured("banana", max_chunks=1)

    assert result.chunks
    assert "[EMAIL_REDACTED]" in result.chunks[0].content
    assert "[PHONE_REDACTED]" in result.chunks[0].content


def test_get_index_is_thread_safe(tmp_path: Path):
    content = "# Doc\n\nBanana focus text.\n"
    (tmp_path / "thread-safe.md").write_text(content, encoding="utf-8")

    rag = _reload_with_root(tmp_path)
    rag.invalidate_index()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(lambda _: rag.retrieve_context("banana", max_chunks=1), range(8))
        )

    assert all("# Source: thread-safe.md" in result for result in results)
