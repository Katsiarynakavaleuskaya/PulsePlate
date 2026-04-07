"""Tests for advisory wiki query CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration import wiki_ingest
from scripts.orchestration import wiki_query


def _seed_wiki(repo: Path) -> None:
    (repo / "src").mkdir(parents=True)
    p = repo / "src" / "doc.md"
    p.write_text("alpha beta gamma\n", encoding="utf-8")
    wiki_ingest.ingest_paths(
        [p],
        corpus="project_internal",
        wiki_root=repo / "wiki",
        repo_root=repo,
        write_support_plane=False,
    )


def test_query_list_and_detail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    _seed_wiki(repo)
    assert (
        wiki_query.main(
            [
                "--mode",
                "list",
                "--repo-root",
                str(repo),
                "--wiki-root",
                str(repo / "wiki"),
            ]
        )
        == 0
    )
    raw = json.loads(capsys.readouterr().out.strip())
    assert raw["ok"] is True
    assert len(raw["pages"]) == 1
    slug = raw["pages"][0]["slug"]
    assert (
        wiki_query.main(
            [
                "--mode",
                "detail",
                "--slug",
                slug,
                "--repo-root",
                str(repo),
                "--wiki-root",
                str(repo / "wiki"),
            ]
        )
        == 0
    )
    detail = json.loads(capsys.readouterr().out.strip())
    assert "beta" in detail["page"]["body"]


def test_query_search_hits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    _seed_wiki(repo)
    assert (
        wiki_query.main(
            [
                "--mode",
                "search",
                "--needle",
                "beta",
                "--repo-root",
                str(repo),
                "--wiki-root",
                str(repo / "wiki"),
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out.strip())
    assert data["hits"]


def test_query_detail_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "wiki" / "project_internal" / "pages").mkdir(parents=True)
    assert (
        wiki_query.main(
            [
                "--mode",
                "detail",
                "--slug",
                "nope",
                "--repo-root",
                str(repo),
                "--wiki-root",
                str(repo / "wiki"),
            ]
        )
        == 1
    )
