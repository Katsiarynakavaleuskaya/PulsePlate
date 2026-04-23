"""Ingest repo paths into the advisory local wiki corpus (filesystem + optional LSP).

RU: Копирует сырьё в ``artifacts/orchestration/wiki`` и опционально пишет метаданные
в local support plane (только при allowlist + execution mode).
EN: Non-canonical; never writes ``docs/**`` or OpenAPI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

from app.security import agent_control_plane as cp

from scripts.orchestration import local_support_plane as lsp
from scripts.orchestration import _wiki_compiler_support as wcs

EXIT_OK: Final[int] = 0
EXIT_USAGE: Final[int] = 2


def _append_log(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line.rstrip() + "\n")


def _rebuild_index(pages_dir: Path, index_path: Path, corpus: str) -> None:
    rows: list[str] = [f"# Wiki index ({corpus})", ""]
    if pages_dir.is_dir():
        for p in sorted(pages_dir.glob("*.md")):
            rows.append(f"- [{p.stem}](pages/{p.name})")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def ingest_paths(
    source_paths: list[Path],
    *,
    corpus: str,
    wiki_root: Path,
    repo_root: Path,
    write_support_plane: bool,
    allowlist: set[tuple[str, str]] | None = None,
    sp_root_override: Path | None = None,
    audit_secret: str | None = None,
    audit_log_path: Path | str | None = None,
) -> tuple[list[str], list[str]]:
    """Copy sources into wiki corpus; optionally mirror metadata to support plane.

    Returns ``(written_slugs, warnings)``.
    """

    warnings: list[str] = []
    written: list[str] = []
    wiki_resolved = wiki_root.resolve()
    layout = wcs.corpus_layout(wcs.corpus_base(wiki_root, corpus))
    wcs.reject_if_under_canonical_docs(layout["base"], repo_root=repo_root)
    layout["pages"].mkdir(parents=True, exist_ok=True)
    layout["raw"].mkdir(parents=True, exist_ok=True)
    slug_first_source: dict[str, str] = {}

    active_allowlist = allowlist
    if write_support_plane and active_allowlist is None:
        active_allowlist = cp.load_allowlist_from_env()

    for src in source_paths:
        abs_src = src.resolve()
        try:
            rel = abs_src.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise ValueError(f"source_outside_repo:{abs_src}") from exc
        if not abs_src.is_file():
            raise FileNotFoundError(str(abs_src))
        data = abs_src.read_bytes()
        digest = wcs.sha256_hex(data)
        slug = wcs.path_to_slug(rel)
        try:
            wcs.validate_wiki_slug(slug)
        except ValueError as exc:
            raise ValueError(f"slug_from_path_invalid:{rel.as_posix()}:{slug}") from exc
        rel_posix = rel.as_posix()
        prior = slug_first_source.get(slug)
        if prior is not None and prior != rel_posix:
            raise ValueError(f"slug_collision:{slug}:{prior}")
        slug_first_source[slug] = rel_posix
        raw_name = f"{digest}.md"
        raw_path = layout["raw"] / raw_name
        raw_path.write_bytes(data)

        ingested_at = wcs.utc_now_iso()
        meta = {
            "corpus": corpus,
            "source_rel_path": rel.as_posix(),
            "content_hash": digest,
            "ingested_at": ingested_at,
            "advisory": "true",
        }
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
            warnings.append(f"utf8_replace:{rel.as_posix()}")
        page_path = layout["pages"] / f"{slug}.md"
        if page_path.is_file():
            existing_meta, _ = wcs.parse_frontmatter(page_path.read_text(encoding="utf-8"))
            prior_src = existing_meta.get("source_rel_path")
            if prior_src is None or str(prior_src).strip() == "":
                raise ValueError(f"slug_collision_existing:{slug}:missing_source_rel_path")
            if str(prior_src) != rel_posix:
                raise ValueError(f"slug_collision_existing:{slug}:{prior_src}:{rel_posix}")
        page_body = wcs.format_frontmatter(meta) + text
        page_path.write_text(page_body, encoding="utf-8")
        written.append(slug)

        _append_log(
            layout["log"],
            f"{ingested_at} ingest corpus={corpus} slug={slug} hash={digest} path={rel.as_posix()}",
        )

        if write_support_plane:
            try:
                raw_sp = wcs.path_for_support_plane_record(
                    raw_path, repo_root=repo_root, wiki_root=wiki_resolved
                )
                page_sp = wcs.path_for_support_plane_record(
                    page_path, repo_root=repo_root, wiki_root=wiki_resolved
                )
                src_record: dict[str, Any] = {
                    "corpus": corpus,
                    "source_rel_path": rel.as_posix(),
                    "content_hash": digest,
                    "raw_path": raw_sp,
                    "ingested_at": ingested_at,
                }
                lsp.put_record(
                    f"wiki.source.{digest}",
                    src_record,
                    allowlist=active_allowlist or set(),
                    repo_root=repo_root,
                    root_override=sp_root_override,
                    audit_secret=audit_secret,
                    audit_log_path=audit_log_path,
                )
                page_record: dict[str, Any] = {
                    "corpus": corpus,
                    "slug": slug,
                    "source_rel_path": rel.as_posix(),
                    "content_hash": digest,
                    "page_path": page_sp,
                    "ingested_at": ingested_at,
                }
                lsp.put_record(
                    f"wiki.page.{slug}",
                    page_record,
                    allowlist=active_allowlist or set(),
                    repo_root=repo_root,
                    root_override=sp_root_override,
                    audit_secret=audit_secret,
                    audit_log_path=audit_log_path,
                )
            except (PermissionError, ValueError, OSError) as exc:
                warnings.append(f"support_plane_skip:{slug}:{exc}")

    _rebuild_index(layout["pages"], layout["index"], corpus)
    return written, warnings


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--source",
        dest="sources",
        action="append",
        default=[],
        required=True,
        help="File path to ingest (repeatable), relative to repo root or absolute",
    )
    p.add_argument("--corpus", default="project_internal", help="Corpus name under wiki root")
    p.add_argument(
        "--wiki-root",
        type=Path,
        default=wcs.DEFAULT_WIKI_ROOT,
        help="Wiki root (default: artifacts/orchestration/wiki)",
    )
    p.add_argument("--repo-root", type=Path, default=None, help="Repository root (auto-detected)")
    p.add_argument(
        "--write-support-plane",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write wiki.* records to local support plane when policy allows",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = wcs.resolve_repo_root(args.repo_root)
    wiki_root = args.wiki_root
    if not wiki_root.is_absolute():
        wiki_root = (repo_root / wiki_root).resolve()
    sources = [
        (repo_root / Path(s)).resolve() if not Path(s).is_absolute() else Path(s).resolve()
        for s in args.sources
    ]
    try:
        _, warnings = ingest_paths(
            sources,
            corpus=args.corpus,
            wiki_root=wiki_root,
            repo_root=repo_root,
            write_support_plane=args.write_support_plane,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    for w in warnings:
        print(json.dumps({"warning": w}, sort_keys=True), file=sys.stderr)
    print(
        json.dumps(
            {
                "corpus": args.corpus,
                "ok": True,
                "repo_root": repo_root.as_posix(),
                "wiki_root": wiki_root.as_posix(),
            },
            sort_keys=True,
        )
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
