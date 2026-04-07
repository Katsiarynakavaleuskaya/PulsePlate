"""Support-plane key shape checks for advisory wiki compiler metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.orchestration import _wiki_compiler_support as wcs
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


def test_path_to_slug_truncates_to_max_length() -> None:
    parts = [f"seg{i}" for i in range(40)]
    rel = Path(*parts) / "tail.md"
    slug = wcs.path_to_slug(rel)
    assert len(slug) <= wcs.MAX_WIKI_SLUG_CHARS


def test_validate_wiki_slug_rejects_oversized_slug() -> None:
    too_long = "a" * (wcs.MAX_WIKI_SLUG_CHARS + 1)
    with pytest.raises(ValueError, match="slug_invalid"):
        wcs.validate_wiki_slug(too_long)


def test_path_for_support_plane_record_prefers_repo_relative(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    wiki = repo / "wiki"
    target = wiki / "c" / "f.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    assert (
        wcs.path_for_support_plane_record(target, repo_root=repo, wiki_root=wiki) == "wiki/c/f.md"
    )


def test_path_for_support_plane_record_wiki_prefix_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    wiki = tmp_path / "external_wiki"
    target = wiki / "raw" / "a.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    out = wcs.path_for_support_plane_record(target, repo_root=repo, wiki_root=wiki)
    assert out == "wiki:raw/a.md"
