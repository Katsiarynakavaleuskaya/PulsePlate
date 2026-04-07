"""Tests for advisory wiki promote (filesystem + support plane)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from app.security import agent_control_plane as cp
from scripts.orchestration import _wiki_compiler_support as wcs
from scripts.orchestration import local_support_plane as lsp
from scripts.orchestration import wiki_ingest
from scripts.orchestration import wiki_promote


@pytest.fixture
def allowlist() -> set[tuple[str, str]]:
    return {lsp.default_allowlist_pair()}


@pytest.fixture
def audit_signing_material(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(cp.EXECUTION_MODE_ENV, cp.EXECUTION_MODE_AUTO_SAFE)
    material = "unit-test-hmac-key-wiki-promote-2026"  # pragma: allowlist secret
    monkeypatch.setenv(cp.AUDIT_SIGNING_KEY_ENV, material)
    return material


def _ingest_one(repo: Path, wiki: Path) -> str:
    (repo / "s").mkdir(parents=True)
    f = repo / "s" / "a.md"
    f.write_text("body", encoding="utf-8")
    slugs, _ = wiki_ingest.ingest_paths(
        [f],
        corpus="project_internal",
        wiki_root=wiki,
        repo_root=repo,
        write_support_plane=False,
    )
    assert len(slugs) == 1
    return slugs[0]


def test_promote_writes_promoted_and_metadata(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    out = wiki_promote.promote_slug(
        slug,
        corpus="project_internal",
        wiki_root=wiki,
        repo_root=repo,
        write_support_plane=False,
    )
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "promoted: true" in text
    assert "promoted_at:" in text


def test_promote_support_plane_external_wiki_root(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    """Promoted path in SP JSON must not use repo relative_to when wiki lives outside repo."""

    repo = tmp_path / "r"
    (repo / "s").mkdir(parents=True)
    f = repo / "s" / "a.md"
    f.write_text("body", encoding="utf-8")
    wiki_root = tmp_path / "ext_wiki"
    sp = tmp_path / "sp"
    audit_log = tmp_path / "audit.jsonl"
    wiki_ingest.ingest_paths(
        [f],
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    wiki_promote.promote_slug(
        "s.a",
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=True,
        allowlist=allowlist,
        sp_root_override=sp,
        audit_secret=audit_signing_material,
        audit_log_path=audit_log,
    )
    rec = lsp.get_record("wiki.promoted.s.a", root_override=sp)
    assert rec is not None
    promoted_path = str(rec["promoted_path"])
    assert promoted_path.startswith("wiki:")
    assert "/promoted/" in promoted_path


def test_promote_support_plane_record(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    sp = tmp_path / "sp"
    audit_log = tmp_path / "audit.jsonl"
    wiki_promote.promote_slug(
        slug,
        corpus="project_internal",
        wiki_root=wiki,
        repo_root=repo,
        write_support_plane=True,
        allowlist=allowlist,
        sp_root_override=sp,
        audit_secret=audit_signing_material,
        audit_log_path=audit_log,
    )
    rec = lsp.get_record(f"wiki.promoted.{slug}", root_override=sp)
    assert rec is not None
    assert rec["slug"] == slug


def test_promote_forbidden_under_canonical_docs(tmp_path: Path) -> None:
    """Promote fail-closed under ``docs/**`` even when corpus was created without ingest."""

    repo = tmp_path / "r"
    wiki = repo / "docs" / "evil_wiki"
    digest = hashlib.sha256(b"body").hexdigest()
    layout = wcs.corpus_layout(wcs.corpus_base(wiki, "project_internal"))
    layout["raw"].mkdir(parents=True, exist_ok=True)
    layout["pages"].mkdir(parents=True, exist_ok=True)
    (layout["raw"] / f"{digest}.md").write_bytes(b"body")
    slug = "hello"
    meta = {
        "advisory": "true",
        "corpus": "project_internal",
        "content_hash": digest,
        "ingested_at": "2026-01-01T00:00:00Z",
    }
    page_body = wcs.format_frontmatter({str(k): str(v) for k, v in meta.items()}) + "body\n"
    (layout["pages"] / f"{slug}.md").write_text(page_body, encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden_under_canonical_docs"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=False,
        )


def test_promote_rejects_bad_slug() -> None:
    with pytest.raises(ValueError, match="slug_invalid"):
        wiki_promote.validate_slug("../x")


@pytest.mark.skipif(
    not hasattr(os, "symlink"),
    reason="symlink required to simulate promoted/ escaping corpus",
)
def test_promote_rejects_symlink_promoted_dir_outside_corpus(tmp_path: Path) -> None:
    """Resolved destination must stay under corpus before mkdir (symlink escape)."""

    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    layout = wcs.corpus_layout(wcs.corpus_base(wiki, "project_internal"))
    promoted = layout["promoted"]
    if promoted.exists():
        if promoted.is_dir():
            shutil.rmtree(promoted)
        else:
            promoted.unlink()
    outside = tmp_path / "outside_promoted"
    outside.mkdir(parents=True)
    os.symlink(outside, promoted, target_is_directory=True)
    with pytest.raises(ValueError, match="promote_path_outside_corpus"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=False,
        )


def test_promote_preserves_existing_promoted_file_on_put_record_failure(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second promote with SP failure must restore prior promoted content (non-destructive)."""

    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    dst = wiki / "project_internal" / "promoted" / f"{slug}.md"
    wiki_promote.promote_slug(
        slug,
        corpus="project_internal",
        wiki_root=wiki,
        repo_root=repo,
        write_support_plane=False,
    )
    prior = dst.read_text(encoding="utf-8")
    assert "promoted_at:" in prior

    def boom(*_a: object, **_kw: object) -> None:
        raise ValueError("support_plane_value_too_large")

    monkeypatch.setattr(lsp, "put_record", boom)
    with pytest.raises(ValueError, match="support_plane_value_too_large"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=True,
            allowlist=allowlist,
            sp_root_override=tmp_path / "sp",
            audit_secret=audit_signing_material,
        )
    assert dst.read_text(encoding="utf-8") == prior


def test_promote_keeps_new_dst_when_backup_missing_on_rollback(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If .bak appears missing during rollback, do not unlink dst (avoid total loss)."""

    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    dst = wiki / "project_internal" / "promoted" / f"{slug}.md"
    _promo_times = iter(["2026-01-10T10:00:00Z", "2026-01-11T11:00:00Z"])
    monkeypatch.setattr(wcs, "utc_now_iso", lambda: next(_promo_times))
    wiki_promote.promote_slug(
        slug,
        corpus="project_internal",
        wiki_root=wiki,
        repo_root=repo,
        write_support_plane=False,
        allowlist=allowlist,
        sp_root_override=tmp_path / "sp",
        audit_secret=audit_signing_material,
    )
    prior = dst.read_text(encoding="utf-8")

    orig_is_file = Path.is_file

    def is_file_patched(self: Path) -> bool:
        if str(self).endswith(".promote.bak"):
            return False
        return orig_is_file(self)

    monkeypatch.setattr(Path, "is_file", is_file_patched)

    def boom(*_a: object, **_kw: object) -> None:
        raise ValueError("support_plane_missing_backup_sim")

    monkeypatch.setattr(lsp, "put_record", boom)
    with pytest.raises(ValueError, match="support_plane_missing_backup_sim"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=True,
            allowlist=allowlist,
            sp_root_override=tmp_path / "sp",
            audit_secret=audit_signing_material,
        )
    assert dst.is_file()
    assert dst.read_text(encoding="utf-8") != prior


def test_promote_preserves_prior_on_unexpected_put_record_failure(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    dst = wiki / "project_internal" / "promoted" / f"{slug}.md"
    wiki_promote.promote_slug(
        slug,
        corpus="project_internal",
        wiki_root=wiki,
        repo_root=repo,
        write_support_plane=False,
    )
    prior = dst.read_text(encoding="utf-8")

    def boom(*_a: object, **_kw: object) -> None:
        raise TypeError("unexpected_support_plane")

    monkeypatch.setattr(lsp, "put_record", boom)
    with pytest.raises(TypeError, match="unexpected_support_plane"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=True,
            allowlist=allowlist,
            sp_root_override=tmp_path / "sp",
            audit_secret=audit_signing_material,
        )
    assert dst.read_text(encoding="utf-8") == prior


def test_promote_does_not_write_file_when_put_record_fails(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    dst = wiki / "project_internal" / "promoted" / f"{slug}.md"

    def boom(*_a: object, **_kw: object) -> None:
        raise ValueError("support_plane_value_too_large")

    monkeypatch.setattr(lsp, "put_record", boom)
    with pytest.raises(ValueError, match="support_plane_value_too_large"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=True,
            allowlist=allowlist,
            sp_root_override=tmp_path / "sp",
            audit_secret=audit_signing_material,
        )
    assert not dst.is_file()


def test_promote_unlinks_on_unexpected_put_record_failure(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rollback promoted file on any support-plane failure, not only a fixed tuple."""

    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    dst = wiki / "project_internal" / "promoted" / f"{slug}.md"

    def boom(*_a: object, **_kw: object) -> None:
        raise TypeError("unexpected_support_plane")

    monkeypatch.setattr(lsp, "put_record", boom)
    with pytest.raises(TypeError, match="unexpected_support_plane"):
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=True,
            allowlist=allowlist,
            sp_root_override=tmp_path / "sp",
            audit_secret=audit_signing_material,
        )
    assert not dst.is_file()


def test_promote_rollback_unlink_failure_chains_from_support_plane_error(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Ошибка unlink при откате не глотается — видна вместе с причиной из SP.
    EN: Rollback unlink errors propagate; support-plane failure remains __cause__ chain.
    """

    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    dst = wiki / "project_internal" / "promoted" / f"{slug}.md"
    real_unlink = Path.unlink

    def boom(*_a: object, **_kw: object) -> None:
        raise RuntimeError("support_plane_failed")

    def unlink_patched(self: Path, *a: object, **kw: object) -> None:
        if self == dst:
            raise PermissionError("rollback_unlink_denied")
        return real_unlink(self, *a, **kw)

    monkeypatch.setattr(lsp, "put_record", boom)
    monkeypatch.setattr(Path, "unlink", unlink_patched)
    with pytest.raises(PermissionError, match="rollback_unlink_denied") as record:
        wiki_promote.promote_slug(
            slug,
            corpus="project_internal",
            wiki_root=wiki,
            repo_root=repo,
            write_support_plane=True,
            allowlist=allowlist,
            sp_root_override=tmp_path / "sp",
            audit_secret=audit_signing_material,
        )
    assert record.value.__cause__ is not None
    assert isinstance(record.value.__cause__, RuntimeError)
    assert dst.is_file()


def test_main_out_when_wiki_outside_repo(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "r"
    (repo / "s").mkdir(parents=True)
    f = repo / "s" / "a.md"
    f.write_text("body", encoding="utf-8")
    wiki_root = tmp_path / "ext_wiki"
    wiki_ingest.ingest_paths(
        [f],
        corpus="project_internal",
        wiki_root=wiki_root,
        repo_root=repo,
        write_support_plane=False,
    )
    assert (
        wiki_promote.main(
            [
                "--slug",
                "s.a",
                "--repo-root",
                str(repo),
                "--wiki-root",
                str(wiki_root),
                "--no-write-support-plane",
            ]
        )
        == 0
    )
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
    assert out["out"].startswith("wiki:")


def test_main_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "r"
    wiki = repo / "wiki"
    slug = _ingest_one(repo, wiki)
    assert (
        wiki_promote.main(
            [
                "--slug",
                slug,
                "--repo-root",
                str(repo),
                "--wiki-root",
                str(wiki),
                "--no-write-support-plane",
            ]
        )
        == 0
    )
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
