"""Support-plane key shape checks for advisory wiki compiler metadata."""

from __future__ import annotations

import pytest

from scripts.orchestration import local_support_plane as lsp


def test_normalize_key_accepts_wiki_source_sha256() -> None:
    digest = "a" * 64
    key = f"wiki.source.{digest}"
    assert lsp.normalize_key(key) == key


def test_normalize_key_accepts_wiki_page_slug() -> None:
    assert lsp.normalize_key("wiki.page.docs.note") == "wiki.page.docs.note"


def test_normalize_key_accepts_wiki_promoted_slug() -> None:
    assert lsp.normalize_key("wiki.promoted.src.doc") == "wiki.promoted.src.doc"


def test_normalize_key_rejects_invalid_wiki_segments() -> None:
    with pytest.raises(ValueError, match="support_plane_key_invalid_chars"):
        lsp.normalize_key("wiki.page.bad/slug")
