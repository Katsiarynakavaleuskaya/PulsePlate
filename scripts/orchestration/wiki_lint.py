"""Lint advisory wiki pages (frontmatter + raw hash presence).

RU: Проверка полей метаданных и наличия raw-копии; только локально.
EN: Read-only; no network; does not modify support plane.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Final

from scripts.orchestration import _wiki_compiler_support as wcs

EXIT_OK: Final[int] = 0
EXIT_VIOLATIONS: Final[int] = 1
EXIT_USAGE: Final[int] = 2

_REQUIRED_KEYS = ("advisory", "corpus", "content_hash", "ingested_at")
_CONTENT_HASH_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_INDEX_PAGE_LINK_RE: Final[re.Pattern[str]] = re.compile(r"\]\(pages/([^)/]+)\.md\)")
_LOCAL_PAGE_LINK_RE: Final[re.Pattern[str]] = re.compile(
    r"\[[^\]]+\]\(<?(?:\./)?pages/([^)/]+)\.md(?:#[^)>\s]+)?(?:>?|\s+[^)]*)\)"
)
_FENCE_OPEN_RE: Final[re.Pattern[str]] = re.compile(r"^(`{3,}|~{3,})")


def _index_page_slugs(index_path: Path) -> set[str] | None:
    if not index_path.is_file():
        return None
    text = index_path.read_text(encoding="utf-8")
    return {match.group(1) for match in _INDEX_PAGE_LINK_RE.finditer(text)}


def _strip_fenced_code_blocks(body: str) -> str:
    kept: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    for line in body.splitlines():
        stripped = line.lstrip()
        opening = _FENCE_OPEN_RE.match(stripped)
        if not in_fence and opening is not None:
            in_fence = True
            fence_marker = opening.group(1)
            continue
        if (
            in_fence
            and fence_marker is not None
            and stripped.startswith(fence_marker[0] * len(fence_marker))
        ):
            in_fence = False
            fence_marker = None
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def _local_page_links(body: str) -> set[str]:
    linkable_body = _strip_fenced_code_blocks(body)
    slugs = {match.group(1) for match in _LOCAL_PAGE_LINK_RE.finditer(linkable_body)}
    return {slug for slug in slugs if _is_valid_wiki_slug(slug)}


def _is_valid_wiki_slug(slug: str) -> bool:
    try:
        wcs.validate_wiki_slug(slug)
    except ValueError:
        return False
    return True


def lint_corpus(
    *,
    corpus: str,
    wiki_root: Path,
    repo_root: Path,
) -> list[str]:
    """Return human-readable violation messages (empty if OK)."""

    violations: list[str] = []
    layout = wcs.corpus_layout(wcs.corpus_base(wiki_root, corpus))
    pages_dir = layout["pages"]
    raw_dir = layout["raw"]
    if not pages_dir.is_dir():
        violations.append("pages_directory_missing")
        return violations
    page_slugs = {page.stem for page in sorted(pages_dir.glob("*.md"))}
    indexed_slugs = _index_page_slugs(layout["index"])
    if indexed_slugs is None:
        violations.append("index_missing")
    else:
        for slug in sorted(page_slugs - indexed_slugs):
            violations.append(f"index_missing_page:{slug}")
        for slug in sorted(indexed_slugs - page_slugs):
            violations.append(f"index_stale_page:{slug}")
    for page in sorted(pages_dir.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        meta, body = wcs.parse_frontmatter(text)
        for key in _REQUIRED_KEYS:
            if key not in meta:
                violations.append(f"{page.name}:missing_meta:{key}")
        if meta.get("advisory") != "true":
            violations.append(f"{page.name}:advisory_not_true")
        ch = str(meta.get("content_hash", ""))
        if not ch:
            violations.append(f"{page.name}:empty_content_hash")
            continue
        if not _CONTENT_HASH_RE.match(ch):
            violations.append(f"{page.name}:invalid_content_hash_format")
            continue
        raw_path = raw_dir / f"{ch}.md"
        if not raw_path.is_file():
            violations.append(f"{page.name}:missing_raw:{ch}")
        for target in sorted(_local_page_links(body) - page_slugs):
            violations.append(f"{page.name}:page_local_link_missing:{target}")
    return violations


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default="project_internal")
    p.add_argument("--wiki-root", type=Path, default=wcs.DEFAULT_WIKI_ROOT)
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = wcs.resolve_repo_root(args.repo_root)
    wiki_root = args.wiki_root
    if not wiki_root.is_absolute():
        wiki_root = (repo_root / wiki_root).resolve()
    try:
        violations = lint_corpus(corpus=args.corpus, wiki_root=wiki_root, repo_root=repo_root)
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    print(
        json.dumps(
            {
                "corpus": args.corpus,
                "ok": not violations,
                "violations": violations,
            },
            sort_keys=True,
        )
    )
    return EXIT_OK if not violations else EXIT_VIOLATIONS


if __name__ == "__main__":
    raise SystemExit(main())
