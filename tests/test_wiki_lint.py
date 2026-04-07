"""Tests for advisory wiki lint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration import wiki_ingest
from scripts.orchestration import wiki_lint


def test_lint_pages_missing(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    wiki = repo / "w"
    (wiki / "project_internal").mkdir(parents=True)
    v = wiki_lint.lint_corpus(corpus="project_internal", wiki_root=wiki, repo_root=repo)
    assert "pages_directory_missing" in v


def test_lint_rejects_invalid_content_hash_format(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    wiki = repo / "w"
    layout_base = wiki / "project_internal"
    pages = layout_base / "pages"
    raw = layout_base / "raw"
    pages.mkdir(parents=True)
    raw.mkdir(parents=True)
    bad_page = pages / "bad.md"
    bad_page.write_text(
        "---\n"
        "advisory: true\n"
        "content_hash: NOT_A_HASH\n"
        "corpus: project_internal\n"
        "ingested_at: 2026-01-01T00:00:00Z\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )
    v = wiki_lint.lint_corpus(corpus="project_internal", wiki_root=wiki, repo_root=repo)
    assert any("invalid_content_hash_format" in x for x in v)


def test_lint_clean_after_ingest(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    (repo / "s").mkdir(parents=True)
    f = repo / "s" / "a.md"
    f.write_text("ok", encoding="utf-8")
    wiki_ingest.ingest_paths(
        [f],
        corpus="project_internal",
        wiki_root=repo / "wiki",
        repo_root=repo,
        write_support_plane=False,
    )
    v = wiki_lint.lint_corpus(corpus="project_internal", wiki_root=repo / "wiki", repo_root=repo)
    assert v == []


def test_main_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "r"
    (repo / "s").mkdir(parents=True)
    f = repo / "s" / "a.md"
    f.write_text("ok", encoding="utf-8")
    wiki_ingest.ingest_paths(
        [f],
        corpus="project_internal",
        wiki_root=repo / "wiki",
        repo_root=repo,
        write_support_plane=False,
    )
    assert wiki_lint.main(["--repo-root", str(repo), "--wiki-root", str(repo / "wiki")]) == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
