"""Query advisory local wiki pages (list, search, detail).

RU: Только чтение файловой вики; без embeddings и без сети.
EN: Read-only; does not mutate support plane or canonical docs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

from scripts.orchestration import _wiki_compiler_support as wcs

EXIT_OK: Final[int] = 0
EXIT_NOT_FOUND: Final[int] = 1
EXIT_USAGE: Final[int] = 2


def list_pages(pages_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not pages_dir.is_dir():
        return out
    for p in sorted(pages_dir.glob("*.md")):
        meta, _ = wcs.parse_frontmatter(p.read_text(encoding="utf-8"))
        out.append({"slug": p.stem, "meta": meta, "path": p.as_posix()})
    return out


def _nearest_heading(lines: list[str], index: int) -> str | None:
    for previous in range(index, -1, -1):
        line = lines[previous].strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
    return None


def search_pages(
    pages_dir: Path,
    needle: str,
    *,
    include_context: bool = False,
) -> list[dict[str, Any]]:
    n = needle.casefold()
    hits: list[dict[str, Any]] = []
    if not pages_dir.is_dir():
        return hits
    for p in sorted(pages_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        _, body = wcs.parse_frontmatter(text)
        body_lines = body.splitlines()
        line_indexes = [i for i, line in enumerate(body_lines) if n in line.casefold()]
        if line_indexes:
            hit: dict[str, Any] = {
                "lines": [i + 1 for i in line_indexes],
                "slug": p.stem,
            }
            if include_context:
                first = line_indexes[0]
                hit.update(
                    {
                        "excerpt": body_lines[first].strip(),
                        "heading": _nearest_heading(body_lines, first),
                        "match_count": len(line_indexes),
                    }
                )
            hits.append(hit)
    return hits


def detail_page(pages_dir: Path, slug: str) -> dict[str, Any] | None:
    wcs.validate_wiki_slug(slug)
    path = pages_dir / f"{slug}.md"
    if not path.is_file():
        return None
    meta, body = wcs.parse_frontmatter(path.read_text(encoding="utf-8"))
    return {"body": body, "meta": meta, "slug": slug}


def run_query(
    *,
    mode: str,
    corpus: str,
    wiki_root: Path,
    repo_root: Path,
    needle: str | None = None,
    slug: str | None = None,
    include_context: bool = False,
) -> dict[str, Any]:
    base = wcs.corpus_base(wiki_root, corpus)
    layout = wcs.corpus_layout(base)
    if mode == "list":
        return {"pages": list_pages(layout["pages"])}
    if mode == "search":
        if not needle:
            raise ValueError("search_requires_needle")
        return {"hits": search_pages(layout["pages"], needle, include_context=include_context)}
    if mode == "detail":
        if not slug:
            raise ValueError("detail_requires_slug")
        d = detail_page(layout["pages"], slug)
        if d is None:
            raise FileNotFoundError(slug)
        return {"page": d}
    raise ValueError(f"unknown_mode:{mode}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--mode",
        choices=("list", "search", "detail"),
        required=True,
    )
    p.add_argument("--corpus", default="project_internal")
    p.add_argument("--wiki-root", type=Path, default=wcs.DEFAULT_WIKI_ROOT)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--needle", default=None, help="Substring for search mode")
    p.add_argument("--slug", default=None, help="Page slug for detail mode")
    p.add_argument(
        "--include-context",
        action="store_true",
        help="Include deterministic heading/excerpt metadata for search hits",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = wcs.resolve_repo_root(args.repo_root)
    wiki_root = args.wiki_root
    if not wiki_root.is_absolute():
        wiki_root = (repo_root / wiki_root).resolve()
    try:
        payload = run_query(
            mode=args.mode,
            corpus=args.corpus,
            wiki_root=wiki_root,
            repo_root=repo_root,
            needle=args.needle,
            slug=args.slug,
            include_context=args.include_context,
        )
    except FileNotFoundError as exc:
        print(json.dumps({"error": "not_found", "slug": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_NOT_FOUND
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    print(json.dumps({"corpus": args.corpus, "ok": True, **payload}, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
