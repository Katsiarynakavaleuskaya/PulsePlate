"""Tests for advisory wiki ingest (filesystem layout + optional support plane)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.security import agent_control_plane as cp
from scripts.orchestration import local_support_plane as lsp
from scripts.orchestration import wiki_ingest


@pytest.fixture
def allowlist() -> set[tuple[str, str]]:
    return {lsp.default_allowlist_pair()}


@pytest.fixture
def audit_signing_material(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(cp.EXECUTION_MODE_ENV, cp.EXECUTION_MODE_AUTO_SAFE)
    material = "unit-test-hmac-key-wiki-ingest-2026"  # pragma: allowlist secret
    monkeypatch.setenv(cp.AUDIT_SIGNING_KEY_ENV, material)
    return material


def test_ingest_writes_raw_page_index_log(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    src = repo / "docs" / "note.md"
    src.write_text("# Hello\nbody\n", encoding="utf-8")
    wiki_root = repo / "wiki"
    slugs, warnings = wiki_ingest.ingest_paths(
        [src],
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    assert slugs == ["docs.note"]
    assert warnings == []
    base = wiki_root / "project_internal"
    raw_dir = base / "raw"
    pages = base / "pages"
    assert raw_dir.is_dir()
    raw_files = list(raw_dir.glob("*.md"))
    assert len(raw_files) == 1
    page = pages / "docs.note.md"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert "content_hash:" in text
    assert "# Hello" in text
    assert (base / "index.md").is_file()
    log = (base / "log.md").read_text(encoding="utf-8")
    assert "ingest" in log


def test_ingest_rejects_wiki_root_under_canonical_docs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs" / "wiki_here").mkdir(parents=True)
    src = repo / "docs" / "wiki_here" / "n.md"
    src.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden_under_canonical_docs"):
        wiki_ingest.ingest_paths(
            [src],
            corpus="project_internal",
            wiki_root=repo / "docs" / "wiki_here",
            repo_root=repo,
            write_support_plane=False,
        )


@pytest.mark.parametrize(
    ("dirname", "match"),
    [("pages", "pages_path_outside_corpus"), ("raw", "raw_path_outside_corpus")],
)
def test_ingest_rejects_symlink_escape_dirs(tmp_path: Path, dirname: str, match: str) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    src = repo / "docs" / "note.md"
    src.write_text("hello", encoding="utf-8")
    wiki_root = repo / "wiki"
    corpus_base = wiki_root / "project_internal"
    corpus_base.mkdir(parents=True)
    escape = tmp_path / f"escape_{dirname}"
    escape.mkdir(parents=True)
    try:
        (corpus_base / dirname).symlink_to(escape, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symlink unsupported in this environment")
    with pytest.raises(ValueError, match=match):
        wiki_ingest.ingest_paths(
            [src],
            corpus="project_internal",
            wiki_root=wiki_root,
            repo_root=repo,
            write_support_plane=False,
        )


def test_ingest_rejects_path_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="source_outside_repo"):
        wiki_ingest.ingest_paths(
            [outside],
            corpus="c",
            wiki_root=repo / "w",
            repo_root=repo,
            write_support_plane=False,
        )


def test_ingest_support_plane_roundtrip(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    repo = tmp_path / "repo"
    (repo / "a").mkdir(parents=True)
    src = repo / "a" / "f.md"
    src.write_text("content", encoding="utf-8")
    sp_root = tmp_path / "sp"
    audit_log = tmp_path / "audit.jsonl"
    wiki_root = repo / "wiki"
    digest = hashlib.sha256(b"content").hexdigest()
    wiki_ingest.ingest_paths(
        [src],
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=True,
        allowlist=allowlist,
        sp_root_override=sp_root,
        audit_secret=audit_signing_material,
        audit_log_path=audit_log,
    )
    rec = lsp.get_record(f"wiki.source.{digest}", root_override=sp_root)
    assert rec is not None
    assert rec["content_hash"] == digest
    page_rec = lsp.get_record("wiki.page.a.f", root_override=sp_root)
    assert page_rec is not None
    assert page_rec["slug"] == "a.f"


def test_ingest_slug_collision_raises(tmp_path: Path) -> None:
    """Two sources must not map to the same slug (sanitized path segments)."""

    repo = tmp_path / "repo"
    pdir = repo / "p"
    pdir.mkdir(parents=True)
    (pdir / "q").write_text("plain", encoding="utf-8")
    (pdir / "q.md").write_text("markdown", encoding="utf-8")
    wiki_root = repo / "w"
    with pytest.raises(ValueError, match="slug_collision"):
        wiki_ingest.ingest_paths(
            [pdir / "q", pdir / "q.md"],
            corpus="c",
            wiki_root=wiki_root,
            repo_root=repo,
            write_support_plane=False,
        )


def test_ingest_slug_collision_existing_across_runs(tmp_path: Path) -> None:
    """Same slug from different sources on separate ingest calls must not overwrite silently."""

    repo = tmp_path / "repo"
    pdir = repo / "p"
    pdir.mkdir(parents=True)
    (pdir / "q").write_text("first", encoding="utf-8")
    (pdir / "q.md").write_text("second", encoding="utf-8")
    wiki_root = repo / "w"
    wiki_ingest.ingest_paths(
        [pdir / "q"],
        corpus="c",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    with pytest.raises(ValueError, match="slug_collision_existing"):
        wiki_ingest.ingest_paths(
            [pdir / "q.md"],
            corpus="c",
            wiki_root=wiki_root,
            repo_root=repo,
            write_support_plane=False,
        )


def test_ingest_same_source_reingest_overwrites(tmp_path: Path) -> None:
    """Re-ingesting the same repo path updates the page (same source_rel_path)."""

    repo = tmp_path / "repo"
    (repo / "x").mkdir(parents=True)
    f = repo / "x" / "note.md"
    f.write_text("v1", encoding="utf-8")
    wiki_root = repo / "w"
    wiki_ingest.ingest_paths(
        [f],
        corpus="c",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    f.write_text("v2", encoding="utf-8")
    slugs, _ = wiki_ingest.ingest_paths(
        [f],
        corpus="c",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    assert slugs == ["x.note"]
    page = wiki_root / "c" / "pages" / "x.note.md"
    assert "v2" in page.read_text(encoding="utf-8")


def test_ingest_non_utf8_emits_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "bin").mkdir(parents=True)
    src = repo / "bin" / "x.md"
    src.write_bytes(b"\xff\xfe\x00not-utf8")
    wiki_root = repo / "w"
    _, warnings = wiki_ingest.ingest_paths(
        [src],
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    assert any(w.startswith("utf8_replace:") for w in warnings)


def test_ingest_support_plane_paths_when_wiki_outside_repo(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    f = repo / "src" / "note.md"
    f.write_text("hello", encoding="utf-8")
    wiki_root = tmp_path / "external_wiki"
    sp_root = tmp_path / "sp"
    audit_log = tmp_path / "audit.jsonl"
    digest = hashlib.sha256(b"hello").hexdigest()
    wiki_ingest.ingest_paths(
        [f],
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=True,
        allowlist=allowlist,
        sp_root_override=sp_root,
        audit_secret=audit_signing_material,
        audit_log_path=audit_log,
    )
    rec = lsp.get_record(f"wiki.source.{digest}", root_override=sp_root)
    assert rec is not None
    assert rec["raw_path"].startswith("wiki:")
    page = lsp.get_record("wiki.page.src.note", root_override=sp_root)
    assert page is not None
    assert page["page_path"].startswith("wiki:")


def test_main_json_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "r"
    (repo / "x").mkdir(parents=True)
    f = repo / "x" / "y.md"
    f.write_text("z", encoding="utf-8")
    code = wiki_ingest.main(
        [
            "--source",
            str(f.relative_to(repo)),
            "--repo-root",
            str(repo),
            "--wiki-root",
            str(repo / "w"),
            "--no-write-support-plane",
        ]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True


def test_main_stderr_json_on_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    code = wiki_ingest.main(
        [
            "--source",
            "missing.md",
            "--repo-root",
            str(repo),
            "--wiki-root",
            str(repo / "w"),
            "--no-write-support-plane",
        ]
    )
    assert code == wiki_ingest.EXIT_USAGE
    err_lines = [ln for ln in capsys.readouterr().err.strip().split("\n") if ln.strip()]
    payload = json.loads(err_lines[-1])
    assert payload["ok"] is False
    assert "error" in payload
