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
    wcs.validate_wiki_slug(slug)


def test_path_to_slug_long_path_is_stable() -> None:
    parts = [f"seg{i}" for i in range(40)]
    rel = Path(*parts) / "tail.md"
    assert wcs.path_to_slug(rel) == wcs.path_to_slug(rel)


def test_path_to_slug_long_paths_disambiguate() -> None:
    """Paths sharing the same naive 114-char prefix must not share slug after hashing."""

    inner = tuple(f"x{i}" for i in range(45))
    rel_a = Path(*inner) / "marker_a.md"
    rel_b = Path(*inner) / "marker_b.md"
    slug_a = wcs.path_to_slug(rel_a)
    slug_b = wcs.path_to_slug(rel_b)
    assert slug_a != slug_b
    wcs.validate_wiki_slug(slug_a)
    wcs.validate_wiki_slug(slug_b)


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
