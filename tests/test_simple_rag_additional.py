from __future__ import annotations

import types
from pathlib import Path

import pytest

import core.rag.simple_rag as simple_rag


def test_build_index_skips_read_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, identifier: str):
            self._id = identifier

        def stat(self):
            return types.SimpleNamespace(st_size=1)

        def read_text(self, encoding="utf-8", errors="ignore"):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad data")

        def __str__(self):
            return self._id

    monkeypatch.setattr(simple_rag, "_iter_docs", lambda: [FakePath("bad")])
    simple_rag.invalidate_index()
    assert simple_rag._build_index() == []


def test_build_index_skips_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, identifier: str):
            self._id = identifier

        def stat(self):
            return types.SimpleNamespace(st_size=1)

        def read_text(self, encoding="utf-8", errors="ignore"):
            raise RuntimeError("boom")

        def __str__(self):
            return self._id

    monkeypatch.setattr(simple_rag, "_iter_docs", lambda: [FakePath("bad")])
    simple_rag.invalidate_index()
    assert simple_rag._build_index() == []


def test_retrieve_context_empty_index(monkeypatch: pytest.MonkeyPatch) -> None:
    simple_rag.invalidate_index()
    monkeypatch.setattr(simple_rag, "_build_index", lambda: [])
    assert simple_rag.retrieve_context("query") == ""
